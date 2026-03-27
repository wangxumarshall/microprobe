# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""Passes for static SDC-oriented coverage analysis."""

from microprobe.passes.sdc_analysis.offline_coverage import (
    CapstoneValidationPass,
    Kunpeng920MemoryPressurePass,
    StaticACECalculatorPass,
    StaticIBRCoveragePass,
)

__all__ = [
    "StaticACECalculatorPass",
    "StaticIBRCoveragePass",
    "Kunpeng920MemoryPressurePass",
    "CapstoneValidationPass",
]
