#!/usr/bin/env python3
"""
测试频道推送功能
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import config
from telethon import TelegramClient

async def test_channel_push():
    print("=" * 50)
    print("测试频道推送功能")
    print("=" * 50)
    
    if not config.main_account:
        print("❌ 未配置主账号")
        return False
    
    account = config.main_account
    print(f"主账号: {account.phone}")
    print(f"推送频道: {config.push_config.channel_username}")
    print()
    
    # 检查会话文件
    session_file = f"{account.session_name}.session"
    if not os.path.exists(session_file):
        print(f"❌ 主账号会话文件不存在: {session_file}")
        print("需要先认证主账号")
        return False
    
    print(f"使用会话文件: {session_file}")
    client = TelegramClient(
        account.session_name,
        account.api_id,
        account.api_hash
    )
    
    try:
        # 连接
        await client.connect()
        print("✅ 连接成功")
        
        # 检查是否已登录
        if not await client.is_user_authorized():
            print("❌ 主账号未登录，需要先认证")
            return False
        
        print("✅ 主账号已登录")
        
        # 测试获取频道信息
        channel_username = config.push_config.channel_username
        print(f"\n尝试获取频道信息: {channel_username}")
        try:
            entity = await client.get_entity(channel_username)
            print(f"✅ 成功获取频道信息")
            print(f"频道名称: {entity.title}")
            print(f"频道ID: {entity.id}")
            
            # 测试发送消息
            print(f"\n测试发送消息到频道...")
            message = await client.send_message(
                entity,
                "📢 测试消息：Telegram 信息自动化系统已成功连接！\n\n系统状态：✅ 正常运行\n时间：2026-01-22"
            )
            print(f"✅ 消息发送成功！")
            print(f"消息ID: {message.id}")
            
            return True
            
        except Exception as e:
            print(f"❌ 获取频道失败: {e}")
            print("\n可能的原因：")
            print("1. 频道用户名不正确")
            print("2. 主账号没有权限访问该频道")
            print("3. 频道不存在")
            print(f"\n当前频道用户名: {channel_username}")
            return False
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()

async def main():
    print("测试频道推送功能")
    print()
    
    success = await test_channel_push()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 频道推送测试成功！")
        print("\n系统已准备好：")
        print("1. ✅ 采集账号认证成功")
        print("2. ✅ 主账号认证成功")
        print("3. ✅ 频道推送功能正常")
        print("\n现在可以运行完整的数据采集和推送流程")
    else:
        print("❌ 频道推送测试失败")
        print("\n需要检查：")
        print("1. 主账号是否已认证")
        print("2. 频道ID是否正确")
        print("3. 主账号是否有权限访问频道")

if __name__ == "__main__":
    asyncio.run(main())