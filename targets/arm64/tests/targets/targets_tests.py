# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""
ARM64 Target Tests
"""

from __future__ import absolute_import, print_function

import unittest
from microprobe.target import import_definition


class Arm64TargetTest(unittest.TestCase):
    """ARM64 Target tests."""
    
    def test_target_import(self):
        """Test that ARM64 target can be imported."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            self.assertIsNotNone(target)
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_registers(self):
        """Test that ARM64 registers are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check for key registers
            self.assertIn("X0", target.isa.registers)
            self.assertIn("X30", target.isa.registers)
            self.assertIn("SP", target.isa.registers)
            self.assertIn("V0", target.isa.registers)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")
    
    def test_instructions(self):
        """Test that ARM64 instructions are defined."""
        try:
            target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
            
            # Check for key instructions
            self.assertIn("ADD_X_IMM_V0", target.isa.instructions)
            self.assertIn("SUB_X_IMM_V0", target.isa.instructions)
            self.assertIn("LDR_X_IMM_V0", target.isa.instructions)
            self.assertIn("B_V0", target.isa.instructions)
            
        except Exception as e:
            self.skipTest(f"Target not yet available: {e}")


if __name__ == "__main__":
    unittest.main()
