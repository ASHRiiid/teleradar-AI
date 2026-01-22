"""
单账号采集测试脚本
用于验证采集账号1的配置和基本功能
"""

import asyncio
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from loguru import logger

from src.config import config
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter

load_dotenv()

async def test_single_account():
    """测试单账号采集功能"""
    
    logger.info("=== 单账号采集测试开始 ===")
    
    # 1. 检查配置
    logger.info("检查配置...")
    
    # 检查采集账号配置
    if not config.collector_accounts:
        logger.error("未配置采集账号")
        return False
    
    collector1 = config.collector_accounts[0]
    logger.info(f"使用采集账号: {collector1.account_id}")
    logger.info(f"API ID: {collector1.api_id}")
    logger.info(f"API Hash: {'已配置' if collector1.api_hash else '未配置'}")
    logger.info(f"Phone: {'已配置' if collector1.phone else '未配置'}")
    
    # 检查监控群组
    if not config.collector_config.monitored_chats:
        logger.error("未配置监控群组")
        return False
    
    logger.info(f"监控群组: {config.collector_config.monitored_chats}")
    
    # 2. 初始化适配器
    logger.info("初始化多账号适配器...")
    try:
        tg_adapter = TelegramMultiAccountAdapter()
        logger.info("适配器初始化成功")
    except Exception as e:
        logger.error(f"适配器初始化失败: {e}")
        return False
    
    # 3. 测试连接
    logger.info("测试连接...")
    try:
        await tg_adapter.connect_all()
        logger.info("所有客户端连接成功")
    except Exception as e:
        logger.error(f"连接失败: {e}")
        return False
    
    # 4. 测试采集（只采集最近1小时的消息，避免过多数据）
    logger.info("测试采集功能...")
    
    # 设置测试时间窗口（最近1小时）
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now_beijing = datetime.now(beijing_tz)
    end_time = now_beijing
    start_time = end_time - timedelta(hours=1)
    
    # 转换为 UTC
    start_time_utc = start_time.astimezone(pytz.utc).replace(tzinfo=None)
    end_time_utc = end_time.astimezone(pytz.utc).replace(tzinfo=None)
    
    logger.info(f"测试时间窗口: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 到 {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        messages = await tg_adapter.fetch_messages_concurrently(
            config.collector_config.monitored_chats,
            start_time_utc,
            end_time_utc,
            limit_per_chat=10  # 限制为10条，仅用于测试
        )
        
        logger.info(f"采集到 {len(messages)} 条消息")
        
        # 显示消息示例
        if messages:
            logger.info("消息示例:")
            for i, msg in enumerate(messages[:3]):  # 显示前3条
                logger.info(f"  {i+1}. [{msg.timestamp.strftime('%H:%M:%S')}] {msg.content[:100]}...")
                logger.info(f"     来源: {msg.metadata.get('collector_account')}, 群组: {msg.metadata.get('chat')}")
        
        # 5. 测试频道推送（可选）
        if config.push_config.channel_username or config.push_config.channel_id:
            logger.info("测试频道推送...")
            test_message = f"📊 测试消息\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n采集账号: {collector1.account_id}\n状态: 测试成功"
            
            success = await tg_adapter.send_digest_to_channel(test_message)
            if success:
                logger.info("测试消息已发送到频道")
            else:
                logger.warning("测试消息发送失败（可能是权限问题）")
    
    except Exception as e:
        logger.error(f"采集测试失败: {e}")
        return False
    
    finally:
        # 6. 断开连接
        logger.info("断开连接...")
        await tg_adapter.disconnect_all()
    
    logger.info("=== 单账号采集测试完成 ===")
    return True

async def check_configuration():
    """检查环境配置"""
    logger.info("=== 环境配置检查 ===")
    
    # 检查必要的环境变量
    required_vars = [
        ("TELEGRAM_COLLECTOR1_API_ID", "采集账号1 API ID"),
        ("TELEGRAM_COLLECTOR1_API_HASH", "采集账号1 API Hash"),
        ("TELEGRAM_COLLECTOR1_PHONE", "采集账号1 手机号"),
        ("MONITORED_CHATS", "监控群组"),
    ]
    
    missing_vars = []
    for var_name, description in required_vars:
        value = os.getenv(var_name)
        if not value:
            missing_vars.append(f"{description} ({var_name})")
        else:
            logger.info(f"✓ {description}: {'已配置' if var_name.endswith('_PHONE') else value[:10] + '...' if len(value) > 10 else value}")
    
    if missing_vars:
        logger.error(f"缺少必要配置: {', '.join(missing_vars)}")
        return False
    
    # 检查可选配置
    optional_vars = [
        ("TELEGRAM_MAIN_API_ID", "主账号 API ID"),
        ("TELEGRAM_MAIN_API_HASH", "主账号 API Hash"),
        ("TELEGRAM_MAIN_PHONE", "主账号 手机号"),
        ("TELEGRAM_CHANNEL_USERNAME", "频道用户名"),
        ("TELEGRAM_BOT_TOKEN", "Bot Token"),
        ("DEEPSEEK_API_KEY", "DeepSeek API Key"),
    ]
    
    for var_name, description in optional_vars:
        value = os.getenv(var_name)
        if value:
            logger.info(f"✓ {description}: {'已配置' if var_name.endswith('_PHONE') or var_name.endswith('_KEY') else value[:10] + '...' if len(value) > 10 else value}")
        else:
            logger.warning(f"⚠ {description}: 未配置（可选）")
    
    logger.info("=== 配置检查完成 ===")
    return True

if __name__ == "__main__":
    # 先检查配置
    config_ok = asyncio.run(check_configuration())
    
    if config_ok:
        # 运行测试
        test_result = asyncio.run(test_single_account())
        if test_result:
            logger.success("✅ 测试成功！系统可以正常工作。")
        else:
            logger.error("❌ 测试失败，请检查配置和日志。")
    else:
        logger.error("❌ 配置检查失败，请先完善 .env 配置。")