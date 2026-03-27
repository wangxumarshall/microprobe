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
    """Pick ARM64 instructions that are more likely to expose silent faults."""

    _FMA_MNEMONICS = {"FMADD", "FMSUB", "FNMADD", "FNMSUB"}
    _PAIR_MEMORY_MNEMONICS = {"LDP", "STP"}
    _LSE_PREFIXES = ("CAS", "LDADD", "LDXR", "STXR", "LDAXR", "STLXR")

    def __init__(self, target):
        self._target = target

    def collect(self):
        instructions = list(self._target.isa.instructions.values())
        fma = []
        pair_memory = []
        lse = []
        for instr in instructions:
            mnemonic = instr.mnemonic.upper()
            if mnemonic in self._FMA_MNEMONICS:
                fma.append(instr)
                continue
            if (
                mnemonic in self._PAIR_MEMORY_MNEMONICS
                and instr.name.endswith("_X_V0")
            ):
                pair_memory.append(instr)
                continue
            if any(mnemonic.startswith(prefix) for prefix in self._LSE_PREFIXES):
                lse.append(instr)

        for bucket in [fma, pair_memory, lse]:
            bucket.sort(key=lambda instr: instr.name)

        sensitive = []
        max_len = max(len(fma), len(pair_memory), len(lse), 1)
        for idx in range(max_len):
            if idx < len(fma):
                sensitive.append(fma[idx])
            if idx < len(pair_memory):
                sensitive.append(pair_memory[idx])
            if idx < len(lse):
                sensitive.append(lse[idx])

        return sensitive

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
    synthesizer.add_pass(
        microprobe.passes.memory.SingleMemoryStreamPass(
            memory_stream_size,
            memory_stream_stride,
        )
    )

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
