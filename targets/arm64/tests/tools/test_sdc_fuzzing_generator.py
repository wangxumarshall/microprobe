from collections import OrderedDict
from pathlib import Path
import sys

PROJECT_MICROPROBE_ROOT = Path(__file__).resolve().parents[4]
PROJECT_MICROPROBE_SRC = PROJECT_MICROPROBE_ROOT / "src"

for extra_path in [PROJECT_MICROPROBE_SRC, PROJECT_MICROPROBE_ROOT]:
    if str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))

from sdc_fuzzing_generator import InstructionPool


class _FakeInstruction:
    def __init__(self, name, mnemonic):
        self.name = name
        self.mnemonic = mnemonic


class _FakeISA:
    def __init__(self, instructions):
        self.instructions = OrderedDict((instr.name, instr) for instr in instructions)


class _FakeTarget:
    def __init__(self, instructions):
        self.isa = _FakeISA(instructions)


def test_instruction_pool_preserves_requested_length():
    target = _FakeTarget(
        [
            _FakeInstruction("ADD_X_REG_V0", "ADD"),
            _FakeInstruction("SUB_X_REG_V0", "SUB"),
        ]
    )
    pool = InstructionPool(target)

    sequence = pool.get_random_instructions(6, category="arithmetic")

    assert len(sequence) == 6
    assert all(instr.mnemonic in {"ADD", "SUB"} for instr in sequence)


def test_instruction_pool_prefers_same_category_for_similar_replacement():
    add = _FakeInstruction("ADD_X_REG_V0", "ADD")
    sub = _FakeInstruction("SUB_X_REG_V0", "SUB")
    ldr = _FakeInstruction("LDR_X_IMM_V0", "LDR")
    target = _FakeTarget([add, sub, ldr])
    pool = InstructionPool(target)

    replacement = pool.get_similar_instruction(add)

    assert replacement.name in {"SUB_X_REG_V0", "ADD_X_REG_V0"}
