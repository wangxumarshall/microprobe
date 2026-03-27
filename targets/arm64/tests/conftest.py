from pathlib import Path
import sys

import pytest


PROJECT_MICROPROBE_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = PROJECT_MICROPROBE_ROOT.parent
PROJECT_MICROPROBE_SRC = PROJECT_MICROPROBE_ROOT / "src"
TARGETS_ROOT = PROJECT_MICROPROBE_ROOT / "targets"

for extra_path in [PROJECT_MICROPROBE_SRC, PROJECT_ROOT]:
    if str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))

from microprobe import MICROPROBE_RC  # noqa: E402

for key in [
    "default_paths",
    "architecture_paths",
    "microarchitecture_paths",
    "environment_paths",
    "wrapper_paths",
]:
    if str(TARGETS_ROOT) not in MICROPROBE_RC[key]:
        MICROPROBE_RC[key].append(str(TARGETS_ROOT))

from microprobe.code import get_wrapper  # noqa: E402
from microprobe.target import import_definition  # noqa: E402


TARGET_NAME = "armv8_common-armv8_common-aarch64_linux_gcc"
LEGACY_TARGET_NAME = "armv8-common-cortex-a53-aarch64_linux_gcc"


@pytest.fixture(scope="session")
def arm64_target():
    return import_definition(TARGET_NAME)


@pytest.fixture(scope="session")
def legacy_arm64_target():
    return import_definition(LEGACY_TARGET_NAME)


@pytest.fixture(scope="session")
def arm64asm_wrapper_cls():
    return get_wrapper("Arm64AsmWrapper")


@pytest.fixture(scope="session")
def baremetal_diff_wrapper_cls():
    return get_wrapper("BareMetalDiffWrapper")
