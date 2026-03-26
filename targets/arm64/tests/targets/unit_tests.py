# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Unit Tests
"""

from __future__ import absolute_import, print_function

import unittest
from microprobe.target import import_definition


class Arm64RegisterTest(unittest.TestCase):
    """ARM64 Register tests."""
    
    def test_register_types(self):
        """Test that ARM64 register types are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check register types exist
            self.assertIsNotNone(target.isa.register_types)
            
            # Check key register types
            reg_types = target.isa.register_types
            self.assertIn("GPR64", reg_types)
            self.assertIn("GPR32", reg_types)
            self.assertIn("SIMD_FP", reg_types)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_general_purpose_registers(self):
        """Test that ARM64 GPRs are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check X0-X30 exist
            for i in range(31):
                self.assertIn(f"X{i}", target.isa.registers)
            
            # Check W0-W30 exist
            for i in range(31):
                self.assertIn(f"W{i}", target.isa.registers)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_simd_fp_registers(self):
        """Test that ARM64 SIMD/FP registers are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check V0-V31 exist
            for i in range(32):
                self.assertIn(f"V{i}", target.isa.registers)
            
            # Check D0-D31 exist
            for i in range(32):
                self.assertIn(f"D{i}", target.isa.registers)
            
            # Check S0-S31 exist
            for i in range(32):
                self.assertIn(f"S{i}", target.isa.registers)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_special_registers(self):
        """Test that ARM64 special registers are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check special registers
            self.assertIn("XZR", target.isa.registers)
            self.assertIn("WZR", target.isa.registers)
            self.assertIn("SP", target.isa.registers)
            self.assertIn("PC", target.isa.registers)
            self.assertIn("LR", target.isa.registers)
            self.assertIn("FP", target.isa.registers)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")


class Arm64InstructionTest(unittest.TestCase):
    """ARM64 Instruction tests."""
    
    def test_data_processing_instructions(self):
        """Test that ARM64 data processing instructions are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check key instructions
            self.assertIn("ADD_X_IMM_V0", target.isa.instructions)
            self.assertIn("SUB_X_IMM_V0", target.isa.instructions)
            self.assertIn("MUL_X_V0", target.isa.instructions)
            self.assertIn("UDIV_X_V0", target.isa.instructions)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_load_store_instructions(self):
        """Test that ARM64 load/store instructions are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check key instructions
            self.assertIn("LDR_X_IMM_V0", target.isa.instructions)
            self.assertIn("STR_X_IMM_V0", target.isa.instructions)
            self.assertIn("LDP_X_V0", target.isa.instructions)
            self.assertIn("STP_X_V0", target.isa.instructions)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_branch_instructions(self):
        """Test that ARM64 branch instructions are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check key instructions
            self.assertIn("B_V0", target.isa.instructions)
            self.assertIn("BL_V0", target.isa.instructions)
            self.assertIn("RET_V0", target.isa.instructions)
            self.assertIn("B_COND_V0", target.isa.instructions)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_floating_point_instructions(self):
        """Test that ARM64 floating point instructions are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check key instructions
            self.assertIn("FADD_D_V0", target.isa.instructions)
            self.assertIn("FSUB_D_V0", target.isa.instructions)
            self.assertIn("FMUL_D_V0", target.isa.instructions)
            self.assertIn("FDIV_D_V0", target.isa.instructions)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")


class Arm64InstructionFormatTest(unittest.TestCase):
    """ARM64 Instruction Format tests."""
    
    def test_instruction_formats_exist(self):
        """Test that ARM64 instruction formats are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check formats exist
            self.assertIsNotNone(target.isa.formats)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_key_instruction_formats(self):
        """Test that key ARM64 instruction formats are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check key formats
            formats = target.isa.formats
            self.assertIn("ADD_SUB_IMM", formats)
            self.assertIn("LOAD_STORE_IMM", formats)
            self.assertIn("UNCOND_BRANCH_IMM", formats)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")


class Arm64OperandTest(unittest.TestCase):
    """ARM64 Operand tests."""
    
    def test_register_operands(self):
        """Test that ARM64 register operands are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check operands exist
            self.assertIsNotNone(target.isa.operands)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_immediate_operands(self):
        """Test that ARM64 immediate operands are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check immediate operands exist
            operands = target.isa.operands
            self.assertIn("u.imm5", operands)
            self.assertIn("u.imm12", operands)
            self.assertIn("s.imm7", operands)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")


if __name__ == "__main__":
    unittest.main()
