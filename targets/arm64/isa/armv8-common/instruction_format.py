# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Instruction Format Implementation
"""

from __future__ import absolute_import, print_function

from microprobe.target.isa.instruction_field import GenericInstructionField
from microprobe.target.isa.instruction_format import GenericInstructionFormat
from microprobe.target.isa.operand import OperandConst
from microprobe.utils.typeguard_decorator import typeguard_testsuite


@typeguard_testsuite
class Arm64InstructionFormat(GenericInstructionFormat):
    """ARM64 Instruction Format implementation."""

    def __init__(self, name, descr, fields, assembly):
        fields = list(fields)
        normalized_fields = []
        seen_names = {}

        for field in fields:
            count = seen_names.get(field.name, 0)
            seen_names[field.name] = count + 1

            if count == 0:
                normalized_fields.append(field)
                continue

            normalized_fields.append(
                GenericInstructionField(
                    f"{field.name}_{count}",
                    f"{field.description} [{count}]",
                    field.size,
                    field.default_show,
                    field.default_io,
                    field.default_operand,
                )
            )

        total_bits = sum(field.size for field in normalized_fields)

        # Current ARM64 YAML stores a partial layout plus a separate opcode
        # prefix. Pad the residual bits so the generic formatter can import
        # the definition and the rest of the stack can reason about operands.
        if total_bits % 8 != 0:
            pad_bits = 8 - (total_bits % 8)
            normalized_fields.append(
                GenericInstructionField(
                    "_pad_%s" % name,
                    "Auto-generated ARM64 padding",
                    pad_bits,
                    False,
                    "?",
                    OperandConst("Zero", "Zero operand", 0),
                )
            )

        super(Arm64InstructionFormat, self).__init__(
            name, descr, normalized_fields, assembly
        )

    def __str__(self):
        return "Arm64InstructionFormat(%s)" % self.name
