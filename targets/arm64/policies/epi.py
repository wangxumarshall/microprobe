# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 EPI Policy
"""

from __future__ import absolute_import, print_function

import microprobe.code
import microprobe.passes.address
import microprobe.passes.branch
import microprobe.passes.initialization
import microprobe.passes.instruction
import microprobe.passes.memory
import microprobe.passes.register
import microprobe.passes.structure
from microprobe.exceptions import MicroprobePolicyError
from microprobe.utils.logger import get_logger
from microprobe.utils.misc import RND, RNDINT

__all__ = ["NAME", "DESCRIPTION", "SUPPORTED_TARGETS", "policy"]

NAME = "epi"
DESCRIPTION = "EPI generation policy for ARM64"
SUPPORTED_TARGETS = ["armv8-common-cortex-a53-aarch64_linux_gcc"]

LOG = get_logger(__name__)


def policy(target, wrapper, **kwargs):
    """EPI generation policy for ARM64."""
    
    if target.name not in SUPPORTED_TARGETS:
        raise MicroprobePolicyError(
            f"Policy '{NAME}' not valid for target '{target.name}'. "
            f"Supported targets: {','.join(SUPPORTED_TARGETS)}"
        )
    
    instr = kwargs["instruction"]
    sequence = [kwargs["instruction"]]
    
    synthesizer = microprobe.code.Synthesizer(target, wrapper, value=RNDINT)
    
    synthesizer.add_pass(
        microprobe.passes.initialization.InitializeRegistersPass(value=RNDINT)
    )
    
    synthesizer.add_pass(
        microprobe.passes.structure.SimpleBuildingBlockPass(
            kwargs["benchmark_size"]
        )
    )
    
    synthesizer.add_pass(
        microprobe.passes.instruction.SetInstructionTypeBySequencePass(
            sequence
        )
    )
    
    synthesizer.add_pass(
        microprobe.passes.address.UpdateInstructionAddressesPass()
    )
    
    synthesizer.add_pass(microprobe.passes.branch.BranchNextPass())
    
    synthesizer.add_pass(
        microprobe.passes.memory.SingleMemoryStreamPass(16, 256)
    )
    
    if kwargs["dependency_distance"] < 1:
        synthesizer.add_pass(
            microprobe.passes.register.NoHazardsAllocationPass()
        )
    
    synthesizer.add_pass(
        microprobe.passes.register.DefaultRegisterAllocationPass(
            RND, dd=kwargs["dependency_distance"]
        )
    )
    
    synthesizer.add_pass(
        microprobe.passes.address.UpdateInstructionAddressesPass()
    )
    
    return synthesizer
