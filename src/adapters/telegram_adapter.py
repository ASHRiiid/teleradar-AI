import re
import asyncio
import random
from typing import List
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from src.models import UnifiedMessage, Platform
from datetime import datetime
import uuid
from loguru import logger

class TelegramAdapter:
    def __init__(self, api_id: int, api_hash: str, session_name: str = "data/aggregator"):
        import os
        os.makedirs("data", exist_ok=True)
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.url_pattern = re.compile(r'https?://\S+')

    def extract_urls(self, text: str) -> List[str]:
        return self.url_pattern.findall(text)

    async def resolve_chat(self, chat_identifier: str):
        """
        解析群组标识符（ID, Username, 或 Link）为实体对象
        """
        try:
            # 处理 t.me/joinchat/ 这种私有链接
            if "joinchat/" in chat_identifier:
                invite_hash = chat_identifier.split("joinchat/")[-1]
                from telethon.tl.functions.messages import CheckChatInviteRequest
                invite = await self.client(CheckChatInviteRequest(invite_hash))
                return invite.chat
            
            # 处理普通链接或用户名
            entity = await self.client.get_entity(chat_identifier)
            return entity
        except Exception as e:
            logger.error(f"Failed to resolve chat {chat_identifier}: {e}")
            return None

    async def fetch_messages_between(self, chats: List[str], start_datetime: datetime, end_datetime: datetime) -> List[UnifiedMessage]:
        """
        抓取指定时间范围内的消息 (UTC)
        """
        unified_messages = []
        if not self.client.is_connected():
            await self.client.start()
        
        for chat_identifier in chats:
            chat_entity = await self.resolve_chat(chat_identifier)
            if not chat_entity:
                continue

            logger.info(f"Fetching from: {getattr(chat_entity, 'title', chat_identifier)}")
            try:
                # offset_date 是抓取的起点（由于 reverse=True，它是最早的时间）
                # 但是 Telethon 的 iter_messages 在 reverse=True 时逻辑比较绕
                # 最稳妥的方法：抓取 offset_date 之后的，自己在循环里判断 end_date
                async for msg in self.client.iter_messages(
                    chat_entity, 
                    offset_date=start_datetime, 
                    reverse=True
                ):
                    # 如果消息时间已经超过了结束时间，跳出该频道的循环
                    msg_date = msg.date.replace(tzinfo=None)
                    if msg_date > end_datetime:
                        break
                    
                    if not msg.text or len(msg.text) < 10:
                        continue

                    urls = self.extract_urls(msg.text)
                    unified_msg = UnifiedMessage(
                        id=str(uuid.uuid4()),
                        platform=Platform.TELEGRAM,
                        external_id=str(msg.id),
                        content=msg.text,
                        author_id=str(msg.sender_id),
                        author_name=(await msg.get_sender()).username if await msg.get_sender() else "Unknown",
                        timestamp=msg_date,
                        chat_id=str(msg.chat_id),
                        chat_name=(await msg.get_chat()).title if hasattr(await msg.get_chat(), 'title') else "Private",
                        urls=urls,
                        raw_metadata={}
                    )
                    unified_messages.append(unified_msg)
                
                await asyncio.sleep(random.uniform(2, 5))

            except FloodWaitError as e:
                logger.warning(f"Flood wait for {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error(f"Error fetching from {chat_identifier}: {e}")
        
        return unified_messages

