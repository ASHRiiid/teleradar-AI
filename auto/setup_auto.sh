#!/bin/bash

# =================================================================
# 自动化安装与配置脚本 (Setup Automation)
# Path: /Users/axrid/Documents/EVM/information-ai/auto/setup_auto.sh
# 功能：一键配置 macOS 自动化任务 (launchd + pmset)
# =================================================================

# --- 1. 配置参数 ---
PROJECT_DIR="/Users/axrid/Documents/EVM/information-ai"
AUTO_DIR="${PROJECT_DIR}/auto"
WRAPPER_SCRIPT="${AUTO_DIR}/auto_wake_run.sh"
LOG_FILE="${AUTO_DIR}/auto_setup.log"
PLIST_LABEL="com.antigravity.evm.auto"
PLIST_PATH="${HOME}/Library/LaunchAgents/${PLIST_LABEL}.plist"

# 默认运行时间 (24小时制)
WAKE_TIME="08:00:00"
SCHEDULE_HOUR=8
SCHEDULE_MINUTE=0

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- 2. 辅助函数 ---
log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$message"
    echo "$message" >> "$LOG_FILE" 2>/dev/null
}

error_exit() {
    log "${RED}❌ 错误: $1${NC}"
    exit 1
}

# --- 3. 安装功能 ---
install_auto() {
    log "${BLUE}开始安装自动化流程...${NC}"

    # 3.1 检查必要文件
    log "检查必要文件..."
    [ -d "$PROJECT_DIR" ] || error_exit "项目目录不存在: $PROJECT_DIR"
    [ -f "$WRAPPER_SCRIPT" ] || error_exit "包装脚本不存在: $WRAPPER_SCRIPT"
    [ -f "${PROJECT_DIR}/launch.command" ] || error_exit "launch.command 不存在"

    # 3.2 设置权限
    log "设置脚本执行权限..."
    chmod +x "$WRAPPER_SCRIPT" || error_exit "无法设置权限: $WRAPPER_SCRIPT"
    chmod +x "${PROJECT_DIR}/launch.command" || error_exit "无法设置权限: launch.command"
    log "${GREEN}✅ 权限设置完成${NC}"

    # 3.3 配置业务逻辑 (注入到 auto_wake_run.sh)
    log "配置业务逻辑关联..."
    # 检查是否已经注入过
    if grep -q "launch.command" "$WRAPPER_SCRIPT"; then
        log "${YELLOW}提示: 业务逻辑已在 $WRAPPER_SCRIPT 中配置过，跳过。${NC}"
    else
        sed -i '' "s|# /usr/local/bin/node /path/to/your/app.js >> \"\$LOG_FILE\" 2>\&1|cd \"${PROJECT_DIR}\" \&\& ./launch.command >> \"\$LOG_FILE\" 2>\&1|g" "$WRAPPER_SCRIPT"
        log "${GREEN}✅ 业务逻辑关联成功${NC}"
    fi

    # 3.4 创建 launchd 配置 (Plist)
    log "创建 LaunchAgent 配置文件..."
    cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${WRAPPER_SCRIPT}</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>${SCHEDULE_HOUR}</integer>
            <key>Minute</key>
            <integer>${SCHEDULE_MINUTE}</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>${AUTO_DIR}/auto_wake.log</string>
    <key>StandardErrorPath</key>
    <string>${AUTO_DIR}/auto_wake.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF
    log "${GREEN}✅ 已生成: $PLIST_PATH${NC}"

    # 3.5 加载 launchd 任务
    log "加载并启用 launchd 任务..."
    launchctl unload "$PLIST_PATH" 2>/dev/null
    launchctl load "$PLIST_PATH" || error_exit "launchctl load 失败"
    log "${GREEN}✅ 自动化任务已启动${NC}"

    # 3.6 配置电源管理 (pmset)
    log "配置系统电源唤醒计划..."
    log "计划时间: 每天 ${WAKE_TIME} (提前 5 分钟唤醒)"
    # 计算唤醒时间 (提前5分钟)
    local WAKE_H=$(printf "%02d" $(( ($SCHEDULE_HOUR * 60 + $SCHEDULE_MINUTE - 5 + 1440) / 60 % 24 )))
    local WAKE_M=$(printf "%02d" $(( ($SCHEDULE_HOUR * 60 + $SCHEDULE_MINUTE - 5 + 1440) % 60 )))
    
    log "正在执行: sudo pmset repeat wakeorpoweron MTWRFSU ${WAKE_H}:${WAKE_M}:00"
    echo "请输入系统密码以配置电源管理："
    sudo pmset repeat wakeorpoweron MTWRFSU "${WAKE_H}:${WAKE_M}:00" || log "${YELLOW}警告: 电源管理设置失败，请检查权限。${NC}"
    
    log "${GREEN}🎉 自动化系统安装完成！${NC}"
    show_status
}

# --- 4. 卸载功能 ---
uninstall_auto() {
    log "${YELLOW}正在清理自动化配置...${NC}"

    # 4.1 停止 launchd
    if [ -f "$PLIST_PATH" ]; then
        log "停止并移除 launchd 任务..."
        launchctl unload "$PLIST_PATH" 2>/dev/null
        rm "$PLIST_PATH"
        log "${GREEN}✅ 已移除 Plist${NC}"
    fi

    # 4.2 清除 pmset
    log "清除电源唤醒计划..."
    sudo pmset repeat cancel 2>/dev/null
    log "${GREEN}✅ 已清除电源计划${NC}"

    # 4.3 还原脚本变更 (可选)
    log "还原脚本占位符..."
    sed -i '' "s|cd \"${PROJECT_DIR}\" \&\& ./launch.command >> \"\$LOG_FILE\" 2>\&1|# /usr/local/bin/node /path/to/your/app.js >> \"\$LOG_FILE\" 2>\&1|g" "$WRAPPER_SCRIPT"

    log "${GREEN}✅ 卸载完成。${NC}"
}

# --- 5. 状态查询 ---
show_status() {
    echo -e "\n${BLUE}=== 自动化运行状态 ===${NC}"
    
    # 检查 launchd
    if launchctl list | grep -q "$PLIST_LABEL"; then
        echo -e "LaunchAgent 状态: ${GREEN}运行中 (Active)${NC}"
    else
        echo -e "LaunchAgent 状态: ${RED}未加载 (Inactive)${NC}"
    fi

    # 检查 Plist
    if [ -f "$PLIST_PATH" ]; then
        echo -e "Plist 配置文件: ${GREEN}存在${NC} ($PLIST_PATH)"
    else
        echo -e "Plist 配置文件: ${RED}不存在${NC}"
    fi

    # 检查电源计划
    echo "电源计划 (pmset repeat):"
    pmset -g sched | grep "wake" || echo "  [未发现唤醒计划]"

    # 检查权限
    echo "脚本权限:"
    ls -l "$WRAPPER_SCRIPT" | awk '{print "  " $1 " " $9}'
    ls -l "${PROJECT_DIR}/launch.command" | awk '{print "  " $1 " " $9}'

    # 最近日志
    if [ -f "${AUTO_DIR}/auto_wake.log" ]; then
        echo -e "\n最近运行日志 (最后 3 行):"
        tail -n 3 "${AUTO_DIR}/auto_wake.log" | sed 's/^/  /'
    fi
    echo -e "${BLUE}=====================${NC}\n"
}

# --- 6. 执行入口 ---
case "$1" in
    install)
        install_auto
        ;;
    uninstall)
        uninstall_auto
        ;;
    status)
        show_status
        ;;
    *)
        echo "用法: $0 {install|uninstall|status}"
        echo "  install   - 安装并启动所有自动化任务"
        echo "  uninstall - 停止并移除所有自动化任务"
        echo "  status    - 查看当前运行状态"
        exit 1
        ;;
esac
