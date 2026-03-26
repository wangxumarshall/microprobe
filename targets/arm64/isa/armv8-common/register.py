# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Register Implementation
"""

from __future__ import absolute_import, print_function

from microprobe.target.isa.register import GenericRegister
from microprobe.utils.typeguard_decorator import typeguard_testsuite


@typeguard_testsuite
class Arm64Register(GenericRegister):
    """ARM64 Register implementation."""
    
    def __init__(self, name, descr, rtype, repr_val, codif):
        super(Arm64Register, self).__init__(
            name, descr, rtype, repr_val, codif
        )
    
    def __str__(self):
        return "Arm64Register(%s)" % self.name
    
    def __repr__(self):
        return "Arm64Register(%s)" % self.name
