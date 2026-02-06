#!/bin/bash

# ============================================
# 区块链信息简报生成脚本 - 内部执行
# 由 launch.command 调用，后台静默执行
# ============================================

exec 2>&1  # 重定向 stderr 到 stdout

echo "🚀 开始区块链信息简报生成流程"
echo "========================================="

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查并激活虚拟环境
echo "🐍 检查Python虚拟环境..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ 已激活 venv 虚拟环境"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ 已激活 .venv 虚拟环境"
else
    echo "⚠️  未找到虚拟环境，使用系统Python"
fi

# 1. 检查环境变量
echo "📋 步骤1: 检查环境变量配置"
if [ ! -f ".env" ]; then
    echo "❌ 错误: .env 文件不存在"
    exit 1
fi
echo "✅ 环境变量文件存在"

# 2. 检查配置文件更新
echo "📋 步骤2: 检查配置文件更新"
echo "-----------------------------------------"

# 检查setting_AI.md是否有更新
if [ -f "setting_AI.md" ]; then
    echo "🔍 检查 setting_AI.md 更新..."
    if grep -q "代码变更" setting_AI.md || grep -q "需要修改" setting_AI.md; then
        echo "⚠️  检测到 setting_AI.md 中包含代码变更要求"
    else
        echo "✅ setting_AI.md 无需代码变更，仅提示词更新"
    fi
else
    echo "❌ setting_AI.md 文件不存在"
    exit 1
fi

# 3. 检查采集账号配置并同步到环境变量
echo "-----------------------------------------"
echo "🔄 同步采集配置到环境变量..."

# 更新采集账号1的群组列表
echo "📱 步骤1: 更新采集账号1的群组列表..."
if [ -f "scripts/list_collector1_dialogs.py" ]; then
    echo "   🔍 正在获取账号1加入的所有群组..."
    python3 scripts/list_collector1_dialogs.py
    if [ $? -eq 0 ]; then
        echo "   ✅ 账号1群组列表更新完成"
    else
        echo "   ⚠️  账号1群组列表更新失败，继续使用现有配置"
    fi
fi

# 同步所有配置到环境变量
echo "📱 步骤2: 同步配置到环境变量..."
if [ -f "scripts/sync_settings_to_env.py" ]; then
    python3 scripts/sync_settings_to_env.py
    if [ $? -eq 0 ]; then
        echo "   ✅ 频道配置同步完成"
    else
        echo "   ❌ 频道配置同步失败"
        exit 1
    fi
fi

# 4. 检查数据库状态
echo "📋 步骤3: 检查数据库状态"
echo "-----------------------------------------"
if [ -d "data" ]; then
    DB_FILES=$(find data -name "*.db" -type f | wc -l)
    if [ $DB_FILES -eq 0 ]; then
        echo "⚠️  数据库目录为空，将创建新数据库"
    else
        echo "✅ 发现 ${DB_FILES} 个数据库文件"
    fi
else
    echo "📁 创建数据目录"
    mkdir -p data
fi

# 5. 运行简报生成脚本
echo "📋 步骤4: 生成24小时深度简报"
echo "-----------------------------------------"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 运行简报生成
python3 process_24h_report.py
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 简报生成成功"
    
    # 检查是否生成了简报文件
    if [ -d "obsidian-tem" ]; then
        LATEST_REPORT=$(ls -t obsidian-tem/简报_*.md 2>/dev/null | head -1)
        if [ -n "$LATEST_REPORT" ]; then
            echo "📄 最新简报: $(basename $LATEST_REPORT)"
        fi
    fi
else
    echo "❌ 简报生成失败，退出码: $EXIT_CODE"
    exit $EXIT_CODE
fi

# 6. 管理旧简报文件
echo "📋 步骤5: 管理旧简报文件"
echo "-----------------------------------------"
echo "📂 将超过一周的简报移动到 Oldsletters 文件夹..."

if [ -f "scripts/manage_obsidian_reports.py" ]; then
    python3 scripts/manage_obsidian_reports.py
    if [ $? -eq 0 ]; then
        echo "✅ 旧简报文件管理完成"
    else
        echo "⚠️  旧简报文件管理过程中出现警告"
    fi
fi

# 7. 流程完成
echo "📋 步骤6: 流程完成"
echo "-----------------------------------------"
echo "完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "✅ 区块链信息简报生成流程执行完毕"
echo ""
echo "📱 简报已推送到 Telegram 频道: @HDXSradar"
echo "💾 本地备份已保存到 obsidian-tem/ 目录"

exit 0
