#!/usr/bin/env python3
"""
采集脚本 - 避免数据库锁定问题
"""

import asyncio
import sys
import os
import sqlite3
from datetime import datetime, timedelta
import logging
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.config import config
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class Message:
    def __init__(self, content: str, timestamp: datetime, source: str, url: str = None):
        self.content = content
        self.timestamp = timestamp
        self.source = source
        self.url = url

def create_database():
    """创建数据库表"""
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect(config.database_path)
    cursor = conn.cursor()
    
    # 创建消息表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        content TEXT NOT NULL,
        source TEXT NOT NULL,
        url TEXT,
        content_hash TEXT UNIQUE,
        url_hash TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON messages(source)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_content_hash ON messages(content_hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_url_hash ON messages(url_hash)')
    
    conn.commit()
    conn.close()
    logger.info("数据库表创建/检查完成")

def save_messages(messages: List[Message]):
    """保存消息到数据库"""
    if not messages:
        logger.info("没有新消息需要保存")
        return 0
    
    conn = sqlite3.connect(config.database_path)
    cursor = conn.cursor()
    
    saved_count = 0
    for msg in messages:
        try:
            # 计算哈希值用于去重
            import hashlib
            content_hash = hashlib.md5(msg.content.encode()).hexdigest()
            url_hash = hashlib.md5(msg.url.encode()).hexdigest() if msg.url else None
            
            # 检查是否已存在
            if url_hash:
                cursor.execute(
                    'SELECT id FROM messages WHERE url_hash = ?',
                    (url_hash,)
                )
            else:
                cursor.execute(
                    'SELECT id FROM messages WHERE content_hash = ?',
                    (content_hash,)
                )
            
            if cursor.fetchone():
                logger.debug(f"消息已存在，跳过: {msg.content[:50]}...")
                continue
            
            # 插入新消息
            cursor.execute('''
            INSERT INTO messages (timestamp, content, source, url, content_hash, url_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                msg.timestamp.isoformat(),
                msg.content,
                msg.source,
                msg.url,
                content_hash,
                url_hash
            ))
            saved_count += 1
            
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
    
    conn.commit()
    conn.close()
    logger.info(f"保存了 {saved_count} 条去重后的消息到 {config.database_path}")
    return saved_count

async def collect_messages():
    """采集消息"""
    logger.info("开始采集消息...")
    
    # 创建数据库
    create_database()
    
    # 初始化适配器
    adapter = TelegramMultiAccountAdapter()
    
    # 设置时间窗口（过去24小时）
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    logger.info(f"时间窗口: {start_time} 到 {end_time}")
    
    all_messages = []
    
    # 采集每个群组的消息
    for chat_url in config.collector_config.monitored_chats:
        logger.info(f"采集群组: {chat_url}")
        try:
            # 使用适配器采集消息
            messages = await adapter.fetch_messages(
                chat_url=chat_url,
                hours_back=24
            )
            
            logger.info(f"从 {chat_url} 采集到 {len(messages)} 条消息")
            
            # 转换为Message对象
            for msg_data in messages:
                msg = Message(
                    content=msg_data.get('content', ''),
                    timestamp=msg_data.get('timestamp', datetime.now()),
                    source=chat_url,
                    url=msg_data.get('url')
                )
                all_messages.append(msg)
                
        except Exception as e:
            logger.error(f"采集群组 {chat_url} 失败: {e}")
    
    # 保存消息
    saved_count = save_messages(all_messages)
    
    logger.info(f"采集完成: 总共采集到 {len(all_messages)} 条消息，保存了 {saved_count} 条去重后的消息")
    return all_messages

def get_last_three_messages():
    """获取最后三条消息"""
    conn = sqlite3.connect(config.database_path)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT timestamp, content, source, url 
    FROM messages 
    ORDER BY timestamp DESC 
    LIMIT 3
    ''')
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'timestamp': row[0],
            'content': row[1],
            'source': row[2],
            'url': row[3]
        })
    
    conn.close()
    return messages

async def push_to_channel(messages):
    """推送消息到频道"""
    if not messages:
        logger.info("没有消息需要推送")
        return False
    
    try:
        adapter = TelegramMultiAccountAdapter()
        
        # 构建消息内容
        message_text = "📊 最新采集消息（最后3条）\n\n"
        
        for i, msg in enumerate(messages, 1):
            source_name = msg['source'].split('/')[-1] if '/' in msg['source'] else msg['source']
            timestamp = msg['timestamp'][:19] if len(msg['timestamp']) > 19 else msg['timestamp']
            
            message_text += f"🔹 **消息 {i}**\n"
            message_text += f"来源: {source_name}\n"
            message_text += f"时间: {timestamp}\n"
            
            # 截取内容，避免消息过长
            content = msg['content']
            if len(content) > 200:
                content = content[:200] + "..."
            
            message_text += f"内容: {content}\n"
            
            if msg['url']:
                message_text += f"链接: {msg['url']}\n"
            
            message_text += "\n"
        
        message_text += "📅 采集时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 推送消息
        success = await adapter.push_to_channel(message_text)
        if success:
            logger.info("消息已成功推送到频道")
        else:
            logger.error("消息推送失败")
        
        return success
        
    except Exception as e:
        logger.error(f"推送消息失败: {e}")
        return False

def create_obsidian_md(messages):
    """创建 Obsidian MD 文件"""
    obsidian_dir = "obsidian-tem"
    os.makedirs(obsidian_dir, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"telegram_collection_{timestamp}.md"
    filepath = os.path.join(obsidian_dir, filename)
    
    # 构建 Markdown 内容
    md_content = f"""# Telegram 信息采集报告

> 采集时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 监控群组: {len(config.collector_config.monitored_chats)} 个

## 📊 采集统计
- 总消息数: {len(messages)}
- 采集时间范围: 过去24小时
- 数据库文件: `{config.database_path}`

## 📋 监控群组列表
"""
    
    # 添加群组列表
    for i, chat in enumerate(config.collector_config.monitored_chats, 1):
        md_content += f"{i}. `{chat}`\n"
    
    md_content += "\n## 📝 最新消息详情\n\n"
    
    # 添加消息详情
    for i, msg in enumerate(messages, 1):
        source_name = msg['source'].split('/')[-1] if '/' in msg['source'] else msg['source']
        
        md_content += f"### 消息 {i}\n"
        md_content += f"- **来源**: `{source_name}`\n"
        md_content += f"- **时间**: `{msg['timestamp']}`\n"
        
        if msg['url']:
            md_content += f"- **链接**: [{msg['url']}]({msg['url']})\n"
        
        md_content += f"- **内容**:\n\n```\n{msg['content']}\n```\n\n"
    
    # 添加系统信息
    md_content += f"""
## 🔧 系统信息
- 项目路径: `{os.path.abspath('.')}`
- 数据库路径: `{os.path.abspath(config.database_path)}`
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
    
    # 1. 采集消息
    print("\n1. 📥 采集消息...")
    messages = await collect_messages()
    
    # 2. 获取最后三条消息
    print("\n2. 📊 获取最后三条消息...")
    last_three = get_last_three_messages()
    print(f"   获取到 {len(last_three)} 条最新消息")
    
    # 3. 推送到频道
    print("\n3. 📤 推送到测试频道...")
    if last_three:
        await push_to_channel(last_three)
    else:
        print("   没有消息需要推送")
    
    # 4. 创建 Obsidian MD 文件
    print("\n4. 📝 创建 Obsidian MD 文件...")
    if messages:
        md_file = create_obsidian_md(last_three)
        print(f"   MD 文件已创建: {md_file}")
    else:
        print("   没有消息，跳过创建 MD 文件")
    
    print("\n" + "=" * 60)
    print("✅ 采集流程完成！")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())