import asyncio
import os
import sys

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from telethon import TelegramClient
from src.config import config
from telethon.tl.types import Channel, Chat

async def generate_setting_file():
    # 查找 collector2 配置
    collector2_config = next((acc for acc in config.collector_accounts if acc.account_id == "collector2"), None)
    
    if not collector2_config:
        print("❌ 未在配置中找到 collector2。请检查 .env 是否正确设置。")
        return

    client = TelegramClient(
        collector2_config.session_name,
        collector2_config.api_id,
        collector2_config.api_hash
    )
    
    print(f"📡 正在连接采集账号 2 ({collector2_config.phone})...")
    await client.connect()
    
    if not await client.is_user_authorized():
        print("🔑 需要认证。请在下方输入验证码：")
        try:
            await client.send_code_request(collector2_config.phone)
            code = input("请输入 Telegram 发送给您的验证码: ")
            await client.sign_in(collector2_config.phone, code)
        except Exception as e:
            print(f"❌ 认证失败: {e}")
            return
    
    print("✅ 认证成功！正在获取群组列表...")
    dialogs = await client.get_dialogs()
    
    # 读取现有配置文件（如果存在）
    existing_channels = {}
    existing_header = []
    setting_file = "setting_collector2.md"
    
    if os.path.exists(setting_file):
        with open(setting_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 提取现有频道和注释状态
        for line in lines:
            stripped = line.strip()
            if '|' in stripped:
                # 保存原始行（包括注释状态）
                existing_channels[stripped] = True
            else:
                # 保存头部内容
                existing_header.append(line.rstrip('\n'))
    
    # 构建新的频道列表
    new_channels = []
    for dialog in dialogs:
        if dialog.is_group or dialog.is_channel:
            name = dialog.name
            entity = dialog.entity
            
            # 获取标识符
            if getattr(entity, 'username', None) and entity.username:
                identifier = f"@{entity.username}"
            else:
                identifier = str(entity.id)
            
            channel_line = f"# {name} | {identifier}"
            
            # 检查是否已存在（包括注释状态）
            found = False
            for existing_line in existing_channels.keys():
                if identifier in existing_line:
                    # 使用现有的行（保持注释状态）
                    new_channels.append(existing_line)
                    found = True
                    break
            
            if not found:
                # 新频道，以注释方式添加
                new_channels.append(channel_line)
    
    # 构建最终内容
    if existing_header:
        # 使用现有头部
        md_lines = existing_header
    else:
        # 使用默认头部
        md_lines = [
            "# 🤖 采集账号 2 监控配置清单",
            "# 说明：",
            "# 1. 下面列出了该账号加入的所有群组和频道。",
            "# 2. 去掉行首的 '#' 号即代表启用监控该频道。",
            "# 3. 保存后，运行 'python3 sync_settings_to_env.py' 即可同步到 .env 文件。",
            "",
            "## 📢 频道与群组列表",
            ""
        ]
    
    # 添加频道列表
    md_lines.extend(new_channels)
    
    # 写入文件
    with open(setting_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
    
    # 统计信息
    total_channels = len(new_channels)
    existing_count = len([line for line in new_channels if any(identifier in line for identifier in [line.split('|')[1].strip() for line in existing_channels.keys()])])
    new_count = total_channels - existing_count
    
    print(f"✨ 成功更新配置文件: {setting_file}")
    print(f"📊 统计信息:")
    print(f"  - 总频道数: {total_channels}")
    print(f"  - 保留现有频道: {existing_count} 个（保持原注释状态）")
    print(f"  - 新增频道: {new_count} 个（以注释方式添加）")
    print(f"👉 请在该文件中取消注释您想监控的频道，然后运行 sync_settings_to_env.py")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(generate_setting_file())
