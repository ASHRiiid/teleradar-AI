"""
Telegram 认证测试脚本
处理首次连接的验证码输入
"""

import asyncio
import sys
from dotenv import load_dotenv
from loguru import logger

from src.config import config
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter

load_dotenv()

async def test_telegram_auth():
    """测试 Telegram 认证"""
    logger.info("=== Telegram 认证测试开始 ===")
    
    # 检查配置
    if not config.collector_accounts:
        logger.error("未配置采集账号")
        return False
    
    collector1 = config.collector_accounts[0]
    logger.info(f"测试账号: {collector1.account_id}")
    logger.info(f"Phone: {collector1.phone}")
    
    # 初始化适配器
    try:
        tg_adapter = TelegramMultiAccountAdapter()
        logger.info("适配器初始化成功")
    except Exception as e:
        logger.error(f"适配器初始化失败: {e}")
        return False
    
    # 尝试连接（会触发验证码输入）
    logger.info("尝试连接 Telegram...")
    logger.info("注意：首次连接可能需要输入验证码")
    logger.info("验证码会发送到您的 Telegram 应用")
    
    try:
        # 连接所有客户端
        await tg_adapter.connect_all()
        logger.success("✅ Telegram 连接成功！")
        
        # 测试简单的消息获取
        logger.info("测试消息获取...")
        
        # 只获取最近5分钟的消息用于测试
        from datetime import datetime, timedelta
        import pytz
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now_beijing = datetime.now(beijing_tz)
        end_time = now_beijing
        start_time = end_time - timedelta(minutes=5)
        
        start_time_utc = start_time.astimezone(pytz.utc).replace(tzinfo=None)
        end_time_utc = end_time.astimezone(pytz.utc).replace(tzinfo=None)
        
        messages = await tg_adapter.fetch_messages_concurrently(
            config.collector_config.monitored_chats,
            start_time_utc,
            end_time_utc,
            limit_per_chat=5
        )
        
        logger.info(f"测试采集到 {len(messages)} 条消息")
        
        if messages:
            logger.info("消息示例:")
            for i, msg in enumerate(messages[:2]):
                logger.info(f"  {i+1}. [{msg.timestamp.strftime('%H:%M:%S')}] {msg.content[:80]}...")
        
        # 测试频道推送
        if config.push_config.channel_username or config.push_config.channel_id:
            logger.info("测试频道推送...")
            test_message = f"🔧 系统测试消息\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n状态: Telegram 认证测试成功"
            
            success = await tg_adapter.send_digest_to_channel(test_message)
            if success:
                logger.success("✅ 测试消息已发送到频道")
            else:
                logger.warning("⚠️ 测试消息发送失败（可能是权限问题）")
        
        # 断开连接
        await tg_adapter.disconnect_all()
        logger.info("连接已断开")
        
        return True
        
    except Exception as e:
        logger.error(f"认证测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 设置日志
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # 运行测试
    try:
        result = asyncio.run(test_telegram_auth())
        if result:
            logger.success("✅ 认证测试完成！系统可以正常工作。")
            print("\n下一步:")
            print("1. 运行 'python3 collect_raw_data.py' 进行完整数据采集")
            print("2. 系统会自动保存24小时的消息到数据库")
        else:
            logger.error("❌ 认证测试失败")
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")