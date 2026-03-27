# Copyright 2011-2021 IBM Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""ARM64 differential-test wrapper."""

from __future__ import absolute_import, division

from typing import List, Union

from microprobe.code import get_wrapper
from microprobe.code.ins import Instruction
from microprobe.utils.logger import get_logger
from microprobe.utils.typeguard_decorator import typeguard_testsuite

__all__ = ["BareMetalDiffWrapper"]

LOG = get_logger(__name__)


@typeguard_testsuite
class BareMetalDiffWrapper(get_wrapper("CWrapper")):
    """Emit a single-run C wrapper that prints a stable architectural digest."""

    def __init__(self):
        super(BareMetalDiffWrapper, self).__init__(reset=False)

    def _escape_c_string(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _instruction_asm(self, instr: Union[str, Instruction]) -> str:
        if isinstance(instr, str):
            return instr

        if instr.disable_asm:
            asm_parts: List[str] = []
            if instr.label is not None:
                asm_parts.append(instr.label + ":")

            fmtstr = "%%0%dx" % (len(instr.binary()) / 4)
            hstr = fmtstr % int(instr.binary(), 2)
            asm_parts.append(
                ".byte "
                + ",".join(
                    [
                        "0x%s" % hstr[idx : idx + 2]
                        for idx in range(0, len(hstr), 2)
                    ]
                )
            )
            return "\n".join(asm_parts)

        return instr.assembly()

    def _benchmark_instruction_lines(self) -> List[str]:
        lines: List[str] = []

        for instr in self.benchmark.init:
            lines.append(self._instruction_asm(instr))

        for bbl in self.benchmark.cfg.bbls:
            for instr in bbl.instrs:
                lines.append(self._instruction_asm(instr))

        for instr in self.benchmark.fini:
            lines.append(self._instruction_asm(instr))

        return [line for line in lines if line.strip()]

    def _asm_block(self, lines: List[str]) -> str:
        return "\n".join(
            ['"%s\\n"' % self._escape_c_string(line) for line in lines]
        )

    def _benchmark_function(self) -> str:
        body = [
            ".text",
            ".align 4",
            ".global sdc_benchmark_body",
            ".type sdc_benchmark_body, %function",
            "sdc_benchmark_body:",
            "adr x16, sdc_saved_core",
            "stp x19, x20, [x16, #0]",
            "stp x21, x22, [x16, #16]",
            "stp x23, x24, [x16, #32]",
            "stp x25, x26, [x16, #48]",
            "stp x27, x28, [x16, #64]",
            "stp x29, x30, [x16, #80]",
            "mov x17, sp",
            "str x17, [x16, #96]",
            "adr x16, sdc_saved_simd",
            "str q8, [x16, #0]",
            "str q9, [x16, #16]",
            "str q10, [x16, #32]",
            "str q11, [x16, #48]",
            "str q12, [x16, #64]",
            "str q13, [x16, #80]",
            "str q14, [x16, #96]",
            "str q15, [x16, #112]",
            "movi v0.16b, #0",
            "movi v1.16b, #0",
            "movi v2.16b, #0",
            "movi v3.16b, #0",
            "movi v4.16b, #0",
            "movi v5.16b, #0",
            "movi v6.16b, #0",
            "movi v7.16b, #0",
            "movi v8.16b, #0",
            "movi v9.16b, #0",
            "movi v10.16b, #0",
            "movi v11.16b, #0",
            "movi v12.16b, #0",
            "movi v13.16b, #0",
            "movi v14.16b, #0",
            "movi v15.16b, #0",
            "movi v16.16b, #0",
            "movi v17.16b, #0",
            "movi v18.16b, #0",
            "movi v19.16b, #0",
            "movi v20.16b, #0",
            "movi v21.16b, #0",
            "movi v22.16b, #0",
            "movi v23.16b, #0",
            "movi v24.16b, #0",
            "movi v25.16b, #0",
            "movi v26.16b, #0",
            "movi v27.16b, #0",
            "movi v28.16b, #0",
            "movi v29.16b, #0",
            "movi v30.16b, #0",
            "movi v31.16b, #0",
        ]
        body.extend(self._benchmark_instruction_lines())
        body.extend(
            [
                # One caller-saved GPR is intentionally used as scratch during
                # capture so the function can return safely even if the
                # benchmark clobbers SP/LR/frame state. We omit x18 from the
                # digest rather than risking undefined ABI behavior.
                "mov x18, x17",
                "mov x17, x16",
                "adr x16, sdc_gprs",
                "str x0, [x16, #0]",
                "str x1, [x16, #8]",
                "str x2, [x16, #16]",
                "str x3, [x16, #24]",
                "str x4, [x16, #32]",
                "str x5, [x16, #40]",
                "str x6, [x16, #48]",
                "str x7, [x16, #56]",
                "str x8, [x16, #64]",
                "str x9, [x16, #72]",
                "str x10, [x16, #80]",
                "str x11, [x16, #88]",
                "str x12, [x16, #96]",
                "str x13, [x16, #104]",
                "str x14, [x16, #112]",
                "str x15, [x16, #120]",
                "str x17, [x16, #128]",
                "str x18, [x16, #136]",
                "str x19, [x16, #152]",
                "str x20, [x16, #160]",
                "str x21, [x16, #168]",
                "str x22, [x16, #176]",
                "str x23, [x16, #184]",
                "str x24, [x16, #192]",
                "str x25, [x16, #200]",
                "str x26, [x16, #208]",
                "str x27, [x16, #216]",
                "str x28, [x16, #224]",
                "str x29, [x16, #232]",
                "str x30, [x16, #240]",
                "adr x16, sdc_nzcv",
                "mrs x17, nzcv",
                "str x17, [x16]",
                "adr x16, sdc_simd",
                "str q0, [x16, #0]",
                "str q1, [x16, #16]",
                "str q2, [x16, #32]",
                "str q3, [x16, #48]",
                "str q4, [x16, #64]",
                "str q5, [x16, #80]",
                "str q6, [x16, #96]",
                "str q7, [x16, #112]",
                "str q8, [x16, #128]",
                "str q9, [x16, #144]",
                "str q10, [x16, #160]",
                "str q11, [x16, #176]",
                "str q12, [x16, #192]",
                "str q13, [x16, #208]",
                "str q14, [x16, #224]",
                "str q15, [x16, #240]",
                "str q16, [x16, #256]",
                "str q17, [x16, #272]",
                "str q18, [x16, #288]",
                "str q19, [x16, #304]",
                "str q20, [x16, #320]",
                "str q21, [x16, #336]",
                "str q22, [x16, #352]",
                "str q23, [x16, #368]",
                "str q24, [x16, #384]",
                "str q25, [x16, #400]",
                "str q26, [x16, #416]",
                "str q27, [x16, #432]",
                "str q28, [x16, #448]",
                "str q29, [x16, #464]",
                "str q30, [x16, #480]",
                "str q31, [x16, #496]",
                "adr x16, sdc_saved_simd",
                "ldr q8, [x16, #0]",
                "ldr q9, [x16, #16]",
                "ldr q10, [x16, #32]",
                "ldr q11, [x16, #48]",
                "ldr q12, [x16, #64]",
                "ldr q13, [x16, #80]",
                "ldr q14, [x16, #96]",
                "ldr q15, [x16, #112]",
                "adr x16, sdc_saved_core",
                "ldp x19, x20, [x16, #0]",
                "ldp x21, x22, [x16, #16]",
                "ldp x23, x24, [x16, #32]",
                "ldp x25, x26, [x16, #48]",
                "ldp x27, x28, [x16, #64]",
                "ldp x29, x30, [x16, #80]",
                "ldr x17, [x16, #96]",
                "mov sp, x17",
                "ret",
                ".size sdc_benchmark_body, .-sdc_benchmark_body",
            ]
        )

        return "\n".join(
            [
                "extern void sdc_benchmark_body(void);",
                "__asm__(",
                self._asm_block(body),
                ");",
            ]
        )

    def headers(self):
        helper_lines = [
            super(BareMetalDiffWrapper, self).headers(),
            "#include <inttypes.h>",
            "",
            "static uint64_t sdc_gprs[31] = {0};",
            "static uint64_t sdc_nzcv = 0;",
            "static uint8_t sdc_simd[32 * 16] = {0};",
            "static uint64_t sdc_saved_core[13] = {0};",
            "static uint8_t sdc_saved_simd[8 * 16] = {0};",
            "",
            "static inline uint64_t sdc_rotl64(uint64_t value, unsigned shift)",
            "{",
            "    return (value << shift) | (value >> (64 - shift));",
            "}",
            "",
            "static inline uint64_t sdc_mix_u64(uint64_t state, uint64_t value)",
            "{",
            "    state ^= value + 0x9e3779b97f4a7c15ULL + (state << 6) + (state >> 2);",
            "    return sdc_rotl64(state, 17);",
            "}",
            "",
            "static inline uint64_t sdc_mix_bytes(",
            "    uint64_t state, const uint8_t *buffer, size_t size)",
            "{",
            "    size_t index = 0;",
            "    for (index = 0; index < size; ++index)",
            "    {",
            "        state ^= (uint64_t)buffer[index] << ((index & 7U) * 8U);",
            "        state *= 0x100000001b3ULL;",
            "        state = sdc_rotl64(state, 9);",
            "    }",
            "    return state;",
            "}",
            "",
            self._benchmark_function(),
            "",
        ]
        return "\n".join(helper_lines)

    def start_main(self):
        main = [super(BareMetalDiffWrapper, self).start_main()]
        main.extend(
            [
                "uint64_t sdc_digest = 0xcbf29ce484222325ULL;",
                "",
            ]
        )
        return "\n".join(main)

    def post_var(self):
        return "sdc_benchmark_body();\n"

    def start_loop(
        self, dummy_instr, dummy_instr_reset, dummy_aligned: bool = False
    ):
        return ""

    def wrap_ins(self, instr):
        LOG.debug("Benchmark instruction handled by sdc_benchmark_body: %s", instr)
        return ""

    def end_loop(self, dummy_instr):
        return ""

    def _memory_digest(self) -> str:
        digest_lines = []
        for var in self.benchmark.registered_global_vars():
            digest_lines.append(
                "sdc_digest = sdc_mix_bytes("
                f"sdc_digest, (const uint8_t *)&{var.name}, sizeof({var.name}));"
            )
        return "\n".join(digest_lines)

    def end_main(self):
        lines = [
            "for (size_t sdc_index = 0; sdc_index < 31; ++sdc_index)",
            "{",
            "    if (sdc_index == 18U)",
            "    {",
            "        continue;",
            "    }",
            "    sdc_digest = sdc_mix_u64(sdc_digest, sdc_gprs[sdc_index]);",
            "}",
            "sdc_digest = sdc_mix_u64(sdc_digest, sdc_nzcv);",
            "sdc_digest = sdc_mix_bytes(sdc_digest, sdc_simd, sizeof(sdc_simd));",
        ]

        memory_digest = self._memory_digest()
        if memory_digest:
            lines.append(memory_digest)

        lines.extend(
            [
                'printf("SDC_DIGEST=%016" PRIx64 "\\n", sdc_digest);',
                "fflush(stdout);",
                "return 0;",
                "}",
            ]
        )
        return "\n".join(lines)
