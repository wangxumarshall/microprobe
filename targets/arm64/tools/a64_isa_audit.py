#!/usr/bin/env python3
"""Audit the local ARM64 ISA definitions against the official Arm A64 XML."""

from __future__ import annotations

import argparse
import json
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

OFFICIAL_XML_URL = (
    "https://developer.arm.com/-/cdn-downloads/permalink/"
    "Exploration-Tools-A64-ISA/ISA_A64/ISA_A64_xml_A_profile-2025-09_ASL1.tar.gz"
)
DEFAULT_XML_DIR = Path(".codex_tmp/arm_a64_xml/xml")
DEFAULT_INSTRUCTION_FILE = Path("targets/arm64/isa/armv8-common/instruction.yaml")


def _safe_extractall(tf: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in tf.getmembers():
        if member.islnk() or member.issym():
            raise ValueError(
                f"Refusing to extract link member '{member.name}' from '{tf.name}'"
            )

        target = (destination / member.name).resolve()
        if target != destination and destination not in target.parents:
            raise ValueError(
                f"Refusing to extract '{member.name}' outside '{destination}'"
            )

    tf.extractall(destination)


def _download_official_xml(xml_dir: Path) -> Path:
    xml_dir.parent.mkdir(parents=True, exist_ok=True)
    archive = xml_dir.parent / "arm_a64.tar.gz"
    if not archive.exists():
        print(f"[audit] downloading official XML from {OFFICIAL_XML_URL}")
        urllib.request.urlretrieve(OFFICIAL_XML_URL, archive)
    if not xml_dir.exists():
        print(f"[audit] extracting {archive}")
        with tarfile.open(archive, "r:gz") as tf:
            _safe_extractall(tf, xml_dir.parent)
        extracted = xml_dir.parent / "ISA_A64_xml_A_profile-2025-09_ASL1"
        if extracted.exists():
            extracted.rename(xml_dir)
    return xml_dir


def _load_current_mnemonics(instruction_file: Path) -> Counter:
    with instruction_file.open("r", encoding="utf-8") as stream:
        instructions = yaml.safe_load(stream) or []
    return Counter(item["Mnemonic"] for item in instructions)


def _parse_official_xml(
    xml_dir: Path, classes: Iterable[str]
) -> Tuple[Dict[str, List[Tuple[str, str]]], Counter]:
    wanted = set(classes)
    by_class: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    class_counts: Counter = Counter()

    for xml_file in sorted(xml_dir.glob("*.xml")):
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            continue

        docvars = {
            elem.attrib.get("key"): elem.attrib.get("value")
            for elem in root.findall("./docvars/docvar")
        }

        if docvars.get("isa") != "A64":
            continue

        instr_class = docvars.get("instr-class")
        if instr_class not in wanted:
            continue

        mnemonic = docvars.get("alias_mnemonic") or docvars.get("mnemonic")
        if mnemonic is None:
            continue

        by_class[instr_class].append((mnemonic, xml_file.name))
        class_counts[instr_class] += 1

    return by_class, class_counts


def build_report(
    instruction_file: Path, xml_dir: Path, classes: Iterable[str]
) -> Dict[str, object]:
    current = _load_current_mnemonics(instruction_file)
    official, class_counts = _parse_official_xml(xml_dir, classes)

    report: Dict[str, object] = {
        "instruction_file": str(instruction_file),
        "xml_dir": str(xml_dir),
        "current_entries": sum(current.values()),
        "current_unique_mnemonics": len(current),
        "current_mnemonics": sorted(current),
        "classes": {},
    }

    for instr_class, entries in sorted(official.items()):
        unique: Dict[str, str] = {}
        for mnemonic, filename in entries:
            unique.setdefault(mnemonic, filename)

        missing = sorted(set(unique) - set(current))
        present = sorted(set(unique) & set(current))
        report["classes"][instr_class] = {
            "xml_entries": class_counts[instr_class],
            "xml_unique_mnemonics": len(unique),
            "present_unique_mnemonics": len(present),
            "missing_unique_mnemonics": len(missing),
            "missing": [
                {"mnemonic": mnemonic, "xml_file": unique[mnemonic]}
                for mnemonic in missing
            ],
        }

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the local ARM64 instruction set definition against the "
            "official Arm A64 XML catalog."
        )
    )
    parser.add_argument(
        "--instruction-file",
        default=str(DEFAULT_INSTRUCTION_FILE),
        help="Path to the local ARM64 instruction.yaml file.",
    )
    parser.add_argument(
        "--xml-dir",
        default=str(DEFAULT_XML_DIR),
        help="Path to an extracted Arm A64 XML directory.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the official XML archive when --xml-dir does not exist.",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        default=["general", "system", "float", "advsimd"],
        help="Official Arm instruction classes to include in the audit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full report as JSON.",
    )
    parser.add_argument(
        "--top-missing",
        type=int,
        default=25,
        help="Number of missing mnemonics to show per class in text mode.",
    )
    args = parser.parse_args()

    instruction_file = Path(args.instruction_file)
    xml_dir = Path(args.xml_dir)

    if not xml_dir.exists():
        if not args.download:
            raise SystemExit(
                f"XML directory '{xml_dir}' does not exist. Re-run with --download."
            )
        _download_official_xml(xml_dir)

    report = build_report(instruction_file, xml_dir, args.classes)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print("ARM64 ISA audit")
    print(f"  instruction file : {instruction_file}")
    print(f"  official xml dir : {xml_dir}")
    print(f"  current entries  : {report['current_entries']}")
    print(f"  current mnemonics: {report['current_unique_mnemonics']}")

    for instr_class, payload in report["classes"].items():
        print(f"\n[{instr_class}]")
        print(f"  xml unique   : {payload['xml_unique_mnemonics']}")
        print(f"  present      : {payload['present_unique_mnemonics']}")
        print(f"  missing      : {payload['missing_unique_mnemonics']}")
        for missing in payload["missing"][: args.top_missing]:
            print(f"    - {missing['mnemonic']} ({missing['xml_file']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
