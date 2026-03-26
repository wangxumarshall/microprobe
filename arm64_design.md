# ARM64 (AArch64) 移植详细设计

## 一、ARM64架构概述

### 1.1 ARM64基本特性

**指令集特点**:
- 32位固定长度指令
- Little-endian默认（支持big-endian）
- 加载存储架构
- 条件执行支持（部分指令）

**寄存器模型**:
- 31个通用寄存器 (X0-X30)
- 32个SIMD/浮点寄存器 (V0-V31, 128-bit)
- 零寄存器 (XZR/WZR)
- 栈指针 (SP)
- 程序计数器 (PC)
- 程序状态寄存器 (PSTATE: NZCV标志)
- 系统寄存器

**特权级模型**:
- EL0: 用户态
- EL1: 内核态（操作系统）
- EL2: 虚拟化层（Hypervisor）
- EL3: 安全监控（Secure Monitor）

### 1.2 ARM64指令编码格式

ARM64指令编码分为多个类别：

**数据处理（立即数）**:
```
| 31 30 29 28 | 27 26 25 | 24 23 22 21 | 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 | 4 3 2 1 0 |
|    sf op    |   S      |    sh       |              imm16                         |    Rd     |
```

**数据处理（寄存器）**:
```
| 31 30 29 28 27 26 25 | 24 23 22 21 | 20 19 18 17 16 15 14 13 12 11 | 10 9 8 7 6 5 | 4 3 2 1 0 |
|      sf op S         |    shift    |           Rm                 |   imm6      |    Rn     | ... |
```

**加载存储**:
```
| 31 30 29 28 27 26 25 | 24 23 22 | 21 | 20 19 18 17 16 15 14 13 12 11 10 | 9 8 7 6 5 | 4 3 2 1 0 |
|     size L           |  opc     | V  |          imm12                 |    Rn     |    Rt     |
```

**分支**:
```
| 31 30 29 28 27 26 25 24 23 22 21 20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 | 4 3 2 1 0 |
|                         imm26                                              |   opcode  |
```

---

## 二、目录结构设计

### 2.1 ARM64目标目录

```
targets/arm64/
├── isa/
│   ├── armv8-common/                    # ARMv8通用定义
│   │   ├── instruction.yaml             # 指令定义
│   │   ├── instruction_format.yaml      # 指令格式定义
│   │   ├── instruction_field.yaml       # 指令字段定义
│   │   ├── register.yaml                # 寄存器定义
│   │   ├── register_type.yaml           # 寄存器类型定义
│   │   ├── operand.yaml                 # 操作数定义
│   │   ├── isa.yaml                     # ISA主配置
│   │   ├── isa.py                       # ISA类实现
│   │   ├── instruction.py               # 指令类实现
│   │   ├── instruction_format.py        # 指令格式类实现
│   │   ├── instruction_field.py         # 指令字段类实现
│   │   ├── register.py                  # 寄存器类实现
│   │   ├── register_type.py             # 寄存器类型类实现
│   │   ├── operand.py                   # 操作数类实现
│   │   ├── comparator.py                # 指令比较器
│   │   ├── generator.py                 # 指令生成器
│   │   └── instruction_props/           # 指令属性分类
│   │       ├── branch.yaml
│   │       ├── memory.yaml
│   │       ├── arithmetic.yaml
│   │       ├── logical.yaml
│   │       ├── floating.yaml
│   │       ├── simd.yaml
│   │       ├── system.yaml
│   │       └── privileged.yaml
│   ├── armv8-a/                         # ARMv8-A特定定义
│   │   ├── isa.yaml
│   │   ├── instruction.yaml
│   │   └── ...
│   └── armv8-m/                         # ARMv8-M特定定义
│       ├── isa.yaml
│       └── ...
├── uarch/
│   ├── armv8-common/                    # 通用微架构定义
│   │   ├── microarchitecture.yaml
│   │   ├── element.yaml
│   │   ├── element_type.yaml
│   │   └── ...
│   ├── cortex-a53/                      # Cortex-A53特定
│   ├── cortex-a72/                      # Cortex-A72特定
│   └── neoverse-n1/                     # Neoverse N1特定
├── env/
│   ├── aarch64_linux_gcc.py             # Linux/ARM64环境
│   ├── aarch64_baremetal.py             # 裸机环境
│   └── aarch64_qemu.py                  # QEMU模拟环境
├── policies/
│   ├── epi.py                           # EPI生成策略
│   ├── seq.py                           # 序列生成策略
│   ├── seqtune.py                       # 序列调优策略
│   └── sdc_detect.py                    # SDC检测策略
├── wrappers/
│   ├── aarch64_asm.py                   # ARM64汇编包装器
│   └── aarch64_c.py                     # ARM64 C代码包装器
├── templates/
│   ├── aarch64.ldscript                 # 链接脚本
│   └── startup.S                        # 启动代码
├── tests/
│   ├── tools/                           # 工具测试
│   ├── targets/                         # 目标测试
│   └── examples/                        # 示例测试
└── doc/
    ├── examples.rst
    └── examples_arm64.rst
```

---

## 三、寄存器定义设计

### 3.1 寄存器类型 (register_type.yaml)

```yaml
- Name: GPR64
  Description: 64-bit General Purpose Register
  Size: 64
  
- Name: GPR32
  Description: 32-bit General Purpose Register (lower 32 bits)
  Size: 32
  
- Name: SIMD_FP
  Description: SIMD and Floating Point Register (128-bit)
  Size: 128
  
- Name: SPR
  Description: Special Purpose Register
  Size: 64
  
- Name: SystemReg
  Description: System Register
  Size: 64
  
- Name: Condition
  Description: Condition Flags (NZCV)
  Size: 4
```

### 3.2 寄存器定义 (register.yaml)

```yaml
# Zero Register
- Name: XZR
  Type: GPR64
  Representation: 'xzr'
  Codification: '31'
  Description: Zero Register (64-bit)

- Name: WZR
  Type: GPR32
  Representation: 'wzr'
  Codification: '31'
  Description: Zero Register (32-bit)

# Stack Pointer
- Name: SP
  Type: SPR
  Representation: 'sp'
  Description: Stack Pointer

# General Purpose Registers (64-bit)
- Name: X0
  Type: GPR64
  Representation: 'x0'
  Codification: '0'
  Description: General Purpose Register 0 (64-bit)
  Repeat:
    From: 0
    To: 30

# General Purpose Registers (32-bit view)
- Name: W0
  Type: GPR32
  Representation: 'w0'
  Codification: '0'
  Description: General Purpose Register 0 (32-bit)
  Repeat:
    From: 0
    To: 30

# SIMD/Floating Point Registers
- Name: V0
  Type: SIMD_FP
  Representation: 'v0'
  Codification: '0'
  Description: SIMD/Floating Point Register 0
  Repeat:
    From: 0
    To: 31

# 64-bit view of SIMD registers (D registers)
- Name: D0
  Type: SIMD_FP
  Representation: 'd0'
  Codification: '0'
  Description: Double Precision Register 0
  Repeat:
    From: 0
    To: 31

# 32-bit view of SIMD registers (S registers)
- Name: S0
  Type: SIMD_FP
  Representation: 's0'
  Codification: '0'
  Description: Single Precision Register 0
  Repeat:
    From: 0
    To: 31

# Program Counter
- Name: PC
  Type: SPR
  Representation: 'pc'
  Description: Program Counter

# Special Registers
- Name: LR
  Type: GPR64
  Representation: 'x30'
  Codification: '30'
  Description: Link Register (X30)

- Name: FP
  Type: GPR64
  Representation: 'x29'
  Codification: '29'
  Description: Frame Pointer (X29)

# System Registers
- Name: NZCV
  Type: Condition
  Representation: 'nzcv'
  Description: Condition Flags

- Name: FPCR
  Type: SystemReg
  Representation: 'fpcr'
  Description: Floating-Point Control Register

- Name: FPSR
  Type: SystemReg
  Representation: 'fpsr'
  Description: Floating-Point Status Register

- Name: SPSR_EL1
  Type: SystemReg
  Representation: 'spsr_el1'
  Description: Saved Program Status Register (EL1)

- Name: ELR_EL1
  Type: SystemReg
  Representation: 'elr_el1'
  Description: Exception Link Register (EL1)
```

---

## 四、指令格式定义设计

### 4.1 指令字段定义 (instruction_field.yaml)

```yaml
# Common fields

# 5-bit register fields
- Name: Rd
  Description: Destination Register
  Operand: GPR64_regs
  Show: True
  Size: 5
  IO: "O"

- Name: Rn
  Description: First Source Register
  Operand: GPR64_regs
  Show: True
  Size: 5
  IO: "I"

- Name: Rm
  Description: Second Source Register
  Operand: GPR64_regs
  Show: True
  Size: 5
  IO: "I"

- Name: Rt
  Description: Transfer Register (for load/store)
  Operand: GPR64_regs
  Show: True
  Size: 5
  IO: "IO"

# 32-bit register fields
- Name: Wd
  Description: Destination Register (32-bit)
  Operand: GPR32_regs
  Show: True
  Size: 5
  IO: "O"

- Name: Wn
  Description: First Source Register (32-bit)
  Operand: GPR32_regs
  Show: True
  Size: 5
  IO: "I"

- Name: Wm
  Description: Second Source Register (32-bit)
  Operand: GPR32_regs
  Show: True
  Size: 5
  IO: "I"

# SIMD/FP register fields
- Name: Vd
  Description: Destination SIMD Register
  Operand: SIMD_FP_regs
  Show: True
  Size: 5
  IO: "O"

- Name: Vn
  Description: First Source SIMD Register
  Operand: SIMD_FP_regs
  Show: True
  Size: 5
  IO: "I"

- Name: Vm
  Description: Second Source SIMD Register
  Operand: SIMD_FP_regs
  Show: True
  Size: 5
  IO: "I"

# Immediate fields
- Name: imm16
  Description: 16-bit Immediate
  Operand: u.imm16
  Show: True
  Size: 16
  IO: "I"

- Name: imm12
  Description: 12-bit Immediate
  Operand: u.imm12
  Show: True
  Size: 12
  IO: "I"

- Name: imm9
  Description: 9-bit Immediate (signed)
  Operand: s.imm9
  Show: True
  Size: 9
  IO: "I"

- Name: imm7
  Description: 7-bit Immediate (signed)
  Operand: s.imm7
  Show: True
  Size: 7
  IO: "I"

- Name: imm5
  Description: 5-bit Immediate (for shifts)
  Operand: u.imm5
  Show: True
  Size: 5
  IO: "I"

- Name: imm26
  Description: 26-bit Branch Immediate
  Operand: s.imm26_shift2
  Show: True
  Size: 26
  IO: "I"

- Name: imm19
  Description: 19-bit Conditional Branch Immediate
  Operand: s.imm19_shift2
  Show: True
  Size: 19
  IO: "I"

# Condition code
- Name: cond
  Description: Condition Code
  Operand: condition_codes
  Show: True
  Size: 4
  IO: "I"

# Shift type
- Name: shift
  Description: Shift Type
  Operand: shift_types
  Show: True
  Size: 2
  IO: "I"

# Option field (for prefetch, etc.)
- Name: option
  Description: Option Field
  Operand: option_values
  Show: False
  Size: 3
  IO: "I"

# Fixed fields
- Name: sf
  Description: Size Flag (0=32-bit, 1=64-bit)
  Show: False
  Size: 1
  IO: "?"

- Name: S
  Description: Set Flags
  Show: False
  Size: 1
  IO: "?"

# Opcode fields
- Name: opcode_dp_imm
  Description: Data Processing Immediate Opcode
  Show: False
  Size: 3
  IO: "?"

- Name: opcode_dp_reg
  Description: Data Processing Register Opcode
  Show: False
  Size: 6
  IO: "?"

- Name: opcode_ls
  Description: Load Store Opcode
  Show: False
  Size: 4
  IO: "?"

- Name: opcode_branch
  Description: Branch Opcode
  Show: False
  Size: 4
  IO: "?"
```

### 4.2 指令格式定义 (instruction_format.yaml)

```yaml
# Data Processing - Immediate

- Name: "PCREL_ADDR"
  Description: "PC-relative Addressing"
  Fields:
  - "opcode_dp_imm"
  - "immlo"
  - "immhi"
  - "Rd"
  Assembly: "OPC Rd, label"

- Name: "ADD_SUB_IMM"
  Description: "Add/Subtract (Immediate)"
  Fields:
  - "sf"
  - "opcode_dp_imm"
  - "S"
  - "shift"
  - "imm12"
  - "Rn"
  - "Rd"
  Assembly: "OPC Rd, Rn, imm12"

- Name: "LOGICAL_IMM"
  Description: "Logical (Immediate)"
  Fields:
  - "sf"
  - "opcode_dp_imm"
  - "immr"
  - "imms"
  - "Rn"
  - "Rd"
  Assembly: "OPC Rd, Rn, imm"

- Name: "MOVE_WIDE"
  Description: "Move Wide (Immediate)"
  Fields:
  - "sf"
  - "opcode_dp_imm"
  - "hw"
  - "imm16"
  - "Rd"
  Assembly: "OPC Rd, imm16"

# Data Processing - Register

- Name: "LOGICAL_REG"
  Description: "Logical (Shifted Register)"
  Fields:
  - "sf"
  - "opcode_dp_reg"
  - "shift"
  - "N"
  - "Rm"
  - "imm6"
  - "Rn"
  - "Rd"
  Assembly: "OPC Rd, Rn, Rm, shift imm6"

- Name: "ADD_SUB_REG"
  Description: "Add/Subtract (Shifted Register)"
  Fields:
  - "sf"
  - "opcode_dp_reg"
  - "S"
  - "shift"
  - "0_1"
  - "Rm"
  - "imm6"
  - "Rn"
  - "Rd"
  Assembly: "OPC Rd, Rn, Rm, shift imm6"

- Name: "ADD_SUB_EXT"
  Description: "Add/Subtract (Extended Register)"
  Fields:
  - "sf"
  - "opcode_dp_reg"
  - "S"
  - "option"
  - "imm3"
  - "Rm"
  - "Rn"
  - "Rd"
  Assembly: "OPC Rd, Rn, Rm, extend imm3"

- Name: "MUL_DIV"
  Description: "Multiply/Divide"
  Fields:
  - "sf"
  - "opcode_dp_reg"
  - "Rm"
  - "0_14"
  - "Rn"
  - "Rd"
  Assembly: "OPC Rd, Rn, Rm"

# Load/Store

- Name: "LOAD_STORE_IMM"
  Description: "Load/Store (Immediate)"
  Fields:
  - "size"
  - "opcode_ls"
  - "V"
  - "imm12"
  - "Rn"
  - "Rt"
  Assembly: "OPC Rt, [Rn, imm12]"

- Name: "LOAD_STORE_REG"
  Description: "Load/Store (Register)"
  Fields:
  - "size"
  - "opcode_ls"
  - "V"
  - "option"
  - "S"
  - "Rm"
  - "Rn"
  - "Rt"
  Assembly: "OPC Rt, [Rn, Rm, extend]"

- Name: "LOAD_STORE_PAIR"
  Description: "Load/Store Pair"
  Fields:
  - "opcode_ls"
  - "L"
  - "imm7"
  - "Rt2"
  - "Rn"
  - "Rt"
  Assembly: "OPC Rt, Rt2, [Rn, imm7]"

- Name: "LOAD_LITERAL"
  Description: "Load Literal"
  Fields:
  - "opcode_ls"
  - "imm19"
  - "Rt"
  Assembly: "OPC Rt, label"

# Branch

- Name: "UNCOND_BRANCH_IMM"
  Description: "Unconditional Branch (Immediate)"
  Fields:
  - "opcode_branch"
  - "imm26"
  Assembly: "OPC label"

- Name: "COND_BRANCH_IMM"
  Description: "Conditional Branch (Immediate)"
  Fields:
  - "opcode_branch"
  - "imm19"
  - "0_5"
  - "cond"
  Assembly: "OPC cond, label"

- Name: "COMPARE_BRANCH"
  Description: "Compare and Branch"
  Fields:
  - "sf"
  - "opcode_branch"
  - "imm19"
  - "Rn"
  - "0_5"
  Assembly: "OPC Rn, label"

- Name: "TEST_BRANCH"
  Description: "Test and Branch"
  Fields:
  - "sf"
  - "opcode_branch"
  - "b5"
  - "b40"
  - "imm14"
  - "Rn"
  - "0_5"
  Assembly: "OPC Rn, bit, label"

- Name: "UNCOND_BRANCH_REG"
  Description: "Unconditional Branch (Register)"
  Fields:
  - "opcode_branch"
  - "0_5"
  - "Rn"
  - "0_15"
  Assembly: "OPC Rn"
```

---

## 五、指令定义设计

### 5.1 数据处理指令 (instruction.yaml - 部分)

```yaml
# ADD Instructions
- Name: "ADD_X_V0"
  Mnemonic: "ADD"
  Description: "Add (64-bit, immediate)"
  Opcode: "1000"
  Format: "ADD_SUB_IMM"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['0', 'opcode_dp_imm', '?']
    S: ['0', 'S', '?']
    shift: ['0', 'shift', '?']

- Name: "ADDS_X_V0"
  Mnemonic: "ADDS"
  Description: "Add and Set Flags (64-bit, immediate)"
  Opcode: "1000"
  Format: "ADD_SUB_IMM"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['0', 'opcode_dp_imm', '?']
    S: ['1', 'S', '?']
    shift: ['0', 'shift', '?']
  ImplicitOperands:
    NZCV: ['NZCV', 'O']

- Name: "SUB_X_V0"
  Mnemonic: "SUB"
  Description: "Subtract (64-bit, immediate)"
  Opcode: "1010"
  Format: "ADD_SUB_IMM"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['2', 'opcode_dp_imm', '?']
    S: ['0', 'S', '?']
    shift: ['0', 'shift', '?']

- Name: "SUBS_X_V0"
  Mnemonic: "SUBS"
  Description: "Subtract and Set Flags (64-bit, immediate)"
  Opcode: "1010"
  Format: "ADD_SUB_IMM"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['2', 'opcode_dp_imm', '?']
    S: ['1', 'S', '?']
    shift: ['0', 'shift', '?']
  ImplicitOperands:
    NZCV: ['NZCV', 'O']

# Logical Instructions
- Name: "AND_X_V0"
  Mnemonic: "AND"
  Description: "Bitwise AND (64-bit, immediate)"
  Opcode: "1000"
  Format: "LOGICAL_IMM"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['0', 'opcode_dp_imm', '?']

- Name: "ORR_X_V0"
  Mnemonic: "ORR"
  Description: "Bitwise OR (64-bit, immediate)"
  Opcode: "1000"
  Format: "LOGICAL_IMM"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['1', 'opcode_dp_imm', '?']

- Name: "EOR_X_V0"
  Mnemonic: "EOR"
  Description: "Bitwise Exclusive OR (64-bit, immediate)"
  Opcode: "1000"
  Format: "LOGICAL_IMM"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['2', 'opcode_dp_imm', '?']

# Move Instructions
- Name: "MOVZ_X_V0"
  Mnemonic: "MOVZ"
  Description: "Move Wide with Zero (64-bit)"
  Opcode: "1010"
  Format: "MOVE_WIDE"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['2', 'opcode_dp_imm', '?']
    hw: ['0', 'hw', '?']

- Name: "MOVK_X_V0"
  Mnemonic: "MOVK"
  Description: "Move Wide with Keep (64-bit)"
  Opcode: "1011"
  Format: "MOVE_WIDE"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['3', 'opcode_dp_imm', '?']
    hw: ['0', 'hw', '?']

- Name: "MOVN_X_V0"
  Mnemonic: "MOVN"
  Description: "Move Wide with NOT (64-bit)"
  Opcode: "1000"
  Format: "MOVE_WIDE"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_imm: ['0', 'opcode_dp_imm', '?']
    hw: ['0', 'hw', '?']

# Multiply/Divide
- Name: "MUL_X_V0"
  Mnemonic: "MUL"
  Description: "Multiply (64-bit)"
  Opcode: "11011010"
  Format: "MUL_DIV"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_reg: ['0', 'opcode_dp_reg', '?']

- Name: "SDIV_X_V0"
  Mnemonic: "SDIV"
  Description: "Signed Divide (64-bit)"
  Opcode: "11011010"
  Format: "MUL_DIV"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_reg: ['3', 'opcode_dp_reg', '?']

- Name: "UDIV_X_V0"
  Mnemonic: "UDIV"
  Description: "Unsigned Divide (64-bit)"
  Opcode: "11011010"
  Format: "MUL_DIV"
  Operands:
    sf: ['1', 'sf', '?']
    opcode_dp_reg: ['2', 'opcode_dp_reg', '?']
```

### 5.2 加载存储指令

```yaml
# Load Instructions
- Name: "LDR_X_V0"
  Mnemonic: "LDR"
  Description: "Load Register (64-bit, immediate)"
  Opcode: "1110"
  Format: "LOAD_STORE_IMM"
  Operands:
    size: ['3', 'size', '?']
    opcode_ls: ['1', 'opcode_ls', '?']
    V: ['0', 'V', '?']

- Name: "LDUR_X_V0"
  Mnemonic: "LDUR"
  Description: "Load Register (64-bit, unscaled)"
  Opcode: "1110"
  Format: "LOAD_STORE_IMM"
  Operands:
    size: ['3', 'size', '?']
    opcode_ls: ['0', 'opcode_ls', '?']
    V: ['0', 'V', '?']

- Name: "LDP_X_V0"
  Mnemonic: "LDP"
  Description: "Load Pair (64-bit)"
  Opcode: "1010"
  Format: "LOAD_STORE_PAIR"
  Operands:
    L: ['1', 'L', '?']

# Store Instructions
- Name: "STR_X_V0"
  Mnemonic: "STR"
  Description: "Store Register (64-bit, immediate)"
  Opcode: "1110"
  Format: "LOAD_STORE_IMM"
  Operands:
    size: ['3', 'size', '?']
    opcode_ls: ['0', 'opcode_ls', '?']
    V: ['0', 'V', '?']

- Name: "STUR_X_V0"
  Mnemonic: "STUR"
  Description: "Store Register (64-bit, unscaled)"
  Opcode: "1110"
  Format: "LOAD_STORE_IMM"
  Operands:
    size: ['3', 'size', '?']
    opcode_ls: ['0', 'opcode_ls', '?']
    V: ['0', 'V', '?']

- Name: "STP_X_V0"
  Mnemonic: "STP"
  Description: "Store Pair (64-bit)"
  Opcode: "1010"
  Format: "LOAD_STORE_PAIR"
  Operands:
    L: ['0', 'L', '?']
```

### 5.3 分支指令

```yaml
# Unconditional Branch
- Name: "B_V0"
  Mnemonic: "B"
  Description: "Branch (unconditional)"
  Opcode: "0001"
  Format: "UNCOND_BRANCH_IMM"

- Name: "BL_V0"
  Mnemonic: "BL"
  Description: "Branch with Link"
  Opcode: "1001"
  Format: "UNCOND_BRANCH_IMM"
  ImplicitOperands:
    LR: ['LR', 'O']

- Name: "BR_V0"
  Mnemonic: "BR"
  Description: "Branch to Register"
  Opcode: "1101"
  Format: "UNCOND_BRANCH_REG"

- Name: "BLR_V0"
  Mnemonic: "BLR"
  Description: "Branch with Link to Register"
  Opcode: "1101"
  Format: "UNCOND_BRANCH_REG"
  ImplicitOperands:
    LR: ['LR', 'O']

- Name: "RET_V0"
  Mnemonic: "RET"
  Description: "Return from Subroutine"
  Opcode: "1101"
  Format: "UNCOND_BRANCH_REG"
  Operands:
    Rn: ['30', 'Rn', 'I']

# Conditional Branch
- Name: "B_COND_V0"
  Mnemonic: "B."
  Description: "Branch Conditional"
  Opcode: "0101"
  Format: "COND_BRANCH_IMM"

- Name: "CBZ_X_V0"
  Mnemonic: "CBZ"
  Description: "Compare and Branch on Zero (64-bit)"
  Opcode: "0110"
  Format: "COMPARE_BRANCH"
  Operands:
    sf: ['1', 'sf', '?']

- Name: "CBNZ_X_V0"
  Mnemonic: "CBNZ"
  Description: "Compare and Branch on Non-Zero (64-bit)"
  Opcode: "0111"
  Format: "COMPARE_BRANCH"
  Operands:
    sf: ['1', 'sf', '?']

- Name: "TBZ_V0"
  Mnemonic: "TBZ"
  Description: "Test and Branch on Zero"
  Opcode: "0110"
  Format: "TEST_BRANCH"

- Name: "TBNZ_V0"
  Mnemonic: "TBNZ"
  Description: "Test and Branch on Non-Zero"
  Opcode: "0111"
  Format: "TEST_BRANCH"
```

---

## 六、操作数定义设计

### 6.1 操作数定义 (operand.yaml)

```yaml
# Register Operands

- Name: GPR64_regs
  Description: 64-bit General Purpose Registers
  Registers:
    X0 : ['X0']
    X1 : ['X1']
    X2 : ['X2']
    # ... X3-X30
    X30: ['X30']

- Name: GPR32_regs
  Description: 32-bit General Purpose Registers
  Registers:
    W0 : ['W0']
    W1 : ['W1']
    W2 : ['W2']
    # ... W3-W30
    W30: ['W30']

- Name: SIMD_FP_regs
  Description: SIMD/Floating Point Registers
  Registers:
    V0 : ['V0']
    V1 : ['V1']
    # ... V2-V31
    V31: ['V31']

- Name: D_regs
  Description: Double Precision Registers
  Registers:
    D0 : ['D0']
    D1 : ['D1']
    # ... D2-D31
    D31: ['D31']

- Name: S_regs
  Description: Single Precision Registers
  Registers:
    S0 : ['S0']
    S1 : ['S1']
    # ... S2-S31
    S31: ['S31']

# Immediate Operands

- Name: u.imm5
  Description: Unsigned 5-bit Immediate
  Min: 0
  Max: 31

- Name: u.imm12
  Description: Unsigned 12-bit Immediate
  Min: 0
  Max: 4095

- Name: u.imm16
  Description: Unsigned 16-bit Immediate
  Min: 0
  Max: 65535

- Name: s.imm7
  Description: Signed 7-bit Immediate
  Min: -64
  Max: 63

- Name: s.imm9
  Description: Signed 9-bit Immediate
  Min: -256
  Max: 255

- Name: s.imm19_shift2
  Description: Signed 19-bit Immediate (shifted left 2)
  Min: -262144
  Max: 262143
  Shift: 2
  Relative: True

- Name: s.imm26_shift2
  Description: Signed 26-bit Immediate (shifted left 2)
  Min: -33554432
  Max: 33554431
  Shift: 2
  Relative: True

# Condition Codes

- Name: condition_codes
  Description: Condition Codes
  Values:
  - 0   # EQ (Equal)
  - 1   # NE (Not Equal)
  - 2   # CS/HS (Carry Set/Unsigned Higher or Same)
  - 3   # CC/LO (Carry Clear/Unsigned Lower)
  - 4   # MI (Minus/Negative)
  - 5   # PL (Plus/Positive or Zero)
  - 6   # VS (Overflow)
  - 7   # VC (No Overflow)
  - 8   # HI (Unsigned Higher)
  - 9   # LS (Unsigned Lower or Same)
  - 10  # GE (Signed Greater or Equal)
  - 11  # LT (Signed Less Than)
  - 12  # GT (Signed Greater Than)
  - 13  # LE (Signed Less or Equal)
  - 14  # AL (Always)
  - 15  # NV (Never)

# Shift Types

- Name: shift_types
  Description: Shift Types
  Values:
  - 0  # LSL (Logical Shift Left)
  - 1  # LSR (Logical Shift Right)
  - 2  # ASR (Arithmetic Shift Right)
  - 3  # ROR (Rotate Right)

# Extend Types

- Name: extend_types
  Description: Extend Types
  Values:
  - 0  # UXTB (Unsigned Extend Byte)
  - 1  # UXTH (Unsigned Extend Halfword)
  - 2  # UXTW (Unsigned Extend Word)
  - 3  # UXTX (Unsigned Extend Doubleword)
  - 4  # SXTB (Signed Extend Byte)
  - 5  # SXTH (Signed Extend Halfword)
  - 6  # SXTW (Signed Extend Word)
  - 7  # SXTX (Signed Extend Doubleword)

# Option Values (for load/store)

- Name: option_values
  Description: Option Values
  Values:
  - 0  # UXTW
  - 2  # UXTX
  - 3  # SXTW
  - 6  # SXTX
```

---

## 七、ISA类实现设计

### 7.1 ISA类 (isa.py)

```python
# Copyright 2026
# Licensed under Apache License 2.0

from __future__ import absolute_import, print_function

import os
from microprobe.code.address import Address, InstructionAddress
from microprobe.code.ins import Instruction
from microprobe.code.var import Variable, VariableArray
from microprobe.exceptions import MicroprobeCodeGenerationError
from microprobe.target.isa import GenericISA
from microprobe.target.isa.register import Register
from microprobe.utils.logger import get_logger

__all__ = ["Arm64ISA"]
LOG = get_logger(__name__)
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


class Arm64ISA(GenericISA):
    """ARM64 (AArch64) Instruction Set Architecture."""
    
    def __init__(self, name, descr, path, ins, regs, comparators, generators):
        super(Arm64ISA, self).__init__(
            name, descr, path, ins, regs, comparators, generators
        )
        
        # Scratch registers for code generation
        self._scratch_registers += [
            self.registers["X9"],
            self.registers["X10"],
            self.registers["X11"],
            self.registers["X12"],
            self.registers["X13"],
            self.registers["X14"],
            self.registers["X15"],
            self.registers["V16"],
            self.registers["V17"],
            self.registers["V18"],
            self.registers["V19"],
            self.registers["V20"],
            self.registers["V21"],
            self.registers["V22"],
            self.registers["V23"],
            self.registers["V24"],
            self.registers["V25"],
            self.registers["V26"],
            self.registers["V27"],
            self.registers["V28"],
            self.registers["V29"],
            self.registers["V30"],
            self.registers["V31"],
        ]
        
        # Control registers
        self._control_registers += [
            self.registers["NZCV"],
            self.registers["FPCR"],
            self.registers["FPSR"],
            self.registers["SP"],
            self.registers["PC"],
        ]
    
    def set_register(self, register, value, context, opt=True):
        """Set a register to a specific value."""
        LOG.debug("Setting '%s' to value '%s'", register, value)
        instrs = []
        
        current_value = context.get_register_value(register)
        
        if context.register_has_value(value):
            present_reg = context.registers_get_value(value)[0]
            if present_reg.name != register.name:
                mov_ins = self.new_instruction("MOV_X_V0")
                mov_ins.set_operands([register, present_reg])
                instrs.append(mov_ins)
                return instrs
        
        if isinstance(value, int):
            instrs.extend(self._set_register_immediate(register, value))
        elif isinstance(value, Address):
            instrs.extend(self._set_register_address(register, value))
        else:
            raise MicroprobeCodeGenerationError(
                f"Unsupported value type for register: {type(value)}"
            )
        
        return instrs
    
    def _set_register_immediate(self, register, value):
        """Set register to an immediate value."""
        instrs = []
        
        if value == 0:
            # Use MOV to zero register
            mov_ins = self.new_instruction("MOV_X_V0")
            mov_ins.set_operands([register, self.registers["XZR"]])
            instrs.append(mov_ins)
        elif -65536 <= value <= 65535:
            # Use MOVZ/MOVN
            if value >= 0:
                mov_ins = self.new_instruction("MOVZ_X_V0")
                mov_ins.set_operands([register, value, 0])
            else:
                mov_ins = self.new_instruction("MOVN_X_V0")
                mov_ins.set_operands([register, ~value, 0])
            instrs.append(mov_ins)
        else:
            # Use multiple MOVK instructions
            mov_ins = self.new_instruction("MOVZ_X_V0")
            mov_ins.set_operands([register, value & 0xFFFF, 0])
            instrs.append(mov_ins)
            
            for shift in [16, 32, 48]:
                imm = (value >> shift) & 0xFFFF
                if imm != 0:
                    movk_ins = self.new_instruction("MOVK_X_V0")
                    movk_ins.set_operands([register, imm, shift // 16])
                    instrs.append(movk_ins)
        
        return instrs
    
    def _set_register_address(self, register, address):
        """Set register to an address."""
        instrs = []
        
        # Use ADRP + ADD for PC-relative addressing
        # This will be resolved later during address assignment
        
        adrp_ins = self.new_instruction("ADRP_X_V0")
        adrp_ins.set_operands([register, address])
        instrs.append(adrp_ins)
        
        add_ins = self.new_instruction("ADD_X_V0")
        add_ins.set_operands([register, register, address])
        instrs.append(add_ins)
        
        return instrs
    
    def get_context(self):
        """Get context setup instructions."""
        return []
    
    @property
    def little_endian(self):
        """ARM64 is little-endian by default."""
        return True
```

---

## 八、环境定义设计

### 8.1 Linux环境 (aarch64_linux_gcc.py)

```python
# Copyright 2026
# Licensed under Apache License 2.0

from __future__ import absolute_import

from microprobe.code.address import InstructionAddress
from microprobe.target.env import GenericEnvironment


__all__ = ["aarch64_linux_gcc"]


class aarch64_linux_gcc(GenericEnvironment):
    """ARM64 Linux environment with GCC."""
    
    def __init__(self, isa):
        super(aarch64_linux_gcc, self).__init__(
            "aarch64_linux_gcc",
            "ARM64 architecture (AArch64), Linux OS, GCC compiler",
            isa,
            little_endian=True
        )
        self._default_wrapper = "CWrapper"
    
    @property
    def stack_pointer(self):
        """Stack pointer register."""
        return self.isa.registers["SP"]
    
    @property
    def stack_direction(self):
        """Stack grows downward."""
        return "decrease"
    
    def elf_abi(self, stack_size, start_symbol, **kwargs):
        """ELF ABI configuration."""
        return super(aarch64_linux_gcc, self).elf_abi(
            stack_size,
            start_symbol,
            stack_alignment=16,
            **kwargs
        )
    
    def function_call(self, target, return_address_reg=None, long_jump=False):
        """Generate function call instructions."""
        if return_address_reg is None:
            return_address_reg = self.target.isa.registers["LR"]
        
        if isinstance(target, str):
            target = InstructionAddress(base_address=target)
        
        bl_ins = self.target.new_instruction("BL_V0")
        bl_ins.set_operands([target])
        
        return [bl_ins]
    
    def function_return(self, return_address_reg=None):
        """Generate function return instructions."""
        if return_address_reg is None:
            return_address_reg = self.target.isa.registers["LR"]
        
        ret_ins = self.target.new_instruction("RET_V0")
        ret_ins.set_operands([return_address_reg])
        
        return [ret_ins]
    
    @property
    def volatile_registers(self):
        """Return list of volatile (caller-saved) registers."""
        rlist = []
        
        # Volatile GPRs: X0-X18
        for idx in range(0, 19):
            rlist.append(self.target.registers[f'X{idx}'])
        
        # Volatile SIMD/FP: V0-V7, V16-V31
        for idx in list(range(0, 8)) + list(range(16, 32)):
            rlist.append(self.target.registers[f'V{idx}'])
        
        return rlist
```

---

## 九、SDC检测策略设计

### 9.1 SDC检测策略 (sdc_detect.py)

```python
# Copyright 2026
# Licensed under Apache License 2.0

"""
SDC (Silent Data Corruption) Detection Policy for ARM64
"""

from __future__ import absolute_import

import microprobe.code
import microprobe.passes.address
import microprobe.passes.branch
import microprobe.passes.initialization
import microprobe.passes.instruction
import microprobe.passes.memory
import microprobe.passes.register
import microprobe.passes.structure
from microprobe.exceptions import MicroprobePolicyError
from microprobe.utils.logger import get_logger
from microprobe.utils.misc import RND, RNDINT

__all__ = ["NAME", "DESCRIPTION", "SUPPORTED_TARGETS", "policy"]

NAME = "sdc_detect"
DESCRIPTION = "SDC detection policy for ARM64"
SUPPORTED_TARGETS = ["armv8-common-cortex-a53-aarch64_linux_gcc"]

LOG = get_logger(__name__)


def policy(target, wrapper, **kwargs):
    """
    SDC detection benchmark generation policy.
    
    This policy generates test sequences designed to detect silent data
    corruption in ARM64 systems.
    """
    
    if target.name not in SUPPORTED_TARGETS:
        raise MicroprobePolicyError(
            f"Policy '{NAME}' not valid for target '{target.name}'. "
            f"Supported targets: {','.join(SUPPORTED_TARGETS)}"
        )
    
    instr = kwargs["instruction"]
    sequence = [kwargs["instruction"]]
    
    synthesizer = microprobe.code.Synthesizer(target, wrapper, value=RNDINT)
    
    # Initialize registers with known values
    synthesizer.add_pass(
        microprobe.passes.initialization.InitializeRegistersPass(value=RNDINT)
    )
    
    # Initialize floating point registers
    synthesizer.add_pass(
        microprobe.passes.initialization.InitializeRegistersPass(
            fp_value=1.000000000000001
        )
    )
    
    # Create test structure
    synthesizer.add_pass(
        microprobe.passes.structure.SimpleBuildingBlockPass(
            kwargs["benchmark_size"]
        )
    )
    
    # Set instruction sequence
    synthesizer.add_pass(
        microprobe.passes.instruction.SetInstructionTypeBySequencePass(
            sequence
        )
    )
    
    # Update addresses
    synthesizer.add_pass(
        microprobe.passes.address.UpdateInstructionAddressesPass()
    )
    
    # Add SDC detection checks
    # 1. Checksum verification
    # 2. Redundant computation
    # 3. Boundary checks
    
    # Branch to next
    synthesizer.add_pass(microprobe.passes.branch.BranchNextPass())
    
    # Memory initialization
    synthesizer.add_pass(
        microprobe.passes.memory.DefineDataSegmentPass(
            kwargs.get("data_size", 1024),
            kwargs.get("data_value", 0)
        )
    )
    
    # Register allocation
    synthesizer.add_pass(
        microprobe.passes.register.AllocateRegistersPass()
    )
    
    return synthesizer


def generate_sdc_test_sequence(target, instruction, test_type="checksum"):
    """
    Generate SDC detection test sequence.
    
    Args:
        target: Target object
        instruction: Instruction to test
        test_type: Type of SDC test (checksum, redundant, boundary)
    
    Returns:
        List of instructions for SDC detection
    """
    
    instrs = []
    
    if test_type == "checksum":
        # Generate checksum-based SDC detection
        instrs.extend(_generate_checksum_test(target, instruction))
    elif test_type == "redundant":
        # Generate redundant computation test
        instrs.extend(_generate_redundant_test(target, instruction))
    elif test_type == "boundary":
        # Generate boundary check test
        instrs.extend(_generate_boundary_test(target, instruction))
    
    return instrs


def _generate_checksum_test(target, instruction):
    """Generate checksum-based SDC detection."""
    instrs = []
    
    # Initialize checksum register
    checksum_reg = target.registers["X9"]
    mov_ins = target.new_instruction("MOV_X_V0")
    mov_ins.set_operands([checksum_reg, 0])
    instrs.append(mov_ins)
    
    # Add test instruction
    instrs.append(instruction)
    
    # Update checksum
    add_ins = target.new_instruction("ADD_X_V0")
    add_ins.set_operands([checksum_reg, checksum_reg, checksum_reg])
    instrs.append(add_ins)
    
    # Verify checksum (will be done by wrapper)
    
    return instrs


def _generate_redundant_test(target, instruction):
    """Generate redundant computation test."""
    instrs = []
    
    # Execute instruction twice and compare results
    instrs.append(instruction)
    
    # Save result
    save_reg = target.registers["X10"]
    mov_ins = target.new_instruction("MOV_X_V0")
    mov_ins.set_operands([save_reg, target.registers["X0"]])
    instrs.append(mov_ins)
    
    # Execute again
    instrs.append(instruction)
    
    # Compare
    cmp_ins = target.new_instruction("SUBS_X_V0")
    cmp_ins.set_operands([
        target.registers["XZR"],
        target.registers["X0"],
        save_reg
    ])
    instrs.append(cmp_ins)
    
    return instrs


def _generate_boundary_test(target, instruction):
    """Generate boundary check test."""
    instrs = []
    
    # Test with boundary values
    boundary_values = [0, 1, -1, 0x7FFFFFFFFFFFFFFF, 0x8000000000000000]
    
    for value in boundary_values:
        # Set input value
        set_instrs = target.isa.set_register(
            target.registers["X0"],
            value,
            microprobe.code.context.Context()
        )
        instrs.extend(set_instrs)
        
        # Execute instruction
        instrs.append(instruction)
        
        # Check result validity
        # (wrapper will add verification code)
    
    return instrs
```

---

## 十、实现优先级和里程碑

### 10.1 第一阶段：基础框架（2周）

**目标**: 建立ARM64目标的基础结构

**任务**:
1. 创建目录结构
2. 实现寄存器定义
3. 实现寄存器类型定义
4. 实现基础ISA类
5. 创建基础测试框架

**交付物**:
- 完整的目录结构
- 寄存器定义YAML文件
- 基础ISA类实现
- 单元测试框架

### 10.2 第二阶段：核心指令（3周）

**目标**: 实现ARM64核心指令集

**任务**:
1. 定义指令格式和字段
2. 实现数据处理指令（ADD, SUB, MUL, DIV等）
3. 实现逻辑指令（AND, ORR, EOR等）
4. 实现加载存储指令（LDR, STR, LDP, STP等）
5. 实现分支指令（B, BL, BR, RET等）
6. 实现操作数定义

**交付物**:
- 指令格式定义YAML
- 指令字段定义YAML
- 核心指令定义YAML
- 操作数定义YAML
- 指令编码测试

### 10.3 第三阶段：浮点和SIMD（2周）

**目标**: 实现浮点和SIMD指令

**任务**:
1. 实现浮点寄存器定义
2. 实现浮点指令（FADD, FSUB, FMUL, FDIV等）
3. 实现NEON SIMD指令
4. 实现浮点/SIMD操作数

**交付物**:
- 浮点指令定义
- SIMD指令定义
- 浮点/SIMD测试

### 10.4 第四阶段：系统和扩展指令（2周）

**目标**: 实现系统和扩展指令

**任务**:
1. 实现系统指令（MRS, MSR等）
2. 实现原子指令（LDADD, CAS等）
3. 实现加密指令（AES, SHA等）
4. 实现特权指令

**交付物**:
- 系统指令定义
- 原子指令定义
- 扩展指令定义

### 10.5 第五阶段：环境和策略（1周）

**目标**: 实现执行环境和代码生成策略

**任务**:
1. 实现Linux/ARM64环境
2. 实现C代码包装器
3. 实现汇编包装器
4. 实现代码生成策略

**交付物**:
- 环境定义
- 包装器实现
- 策略实现

### 10.6 第六阶段：SDC检测（2周）

**目标**: 实现SDC检测用例生成

**任务**:
1. 设计SDC检测策略
2. 实现校验和检测
3. 实现冗余计算检测
4. 实现边界检查
5. 创建SDC测试模板

**交付物**:
- SDC检测策略
- SDC测试模板
- SDC检测文档

### 10.7 第七阶段：测试和验证（2周）

**目标**: 全面测试和验证

**任务**:
1. 编写单元测试
2. 编写集成测试
3. 在QEMU上测试
4. 在真实硬件上测试
5. 性能基准测试

**交付物**:
- 测试套件
- 测试报告
- 性能基准

### 10.8 第八阶段：文档和发布（1周）

**目标**: 完善文档并发布

**任务**:
1. 编写用户文档
2. 编写开发者文档
3. 创建示例
4. 代码审查
5. 发布准备

**交付物**:
- 用户文档
- 开发者文档
- 示例代码
- 发布包

---

## 十一、测试策略

### 11.1 单元测试

**指令编码测试**:
- 验证每条指令的二进制编码
- 测试所有操作数组合
- 验证边界条件

**寄存器测试**:
- 验证寄存器定义
- 测试寄存器分配
- 验证寄存器访问

**代码生成测试**:
- 验证指令序列生成
- 测试寄存器分配算法
- 验证地址解析

### 11.2 集成测试

**端到端测试**:
- 生成完整测试程序
- 在QEMU上执行
- 验证输出正确性

**跨平台测试**:
- 在不同ARM64处理器上测试
- 验证兼容性

### 11.3 SDC检测测试

**注入测试**:
- 注入错误数据
- 验证SDC检测机制
- 测试检测覆盖率

---

## 十二、风险和缓解

### 12.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 指令编码复杂 | 高 | 参考ARM官方文档，使用验证工具 |
| 寄存器模型差异 | 中 | 详细对比ARM64与其他架构 |
| 测试覆盖不足 | 高 | 建立完善的测试框架 |
| 性能问题 | 中 | 优化代码生成算法 |

### 12.2 进度风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 时间估算不准 | 中 | 预留缓冲时间 |
| 依赖问题 | 低 | 提前识别依赖 |
| 资源不足 | 中 | 合理分配资源 |

---

## 更新日志

- 2026-03-26: 创建ARM64移植详细设计文档
