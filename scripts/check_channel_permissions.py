#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def check_permissions():
    """检查主账号在频道中的权限"""
    from telethon import TelegramClient
    
    # 主账号配置
    api_id = int(os.getenv("TELEGRAM_MAIN_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_MAIN_API_HASH", "")
    channel_username = os.getenv("TELEGRAM_CHANNEL_USERNAME", "@HDXSradar")
    
    print(f"检查频道权限:")
    print(f"  频道: {channel_username}")
    
    client = TelegramClient("main_session.session", api_id, api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ 会话未授权")
            return
        
        print("✅ 主账号已授权")
        
        # 获取频道信息
        channel = await client.get_entity(channel_username)
        print(f"✅ 频道信息:")
        print(f"   频道ID: {channel.id}")
        print(f"   频道名称: {channel.title}")
        print(f"   用户名: {getattr(channel, 'username', 'N/A')}")
        
        # 检查是否加入了频道
        print(f"\n检查是否加入了频道...")
        try:
            # 尝试获取对话
            dialog = await client.get_dialogs()
            found = False
            for d in dialog:
                if hasattr(d.entity, 'id') and d.entity.id == channel.id:
                    print(f"✅ 已找到频道对话")
                    print(f"   对话标题: {d.title}")
                    print(f"   未读消息: {d.unread_count}")
                    found = True
                    break
            
            if not found:
                print("❌ 未在对话列表中找到该频道")
                print("   可能原因:")
                print("   1. 主账号未加入该频道")
                print("   2. 频道是私密的")
                print("   3. 需要手动加入频道")
                
        except Exception as e:
            print(f"❌ 检查对话失败: {e}")
        
        # 检查管理员权限
        print(f"\n检查管理员权限...")
        try:
            # 获取频道参与者列表
            participants = await client.get_participants(channel)
            me = await client.get_me()
            
            found_me = False
            for participant in participants:
                if participant.id == me.id:
                    found_me = True
                    print(f"✅ 在参与者列表中找到自己")
                    print(f"   用户名: {participant.username}")
                    print(f"   姓名: {participant.first_name}")
                    
                    # 检查是否是管理员
                    if hasattr(participant, 'admin_rights') and participant.admin_rights:
                        print(f"✅ 是管理员!")
                        print(f"   管理员权限:")
                        if participant.admin_rights.post_messages:
                            print(f"     - 可以发送消息: ✅")
                        else:
                            print(f"     - 可以发送消息: ❌")
                        if participant.admin_rights.edit_messages:
                            print(f"     - 可以编辑消息: ✅")
                        else:
                            print(f"     - 可以编辑消息: ❌")
                        if participant.admin_rights.delete_messages:
                            print(f"     - 可以删除消息: ✅")
                        else:
                            print(f"     - 可以删除消息: ❌")
                    else:
                        print(f"❌ 不是管理员")
                    break
            
            if not found_me:
                print("❌ 未在参与者列表中找到自己")
                print("   可能没有加入频道或没有查看参与者权限")
                
        except Exception as e:
            print(f"❌ 检查参与者失败: {e}")
            print(f"   可能没有查看参与者列表的权限")
        
        # 尝试其他发送方式
        print(f"\n尝试其他发送方式...")
        print("1. 尝试使用频道ID发送...")
        try:
            # 使用频道ID发送
            test_message = "🤖 测试消息 (使用频道ID)"
            sent = await client.send_message(channel.id, test_message)
            print(f"✅ 使用频道ID发送成功!")
            await client.delete_messages(channel, [sent.id])
            print(f"✅ 测试消息已删除")
        except Exception as e:
            print(f"❌ 使用频道ID发送失败: {e}")
        
        print("\n2. 尝试使用InputPeerChannel...")
        try:
            from telethon.tl.types import InputPeerChannel
            peer = InputPeerChannel(channel_id=channel.id, access_hash=channel.access_hash)
            test_message = "🤖 测试消息 (使用InputPeerChannel)"
            sent = await client.send_message(peer, test_message)
            print(f"✅ 使用InputPeerChannel发送成功!")
            await client.delete_messages(channel, [sent.id])
            print(f"✅ 测试消息已删除")
        except Exception as e:
            print(f"❌ 使用InputPeerChannel发送失败: {e}")
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
    finally:
        await client.disconnect()
        print(f"\n✅ 检查完成")

if __name__ == "__main__":
    asyncio.run(check_permissions())