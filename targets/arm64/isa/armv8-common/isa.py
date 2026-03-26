# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 ISA Implementation
"""

from __future__ import absolute_import, print_function

import os
from microprobe.code.address import Address, InstructionAddress
from microprobe.code.ins import Instruction
from microprobe.code.var import Variable, VariableArray
from microprobe.exceptions import MicroprobeCodeGenerationError
from microprobe.target.isa import GenericISA
from microprobe.target.isa.register import Register
from microprobe.utils.logger import get_logger

__all__ = ["Arm64ISA"]
LOG = get_logger(__name__)
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class Arm64ISA(GenericISA):
    """ARM64 (AArch64) Instruction Set Architecture."""
    
    def __init__(self, name, descr, path, ins, regs, comparators, generators):
        super(Arm64ISA, self).__init__(
            name, descr, path, ins, regs, comparators, generators
        )
        
        # Scratch registers for code generation
        # ARM64 calling convention: X0-X7 are arguments, X8-X18 are temp
        self._scratch_registers += [
            self.registers["X9"],
            self.registers["X10"],
            self.registers["X11"],
            self.registers["X12"],
            self.registers["X13"],
            self.registers["X14"],
            self.registers["X15"],
            self.registers["X16"],
            self.registers["X17"],
            self.registers["X18"],
            # SIMD/FP scratch registers
            self.registers["V16"],
            self.registers["V17"],
            self.registers["V18"],
            self.registers["V19"],
            self.registers["V20"],
            self.registers["V21"],
            self.registers["V22"],
            self.registers["V23"],
            self.registers["V24"],
            self.registers["V25"],
            self.registers["V26"],
            self.registers["V27"],
            self.registers["V28"],
            self.registers["V29"],
            self.registers["V30"],
            self.registers["V31"],
        ]
        
        # Control registers
        self._control_registers += [
            self.registers["NZCV"],
            self.registers["FPCR"],
            self.registers["FPSR"],
            self.registers["SP"],
            self.registers["PC"],
        ]
    
    def set_register(self, register, value, context, opt=True):
        """
        Set a register to a specific value.
        
        Args:
            register: Target register
            value: Value to set (int, Address, or Register)
            context: Execution context
            opt: Enable optimization
        
        Returns:
            List of instructions to set the register
        """
        LOG.debug("Setting '%s' to value '%s'", register, value)
        instrs = []
        
        current_value = context.get_register_value(register)
        
        # Check if value is already in a register
        if context.register_has_value(value):
            present_reg = context.registers_get_value(value)[0]
            if present_reg.name != register.name:
                # Use MOV instruction
                mov_ins = self.new_instruction("MOV_X_V0")
                mov_ins.set_operands([register, present_reg])
                instrs.append(mov_ins)
                return instrs
        
        # Handle different value types
        if isinstance(value, int):
            instrs.extend(self._set_register_immediate(register, value))
        elif isinstance(value, Address):
            instrs.extend(self._set_register_address(register, value))
        elif isinstance(value, Register):
            # Copy from another register
            mov_ins = self.new_instruction("MOV_X_V0")
            mov_ins.set_operands([register, value])
            instrs.append(mov_ins)
        else:
            raise MicroprobeCodeGenerationError(
                f"Unsupported value type for register: {type(value)}"
            )
        
        return instrs
    
    def _set_register_immediate(self, register, value):
        """
        Set register to an immediate value.
        
        ARM64 has multiple ways to load immediates:
        - MOVZ/MOVN for small values
        - MOVK for larger values (up to 4 instructions)
        """
        instrs = []
        
        if value == 0:
            # Use MOV to zero register (XZR)
            mov_ins = self.new_instruction("MOV_X_V0")
            mov_ins.set_operands([register, self.registers["XZR"]])
            instrs.append(mov_ins)
        
        elif -65536 <= value <= 65535:
            # Can use single MOVZ or MOVN
            if value >= 0:
                mov_ins = self.new_instruction("MOVZ_X_V0")
                mov_ins.set_operands([register, value, 0])
            else:
                # Use MOVN for negative numbers
                mov_ins = self.new_instruction("MOVN_X_V0")
                mov_ins.set_operands([register, ~value & 0xFFFF, 0])
            instrs.append(mov_ins)
        
        else:
            # Need multiple MOVK instructions
            # First, use MOVZ for lower 16 bits
            mov_ins = self.new_instruction("MOVZ_X_V0")
            mov_ins.set_operands([register, value & 0xFFFF, 0])
            instrs.append(mov_ins)
            
            # Then use MOVK for remaining bits
            for shift in [16, 32, 48]:
                imm = (value >> shift) & 0xFFFF
                if imm != 0:
                    movk_ins = self.new_instruction("MOVK_X_V0")
                    movk_ins.set_operands([register, imm, shift // 16])
                    instrs.append(movk_ins)
        
        return instrs
    
    def _set_register_address(self, register, address):
        """
        Set register to an address.
        
        Uses ADRP + ADD for PC-relative addressing.
        """
        instrs = []
        
        # ADRP instruction (will be resolved later)
        adrp_ins = self.new_instruction("ADRP_X_V0")
        adrp_ins.set_operands([register, address])
        instrs.append(adrp_ins)
        
        # ADD instruction for page offset
        add_ins = self.new_instruction("ADD_X_IMM_V0")
        add_ins.set_operands([register, register, address])
        instrs.append(add_ins)
        
        return instrs
    
    def get_context(self):
        """
        Get context setup instructions.
        
        For ARM64, no special context setup is needed.
        """
        return []
    
    @property
    def little_endian(self):
        """ARM64 is little-endian by default."""
        return True
    
    def get_branch_instruction(self, target):
        """
        Get a branch instruction to the target.
        
        Args:
            target: Branch target (Address or str)
        
        Returns:
            Branch instruction
        """
        if isinstance(target, str):
            target = InstructionAddress(base_address=target)
        
        bl_ins = self.new_instruction("BL_V0")
        bl_ins.set_operands([target])
        return bl_ins
    
    def get_return_instruction(self):
        """
        Get a return instruction.
        
        Returns:
            RET instruction
        """
        ret_ins = self.new_instruction("RET_V0")
        ret_ins.set_operands([self.registers["LR"]])
        return ret_ins
    
    def get_nop_instruction(self):
        """
        Get a NOP instruction.
        
        Returns:
            NOP instruction
        """
        # ARM64 NOP is encoded as HINT #0
        nop_ins = self.new_instruction("NOP_V0")
        return nop_ins
