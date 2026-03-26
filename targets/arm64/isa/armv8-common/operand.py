# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Operand Implementation
"""

from __future__ import absolute_import, print_function

from microprobe.target.isa.operand import (
    Operand,
    OperandReg,
    OperandImmRange,
    OperandValueSet,
    OperandConst,
)
from microprobe.utils.typeguard_decorator import typeguard_testsuite


@typeguard_testsuite
class Arm64OperandReg(OperandReg):
    """ARM64 Register Operand implementation."""
    
    def __init__(self, name, descr, regs, **kwargs):
        super(Arm64OperandReg, self).__init__(name, descr, regs, **kwargs)
    
    def __str__(self):
        return "Arm64OperandReg(%s)" % self.name


@typeguard_testsuite
class Arm64OperandImmRange(OperandImmRange):
    """ARM64 Immediate Range Operand implementation."""
    
    def __init__(self, name, descr, min_val, max_val, **kwargs):
        super(Arm64OperandImmRange, self).__init__(
            name, descr, min_val, max_val, **kwargs
        )
    
    def __str__(self):
        return "Arm64OperandImmRange(%s)" % self.name


@typeguard_testsuite
class Arm64OperandValueSet(OperandValueSet):
    """ARM64 Value Set Operand implementation."""
    
    def __init__(self, name, descr, values):
        super(Arm64OperandValueSet, self).__init__(name, descr, values)
    
    def __str__(self):
        return "Arm64OperandValueSet(%s)" % self.name
