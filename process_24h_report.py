import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta

# Ensure we can import from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.config import config
from src.processors.summarizer import AISummarizer
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter
from src.models import UnifiedMessage, Platform

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def generate_global_summary(summarizer, aggregated_text):
    """调用 AI 生成全局摘要，遵循 setting_AI.md 中的逻辑"""
    prompt = f"""
    你是一个专业的区块链投研助手。请根据以下从多个 Telegram 群组采集到的碎片化信息，整理出一份深度简报。

    请严格遵循以下整理逻辑：

    ## 消息分类 (Categorization)
    - **市场动态 (Market News)**: 重大政策、交易所公告、大额异动。
    - **项目研报 (Project Alpha)**: 新项目上线、融资信息、深度技术解析。
    - **链上异动 (On-chain Tracking)**: 巨鲸动向、Smart Money 追踪。
    - **社区情绪 (Sentiment)**: 热门讨论话题、FOMO/FUD 情绪捕捉。
    - **Meme/土狗 (Meme/Speculation)**: 整理出聊的最多的三个币的名字

    ## 去重与聚合 (Deduplication & Aggregation)
    - **跨群去重**: 多个频道转发同一条新闻时，只保留一条。
    - **内容聚合**: 将同一个话题（如：某个特定项目的融资）下的多条评论聚合为一个综述。

    ## 质量过滤 (Filtering)
    - **过滤噪音**: 剔除纯水聊、表情包回复、无意义的广告、重复的复读机内容。
    - **优先级**: 优先保留带有链接、数据、深度分析或原创观点的消息。

    ## 简报撰写准则
    - **精炼**: 使用 Markdown 列表，禁止冗长描述。
    - **突出重点**: 关键项目名、代币符号、具体数字使用 **加粗**。
    - **不用保留来源**: 简报中不用保留消息的来源群组名。
    - **时区一致**: 所有时间点必须明确为北京时间 (UTC+8)。
    - **突出人数**: 每一条信息后面用【x人，x视角】这个格式来说明有多少人讨论过这条，以及有多少不同的视角

    ## 常见问题处理
    - **链接处理**: 识别消息中的链接，并在摘要中说明该链接的内容（如：研报链接、推特链接）。
    - **多语言处理**: 无论原始消息是何种语言，简报输出统一使用 **简体中文**。

    ## 特别注意
    - 不要提及"社区氛围与诈骗警告"、"操作与工具咨询"、"诈骗警惕性高"这类信息
    - 不要使用"好的，作为专业的区块链投研助手，我已根据您提供的多源碎片化信息，整理并提炼出以下深度简报。"这样的开头
    - Telegram推送的消息不要使用md语法，简单的用序号、点、空格、空行来清晰表达

    采集到的原始信息如下：
    {aggregated_text}
    """
    
    # 这里直接复用 summarizer 的底层调用
    try:
        response = await summarizer.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的区块链投研助手，严格按照给定的整理逻辑生成简报。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return {"content": response.choices[0].message.content}
    except Exception as e:
        logger.error(f"AI 生成摘要失败: {e}")
        return {"content": f"AI 摘要生成失败: {e}"}

def save_to_obsidian(content, filename):
    vault_path = config.obsidian_vault_path
    if not vault_path:
        logger.warning("未配置 OBSIDIAN_VAULT_PATH，跳过保存")
        return
    if not os.path.exists(vault_path):
        os.makedirs(vault_path)
    
    file_path = os.path.join(vault_path, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"报告已保存到 Obsidian: {file_path}")

async def main():
    logger.info("开始生成 24 小时深度简报 (昨日 08:00 - 今日 08:00)...")
    
    # 调试：检查配置是否正确加载
    for acc in config.collector_accounts:
        logger.info(f"账号 {acc.account_id} 监控群组数量: {len(acc.monitored_chats) if acc.monitored_chats else 0}")
    
    # 设定北京时间范围
    now = datetime.now()
    # 假设今天是 23 号
    # 结束时间：2026-01-23 08:00:00
    # 开始时间：2026-01-22 08:00:00
    end_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=1)
    
    logger.info(f"时间窗口 (北京时间): {start_time} 至 {end_time}")
    
    # 初始化 AI 总结器
    summarizer = AISummarizer(
        api_key=config.ai_config.deepseek_api_key, 
        base_url=config.ai_config.openai_base_url
    )
    
    async with TelegramMultiAccountAdapter() as adapter:
        logger.info("正在并发采集消息...")
        
        # limit_per_chat 设大一点，因为是 24 小时
        unified_messages = await adapter.fetch_messages_concurrently(
            start_time=start_time,
            end_time=end_time,
            limit_per_chat=300
        )
        
        if not unified_messages:
            logger.info("该时间段内没有抓取到新消息")
            return
            
        logger.info(f"成功抓取 {len(unified_messages)} 条去重后的消息，正在聚合内容...")
        
        # 按群组聚合
        chat_contents = {}
        for msg in unified_messages:
            chat_name = msg.chat_name
            if chat_name not in chat_contents:
                chat_contents[chat_name] = []
            chat_contents[chat_name].append(f"- {msg.content}")
            
        aggregated_input = ""
        for chat_name, contents in chat_contents.items():
            # 每个群组只取前 50 条，防止输入过大
            aggregated_input += f"### Group: {chat_name}\n" + "\n".join(contents[:50]) + "\n\n"
        
        logger.info("正在调用 AI 生成深度简报...")
        summary_result = await generate_global_summary(summarizer, aggregated_input)
        report_content = summary_result['content']
        
        # 保存到 Obsidian
        filename = f"DailyReport_{start_time.strftime('%Y%m%d')}_to_{end_time.strftime('%Y%m%d')}.md"
        save_to_obsidian(f"# 📊 24小时信息深度简报\n\n**周期**: {start_time} - {end_time}\n\n{report_content}", filename)
        
        # 推送到 Telegram
        header = f"📊 **24小时信息深度简报**\n📅 {start_time.strftime('%m-%d 08:00')} ~ {end_time.strftime('%m-%d 08:00')}\n\n"
        await adapter.send_digest_to_channel(header + report_content)
        logger.info("简报已推送到 Telegram 频道")

if __name__ == "__main__":
    asyncio.run(main())
