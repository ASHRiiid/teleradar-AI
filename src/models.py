from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Platform(str, Enum):
    TELEGRAM = "telegram"
    WECHAT = "wechat"
    FEISHU = "feishu"
    DISCORD = "discord"

class UnifiedMessage(BaseModel):
    id: str = Field(description="Internal unique ID")
    platform: Platform
    external_id: str = Field(description="Platform specific message ID")
    
    content: str
    author_id: str
    author_name: str
    timestamp: datetime
    
    chat_id: str = Field(description="Group or DM ID")
    chat_name: Optional[str] = None
    
    urls: List[str] = []
    summary: Optional[str] = None
    tags: List[str] = []
    
    raw_metadata: Dict[str, Any] = {}

class ScrapedContent(BaseModel):
    url: str
    title: Optional[str]
    markdown: str
    timestamp: datetime = Field(default_factory=datetime.now)
