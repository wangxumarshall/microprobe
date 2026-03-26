#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SDC-Fuzzing批量生成工具

用于批量生成海量指令流序列，用于SDC（Silent Data Corruption）检测用例模糊测试

功能：
1. 指令池管理
2. 序列生成策略
3. 变异引擎
4. SDC检测注入
5. 批量并行生成
6. 结果收集与分析
"""

from __future__ import absolute_import, print_function, division

import argparse
import hashlib
import itertools
import json
import multiprocessing as mp
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from microprobe import MICROPROBE_RC
from microprobe.code import get_wrapper
from microprobe.exceptions import MicroprobeException, MicroprobeValueError
from microprobe.target import Target, import_definition
from microprobe.target.isa.instruction import InstructionType
from microprobe.utils.cmdline import (
    CLI,
    existing_dir,
    float_type,
    int_type,
    new_file,
    parse_instruction_list,
    print_error,
    print_info,
)
from microprobe.utils.logger import get_logger
from microprobe.utils.misc import findfiles, iter_flatten, move_file
from microprobe.utils.policy import find_policy

LOG = get_logger(__name__)

__all__ = [
    "SDCFuzzingGenerator",
    "InstructionPool",
    "MutationEngine",
    "SDCDetector",
]


class InstructionPool:
    """
    指令池管理类
    
    管理所有可用的指令，支持按类别、功能、风险等级分类
    """
    
    def __init__(self, target: Target):
        self.target = target
        self.instructions = {}
        self.categories = defaultdict(list)
        self.risk_levels = defaultdict(list)
        
        self._categorize_instructions()
    
    def _categorize_instructions(self):
        """对指令进行分类"""
        for instr in self.target.isa.instructions.values():
            self.instructions[instr.name] = instr
            
            # 按助记符分类
            mnemonic = instr.mnemonic
            self.categories[mnemonic].append(instr)
            
            # 按功能分类
            category = self._get_instruction_category(instr)
            self.categories[category].append(instr)
            
            # 按风险等级分类
            risk = self._get_instruction_risk(instr)
            self.risk_levels[risk].append(instr)
    
    def _get_instruction_category(self, instr: InstructionType) -> str:
        """获取指令功能类别"""
        mnemonic = instr.mnemonic.upper()
        
        if mnemonic.startswith(('ADD', 'SUB', 'MUL', 'DIV', 'NEG')):
            return 'arithmetic'
        elif mnemonic.startswith(('AND', 'ORR', 'EOR', 'XOR', 'NOT')):
            return 'logical'
        elif mnemonic.startswith(('LD', 'ST', 'LDR', 'STR')):
            return 'memory'
        elif mnemonic.startswith(('B', 'BR', 'CALL', 'RET')):
            return 'branch'
        elif mnemonic.startswith(('FADD', 'FSUB', 'FMUL', 'FDIV')):
            return 'floating'
        elif mnemonic.startswith(('V', 'SIMD')):
            return 'simd'
        else:
            return 'other'
    
    def _get_instruction_risk(self, instr: InstructionType) -> str:
        """获取指令风险等级"""
        mnemonic = instr.mnemonic.upper()
        
        # 高风险指令：可能导致系统崩溃或数据损坏
        high_risk_keywords = [
            'LDXR', 'STXR', 'CAS', 'SWP',  # 原子操作
            'DC', 'IC', 'TLBI',  # 缓存/TLB操作
            'MSR', 'MRS',  # 系统寄存器访问
            'SVC', 'HVC', 'SMC',  # 异常调用
        ]
        
        # 中风险指令：可能导致数据不一致
        medium_risk_keywords = [
            'LDP', 'STP',  # 多寄存器加载存储
            'LDAXR', 'STLXR',  # 带屏障的原子操作
            'PRFM',  # 预取指令
        ]
        
        for keyword in high_risk_keywords:
            if keyword in mnemonic:
                return 'high'
        
        for keyword in medium_risk_keywords:
            if keyword in mnemonic:
                return 'medium'
        
        return 'low'
    
    def get_instructions_by_category(self, category: str) -> List[InstructionType]:
        """获取指定类别的指令"""
        return self.categories.get(category, [])
    
    def get_instructions_by_risk(self, risk: str) -> List[InstructionType]:
        """获取指定风险等级的指令"""
        return self.risk_levels.get(risk, [])
    
    def get_random_instructions(self, n: int, category: Optional[str] = None) -> List[InstructionType]:
        """随机获取n条指令"""
        if category:
            pool = self.categories.get(category, [])
        else:
            pool = list(self.instructions.values())
        
        return random.sample(pool, min(n, len(pool)))
    
    def get_instruction_combinations(self, length: int, max_combinations: int = 10000) -> List[List[InstructionType]]:
        """获取指令组合"""
        all_instrs = list(self.instructions.values())
        
        # 如果组合数太大，使用随机采样
        total_combinations = len(all_instrs) ** length
        if total_combinations > max_combinations:
            combinations = []
            for _ in range(max_combinations):
                combinations.append(random.choices(all_instrs, k=length))
            return combinations
        else:
            return list(itertools.product(all_instrs, repeat=length))


class MutationEngine:
    """
    变异引擎
    
    对指令序列进行各种变异操作，生成多样化的测试用例
    """
    
    def __init__(self, instruction_pool: InstructionPool):
        self.pool = instruction_pool
        self.mutation_strategies = [
            self._mutate_replace,
            self._mutate_insert,
            self._mutate_delete,
            self._mutate_swap,
            self._mutate_duplicate,
            self._mutate_reverse,
        ]
    
    def mutate(self, sequence: List[InstructionType], mutation_rate: float = 0.3) -> List[InstructionType]:
        """
        对指令序列进行变异
        
        Args:
            sequence: 原始指令序列
            mutation_rate: 变异率（0-1之间）
        
        Returns:
            变异后的指令序列
        """
        mutated = sequence.copy()
        
        # 根据变异率决定变异次数
        num_mutations = max(1, int(len(sequence) * mutation_rate))
        
        for _ in range(num_mutations):
            # 随机选择一个变异策略
            mutation_func = random.choice(self.mutation_strategies)
            mutated = mutation_func(mutated)
        
        return mutated
    
    def _mutate_replace(self, sequence: List[InstructionType]) -> List[InstructionType]:
        """替换变异：随机替换一条指令"""
        if len(sequence) == 0:
            return sequence
        
        idx = random.randint(0, len(sequence) - 1)
        new_instr = random.choice(list(self.pool.instructions.values()))
        sequence[idx] = new_instr
        return sequence
    
    def _mutate_insert(self, sequence: List[InstructionType]) -> List[InstructionType]:
        """插入变异：随机插入一条指令"""
        new_instr = random.choice(list(self.pool.instructions.values()))
        idx = random.randint(0, len(sequence))
        sequence.insert(idx, new_instr)
        return sequence
    
    def _mutate_delete(self, sequence: List[InstructionType]) -> List[InstructionType]:
        """删除变异：随机删除一条指令"""
        if len(sequence) > 1:
            idx = random.randint(0, len(sequence) - 1)
            sequence.pop(idx)
        return sequence
    
    def _mutate_swap(self, sequence: List[InstructionType]) -> List[InstructionType]:
        """交换变异：随机交换两条指令的位置"""
        if len(sequence) < 2:
            return sequence
        
        idx1, idx2 = random.sample(range(len(sequence)), 2)
        sequence[idx1], sequence[idx2] = sequence[idx2], sequence[idx1]
        return sequence
    
    def _mutate_duplicate(self, sequence: List[InstructionType]) -> List[InstructionType]:
        """复制变异：随机复制一条指令"""
        if len(sequence) == 0:
            return sequence
        
        idx = random.randint(0, len(sequence) - 1)
        sequence.insert(idx, sequence[idx])
        return sequence
    
    def _mutate_reverse(self, sequence: List[InstructionType]) -> List[InstructionType]:
        """反转变异：反转一个子序列"""
        if len(sequence) < 2:
            return sequence
        
        start = random.randint(0, len(sequence) - 2)
        end = random.randint(start + 1, len(sequence) - 1)
        sequence[start:end+1] = reversed(sequence[start:end+1])
        return sequence
    
    def generate_mutants(self, base_sequence: List[InstructionType], num_mutants: int, mutation_rate: float = 0.3) -> List[List[InstructionType]]:
        """
        生成多个变异体
        
        Args:
            base_sequence: 基础指令序列
            num_mutants: 变异体数量
            mutation_rate: 变异率
        
        Returns:
            变异体列表
        """
        mutants = []
        for _ in range(num_mutants):
            mutant = self.mutate(base_sequence, mutation_rate)
            mutants.append(mutant)
        return mutants


class SDCDetector:
    """
    SDC检测注入器
    
    在生成的代码中注入SDC检测机制
    """
    
    def __init__(self, target: Target):
        self.target = target
    
    def inject_checksum(self, sequence_length: int) -> List[str]:
        """
        注入校验和检测
        
        在代码执行前后计算校验和，检测数据损坏
        """
        detection_code = []
        
        # 初始化校验和寄存器
        detection_code.append("// SDC Detection: Checksum initialization")
        detection_code.append("uint64_t checksum = 0;")
        
        # 在关键点插入校验和更新
        if sequence_length > 100:
            # 每100条指令检查一次
            detection_code.append(f"// Checksum update every 100 instructions")
        
        # 最终校验
        detection_code.append("// SDC Detection: Final checksum verification")
        detection_code.append("if (checksum != expected_checksum) {")
        detection_code.append("    report_sdc_error();")
        detection_code.append("}")
        
        return detection_code
    
    def inject_redundant_execution(self) -> List[str]:
        """
        注入冗余执行检测
        
        同一段代码执行两次，比较结果
        """
        detection_code = []
        
        detection_code.append("// SDC Detection: Redundant execution")
        detection_code.append("// Execute critical section twice and compare results")
        detection_code.append("uint64_t result1 = execute_critical_section();")
        detection_code.append("uint64_t result2 = execute_critical_section();")
        detection_code.append("if (result1 != result2) {")
        detection_code.append("    report_sdc_error();")
        detection_code.append("}")
        
        return detection_code
    
    def inject_boundary_check(self) -> List[str]:
        """
        注入边界检查
        
        检查计算结果是否在合理范围内
        """
        detection_code = []
        
        detection_code.append("// SDC Detection: Boundary check")
        detection_code.append("if (result < MIN_EXPECTED || result > MAX_EXPECTED) {")
        detection_code.append("    report_sdc_error();")
        detection_code.append("}")
        
        return detection_code
    
    def inject_memory_canary(self) -> List[str]:
        """
        注入内存金丝雀
        
        在内存关键位置放置金丝雀值，检测内存损坏
        """
        detection_code = []
        
        detection_code.append("// SDC Detection: Memory canary")
        detection_code.append("volatile uint64_t canary = CANARY_VALUE;")
        detection_code.append("// ... critical code ...")
        detection_code.append("if (canary != CANARY_VALUE) {")
        detection_code.append("    report_sdc_error();")
        detection_code.append("}")
        
        return detection_code
    
    def get_detection_strategy(self, strategy: str) -> List[str]:
        """获取指定的SDC检测策略代码"""
        strategies = {
            'checksum': self.inject_checksum,
            'redundant': self.inject_redundant_execution,
            'boundary': self.inject_boundary_check,
            'canary': self.inject_memory_canary,
        }
        
        if strategy in strategies:
            return strategies[strategy]()
        else:
            return []


class SDCFuzzingGenerator:
    """
    SDC-Fuzzing批量生成器
    
    主要类，协调整个生成流程
    """
    
    def __init__(self, target_name: str, output_dir: str, config: Optional[Dict] = None):
        self.target_name = target_name
        self.output_dir = output_dir
        self.config = config or self._default_config()
        
        # 加载目标
        LOG.info(f"Loading target: {target_name}")
        self.target = import_definition(target_name)
        
        # 初始化组件
        self.instruction_pool = InstructionPool(self.target)
        self.mutation_engine = MutationEngine(self.instruction_pool)
        self.sdc_detector = SDCDetector(self.target)
        
        # 统计信息
        self.stats = {
            'total_generated': 0,
            'total_failed': 0,
            'by_category': defaultdict(int),
            'by_risk': defaultdict(int),
        }
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'sequence_length_min': 10,
            'sequence_length_max': 100,
            'num_sequences': 1000,
            'mutation_rate': 0.3,
            'num_mutants_per_base': 10,
            'sdc_detection': ['checksum', 'redundant'],
            'parallel_workers': mp.cpu_count(),
            'batch_size': 100,
            'compress_output': True,
            'seed': None,
        }
    
    def generate_base_sequences(self) -> List[List[InstructionType]]:
        """
        生成基础指令序列
        
        策略：
        1. 从不同类别随机组合
        2. 按风险等级混合
        3. 特定模式序列（如内存密集型、计算密集型）
        """
        base_sequences = []
        
        # 策略1：随机组合
        num_random = self.config['num_sequences'] // 4
        for _ in range(num_random):
            length = random.randint(
                self.config['sequence_length_min'],
                self.config['sequence_length_max']
            )
            sequence = self.instruction_pool.get_random_instructions(length)
            base_sequences.append(sequence)
        
        # 策略2：按类别生成
        categories = ['arithmetic', 'logical', 'memory', 'branch', 'floating', 'simd']
        for category in categories:
            num_per_category = self.config['num_sequences'] // (len(categories) * 2)
            for _ in range(num_per_category):
                length = random.randint(
                    self.config['sequence_length_min'],
                    self.config['sequence_length_max']
                )
                sequence = self.instruction_pool.get_random_instructions(length, category)
                base_sequences.append(sequence)
        
        # 策略3：混合风险等级
        for risk in ['low', 'medium', 'high']:
            num_per_risk = self.config['num_sequences'] // 12
            for _ in range(num_per_risk):
                length = random.randint(
                    self.config['sequence_length_min'],
                    self.config['sequence_length_max']
                )
                pool = self.instruction_pool.get_instructions_by_risk(risk)
                if pool:
                    sequence = random.choices(pool, k=length)
                    base_sequences.append(sequence)
        
        # 策略4：特定模式
        # 内存密集型
        memory_instrs = self.instruction_pool.get_instructions_by_category('memory')
        if memory_instrs:
            for _ in range(self.config['num_sequences'] // 8):
                length = random.randint(20, 50)
                sequence = random.choices(memory_instrs, k=length)
                base_sequences.append(sequence)
        
        # 计算密集型
        compute_instrs = (
            self.instruction_pool.get_instructions_by_category('arithmetic') +
            self.instruction_pool.get_instructions_by_category('floating')
        )
        if compute_instrs:
            for _ in range(self.config['num_sequences'] // 8):
                length = random.randint(20, 50)
                sequence = random.choices(compute_instrs, k=length)
                base_sequences.append(sequence)
        
        LOG.info(f"Generated {len(base_sequences)} base sequences")
        return base_sequences
    
    def generate_mutants(self, base_sequences: List[List[InstructionType]]) -> List[List[InstructionType]]:
        """
        对基础序列进行变异，生成变异体
        """
        all_sequences = base_sequences.copy()
        
        for base_seq in base_sequences:
            mutants = self.mutation_engine.generate_mutants(
                base_seq,
                self.config['num_mutants_per_base'],
                self.config['mutation_rate']
            )
            all_sequences.extend(mutants)
        
        LOG.info(f"Generated {len(all_sequences)} total sequences (base + mutants)")
        return all_sequences
    
    def generate_single_testcase(
        self,
        sequence: List[InstructionType],
        output_file: str,
        policy_name: str = 'seq',
        **kwargs
    ) -> bool:
        """
        生成单个测试用例
        """
        try:
            # 查找策略
            policy = find_policy(self.target.name, policy_name)
            
            # 获取wrapper
            wrapper_name = self.target.environment.default_wrapper
            wrapper_class = get_wrapper(wrapper_name)
            wrapper = wrapper_class(
                endless=kwargs.get('endless', False),
                reset=kwargs.get('reset', False)
            )
            
            # 创建synthesizer
            import microprobe.code
            synthesizer = microprobe.code.Synthesizer(
                self.target,
                wrapper,
                value=kwargs.get('value', 0)
            )
            
            # 应用策略
            policy_kwargs = {
                'instructions': sequence,
                'benchmark_size': kwargs.get('benchmark_size', len(sequence)),
                'dependency_distance': kwargs.get('dependency_distance', 1),
                'force_switch': kwargs.get('force_switch', False),
                'endless': kwargs.get('endless', False),
            }
            
            policy.apply(self.target, wrapper, **policy_kwargs)
            
            # 生成代码
            benchmark = synthesizer.generate()
            
            # 写入文件
            with open(output_file, 'w') as f:
                f.write(benchmark)
            
            # 更新统计
            self.stats['total_generated'] += 1
            
            return True
            
        except Exception as e:
            LOG.error(f"Failed to generate testcase: {e}")
            self.stats['total_failed'] += 1
            return False
    
    def generate_batch(
        self,
        sequences: List[List[InstructionType]],
        start_idx: int = 0
    ) -> Tuple[int, int]:
        """
        批量生成测试用例
        
        Returns:
            (成功数, 失败数)
        """
        success_count = 0
        fail_count = 0
        
        for idx, sequence in enumerate(sequences):
            # 生成输出文件名
            seq_hash = hashlib.sha256(
                '_'.join(instr.name for instr in sequence).encode()
            ).hexdigest()[:16]
            
            output_file = os.path.join(
                self.output_dir,
                f"sdc_test_{start_idx + idx:06d}_{seq_hash}.c"
            )
            
            # 生成测试用例
            if self.generate_single_testcase(sequence, output_file):
                success_count += 1
            else:
                fail_count += 1
            
            # 进度报告
            if (idx + 1) % 100 == 0:
                LOG.info(f"Progress: {idx + 1}/{len(sequences)} "
                        f"(success: {success_count}, failed: {fail_count})")
        
        return success_count, fail_count
    
    def generate_parallel(self, sequences: List[List[InstructionType]]) -> Dict[str, int]:
        """
        并行生成测试用例
        """
        num_workers = self.config['parallel_workers']
        batch_size = self.config['batch_size']
        
        # 分割任务
        batches = []
        for i in range(0, len(sequences), batch_size):
            batches.append((i, sequences[i:i+batch_size]))
        
        LOG.info(f"Starting parallel generation with {num_workers} workers")
        LOG.info(f"Total batches: {len(batches)}, batch size: {batch_size}")
        
        # 并行执行
        with mp.Pool(num_workers) as pool:
            results = pool.starmap(self.generate_batch, batches)
        
        # 汇总结果
        total_success = sum(r[0] for r in results)
        total_fail = sum(r[1] for r in results)
        
        self.stats['total_generated'] = total_success
        self.stats['total_failed'] = total_fail
        
        return {
            'success': total_success,
            'failed': total_fail,
            'total': len(sequences),
        }
    
    def run(self) -> Dict[str, Any]:
        """
        运行完整的生成流程
        """
        start_time = time.time()
        
        LOG.info("="*80)
        LOG.info("SDC-Fuzzing Generation Started")
        LOG.info("="*80)
        LOG.info(f"Target: {self.target_name}")
        LOG.info(f"Output directory: {self.output_dir}")
        LOG.info(f"Configuration: {json.dumps(self.config, indent=2)}")
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 保存配置
        config_file = os.path.join(self.output_dir, 'config.json')
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        # 步骤1：生成基础序列
        LOG.info("\n[Step 1] Generating base sequences...")
        base_sequences = self.generate_base_sequences()
        
        # 步骤2：生成变异体
        LOG.info("\n[Step 2] Generating mutants...")
        all_sequences = self.generate_mutants(base_sequences)
        
        # 步骤3：并行生成测试用例
        LOG.info("\n[Step 3] Generating test cases in parallel...")
        results = self.generate_parallel(all_sequences)
        
        # 步骤4：生成报告
        end_time = time.time()
        duration = end_time - start_time
        
        report = {
            'target': self.target_name,
            'output_dir': self.output_dir,
            'config': self.config,
            'statistics': {
                'base_sequences': len(base_sequences),
                'total_sequences': len(all_sequences),
                'generated': results['success'],
                'failed': results['failed'],
                'success_rate': results['success'] / results['total'] if results['total'] > 0 else 0,
            },
            'timing': {
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.fromtimestamp(end_time).isoformat(),
                'duration_seconds': duration,
                'sequences_per_second': len(all_sequences) / duration if duration > 0 else 0,
            }
        }
        
        # 保存报告
        report_file = os.path.join(self.output_dir, 'generation_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # 打印摘要
        LOG.info("\n" + "="*80)
        LOG.info("Generation Complete!")
        LOG.info("="*80)
        LOG.info(f"Total sequences generated: {results['success']}")
        LOG.info(f"Failed: {results['failed']}")
        LOG.info(f"Success rate: {report['statistics']['success_rate']:.2%}")
        LOG.info(f"Duration: {duration:.2f} seconds")
        LOG.info(f"Rate: {report['timing']['sequences_per_second']:.2f} sequences/second")
        LOG.info(f"Report saved to: {report_file}")
        
        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="SDC-Fuzzing Batch Generation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 生成1000个测试用例
  python sdc_fuzzing_generator.py -t power_v207-power8-ppc64_linux_gcc -o ./output -n 1000

  # 使用自定义配置
  python sdc_fuzzing_generator.py -t riscv_v22-riscv_generic-riscv64_linux_gcc -o ./output -c config.json

  # 并行生成
  python sdc_fuzzing_generator.py -t target -o ./output -n 10000 -w 8
        """
    )
    
    parser.add_argument(
        '-t', '--target',
        required=True,
        help='Target name (e.g., power_v207-power8-ppc64_linux_gcc)'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output directory for generated test cases'
    )
    
    parser.add_argument(
        '-n', '--num-sequences',
        type=int,
        default=1000,
        help='Number of base sequences to generate (default: 1000)'
    )
    
    parser.add_argument(
        '-m', '--mutants',
        type=int,
        default=10,
        help='Number of mutants per base sequence (default: 10)'
    )
    
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=mp.cpu_count(),
        help='Number of parallel workers (default: CPU count)'
    )
    
    parser.add_argument(
        '-l', '--length-min',
        type=int,
        default=10,
        help='Minimum sequence length (default: 10)'
    )
    
    parser.add_argument(
        '-L', '--length-max',
        type=int,
        default=100,
        help='Maximum sequence length (default: 100)'
    )
    
    parser.add_argument(
        '-r', '--mutation-rate',
        type=float,
        default=0.3,
        help='Mutation rate (default: 0.3)'
    )
    
    parser.add_argument(
        '-b', '--batch-size',
        type=int,
        default=100,
        help='Batch size for parallel processing (default: 100)'
    )
    
    parser.add_argument(
        '-s', '--seed',
        type=int,
        default=None,
        help='Random seed for reproducibility'
    )
    
    parser.add_argument(
        '-c', '--config',
        help='Configuration file (JSON format)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # 设置随机种子
    if args.seed is not None:
        random.seed(args.seed)
    
    # 加载配置
    config = None
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        config = {
            'num_sequences': args.num_sequences,
            'num_mutants_per_base': args.mutants,
            'sequence_length_min': args.length_min,
            'sequence_length_max': args.length_max,
            'mutation_rate': args.mutation_rate,
            'parallel_workers': args.workers,
            'batch_size': args.batch_size,
            'seed': args.seed,
        }
    
    # 创建生成器并运行
    generator = SDCFuzzingGenerator(
        target_name=args.target,
        output_dir=args.output,
        config=config
    )
    
    report = generator.run()
    
    return 0 if report['statistics']['success_rate'] > 0.9 else 1


if __name__ == '__main__':
    sys.exit(main())
