import asyncio
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from loguru import logger

from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter
from src.storage import Storage
from src.config import config

load_dotenv()

async def collect_only():
    # 1. 初始化多账号适配器
    tg_adapter = TelegramMultiAccountAdapter()
    storage = Storage()
    
    # 获取监控的群组
    chats = config.collector_config.monitored_chats
    if not chats:
        logger.error("未配置监控群组")
        return

    # 2. 计算北京时间 (UTC+8) 的抓取窗口
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now_beijing = datetime.now(beijing_tz)
    
    # 今天的 08:00 (北京时间)
    today_08am = now_beijing.replace(hour=8, minute=0, second=0, microsecond=0)
    
    # 如果当前还没到 08:00，则结束时间设为昨天的 08:00，起始时间为前天的 08:00
    # 但通常自动化任务在 08:00 之后跑，所以我们取：
    # 结束点：今天的 08:00
    # 起始点：昨天的 08:00
    if now_beijing < today_08am:
        end_time = today_08am - timedelta(days=0) # 逻辑保持，即当前采集周期还没结束
    else:
        end_time = today_08am

    start_time = end_time - timedelta(days=1)
    
    logger.info(f"Beijing Time Window: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Telethon 使用 UTC 时间，所以我们需要转换回 UTC 传给 API
    start_time_utc = start_time.astimezone(pytz.utc).replace(tzinfo=None)
    end_time_utc = end_time.astimezone(pytz.utc).replace(tzinfo=None)

    # 3. 执行并发抓取并存入数据库
    messages = await tg_adapter.fetch_messages_concurrently(chats, start_time_utc, end_time_utc)
    
    count = 0
    for msg in messages:
        storage.save_message(msg)
        count += 1
    
    logger.info(f"采集完成: 保存了 {count} 条去重后的消息到 data/raw_messages.db")
    
    # 4. 显示采集统计
    if messages:
        accounts_used = set()
        chats_covered = set()
        for msg in messages:
            accounts_used.add(msg.metadata.get('collector_account', 'unknown'))
            chats_covered.add(msg.metadata.get('chat', 'unknown'))
        
        logger.info(f"使用的采集账号: {', '.join(accounts_used)}")
        logger.info(f"覆盖的群组: {', '.join(chats_covered)}")
        logger.info(f"最早消息时间: {min(m.timestamp for m in messages).strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"最晚消息时间: {max(m.timestamp for m in messages).strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(collect_only())
