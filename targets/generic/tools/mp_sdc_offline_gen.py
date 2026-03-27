#!/usr/bin/env python3
"""Offline ARM64 SDC testcase generator with SQLite vault persistence."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import random
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[4]
MICROPROBE_SRC = REPO_ROOT / "microprobe" / "src"
TARGETS_ROOT = REPO_ROOT / "microprobe" / "targets"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(MICROPROBE_SRC) not in sys.path:
    sys.path.insert(0, str(MICROPROBE_SRC))


def bootstrap_microprobe_paths() -> None:
    from microprobe import MICROPROBE_RC

    for key in [
        "default_paths",
        "architecture_paths",
        "microarchitecture_paths",
        "environment_paths",
        "wrapper_paths",
    ]:
        if str(TARGETS_ROOT) not in MICROPROBE_RC[key]:
            MICROPROBE_RC[key].append(str(TARGETS_ROOT))


bootstrap_microprobe_paths()

from microprobe.code import get_wrapper  # noqa: E402
from microprobe.target import import_definition  # noqa: E402
from microprobe.utils.policy import find_policy  # noqa: E402

from sdc_vault import SDCVault, VaultEntry  # noqa: E402

try:  # noqa: E402
    from sdc_fuzzing_generator import InstructionPool
except Exception:  # pragma: no cover - fallback path
    InstructionPool = None


def _select_instructions(target, sequence_length: int, seed: int):
    rng = random.Random(seed)

    if InstructionPool is not None:
        pool = InstructionPool(target)
        candidates: List[Any] = []
        for category in ["floating", "memory", "branch", "logical", "arithmetic"]:
            candidates.extend(pool.get_top_instructions(category=category, limit=4))

        if candidates:
            return [rng.choice(candidates) for _ in range(sequence_length)]

    try:
        from microprobe.targets.arm64.policies.sdc_fuzzing_policy import (
            SDCSensitiveAnalyzer,
        )

        analyzer = SDCSensitiveAnalyzer(target)
        candidates = analyzer.collect()
        if candidates:
            return [rng.choice(candidates) for _ in range(sequence_length)]
    except Exception:
        pass

    instructions = list(target.isa.instructions.values())
    if not instructions:
        raise RuntimeError("No instructions available in target ISA")
    return [rng.choice(instructions) for _ in range(sequence_length)]


def _compute_risk_score(metadata: Dict[str, Any]) -> float:
    ace = float(metadata.get("ace_score", 0.0))
    ibr = float(metadata.get("ibr_score", 0.0))
    mem = float(metadata.get("memory_pressure_score", 0.0))
    return (ace * 0.45) + (ibr * 0.35) + (mem * 0.20)


def _generate_one(task: Dict[str, Any]) -> Dict[str, Any]:
    bootstrap_microprobe_paths()

    target = import_definition(task["target"])

    wrapper_name = task["wrapper"]
    try:
        wrapper_cls = get_wrapper(wrapper_name)
    except Exception:
        fallback_name = "Arm64AsmWrapper"
        wrapper_cls = get_wrapper(fallback_name)
        wrapper_name = fallback_name

    wrapper = wrapper_cls()
    policy = find_policy(task["target"], task["policy"])
    instructions = _select_instructions(
        target, task["sequence_length"], int(task["seed"])
    )

    synth = policy.apply(
        target,
        wrapper,
        instructions=instructions,
        benchmark_size=task["benchmark_size"],
        dependency_distance=task["dependency_distance"],
        sequence_length=task["sequence_length"],
        memory_stream_stride=task["memory_stream_stride"],
        strict_validation=task["strict_validation"],
    )
    bench = synth.synthesize()
    asm_content = "".join(str(elem) for elem in synth._wrap(bench))
    testcase_key = hashlib.sha1(asm_content.encode("utf-8")).hexdigest()

    metadata = dict(getattr(bench, "metadata", {}))
    metadata["wrapper_name"] = wrapper_name
    metadata["instruction_names"] = [instr.name for instr in instructions]
    metadata["seed"] = task["seed"]
    risk_score = _compute_risk_score(metadata)
    metadata["risk_score"] = risk_score

    output_file = None
    if task["output_dir"] is not None:
        output_dir = Path(task["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = ".s" if wrapper_name in {"Assembly", "Arm64AsmWrapper"} else ".c"
        output_file = output_dir / f"{testcase_key}{suffix}"
        output_file.write_text(asm_content, encoding="utf-8")

    entry = VaultEntry(
        testcase_key=testcase_key,
        asm_content=asm_content,
        target_name=task["target"],
        policy_name=task["policy"],
        ace_score=float(metadata.get("ace_score", 0.0)),
        ibr_score=float(metadata.get("ibr_score", 0.0)),
        memory_pressure_score=float(metadata.get("memory_pressure_score", 0.0)),
        risk_score=risk_score,
        metadata=metadata,
    )
    return {
        "entry": entry,
        "output_file": str(output_file) if output_file is not None else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate ARM64 SDC fuzzing candidates and store them in SQLite."
    )
    parser.add_argument(
        "--target",
        default="armv8_common-armv8_common-aarch64_linux_gcc",
        help="Target tuple for Microprobe import_definition().",
    )
    parser.add_argument(
        "--policy",
        default="sdc_fuzzing",
        help="Policy name to use for testcase generation.",
    )
    parser.add_argument(
        "--wrapper",
        default="Arm64AsmWrapper",
        help="Wrapper used for persisted testcase text.",
    )
    parser.add_argument(
        "--count", type=int, default=16, help="Number of candidates to generate."
    )
    parser.add_argument(
        "--jobs", type=int, default=1, help="Parallel worker count."
    )
    parser.add_argument(
        "--sequence-length",
        type=int,
        default=8,
        help="Instruction sequence length per testcase.",
    )
    parser.add_argument(
        "--benchmark-size",
        type=int,
        default=64,
        help="Benchmark size passed into the policy.",
    )
    parser.add_argument(
        "--dependency-distance",
        type=int,
        default=1,
        help="Dependency distance passed into the policy.",
    )
    parser.add_argument(
        "--memory-stream-stride",
        type=int,
        default=8192,
        help="Stride used by memory-focused passes.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=REPO_ROOT / "artifacts" / "sdc_vault.sqlite3",
        help="SQLite vault path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory to dump generated sources/assembly.",
    )
    parser.add_argument(
        "--strict-validation",
        action="store_true",
        help="Fail generation when Capstone validation fails.",
    )
    parser.add_argument(
        "--seed", type=int, default=13, help="Base RNG seed."
    )
    return parser.parse_args()


def _task_stream(args: argparse.Namespace) -> Iterable[Dict[str, Any]]:
    for index in range(args.count):
        yield {
            "target": args.target,
            "policy": args.policy,
            "wrapper": args.wrapper,
            "sequence_length": args.sequence_length,
            "benchmark_size": args.benchmark_size,
            "dependency_distance": args.dependency_distance,
            "memory_stream_stride": args.memory_stream_stride,
            "strict_validation": args.strict_validation,
            "seed": args.seed + index,
            "output_dir": str(args.output_dir) if args.output_dir else None,
        }


def main() -> int:
    args = parse_args()
    bootstrap_microprobe_paths()

    successes = 0
    failures: List[Dict[str, Any]] = []

    with SDCVault(args.db) as vault:
        if args.jobs <= 1:
            iterator = map(_generate_one, _task_stream(args))
        else:
            with mp.Pool(processes=args.jobs) as pool:
                iterator = pool.imap_unordered(_generate_one, _task_stream(args))

        for index in range(args.count):
            try:
                result = next(iterator)
            except StopIteration:
                break
            except Exception as exc:
                failures.append({"index": index, "error": str(exc)})
                continue

            vault.upsert_testcase(result["entry"])
            successes += 1

    payload = {
        "requested": args.count,
        "inserted": successes,
        "failed": failures,
        "db": str(args.db),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
