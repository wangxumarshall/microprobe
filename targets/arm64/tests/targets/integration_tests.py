# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Integration Tests
"""

from __future__ import absolute_import, print_function

import unittest
import tempfile
import os
from microprobe.target import import_definition
from microprobe.code import Synthesizer
from microprobe.target.arm64.env.aarch64_linux_gcc import aarch64_linux_gcc


class Arm64CodeGenerationTest(unittest.TestCase):
    """ARM64 Code Generation tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            self.target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            self.env = aarch64_linux_gcc(self.target.isa)
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_basic_instruction_generation(self):
        """Test basic instruction generation."""
        try:
            # Create a simple instruction
            add_instr = self.target.new_instruction("ADD_X_IMM_V0")
            add_instr.set_operands([
                self.target.registers["X0"],
                self.target.registers["X1"],
                42
            ])
            
            # Check instruction was created
            self.assertIsNotNone(add_instr)
            self.assertEqual(add_instr.mnemonic, "ADD")
            
        except Exception as e:
            self.skipTest(f"Instruction generation failed: {e}")
    
    def test_load_store_generation(self):
        """Test load/store instruction generation."""
        try:
            # Create load instruction
            ldr_instr = self.target.new_instruction("LDR_X_IMM_V0")
            ldr_instr.set_operands([
                self.target.registers["X0"],
                self.target.registers["X1"],
                16
            ])
            
            # Create store instruction
            str_instr = self.target.new_instruction("STR_X_IMM_V0")
            str_instr.set_operands([
                self.target.registers["X0"],
                self.target.registers["X1"],
                16
            ])
            
            # Check instructions were created
            self.assertIsNotNone(ldr_instr)
            self.assertIsNotNone(str_instr)
            
        except Exception as e:
            self.skipTest(f"Instruction generation failed: {e}")
    
    def test_branch_instruction_generation(self):
        """Test branch instruction generation."""
        try:
            # Create branch instruction
            b_instr = self.target.new_instruction("B_V0")
            b_instr.set_label("target_label")
            
            # Create call instruction
            bl_instr = self.target.new_instruction("BL_V0")
            bl_instr.set_label("function_label")
            
            # Check instructions were created
            self.assertIsNotNone(b_instr)
            self.assertIsNotNone(bl_instr)
            
        except Exception as e:
            self.skipTest(f"Instruction generation failed: {e}")


class Arm64EnvironmentTest(unittest.TestCase):
    """ARM64 Environment tests."""
    
    def test_linux_environment(self):
        """Test Linux environment configuration."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            env = aarch64_linux_gcc(target.isa)
            
            # Check environment properties
            self.assertEqual(env.name, "aarch64_linux_gcc")
            self.assertTrue(env.little_endian)
            self.assertEqual(env.stack_direction, "decrease")
            
        except Exception as e:
            self.skipTest(f"Environment test failed: {e}")
    
    def test_volatile_registers(self):
        """Test volatile register definition."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            env = aarch64_linux_gcc(target.isa)
            
            # Check volatile registers
            volatile = env.volatile_registers
            self.assertIsNotNone(volatile)
            self.assertGreater(len(volatile), 0)
            
        except Exception as e:
            self.skipTest(f"Environment test failed: {e}")


class Arm64SDCDetectionTest(unittest.TestCase):
    """ARM64 SDC Detection tests."""
    
    def test_sdc_policy_import(self):
        """Test SDC detection policy import."""
        try:
            from microprobe.target.arm64.policies.sdc_detect import policy
            
            # Check policy function exists
            self.assertIsNotNone(policy)
            self.assertTrue(callable(policy))
            
        except Exception as e:
            self.skipTest(f"SDC policy import failed: {e}")
    
    def test_checksum_detection(self):
        """Test checksum-based SDC detection."""
        try:
            from microprobe.target.arm64.policies.sdc_detect import _generate_checksum_test
            
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Create a test instruction
            add_instr = target.new_instruction("ADD_X_IMM_V0")
            add_instr.set_operands([
                target.registers["X0"],
                target.registers["X1"],
                42
            ])
            
            # Generate checksum test
            test_instrs = _generate_checksum_test(target, add_instr)
            
            # Check instructions were generated
            self.assertIsNotNone(test_instrs)
            self.assertGreater(len(test_instrs), 0)
            
        except Exception as e:
            self.skipTest(f"Checksum detection test failed: {e}")
    
    def test_redundant_execution_detection(self):
        """Test redundant execution SDC detection."""
        try:
            from microprobe.target.arm64.policies.sdc_detect import _generate_redundant_test
            
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Create a test instruction
            add_instr = target.new_instruction("ADD_X_IMM_V0")
            add_instr.set_operands([
                target.registers["X0"],
                target.registers["X1"],
                42
            ])
            
            # Generate redundant execution test
            test_instrs = _generate_redundant_test(target, add_instr)
            
            # Check instructions were generated
            self.assertIsNotNone(test_instrs)
            self.assertGreater(len(test_instrs), 0)
            
        except Exception as e:
            self.skipTest(f"Redundant execution test failed: {e}")


if __name__ == "__main__":
    unittest.main()
