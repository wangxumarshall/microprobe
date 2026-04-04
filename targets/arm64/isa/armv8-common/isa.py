# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""ARM64 ISA implementation."""

from __future__ import absolute_import, print_function

import os
from typing import TYPE_CHECKING, List

from microprobe.code.address import Address, InstructionAddress
from microprobe.code.ins import Instruction
from microprobe.code.var import Variable, VariableArray
from microprobe.exceptions import MicroprobeCodeGenerationError
from microprobe.target.isa import GenericISA
from microprobe.target.isa.register import Register
from microprobe.utils.logger import get_logger

if TYPE_CHECKING:
    from microprobe.code.context import Context

__all__ = ["Arm64ISA"]
LOG = get_logger(__name__)
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_CONDITION_CODES = {
    "=": 0,
    "!=": 1,
    ">=": 10,
    "<": 11,
    ">": 12,
    "<=": 13,
}


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
        
        # Control/system registers should not be eagerly initialized by the
        # generic passes. Keep them out of the regular integer register pool.
        self._control_registers += [
            reg
            for reg in self.registers.values()
            if reg.type.name in {"SystemReg", "SPR", "Condition"}
        ]
        self._flag_registers += [self.registers["NZCV"]]

    def _normalize_register_alias(self, register):
        if not isinstance(register, Register):
            return register

        if register.name == "FP":
            return self.registers["X29"]
        if register.name == "LR":
            return self.registers["X30"]
        if register.name == "WZR":
            return self.registers["XZR"]
        if register.name.startswith("W") and register.name[1:].isdigit():
            return self.registers["X%s" % register.name[1:]]
        if register.name.startswith("D") and register.name[1:].isdigit():
            return self.registers["V%s" % register.name[1:]]
        if register.name.startswith("S") and register.name[1:].isdigit():
            return self.registers["V%s" % register.name[1:]]
        return register

    @property
    def context_var(self):
        if self._context_var is None:
            self._context_var = VariableArray(
                "%s_CONTEXT_VAR" % self._name.upper(), "uint8_t", 1024, align=16
            )
        return self._context_var

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

        register = self._normalize_register_alias(register)
        if isinstance(value, Register):
            value = self._normalize_register_alias(value)

        if register.name == "XZR":
            return []

        current_value = context.get_register_value(register)

        # Check if value is already in a register
        if context.register_has_value(value):
            present_reg = context.registers_get_value(value)[0]
            if present_reg.name != register.name:
                instrs.extend(self._copy_register(register, present_reg))
                return instrs

        # Handle different value types
        if isinstance(value, int):
            instrs.extend(self._set_register_immediate(register, value, context))
        elif isinstance(value, Address):
            instrs.extend(self.set_register_to_address(register, value, context))
        elif isinstance(value, Register):
            instrs.extend(self._copy_register(register, value))
        elif isinstance(value, str) and register.type.name == "SIMD_FP":
            instrs.extend(self._set_vector_register(register, value, context))
        else:
            raise MicroprobeCodeGenerationError(
                f"Unsupported value type for register: {type(value)}"
            )

        if current_value == value and opt:
            return []

        return instrs

    def _copy_register(self, register, value):
        if register.type.name in {"GPR64", "SPR"} and value.type.name in {
            "GPR64",
            "SPR",
        }:
            mov_ins = self.new_instruction("ADD_X_REG_V0")
            mov_ins.operands()[0].set_value(0)
            mov_ins.operands()[1].set_value(value)
            mov_ins.operands()[2].set_value(register)
            return [mov_ins]

        if register.type.name == "GPR32" and value.type.name == "GPR32":
            mov_ins = self.new_instruction("ADD_W_REG_V0")
            mov_ins.operands()[0].set_value(0)
            mov_ins.operands()[1].set_value(value)
            mov_ins.operands()[2].set_value(register)
            return [mov_ins]

        if register.type.name == "SIMD_FP" and value.type.name == "SIMD_FP":
            mov_ins = self.new_instruction("ORR_V_V0")
            mov_ins.operands()[0].set_value(value)
            mov_ins.operands()[1].set_value(value)
            mov_ins.operands()[2].set_value(register)
            return [mov_ins]

        raise MicroprobeCodeGenerationError(
            "Unsupported register copy from '%s' to '%s'"
            % (value.type.name, register.type.name)
        )

    def _set_register_immediate(self, register, value, context):
        """
        Set register to an immediate value.
        
        ARM64 has multiple ways to load immediates:
        - MOVZ/MOVN for small values
        - MOVK for larger values (up to 4 instructions)
        """
        instrs = []

        if register.type.name not in {"GPR64", "GPR32", "SPR"}:
            raise MicroprobeCodeGenerationError(
                "Immediate initialization is only supported for GPR-like registers"
            )

        if register.type.name == "GPR32":
            movz_name = "MOVZ_W_V0"
            movn_name = "MOVN_W_V0"
            movk_name = "MOVK_W_V0"
            value &= 0xFFFFFFFF
        else:
            movz_name = "MOVZ_X_V0"
            movn_name = "MOVN_X_V0"
            movk_name = "MOVK_X_V0"
            value &= 0xFFFFFFFFFFFFFFFF

        if value == 0:
            mov_ins = self.new_instruction(movz_name)
            mov_ins.operands()[0].set_value(0)
            mov_ins.operands()[1].set_value(0)
            mov_ins.operands()[2].set_value(register)
            instrs.append(mov_ins)
        elif -65536 <= value <= 65535:
            # Can use single MOVZ or MOVN
            if value >= 0:
                mov_ins = self.new_instruction(movz_name)
                mov_ins.operands()[0].set_value(0)
                mov_ins.operands()[1].set_value(value)
                mov_ins.operands()[2].set_value(register)
            else:
                # Use MOVN for negative numbers
                mov_ins = self.new_instruction(movn_name)
                mov_ins.operands()[0].set_value(0)
                mov_ins.operands()[1].set_value(~value & 0xFFFF)
                mov_ins.operands()[2].set_value(register)
            instrs.append(mov_ins)
        else:
            # Need multiple MOVK instructions
            # First, use MOVZ for lower 16 bits
            mov_ins = self.new_instruction(movz_name)
            mov_ins.operands()[0].set_value(0)
            mov_ins.operands()[1].set_value(value & 0xFFFF)
            mov_ins.operands()[2].set_value(register)
            instrs.append(mov_ins)

            # Then use MOVK for remaining bits
            for shift in [16, 32, 48]:
                imm = (value >> shift) & 0xFFFF
                if imm != 0:
                    movk_ins = self.new_instruction(movk_name)
                    movk_ins.operands()[0].set_value(shift // 16)
                    movk_ins.operands()[1].set_value(imm)
                    movk_ins.operands()[2].set_value(register)
                    instrs.append(movk_ins)

        return instrs

    def _set_vector_register(self, register, value, context):
        elems = value.split("_", 1)
        if len(elems) != 2:
            raise MicroprobeCodeGenerationError(
                "Unsupported vector initialization format '%s'" % value
            )

        raw_value = int(elems[0], 0)
        elem_size = int(elems[1], 0)
        if elem_size != 64:
            raise MicroprobeCodeGenerationError(
                "Only 64-bit vector element initialization is currently supported"
            )

        scratch = self.scratch_registers[0]
        instrs = self.set_register(scratch, raw_value, context, opt=False)
        dup_ins = self.new_instruction("DUP_V_GPR_V0")
        dup_ins.set_operands([register, scratch])
        instrs.append(dup_ins)
        return instrs

    def get_context(self):
        """
        Get context setup instructions.
        
        For ARM64, no special context setup is needed.
        """
        return []

    def set_context(self, variable=None, tmpl_path=None):
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
        bl_ins.operands()[0].set_value(target, check=False)
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

    def negate_register(self, reg: Register, context: "Context"):
        if reg.type.name == "GPR32":
            instruction = self.new_instruction("SUB_W_REG_V0")
            instruction.operands()[1].set_value(reg)
            instruction.operands()[2].set_value(0)
            instruction.operands()[3].set_value(self.registers["WZR"])
            instruction.operands()[4].set_value(reg)
            return [instruction]

        if reg.type.name in {"GPR64", "SPR"}:
            instruction = self.new_instruction("SUB_X_REG_V0")
            instruction.operands()[1].set_value(reg)
            instruction.operands()[2].set_value(0)
            instruction.operands()[3].set_value(self.registers["XZR"])
            instruction.operands()[4].set_value(reg)
            return [instruction]

        if reg.type.name == "SIMD_FP":
            instruction = self.new_instruction("FNEG_D_V0")
            instruction.operands()[0].set_value(reg)
            instruction.operands()[1].set_value(reg)
            return [instruction]

        raise NotImplementedError

    def load(self, reg: Register, address, context: "Context"):
        if reg.type.name == "GPR32":
            instruction = self.new_instruction("LDR_W_IMM_V0")
        elif reg.type.name in {"GPR64", "SPR"}:
            instruction = self.new_instruction("LDR_X_IMM_V0")
        elif reg.type.name == "SIMD_FP":
            instruction = self.new_instruction("LDR_V_IMM_V0")
        else:
            raise NotImplementedError

        instruction.memory_operands()[0].set_address(address, context)
        instruction.operands()[2].set_value(reg)
        return [instruction]

    def load_float(self, reg: Register, address, context: "Context"):
        return self.load(reg, address, context)

    def store_float(self, reg: Register, address, context: "Context"):
        instruction = self.new_instruction("STR_V_IMM_V0")
        instruction.memory_operands()[0].set_address(address, context)
        instruction.operands()[2].set_value(reg)
        return [instruction]

    def store_integer(
        self, reg: Register, address, length, context: "Context"
    ):
        if length == 32:
            instruction = self.new_instruction("STR_W_IMM_V0")
        elif length == 64:
            instruction = self.new_instruction("STR_X_IMM_V0")
        else:
            raise NotImplementedError

        instruction.memory_operands()[0].set_address(address, context)
        instruction.operands()[2].set_value(reg)
        return [instruction]

    def store_decimal(self, address, length, value, context: "Context"):
        scratch = self.get_register_for_address_arithmetic(context)
        instrs = self.set_register(scratch, value, context)
        instrs.extend(self.store_integer(scratch, address, length, context))
        return instrs

    def set_register_to_address(
        self,
        reg: Register,
        address,
        context: "Context",
        force_absolute: bool = False,
        force_relative: bool = False,
    ):
        if context.register_has_value(address):
            present = context.registers_get_value(address)[0]
            if present.name == reg.name:
                return []
            return self._copy_register(reg, present)

        closest = context.get_closest_address_value(address)
        if closest is not None:
            base_reg, base_address = closest
            displacement = address.displacement - base_address.displacement
            instrs = []
            if base_reg.name != reg.name:
                instrs.extend(self._copy_register(reg, base_reg))
            if displacement != 0:
                instrs.extend(self.add_to_register(reg, displacement))
            return instrs

        if not context.symbolic or force_absolute:
            raise MicroprobeCodeGenerationError(
                "Unable to materialize absolute ARM64 address '%s' without "
                "a base register already present in the context" % address
            )

        basename = address.base_address
        if isinstance(basename, Variable):
            basename = basename.name

        displacement = address.displacement
        expr = str(basename)
        if displacement > 0:
            expr = "%s+0x%X" % (expr, displacement)
        elif displacement < 0:
            expr = "%s-0x%X" % (expr, abs(displacement))

        adrp = self.new_instruction("ADRP_X_V0")
        adrp.operands()[0].set_value(expr, check=False)
        adrp.operands()[1].set_value(reg)

        add = self.new_instruction("ADD_X_IMM_V0")
        add.operands()[1].set_value(":lo12:%s" % expr, check=False)
        add.operands()[2].set_value(reg)
        add.operands()[3].set_value(reg)

        return [adrp, add]

    def set_register_bits(
        self, register, value, mask, shift, context: "Context"
    ):
        current = context.get_register_value(register)
        if current is None or isinstance(current, Address):
            raise MicroprobeCodeGenerationError(
                "Need a concrete integer value in '%s' to update masked bits"
                % register.name
            )

        new_value = (int(current) & ~mask) | ((int(value) << shift) & mask)
        return self.set_register(register, new_value, context, opt=False)

    def add_to_register(self, register: Register, value):
        if not isinstance(value, int):
            raise NotImplementedError

        instrs: List[Instruction] = []
        if register.type.name == "GPR32":
            max_imm = 4095
            add_name = "ADD_W_IMM_V0"
            sub_name = "SUB_W_IMM_V0"
        elif register.type.name in {"GPR64", "SPR"}:
            max_imm = 4095
            add_name = "ADD_X_IMM_V0"
            sub_name = "SUB_X_IMM_V0"
        else:
            raise NotImplementedError

        while value > max_imm:
            ins = self.new_instruction(add_name)
            ins.operands()[1].set_value(max_imm)
            ins.operands()[2].set_value(register)
            ins.operands()[3].set_value(register)
            instrs.append(ins)
            value -= max_imm

        while value < -max_imm:
            ins = self.new_instruction(sub_name)
            ins.operands()[1].set_value(max_imm)
            ins.operands()[2].set_value(register)
            ins.operands()[3].set_value(register)
            instrs.append(ins)
            value += max_imm

        if value > 0:
            ins = self.new_instruction(add_name)
            ins.operands()[1].set_value(value)
            ins.operands()[2].set_value(register)
            ins.operands()[3].set_value(register)
            instrs.append(ins)
        elif value < 0:
            ins = self.new_instruction(sub_name)
            ins.operands()[1].set_value(abs(value))
            ins.operands()[2].set_value(register)
            ins.operands()[3].set_value(register)
            instrs.append(ins)

        return instrs

    def compare_and_branch(self, val1, val2, cond, target, context: "Context"):
        assert cond in ["<", ">", "!=", "=", ">=", "<="]

        instrs: List[Instruction] = []
        scratch_index = 0
        if isinstance(val1, int):
            scratch = self.scratch_registers[scratch_index]
            scratch_index += 1
            instrs.extend(self.set_register(scratch, val1, context, opt=False))
            val1 = scratch
        if isinstance(val2, int):
            scratch = self.scratch_registers[scratch_index]
            instrs.extend(self.set_register(scratch, val2, context, opt=False))
            val2 = scratch

        if isinstance(target, str):
            target = InstructionAddress(base_address=target)

        if cond == "=" and isinstance(val2, Register) and val2.name in {"XZR", "WZR"}:
            instruction = self.new_instruction(
                "CBZ_X_V0" if val1.type.name != "GPR32" else "CBZ_X_V0"
            )
            instruction.operands()[0].set_value(target, check=False)
            instruction.operands()[1].set_value(val1)
            instrs.append(instruction)
            return instrs

        if cond == "!=" and isinstance(val2, Register) and val2.name in {"XZR", "WZR"}:
            instruction = self.new_instruction(
                "CBNZ_X_V0" if val1.type.name != "GPR32" else "CBNZ_X_V0"
            )
            instruction.operands()[0].set_value(target, check=False)
            instruction.operands()[1].set_value(val1)
            instrs.append(instruction)
            return instrs

        if val1.type.name == "GPR32":
            cmp_instruction = self.new_instruction("SUBS_W_REG_V0")
            zero_reg = self.registers["WZR"]
        else:
            cmp_instruction = self.new_instruction("SUBS_X_REG_V0")
            zero_reg = self.registers["XZR"]
        cmp_instruction.operands()[1].set_value(val2)
        cmp_instruction.operands()[2].set_value(0)
        cmp_instruction.operands()[3].set_value(val1)
        cmp_instruction.operands()[4].set_value(zero_reg)
        instrs.append(cmp_instruction)

        branch_instruction = self.new_instruction("B_COND_V0")
        branch_instruction.operands()[0].set_value(target, check=False)
        branch_instruction.operands()[1].set_value(_CONDITION_CODES[cond])
        instrs.append(branch_instruction)
        return instrs

    def nop(self):
        return self.get_nop_instruction()
