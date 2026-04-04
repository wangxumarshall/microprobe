#!/usr/bin/env python3
"""Batch ARM64 SDC testcase generator — writes to vault."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import List, Optional

# Setup microprobe paths
_MICROPROBE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_MICROPROBE_ROOT / "src"))
sys.path.insert(0, str(_MICROPROBE_ROOT / "targets"))

# Env for microprobe
os.environ.setdefault(
    "MICROPROBEDATA",
    str(_MICROPROBE_ROOT / "targets"),
)
os.environ.setdefault(
    "MICROPROBEWRAPPERS",
    str(_MICROPROBE_ROOT / "targets" / "arm64" / "wrappers"),
)

from microprobe.target import import_definition
from microprobe.code import get_wrapper
from microprobe.utils.policy import find_policy

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT = REPO_ROOT / "artifacts" / "sdc_vault.sqlite3"
DEFAULT_TARGET_DEF = "armv8_common-armv8_common-aarch64_baremetal"
WRAPPER_NAME = "BareMetalDiffWrapper"


def _hash_key(asm_lines: List[str]) -> str:
    content = "\n".join(asm_lines)
    return hashlib.sha1(content.encode()).hexdigest()[:16]


def _compute_risk(ace: float, ibr: float, mem: float) -> float:
    """Weighted risk score from component scores."""
    return ace * 0.5 + ibr * 0.3 + mem * 0.2


def generate_testcase(
    target_def: str = DEFAULT_TARGET_DEF,
    benchmark_size: int = 64,
    sequence_length: int = 8,
    strict_validation: bool = False,
) -> dict:
    """Generate a single ARM64 SDC testcase via Microprobe."""
    target = import_definition(target_def)
    policy = find_policy(target.name, "sdc_fuzzing")
    wrapper = get_wrapper(WRAPPER_NAME)()
    synth = policy.apply(
        target,
        wrapper,
        benchmark_size=benchmark_size,
        sequence_length=sequence_length,
        strict_validation=strict_validation,
    )
    bench = synth.synthesize()

    # Extract assembly lines
    asm_lines = []
    for bbl in bench.cfg.bbls:
        for instr in bbl.instrs:
            asm = instr.assembly()
            if asm:
                asm_lines.append(asm)

    # Extract static scores from benchmark metadata (written by SDC analysis passes)
    ace_score = float(bench.get_metadata("ace_score", 0.0))
    ibr_score = float(bench.get_metadata("ibr_score", 0.0))
    mem_score = float(bench.get_metadata("memory_pressure_score", 0.0))
    risk_score = _compute_risk(ace_score, ibr_score, mem_score)

    return {
        "asm_content": "\n".join(asm_lines),
        "target_name": target.name,
        "policy_name": "sdc_fuzzing",
        "ace_score": ace_score,
        "ibr_score": ibr_score,
        "memory_pressure_score": mem_score,
        "risk_score": risk_score,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate ARM64 SDC testcases and write to vault."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_VAULT,
        help="Vault SQLite database path.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of testcases to generate.",
    )
    parser.add_argument(
        "--benchmark-size",
        type=int,
        default=64,
        help="Number of instructions per testcase.",
    )
    parser.add_argument(
        "--sequence-length",
        type=int,
        default=8,
        help="Number of SDC-sensitive instructions in sequence.",
    )
    parser.add_argument(
        "--target-def",
        default=DEFAULT_TARGET_DEF,
        help="Microprobe target definition string.",
    )
    parser.add_argument(
        "--strict-validation",
        action="store_true",
        help="Enable strict Capstone validation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated asm without writing to vault.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    if args.dry_run:
        print(f"Generating 1 testcase (dry-run)...")
        result = generate_testcase(
            target_def=args.target_def,
            benchmark_size=args.benchmark_size,
            sequence_length=args.sequence_length,
            strict_validation=args.strict_validation,
        )
        print(f"Target: {result['target_name']}")
        print(f"ACE={result['ace_score']:.3f}  IBR={result['ibr_score']:.3f}  MEM={result['memory_pressure_score']:.3f}  RISK={result['risk_score']:.3f}")
        print(f"\nAssembly ({len(result['asm_content'].splitlines())} lines):")
        print(result["asm_content"])
        return 0

    # Import vault
    sys.path.insert(0, str(REPO_ROOT))
    from sdc_vault import SDCVault, VaultEntry

    vault = SDCVault(args.db)

    generated = 0
    skipped = 0

    for i in range(args.count):
        try:
            result = generate_testcase(
                target_def=args.target_def,
                benchmark_size=args.benchmark_size,
                sequence_length=args.sequence_length,
                strict_validation=args.strict_validation,
            )
        except Exception as exc:
            print(f"[{i+1}] Generation failed: {exc}", file=sys.stderr)
            skipped += 1
            continue

        asm_lines = result["asm_content"].splitlines()
        testcase_key = f"sdc_{_hash_key(asm_lines)}"

        entry = VaultEntry(
            testcase_key=testcase_key,
            asm_content=result["asm_content"],
            target_name=result["target_name"],
            policy_name=result["policy_name"],
            ace_score=result["ace_score"],
            ibr_score=result["ibr_score"],
            memory_pressure_score=result["memory_pressure_score"],
            risk_score=result["risk_score"],
            status="PENDING",
        )

        vault.upsert_testcase(entry)
        print(f"[{i+1}] {testcase_key}  ACE={result['ace_score']:.3f}  IBR={result['ibr_score']:.3f}  RISK={result['risk_score']:.3f}")
        generated += 1

    vault.close()
    print(f"\nDone: {generated} written, {skipped} skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())