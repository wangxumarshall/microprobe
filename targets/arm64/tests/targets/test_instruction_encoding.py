# Copyright 2026
# Licensed under the Apache License, Version 2.0

"""ARM64 instruction encoding validation tests for SDC-sensitive instructions."""

import pytest

from microprobe.target import import_definition

TARGET_NAME = "armv8_common-armv8_common-aarch64_linux_gcc"


@pytest.fixture
def arm64_target():
    return import_definition(TARGET_NAME)


class TestFMAInstructionEncoding:
    """Test encoding of FMA (Fused Multiply-Add) instructions."""

    def test_fmadd_double_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMADD_D_V0")
        assert instr is not None
        assert instr.mnemonic == "FMADD"
        assert instr.format.name == "FP_DP_3REG"

    def test_fmadd_single_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMADD_S_V0")
        assert instr is not None
        assert instr.mnemonic == "FMADD"
        assert instr.format.name == "FP_DP_3REG"

    def test_fmsub_double_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMSUB_D_V0")
        assert instr is not None
        assert instr.mnemonic == "FMSUB"
        assert instr.format.name == "FP_DP_3REG"

    def test_fmsub_single_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMSUB_S_V0")
        assert instr is not None
        assert instr.mnemonic == "FMSUB"
        assert instr.format.name == "FP_DP_3REG"

    def test_fnmadd_double_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FNMADD_D_V0")
        assert instr is not None
        assert instr.mnemonic == "FNMADD"
        assert instr.format.name == "FP_DP_3REG"

    def test_fnmadd_single_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FNMADD_S_V0")
        assert instr is not None
        assert instr.mnemonic == "FNMADD"
        assert instr.format.name == "FP_DP_3REG"

    def test_fnmsub_double_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FNMSUB_D_V0")
        assert instr is not None
        assert instr.mnemonic == "FNMSUB"
        assert instr.format.name == "FP_DP_3REG"

    def test_fnmsub_single_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FNMSUB_S_V0")
        assert instr is not None
        assert instr.mnemonic == "FNMSUB"
        assert instr.format.name == "FP_DP_3REG"


class TestVectorFMAInstructionEncoding:
    """Test encoding of vector FMA instructions."""

    def test_fmla_2s_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMLA_V_2S_V0")
        assert instr is not None
        assert instr.mnemonic == "FMLA"
        assert instr.format.name == "SIMD_DP_3REG"

    def test_fmla_4s_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMLA_V_4S_V0")
        assert instr is not None
        assert instr.mnemonic == "FMLA"
        assert instr.format.name == "SIMD_DP_3REG"

    def test_fmla_2d_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMLA_V_2D_V0")
        assert instr is not None
        assert instr.mnemonic == "FMLA"
        assert instr.format.name == "SIMD_DP_3REG"

    def test_fmls_2s_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMLS_V_2S_V0")
        assert instr is not None
        assert instr.mnemonic == "FMLS"
        assert instr.format.name == "SIMD_DP_3REG"

    def test_fmls_4s_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMLS_V_4S_V0")
        assert instr is not None
        assert instr.mnemonic == "FMLS"
        assert instr.format.name == "SIMD_DP_3REG"

    def test_fmls_2d_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMLS_V_2D_V0")
        assert instr is not None
        assert instr.mnemonic == "FMLS"
        assert instr.format.name == "SIMD_DP_3REG"


class TestLSEAtomicInstructionEncoding:
    """Test encoding of LSE atomic instructions."""

    def test_ldadd_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("LDADD_X_V0")
        assert instr is not None
        assert instr.mnemonic == "LDADD"
        assert instr.format.name == "ATOMIC"

    def test_cas_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("CAS_X_V0")
        assert instr is not None
        assert instr.mnemonic == "CAS"
        assert instr.format.name == "CAS"

    def test_swp_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("SWP_X_V0")
        assert instr is not None
        assert instr.mnemonic == "SWP"
        assert instr.format.name == "ATOMIC"

    def test_ldsmax_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("LDSMAX_X_V0")
        assert instr is not None
        assert instr.mnemonic == "LDSMAX"
        assert instr.format.name == "ATOMIC"

    def test_ldsmin_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("LDSMIN_X_V0")
        assert instr is not None
        assert instr.mnemonic == "LDSMIN"
        assert instr.format.name == "ATOMIC"

    def test_ldumax_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("LDUMAX_X_V0")
        assert instr is not None
        assert instr.mnemonic == "LDUMAX"
        assert instr.format.name == "ATOMIC"

    def test_ldumin_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("LDUMIN_X_V0")
        assert instr is not None
        assert instr.mnemonic == "LDUMIN"
        assert instr.format.name == "ATOMIC"

    def test_ldset_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("LDSET_X_V0")
        assert instr is not None
        assert instr.mnemonic == "LDSET"
        assert instr.format.name == "ATOMIC"

    def test_ldeor_encoding(self, arm64_target):
        instr = arm64_target.isa.instructions.get("LDEOR_X_V0")
        assert instr is not None
        assert instr.mnemonic == "LDEOR"
        assert instr.format.name == "ATOMIC"


class TestPairMemoryInstructionEncoding:
    """Test encoding of pair memory instructions (SDC-sensitive)."""

    def test_ldp_encoding(self, arm64_target):
        ldp_instrs = [
            name for name in arm64_target.isa.instructions.keys()
            if name.startswith("LDP_") and name.endswith("_V0")
        ]
        assert len(ldp_instrs) > 0
        for name in ldp_instrs:
            instr = arm64_target.isa.instructions.get(name)
            assert instr.mnemonic == "LDP"
            assert instr.format.name == "LOAD_STORE_PAIR"

    def test_stp_encoding(self, arm64_target):
        stp_instrs = [
            name for name in arm64_target.isa.instructions.keys()
            if name.startswith("STP_") and name.endswith("_V0")
        ]
        assert len(stp_instrs) > 0
        for name in stp_instrs:
            instr = arm64_target.isa.instructions.get(name)
            assert instr.mnemonic == "STP"
            assert instr.format.name == "LOAD_STORE_PAIR"


class TestInstructionFieldDefinitions:
    """Test that instruction fields are properly defined."""

    def test_fp_dp_3reg_fields(self, arm64_target):
        instr = arm64_target.isa.instructions.get("FMADD_D_V0")
        assert instr is not None
        format_fields = [f.name for f in instr.format.fields]
        assert "type" in format_fields
        assert "o1" in format_fields
        assert "o0" in format_fields
        assert "Vm" in format_fields
        assert "Va" in format_fields
        assert "Vn" in format_fields
        assert "Vd" in format_fields

    def test_atomic_fields(self, arm64_target):
        instr = arm64_target.isa.instructions.get("LDADD_X_V0")
        assert instr is not None
        format_fields = [f.name for f in instr.format.fields]
        assert "size" in format_fields
        assert "V" in format_fields
        assert "A" in format_fields
        assert "R" in format_fields
        assert "opc" in format_fields
