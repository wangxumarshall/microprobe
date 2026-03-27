# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Instruction Implementation
"""

from __future__ import absolute_import, print_function

from microprobe.utils.misc import OrderedDict
from microprobe.target.isa.instruction import GenericInstructionType
from microprobe.target.isa.operand import (
    MemoryOperand,
    MemoryOperandDescriptor,
)
from microprobe.utils.typeguard_decorator import typeguard_testsuite


@typeguard_testsuite
class Arm64Instruction(GenericInstructionType):
    """ARM64 Instruction implementation."""

    _BRANCH_FORMATS = {
        "UNCOND_BRANCH_IMM",
        "COND_BRANCH_IMM",
        "COMPARE_BRANCH",
        "TEST_BRANCH",
        "UNCOND_BRANCH_REG",
    }
    _BRANCH_RELATIVE_FORMATS = {
        "UNCOND_BRANCH_IMM",
        "COND_BRANCH_IMM",
        "COMPARE_BRANCH",
        "TEST_BRANCH",
    }
    _MEMORY_FORMATS = {
        "LOAD_STORE_IMM",
        "LOAD_STORE_REG",
        "LOAD_STORE_PAIR",
        "LOAD_LITERAL",
        "LOAD_STORE_EXCLUSIVE",
        "ATOMIC",
        "CAS",
    }
    _STORE_MNEMONIC_PREFIXES = ("STR", "STP", "ST1", "STXR", "STLXR")
    _LOAD_MNEMONIC_PREFIXES = ("LDR", "LDP", "LD1", "LDXR", "LDAXR")
    _ATOMIC_MEMORY_FORMATS = {"ATOMIC", "CAS"}
    _TRAP_MNEMONICS = {"BRK", "HLT", "SMC"}
    _SYSCALL_MNEMONICS = {"SVC"}
    _HYPERVISOR_MNEMONICS = {"HVC", "ERET"}

    def __init__(
        self,
        name,
        mnemonic,
        opcode,
        descr,
        iformat,
        operands,
        ioperands,
        moperands,
        instruction_checks,
        target_checks,
    ):
        normalized_operands = OrderedDict()
        for field_name, (operand, io_def) in operands.items():
            normalized_operands[field_name] = (operand.copy(), io_def)

        # The local ARM64 YAML only spells out fields that vary per
        # instruction and relies on the field defaults for the rest.
        # Normalize to the fully expanded representation expected by
        # GenericInstructionType.
        for field in iformat.fields:
            if field.name not in normalized_operands:
                normalized_operands[field.name] = (
                    field.default_operand.copy(),
                    field.default_io,
                )

        super(Arm64Instruction, self).__init__(
            name,
            mnemonic,
            opcode,
            descr,
            iformat,
            normalized_operands,
            ioperands,
            moperands,
            instruction_checks,
            target_checks,
        )

        if len(self._memoperands) == 0:
            self._memoperands = self._infer_memory_operands()

    def _memory_operand_type(
        self, field_name, address_base=False, address_index=False
    ):
        operand = self.operands[field_name][0]

        if address_base:
            operand._ab = True
            operand._ai = False
            operand._aim = False

        if address_index:
            if operand.immediate or operand.address_relative:
                operand._aim = True
            else:
                operand._ai = True

        return operand

    def _memory_length_bytes(self):
        upper_name = self.name.upper()
        upper_mnemonic = self.mnemonic.upper()

        if upper_name.endswith("_W_IMM_V0") or "_W_" in upper_name:
            return 4

        if upper_name.startswith(("LDR_V_", "STR_V_", "LD1_V_", "ST1_V_")):
            return 16

        if upper_name.startswith(("LDP_V_", "STP_V_")):
            return 32

        if upper_name.startswith(("LDP_", "STP_")):
            return 16

        if upper_mnemonic in {"LD1", "ST1"}:
            return 16

        return 8

    def _infer_memory_operand(self, io_flags, address_fields):
        address_operands = OrderedDict()
        for field_name, role in address_fields:
            address_operands[field_name] = self._memory_operand_type(
                field_name,
                address_base=(role == "base"),
                address_index=(role == "index"),
            )

        length = self._memory_length_bytes()
        memoperand = MemoryOperand(address_operands, OrderedDict([("len", length)]))
        return MemoryOperandDescriptor(memoperand, io_flags, length)

    def _infer_memory_operands(self):
        if self.format.name not in self._MEMORY_FORMATS:
            return []

        if self.format.name in self._ATOMIC_MEMORY_FORMATS:
            return [self._infer_memory_operand("I", [("Rn", "base")])]

        mnemonic = self.mnemonic.upper()
        is_store = any(
            mnemonic.startswith(prefix) for prefix in self._STORE_MNEMONIC_PREFIXES
        )
        is_load = any(
            mnemonic.startswith(prefix) for prefix in self._LOAD_MNEMONIC_PREFIXES
        )

        if not is_load and not is_store:
            return []

        io_flags = "O" if is_store else "I"

        if self.format.name == "LOAD_STORE_IMM":
            return [self._infer_memory_operand(io_flags, [("Rn", "base"), ("imm9", "index")])]

        if self.format.name == "LOAD_STORE_REG":
            if "Rm" in self.operands:
                return [self._infer_memory_operand(io_flags, [("Rn", "base"), ("Rm", "index")])]
            return [self._infer_memory_operand(io_flags, [("Rn", "base")])]

        if self.format.name == "LOAD_STORE_PAIR":
            return [self._infer_memory_operand(io_flags, [("Rn", "base"), ("imm7", "index")])]

        if self.format.name == "LOAD_LITERAL":
            return [self._infer_memory_operand(io_flags, [("imm19", "index")])]

        if self.format.name == "LOAD_STORE_EXCLUSIVE":
            return [self._infer_memory_operand(io_flags, [("Rn", "base")])]

        return []

    @property
    def branch(self):
        return self.format.name in self._BRANCH_FORMATS

    @property
    def branch_relative(self):
        return self.format.name in self._BRANCH_RELATIVE_FORMATS

    @property
    def access_storage(self):
        return len(self.memory_operand_descriptors) > 0

    @property
    def access_storage_with_update(self):
        return False

    @property
    def privileged(self):
        return self.format.name == "SYSTEM_REG"

    @property
    def hypervisor(self):
        return self.mnemonic.upper() in self._HYPERVISOR_MNEMONICS

    @property
    def trap(self):
        return self.mnemonic.upper() in self._TRAP_MNEMONICS

    @property
    def syscall(self):
        return self.mnemonic.upper() in self._SYSCALL_MNEMONICS

    def __str__(self):
        return "Arm64Instruction(%s)" % self.name
