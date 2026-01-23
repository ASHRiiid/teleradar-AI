import sqlite3
from datetime import datetime
from src.models import UnifiedMessage, Platform
from typing import List, Optional
import json
from loguru import logger

from src.config import config

class Storage:
    def __init__(self, db_path: Optional[str] = None):
        import os
        if db_path is None:
            db_path = config.database_path
            
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    internal_id TEXT PRIMARY KEY,
                    platform TEXT,
                    external_id TEXT,
                    chat_id TEXT,
                    chat_name TEXT,
                    author_name TEXT,
                    content TEXT,
                    urls TEXT,
                    timestamp DATETIME,
                    summary TEXT,
                    tags TEXT,
                    processed INTEGER DEFAULT 0,
                    UNIQUE(platform, chat_id, external_id)
                )
            """)
            # Ensure columns exist if table was created earlier
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(messages)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'summary' not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN summary TEXT")
            if 'tags' not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN tags TEXT")
            conn.commit()

    def save_message(self, msg: UnifiedMessage):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO messages 
                    (internal_id, platform, external_id, chat_id, chat_name, author_name, content, urls, timestamp, summary, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg.id,
                    msg.platform.value,
                    msg.external_id,
                    msg.chat_id,
                    msg.chat_name,
                    msg.author_name,
                    msg.content,
                    json.dumps(msg.urls),
                    msg.timestamp,
                    msg.summary,
                    json.dumps(msg.tags)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save message to DB: {e}")

    def update_message_summary(self, internal_id: str, summary: str, tags: List[str]):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE messages 
                    SET summary = ?, tags = ?, processed = 1 
                    WHERE internal_id = ?
                """, (summary, json.dumps(tags), internal_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update message summary: {e}")

    def get_unprocessed(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM messages WHERE processed = 0")
            return cursor.fetchall()

    def mark_as_processed(self, internal_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE messages SET processed = 1 WHERE internal_id = ?", (internal_id,))
            conn.commit()
