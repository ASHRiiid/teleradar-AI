from openai import AsyncOpenAI
from src.models import UnifiedMessage, ScrapedContent
from typing import List, Optional
from loguru import logger

class AISummarizer:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def summarize_message(self, message: UnifiedMessage, scraped_contents: List[ScrapedContent]) -> str:
        """
        结合消息原文和爬取到的网页内容生成归纳
        """
        context = f"Message: {message.content}\n\n"
        for i, sc in enumerate(scraped_contents):
            context += f"Link {i+1} ({sc.url}) Content Snippet:\n{sc.markdown[:2000]}\n\n"

        prompt = f"""
        你是一个信息整理助手。请根据以下来自 Telegram 群组的消息和相关的链接内容，提取核心信息并生成一份简报。
        
        要求：
        1. 摘要：简洁明了地说明这条信息在讲什么。
        2. 价值点：如果涉及技术、产品或新闻，提炼出核心要点。
        3. 标签：给出 3-5 个关键词标签。
        4. 语言：中文。

        输入内容：
        {context}
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI Summary failed: {e}")
            return "AI 归纳失败。"
