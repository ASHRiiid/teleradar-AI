#!/usr/bin/env python3
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_channel_access():
    """测试主账号是否能访问频道"""
    from telethon import TelegramClient
    
    # 主账号配置
    api_id = int(os.getenv("TELEGRAM_MAIN_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_MAIN_API_HASH", "")
    phone = os.getenv("TELEGRAM_MAIN_PHONE", "")
    channel_username = os.getenv("TELEGRAM_CHANNEL_USERNAME", "@HDXSradar")
    
    print(f"测试配置:")
    print(f"  API ID: {api_id}")
    print(f"  API Hash: {api_hash[:10]}...")
    print(f"  手机号: {phone}")
    print(f"  频道: {channel_username}")
    
    client = TelegramClient("test_main_session", api_id, api_hash)
    
    try:
        # 定义验证码回调函数
        async def code_callback():
            import sys
            print(f"\n⚠️  验证码已发送到 {phone}")
            print("请在 Telegram 应用中查看最新的验证码")
            code = input("请输入验证码: ").strip()
            return code
        
        # 定义密码回调函数
        async def password_callback():
            password = input(f"请输入两步验证密码（如果设置了）: ")
            return password.strip()
        
        # 启动客户端
        await client.start(
            phone=phone,
            code_callback=code_callback,
            password=password_callback
        )
        
        print(f"\n✅ 主账号连接成功")
        
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
    asyncio.run(test_channel_access())