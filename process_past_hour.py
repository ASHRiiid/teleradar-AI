#!/usr/bin/env python3
"""
Hourly Process Script:
1. Collect messages from the last 1 hour for all monitored chats.
2. Generate a structured Global Summary using DeepSeek API.
3. Save to Obsidian and push to Telegram channel.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Ensure we can import from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from src.config import load_config
from src.processors.summarizer import AISummarizer
from collect_compatible import collect_from_group
from telethon import TelegramClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def generate_global_summary(summarizer: AISummarizer, aggregated_content: str) -> Dict[str, Any]:
    """
    使用 DeepSeek API 生成结构化的全局摘要
    """
    prompt = f"""
    你是一个专业的金融和市场数据分析师。请对过去一小时内 Telegram 多个群组讨论的内容进行深度总结。

    输入内容（按群组排列的消息列表）：
    {aggregated_content}

    你的总结必须包含以下四个明确的部分：
    1. **主要聊了哪些内容** (Main discussion topics)
    2. **情绪如何** (Sentiment analysis)
    3. **对行情怎么看** (Market outlook)
    4. **提及到的代币/股票/项目** (Mentioned assets)

    要求：
    - 语言简洁、专业。
    - 突出过去一小时的热点和突发动态。
    - 如果没有提到某些部分，请注明“未提及”。
    - 输出格式为 Markdown，包含以上四个标题。

    请直接输出 Markdown 内容。
    """

    try:
        response = await summarizer.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional market analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return {"content": response.choices[0].message.content}
    except Exception as e:
        logger.error(f"Global Summary generation failed: {e}")
        return {"content": "生成全局摘要失败。"}

def save_to_obsidian(report_content: str) -> str:
    """保存摘要到 Obsidian 文件夹"""
    obsidian_dir = "obsidian-tem"
    os.makedirs(obsidian_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"PastHourReport_{timestamp}.md"
    filepath = os.path.join(obsidian_dir, filename)
    
    full_md = f"""# 📊 全局信息简报 (过去 1 小时)

> 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 报告周期: { (datetime.now() - timedelta(hours=1)).strftime("%H:%M") } - { datetime.now().strftime("%H:%M") }

{report_content}

---
*由 Telegram 信息自动化系统自动生成*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_md)
    
    logger.info(f"Obsidian 报告已保存: {filepath}")
    return filepath

async def push_to_telegram(report_content: str, config):
    """推送到 Telegram 频道"""
    try:
        main_account = config.main_account
        client = TelegramClient(
            main_account.session_name,
            main_account.api_id,
            main_account.api_hash
        )
        
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error("推送账号未认证")
            return
        
        channel_username = config.push_config.channel_username
        if not channel_username:
            logger.error("未配置推送频道")
            return
            
        entity = await client.get_entity(channel_username)
        
        header = f"📊 **全局信息简报 (过去 1 小时)**\n\n"
        full_message = header + report_content
        
        # Telegram 消息长度限制为 4096 字符
        if len(full_message) > 4000:
            full_message = full_message[:4000] + "..."
            
        await client.send_message(entity, full_message)
        logger.info("简报已推送到 Telegram")
        
        await client.disconnect()
    except Exception as e:
        logger.error(f"推送 Telegram 失败: {e}")

async def main():
    logger.info("开始执行过去一小时信息处理脚本")
    
    # 1. 重新加载配置
    load_dotenv(override=True)
    config = load_config()
    logger.info(f"重新加载配置完成，待监控群组: {len(config.collector_config.monitored_chats)} 个")
    
    # 初始化 AI 总结器
    summarizer = AISummarizer(
        api_key=config.ai_config.deepseek_api_key, 
        base_url=config.ai_config.openai_base_url
    )
    
    # 2. 采集消息
    if not config.collector_accounts:
        logger.error("没有配置采集账号")
        return
        
    collector_account = config.collector_accounts[0]
    client = TelegramClient(
        collector_account.session_name,
        collector_account.api_id,
        collector_account.api_hash
    )
    
    all_chat_contents = []
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error("采集账号未认证")
            return
            
        # 并发限制，避免被封
        semaphore = asyncio.Semaphore(3)
        
        async def fetch_chat(chat_url):
            async with semaphore:
                messages = await collect_from_group(client, chat_url, hours_back=1)
                if messages:
                    # 按照群组聚合内容
                    chat_name = messages[0]['chat_name']
                    combined_text = "\n".join([f"- {m['content']}" for m in messages])
                    return f"### Group: {chat_name}\n{combined_text}\n"
                return ""

        tasks = [fetch_chat(url) for url in config.collector_config.monitored_chats]
        results = await asyncio.gather(*tasks)
        
        aggregated_input = "\n".join([r for r in results if r])
        
        if not aggregated_input:
            logger.info("过去一小时没有新消息，跳过处理")
            return
            
        # 3. 生成全局摘要
        logger.info("正在生成全局摘要...")
        summary_result = await generate_global_summary(summarizer, aggregated_input)
        report_content = summary_result['content']
        
        # 4. 保存到 Obsidian
        save_to_obsidian(report_content)
        
        # 5. 推送到 Telegram
        await push_to_telegram(report_content, config)
        
    except Exception as e:
        logger.error(f"运行脚本出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
