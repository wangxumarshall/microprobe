# Microprobe架构研究发现

## 2026-03-27 SDC Fuzzing闭环修复结论

### 已修复

1. ARM64 target 无法导入：
   - `targets/arm64/isa/armv8-common/isa.py` 已补齐 `load/store/compare_and_branch/nop/set_register_to_address` 等最小实现。
   - `import_definition('armv8_common-armv8_common-aarch64_linux_gcc')` 现已通过。

2. ARM64 指令缺失关键语义属性：
   - `targets/arm64/isa/armv8-common/instruction.py` 现可推导 `branch`、`branch_relative`、`access_storage`、`privileged`、`trap`、`syscall`。
   - 对 `LOAD/STORE/PAIR/EXCLUSIVE/ATOMIC/CAS` 格式自动补最小 memory operand 描述。

3. ARM64 内存访存 pass 无法工作：
   - `src/microprobe/target/isa/instruction.py` 已补 `[...]` 语法的 assembly 替换。
   - `src/microprobe/code/ins.py` 现在会为常量可见 operand 自动填默认值，避免 helper 生成的指令在 `assembly()` 时崩溃。
   - `targets/arm64/isa/armv8-common/instruction.py` 现在按字段复制 operand，避免 `Rn` 的 address 标记污染 `Rs/Rt`。

4. ARM64 符号地址无法物化：
   - `targets/arm64/isa/armv8-common/instruction.yaml` 新增 `ADRP_X_V0`。
   - `targets/arm64/isa/armv8-common/instruction_field.yaml` 允许 `PCREL_ADDR` 使用可见 `immhi`。
   - `set_register_to_address()` 现在可发出 `ADRP + ADD :lo12:` 组合来初始化 `SingleMemoryStreamPass` 的全局变量基址。

5. 默认敏感种子分布失衡：
   - `targets/arm64/policies/sdc_fuzzing_policy.py` 的 `SDCSensitiveAnalyzer` 已改为按 `FMA / pair-memory / LSE` 交织取样。
   - 默认前 8 个种子现在会混合 `FMADD/FMSUB`、`LDP/STP`、`CAS*`。

6. `BareMetalDiffWrapper` 入口校验不稳：
   - 通过 `Instruction.__getattr__` 的默认布尔回退，补齐 `disable_asm` / `unsupported` 等常用标志缺省值。
   - 绑定真实 benchmark 后，wrapper 现在可以生成 `sdc_benchmark_body` 与 `SDC_DIGEST` 代码。

7. 安全问题：
   - `targets/arm64/tools/a64_isa_audit.py` 的 tar 解包已改为安全提取，避免路径穿越。

### 剩余风险 / 待决事项

1. 根目录 `run_sdc_differential.py` 与 `sdc_vault.py` 仍不在任何 git repo 中。
   - 这不是功能阻塞，但会影响“全部改动推送远端”的完整性。

2. 向量 load/store 相关格式仍未做端到端执行验证。
   - 当前默认主链已经依赖并验证了 `FMA + scalar pair + LSE/CAS`，但 `LDR_V/STR_V/LDP_V/STP_V/LD1/ST1` 仍建议后续单独补测试。

3. 本地缺少 `typeguard` 依赖，`pytest` 无法完整收敛。
   - 本轮主要使用 `py_compile` 与 focused smoke tests 验证。

4. `mcpat/mcpat` 仓库内没有现成 ARM64 gem5 样例输入。
   - 当前可确认模板/profile/CLI 接线已落地，但缺少仓库内自带的 `config.json + stats.txt` 回归样本。

5. ARM64 shifted-register assembly 语法仍未完全 canonical。
   - 当前 `ADD_X_REG_V0` / `SUBS_X_REG_V0` 已可生成字符串，但仍倾向输出 `..., lsl 0` / `..., 0 0` 风格而不是严格的 GNU AArch64 推荐写法。
   - 这不阻塞当前 `sdc_fuzzing` 主链，但后续若扩大依赖这类 register-shift helper，建议单独收敛 `shift_types` / immediate 表示层。

## 2026-03-26 ISA审计补充

### A. 仓库现状与文档一致性

1. `targets/arm64/` 目录已经存在完整骨架，包含 `isa/armv8-common/`、`env/`、`policies/`、`tests/`、`wrappers/`。
2. 根目录中的 `task_plan.md` 仍将 ARM64 实现标记为“未开始”，但 `targets/arm64/`、`ARM64_FINAL_REPORT.md`、`ARM64_PORTING_COMPLETE.md` 显示此前已经进行过实现。
3. 多份报告宣称“100% 完成”与“170+ 指令”，真实性需要直接以 YAML 定义、导入能力和测试结果复核。

### B. 本轮审计的直接入口

1. ISA 定义主入口：
   - `/Users/wangxu/1-project/sdc-fuzzing/microprobe/targets/arm64/isa/armv8-common/isa.yaml`
   - `/Users/wangxu/1-project/sdc-fuzzing/microprobe/targets/arm64/isa/armv8-common/instruction.yaml`
2. 扩展指令属性文件：
   - `/Users/wangxu/1-project/sdc-fuzzing/microprobe/targets/arm64/isa/armv8-common/instruction_props/`
3. 生成与检测策略入口：
   - `/Users/wangxu/1-project/sdc-fuzzing/microprobe/targets/arm64/policies/seq.py`
   - `/Users/wangxu/1-project/sdc-fuzzing/microprobe/targets/arm64/policies/sdc_detect.py`
4. 测试入口：
   - `/Users/wangxu/1-project/sdc-fuzzing/microprobe/targets/arm64/tests/targets/unit_tests.py`
   - `/Users/wangxu/1-project/sdc-fuzzing/microprobe/targets/arm64/tests/targets/integration_tests.py`

## 一、项目整体架构

### 1.1 目录结构分析

```
microprobe.wangxu/
├── microprobe/
│   ├── src/microprobe/          # 核心框架源码
│   │   ├── code/                # 代码生成模块
│   │   ├── driver/              # 设计空间探索驱动
│   │   ├── model/               # 分析模型
│   │   ├── passes/              # 代码转换passes
│   │   ├── schemas/             # YAML schema定义
│   │   ├── target/              # 目标架构抽象
│   │   │   ├── env/             # 执行环境
│   │   │   ├── isa/             # 指令集架构
│   │   │   └── uarch/           # 微架构
│   │   └── utils/               # 工具函数
│   │
│   ├── targets/                 # 具体目标实现
│   │   ├── generic/             # 通用组件
│   │   ├── power/               # PowerPC架构
│   │   └── riscv/               # RISC-V架构
│   │
│   ├── dev_tools/               # 开发工具
│   └── doc/                     # 文档
```

### 1.2 核心设计理念

**模块化架构**: Microprobe采用高度模块化的设计，将目标架构定义与代码生成逻辑完全分离。

**声明式定义**: 使用YAML文件声明式地定义指令集、寄存器、指令格式等，便于移植和维护。

**继承机制**: 支持ISA定义的继承（Extends字段），可以基于基础定义扩展新版本。

---

## 二、ISA定义机制深度分析

### 2.1 指令定义结构

**文件位置**: `targets/<arch>/isa/<variant>/instruction.yaml`

**核心字段**:
```yaml
- Name: "ADD_V0"              # 指令内部名称（唯一标识）
  Mnemonic: "ADD"             # 汇编助记符
  Description: "Add"          # 指令描述
  Opcode: "33"                # 操作码（十六进制）
  Format: "r"                 # 指令格式引用
  Operands:                   # 操作数定义
    funct3: ['0', 'funct3', '?']    # [值, 字段名, 类型]
  ImplicitOperands:           # 隐式操作数
    CR0: ['CR0', 'O']         # 条件寄存器
  MemoryOperands:             # 内存操作数
    MEM1: [['rs1'], [8], 8, 'IO']  # [[地址寄存器], [大小], 对齐, 访问类型]
```

### 2.2 操作数类型编码

**操作数格式**: `[value, field_name, type]`

**类型标识**:
- `I`: Input (输入操作数)
- `O`: Output (输出操作数)
- `IO`: Input/Output (输入输出操作数)
- `?`: 固定值/编码字段

### 2.3 指令格式定义

**文件位置**: `targets/<arch>/isa/<variant>/instruction_format.yaml`

**作用**: 定义指令的二进制编码布局和字段位置。

### 2.4 指令字段定义

**文件位置**: `targets/<arch>/isa/<variant>/instruction_field.yaml`

**作用**: 定义指令中各个字段的名称、位置和宽度。

---

## 三、寄存器定义机制

### 3.1 寄存器定义结构

**文件位置**: `targets/<arch>/isa/<variant>/register.yaml`

**核心字段**:
```yaml
- Name: X0                    # 寄存器名称
  Type: ireg                  # 寄存器类型
  Representation: 'x0'        # 汇编表示
  Codification: '0'           # 二进制编码
  Description: "General Purpose Register 0"
  Repeat:                     # 批量定义
    From: 0
    To: 31
```

### 3.2 寄存器类型

**文件位置**: `targets/<arch>/isa/<variant>/register_type.yaml`

**常见类型**:
- `GPR`: 通用寄存器
- `FPR`: 浮点寄存器
- `SPR`: 特殊寄存器
- `CR`: 条件寄存器
- `VR`: 向量寄存器

---

## 四、PowerPC架构实现分析

### 4.1 PowerPC ISA组织结构

```
targets/power/isa/
├── p-common/              # 通用PowerPC定义
│   ├── instruction.yaml
│   ├── register.yaml
│   ├── instruction_format.yaml
│   └── instruction_props/     # 指令属性分类
│       ├── branch.yaml
│       ├── memory.yaml
│       └── ...
├── p-v2_06/               # Power ISA 2.06
├── p-v2_07/               # Power ISA 2.07
├── p-v3_00/               # Power ISA 3.00
└── p-v3_10/               # Power ISA 3.10
```

### 4.2 PowerPC指令特点

1. **固定长度**: 32位固定长度指令
2. **多种格式**: I, B, SC, D, DS, DQ, X, XL, etc.
3. **条件码**: 强大的条件寄存器（CR0-CR7）
4. **链接分支**: 带链接的分支指令（保存返回地址）

### 4.3 PowerPC寄存器模型

- **GPR**: 32个通用寄存器（GPR0-GPR31）
- **FPR**: 32个浮点寄存器（FPR0-FPR31）
- **VSR**: 64个向量标量寄存器（VSR0-VSR63）
- **CR**: 8个条件寄存器字段（CR0-CR7）
- **SPR**: 特殊寄存器（LR, CTR, XER, etc.）

---

## 五、RISC-V架构实现分析

### 5.1 RISC-V ISA组织结构

```
targets/riscv/isa/
├── riscv-common/          # 通用RISC-V定义
│   ├── instruction.yaml
│   ├── register.yaml
│   └── ...
├── riscv-v2_2/            # RISC-V v2.2
└── riscv-boom/            # BOOM处理器特定
```

### 5.2 RISC-V指令特点

1. **变长指令**: 支持多种长度（16/32/48/64位）
2. **模块化**: 基础整数指令集 + 可选扩展
3. **简洁设计**: 规则化的指令编码
4. **加载存储架构**: 只有加载/存储指令访问内存

### 5.3 RISC-V寄存器模型

- **X0-X31**: 32个通用寄存器（X0硬连线为0）
- **F0-F31**: 32个浮点寄存器
- **PC**: 程序计数器

---

## 六、代码生成流程

### 6.1 核心类关系

```
Target (目标平台)
├── ISA (指令集架构)
│   ├── Instructions (指令集合)
│   ├── Registers (寄存器集合)
│   └── Formats (指令格式)
├── Microarchitecture (微架构)
└── Environment (执行环境)

Instruction (指令实例)
├── InstructionType (指令类型)
├── Operands (操作数值)
└── Context (上下文信息)
```

### 6.2 代码生成步骤

1. **目标选择**: 加载Target定义
2. **策略应用**: 应用代码生成策略
3. **指令选择**: 根据策略选择指令
4. **寄存器分配**: 分配物理寄存器
5. **地址解析**: 解析标签和地址
6. **二进制生成**: 生成最终二进制代码

---

## 七、工具链分析

### 7.1 核心工具

| 工具 | 功能 |
|------|------|
| mp_seq | 生成指令序列 |
| mp_seqtune | 调优指令序列 |

---

## 八、ARM64 ISA 审计发现（2026-03-26）

### 8.1 官方规范基线

- 使用 Arm 官方 A64 XML 数据集作为指令覆盖基线：
  `https://developer.arm.com/-/cdn-downloads/permalink/Exploration-Tools-A64-ISA/ISA_A64/ISA_A64_xml_A_profile-2025-09_ASL1.tar.gz`
- 该数据集可直接解析出 `mnemonic`、`instr-class`、编码图和 alias 关系，适合自动化审计当前仓库的 ARM64 实现。

### 8.2 当前仓库的 ARM64 覆盖现状

- `targets/arm64/isa/armv8-common/instruction.yaml` 目前只有 `56` 个 instruction entries。
- 唯一助记符只有 `27` 个：
  `ADD, ADDS, AND, B, B., BL, BLR, BR, CBNZ, CBZ, EOR, LDP, LDR, MOVK, MOVN, MOVZ, MUL, ORR, RET, SDIV, STP, STR, SUB, SUBS, TBNZ, TBZ, UDIV`
- Arm 官方 A64 XML 中，仅 `general` 类就有 `388` 个唯一助记符，`system` 类还有 `74` 个唯一助记符。
- 因此，当前实现并不接近“完整 ARMv8/A64 指令集”，更像一个非常初步的整数/分支子集。

### 8.3 关键缺口

- `isa.py` 中实际依赖但 YAML 未定义的指令：
  - `MOV_X_V0`
  - `ADRP_X_V0`
  - `NOP_V0`
- 高价值但缺失的基础 general/system 指令族包括：
  - 地址形成：`ADR`, `ADRP`
  - 寄存器/别名：`MOV (register)`
  - 条件选择：`CSEL`, `CSINC`, `CSINV`, `CSNEG`
  - 带进位算术：`ADC`, `ADCS`
  - 标志更新逻辑：`ANDS`, `BICS`
  - 位域/提取：`BFM`, `EXTR`
  - 屏障/提示：`NOP`, `DMB`, `DSB`, `ISB`

### 8.4 生成质量问题

- `targets/arm64/isa/armv8-common/generator.py` 的 `generate()` 直接返回空列表，ARM64 特定的 immediate/address/helper 生成能力实际上没有落地。
- `sdc_fuzzing_generator.py` 以随机采样为主，缺少：
  - 覆盖驱动的类别平衡
  - 数据依赖链
  - 标志寄存器相关序列
  - 地址生成 + load/store 组合
  - 冗余计算/多样化检错模式优先级
- `generate_single_testcase()` 没有使用 policy 返回的 synthesizer，导致生成流程语义上就是错的。

### 8.5 编码核对样例

- 使用 `clang -target aarch64-linux-gnu` 组装样例指令后，确认以下真实编码存在并值得纳入仓库基线：
  - `add x0, x1, #1` -> `0x91000420`
  - `sub x2, x3, #0x123` -> `0xd1048c62`
  - `adr x8, label` -> `0x10000088`
  - `adrp x9, label` -> `0x90000009`
  - `csel x10, x11, x12, eq` -> `0x9a8c016a`
  - `nop` -> `0xd503201f`
  - `ret` -> `0xd65f03c0`
| mp_epi | 生成EP (Execution Profile) |
| mp_mpt2bin | MPT格式转二进制 |
| mp_mpt2elf | MPT格式转ELF |
| mp_bin2asm | 二进制转汇编 |
| mp_objdump2mpt | objdump转MPT |
| mp_c2mpt | C代码转MPT |
| mp_target | 目标信息查询 |

### 7.2 输出格式

- **MPT**: Microprobe Test format (.mpt)
- **C代码**: C语言测试程序
- **汇编**: 汇编代码
- **二进制**: 原始二进制
- **ELF**: ELF可执行文件

---

## 八、测试框架

### 8.1 测试组织

```
targets/<arch>/tests/
├── tools/                 # 工具测试
│   ├── mp_seq_tests.py
│   ├── mp_epi_tests.py
│   └── ...
├── targets/               # 目标测试
│   └── targets_tests.py
└── examples/              # 示例测试
    └── examples_<arch>_tests.py
```

### 8.2 测试方法

- **单元测试**: 针对单个组件的测试
- **集成测试**: 端到端测试
- **回归测试**: 确保修改不破坏现有功能

---

## 九、ARM64移植关键发现

### 9.1 ARM64 vs PowerPC/RISC-V对比

| 特性 | ARM64 | PowerPC | RISC-V |
|------|-------|---------|--------|
| 指令长度 | 32位固定 | 32位固定 | 变长 |
| 通用寄存器 | 31个(X0-X30) | 32个 | 32个 |
| 浮点寄存器 | 32个(V0-V31) | 32个 | 32个 |
| 条件码 | NZCV标志 | CR寄存器 | 无 |
| 特权级 | EL0-EL3 | MSR bits | U/S/M modes |
| 指令编码 | 复杂规则化 | 多种格式 | 规则化 |

### 9.2 ARM64指令分类

**数据处理**:
- 算术: ADD, SUB, MUL, DIV, SDIV, UDIV
- 逻辑: AND, ORR, EOR, BIC, ORN, EON
- 移位: LSL, LSR, ASR, ROR
- 扩展: SXTB, SXTH, SXTW, UXTB, UXTH, UXTW

**加载存储**:
- 单寄存器: LDR, STR
- 多寄存器: LDP, STP
- 原子: LDADD, STADD, CAS, SWP
- 排他: LDXR, STXR

**分支**:
- 无条件: B, BL, BR, BLR, RET
- 条件: B.cond, CBNZ, CBZ, TBNZ, TBZ
- 异常: SVC, HVC, SMC, BRK

**浮点/SIMD**:
- 标量浮点: FADD, FSUB, FMUL, FDIV
- NEON向量: VADD, VSUB, VMUL, VMLA
- 加密: AES, SHA, PMULL

**系统**:
- 寄存器访问: MRS, MSR
- 内存屏障: DMB, DSB, ISB
- 缓存: IC, DC, TLBI

### 9.3 ARM64编码特点

1. **操作码位置**: 不同指令类别操作码位置不同
2. **条件码**: 部分指令支持条件执行
3. **立即数**: 多种立即数编码方式
4. **向量元素**: 支持向量元素访问

---

## 十、SDC检测策略

### 10.1 SDC类型

1. **计算错误**: 算术运算结果错误
2. **内存错误**: 数据损坏或错误读写
3. **控制流错误**: 分支跳转错误
4. **时序错误**: 并发竞争条件

### 10.2 检测方法

**冗余计算**:
- 相同操作执行多次，比较结果
- 使用不同算法计算相同结果

**校验和**:
- 计算数据校验和
- 定期验证数据完整性

**边界检查**:
- 检查数组访问边界
- 验证指针有效性

**断言**:
- 插入运行时断言
- 验证不变量条件

### 10.3 ARM64特定检测

- **NZCV标志验证**: 检查条件码正确性
- **浮点异常**: 检查FPCR/FPSR状态
- **内存一致性**: 使用DC CVAP等指令
- **原子操作**: 验证LDXR/STXR配对

---

## 十一、实现建议

### 11.1 分阶段实现

**Phase 1**: 核心指令集
- 数据处理指令
- 基本加载存储
- 分支指令

**Phase 2**: 扩展指令
- 浮点指令
- SIMD指令
- 原子指令

**Phase 3**: 高级特性
- 系统指令
- 加密指令
- SVE扩展

### 11.2 代码复用

- 复用PowerPC的ISA框架
- 参考RISC-V的简洁设计
- 利用现有的代码生成pass

### 11.3 测试策略

- 逐指令验证编码正确性
- 使用QEMU进行功能测试
- 在真实硬件上验证

---

## 十二、ARM64架构研究发现

### 12.1 ARM64架构特性

**基本特性**:
- 32位固定长度指令
- Little-endian默认
- 加载存储架构
- 31个通用寄存器 (X0-X30)
- 32个SIMD/浮点寄存器 (V0-V31, 128-bit)
- 零寄存器 (XZR/WZR)
- 条件码标志 (NZCV)
- 四级特权模型 (EL0-EL3)

### 12.2 ARM64 vs PowerPC/RISC-V对比

| 特性 | ARM64 | PowerPC | RISC-V |
|------|-------|---------|--------|
| 指令长度 | 32位固定 | 32位固定 | 变长 |
| 通用寄存器 | 31个(X0-X30) | 32个 | 32个 |
| 浮点寄存器 | 32个(V0-V31) | 32个 | 32个 |
| 条件码 | NZCV标志 | CR寄存器 | 无 |
| 特权级 | EL0-EL3 | MSR bits | U/S/M modes |
| 指令编码 | 复杂规则化 | 多种格式 | 规则化 |
| 零寄存器 | 有(XZR) | 无 | 有(X0) |

### 12.3 ARM64指令编码特点

**编码格式**:
- 数据处理（立即数）: sf + op + S + sh + imm16 + Rd
- 数据处理（寄存器）: sf + op + S + shift + Rm + imm6 + Rn + Rd
- 加载存储: size + opc + V + imm12 + Rn + Rt
- 分支: opcode + imm26 或 opcode + imm19 + cond

**关键发现**:
1. ARM64指令编码比PowerPC更规则
2. 条件码机制比PowerPC简单
3. 零寄存器简化了某些操作
4. SIMD和浮点使用相同寄存器组

### 12.4 移植策略

**目录结构**:
```
targets/arm64/
├── isa/armv8-common/      # 通用定义
├── uarch/                 # 微架构
├── env/                   # 环境
├── policies/              # 策略
├── wrappers/              # 包装器
└── tests/                 # 测试
```

**实现优先级**:
1. 寄存器定义
2. 指令格式和字段
3. 核心整数指令
4. 加载存储指令
5. 分支指令
6. 浮点/SIMD指令
7. 系统指令
8. SDC检测策略

### 12.5 SDC检测关键点

**ARM64特定检测**:
- NZCV标志验证
- 浮点异常检查 (FPCR/FPSR)
- 内存一致性验证
- 原子操作正确性 (LDXR/STXR)

**检测方法**:
1. 校验和验证
2. 冗余计算对比
3. 边界值测试
4. 条件码检查

---

## 更新日志

- 2026-03-26: 创建研究发现文档，完成初步架构分析
- 2026-03-26: 添加ARM64架构研究发现
