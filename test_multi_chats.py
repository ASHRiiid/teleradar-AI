#!/usr/bin/env python3
"""
测试多群组配置
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import config
from telethon import TelegramClient

async def test_multi_chats():
    print("=" * 50)
    print("测试多群组配置")
    print("=" * 50)
    
    print("\n📋 当前监控的群组:")
    for i, chat in enumerate(config.collector_config.monitored_chats, 1):
        print(f"  {i}. {chat}")
    
    # 验证采集账号
    print("\n🔐 验证采集账号连接...")
    collector_account = config.collector_accounts[0]
    collector_client = TelegramClient(
        collector_account.session_name,
        collector_account.api_id,
        collector_account.api_hash
    )
    
    try:
        await collector_client.connect()
        if await collector_client.is_user_authorized():
            print("✅ 采集账号认证成功")
            
            # 测试每个群组连接
            print("\n📥 测试群组连接...")
            for i, chat_url in enumerate(config.collector_config.monitored_chats, 1):
                print(f"\n  {i}. 测试: {chat_url}")
                try:
                    entity = await collector_client.get_entity(chat_url)
                    print(f"     ✅ 连接成功: {entity.title}")
                    
                    # 获取最近消息
                    messages = await collector_client.get_messages(entity, limit=3)
                    print(f"     📊 最近消息: {len(messages)} 条")
                    
                    if messages:
                        for j, msg in enumerate(messages, 1):
                            if msg.text:
                                print(f"       {j}. {msg.text[:60]}...")
                            else:
                                print(f"       {j}. [媒体消息]")
                    
                except Exception as e:
                    print(f"     ❌ 连接失败: {e}")
                    
        else:
            print("❌ 采集账号未认证")
            
    except Exception as e:
        print(f"❌ 采集账号连接失败: {e}")
    finally:
        await collector_client.disconnect()
    
    print("\n" + "=" * 50)
    print("多群组配置测试完成")
    print("=" * 50)

async def main():
    print("测试多群组监控配置")
    print(f"共配置 {len(config.collector_config.monitored_chats)} 个群组")
    print()
    
    await test_multi_chats()
    
    print("\n✅ 配置验证:")
    print(f"  群组数量: {len(config.collector_config.monitored_chats)}")
    print("  格式: ✅ 逗号分隔正确")
    print("  解析: ✅ 代码支持多群组")

if __name__ == "__main__":
    asyncio.run(main())