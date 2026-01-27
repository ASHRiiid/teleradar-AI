#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_channel():
    """测试主账号是否能访问频道"""
    from telethon import TelegramClient
    
    # 主账号配置
    api_id = int(os.getenv("TELEGRAM_MAIN_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_MAIN_API_HASH", "")
    channel_username = os.getenv("TELEGRAM_CHANNEL_USERNAME", "@HDXSradar")
    
    print(f"测试配置:")
    print(f"  API ID: {api_id}")
    print(f"  API Hash: {api_hash[:10]}...")
    print(f"  频道: {channel_username}")
    
    # 检查会话文件
    session_file = "main_session.session"
    if not os.path.exists(session_file):
        print(f"❌ 会话文件不存在: {session_file}")
        return
    
    print(f"✅ 会话文件存在: {session_file}")
    
    client = TelegramClient(session_file, api_id, api_hash)
    
    try:
        # 尝试连接（使用现有会话）
        await client.connect()
        
        # 检查是否已授权
        if not await client.is_user_authorized():
            print("❌ 会话未授权，需要重新登录")
            return
        
        print("✅ 主账号已授权")
        
        # 获取当前用户信息
        me = await client.get_me()
        print(f"✅ 当前用户: {me.first_name} (@{me.username})")
        
        # 尝试获取频道信息
        try:
            print(f"\n尝试获取频道信息: {channel_username}")
            channel = await client.get_entity(channel_username)
            print(f"✅ 成功获取频道信息:")
            print(f"   频道ID: {channel.id}")
            print(f"   频道名称: {getattr(channel, 'title', 'N/A')}")
            print(f"   用户名: {getattr(channel, 'username', 'N/A')}")
            
            # 检查是否有发送消息的权限
            print(f"\n检查发送权限...")
            try:
                # 尝试发送一条测试消息
                test_message = "🤖 测试消息: 这是来自信息AI系统的测试消息"
                sent_message = await client.send_message(channel, test_message)
                print(f"✅ 测试消息发送成功!")
                print(f"   消息ID: {sent_message.id}")
                
                # 删除测试消息
                await client.delete_messages(channel, [sent_message.id])
                print(f"✅ 测试消息已删除")
                
            except Exception as e:
                print(f"❌ 发送消息失败: {e}")
                print(f"   错误类型: {type(e).__name__}")
                
        except Exception as e:
            print(f"❌ 获取频道信息失败: {e}")
            print(f"   错误类型: {type(e).__name__}")
            
            # 尝试其他可能的格式
            print(f"\n尝试其他格式...")
            # 尝试去掉@符号
            if channel_username.startswith("@"):
                try:
                    channel = await client.get_entity(channel_username[1:])
                    print(f"✅ 成功获取频道信息 (去掉@符号):")
                    print(f"   频道ID: {channel.id}")
                    print(f"   频道名称: {getattr(channel, 'title', 'N/A')}")
                except Exception as e2:
                    print(f"❌ 仍然失败: {e2}")
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    finally:
        await client.disconnect()
        print(f"\n✅ 客户端已断开")

if __name__ == "__main__":
    asyncio.run(test_channel())