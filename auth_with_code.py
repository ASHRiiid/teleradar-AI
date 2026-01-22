#!/usr/bin/env python3
"""
带验证码输入的认证脚本
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
    print("=" * 60)
    print("Telegram 认证和数据采集")
    print("=" * 60)
    
    if not config.collector_accounts:
        print("❌ 错误：未配置采集账号")
        return
    
    account = config.collector_accounts[0]
    print(f"📱 账号: {account.phone}")
    print(f"👥 监控群组: {config.collector_config.monitored_chats}")
    print()
    
    # 获取验证码
    print("⚠️  验证码已发送到您的 Telegram 应用")
    print("   请在5分钟内输入验证码")
    print()
    
    # 创建临时验证码文件
    code_file = "/tmp/telegram_code.txt"
    
    print(f"请将验证码写入文件: {code_file}")
    print("例如: echo '123456' > {code_file}")
    print()
    print("等待验证码输入...")
    
    # 等待验证码文件被创建
    max_wait = 300  # 5分钟
    wait_interval = 5  # 每5秒检查一次
    
    for i in range(max_wait // wait_interval):
        if os.path.exists(code_file):
            try:
                with open(code_file, 'r') as f:
                    code = f.read().strip()
                if code:
                    print(f"✅ 读取到验证码: {code}")
                    os.remove(code_file)  # 删除临时文件
                    break
            except:
                code = ""
        else:
            print(f"⏳ 等待验证码... ({i * wait_interval}秒)")
            await asyncio.sleep(wait_interval)
    else:
        print("❌ 超时：未收到验证码")
        return
    
    print(f"使用验证码: {code}")
    print("正在连接 Telegram...")
    
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
        
        # 采集数据
        print("\n" + "=" * 60)
        print("开始数据采集...")
        print("=" * 60)
        
        from datetime import datetime, timedelta
        import pytz
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now_beijing = datetime.now(beijing_tz)
        
        # 今天的 08:00 (北京时间)
        today_08am = now_beijing.replace(hour=8, minute=0, second=0, microsecond=0)
        
        if now_beijing < today_08am:
            end_time = today_08am - timedelta(days=0)
        else:
            end_time = today_08am

        start_time = end_time - timedelta(days=1)
        
        print(f"采集时间窗口: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 到 {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 转换为 UTC
        start_time_utc = start_time.astimezone(pytz.utc).replace(tzinfo=None)
        end_time_utc = end_time.astimezone(pytz.utc).replace(tzinfo=None)
        
        messages = await adapter.fetch_messages_concurrently(
            config.collector_config.monitored_chats,
            start_time_utc,
            end_time_utc,
            limit_per_chat=100
        )
        
        print(f"✅ 采集完成: 获取到 {len(messages)} 条消息")
        
        # 保存到数据库
        from src.storage import Storage
        storage = Storage()
        
        count = 0
        for msg in messages:
            storage.save_message(msg)
            count += 1
        
        print(f"💾 保存了 {count} 条消息到数据库")
        
        if messages:
            print("\n📊 采集统计:")
            accounts_used = set()
            chats_covered = set()
            for msg in messages:
                accounts_used.add(msg.metadata.get('collector_account', 'unknown'))
                chats_covered.add(msg.metadata.get('chat', 'unknown'))
            
            print(f"   使用的采集账号: {', '.join(accounts_used)}")
            print(f"   覆盖的群组: {', '.join(chats_covered)}")
            print(f"   最早消息: {min(m.timestamp for m in messages).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   最晚消息: {max(m.timestamp for m in messages).strftime('%Y-%m-%d %H:%M:%S')}")
            
            print("\n📝 最新消息示例:")
            for i, msg in enumerate(messages[:3]):
                preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
                print(f"   {i+1}. [{msg.timestamp.strftime('%H:%M:%S')}] {preview}")
        
        # 测试频道推送
        if config.push_config.channel_username or config.push_config.channel_id:
            print("\n" + "=" * 60)
            print("测试频道推送...")
            print("=" * 60)
            
            test_message = f"📊 数据采集测试\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n采集账号: {account.account_id}\n消息数量: {len(messages)}条\n状态: 首次采集测试成功"
            
            success = await adapter.send_digest_to_channel(test_message)
            if success:
                print("✅ 测试消息已发送到频道")
            else:
                print("⚠️  测试消息发送失败（可能是权限问题）")
        
        # 断开连接
        await adapter.disconnect_all()
        
        print("\n" + "=" * 60)
        print("✅ 认证和数据采集完成！")
        print("=" * 60)
        
        print("\n🎉 成功！下一步:")
        print("1. 会话文件已保存，下次无需验证码")
        print("2. 可以设置定时任务自动运行采集")
        print("3. 运行数据分析脚本处理采集的数据")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())