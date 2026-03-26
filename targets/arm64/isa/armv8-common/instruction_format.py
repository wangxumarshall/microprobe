# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Instruction Format Implementation
"""

from __future__ import absolute_import, print_function

from microprobe.target.isa.instruction_format import GenericInstructionFormat
from microprobe.utils.typeguard_decorator import typeguard_testsuite


@typeguard_testsuite
class Arm64InstructionFormat(GenericInstructionFormat):
    """ARM64 Instruction Format implementation."""
    
    def __init__(self, name, descr, fields, assembly):
        super(Arm64InstructionFormat, self).__init__(name, descr, fields, assembly)
    
    def __str__(self):
        return "Arm64InstructionFormat(%s)" % self.name
