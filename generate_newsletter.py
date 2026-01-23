#!/usr/bin/env python3
import asyncio
import json
import os
import sqlite3
from datetime import datetime, timedelta
from loguru import logger
from src.config import config
from src.processors.summarizer import AISummarizer
from openai import AsyncOpenAI

async def generate_daily_newsletter():
    """生成每日简报"""
    logger.info("Starting Daily Newsletter generation...")
    
    # 1. 获取最近 24 小时已分析的消息
    time_threshold = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    conn = sqlite3.connect(config.database_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT chat_name, summary, tags, timestamp 
        FROM messages 
        WHERE processed = 1 AND timestamp >= ?
    ''', (time_threshold,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        logger.warning("No analyzed messages found for today.")
        return

    messages = [dict(row) for row in rows]
    logger.info(f"Found {len(messages)} analyzed messages for today.")

    # 2. 准备 AI 输入
    # 按照群组分组
    groups = {}
    for m in messages:
        group_name = m['chat_name']
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(m)

    context = ""
    for group_name, msgs in groups.items():
        context += f"### 群组: {group_name}\n"
        for i, m in enumerate(msgs, 1):
            context += f"{i}. {m['summary']}\n"
        context += "\n"

    # 3. 使用 AI 生成聚合简报
    client = AsyncOpenAI(api_key=config.ai_config.deepseek_api_key, base_url=config.ai_config.openai_base_url)
    
    prompt = f"""
    你是一个专业的新闻编辑。请根据以下来自不同 Telegram 群组的消息摘要，整理出一份“今日技术与资讯每日简报”。
    
    要求：
    1. 分类整理：根据内容将信息分为几个大类（如：技术、产品、市场、其他）。
    2. 深度归纳：不要只是罗列摘要，要试图发现不同消息之间的关联，总结出今日的核心趋势。
    3. 语言：中文，风格专业且易读。
    4. 包含一个“今日金句”或“今日总结”，但严禁在末尾提供重复所有内容的冗余总结部分。
    5. **严禁长分隔符**: 严禁使用过长的装饰性分隔符（如 '━━━━━━━━'），因为它们在移动端 Telegram 上会导致显示错乱。如有必要，仅使用极短的分隔线。
    6. 请直接输出内容，不要有任何废话开头。

    今日消息摘要：
    {context}
    """

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional editor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        newsletter_content = response.choices[0].message.content
    except Exception as e:
        logger.error(f"Failed to generate newsletter with AI: {e}")
        return

    # 4. 保存为 Markdown 文件
    newsletter_dir = "obsidian-tem/Newsletters"
    os.makedirs(newsletter_dir, exist_ok=True)
    
    current_time = datetime.now().strftime('%Y-%m-%d')
    filename = f"Newsletter_{datetime.now().strftime('%Y%m%d')}.md"
    filepath = os.path.join(newsletter_dir, filename)
    
    full_content = f"""# 📰 今日技术与资讯每日简报

> 日期: {current_time}
> 来源消息总数: {len(messages)}

---

{newsletter_content}

---
*此简报由 AI 自动生成*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    logger.info(f"Newsletter generated successfully: {filepath}")
    return filepath

if __name__ == "__main__":
    asyncio.run(generate_daily_newsletter())
