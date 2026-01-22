#!/usr/bin/env python3
"""
测试完整工作流程
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import config
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter
from telethon import TelegramClient

async def test_full_workflow():
    print("=" * 50)
    print("测试完整工作流程")
    print("=" * 50)
    
    # 1. 测试采集账号连接
    print("\n1. 测试采集账号连接...")
    if not config.collector_accounts:
        print("❌ 未配置采集账号")
        return False
    
    collector_account = config.collector_accounts[0]
    collector_session = f"{collector_account.session_name}.session"
    
    if not os.path.exists(collector_session):
        print(f"❌ 采集账号会话文件不存在: {collector_session}")
        return False
    
    print(f"✅ 采集账号会话文件存在: {collector_session}")
    
    # 2. 测试主账号连接
    print("\n2. 测试主账号连接...")
    if not config.main_account:
        print("❌ 未配置主账号")
        return False
    
    main_account = config.main_account
    main_session = f"{main_account.session_name}.session"
    
    if not os.path.exists(main_session):
        print(f"❌ 主账号会话文件不存在: {main_session}")
        return False
    
    print(f"✅ 主账号会话文件存在: {main_session}")
    
    # 3. 测试频道连接
    print("\n3. 测试频道连接...")
    channel_username = config.push_config.channel_username
    if not channel_username:
        print("❌ 未配置频道用户名")
        return False
    
    print(f"✅ 频道用户名配置: {channel_username}")
    
        # 4. 测试Telegram适配器
        print("\n4. 测试Telegram适配器...")
        try:
            adapter = TelegramMultiAccountAdapter()
            print("✅ Telegram适配器初始化成功")
        
        # 测试采集功能
        print("\n5. 测试采集功能...")
        messages = await adapter.collect_messages(
            monitored_chats=[config.monitored_chats[0]],
            hours_back=24
        )
        print(f"✅ 采集功能正常，采集到 {len(messages)} 条消息")
        
        if messages:
            for i, msg in enumerate(messages[:3], 1):
                print(f"  消息 {i}: {msg.content[:50]}...")
        
        # 测试推送功能
        print("\n6. 测试推送功能...")
        test_message = "📊 系统测试消息\n\n" \
                      "✅ Telegram 信息自动化系统运行正常\n" \
                      "📅 时间: 2026-01-22\n" \
                      "🔧 状态: 所有功能就绪\n" \
                      "📈 监控群组: RaccoonDegen\n" \
                      "📢 推送频道: HDXSradar"
        
        success = await adapter.push_to_channel(test_message)
        if success:
            print("✅ 推送功能正常")
        else:
            print("❌ 推送功能失败")
            return False
        
        print("\n" + "=" * 50)
        print("✅ 完整工作流程测试成功！")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("测试 Telegram 信息自动化系统完整工作流程")
    print()
    
    success = await test_full_workflow()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 系统测试完成！")
        print("\n系统状态：")
        print("  ✅ 采集账号认证正常")
        print("  ✅ 主账号认证正常")
        print("  ✅ 频道连接正常")
        print("  ✅ 采集功能正常")
        print("  ✅ 推送功能正常")
        print("\n系统已准备好自动运行！")
        print("\n建议运行：")
        print("  1. python3 collect_raw_data.py  # 定时采集")
        print("  2. 设置定时任务（cron）每小时运行一次")
    else:
        print("❌ 系统测试失败")
        print("\n需要检查：")
        print("  1. 会话文件是否存在")
        print("  2. 频道用户名是否正确")
        print("  3. 网络连接是否正常")

if __name__ == "__main__":
    asyncio.run(main())