import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[4]
    / "targets"
    / "generic"
    / "tools"
    / "mp_sdc_offline_gen.py"
)
SPEC = importlib.util.spec_from_file_location("mp_sdc_offline_gen", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
mp_sdc_offline_gen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mp_sdc_offline_gen)


def test_generate_one_with_diff_wrapper_persists_source_metadata(tmp_path):
    task = {
        "target": "armv8_common-armv8_common-aarch64_linux_gcc",
        "policy": "sdc_fuzzing",
        "wrapper": "BareMetalDiffWrapper",
        "sequence_length": 4,
        "benchmark_size": 32,
        "dependency_distance": 1,
        "memory_stream_stride": 8192,
        "strict_validation": False,
        "seed": 37,
        "output_dir": str(tmp_path / "out"),
    }

    result = mp_sdc_offline_gen._generate_one(task)

    output_file = Path(result["output_file"])
    entry = result["entry"]

    assert output_file.exists()
    assert output_file.suffix == ".c"
    assert entry.metadata is not None
    assert entry.metadata["rendered_path"] == str(output_file.resolve())
    assert entry.metadata["rendered_format"] == "c"
    assert entry.metadata["source_path"] == str(output_file.resolve())

    payload = output_file.read_text(encoding="utf-8")
    assert "SDC_DIGEST=" in payload
    assert "sdc_benchmark_body" in payload
