# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Instruction Implementation
"""

from __future__ import absolute_import, print_function

from microprobe.target.isa.instruction import GenericInstructionType
from microprobe.utils.typeguard_decorator import typeguard_testsuite


@typeguard_testsuite
class Arm64Instruction(GenericInstructionType):
    """ARM64 Instruction implementation."""
    
    def __init__(self, name, mnemonic, opcode, descr, iformat, operands, 
                 ioperands, moperands, instruction_checks, target_checks):
        super(Arm64Instruction, self).__init__(
            name, mnemonic, opcode, descr, iformat, operands,
            ioperands, moperands, instruction_checks, target_checks
        )
    
    def __str__(self):
        return "Arm64Instruction(%s)" % self.name
