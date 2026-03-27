from microprobe.utils.policy import find_policy


TARGET_NAME = "armv8_common-armv8_common-aarch64_linux_gcc"
LEGACY_TARGET_NAME = "armv8-common-cortex-a53-aarch64_linux_gcc"


def test_canonical_arm64_target_imports(arm64_target):
    assert arm64_target.name == TARGET_NAME
    assert arm64_target.environment.name == "aarch64_linux_gcc"


def test_legacy_alias_still_imports_same_target(arm64_target, legacy_arm64_target):
    assert legacy_arm64_target.name == arm64_target.name
    assert legacy_arm64_target.environment.name == arm64_target.environment.name


def test_arm64_wrappers_are_registered(arm64asm_wrapper_cls, baremetal_diff_wrapper_cls):
    assert arm64asm_wrapper_cls.__name__ == "Arm64AsmWrapper"
    assert baremetal_diff_wrapper_cls.__name__ == "BareMetalDiffWrapper"


def test_arm64_target_exposes_expected_registers_and_instructions(arm64_target):
    for register_name in ["X0", "X30", "SP", "LR", "V0", "NZCV"]:
        assert register_name in arm64_target.isa.registers

    for instruction_name in [
        "ADD_X_IMM_V0",
        "LDR_X_IMM_V0",
        "FMADD_D_V0",
        "LDP_X_V0",
        "CASAL_X_V0",
        "RET_V0",
    ]:
        assert instruction_name in arm64_target.isa.instructions


def test_arm64_environment_prefers_differential_wrapper(arm64_target):
    assert arm64_target.environment.preferred_diff_wrapper == "BareMetalDiffWrapper"


def test_sdc_fuzzing_policy_synthesizes_static_scores(arm64_target, arm64asm_wrapper_cls):
    wrapper = arm64asm_wrapper_cls()
    policy = find_policy(TARGET_NAME, "sdc_fuzzing")

    synth = policy.apply(
        arm64_target,
        wrapper,
        benchmark_size=8,
        sequence_length=4,
        dependency_distance=1,
        memory_stream_stride=8192,
    )
    benchmark = synth.synthesize()

    assert benchmark.metadata["ace_score"] >= 0.0
    assert benchmark.metadata["ibr_score"] >= 0.0
    assert benchmark.metadata["memory_pressure_score"] >= 0.0
    assert benchmark.metadata["preferred_stride_bytes"] == 8192
    assert len(benchmark.cfg.bbls) == 1


def test_baremetal_diff_wrapper_can_wrap_generated_benchmark(
    arm64_target, baremetal_diff_wrapper_cls
):
    wrapper = baremetal_diff_wrapper_cls()
    policy = find_policy(LEGACY_TARGET_NAME, "sdc_fuzzing")

    synth = policy.apply(
        arm64_target,
        wrapper,
        benchmark_size=8,
        sequence_length=4,
        dependency_distance=1,
        memory_stream_stride=8192,
    )
    benchmark = synth.synthesize()
    rendered = "".join(str(elem) for elem in synth._wrap(benchmark))

    assert "SDC_DIGEST=" in rendered
    assert "sdc_benchmark_body" in rendered
