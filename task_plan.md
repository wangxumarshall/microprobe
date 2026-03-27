# Microprobe ARM64移植任务规划

## 当前审计会话：2026-03-27 SDC Fuzzing闭环修复与提交准备

### 目标
围绕 ARM64/Kunpeng920 SDC fuzzing 主线，完成可导入 target、可运行 policy、可生成差分 wrapper、可对接 McPAT 的关键修复；同步记录 findings，并准备按仓库提交远端。

### 本轮阶段
- [x] 读取仓库状态与远端边界
- [x] 记录高优先级 findings 并收敛执行计划
- [x] 修复 ARM64 target import 与 ISA helper 阻塞项
- [x] 修复 `sdc_fuzzing` / `sdc_detect` 合成主链
- [x] 修复 ARM64 memory stream 地址物化与原子/访存元数据
- [x] 验证 `BareMetalDiffWrapper` 与差分 runner 关键入口
- [x] 让离线生成器在输出 `.c` 时写回 `source_path` / `rendered_path` metadata
- [x] 为 `mp_sdc_offline_gen.py` 补充 focused pytest 覆盖
- [ ] 清理提交边界并提交 `microprobe`

### 当前结论
1. `armv8_common-armv8_common-aarch64_linux_gcc` 现在可以成功 `import_definition(...)`。
2. `targets/arm64/policies/sdc_fuzzing_policy.py` 现在可以成功 `synthesize()`，并生成包含 `FMA + LDP/STP + CAS/LSE` 的混合高风险序列。
3. `targets/arm64/policies/sdc_detect.py` 现在也可完成最小合成。
4. `BareMetalDiffWrapper` 在绑定真实 benchmark 后可以生成 digest 代码。
5. `targets/generic/tools/mp_sdc_offline_gen.py` 现在会在输出 `.c` 时把 `source_path` 与 `rendered_path` 写回 testcase metadata，便于根目录 campaign 直接消费。
6. 仍需收尾的主要问题不在 ARM64 主链本身，而在提交边界与外部环境：
   - 根目录 `run_sdc_differential.py` / `sdc_vault.py` 不在任何 git repo 内，无法直接推送到现有远端。
   - `pytest` 本地缺少 `typeguard` 依赖，当前只能用 focused smoke tests 验证。
   - `mcpat/mcpat` 仓库没有现成 gem5 `config.json + stats.txt` 样例，McPAT 默认链本轮只能做代码与接口级复核。

## 当前审计会话：2026-03-26 ISA准确性/完备性复核

### 目标
基于 ARM ARM A-profile A64 文档递归核查 `targets/arm64` 的 ISA 定义、生成策略和测试覆盖，修正错误或缺漏，并提升指令序列覆盖率与 SDC 检出能力。

### 本轮阶段
- [x] 恢复既有上下文与仓库状态
- [x] 定位 ARM64 目标实现、策略和测试入口
- [ ] 统计现有 ARM64 指令/格式/操作数覆盖面
- [ ] 对照 ARM 官方文档核验编码与分类
- [ ] 修正 ISA 定义与生成策略
- [ ] 运行测试/自检并更新结论

### 当前发现
1. `targets/arm64/` 已经落地，和旧计划中“未开始”的状态不一致。
2. 根目录存在多份“已完成/100%”报告，但尚未核实真实导入能力、编码正确性和覆盖范围。
3. 本轮任务以真实代码和 ARM 官方文档为准，不以仓库内总结性文档为准。

## 项目概述

**目标**: 将Microprobe微基准测试框架从PowerPC/RISC-V架构移植到ARM64 (AArch64)架构，实现对ARMv8指令集的100%支持，并实现SDC（Silent Data Corruption）检测用例生成机制。

**参考文档**: https://developer.arm.com/documentation/102374/latest/

---

## 阶段一：代码架构深度分析 ✅

### 目标
全面理解Microprobe项目的架构设计、核心功能模块及实现逻辑。

### 任务清单
- [x] 分析项目目录结构
- [x] 理解核心模块划分
- [x] 分析ISA定义机制
- [x] 分析指令编码系统
- [x] 理解寄存器定义机制
- [x] 分析代码生成流程
- [x] 理解测试框架结构
- [x] 分析工具链实现

### 关键发现
1. **项目架构**: Microprobe采用模块化设计，核心包含：
   - `src/microprobe/`: 核心框架代码
   - `targets/`: 目标架构定义（PowerPC, RISC-V）
   - `dev_tools/`: 开发工具和CI脚本

2. **ISA定义模式**: 
   - YAML格式定义指令集
   - 支持指令格式、操作数、寄存器的声明式定义
   - 继承机制支持（Extends字段）
   - 指令格式定义：定义二进制编码布局
   - 指令字段定义：定义字段名称、位置、宽度
   - 操作数定义：定义寄存器、立即数等操作数类型

3. **核心组件**:
   - `target/isa/`: 指令集架构定义（instruction.yaml, register.yaml, instruction_format.yaml等）
   - `target/uarch/`: 微架构定义
   - `target/env/`: 执行环境定义（继承GenericEnvironment）
   - `code/`: 代码生成引擎
   - `passes/`: 代码转换pass（初始化、分支、内存、寄存器等）
   - `policies/`: 代码生成策略（epi, seq等）
   - `wrappers/`: 输出包装器（C代码、汇编等）

4. **代码生成流程**:
   - 目标选择 → 策略应用 → 指令选择 → 寄存器分配 → 地址解析 → 二进制生成
   - 使用Synthesizer对象组合多个pass
   - Wrapper负责生成最终输出格式

5. **PowerPC vs RISC-V对比**:
   - PowerPC: 复杂的条件码系统，多种指令格式
   - RISC-V: 规则化的编码，模块化设计
   - 两者都使用YAML声明式定义，便于移植

### 状态: 已完成 ✅

---

## 阶段二：ARM64架构研究 ✅

### 目标
深入研究ARM64 (AArch64)指令集架构，为移植做准备。

### 任务清单
- [x] 获取ARM64指令集完整规范
- [x] 分析ARM64寄存器模型
- [x] 研究ARM64指令编码格式
- [x] 理解ARM64指令分类
- [x] 分析ARM64特权级模型
- [x] 研究ARM64内存模型

### 关键资源
- ARM官方文档: https://developer.arm.com/documentation/102374/latest/
- ARM Architecture Reference Manual ARMv8

### 关键发现
1. **寄存器模型**: 31个通用寄存器 + 32个SIMD/FP寄存器
2. **指令编码**: 32位固定长度，规则化编码
3. **条件码**: NZCV标志，比PowerPC简单
4. **特权级**: EL0-EL3四级模型
5. **零寄存器**: XZR/WZR简化某些操作
6. **SIMD/FP**: 使用相同寄存器组

### 状态: 已完成 ✅

---

## 阶段三：ARM64目标架构实现

### 目标
创建ARM64架构的完整定义，包括指令集、寄存器、指令格式等。

### 子任务

#### 3.1 创建ARM64目标目录结构
- [ ] 创建 `targets/arm64/` 目录
- [ ] 创建子目录结构（isa, uarch, env, policies, wrappers等）

#### 3.2 实现ARM64寄存器定义
- [ ] 定义通用寄存器 (X0-X30, SP, PC)
- [ ] 定义浮点寄存器 (V0-V31)
- [ ] 定义系统寄存器 (SPSR, ELR, etc.)
- [ ] 定义特殊寄存器 (NZCV, FPCR, FPSR)

#### 3.3 实现ARM64指令格式定义
- [ ] 分析ARM64指令编码格式
- [ ] 定义指令字段 (instruction_field.yaml)
- [ ] 定义指令格式 (instruction_format.yaml)

#### 3.4 实现ARM64指令集定义
- [ ] 数据处理指令 (ADD, SUB, MUL, DIV, etc.)
- [ ] 逻辑运算指令 (AND, ORR, EOR, etc.)
- [ ] 移位指令 (LSL, LSR, ASR, ROR)
- [ ] 加载存储指令 (LDR, STR, LDP, STP, etc.)
- [ ] 分支指令 (B, BL, BR, RET, etc.)
- [ ] 条件分支指令 (B.cond, CBNZ, CBZ)
- [ ] 浮点指令 (FADD, FSUB, FMUL, FDIV, etc.)
- [ ] SIMD指令 (NEON指令集)
- [ ] 系统指令 (SVC, HVC, SMC, MSR, MRS)
- [ ] 原子指令 (LDADD, STADD, CAS, etc.)
- [ ] 加密指令 (AES, SHA, etc.)
- [ ] CRC指令

#### 3.5 实现ARM64操作数定义
- [ ] 定义立即数操作数
- [ ] 定义寄存器操作数
- [ ] 定义条件码操作数
- [ ] 定义系统寄存器操作数

#### 3.6 实现ARM64 ISA类
- [ ] 创建 `isa.py` 继承自 `GenericISA`
- [ ] 实现寄存器设置方法
- [ ] 实现指令生成辅助方法

### 状态: 未开始

---

## 阶段四：ARM64微架构定义

### 目标
定义ARM64处理器的微架构特性。

### 任务清单
- [ ] 创建微架构目录结构
- [ ] 定义通用微架构元素
- [ ] 为特定处理器创建定义（如Cortex-A系列）
- [ ] 定义缓存层次结构
- [ ] 定义执行单元

### 状态: 未开始

---

## 阶段五：ARM64环境定义

### 目标
定义ARM64的执行环境。

### 任务清单
- [ ] 创建Linux/ARM64环境定义
- [ ] 实现裸机环境支持
- [ ] 定义ABI规范
- [ ] 实现启动代码

### 状态: 未开始

---

## 阶段六：SDC检测用例生成

### 目标
实现针对ARM64的SDC（Silent Data Corruption）检测用例生成机制。

### 任务清单
- [ ] 研究SDC检测原理
- [ ] 设计SDC检测策略
- [ ] 实现SDC检测策略
- [ ] 创建SDC测试模板
- [ ] 实现SDC用例生成工具

### SDC检测关键点
1. 数据完整性验证
2. 计算结果校验
3. 内存一致性检查
4. 浮点精度验证
5. 并发正确性检测

### 状态: 未开始

---

## 阶段七：测试与验证

### 目标
全面测试ARM64移植的正确性和完整性。

### 任务清单
- [ ] 创建单元测试
- [ ] 创建集成测试
- [ ] 验证指令编码正确性
- [ ] 验证代码生成正确性
- [ ] 在真实ARM64硬件上测试
- [ ] 性能基准测试

### 状态: 未开始

---

## 阶段八：文档与工具

### 目标
完善文档和工具支持。

### 任务清单
- [ ] 编写ARM64移植文档

---

## 阶段九：ARM64 ISA审计与强化 🔄

### 目标
基于 Arm 官方 A64 机器可读规范审计当前实现的准确性与完备性，并优先修复影响覆盖率、可用性和 SDC 检出率的关键缺陷。

### 任务清单
- [x] 获取 Arm 官方 A64 XML 规范数据集
- [x] 量化当前仓库 ARM64 指令覆盖基线
- [x] 识别 helper/policy 直接依赖但缺失的关键指令
- [ ] 补齐关键基础指令与 alias（MOV/ADR/ADRP/NOP 等）
- [ ] 补齐高价值整数/条件选择/位操作指令族
- [ ] 优化 SDC fuzzing 序列生成策略
- [ ] 修复生成流程中的功能性缺陷
- [ ] 完成编码与回归验证

### 关键发现
1. **覆盖率严重不足**: `targets/arm64/isa/armv8-common/instruction.yaml` 当前仅定义 `56` 个 instruction types、`27` 个唯一助记符；而 Arm 官方 A64 XML 中仅 `general + system` 类就有 `462` 个唯一助记符。
2. **可用性缺陷**: `targets/arm64/isa/armv8-common/isa.py` 直接引用了当前未定义的 `MOV_X_V0`、`ADRP_X_V0`、`NOP_V0`，导致寄存器设置、地址构造和 NOP 生成路径不完整。
3. **生成器问题**: `targets/arm64/isa/armv8-common/generator.py` 为空实现；`sdc_fuzzing_generator.py` 当前以随机抽样为主，无法系统覆盖高价值指令组合。
4. **功能性 bug**: `sdc_fuzzing_generator.py` 在 `generate_single_testcase` 中创建了本地 `Synthesizer`，却没有使用 policy 返回的 synthesizer，实际生成路径不正确。
5. **验证阻塞**: 项目在 Python 3.12 下受 `src/microprobe/utils/imp.py` 中 `imp` 模块移除影响，阻碍目标导入与自动化验证。

### 状态: 进行中 🔄
- [ ] 更新用户手册
- [ ] 创建ARM64示例
- [ ] 实现ARM64专用工具
- [ ] CI/CD集成

### 状态: 未开始

---

## 风险与挑战

### 技术风险
1. **指令集复杂度**: ARM64指令集庞大，需要完整覆盖
2. **编码复杂性**: ARM64指令编码规则复杂
3. **特权级模型**: ARM64的多级异常模型
4. **扩展支持**: SVE/SVE2等扩展指令集

### 缓解措施
1. 参考现有PowerPC/RISC-V实现模式
2. 使用ARM官方工具验证编码
3. 分阶段实现，优先核心指令
4. 建立完善的测试框架

---

## 时间估算

| 阶段 | 预计工作量 | 优先级 |
|------|-----------|--------|
| 阶段一：架构分析 | 已完成大部分 | 高 |
| 阶段二：ARM64研究 | 中等 | 高 |
| 阶段三：ISA实现 | 大 | 高 |
| 阶段四：微架构 | 中等 | 中 |
| 阶段五：环境定义 | 小 | 中 |
| 阶段六：SDC检测 | 大 | 高 |
| 阶段七：测试验证 | 大 | 高 |
| 阶段八：文档工具 | 中等 | 低 |

---

## 依赖关系

```
阶段一 (架构分析)
    ↓
阶段二 (ARM64研究) → 阶段三 (ISA实现)
                           ↓
                    阶段四 (微架构) ──┐
                           ↓          │
                    阶段五 (环境定义) ─┤
                           ↓          │
                    阶段六 (SDC检测) ←─┘
                           ↓
                    阶段七 (测试验证)
                           ↓
                    阶段八 (文档工具)
```

---

## 错误记录

| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
| 暂无 | - | - |

---

## 更新日志

- 2026-03-26: 创建任务规划，开始阶段一
