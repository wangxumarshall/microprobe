#!/usr/bin/env python3
"""Offline ARM64 SDC testcase generator with SQLite vault persistence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sdc_agent.generation import (
    DEFAULT_POLICY,
    PROFILE_SIM_SAFE,
    DEFAULT_TARGET,
    DEFAULT_WRAPPER,
    compute_risk_score as _compute_risk_score,
    generate_batch,
    generate_testcase as _generate_one,
    summarize_generation_result,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate ARM64 SDC fuzzing candidates and store them in SQLite."
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        help="Target tuple for Microprobe import_definition().",
    )
    parser.add_argument(
        "--policy",
        default=DEFAULT_POLICY,
        help="Policy name to use for testcase generation.",
    )
    parser.add_argument(
        "--wrapper",
        default=DEFAULT_WRAPPER,
        help="Wrapper used for persisted testcase text.",
    )
    parser.add_argument(
        "--profile",
        default=PROFILE_SIM_SAFE,
        help="Generation profile contract. Supported: SIM_SAFE, HW_AGGRESSIVE.",
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
        default=Path("artifacts") / "sdc_vault.sqlite3",
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


def main() -> int:
    args = parse_args()
    payload = generate_batch(
        db_path=args.db,
        target=args.target,
        policy=args.policy,
        wrapper=args.wrapper,
        count=args.count,
        jobs=args.jobs,
        sequence_length=args.sequence_length,
        benchmark_size=args.benchmark_size,
        dependency_distance=args.dependency_distance,
        memory_stream_stride=args.memory_stream_stride,
        strict_validation=args.strict_validation,
        seed=args.seed,
        output_dir=args.output_dir,
        profile_name=args.profile,
    )
    print(summarize_generation_result(payload))
    return 0 if not payload["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
