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

async def list_dialogs():
    # 使用主账号配置
    main_account = config.main_account
    client = TelegramClient(
        main_account.session_name,
        main_account.api_id,
        main_account.api_hash
    )
    
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ 主账号未认证，请先完成认证")
        return
    
    dialogs = await client.get_dialogs()
    
    identifiers = []
    print("\n🔍 正在整理可用于监控的群组和频道标识符...\n")
    
    for dialog in dialogs:
        if dialog.is_group or dialog.is_channel:
            entity = dialog.entity
            # 优先使用 username，如果没有则使用 ID
            if getattr(entity, 'username', None):
                identifiers.append(f"@{entity.username}")
            else:
                identifiers.append(str(entity.id))

    if identifiers:
        print("✅ 整理完成！MONITORED_CHATS 格式如下：")
        print(",".join(identifiers))
    else:
        print("⚠️ 未发现已加入的群组或频道。")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(list_dialogs())
