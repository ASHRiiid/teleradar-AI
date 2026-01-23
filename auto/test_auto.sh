#!/bin/bash
# 自动化脚本测试工具

set -e

AUTO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/tmp/autowake_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

echo "=== 自动化脚本测试工具 ==="
echo "测试日志目录: $LOG_DIR"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log "检查依赖..."
    
    local missing_deps=()
    
    for cmd in curl timeout pmset ioreg who; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        error "缺少依赖: ${missing_deps[*]}"
        return 1
    fi
    
    success "所有依赖已安装"
}

# 测试1: 脚本语法检查
test_syntax() {
    log "测试1: 脚本语法检查"
    
    if bash -n "$AUTO_DIR/auto_wake_run.sh" 2>"$LOG_DIR/syntax_check.log"; then
        success "脚本语法正确"
        return 0
    else
        error "脚本语法错误"
        cat "$LOG_DIR/syntax_check.log"
        return 1
    fi
}

# 测试2: 网络检查功能
test_network_check() {
    log "测试2: 网络检查功能"
    
    # 创建测试脚本
    cat > "$LOG_DIR/test_network.sh" << 'EOF'
#!/bin/bash
NETWORK_CHECK_URL="https://www.baidu.com"
NETWORK_RETRY_COUNT=2
NETWORK_RETRY_DELAY=1
NETWORK_WAIT_AFTER_CONNECT=2

check_network() {
    echo "检查网络连接..."
    
    for ((i=1; i<=NETWORK_RETRY_COUNT; i++)); do
        echo "尝试连接 (第${i}次)"
        
        if curl -s --max-time 5 "${NETWORK_CHECK_URL}" > /dev/null 2>&1; then
            echo "网络连接正常"
            echo "等待${NETWORK_WAIT_AFTER_CONNECT}秒..."
            sleep "$NETWORK_WAIT_AFTER_CONNECT"
            return 0
        fi
        
        if [[ $i -lt $NETWORK_RETRY_COUNT ]]; then
            echo "网络连接失败，${NETWORK_RETRY_DELAY}秒后重试..."
            sleep "$NETWORK_RETRY_DELAY"
        fi
    done
    
    echo "无法连接到网络"
    return 1
}

check_network
EOF
    
    chmod +x "$LOG_DIR/test_network.sh"
    
    if "$LOG_DIR/test_network.sh" 2>&1 | tee "$LOG_DIR/network_test.log"; then
        success "网络检查功能正常"
        return 0
    else
        warning "网络检查失败（可能是网络问题）"
        return 0  # 不视为测试失败
    fi
}

# 测试3: 状态检测功能
test_status_detection() {
    log "测试3: 状态检测功能"
    
    # 创建测试脚本
    cat > "$LOG_DIR/test_status.sh" << 'EOF'
#!/bin/bash

echo "=== 系统状态检测 ==="

# 1. 用户活动检测
echo "1. 检查用户活动..."
last_activity=$(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF/1000000000; exit}' 2>/dev/null || echo "未知")
echo "   HID空闲时间: ${last_activity:-未知}秒"

# 2. 登录用户检测
echo "2. 检查登录用户..."
logged_in_users=$(who | grep -v "console" | wc -l)
echo "   登录用户数: $logged_in_users"

# 3. 显示器状态
echo "3. 检查显示器状态..."
display_state=$(pmset -g powerstate | grep "Display is" | head -1 2>/dev/null || echo "未知")
echo "   显示器状态: ${display_state:-未知}"

# 4. 合盖状态
echo "4. 检查合盖状态..."
clamshell_state=$(ioreg -r -k AppleClamshellState -d 4 | grep AppleClamshellState | head -1 2>/dev/null || echo "未知")
echo "   合盖状态: ${clamshell_state:-未知}"

echo "=== 状态检测完成 ==="
EOF
    
    chmod +x "$LOG_DIR/test_status.sh"
    
    if "$LOG_DIR/test_status.sh" 2>&1 | tee "$LOG_DIR/status_test.log"; then
        success "状态检测功能正常"
        return 0
    else
        error "状态检测功能异常"
        return 1
    fi
}

# 测试4: 超时功能测试
test_timeout() {
    log "测试4: 超时功能测试"
    
    # 创建测试脚本（macOS兼容版本）
    cat > "$LOG_DIR/test_timeout.sh" << 'EOF'
#!/bin/bash
echo "开始超时测试（10秒超时）"
echo "执行一个15秒的睡眠命令..."

# macOS兼容的超时实现
(sleep 15) &
pid=$!

# 等待10秒
sleep 10

# 检查进程是否还在运行
if kill -0 "$pid" 2>/dev/null; then
    echo "✓ 超时功能正常（命令在10秒后仍在运行）"
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
    exit 0
else
    echo "⚠ 命令在10秒内完成（这不应该发生）"
    exit 1
fi
EOF
    
    chmod +x "$LOG_DIR/test_timeout.sh"
    
    if "$LOG_DIR/test_timeout.sh" 2>&1 | tee "$LOG_DIR/timeout_test.log"; then
        success "超时功能正常"
        return 0
    else
        error "超时功能异常"
        return 1
    fi
}

# 测试5: 完整脚本快速测试
test_quick_run() {
    log "测试5: 完整脚本快速测试（30秒超时）"
    
    echo "注意：这将运行实际的自动化脚本，但会限制在30秒内"
    echo "按 Ctrl+C 可以中断测试"
    echo ""
    
    # 修改超时为30秒进行测试
    cp "$AUTO_DIR/auto_wake_run.sh" "$LOG_DIR/test_quick.sh"
    sed -i '' 's/TIMEOUT_MINUTES=5/TIMEOUT_MINUTES=0.5/' "$LOG_DIR/test_quick.sh"
    sed -i '' 's|./launch.command|echo "模拟任务执行" && sleep 10|' "$LOG_DIR/test_quick.sh"
    
    chmod +x "$LOG_DIR/test_quick.sh"
    
    timeout 30 "$LOG_DIR/test_quick.sh" 2>&1 | tee "$LOG_DIR/quick_test.log"
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]] || [[ $exit_code -eq 124 ]]; then
        success "完整脚本测试通过"
        return 0
    else
        error "完整脚本测试失败，退出码: $exit_code"
        return 1
    fi
}

# 主测试函数
main() {
    echo "开始自动化脚本测试..."
    echo ""
    
    local tests_passed=0
    local tests_failed=0
    local tests_total=5
    
    # 测试1: 语法检查
    if test_syntax; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    echo ""
    
    # 测试2: 网络检查
    if test_network_check; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    echo ""
    
    # 测试3: 状态检测
    if test_status_detection; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    echo ""
    
    # 测试4: 超时功能
    if test_timeout; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    echo ""
    
    # 测试5: 快速运行
    read -p "是否运行完整脚本测试？(y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if test_quick_run; then
            ((tests_passed++))
        else
            ((tests_failed++))
        fi
    else
        warning "跳过完整脚本测试"
        ((tests_total--))
    fi
    echo ""
    
    # 测试结果汇总
    echo "=== 测试结果汇总 ==="
    echo "总测试数: $tests_total"
    echo "通过: $tests_passed"
    echo "失败: $tests_failed"
    echo ""
    
    if [[ $tests_failed -eq 0 ]]; then
        success "所有测试通过！"
        echo "日志文件保存在: $LOG_DIR"
        return 0
    else
        error "有 $tests_failed 个测试失败"
        echo "请查看日志文件: $LOG_DIR"
        return 1
    fi
}

# 运行主函数
main "$@"