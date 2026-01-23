import asyncio
import os
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
    
    for dialog in dialogs:
        if dialog.is_group or dialog.is_channel:
            name = dialog.name
            entity = dialog.entity
            
            # 获取标识符
            if getattr(entity, 'username', None) and entity.username:
                identifier = f"@{entity.username}"
            else:
                identifier = str(entity.id)
            
            # 默认全部注释掉，方便用户选择
            md_lines.append(f"# {name} | {identifier}")
    
    with open("setting_collector2.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    
    print(f"✨ 成功生成配置文件: setting_collector2.md")
    print(f"👉 请在该文件中取消注释您想监控的频道，然后运行 sync_settings_to_env.py")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(generate_setting_file())
