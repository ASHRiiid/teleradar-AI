#!/usr/bin/env python3
"""
简单的 Telegram 认证脚本
交互式输入验证码
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import config
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter

async def main():
    print("=" * 50)
    print("Telegram 首次连接认证")
    print("=" * 50)
    
    if not config.collector_accounts:
        print("❌ 错误：未配置采集账号")
        return
    
    account = config.collector_accounts[0]
    print(f"账号: {account.phone}")
    print(f"监控群组: {config.collector_config.monitored_chats}")
    print()
    print("⚠️  注意：验证码已发送到您的 Telegram 应用")
    print("    请在5分钟内输入验证码")
    print()
    
    # 获取验证码
    code = input("请输入验证码: ").strip()
    
    if not code:
        print("❌ 错误：验证码不能为空")
        return
    
    print(f"使用验证码: {code}")
    print("正在连接...")
    
    try:
        # 创建适配器
        adapter = TelegramMultiAccountAdapter()
        
        # 修改连接方法使用输入的验证码
        for session in adapter.collector_sessions.values():
            original_connect = session.connect
            
            async def patched_connect():
                try:
                    session.client = TelegramClient(
                        session.account_config.session_name,
                        session.account_config.api_id,
                        session.account_config.api_hash
                    )
                    
                    async def code_callback():
                        return code
                    
                    await session.client.start(
                        phone=session.account_config.phone,
                        code_callback=code_callback
                    )
                    
                    session.is_connected = True
                    print(f"✅ {session.account_config.account_id} 连接成功")
                except Exception as e:
                    print(f"❌ {session.account_config.account_id} 连接失败: {e}")
                    raise
            
            session.connect = patched_connect
        
        # 连接
        await adapter.connect_all()
        
        # 测试获取一条消息
        print("\n测试消息获取...")
        from datetime import datetime, timedelta
        import pytz
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        start_time = now - timedelta(minutes=30)
        
        start_time_utc = start_time.astimezone(pytz.utc).replace(tzinfo=None)
        end_time_utc = now.astimezone(pytz.utc).replace(tzinfo=None)
        
        messages = await adapter.fetch_messages_concurrently(
            config.collector_config.monitored_chats,
            start_time_utc,
            end_time_utc,
            limit_per_chat=3
        )
        
        print(f"✅ 获取到 {len(messages)} 条消息")
        
        if messages:
            print("\n最新消息:")
            for i, msg in enumerate(messages[:2]):
                preview = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
                print(f"  {i+1}. [{msg.timestamp.strftime('%H:%M')}] {preview}")
        
        # 断开连接
        await adapter.disconnect_all()
        
        print("\n" + "=" * 50)
        print("✅ 认证成功！")
        print("会话文件已保存，下次无需验证码")
        print("=" * 50)
        
        # 提示下一步
        print("\n🎉 现在可以运行完整的数据采集了:")
        print("  python3 collect_raw_data.py")
        
    except Exception as e:
        print(f"\n❌ 认证失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())