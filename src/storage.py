import sqlite3
from datetime import datetime
from src.models import UnifiedMessage, Platform
import json
from loguru import logger

class Storage:
    def __init__(self, db_path: str = "data/raw_messages.db"):
        import os
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
                    processed INTEGER DEFAULT 0,
                    UNIQUE(platform, chat_id, external_id)
                )
            """)
            conn.commit()

    def save_message(self, msg: UnifiedMessage):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO messages 
                    (internal_id, platform, external_id, chat_id, chat_name, author_name, content, urls, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg.id,
                    msg.platform.value,
                    msg.external_id,
                    msg.chat_id,
                    msg.chat_name,
                    msg.author_name,
                    msg.content,
                    json.dumps(msg.urls),
                    msg.timestamp
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save message to DB: {e}")

    def get_unprocessed(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM messages WHERE processed = 0")
            return cursor.fetchall()

    def mark_as_processed(self, internal_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE messages SET processed = 1 WHERE internal_id = ?", (internal_id,))
            conn.commit()
