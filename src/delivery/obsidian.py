import os
import aiofiles
from datetime import datetime
from src.models import UnifiedMessage
from loguru import logger

class ObsidianDelivery:
    def __init__(self, vault_path: str, folder_name: str = "Aggregator"):
        self.base_path = os.path.join(vault_path, folder_name)
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    async def deliver(self, message: UnifiedMessage, summary: str):
        date_str = message.timestamp.strftime("%Y-%m-%d")
        file_path = os.path.join(self.base_path, f"{date_str}.md")
        
        # 构造 Markdown 格式
        content = f"""
## [{message.platform.upper()}] From {message.chat_name or 'Private'}
- **Author**: {message.author_name}
- **Time**: {message.timestamp.strftime("%H:%M:%S")}
- **Original**: {message.content[:200].replace('\n', ' ')}...
- **AI Summary**:
{summary}

---
"""
        async with aiofiles.open(file_path, mode='a', encoding='utf-8') as f:
            await f.write(content)
        
        logger.info(f"Delivered to Obsidian: {file_path}")
