#!/usr/bin/env python3
"""
尝试替代认证方法
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import config
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

async def try_alternative_auth():
    print("=" * 50)
    print("尝试替代认证方法")
    print("=" * 50)
    
    if not config.collector_accounts:
        print("❌ 未配置采集账号")
        return
    
    account = config.collector_accounts[0]
    print(f"账号: {account.phone}")
    print()
    
    # 删除旧的会话文件
    session_file = f"{account.session_name}.session"
    if os.path.exists(session_file):
        print(f"删除旧的会话文件: {session_file}")
        os.remove(session_file)
    
    print("创建新的客户端...")
    client = TelegramClient(
        account.session_name,
        account.api_id,
        account.api_hash
    )
    
    try:
        # 连接但不认证
        await client.connect()
        print("✅ 连接成功")
        
        # 尝试发送验证码请求
        print("发送验证码请求...")
        sent_code = await client.send_code_request(account.phone)
        print(f"✅ 验证码请求发送成功")
        print(f"验证码类型: {sent_code.type}")
        
        # 提示用户输入验证码
        print("\n" + "=" * 50)
        print("⚠️  验证码已发送到您的 Telegram 应用")
        print("   请在5分钟内输入验证码")
        print("=" * 50)
        
        # 获取验证码
        code = input("\n请输入验证码: ").strip()
        
        if not code:
            print("❌ 验证码不能为空")
            return
        
        print(f"使用验证码: {code}")
        
        try:
            # 使用验证码登录
            print("使用验证码登录...")
            await client.sign_in(account.phone, code, phone_code_hash=sent_code.phone_code_hash)
            print("✅ 登录成功！")
            
            # 保存会话
            await client.disconnect()
            
            print("\n" + "=" * 50)
            print("✅ 认证成功！")
            print(f"会话文件已保存: {account.session_name}.session")
            print("=" * 50)
            
            return True
            
        except SessionPasswordNeededError:
            print("⚠️  需要两步验证密码")
            password = input("请输入两步验证密码: ").strip()
            
            if password:
                await client.sign_in(password=password)
                print("✅ 两步验证成功！")
                
                # 保存会话
                await client.disconnect()
                
                print("\n" + "=" * 50)
                print("✅ 认证成功！")
                print(f"会话文件已保存: {account.session_name}.session")
                print("=" * 50)
                
                return True
            else:
                print("❌ 未提供两步验证密码")
                return False
                
        except Exception as e:
            print(f"❌ 登录失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("尝试替代认证方法...")
    print("注意：如果之前请求太频繁，可能仍然会被限制")
    print()
    
    success = await try_alternative_auth()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 认证成功！")
        print("\n现在可以运行数据采集：")
        print("  python3 collect_raw_data.py")
    else:
        print("❌ 认证失败")
        print("\n建议：")
        print("1. 等待24小时再尝试（Telegram 限制验证码频率）")
        print("2. 确保手机号 +86 YOUR_PHONE_NUMBER 正确")
        print("3. 检查 Telegram 应用是否正常工作")

if __name__ == "__main__":
    asyncio.run(main())