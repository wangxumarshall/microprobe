# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""ARM64 SDC fuzzing policy tuned for Kunpeng920-style stress patterns."""

from __future__ import absolute_import, print_function

import microprobe.code
import microprobe.passes.address
import microprobe.passes.branch
import microprobe.passes.initialization
import microprobe.passes.instruction
import microprobe.passes.memory
import microprobe.passes.register
import microprobe.passes.structure
import microprobe.passes.sdc_analysis
from microprobe.exceptions import MicroprobePolicyError
from microprobe.utils.logger import get_logger
from microprobe.utils.misc import RND, RNDINT

__all__ = [
    "NAME",
    "DESCRIPTION",
    "SUPPORTED_TARGETS",
    "SDCSensitiveAnalyzer",
    "policy",
]

NAME = "sdc_fuzzing"
DESCRIPTION = "Static-score-first SDC fuzzing policy for ARM64"
SUPPORTED_TARGETS = ["all"]

LOG = get_logger(__name__)


def _target_looks_like_arm64(target):
    registers = getattr(target, "registers", {})
    return all(reg in registers for reg in ["X0", "SP", "V0", "LR"])


class SDCSensitiveAnalyzer(object):
    """Pick ARM64 instructions that are more likely to expose silent faults.

    Note: Only uses gem5-compatible instructions to avoid GEM5_UNKNOWN_INST errors.
    Avoids: FMADD, FMLA, CAS*, LDP, STP (unsupported in gem5 SE bare-metal)
    Uses: Simple integer and logical instructions only.
    """

    # Exclude these - not supported in gem5 bare-metal SE or
    # aarch64-elf-gcc/aarch64-elf-as (no LSE target)
    _EXCLUDED_MNEMONICS = {
        # FP SIMD
        "FMADD", "FMSUB", "FNMADD", "FNMSUB",
        "FMLA", "FMLS", "FNMLA", "FNMLS",
        "LD1", "ST1", "LD2", "ST2", "LD3", "ST3", "LD4", "ST4",
        "LD1R", "LD2R",
        # Pair memory (some variants)
        "LDP", "STP",
        # LSE atomics (ARMv8.1 — not in bare-metal gcc/aarch64-elf-as)
        "LDSMAX", "STSMIN", "SDSMAX", "SSMIN",
        "LDUMAX", "STUMAX", "SDUMAX", "SUMAX",
        "LDSABA", "STSABL", "SDSABAL", "SSABAL",
        "LDADD", "LDADDA", "LDADDAL", "LDADDL",
        "STADD", "STADDL",
        "LDCLR", "LDCLRA", "LDCLRAL", "LDCLRL",
        "STCLR", "STCLRL",
        "LDEOR", "LDEORA", "LDEORAL", "LDEORL",
        "STEOR", "STEORL",
        "LDSET", "LDSETA", "LDSETAL", "LDSETL",
        "STSET", "STSETL",
        "SWP", "SWPA", "SWPAL", "SWPL",
        "CAS", "CASA", "CASAL", "CASL",
        "LDAPR", "STLR", "LDAR", "STLAR",
        "LDXR", "STXR", "LDAXR", "STLXR",
        # CRC instructions (sometimes available)
        "CRC32B", "CRC32H", "CRC32W", "CRC32X",
    }

    # Simple integer/logical instructions that work in gem5
    _INCLUDED_MNEMONICS = {
        "MOVZ", "MOVK", "MOVN",                 # Move
        "ADD", "SUB", "CMP", "CMN",             # Arithmetic
        "AND", "ORR", "EOR", "TST",             # Logical
        "LSL", "LSR", "ASR", "ROR",              # Shift
        "LDUR", "STUR", "LDR", "STR",            # Single register memory
        "B", "BL", "BEQ", "BNE", "BGT", "BLT",  # Branch
        "NOP",                                   # No-op
    }

    def __init__(self, target):
        self._target = target

    def collect(self):
        instructions = list(self._target.isa.instructions.values())
        allowed = []

        for instr in instructions:
            mnemonic = instr.mnemonic.upper()
            # Skip excluded instructions
            if mnemonic in self._EXCLUDED_MNEMONICS:
                continue
            # Only include instructions we know work
            if mnemonic in self._INCLUDED_MNEMONICS:
                allowed.append(instr)

        # Sort by name for deterministic ordering
        allowed.sort(key=lambda instr: instr.name)
        return allowed

    def default_sequence(self, limit=8):
        sensitive = self.collect()
        if not sensitive:
            raise MicroprobePolicyError(
                "No ARM64 SDC-sensitive instructions were found in the target ISA"
            )

        if len(sensitive) >= limit:
            return sensitive[:limit]

        sequence = []
        while len(sequence) < limit:
            sequence.extend(sensitive)
        return sequence[:limit]


def policy(target, wrapper, **kwargs):
    """Compose a Microprobe synthesizer for ARM64 SDC fuzzing."""

    if not _target_looks_like_arm64(target):
        raise MicroprobePolicyError(
            f"Policy '{NAME}' not valid for target '{target.name}'. "
            "Expected an ARM64/AArch64 target with X/V register files."
        )

    benchmark_size = kwargs.get("benchmark_size", 64)
    dependency_distance = kwargs.get("dependency_distance", 1)
    memory_stream_size = kwargs.get("memory_stream_size", 32)
    memory_stream_stride = kwargs.get("memory_stream_stride", 8192)

    instructions = kwargs.get("instructions")
    if instructions is None:
        if "instruction" in kwargs:
            instructions = [kwargs["instruction"]]
        else:
            analyzer = SDCSensitiveAnalyzer(target)
            instructions = analyzer.default_sequence(
                limit=kwargs.get("sequence_length", 8)
            )

    synthesizer = microprobe.code.Synthesizer(target, wrapper, value=RNDINT)

    synthesizer.add_pass(
        microprobe.passes.initialization.InitializeRegistersPass(value=RNDINT)
    )
    synthesizer.add_pass(
        microprobe.passes.initialization.InitializeRegistersPass()
    )
    synthesizer.add_pass(
        microprobe.passes.structure.SimpleBuildingBlockPass(benchmark_size)
    )
    synthesizer.add_pass(
        microprobe.passes.instruction.SetInstructionTypeBySequencePass(
            instructions
        )
    )
    synthesizer.add_pass(microprobe.passes.address.UpdateInstructionAddressesPass())

    if dependency_distance < 1:
        synthesizer.add_pass(microprobe.passes.register.NoHazardsAllocationPass())

    synthesizer.add_pass(
        microprobe.passes.register.DefaultRegisterAllocationPass(
            RND, dd=dependency_distance
        )
    )
    synthesizer.add_pass(microprobe.passes.address.UpdateInstructionAddressesPass())
    synthesizer.add_pass(microprobe.passes.sdc_analysis.StaticACECalculatorPass())
    synthesizer.add_pass(microprobe.passes.sdc_analysis.StaticIBRCoveragePass())
    synthesizer.add_pass(
        microprobe.passes.sdc_analysis.Kunpeng920MemoryPressurePass()
    )
    synthesizer.add_pass(
        microprobe.passes.sdc_analysis.CapstoneValidationPass(
            strict=kwargs.get("strict_validation", False)
        )
    )

    return synthesizer
