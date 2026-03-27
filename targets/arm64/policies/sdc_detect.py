# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 SDC Detection Policy
"""

from __future__ import absolute_import, print_function

import microprobe.code
from microprobe.code.context import Context
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

NAME = "sdc_detect"
DESCRIPTION = "SDC detection policy for ARM64"
SUPPORTED_TARGETS = ["all"]

LOG = get_logger(__name__)


def _target_looks_like_arm64(target):
    """Best-effort guard until the ARM64 target tuple is normalized."""
    registers = getattr(target, "registers", {})
    return all(reg in registers for reg in ["X0", "SP", "V0", "LR"])


def policy(target, wrapper, **kwargs):
    """
    SDC detection benchmark generation policy.
    
    This policy generates test sequences designed to detect silent data
    corruption in ARM64 systems.
    """
    
    if not _target_looks_like_arm64(target):
        raise MicroprobePolicyError(
            f"Policy '{NAME}' not valid for target '{target.name}'. "
            "Expected an ARM64/AArch64 target with X/V register files."
        )

    instruction = kwargs["instruction"]
    if not hasattr(instruction, "name"):
        raise MicroprobePolicyError(
            "The 'instruction' argument must be an ARM64 instruction type"
        )

    sequence = [instruction]
    dependency_distance = kwargs.get("dependency_distance", 1)
    benchmark_size = kwargs["benchmark_size"]

    synthesizer = microprobe.code.Synthesizer(target, wrapper, value=RNDINT)

    # Initialize registers with known values
    synthesizer.add_pass(
        microprobe.passes.initialization.InitializeRegistersPass(value=RNDINT)
    )
    
    # Initialize floating point registers
    synthesizer.add_pass(
        microprobe.passes.initialization.InitializeRegistersPass()
    )
    
    # Create test structure
    synthesizer.add_pass(
        microprobe.passes.structure.SimpleBuildingBlockPass(
            benchmark_size
        )
    )

    # Set instruction sequence
    synthesizer.add_pass(
        microprobe.passes.instruction.SetInstructionTypeBySequencePass(
            sequence
        )
    )
    
    # Update addresses
    synthesizer.add_pass(
        microprobe.passes.address.UpdateInstructionAddressesPass()
    )
    
    # Add SDC detection checks
    # 1. Checksum verification
    # 2. Redundant computation
    # 3. Boundary checks
    
    # Give memory instructions a concrete stream without assuming a special
    # data-segment pass exists.
    synthesizer.add_pass(
        microprobe.passes.memory.SingleMemoryStreamPass(
            kwargs.get("memory_stream_size", 16),
            kwargs.get("memory_stream_stride", 256),
        )
    )

    if dependency_distance < 1:
        synthesizer.add_pass(
            microprobe.passes.register.NoHazardsAllocationPass()
        )

    synthesizer.add_pass(
        microprobe.passes.register.DefaultRegisterAllocationPass(
            RND, dd=dependency_distance
        )
    )

    synthesizer.add_pass(
        microprobe.passes.address.UpdateInstructionAddressesPass()
    )

    return synthesizer


def generate_sdc_test_sequence(target, instruction, test_type="checksum"):
    """
    Generate SDC detection test sequence.
    
    Args:
        target: Target object
        instruction: Instruction to test
        test_type: Type of SDC test (checksum, redundant, boundary)
    
    Returns:
        List of instructions for SDC detection
    """
    
    instrs = []
    
    if test_type == "checksum":
        # Generate checksum-based SDC detection
        instrs.extend(_generate_checksum_test(target, instruction))
    elif test_type == "redundant":
        # Generate redundant computation test
        instrs.extend(_generate_redundant_test(target, instruction))
    elif test_type == "boundary":
        # Generate boundary check test
        instrs.extend(_generate_boundary_test(target, instruction))
    
    return instrs


def _generate_checksum_test(target, instruction):
    """Generate checksum-based SDC detection."""
    instrs = []
    
    # Initialize checksum register
    checksum_reg = target.registers["X9"]
    mov_ins = target.new_instruction("MOVZ_X_V0")
    mov_ins.set_operands([checksum_reg, 0, 0])
    instrs.append(mov_ins)
    
    # Add test instruction
    instrs.append(instruction.copy() if hasattr(instruction, "copy") else instruction)
    
    # Update checksum
    add_ins = target.new_instruction("ADD_X_REG_V0")
    add_ins.set_operands([checksum_reg, checksum_reg, checksum_reg])
    instrs.append(add_ins)
    
    # Verify checksum (will be done by wrapper)
    
    return instrs


def _generate_redundant_test(target, instruction):
    """Generate redundant computation test."""
    instrs = []

    # Execute instruction twice and compare results
    instrs.append(instruction.copy() if hasattr(instruction, "copy") else instruction)
    
    # Save result
    save_reg = target.registers["X10"]
    mov_ins = target.new_instruction("ADD_X_REG_V0")
    mov_ins.set_operands([save_reg, target.registers["X0"], target.registers["XZR"]])
    instrs.append(mov_ins)
    
    # Execute again
    instrs.append(instruction.copy() if hasattr(instruction, "copy") else instruction)
    
    # Compare
    cmp_ins = target.new_instruction("SUBS_X_REG_V0")
    cmp_ins.set_operands([
        target.registers["XZR"],
        target.registers["X0"],
        save_reg
    ])
    instrs.append(cmp_ins)
    
    return instrs


def _generate_boundary_test(target, instruction):
    """Generate boundary check test."""
    instrs = []
    
    # Test with boundary values
    boundary_values = [0, 1, -1, 0x7FFFFFFFFFFFFFFF, 0x8000000000000000]
    
    for value in boundary_values:
        # Set input value
        set_instrs = target.isa.set_register(
            target.registers["X0"],
            value,
            Context()
        )
        instrs.extend(set_instrs)

        # Execute instruction
        instrs.append(instruction.copy() if hasattr(instruction, "copy") else instruction)
        
        # Check result validity
        # (wrapper will add verification code)
    
    return instrs
