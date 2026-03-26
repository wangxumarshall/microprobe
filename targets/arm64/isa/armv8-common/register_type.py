# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Register Type Implementation
"""

from __future__ import absolute_import, print_function

from microprobe.target.isa.register_type import GenericRegisterType
from microprobe.utils.typeguard_decorator import typeguard_testsuite


@typeguard_testsuite
class Arm64RegisterType(GenericRegisterType):
    """ARM64 Register Type implementation."""
    
    def __init__(self, name, descr, size):
        super(Arm64RegisterType, self).__init__(name, descr, size)
    
    def __str__(self):
        return "Arm64RegisterType(%s)" % self.name
