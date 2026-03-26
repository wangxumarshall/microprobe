# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Instruction Comparator
"""

from __future__ import absolute_import, print_function

from microprobe.target.isa.comparator import GenericInstructionComparator
from microprobe.utils.typeguard_decorator import typeguard_testsuite


@typeguard_testsuite
class Arm64InstructionComparator(GenericInstructionComparator):
    """ARM64 Instruction Comparator implementation."""
    
    def __init__(self):
        super(Arm64InstructionComparator, self).__init__()
    
    def compare(self, instr1, instr2):
        """Compare two ARM64 instructions."""
        # Basic comparison - can be extended for ARM64-specific logic
        if instr1.name != instr2.name:
            return False
        if instr1.mnemonic != instr2.mnemonic:
            return False
        return True
