# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""Static SDC coverage passes for ARM64/Kunpeng-style fuzzing."""

from __future__ import absolute_import, annotations

from typing import Iterable, List

import microprobe.passes
from microprobe.exceptions import MicroprobeCodeGenerationError
from microprobe.utils.logger import get_logger

LOG = get_logger(__name__)

__all__ = [
    "StaticACECalculatorPass",
    "StaticIBRCoveragePass",
    "Kunpeng920MemoryPressurePass",
    "CapstoneValidationPass",
]


def _iter_instructions(building_block) -> List:
    instructions = []
    for bbl in building_block.cfg.bbls:
        instructions.extend(bbl.instrs)
    return instructions


def _safe_set_metadata(building_block, key, value):
    if hasattr(building_block, "set_metadata"):
        building_block.set_metadata(key, value)
    else:
        building_block.add_info(f"{key}={value}")


class StaticACECalculatorPass(microprobe.passes.Pass):
    """Estimate ACE-style exposure as def-to-last-use instruction distance."""

    def __init__(self):
        super(StaticACECalculatorPass, self).__init__()
        self._description = (
            "Estimate register exposure using static def-to-last-use distance"
        )

    def __call__(self, building_block, dummy_target):
        instructions = _iter_instructions(building_block)
        if len(instructions) <= 1:
            _safe_set_metadata(building_block, "ace_score", 0.0)
            return

        spans = []
        for idx, instr in enumerate(instructions):
            written = list(dict.fromkeys(instr.sets()))
            if not written:
                continue

            for reg in written:
                last_use = None
                for future_idx in range(idx + 1, len(instructions)):
                    if reg in instructions[future_idx].uses():
                        last_use = future_idx

                if last_use is None:
                    continue

                spans.append(last_use - idx)

        if not spans:
            ace_score = 0.0
        else:
            max_span = max(len(instructions) - 1, 1)
            ace_score = min(sum(spans) / (len(spans) * max_span), 1.0)

        _safe_set_metadata(building_block, "ace_score", ace_score)
        building_block.add_pass_info(f"Static ACE score: {ace_score:.4f}")


class StaticIBRCoveragePass(microprobe.passes.Pass):
    """Estimate information-bit richness from wide register and memory usage."""

    def __init__(self):
        super(StaticIBRCoveragePass, self).__init__()
        self._description = (
            "Estimate wide-data coverage using register types and memory lengths"
        )

    def __call__(self, building_block, dummy_target):
        instructions = _iter_instructions(building_block)
        if not instructions:
            _safe_set_metadata(building_block, "ibr_score", 0.0)
            return

        total_observations = 0
        wide_observations = 0

        for instr in instructions:
            registers = list(instr.sets()) + list(instr.uses())
            for reg in registers:
                total_observations += 1
                if getattr(getattr(reg, "type", None), "size", 0) >= 64:
                    wide_observations += 1
                if getattr(getattr(reg, "type", None), "size", 0) >= 128:
                    wide_observations += 1

            for memoperand in instr.memory_operands():
                if memoperand.length is None:
                    continue
                total_observations += 1
                if memoperand.length >= 8:
                    wide_observations += 1
                if memoperand.length >= 16:
                    wide_observations += 1

        ibr_score = (
            0.0
            if total_observations == 0
            else min(wide_observations / float(total_observations), 1.0)
        )
        _safe_set_metadata(building_block, "ibr_score", ibr_score)
        building_block.add_pass_info(f"Static IBR score: {ibr_score:.4f}")


class Kunpeng920MemoryPressurePass(microprobe.passes.Pass):
    """Estimate how likely a sequence is to stress Kunpeng920-style memory."""

    _HIGH_VALUE_PREFIXES = (
        "LDP",
        "STP",
        "LDXR",
        "STXR",
        "LDAXR",
        "STLXR",
        "CAS",
        "LDADD",
        "PRFM",
    )

    def __init__(self):
        super(Kunpeng920MemoryPressurePass, self).__init__()
        self._description = (
            "Score pair-memory, atomic, and cache-pressure-friendly patterns"
        )

    def __call__(self, building_block, dummy_target):
        instructions = _iter_instructions(building_block)
        if not instructions:
            _safe_set_metadata(building_block, "memory_pressure_score", 0.0)
            return

        score = 0.0
        for instr in instructions:
            mnemonic = instr.mnemonic.upper()
            if any(mnemonic.startswith(prefix) for prefix in self._HIGH_VALUE_PREFIXES):
                score += 1.0
            elif getattr(instr, "access_storage", False):
                score += 0.35

        normalized = min(score / float(len(instructions)), 1.0)
        _safe_set_metadata(building_block, "memory_pressure_score", normalized)
        _safe_set_metadata(building_block, "preferred_stride_bytes", 8192)
        building_block.add_pass_info(
            f"Kunpeng920 memory pressure score: {normalized:.4f}"
        )


class CapstoneValidationPass(microprobe.passes.Pass):
    """Best-effort disassembly validation for generated instruction streams."""

    def __init__(self, strict: bool = False):
        super(CapstoneValidationPass, self).__init__()
        self._strict = strict
        self._description = "Validate generated instructions using Capstone"

    def __call__(self, building_block, dummy_target):
        instructions = _iter_instructions(building_block)
        if not instructions:
            _safe_set_metadata(building_block, "capstone_validated", False)
            return

        try:
            from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
        except ImportError:
            building_block.add_warning(
                "Capstone not available; skipping instruction validation"
            )
            _safe_set_metadata(building_block, "capstone_validated", False)
            return

        disassembler = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        failures = []

        for instr in instructions:
            try:
                binary = instr.binary()
                blob = self._binary_to_bytes(binary)
                decoded = list(disassembler.disasm(blob, 0))
                if not decoded:
                    failures.append(instr.name)
            except Exception as exc:  # pragma: no cover - best effort path
                LOG.debug("Capstone validation failed for %s: %s", instr, exc)
                failures.append(instr.name)

        if failures:
            message = (
                "Capstone validation failed for %d instruction(s): %s"
                % (len(failures), ", ".join(failures[:8]))
            )
            if self._strict:
                raise MicroprobeCodeGenerationError(message)
            building_block.add_warning(message)
            _safe_set_metadata(building_block, "capstone_validated", False)
            return

        _safe_set_metadata(building_block, "capstone_validated", True)
        building_block.add_pass_info("Capstone validation passed")

    @staticmethod
    def _binary_to_bytes(binary: str) -> bytes:
        value = binary.strip().lower()

        if value.startswith("0x"):
            value = value[2:]
            if len(value) % 2 == 1:
                value = "0" + value
            return bytes.fromhex(value)

        if value.startswith("0b"):
            value = value[2:]

        if set(value) <= {"0", "1"} and len(value) % 8 == 0:
            return int(value, 2).to_bytes(len(value) // 8, byteorder="big")

        if len(value) % 2 == 0:
            return bytes.fromhex(value)

        raise ValueError(f"Unsupported instruction binary encoding: {binary}")
