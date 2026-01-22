#!/usr/bin/env python3
"""
兼容现有数据库结构的采集脚本
"""

import asyncio
import sys
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import config
from telethon import TelegramClient
from telethon.tl.types import Message as TLMessage

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
        # 获取群组实体
        entity = await client.get_entity(chat_url)
        chat_name = entity.title if hasattr(entity, 'title') else str(entity.id)
        chat_id = str(entity.id)
        
        logger.info(f"开始采集群组: {chat_name}")
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        # 获取消息
        async for message in client.iter_messages(entity, limit=100):
            # 检查消息时间
            if message.date.replace(tzinfo=None) < start_time:
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
                'timestamp': message.date.replace(tzinfo=None).isoformat(),
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
        message_text = "📊 最新采集消息（最后3条）\n\n"
        
        for i, msg in enumerate(messages, 1):
            message_text += f"🔹 **消息 {i}**\n"
            message_text += f"来源: {msg['chat_name']}\n"
            message_text += f"时间: {msg['timestamp'][:19]}\n"
            
            # 截取内容
            content = msg['content']
            if len(content) > 200:
                content = content[:200] + "..."
            
            message_text += f"内容: {content}\n"
            
            if msg['urls']:
                urls = msg['urls'].split(',')
                for url in urls[:2]:  # 最多显示2个URL
                    message_text += f"链接: {url}\n"
            
            message_text += "\n"
        
        message_text += "📅 采集时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 发送消息
        await client.send_message(channel, message_text)
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
    filename = f"telegram_collection_{timestamp}.md"
    filepath = os.path.join(obsidian_dir, filename)
    
    # 获取数据库统计
    conn = sqlite3.connect('data/raw_messages.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM messages')
    total_count = cursor.fetchone()[0]
    conn.close()
    
    # 构建 Markdown 内容
    md_content = f"""# Telegram 信息采集报告

> 采集时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 监控群组: {len(config.collector_config.monitored_chats)} 个
> 数据库消息总数: {total_count} 条

## 📊 采集统计
- 本次采集消息数: {len(messages)}
- 采集时间范围: 过去24小时
- 数据库文件: `data/raw_messages.db`

## 📋 监控群组列表
"""
    
    # 添加群组列表
    for i, chat in enumerate(config.collector_config.monitored_chats, 1):
        md_content += f"{i}. `{chat}`\n"
    
    md_content += "\n## 📝 最新消息详情\n\n"
    
    # 添加消息详情
    for i, msg in enumerate(messages, 1):
        md_content += f"### 消息 {i}\n"
        md_content += f"- **来源**: `{msg['chat_name']}`\n"
        md_content += f"- **时间**: `{msg['timestamp']}`\n"
        
        if msg['urls']:
            urls = msg['urls'].split(',')
            md_content += f"- **链接**:\n"
            for url in urls:
                md_content += f"  - [{url}]({url})\n"
        
        md_content += f"- **内容**:\n\n```\n{msg['content']}\n```\n\n"
    
    # 添加系统信息
    md_content += f"""
## 🔧 系统信息
- 项目路径: `{os.path.abspath('.')}`
- 数据库路径: `{os.path.abspath('data/raw_messages.db')}`
- 采集账号: {config.collector_accounts[0].phone if config.collector_accounts else '未配置'}
- 推送频道: {config.push_config.channel_username}

## 📈 后续操作
1. 运行 AI 分析: `python3 analyze_messages.py`
2. 生成简报: `python3 generate_summary.py`
3. 定时采集: 设置 cron 任务每小时运行一次

---

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
    print("Telegram 信息自动化系统 - 完整采集流程")
    print("=" * 60)
    
    # 确保数据库存在
    ensure_database()
    
    # 使用采集账号
    collector_account = config.collector_accounts[0]
    client = TelegramClient(
        collector_account.session_name,
        collector_account.api_id,
        collector_account.api_hash
    )
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ 采集账号未认证")
            return
        
        print("✅ 采集账号连接成功")
        
        # 1. 采集消息
        print("\n1. 📥 采集消息...")
        all_messages = []
        
        for chat_url in config.collector_config.monitored_chats:
            print(f"   采集群组: {chat_url}")
            messages = await collect_from_group(client, chat_url, hours_back=24)
            all_messages.extend(messages)
        
        print(f"   总共采集到 {len(all_messages)} 条消息")
        
        # 2. 保存消息
        print("\n2. 💾 保存消息到数据库...")
        saved_count = save_messages(all_messages)
        print(f"   保存了 {saved_count} 条去重后的消息")
        
        # 3. 获取最后三条消息
        print("\n3. 📊 获取最后三条消息...")
        last_three = get_last_three_messages()
        print(f"   获取到 {len(last_three)} 条最新消息")
        
        # 4. 推送到频道
        print("\n4. 📤 推送到测试频道...")
        if last_three:
            success = await push_to_channel(last_three)
            if success:
                print("   ✅ 消息已推送到频道")
            else:
                print("   ❌ 消息推送失败")
        else:
            print("   没有消息需要推送")
        
        # 5. 创建 Obsidian MD 文件
        print("\n5. 📝 创建 Obsidian MD 文件...")
        if last_three:
            md_file = create_obsidian_md(last_three)
            print(f"   ✅ MD 文件已创建: {md_file}")
        else:
            print("   没有消息，跳过创建 MD 文件")
        
        print("\n" + "=" * 60)
        print("✅ 采集流程完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 采集失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())