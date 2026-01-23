#!/bin/bash

# =================================================================
# 智能自动化唤醒运行脚本
# Path: /Users/axrid/Documents/EVM/information-ai/auto/auto_wake_run.sh
# =================================================================

# 配置项
LOG_FILE="/Users/axrid/Documents/EVM/information-ai/auto/auto_wake.log"
ENV_FILE="/Users/axrid/Documents/EVM/information-ai/.env"
LOG_ANALYZER="/Users/axrid/Documents/EVM/information-ai/auto/log_analyzer.sh"
TIMEOUT_SEC=300
NETWORK_TARGETS=("baidu.com" "1.1.1.1" "8.8.8.8")
POST_NET_WAIT=5
IDLE_LIMIT=60 # 判定为“正在使用”的空闲秒数阈值
LOCK_FILE="/tmp/auto_wake_run.lock"

# 加载环境变量
if [ -f "$ENV_FILE" ]; then
    # 提取需要的变量
    export TELEGRAM_BOT_TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" "$ENV_FILE" | cut -d= -f2)
    export TELEGRAM_USER_ID=$(grep "^TELEGRAM_USER_ID=" "$ENV_FILE" | cut -d= -f2)
fi

# 电源安全阈值
MAX_TEMP=85    # CPU 最高温度 (摄氏度)
MIN_BATTERY=20 # 最低电池百分比

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")"

# 日志函数
log() {
    local level="${2:-INFO}"
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $1"
    echo "$message" >> "$LOG_FILE"
    echo "$message"
}

# Telegram 告警推送
push_alert() {
    local title="$1"
    local content="$2"
    local status="${3:-INFO}"
    
    local icon="ℹ️"
    [ "$status" == "WARN" ] && icon="⚠️"
    [ "$status" == "ERROR" ] && icon="🚨"
    
    local message="*${icon} ${title}*

${content}"

    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_USER_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_USER_ID" \
            -d "text=$message" \
            -d "parse_mode=Markdown" > /dev/null
    fi
}

# 进程树清理函数 (macOS 兼容，深度递归)
kill_process_tree() {
    local _target_pid=$1
    local _sig=${2:-TERM}
    if [ -z "$_target_pid" ]; then return; fi
    
    # 获取子进程并递归清理
    local _children=$(pgrep -P "$_target_pid" 2>/dev/null)
    for _child in $_children; do
        kill_process_tree "$_child" "$_sig"
    done
    
    # 终止目标进程 (跳过主进程 $$ 和监控进程 $TIMEOUT_PID)
    if [ "$_target_pid" != "$$" ] && [ "$_target_pid" != "$TIMEOUT_PID" ]; then
        kill -"$_sig" "$_target_pid" 2>/dev/null
    fi
}

# 清理与资源释放
cleanup() {
    local exit_code=$?
    log "执行清理程序 (退出码: $exit_code)..." "INFO"
    
    # 1. 终止业务进程及其子进程树
    if [ -n "$BUSINESS_PID" ]; then
        log "正在终止业务进程树 (PID: $BUSINESS_PID)..." "WARN"
        kill_process_tree "$BUSINESS_PID" TERM
        sleep 0.5
        kill_process_tree "$BUSINESS_PID" KILL
    fi

    # 2. 清理电源管理进程 (Caffeinate)
    if [ -n "$CAFF_PID" ]; then
        kill "$CAFF_PID" 2>/dev/null
    fi

    # 3. 停止超时保护监控器
    if [ -n "$TIMEOUT_PID" ]; then
        pkill -P "$TIMEOUT_PID" 2>/dev/null
        kill "$TIMEOUT_PID" 2>/dev/null
    fi
    
    # 4. 释放系统资源
    rm -f "$LOCK_FILE"
    # 关闭可能遗留的文件描述符 (3-9)
    for fd in 3 4 5 6 7 8 9; do
        eval "exec $fd>&-" 2>/dev/null
    done
    
    if [ "$exit_code" -ne 0 ]; then
        if [ "$exit_code" -eq 143 ] || [ "$exit_code" -eq 137 ]; then
            log "脚本因超时或强制信号被终止。" "ERROR"
        else
            log "脚本异常退出。" "ERROR"
        fi
    else
        log "脚本正常完成。" "INFO"
    fi
}

# 设置 trap
trap cleanup EXIT
trap 'exit 130' SIGINT
trap 'exit 143' SIGTERM

# 0. 锁文件检查 (防止重叠运行)
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        log "错误: 脚本已在运行中 (PID: $PID)，本次退出。" "WARN"
        exit 0
    fi
fi
echo $$ > "$LOCK_FILE"

# 0.5 日志预分析
log "【监控】开始执行预检测日志分析..." "INFO"
if [ -f "$LOG_ANALYZER" ]; then
    ANALYSIS_REPORT=$("$LOG_ANALYZER" -d "$(dirname "$LOG_FILE")" -p "$(basename "$LOG_FILE")" -t 1440)
    ANALYSIS_STATUS=$?
    
    case $ANALYSIS_STATUS in
        2) # STATUS_CRITICAL
            log "【严重】发现严重日志问题，终止程序！" "ERROR"
            push_alert "自动化任务终止 (预检严重异常)" "$ANALYSIS_REPORT" "ERROR"
            exit 1
            ;;
        1) # STATUS_WARNING
            log "【警告】日志中存在不严重问题，将继续执行并稍后告警。" "WARN"
            PENDING_WARNING="$ANALYSIS_REPORT"
            ;;
        *) # STATUS_NORMAL or others
            log "【正常】日志分析未见异常或未发现日志。" "INFO"
            ;;
    esac
else
    log "警告: 未找到日志分析脚本 $LOG_ANALYZER" "WARN"
fi

# 1. 超时保护机制 (包含现场快照与深度清理)
(
    sleep $TIMEOUT_SEC
    log "【超时告警】脚本执行超过限时 ${TIMEOUT_SEC}s，启动强制清理流程。" "ERROR"
    push_alert "自动化任务终止 (执行超时)" "脚本执行超过限时 ${TIMEOUT_SEC}s，已启动强制清理。" "ERROR"
    
    # 记录详细的进程现场快照
    log "【超时现场】活跃进程快照:" "DEBUG"
    if command -v ps >/dev/null; then
        _pgid=$(ps -o pgid= -p $$ | tr -d ' ')
        if [ -n "$_pgid" ]; then
            ps -f -g "$_pgid" >> "$LOG_FILE" 2>/dev/null || ps -ef | grep "$$" >> "$LOG_FILE"
        else
            ps -ef | grep "$$" >> "$LOG_FILE"
        fi
    fi
    
    # 向主进程发送 SIGTERM (15)，触发其 trap 执行 cleanup
    kill -15 $$ 2>/dev/null
    
    # 给予清理时间，若未退出则执行最终 KILL
    sleep 5
    log "【超时强制】主进程清理响应超时，执行最终强制杀除。" "ERROR"
    # 杀掉所有子进程树
    _children=$(pgrep -P $$ 2>/dev/null)
    for _c in $_children; do
        kill_process_tree "$_c" KILL
    done
    kill -9 $$ 2>/dev/null
) &
TIMEOUT_PID=$!

log ">>> 自动化任务启动 <<<" "INFO"

# 2. 防止系统休眠
log "电源管理: 启动 caffeinate 锁定系统状态..." "INFO"
caffeinate -i -m -s -w $$ &
CAFF_PID=$!

# 3. 智能判断电脑是否正在使用 (基于 macOS ioreg)
IDLE_NS=$(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF; exit}')
if [ -n "$IDLE_NS" ]; then
    IDLE_S=$((IDLE_NS / 1000000000))
    if [ "$IDLE_S" -lt "$IDLE_LIMIT" ]; then
        log "状态检测: 电脑当前正在使用中 (空闲时间: ${IDLE_S}s < ${IDLE_LIMIT}s)" "INFO"
    else
        log "状态检测: 电脑当前处于空闲状态 (空闲时间: ${IDLE_S}s)" "INFO"
    fi
else
    log "无法获取空闲时间，跳过状态检测。" "WARN"
fi

# 4. 电源与温度安全检测
check_safety() {
    # 电池检查
    if pmset -g batt | grep -q "InternalBattery"; then
        BATT_INFO=$(pmset -g batt)
        if ! echo "$BATT_INFO" | grep -q "AC Power"; then
            PERCENT=$(echo "$BATT_INFO" | grep -o "[0-9]\{1,3\}%" | tr -d '%' | head -n1)
            if [ -n "$PERCENT" ] && [ "$PERCENT" -lt "$MIN_BATTERY" ]; then
                log "安全终止: 电池电量不足 ($PERCENT% < $MIN_BATTERY%)，为保护硬件停止运行。" "ERROR"
                return 1
            fi
            log "状态检测: 电池供电中 (电量: $PERCENT%)" "INFO"
        else
            log "状态检测: 已连接外接电源" "INFO"
        fi
    fi

    # CPU 温度检查
    if command -v istats >/dev/null 2>&1; then
        TEMP=$(istats cpu temp --value-only | cut -d. -f1)
        if [ -n "$TEMP" ] && [ "$TEMP" -gt "$MAX_TEMP" ]; then
            log "安全终止: CPU 温度过高 ($TEMP°C > $MAX_TEMP°C)，触发过热保护。" "ERROR"
            return 1
        fi
        log "状态检测: CPU 温度正常 ($TEMP°C)" "INFO"
    elif sysctl machdep.cpu.thermal_level >/dev/null 2>&1; then
        LEVEL=$(sysctl -n machdep.cpu.thermal_level)
        if [ "$LEVEL" -ge 2 ]; then
            log "安全终止: 系统热等级过高 (thermal_level: $LEVEL)，触发过热保护。" "ERROR"
            return 1
        fi
        log "状态检测: 系统热等级正常 (level: $LEVEL)" "INFO"
    else
        log "警告: 无法获取温度信息，跳过温度检测。" "WARN"
    fi
    
    return 0
}

if ! check_safety; then
    push_alert "自动化任务终止 (安全检查失败)" "硬件状态不符合运行条件 (电池/温度)。" "ERROR"
    exit 1
fi

# 5. 显示器控制 (仅在空闲时关闭)
if [ -n "$IDLE_S" ] && [ "$IDLE_S" -ge "$IDLE_LIMIT" ]; then
    log "电源管理: 尝试关闭显示器以节省能源..." "INFO"
    if pmset displaysleepnow 2>/dev/null; then
        log "电源管理: 显示器已指令关闭。" "INFO"
    else
        log "警告: 无法控制显示器关闭，将继续执行任务。" "WARN"
    fi
fi

# 6. 增强的网络验证
check_network() {
    for target in "${NETWORK_TARGETS[@]}"; do
        if ping -c 1 -W 2 "$target" &> /dev/null; then
            return 0
        fi
    done
    return 1
}

log "网络验证: 正在检测网络连接..." "INFO"
RETRY_COUNT=0
MAX_RETRIES=30
WAIT_TIME=2

while ! check_network; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        log "网络恢复失败: 无法在预定时间内建立网络连接。" "ERROR"
        push_alert "自动化任务终止 (网络异常)" "无法在预定时间内建立网络连接。" "ERROR"
        exit 1
    fi
    log "网络未就绪，正在重试 ($RETRY_COUNT/$MAX_RETRIES)，等待 ${WAIT_TIME}s..." "WARN"
    sleep $WAIT_TIME
    # 逐渐增加等待时间 (退避算法)
    if [ $RETRY_COUNT -gt 10 ]; then WAIT_TIME=5; fi
done

log "网络验证: 连接成功。" "INFO"

# 7. 网络连接成功后等待
log "状态等待: 网络已就绪，等待 ${POST_NET_WAIT} 秒以确保系统服务稳定..." "INFO"
sleep $POST_NET_WAIT

# 8. 主逻辑执行
log "业务逻辑: 正在执行自动化核心任务..." "INFO"
if [ -f "/Users/axrid/Documents/EVM/information-ai/launch.command" ]; then
    /Users/axrid/Documents/EVM/information-ai/launch.command >> "$LOG_FILE" 2>&1 &
    BUSINESS_PID=$!
    wait $BUSINESS_PID
    RET=$?
    unset BUSINESS_PID
    
    if [ $RET -ne 0 ]; then
        log "核心任务执行失败，退出码: $RET" "ERROR"
        push_alert "自动化任务失败" "核心任务执行失败，退出码: $RET" "ERROR"
        exit $RET
    else
        log ">>> 自动化任务执行成功 <<<" "INFO"
        if [ -n "$PENDING_WARNING" ]; then
            push_alert "自动化任务完成 (附带警告)" "任务已执行成功，但预检发现以下问题：\n\n$PENDING_WARNING" "WARN"
        else
            push_alert "自动化任务圆满完成" "所有预检正常，核心任务执行成功。" "INFO"
        fi
    fi
else
    log "错误: 找不到启动脚本 /Users/axrid/Documents/EVM/information-ai/launch.command" "ERROR"
    push_alert "自动化任务失败" "找不到启动脚本 launch.command" "ERROR"
    exit 1
fi

log ">>> 脚本执行结束 <<<" "INFO"
exit 0
