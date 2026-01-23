#!/usr/bin/env python3
"""
兼容现有数据库结构的采集脚本
"""

import asyncio
import sys
import os
import sqlite3
import uuid
import json
from datetime import datetime, timedelta, timezone
import logging
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import config
from src.storage import Storage
from src.processors.summarizer import AISummarizer
from src.models import UnifiedMessage, Platform
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def ensure_database():
    """确保数据库表存在"""
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect('data/raw_messages.db')
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
    if not cursor.fetchone():
        # 创建表（使用现有结构）
        cursor.execute('''
        CREATE TABLE messages (
            internal_id TEXT PRIMARY KEY,
            platform TEXT,
            external_id TEXT,
            chat_id TEXT,
            chat_name TEXT,
            author_name TEXT,
            content TEXT,
            urls TEXT,
            timestamp DATETIME,
            processed INTEGER DEFAULT 0,
            UNIQUE(platform, chat_id, external_id)
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX idx_timestamp ON messages(timestamp)')
        logger.info("创建了新的数据库表")
    else:
        logger.info("数据库表已存在")
    
    conn.commit()
    conn.close()

async def collect_from_group(client: TelegramClient, chat_url: str, hours_back: int = 24) -> List[Dict[str, Any]]:
    """从单个群组采集消息"""
    messages = []
    
    try:
        # 处理可能的数字 ID
        target = chat_url
        if isinstance(chat_url, str) and (chat_url.isdigit() or (chat_url.startswith('-') and chat_url[1:].isdigit())):
            try:
                target = int(chat_url)
            except ValueError:
                pass

        # 获取群组实体
        entity = await client.get_entity(target)
        chat_name = entity.title if hasattr(entity, 'title') else str(entity.id)
        chat_id = str(entity.id)
        
        logger.info(f"开始采集群组: {chat_name}")
        
        # 计算时间范围
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        # 获取消息
        async for message in client.iter_messages(entity, limit=100):
            # 检查消息时间 (message.date 已经是 timezone-aware UTC)
            if message.date < start_time:
                break
            
            # 提取消息内容
            content = message.text or message.message or ""
            if not content.strip():
                continue
            
            # 提取URL
            urls = []
            if message.entities:
                for entity in message.entities:
                    if hasattr(entity, 'url'):
                        urls.append(entity.url)
            
            # 构建消息数据
            msg_data = {
                'internal_id': str(uuid.uuid4()),
                'platform': 'telegram',
                'external_id': str(message.id),
                'chat_id': chat_id,
                'chat_name': chat_name,
                'author_name': message.sender_id if message.sender_id else 'unknown',
                'content': content,
                'urls': ','.join(urls) if urls else '',
                'timestamp': message.date.isoformat(),
                'processed': 0
            }
            
            messages.append(msg_data)
            
            if len(messages) >= 50:  # 限制每次采集数量
                break
        
        logger.info(f"从 {chat_name} 采集到 {len(messages)} 条消息")
        
    except Exception as e:
        logger.error(f"采集群组 {chat_url} 失败: {e}")
    
    return messages

def save_messages(messages: List[Dict[str, Any]]) -> int:
    """保存消息到数据库"""
    if not messages:
        return 0
    
    conn = sqlite3.connect('data/raw_messages.db')
    cursor = conn.cursor()
    
    saved_count = 0
    for msg in messages:
        try:
            # 检查是否已存在
            cursor.execute(
                'SELECT internal_id FROM messages WHERE platform = ? AND chat_id = ? AND external_id = ?',
                (msg['platform'], msg['chat_id'], msg['external_id'])
            )
            
            if cursor.fetchone():
                logger.debug(f"消息已存在，跳过: {msg['content'][:50]}...")
                continue
            
            # 插入新消息
            cursor.execute('''
            INSERT INTO messages 
            (internal_id, platform, external_id, chat_id, chat_name, author_name, content, urls, timestamp, processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                msg['internal_id'],
                msg['platform'],
                msg['external_id'],
                msg['chat_id'],
                msg['chat_name'],
                msg['author_name'],
                msg['content'],
                msg['urls'],
                msg['timestamp'],
                msg['processed']
            ))
            
            saved_count += 1
            
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
    
    conn.commit()
    conn.close()
    
    return saved_count

def get_last_three_messages() -> List[Dict[str, Any]]:
    """获取最后三条消息"""
    conn = sqlite3.connect('data/raw_messages.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT chat_name, content, urls, timestamp 
    FROM messages 
    ORDER BY timestamp DESC 
    LIMIT 3
    ''')
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'chat_name': row[0],
            'content': row[1],
            'urls': row[2],
            'timestamp': row[3]
        })
    
    conn.close()
    return messages

async def push_to_channel(messages: List[Dict[str, Any]]) -> bool:
    """推送消息到频道"""
    if not messages:
        logger.info("没有消息需要推送")
        return False
    
    try:
        # 使用主账号连接
        main_account = config.main_account
        client = TelegramClient(
            main_account.session_name,
            main_account.api_id,
            main_account.api_hash
        )
        
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error("主账号未认证")
            return False
        
        # 获取频道
        channel = await client.get_entity(config.push_config.channel_username)
        
        # 构建消息内容
        message_text = "📊 **AI 智能信息简报**\n\n"
        
        for i, msg in enumerate(messages, 1):
            message_text += f"🔹 **{msg['chat_name']}**\n"
            
            # 使用 AI 摘要，如果没有则使用原内容
            summary = msg.get('summary', msg['content'])
            if len(summary) > 300:
                summary = summary[:300] + "..."
            
            message_text += f"📝 {summary}\n"
            
            # 添加标签
            if msg.get('tags'):
                tags = msg['tags']
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except:
                        tags = tags.split(',')
                message_text += f"🏷 `{'` `'.join(tags)}`\n"
            
            if msg['urls']:
                urls = msg['urls'].split(',')
                message_text += f"🔗 [查看原文]({urls[0]})\n"
            
            message_text += "\n"
        
        message_text += "📅 生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 发送消息
        await client.send_message(channel, message_text, link_preview=False)
        logger.info("消息已成功推送到频道")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"推送消息失败: {e}")
        return False

def create_obsidian_md(messages: List[Dict[str, Any]]) -> str:
    """创建 Obsidian MD 文件"""
    obsidian_dir = "obsidian-tem"
    os.makedirs(obsidian_dir, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"AI_Report_{timestamp}.md"
    filepath = os.path.join(obsidian_dir, filename)
    
    # 获取数据库统计
    conn = sqlite3.connect('data/raw_messages.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM messages')
    total_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM messages WHERE processed = 1')
    analyzed_count = cursor.fetchone()[0]
    conn.close()
    
    # 构建 Markdown 内容
    md_content = f"""# 🤖 AI 智能信息分析报告

> 报告时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 数据库总消息: {total_count} | 已完成 AI 分析: {analyzed_count}

## 📊 本次分析摘要

"""
    
    # 添加分析详情
    for i, msg in enumerate(messages, 1):
        md_content += f"### {i}. {msg['chat_name']}\n"
        md_content += f"- **采集时间**: `{msg['timestamp']}`\n"
        
        # 标签
        tags = msg.get('tags', [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except:
                tags = []
        
        if tags:
            md_content += f"- **标签**: {' '.join([f'#{tag}' for tag in tags])}\n"
        
        md_content += f"\n#### 💡 AI 摘要\n{msg.get('summary', '无摘要')}\n"
        
        if msg['urls']:
            urls = msg['urls'].split(',')
            md_content += f"\n#### 🔗 相关链接\n"
            for url in urls:
                md_content += f"- [{url}]({url})\n"
        
        md_content += f"\n#### 📄 原始消息\n<details>\n<summary>点击展开</summary>\n\n```\n{msg['content']}\n```\n\n</details>\n\n---\n"
    
    # 添加系统信息
    md_content += f"""
## 🔧 系统状态
- 采集群组: {len(config.collector_config.monitored_chats)} 个
- 运行模式: 自动化全流程 (采集 -> 存储 -> AI 分析 -> 推送)
- AI 模型: `deepseek-chat`

*此文件由 Telegram 信息自动化系统自动生成*
"""
    
    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    logger.info(f"Obsidian MD 文件已创建: {filepath}")
    return filepath

async def main():
    """主函数"""
    print("=" * 60)
    print("Telegram 信息自动化系统 - 完整采集流程 (多账号并发版)")
    print("=" * 60)
    
    # 初始化组件
    storage = Storage()
    summarizer = AISummarizer(api_key=config.ai_config.deepseek_api_key, base_url=config.ai_config.openai_base_url)
    
    # 确保数据库存在
    ensure_database()
    
    # 使用多账号适配器
    async with TelegramMultiAccountAdapter() as adapter:
        # 1. 采集消息
        print("\n1. 📥 并发采集消息...")
        start_time = datetime.now() - timedelta(hours=24)
        end_time = datetime.now()
        
        # fetch_messages_concurrently 会自动根据账号配置进行采集
        unified_messages = await adapter.fetch_messages_concurrently(
            start_time=start_time,
            end_time=end_time,
            limit_per_chat=100
        )
        
        print(f"   总共采集到 {len(unified_messages)} 条去重后的消息")
        
        # 2. 保存消息
        print("\n2. 💾 保存消息到数据库...")
        saved_count = 0
        for msg in unified_messages:
            # 检查是否已存在（storage.save_message 内部使用 INSERT OR IGNORE）
            # 注意：UnifiedMessage 的 id 在 adapter 中被设置为 "{account_id}:{msg_id}"
            # 但在 messages 表中 UNIQUE(platform, chat_id, external_id) 才是真正的唯一键
            storage.save_message(msg)
            saved_count += 1 # 这里其实无法精确知道是否真的插入了，但 save_message 是幂等的
        
        print(f"   处理了 {saved_count} 条消息")
        
        # 3. AI 分析
        print("\n3. 🤖 执行 AI 深度分析...")
        unprocessed = storage.get_unprocessed()
        if unprocessed:
            print(f"   发现 {len(unprocessed)} 条待分析消息，正在处理...")
            for row in unprocessed[:10]: # 每次流程最多处理10条新消息
                try:
                    # 转换行数据为 UnifiedMessage 以便 summarizer 处理
                    msg = UnifiedMessage(
                        id=row['internal_id'],
                        platform=Platform(row['platform']),
                        external_id=row['external_id'],
                        content=row['content'],
                        author_id="unknown",
                        author_name=row['author_name'],
                        timestamp=datetime.fromisoformat(row['timestamp']) if isinstance(row['timestamp'], str) else row['timestamp'],
                        chat_id=row['chat_id'],
                        chat_name=row['chat_name'],
                        urls=row['urls'].split(',') if row['urls'] else []
                    )
                    
                    result = await summarizer.summarize_message(msg, [])
                    storage.update_message_summary(msg.id, result.get("summary", ""), result.get("tags", []))
                    print(f"   ✅ 已分析: {msg.chat_name}")
                except Exception as e:
                    print(f"   ❌ 分析失败: {e}")
        else:
            print("   没有待分析的消息")

        # 4. 获取已分析的消息并推送/归档
        # ... (后续逻辑保持基本一致)

        # 4. 获取最后三条已分析的消息
        print("\n4. 📊 获取已分析消息...")
        conn = sqlite3.connect('data/raw_messages.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT chat_name, content, urls, timestamp, summary, tags 
            FROM messages 
            WHERE processed = 1
            ORDER BY timestamp DESC 
            LIMIT 5
        ''')
        analyzed_messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # 5. 推送到频道
        print("\n5. 📤 推送到测试频道...")
        if analyzed_messages:
            success = await push_to_channel(analyzed_messages[:3])
            if success:
                print("   ✅ 消息已推送到频道")
            else:
                print("   ❌ 消息推送失败")
        else:
            print("   没有消息需要推送")
        
        # 6. 创建 Obsidian MD 文件
        print("\n6. 📝 创建 Obsidian MD 文件...")
        if analyzed_messages:
            md_file = create_obsidian_md(analyzed_messages)
            print(f"   ✅ MD 文件已创建: {md_file}")
        else:
            print("   没有消息，跳过创建 MD 文件")
        
        print("\n" + "=" * 60)
        print("✅ 采集与分析流程完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
