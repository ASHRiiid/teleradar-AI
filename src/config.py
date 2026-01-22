"""
配置管理模块
支持多账号 Telegram 采集配置
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TelegramAccountConfig:
    """单个 Telegram 账号配置"""
    account_id: str  # 账号标识，如 'collector1', 'collector2', 'main'
    api_id: int
    api_hash: str
    phone: str
    session_name: str  # 会话文件名称


@dataclass
class CollectorConfig:
    """采集器配置"""
    monitored_chats: List[str]
    max_messages_per_chat: int = 100
    deduplicate_by_content: bool = True
    deduplicate_by_url: bool = True


@dataclass
class PushConfig:
    """推送配置"""
    bot_token: str
    channel_username: Optional[str] = None
    channel_id: Optional[int] = None
    user_id: Optional[int] = None


@dataclass
class AIConfig:
    """AI 服务配置"""
    deepseek_api_key: str
    openai_base_url: str = "https://api.deepseek.com"


@dataclass
class AppConfig:
    """应用主配置"""
    # 主账号（用于推送）
    main_account: TelegramAccountConfig
    
    # 采集账号列表
    collector_accounts: List[TelegramAccountConfig]
    
    # 采集配置
    collector_config: CollectorConfig
    
    # 推送配置
    push_config: PushConfig
    
    # AI 配置
    ai_config: AIConfig
    
    # 其他配置
    obsidian_vault_path: Optional[str] = None
    jina_reader_base_url: str = "https://r.jina.ai/"


def _safe_int(value: Optional[str]) -> Optional[int]:
    """安全地将字符串转换为整数"""
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def load_config() -> AppConfig:
    """从环境变量加载配置"""
    
    # 解析监控的群组
    monitored_chats_str = os.getenv("MONITORED_CHATS", "")
    monitored_chats = [chat.strip() for chat in monitored_chats_str.split(",") if chat.strip()]
    
    # 主账号配置
    main_account = TelegramAccountConfig(
        account_id="main",
        api_id=int(os.getenv("TELEGRAM_MAIN_API_ID", "0")),
        api_hash=os.getenv("TELEGRAM_MAIN_API_HASH", ""),
        phone=os.getenv("TELEGRAM_MAIN_PHONE", ""),
        session_name="main_session"
    )
    
    # 采集账号配置
    collector_accounts = []
    
    # 采集账号1
    collector1_api_id = os.getenv("TELEGRAM_COLLECTOR1_API_ID")
    if collector1_api_id:
        collector_accounts.append(TelegramAccountConfig(
            account_id="collector1",
            api_id=int(collector1_api_id),
            api_hash=os.getenv("TELEGRAM_COLLECTOR1_API_HASH", ""),
            phone=os.getenv("TELEGRAM_COLLECTOR1_PHONE", ""),
            session_name="collector1_session"
        ))
    
    # 采集账号2
    collector2_api_id = os.getenv("TELEGRAM_COLLECTOR2_API_ID")
    if collector2_api_id:
        collector_accounts.append(TelegramAccountConfig(
            account_id="collector2",
            api_id=int(collector2_api_id),
            api_hash=os.getenv("TELEGRAM_COLLECTOR2_API_HASH", ""),
            phone=os.getenv("TELEGRAM_COLLECTOR2_PHONE", ""),
            session_name="collector2_session"
        ))
    
    # 采集配置
    collector_config = CollectorConfig(
        monitored_chats=monitored_chats,
        max_messages_per_chat=100,
        deduplicate_by_content=True,
        deduplicate_by_url=True
    )
    
    # 推送配置
    push_config = PushConfig(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        channel_username=os.getenv("TELEGRAM_CHANNEL_USERNAME"),
        channel_id=_safe_int(os.getenv("TELEGRAM_CHANNEL_ID")),
        user_id=_safe_int(os.getenv("TELEGRAM_USER_ID"))
    )
    
    # AI 配置
    ai_config = AIConfig(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    )
    
    # 应用配置
    config = AppConfig(
        main_account=main_account,
        collector_accounts=collector_accounts,
        collector_config=collector_config,
        push_config=push_config,
        ai_config=ai_config,
        obsidian_vault_path=os.getenv("OBSIDIAN_VAULT_PATH"),
        jina_reader_base_url=os.getenv("JINA_READER_BASE_URL", "https://r.jina.ai/")
    )
    
    return config


# 全局配置实例
config = load_config()