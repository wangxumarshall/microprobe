# ARM64架构支持 - 使用指南

## 概述

Microprobe现已支持ARM64 (AArch64)架构，包括ARMv8指令集的完整实现。本文档介绍如何使用ARM64目标进行代码生成和SDC检测。

## 快速开始

### 1. 导入ARM64目标

```python
from microprobe.target import import_definition

# 导入ARM64目标
target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
```

### 2. 创建指令

```python
# 创建ADD指令
add_instr = target.new_instruction("ADD_X_IMM_V0")
add_instr.set_operands([
    target.registers["X0"],  # 目标寄存器
    target.registers["X1"],  # 源寄存器
    42                        # 立即数
])

# 创建LDR指令
ldr_instr = target.new_instruction("LDR_X_IMM_V0")
ldr_instr.set_operands([
    target.registers["X0"],  # 目标寄存器
    target.registers["X1"],  # 基址寄存器
    16                        # 偏移量
])

# 创建分支指令
b_instr = target.new_instruction("B_V0")
b_instr.set_label("target_label")
```

### 3. 使用SDC检测策略

```python
from microprobe.target.arm64.policies.sdc_detect import policy
from microprobe.code import Synthesizer
from microprobe.target.arm64.env.aarch64_linux_gcc import aarch64_linux_gcc

# 创建环境
target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
env = aarch64_linux_gcc(target.isa)

# 创建synthesizer
synthesizer = Synthesizer(target, env)

# 应用SDC检测策略
kwargs = {
    "instruction": add_instr,
    "benchmark_size": 100,
    "dependency_distance": 1
}

policy(target, env, **kwargs)

# 生成代码
benchmark = synthesizer.generate()
print(benchmark)
```

## 寄存器使用

### 通用寄存器

ARM64提供31个通用寄存器：

- **X0-X30**: 64位通用寄存器
- **W0-W30**: 32位通用寄存器（X寄存器的低32位）
- **XZR/WZR**: 零寄存器（读取总是返回0，写入被忽略）
- **SP**: 栈指针
- **PC**: 程序计数器
- **LR (X30)**: 链接寄存器
- **FP (X29)**: 帧指针

```python
# 访问寄存器
x0 = target.registers["X0"]
w0 = target.registers["W0"]
sp = target.registers["SP"]
lr = target.registers["LR"]
```

### SIMD/浮点寄存器

ARM64提供32个SIMD/浮点寄存器：

- **V0-V31**: 128位SIMD寄存器
- **D0-D31**: 64位浮点寄存器（V寄存器的低64位）
- **S0-S31**: 32位浮点寄存器（V寄存器的低32位）

```python
# 访问SIMD/浮点寄存器
v0 = target.registers["V0"]
d0 = target.registers["D0"]
s0 = target.registers["S0"]
```

### 系统寄存器

```python
# 访问系统寄存器
nzcv = target.registers["NZCV"]  # 条件标志
fpcr = target.registers["FPCR"]  # 浮点控制寄存器
fpsr = target.registers["FPSR"]  # 浮点状态寄存器
```

## 支持的指令

### 数据处理指令

#### 算术运算
- **ADD**: 加法
- **SUB**: 减法
- **MUL**: 乘法
- **SDIV**: 有符号除法
- **UDIV**: 无符号除法

```python
# 加法
add = target.new_instruction("ADD_X_IMM_V0")
add.set_operands([target.registers["X0"], target.registers["X1"], 42])

# 减法
sub = target.new_instruction("SUB_X_IMM_V0")
sub.set_operands([target.registers["X0"], target.registers["X1"], 10])

# 乘法
mul = target.new_instruction("MUL_X_V0")
mul.set_operands([
    target.registers["X0"],
    target.registers["X1"],
    target.registers["X2"]
])
```

#### 逻辑运算
- **AND**: 按位与
- **ORR**: 按位或
- **EOR**: 按位异或

```python
# 逻辑与
and_instr = target.new_instruction("AND_X_REG_V0")
and_instr.set_operands([
    target.registers["X0"],
    target.registers["X1"],
    target.registers["X2"]
])
```

### 加载存储指令

#### 单寄存器
- **LDR**: 加载寄存器
- **STR**: 存储寄存器

```python
# 加载
ldr = target.new_instruction("LDR_X_IMM_V0")
ldr.set_operands([
    target.registers["X0"],  # 目标
    target.registers["X1"],  # 基址
    16                        # 偏移
])

# 存储
str = target.new_instruction("STR_X_IMM_V0")
str.set_operands([
    target.registers["X0"],  # 源
    target.registers["X1"],  # 基址
    16                        # 偏移
])
```

#### 寄存器对
- **LDP**: 加载寄存器对
- **STP**: 存储寄存器对

```python
# 加载对
ldp = target.new_instruction("LDP_X_V0")
ldp.set_operands([
    target.registers["X0"],  # 目标1
    target.registers["X1"],  # 目标2
    target.registers["X2"],  # 基址
    16                        # 偏移
])
```

### 分支指令

#### 无条件分支
- **B**: 无条件分支
- **BL**: 带链接的分支
- **BR**: 寄存器分支
- **BLR**: 带链接的寄存器分支
- **RET**: 返回

```python
# 无条件分支
b = target.new_instruction("B_V0")
b.set_label("target_label")

# 函数调用
bl = target.new_instruction("BL_V0")
bl.set_label("function_name")

# 返回
ret = target.new_instruction("RET_V0")
ret.set_operands([target.registers["LR"]])
```

#### 条件分支
- **B.cond**: 条件分支（EQ, NE, LT, GT等）
- **CBZ**: 比较并分支（为零）
- **CBNZ**: 比较并分支（非零）
- **TBZ**: 测试并分支（为零）
- **TBNZ**: 测试并分支（非零）

```python
# 条件分支
b_eq = target.new_instruction("B_COND_V0")
b_eq.set_operands([0])  # EQ条件
b_eq.set_label("equal_label")

# 比较并分支
cbz = target.new_instruction("CBZ_X_V0")
cbz.set_operands([target.registers["X0"]])
cbz.set_label("zero_label")
```

### 浮点指令

#### 算术运算
- **FADD**: 浮点加法
- **FSUB**: 浮点减法
- **FMUL**: 浮点乘法
- **FDIV**: 浮点除法

```python
# 浮点加法（双精度）
fadd = target.new_instruction("FADD_D_V0")
fadd.set_operands([
    target.registers["D0"],
    target.registers["D1"],
    target.registers["D2"]
])
```

#### 转换
- **FCVT**: 浮点转换
- **FCVTZS**: 浮点转有符号整数
- **FCVTZU**: 浮点转无符号整数
- **SCVTF**: 有符号整数转浮点
- **UCVTF**: 无符号整数转浮点

```python
# 浮点转整数
fcvtzs = target.new_instruction("FCVTZS_D_X_V0")
fcvtzs.set_operands([
    target.registers["X0"],
    target.registers["D0"]
])
```

### 原子指令

- **LDAXR**: 独占加载
- **STLXR**: 独占存储
- **CAS**: 比较并交换
- **LDADD**: 原子加法

```python
# 独占加载
ldaxr = target.new_instruction("LDAXR_X_V0")
ldaxr.set_operands([
    target.registers["X0"],
    target.registers["X1"]
])

# 比较并交换
cas = target.new_instruction("CAS_X_V0")
cas.set_operands([
    target.registers["X0"],
    target.registers["X1"],
    target.registers["X2"]
])
```

## SDC检测功能

### 1. 校验和检测

```python
from microprobe.target.arm64.policies.sdc_detect import _generate_checksum_test

# 为指令生成校验和测试
test_instrs = _generate_checksum_test(target, instruction)
```

### 2. 冗余执行检测

```python
from microprobe.target.arm64.policies.sdc_detect import _generate_redundant_test

# 为指令生成冗余执行测试
test_instrs = _generate_redundant_test(target, instruction)
```

### 3. 边界检查

```python
from microprobe.target.arm64.policies.sdc_detect import _generate_boundary_test

# 为指令生成边界检查测试
test_instrs = _generate_boundary_test(target, instruction)
```

## 代码生成示例

### 示例1：简单循环

```python
from microprobe.target import import_definition
from microprobe.code import Synthesizer
from microprobe.target.arm64.env.aarch64_linux_gcc import aarch64_linux_gcc

# 创建目标
target = import_definition("armv8-common-cortex-a53-aarch64_linux_gcc")
env = aarch64_linux_gcc(target.isa)

# 创建synthesizer
synthesizer = Synthesizer(target, env)

# 创建指令序列
instructions = [
    target.new_instruction("ADD_X_IMM_V0"),
    target.new_instruction("SUB_X_IMM_V0"),
    target.new_instruction("MUL_X_V0"),
]

# 设置操作数
instructions[0].set_operands([target.registers["X0"], target.registers["X1"], 10])
instructions[1].set_operands([target.registers["X2"], target.registers["X3"], 5])
instructions[2].set_operands([
    target.registers["X4"],
    target.registers["X5"],
    target.registers["X6"]
])

# 生成代码
# ... (使用passes)
```

### 示例2：SDC检测测试

```python
from microprobe.target.arm64.policies.sdc_detect import policy

# 创建测试用例
kwargs = {
    "instruction": add_instr,
    "benchmark_size": 100,
    "dependency_distance": 1,
    "data_size": 1024,
}

# 应用策略
policy(target, env, **kwargs)

# 生成代码
benchmark = synthesizer.generate()
print(benchmark)
```

## 输出格式

### C代码输出

```python
from microprobe.code.wrapper import CWrapper

wrapper = CWrapper()
synthesizer = Synthesizer(target, wrapper)

# 生成C代码
c_code = synthesizer.generate()
```

### 汇编输出

```python
from microprobe.code.wrapper import AsmWrapper

wrapper = AsmWrapper()
synthesizer = Synthesizer(target, wrapper)

# 生成汇编代码
asm_code = synthesizer.generate()
```

### 二进制输出

```python
from microprobe.code.wrapper import BinWrapper

wrapper = BinWrapper()
synthesizer = Synthesizer(target, wrapper)

# 生成二进制
binary = synthesizer.generate()
```

## 性能考虑

### 寄存器分配

ARM64有丰富的寄存器资源，但需要注意：

- **X0-X7**: 函数参数
- **X8**: 间接结果
- **X9-X15**: 临时寄存器
- **X16-X17**: IP寄存器
- **X18**: 平台寄存器
- **X19-X28**: 被调用者保存
- **X29 (FP)**: 帧指针
- **X30 (LR)**: 链接寄存器

### 指令调度

考虑指令延迟和吞吐量：

```python
# 设置依赖距离
kwargs["dependency_distance"] = 4  # 4条指令的依赖距离
```

## 故障排查

### 常见问题

1. **寄存器未定义**
   ```
   KeyError: "X32"
   ```
   解决：使用X0-X30，ARM64只有31个通用寄存器

2. **指令编码错误**
   ```
   MicroprobeCodeGenerationError: Invalid immediate
   ```
   解决：检查立即数范围是否符合指令要求

3. **标签未定义**
   ```
   MicroprobeCodeGenerationError: Undefined label
   ```
   解决：确保所有分支目标都有定义

## 参考资料

- [ARM Architecture Reference Manual ARMv8](https://developer.arm.com/documentation/102374/latest/)
- [ARM64指令集指南](https://developer.arm.com/architectures/instruction-sets/instruction-sets/)
- [Microprobe文档](../doc/)

## 支持

如有问题，请提交Issue或Pull Request。
