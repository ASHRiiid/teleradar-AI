"""
完成 Telegram 认证脚本
使用提供的验证码完成首次连接
"""

import asyncio
import sys
from dotenv import load_dotenv
from loguru import logger

from src.config import config
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter

load_dotenv()

# 使用用户提供的验证码
VERIFICATION_CODE = "926390"

async def complete_telegram_auth():
    """使用验证码完成 Telegram 认证"""
    logger.info("=== 使用验证码完成 Telegram 认证 ===")
    
    # 检查配置
    if not config.collector_accounts:
        logger.error("未配置采集账号")
        return False
    
    collector1 = config.collector_accounts[0]
    logger.info(f"认证账号: {collector1.account_id}")
    logger.info(f"Phone: {collector1.phone}")
    logger.info(f"使用验证码: {VERIFICATION_CODE}")
    
    # 初始化适配器
    try:
        tg_adapter = TelegramMultiAccountAdapter()
        logger.info("适配器初始化成功")
    except Exception as e:
        logger.error(f"适配器初始化失败: {e}")
        return False
    
    # 修改连接方法以使用提供的验证码
    for session in tg_adapter.collector_sessions.values():
        # 覆盖连接方法
        original_connect = session.connect
        
        async def patched_connect():
            try:
                session.client = TelegramClient(
                    session.account_config.session_name,
                    session.account_config.api_id,
                    session.account_config.api_hash
                )
                
                # 使用提供的验证码
                async def code_callback():
                    logger.info(f"使用验证码: {VERIFICATION_CODE}")
                    return VERIFICATION_CODE
                
                # 启动客户端
                await session.client.start(
                    phone=session.account_config.phone,
                    code_callback=code_callback
                )
                
                session.is_connected = True
                logger.info(f"Telegram 客户端 {session.account_config.account_id} 连接成功")
            except Exception as e:
                logger.error(f"Telegram 连接失败 ({session.account_config.account_id}): {e}")
                raise
        
        session.connect = patched_connect
    
    # 尝试连接
    logger.info("尝试使用验证码连接...")
    try:
        await tg_adapter.connect_all()
        logger.success("✅ Telegram 连接成功！")
        
        # 测试简单的消息获取
        logger.info("测试消息获取...")
        
        from datetime import datetime, timedelta
        import pytz
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now_beijing = datetime.now(beijing_tz)
        end_time = now_beijing
        start_time = end_time - timedelta(minutes=10)  # 获取最近10分钟的消息
        
        start_time_utc = start_time.astimezone(pytz.utc).replace(tzinfo=None)
        end_time_utc = end_time.astimezone(pytz.utc).replace(tzinfo=None)
        
        messages = await tg_adapter.fetch_messages_concurrently(
            config.collector_config.monitored_chats,
            start_time_utc,
            end_time_utc,
            limit_per_chat=10
        )
        
        logger.info(f"测试采集到 {len(messages)} 条消息")
        
        if messages:
            logger.info("消息示例:")
            for i, msg in enumerate(messages[:3]):
                content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                logger.info(f"  {i+1}. [{msg.timestamp.strftime('%H:%M:%S')}] {content_preview}")
                logger.info(f"     来源: {msg.metadata.get('collector_account')}, 群组: {msg.metadata.get('chat')}")
        
        # 测试频道推送
        if config.push_config.channel_username or config.push_config.channel_id:
            logger.info("测试频道推送...")
            test_message = f"🔧 系统测试消息\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n状态: Telegram 认证测试成功\n验证码: {VERIFICATION_CODE}"
            
            success = await tg_adapter.send_digest_to_channel(test_message)
            if success:
                logger.success("✅ 测试消息已发送到频道")
            else:
                logger.warning("⚠️ 测试消息发送失败（可能是权限问题）")
        
        # 断开连接
        await tg_adapter.disconnect_all()
        logger.info("连接已断开")
        
        # 保存会话文件，下次无需验证码
        logger.info("会话文件已保存，下次连接无需验证码")
        
        return True
        
    except Exception as e:
        logger.error(f"认证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 设置日志
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # 运行认证
    try:
        result = asyncio.run(complete_telegram_auth())
        if result:
            logger.success("✅ 认证成功！系统可以正常工作。")
            print("\n🎉 认证完成！下一步:")
            print("1. 运行 'python3 collect_raw_data.py' 进行完整数据采集")
            print("2. 系统会自动保存24小时的消息到数据库")
            print("3. 会话文件已保存，下次无需验证码")
        else:
            logger.error("❌ 认证失败")
            print("\n⚠️ 认证失败可能原因:")
            print("1. 验证码已过期（5分钟内有效）")
            print("2. 验证码错误")
            print("3. 需要两步验证密码")
            print("\n请检查 Telegram 应用中的验证码，然后重试")
    except KeyboardInterrupt:
        logger.info("认证被用户中断")
    except Exception as e:
        logger.error(f"认证过程中发生错误: {e}")