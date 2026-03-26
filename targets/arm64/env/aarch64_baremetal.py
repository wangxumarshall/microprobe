# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Baremetal Environment
"""

from __future__ import absolute_import, print_function

from microprobe.code.address import InstructionAddress
from microprobe.target.env import GenericEnvironment


__all__ = ["aarch64_baremetal"]


class aarch64_baremetal(GenericEnvironment):
    """ARM64 baremetal environment."""
    
    def __init__(self, isa):
        super(aarch64_baremetal, self).__init__(
            "aarch64_baremetal",
            "ARM64 architecture (AArch64), Baremetal",
            isa,
            little_endian=True
        )
        self._default_wrapper = "AsmWrapper"
    
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
        return super(aarch64_baremetal, self).elf_abi(
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
        """Return list of volatile registers."""
        rlist = []
        
        # All registers are volatile in baremetal
        for idx in range(0, 31):
            rlist.append(self.target.registers[f'X{idx}'])
        
        for idx in range(0, 32):
            rlist.append(self.target.registers[f'V{idx}'])
        
        return rlist
