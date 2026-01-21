import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

from src.adapters.telegram_adapter import TelegramAdapter
from src.processors.scraper import JinaScraper
from src.processors.summarizer import AISummarizer
from src.delivery.obsidian import ObsidianDelivery

load_dotenv()

async def process_message(msg, scraper, summarizer, delivery):
    logger.info(f"Processing message {msg.external_id} from {msg.chat_name}")
    
    scraped_contents = []
    # 抓取链接内容
    for url in msg.urls[:3]: # 限制每条消息抓取前 3 个链接
        sc = await scraper.scrape(url)
        scraped_contents.append(sc)
    
    # AI 归纳
    summary = await summarizer.summarize_message(msg, scraped_contents)
    
    # 交付到 Obsidian
    await delivery.deliver(msg, summary)

async def main():
    # 1. 初始化
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    openai_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    chats = os.getenv("MONITORED_CHATS").split(",")
    
    tg_adapter = TelegramAdapter(api_id, api_hash)
    scraper = JinaScraper()
    summarizer = AISummarizer(openai_key, base_url=base_url)
    delivery = ObsidianDelivery(vault_path)

    # 2. 确定抓取范围（过去 24 小时）
    since = datetime.now() - timedelta(days=1)
    logger.info(f"Fetching messages since {since}")

    # 3. 执行抓取
    messages = await tg_adapter.fetch_messages_since(chats, since)
    logger.info(f"Found {len(messages)} messages to process")

    # 4. 顺序处理（避免并发过高导致 API 限流）
    for msg in messages:
        await process_message(msg, scraper, summarizer, delivery)

    logger.info("All tasks completed.")

if __name__ == "__main__":
    asyncio.run(main())
