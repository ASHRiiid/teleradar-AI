#!/usr/bin/env python3
"""
测试现有会话文件
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import config
from telethon import TelegramClient

async def test_session():
    print("=" * 50)
    print("测试现有会话文件")
    print("=" * 50)
    
    if not config.collector_accounts:
        print("❌ 未配置采集账号")
        return
    
    account = config.collector_accounts[0]
    print(f"账号: {account.account_id}")
    print(f"会话文件: {account.session_name}.session")
    print(f"API ID: {account.api_id}")
    print()
    
    # 检查会话文件
    session_file = f"{account.session_name}.session"
    if not os.path.exists(session_file):
        print(f"❌ 会话文件不存在: {session_file}")
        return
    
    print(f"✅ 找到会话文件: {session_file} ({os.path.getsize(session_file)} bytes)")
    
    # 尝试连接
    print("\n尝试连接...")
    try:
        client = TelegramClient(
            account.session_name,
            account.api_id,
            account.api_hash
        )
        
        # 尝试连接，不要求验证码
        await client.connect()
        
        # 检查是否已认证
        if await client.is_user_authorized():
            print("✅ 连接成功！用户已认证")
            
            # 获取用户信息
            me = await client.get_me()
            print(f"👤 用户: {me.first_name} {me.last_name or ''} (@{me.username or '无用户名'})")
            print(f"📱 手机号: {me.phone}")
            
            # 测试获取一个群组信息
            print("\n测试群组访问...")
            try:
                chat = await client.get_entity(config.collector_config.monitored_chats[0])
                print(f"✅ 可以访问群组: {chat.title}")
                
                # 获取最近3条消息
                print("\n获取最新消息...")
                messages = []
                async for message in client.iter_messages(chat, limit=3):
                    if message.text:
                        messages.append(message)
                
                print(f"✅ 获取到 {len(messages)} 条消息")
                for i, msg in enumerate(messages):
                    preview = msg.text[:60] + "..." if len(msg.text) > 60 else msg.text
                    print(f"  {i+1}. [{msg.date.strftime('%H:%M:%S')}] {preview}")
                
            except Exception as e:
                print(f"⚠️  群组访问失败: {e}")
            
            await client.disconnect()
            print("\n✅ 测试完成！会话文件有效")
            return True
            
        else:
            print("❌ 用户未认证，需要重新登录")
            # 尝试重新登录
            print("尝试重新登录...")
            try:
                await client.start(phone=account.phone)
                print("✅ 重新登录成功")
                await client.disconnect()
                return True
            except Exception as e:
                print(f"❌ 重新登录失败: {e}")
                return False
                
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_session()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 会话文件测试成功！")
        print("\n现在可以运行数据采集：")
        print("  python3 collect_raw_data.py")
    else:
        print("❌ 会话文件测试失败")
        print("\n可能的解决方案：")
        print("1. 删除会话文件重新认证")
        print("2. 等待24小时再尝试获取验证码")
        print("3. 检查手机号是否正确")

if __name__ == "__main__":
    asyncio.run(main())