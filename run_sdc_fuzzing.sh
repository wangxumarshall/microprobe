#!/bin/bash
# SDC-Fuzzing快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助
show_help() {
    cat << EOF
SDC-Fuzzing批量生成工具 - 快速启动脚本

用法: $0 [选项]

选项:
    -t, --target TARGET        目标架构名称 (必需)
    -o, --output DIR           输出目录 (默认: ./sdc_output)
    -n, --num NUMBER           基础序列数量 (默认: 1000)
    -m, --mutants NUMBER       每个序列的变异体数量 (默认: 10)
    -c, --config FILE          配置文件路径
    -w, --workers NUMBER       并行worker数量 (默认: CPU核心数)
    -p, --preset PRESET        预设配置 (default/memory/compute/risk)
    -h, --help                 显示此帮助信息

示例:
    # 基本用法
    $0 -t power_v207-power8-ppc64_linux_gcc -o ./output -n 1000

    # 使用预设配置
    $0 -t target -o ./output -p memory

    # 使用自定义配置文件
    $0 -t target -o ./output -c config.json

预设配置:
    default     - 默认配置，均衡生成各类指令序列
    memory      - 内存密集型配置，重点测试内存操作
    compute     - 计算密集型配置，重点测试算术和浮点运算
    risk        - 高风险配置，重点测试原子操作和系统指令

EOF
}

# 默认参数
TARGET=""
OUTPUT="./sdc_output"
NUM_SEQUENCES=1000
NUM_MUTANTS=10
CONFIG=""
WORKERS=$(nproc)
PRESET=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -n|--num)
            NUM_SEQUENCES="$2"
            shift 2
            ;;
        -m|--mutants)
            NUM_MUTANTS="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -p|--preset)
            PRESET="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查必需参数
if [ -z "$TARGET" ]; then
    print_error "必须指定目标架构 (-t, --target)"
    show_help
    exit 1
fi

# 设置预设配置
if [ -n "$PRESET" ]; then
    CONFIG_FILE="./config_examples/${PRESET}_intensive_config.json"
    if [ "$PRESET" = "default" ]; then
        CONFIG_FILE="./config_examples/default_config.json"
    fi
    
    if [ -f "$CONFIG_FILE" ]; then
        CONFIG="$CONFIG_FILE"
        print_info "使用预设配置: $PRESET ($CONFIG_FILE)"
    else
        print_warning "预设配置文件不存在: $CONFIG_FILE"
        print_info "将使用默认参数"
    fi
fi

# 显示配置
print_info "========== SDC-Fuzzing配置 =========="
print_info "目标架构: $TARGET"
print_info "输出目录: $OUTPUT"
print_info "基础序列数: $NUM_SEQUENCES"
print_info "变异体数: $NUM_MUTANTS"
print_info "并行worker: $WORKERS"
if [ -n "$CONFIG" ]; then
    print_info "配置文件: $CONFIG"
fi
print_info "======================================"

# 创建输出目录
mkdir -p "$OUTPUT"

# 检查Python脚本
SCRIPT="sdc_fuzzing_generator.py"
if [ ! -f "$SCRIPT" ]; then
    print_error "找不到生成脚本: $SCRIPT"
    exit 1
fi

# 构建命令
CMD="python $SCRIPT -t $TARGET -o $OUTPUT -n $NUM_SEQUENCES -m $NUM_MUTANTS -w $WORKERS"

if [ -n "$CONFIG" ]; then
    CMD="$CMD -c $CONFIG"
fi

# 执行生成
print_info "开始生成测试用例..."
print_info "命令: $CMD"

START_TIME=$(date +%s)

if $CMD; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    print_success "生成完成！"
    print_info "总耗时: ${DURATION}秒"
    print_info "输出目录: $OUTPUT"
    print_info "生成报告: $OUTPUT/generation_report.json"
    
    # 显示统计信息
    if [ -f "$OUTPUT/generation_report.json" ]; then
        print_info "========== 生成统计 =========="
        python -c "
import json
with open('$OUTPUT/generation_report.json', 'r') as f:
    report = json.load(f)
    stats = report['statistics']
    print(f'基础序列数: {stats[\"base_sequences\"]}')
    print(f'总序列数: {stats[\"total_sequences\"]}')
    print(f'成功生成: {stats[\"generated\"]}')
    print(f'失败数: {stats[\"failed\"]}')
    print(f'成功率: {stats[\"success_rate\"]:.2%}')
    print(f'生成速率: {report[\"timing\"][\"sequences_per_second\"]:.2f} 序列/秒')
"
        print_info "=============================="
    fi
else
    print_error "生成失败！"
    exit 1
fi

# 提示下一步
print_info ""
print_info "下一步操作:"
print_info "1. 查看生成报告: cat $OUTPUT/generation_report.json"
print_info "2. 编译测试用例: cd $OUTPUT && make"
print_info "3. 运行测试: ./run_tests.sh"
print_info "4. 分析结果: python analyze_results.py $OUTPUT"
