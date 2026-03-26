# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Instruction Field Implementation
"""

from __future__ import absolute_import, print_function

from microprobe.target.isa.instruction_field import GenericInstructionField
from microprobe.utils.typeguard_decorator import typeguard_testsuite


@typeguard_testsuite
class Arm64InstructionField(GenericInstructionField):
    """ARM64 Instruction Field implementation."""
    
    def __init__(self, name, descr, size, **kwargs):
        super(Arm64InstructionField, self).__init__(name, descr, size, **kwargs)
    
    def __str__(self):
        return "Arm64InstructionField(%s)" % self.name
