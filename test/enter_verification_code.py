#!/usr/bin/env python3
"""
手动输入验证码完成认证
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

async def complete_auth_with_code():
    print("=" * 50)
    print("手动输入验证码完成认证")
    print("=" * 50)
    
    if not config.collector_accounts:
        print("❌ 未配置采集账号")
        return False
    
    account = config.collector_accounts[0]
    print(f"账号: {account.phone}")
    print()
    
    # 使用用户提供的验证码
    code = "216765"
    print(f"使用验证码: {code}")
    
    if not code:
        print("❌ 验证码不能为空")
        return False
    
    if not code.isdigit() or len(code) != 6:
        print("❌ 验证码必须是6位数字")
        return False
    
    print(f"使用验证码: {code}")
    
    # 创建客户端（使用现有的会话文件）
    session_file = f"{account.session_name}.session"
    if not os.path.exists(session_file):
        print(f"❌ 会话文件不存在: {session_file}")
        print("请先运行 try_alternative_auth.py 发送验证码请求")
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
        
        # 获取 phone_code_hash（需要从之前的请求中获取）
        # 由于我们无法获取之前的 phone_code_hash，需要重新发送验证码请求
        print("重新发送验证码请求以获取 phone_code_hash...")
        sent_code = await client.send_code_request(account.phone)
        print(f"✅ 验证码请求发送成功")
        print(f"验证码类型: {sent_code.type}")
        
        # 使用用户输入的验证码登录
        print("使用验证码登录...")
        try:
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
    print("手动输入验证码完成认证")
    print("注意：请确保已在 Telegram 应用中收到验证码")
    print()
    
    success = await complete_auth_with_code()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 认证成功！")
        print("\n现在可以运行数据采集：")
        print("  python3 collect_raw_data.py")
    else:
        print("❌ 认证失败")
        print("\n建议：")
        print("1. 检查验证码是否正确")
        print("2. 确保手机号 +86 YOUR_PHONE_NUMBER 正确")
        print("3. 验证码可能已过期（5分钟有效期）")

if __name__ == "__main__":
    asyncio.run(main())