#!/usr/bin/env python3
import asyncio
import json
from loguru import logger
from src.config import config
from src.storage import Storage
from src.processors.summarizer import AISummarizer
from src.models import UnifiedMessage, Platform
from datetime import datetime

async def analyze_messages():
    storage = Storage()
    summarizer = AISummarizer(api_key=config.ai_config.deepseek_api_key, base_url=config.ai_config.openai_base_url)

    unprocessed = storage.get_unprocessed()
    if not unprocessed:
        logger.info("No unprocessed messages found.")
        return

    # Limit to 3 messages for testing
    unprocessed = unprocessed[:3]
    logger.info(f"Found {len(unprocessed)} unprocessed messages for testing. Starting AI analysis...")

    for row in unprocessed:
        try:
            # Convert row to UnifiedMessage
            msg = UnifiedMessage(
                id=row['internal_id'],
                platform=Platform(row['platform']),
                external_id=row['external_id'],
                content=row['content'],
                author_id="unknown", # Row doesn't have author_id
                author_name=row['author_name'],
                timestamp=datetime.fromisoformat(row['timestamp']) if isinstance(row['timestamp'], str) else row['timestamp'],
                chat_id=row['chat_id'],
                chat_name=row['chat_name'],
                urls=json.loads(row['urls']) if row['urls'].startswith('[') else row['urls'].split(',') if row['urls'] else []
            )

            logger.info(f"Analyzing message {msg.id} from {msg.chat_name}...")
            
            # For now, we don't have scraped content, so we pass an empty list
            result = await summarizer.summarize_message(msg, [])
            
            summary = result.get("summary", "AI 归纳失败。")
            tags = result.get("tags", [])
            
            storage.update_message_summary(msg.id, summary, tags)
            logger.info(f"Successfully analyzed message {msg.id}")

        except Exception as e:
            logger.error(f"Failed to analyze message {row['internal_id']}: {e}")

if __name__ == "__main__":
    asyncio.run(analyze_messages())
