from openai import AsyncOpenAI
from src.models import UnifiedMessage, ScrapedContent
from typing import List, Optional
from loguru import logger

class AISummarizer:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def summarize_message(self, message: UnifiedMessage, scraped_contents: List[ScrapedContent] = []) -> dict:
        """
        结合消息原文和爬取到的网页内容生成归纳
        返回格式: {"summary": str, "tags": List[str]}
        """
        context = f"Message: {message.content}\n\n"
        for i, sc in enumerate(scraped_contents):
            context += f"Link {i+1} ({sc.url}) Content Snippet:\n{sc.markdown[:2000]}\n\n"

        prompt = f"""
        你是一个专门负责整理 Telegram 群组信息的 AI 助手。请根据以下消息内容（以及可能的网页链接内容），提取核心信息并生成一份结构化的简报。

        要求：
        1. 摘要（summary）：简洁明了地说明这条信息在讲什么，核心价值在哪里。200字以内。
        2. 标签（tags）：给出 3-5 个关键词标签。

        输出格式必须为 JSON：
        {{
            "summary": "这里是摘要内容",
            "tags": ["标签1", "标签2", "标签3"]
        }}

        输入内容：
        {context}
        """

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={'type': 'json_object'},
                temperature=0.3
            )
            import json
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"AI Summary failed: {e}")
            return {
                "summary": "AI 归纳失败。",
                "tags": ["error"]
            }
