# SDC-Fuzzing批量生成使用指南

## 概述

本工具用于批量生成海量指令流序列，用于SDC（Silent Data Corruption）检测用例模糊测试。

## 快速开始

### 1. 基本用法

```bash
# 生成1000个基础测试用例
python sdc_fuzzing_generator.py \
    -t power_v207-power8-ppc64_linux_gcc \
    -o ./output \
    -n 1000

# 生成10000个测试用例，每个基础序列生成20个变异体
python sdc_fuzzing_generator.py \
    -t riscv_v22-riscv_generic-riscv64_linux_gcc \
    -o ./output \
    -n 1000 \
    -m 20

# 使用8个并行worker
python sdc_fuzzing_generator.py \
    -t target_name \
    -o ./output \
    -n 10000 \
    -w 8
```

### 2. 高级用法

```bash
# 使用配置文件
python sdc_fuzzing_generator.py \
    -t target_name \
    -o ./output \
    -c config.json

# 设置随机种子（可重现）
python sdc_fuzzing_generator.py \
    -t target_name \
    -o ./output \
    -n 1000 \
    -s 42

# 自定义序列长度和变异率
python sdc_fuzzing_generator.py \
    -t target_name \
    -o ./output \
    -n 1000 \
    -l 20 \
    -L 200 \
    -r 0.5
```

## 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| --target | -t | 目标架构名称 | 必需 |
| --output | -o | 输出目录 | 必需 |
| --num-sequences | -n | 基础序列数量 | 1000 |
| --mutants | -m | 每个基础序列的变异体数量 | 10 |
| --workers | -w | 并行worker数量 | CPU核心数 |
| --length-min | -l | 最小序列长度 | 10 |
| --length-max | -L | 最大序列长度 | 100 |
| --mutation-rate | -r | 变异率 | 0.3 |
| --batch-size | -b | 批处理大小 | 100 |
| --seed | -s | 随机种子 | None |
| --config | -c | 配置文件路径 | None |
| --verbose | -v | 详细输出 | False |

## 配置文件格式

### 完整配置示例 (config.json)

```json
{
  "sequence_length_min": 10,
  "sequence_length_max": 100,
  "num_sequences": 1000,
  "mutation_rate": 0.3,
  "num_mutants_per_base": 10,
  "sdc_detection": [
    "checksum",
    "redundant",
    "boundary",
    "canary"
  ],
  "parallel_workers": 8,
  "batch_size": 100,
  "compress_output": true,
  "seed": 42,
  
  "generation_strategies": {
    "random_combination": {
      "enabled": true,
      "weight": 0.25
    },
    "category_based": {
      "enabled": true,
      "weight": 0.25,
      "categories": [
        "arithmetic",
        "logical",
        "memory",
        "branch",
        "floating",
        "simd"
      ]
    },
    "risk_based": {
      "enabled": true,
      "weight": 0.25,
      "risk_levels": ["low", "medium", "high"]
    },
    "pattern_based": {
      "enabled": true,
      "weight": 0.25,
      "patterns": [
        "memory_intensive",
        "compute_intensive",
        "branch_heavy",
        "mixed"
      ]
    }
  },
  
  "mutation_strategies": {
    "replace": {
      "enabled": true,
      "probability": 0.2
    },
    "insert": {
      "enabled": true,
      "probability": 0.2
    },
    "delete": {
      "enabled": true,
      "probability": 0.15
    },
    "swap": {
      "enabled": true,
      "probability": 0.15
    },
    "duplicate": {
      "enabled": true,
      "probability": 0.15
    },
    "reverse": {
      "enabled": true,
      "probability": 0.15
    }
  },
  
  "sdc_detection_config": {
    "checksum": {
      "enabled": true,
      "algorithm": "crc32",
      "check_interval": 100
    },
    "redundant": {
      "enabled": true,
      "compare_method": "exact"
    },
    "boundary": {
      "enabled": true,
      "min_value": 0,
      "max_value": "UINT64_MAX"
    },
    "canary": {
      "enabled": true,
      "canary_value": "0xDEADBEEFCAFEBABE",
      "positions": ["stack", "heap"]
    }
  }
}
```

### 简化配置示例

```json
{
  "num_sequences": 5000,
  "num_mutants_per_base": 20,
  "sequence_length_min": 50,
  "sequence_length_max": 500,
  "mutation_rate": 0.4,
  "parallel_workers": 16
}
```

## 生成策略详解

### 1. 随机组合策略

从所有可用指令中随机选择，生成多样化的序列。

**适用场景**:
- 探索性测试
- 发现意外错误
- 覆盖率测试

**配置**:
```json
{
  "generation_strategies": {
    "random_combination": {
      "enabled": true,
      "weight": 0.3
    }
  }
}
```

### 2. 类别策略

按指令功能类别生成序列，专注于特定类型的指令。

**类别**:
- `arithmetic`: 算术指令 (ADD, SUB, MUL, DIV)
- `logical`: 逻辑指令 (AND, ORR, EOR)
- `memory`: 内存指令 (LDR, STR, LDP, STP)
- `branch`: 分支指令 (B, BL, BR, RET)
- `floating`: 浮点指令 (FADD, FSUB, FMUL)
- `simd`: SIMD指令 (NEON)

**配置**:
```json
{
  "generation_strategies": {
    "category_based": {
      "enabled": true,
      "weight": 0.3,
      "categories": ["memory", "arithmetic"]
    }
  }
}
```

### 3. 风险等级策略

按指令风险等级生成序列，重点测试高风险指令。

**风险等级**:
- `low`: 低风险（普通算术逻辑指令）
- `medium`: 中风险（多寄存器操作、带屏障操作）
- `high`: 高风险（原子操作、系统指令、特权指令）

**配置**:
```json
{
  "generation_strategies": {
    "risk_based": {
      "enabled": true,
      "weight": 0.3,
      "risk_levels": ["high", "medium"]
    }
  }
}
```

### 4. 模式策略

生成特定模式的指令序列。

**模式**:
- `memory_intensive`: 内存密集型（大量加载存储）
- `compute_intensive`: 计算密集型（大量算术运算）
- `branch_heavy`: 分支密集型（大量分支跳转）
- `mixed`: 混合模式

**配置**:
```json
{
  "generation_strategies": {
    "pattern_based": {
      "enabled": true,
      "weight": 0.2,
      "patterns": ["memory_intensive", "compute_intensive"]
    }
  }
}
```

## 变异策略详解

### 1. 替换变异 (Replace)

随机选择一条指令，替换为另一条指令。

```
原始: ADD X0, X1, X2
      SUB X3, X4, X5
      MUL X6, X7, X8

变异: ADD X0, X1, X2
      LDR X3, [X4]     <- 替换
      MUL X6, X7, X8
```

### 2. 插入变异 (Insert)

在随机位置插入一条新指令。

```
原始: ADD X0, X1, X2
      SUB X3, X4, X5

变异: ADD X0, X1, X2
      MUL X6, X7, X8   <- 插入
      SUB X3, X4, X5
```

### 3. 删除变异 (Delete)

随机删除一条指令。

```
原始: ADD X0, X1, X2
      SUB X3, X4, X5
      MUL X6, X7, X8

变异: ADD X0, X1, X2
      MUL X6, X7, X8   <- 删除了SUB
```

### 4. 交换变异 (Swap)

随机交换两条指令的位置。

```
原始: ADD X0, X1, X2
      SUB X3, X4, X5
      MUL X6, X7, X8

变异: MUL X6, X7, X8   <- 交换
      SUB X3, X4, X5
      ADD X0, X1, X2   <- 交换
```

### 5. 复制变异 (Duplicate)

随机复制一条指令。

```
原始: ADD X0, X1, X2
      SUB X3, X4, X5

变异: ADD X0, X1, X2
      ADD X0, X1, X2   <- 复制
      SUB X3, X4, X5
```

### 6. 反转变异 (Reverse)

反转一个子序列。

```
原始: ADD X0, X1, X2
      SUB X3, X4, X5
      MUL X6, X7, X8
      DIV X9, X10, X11

变异: ADD X0, X1, X2
      DIV X9, X10, X11 <- 反转
      MUL X6, X7, X8   <- 反转
      SUB X3, X4, X5   <- 反转
```

## SDC检测机制

### 1. 校验和检测 (Checksum)

在代码执行过程中计算校验和，定期验证数据完整性。

```c
// 初始化
uint64_t checksum = 0;

// 执行过程中更新
checksum = update_checksum(checksum, data);

// 验证
if (checksum != expected_checksum) {
    report_sdc_error();
}
```

**配置**:
```json
{
  "sdc_detection_config": {
    "checksum": {
      "enabled": true,
      "algorithm": "crc32",
      "check_interval": 100
    }
  }
}
```

### 2. 冗余执行检测 (Redundant Execution)

同一段代码执行两次，比较结果。

```c
uint64_t result1 = execute_critical_section();
uint64_t result2 = execute_critical_section();

if (result1 != result2) {
    report_sdc_error();
}
```

**配置**:
```json
{
  "sdc_detection_config": {
    "redundant": {
      "enabled": true,
      "compare_method": "exact"
    }
  }
}
```

### 3. 边界检查 (Boundary Check)

检查计算结果是否在合理范围内。

```c
if (result < MIN_EXPECTED || result > MAX_EXPECTED) {
    report_sdc_error();
}
```

**配置**:
```json
{
  "sdc_detection_config": {
    "boundary": {
      "enabled": true,
      "min_value": 0,
      "max_value": "UINT64_MAX"
    }
  }
}
```

### 4. 内存金丝雀 (Memory Canary)

在内存关键位置放置金丝雀值，检测内存损坏。

```c
volatile uint64_t canary = 0xDEADBEEFCAFEBABE;

// ... critical code ...

if (canary != 0xDEADBEEFCAFEBABE) {
    report_sdc_error();
}
```

**配置**:
```json
{
  "sdc_detection_config": {
    "canary": {
      "enabled": true,
      "canary_value": "0xDEADBEEFCAFEBABE",
      "positions": ["stack", "heap"]
    }
  }
}
```

## 输出文件结构

```
output/
├── config.json                    # 生成配置
├── generation_report.json         # 生成报告
├── sdc_test_000001_a1b2c3d4.c     # 测试用例
├── sdc_test_000002_e5f6g7h8.c
├── sdc_test_000003_i9j0k1l2.c
├── ...
└── failed/
    ├── sdc_test_000123_failed.log # 失败日志
    └── ...
```

### 生成报告示例

```json
{
  "target": "power_v207-power8-ppc64_linux_gcc",
  "output_dir": "./output",
  "statistics": {
    "base_sequences": 1000,
    "total_sequences": 11000,
    "generated": 10890,
    "failed": 110,
    "success_rate": 0.99
  },
  "timing": {
    "start_time": "2026-03-26T12:00:00",
    "end_time": "2026-03-26T12:30:00",
    "duration_seconds": 1800,
    "sequences_per_second": 6.11
  }
}
```

## 性能优化建议

### 1. 并行化

```bash
# 使用更多worker
python sdc_fuzzing_generator.py ... -w 32

# 调整批处理大小
python sdc_fuzzing_generator.py ... -b 200
```

### 2. 内存优化

```json
{
  "batch_size": 50,
  "compress_output": true,
  "streaming_mode": true
}
```

### 3. 分布式生成

```bash
# 在多台机器上并行生成
# 机器1
python sdc_fuzzing_generator.py ... -s 1 -n 5000

# 机器2
python sdc_fuzzing_generator.py ... -s 2 -n 5000
```

## 最佳实践

### 1. 渐进式生成

```bash
# 第一阶段：小规模测试
python sdc_fuzzing_generator.py -t target -o test1 -n 100 -m 5

# 第二阶段：中等规模
python sdc_fuzzing_generator.py -t target -o test2 -n 1000 -m 10

# 第三阶段：大规模生成
python sdc_fuzzing_generator.py -t target -o test3 -n 10000 -m 20
```

### 2. 分类生成

```bash
# 生成内存密集型测试
python sdc_fuzzing_generator.py -t target -o memory_tests -c memory_config.json

# 生成计算密集型测试
python sdc_fuzzing_generator.py -t target -o compute_tests -c compute_config.json

# 生成高风险指令测试
python sdc_fuzzing_generator.py -t target -o risk_tests -c risk_config.json
```

### 3. 可重现性

```bash
# 使用固定种子确保可重现
python sdc_fuzzing_generator.py -t target -o output -s 42 -n 1000
```

## 故障排查

### 问题1：生成失败率高

**原因**: 配置参数不合理

**解决**:
```json
{
  "sequence_length_min": 5,
  "sequence_length_max": 50,
  "mutation_rate": 0.2
}
```

### 问题2：内存不足

**原因**: 批处理大小过大

**解决**:
```json
{
  "batch_size": 50,
  "streaming_mode": true
}
```

### 问题3：生成速度慢

**原因**: worker数量不足或IO瓶颈

**解决**:
```bash
# 增加worker
python sdc_fuzzing_generator.py ... -w 16

# 使用SSD存储
python sdc_fuzzing_generator.py ... -o /fast_ssd/output
```

## 集成到CI/CD

```yaml
# .gitlab-ci.yml
sdc_fuzzing:
  stage: test
  script:
    - python sdc_fuzzing_generator.py -t $TARGET -o ./output -n 1000
    - ./run_tests.sh ./output
  artifacts:
    paths:
      - output/
    reports:
      junit: output/test_results.xml
```

## 进阶用法

### 自定义指令池

```python
from sdc_fuzzing_generator import InstructionPool, SDCFuzzingGenerator

# 创建自定义指令池
generator = SDCFuzzingGenerator(target_name, output_dir)

# 只使用特定指令
custom_pool = InstructionPool(generator.target)
custom_pool.instructions = {
    name: instr for name, instr in custom_pool.instructions.items()
    if instr.mnemonic in ['ADD', 'SUB', 'MUL', 'DIV']
}

generator.instruction_pool = custom_pool
```

### 自定义变异策略

```python
from sdc_fuzzing_generator import MutationEngine

class CustomMutationEngine(MutationEngine):
    def _mutate_custom(self, sequence):
        # 实现自定义变异逻辑
        return sequence
    
    def __init__(self, instruction_pool):
        super().__init__(instruction_pool)
        self.mutation_strategies.append(self._mutate_custom)
```

## 参考资料

- [Microprobe文档](./doc/)
- [SDC检测技术论文](./doc/sdc_detection.md)
- [模糊测试最佳实践](./doc/fuzzing_best_practices.md)
