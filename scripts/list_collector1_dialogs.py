import asyncio
import os
import sys
import re

# Ensure we can import from src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from telethon import TelegramClient
from src.config import config
from telethon.tl.types import Channel, Chat

def fix_id_format(identifier: str) -> str:
    """处理标识符，如果是 10 位纯正整数则添加 -100 前缀"""
    identifier = identifier.strip()
    # 仅当它是恰好 10 位数字的正整数时才添加 -100 (超级群组常见格式)
    if identifier.isdigit() and len(identifier) == 10:
        return f"-100{identifier}"
    return identifier

def update_env_file(monitored_chats: list):
    """直接更新.env文件中的MONITORED_CHATS_COLLECTOR1配置"""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print(f"❌ 找不到 .env 文件")
        return False
    
    # 读取现有配置
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    new_lines = []
    found_c1 = False
    c1_str = ",".join(monitored_chats)
    
    for line in lines:
        if re.match(r"^#?\s*MONITORED_CHATS_COLLECTOR1\s*=", line):
            new_lines.append(f"MONITORED_CHATS_COLLECTOR1={c1_str}\n")
            found_c1 = True
        else:
            new_lines.append(line)
    
    if not found_c1:
        # 如果没找到，添加到文件末尾
        new_lines.append(f"\nMONITORED_CHATS_COLLECTOR1={c1_str}\n")
    
    # 写入更新
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    
    print(f"✅ 已更新 .env 文件: MONITORED_CHATS_COLLECTOR1={len(monitored_chats)}个频道")
    return True

async def generate_setting_file():
    # 查找 collector1 配置
    collector1_config = next((acc for acc in config.collector_accounts if acc.account_id == "collector1"), None)
    
    if not collector1_config:
        print("❌ 未在配置中找到 collector1。请检查 .env 是否正确设置。")
        return

    client = TelegramClient(
        collector1_config.session_name,
        collector1_config.api_id,
        collector1_config.api_hash
    )
    
    print(f"📡 正在连接采集账号 1 ({collector1_config.phone})...")
    await client.connect()
    
    if not await client.is_user_authorized():
        print("🔑 采集账号 1 需要认证。")
        # 这里的认证逻辑已经在 list_collector2_dialogs.py 中演示过，
        # 如果用户已经有 session 文件则会自动跳过
        try:
            await client.send_code_request(collector1_config.phone)
            code = input("请输入 Telegram 发送给您的验证码: ")
            await client.sign_in(collector1_config.phone, code)
        except Exception as e:
            print(f"❌ 认证失败: {e}")
            return
    
    print("✅ 认证成功！正在获取群组列表...")
    dialogs = await client.get_dialogs()
    
    # 收集所有群组和频道的标识符
    monitored_chats = []
    
    for dialog in dialogs:
        if dialog.is_group or dialog.is_channel:
            entity = dialog.entity
            
            # 获取标识符
            if getattr(entity, 'username', None) and entity.username:
                identifier = f"@{entity.username}"
            else:
                identifier = str(entity.id)
            
            # 格式化标识符
            formatted_identifier = fix_id_format(identifier)
            monitored_chats.append(formatted_identifier)
    
    print(f"📊 找到 {len(monitored_chats)} 个群组/频道")
    
    # 直接更新.env文件
    if update_env_file(monitored_chats):
        print("🚀 采集账号1配置已自动更新完成！")
        print("👉 下次运行采集程序时，将自动监控这些群组")
    else:
        print("❌ 更新.env文件失败")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(generate_setting_file())
