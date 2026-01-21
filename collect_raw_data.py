import asyncio
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from loguru import logger

from src.adapters.telegram_adapter import TelegramAdapter
from src.storage import Storage

load_dotenv()

async def collect_only():
    # 1. 初始化
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    chats = os.getenv("MONITORED_CHATS").split(",")
    
    tg_adapter = TelegramAdapter(api_id, api_hash)
    storage = Storage()

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

    # 3. 执行抓取并存入数据库
    # 修改 adapter 以支持 end_date
    messages = await tg_adapter.fetch_messages_between(chats, start_time_utc, end_time_utc)
    
    count = 0
    for msg in messages:
        storage.save_message(msg)
        count += 1
    
    logger.info(f"Collected and saved {count} new messages to data/raw_messages.db")

if __name__ == "__main__":
    asyncio.run(collect_only())
