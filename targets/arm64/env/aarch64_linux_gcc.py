# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Linux Environment
"""

from __future__ import absolute_import, print_function

from microprobe.code.address import InstructionAddress
from microprobe.target.env import GenericEnvironment


__all__ = ["aarch64_linux_gcc"]


class aarch64_linux_gcc(GenericEnvironment):
    """ARM64 Linux environment with GCC."""

    DEFAULT_WRAPPER = "CWrapper"
    DIFF_WRAPPER = "BareMetalDiffWrapper"

    def __init__(self, isa):
        super(aarch64_linux_gcc, self).__init__(
            "aarch64_linux_gcc",
            "ARM64 architecture (AArch64), Linux OS, GCC compiler",
            isa,
            little_endian=True
        )
        # Keep the default path on the generic C wrapper until the dedicated
        # differential wrapper lands in-tree.
        self._default_wrapper = self.DEFAULT_WRAPPER
    
    @property
    def stack_pointer(self):
        """Stack pointer register."""
        return self.isa.registers["SP"]
    
    @property
    def stack_direction(self):
        """Stack grows downward."""
        return "decrease"
    
    def elf_abi(self, stack_size, start_symbol, **kwargs):
        """ELF ABI configuration."""
        return super(aarch64_linux_gcc, self).elf_abi(
            stack_size,
            start_symbol,
            stack_alignment=16,
            **kwargs
        )
    
    def function_call(self, target, return_address_reg=None, long_jump=False):
        """Generate function call instructions."""
        if return_address_reg is None:
            return_address_reg = self.target.isa.registers["LR"]
        
        if isinstance(target, str):
            target = InstructionAddress(base_address=target)
        
        bl_ins = self.target.new_instruction("BL_V0")
        bl_ins.set_operands([target])
        
        return [bl_ins]
    
    def function_return(self, return_address_reg=None):
        """Generate function return instructions."""
        if return_address_reg is None:
            return_address_reg = self.target.isa.registers["LR"]
        
        ret_ins = self.target.new_instruction("RET_V0")
        ret_ins.set_operands([return_address_reg])
        
        return [ret_ins]
    
    @property
    def volatile_registers(self):
        """Return list of volatile (caller-saved) registers."""
        rlist = []
        
        # Volatile GPRs: X0-X18
        for idx in range(0, 19):
            rlist.append(self.target.registers[f'X{idx}'])
        
        # Volatile SIMD/FP: V0-V7, V16-V31
        for idx in list(range(0, 8)) + list(range(16, 32)):
            rlist.append(self.target.registers[f'V{idx}'])

        return rlist

    @property
    def preferred_diff_wrapper(self):
        """Dedicated wrapper name to use for SDC differential runs."""
        return self.DIFF_WRAPPER
