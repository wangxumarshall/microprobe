# Microprobe架构研究发现

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
