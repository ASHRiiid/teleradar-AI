"""
Telegram 适配器 V2
支持多账号并发采集和消息去重
"""

import asyncio
import hashlib
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime
from dataclasses import dataclass

from telethon import TelegramClient
from telethon.tl.types import Message as TelethonMessage
from telethon.errors import FloodWaitError

from ..models import UnifiedMessage, Platform
from ..config import config, TelegramAccountConfig


logger = logging.getLogger(__name__)


@dataclass
class TelegramClientSession:
    """Telegram 客户端会话管理"""
    account_config: TelegramAccountConfig
    client: Optional[TelegramClient] = None
    is_connected: bool = False
    
    async def connect(self):
        """连接到 Telegram"""
        if self.is_connected:
            return
            
        try:
            self.client = TelegramClient(
                self.account_config.session_name,
                self.account_config.api_id,
                self.account_config.api_hash
            )
            
            # 定义验证码回调函数 - 交互式输入
            async def code_callback():
                import sys
                print(f"\n⚠️  验证码已发送到 {self.account_config.phone}")
                print("请在 Telegram 应用中查看最新的验证码")
                code = input("请输入验证码: ").strip()
                return code
            
            # 定义密码回调函数（如果需要两步验证）
            async def password_callback():
                password = input(f"请输入两步验证密码（如果设置了）: ")
                return password.strip()
            
            # 启动客户端
            await self.client.start(
                phone=self.account_config.phone,
                code_callback=code_callback,
                password=password_callback
            )
            
            self.is_connected = True
            logger.info(f"Telegram 客户端 {self.account_config.account_id} 连接成功")
        except Exception as e:
            logger.error(f"Telegram 连接失败 ({self.account_config.account_id}): {e}")
            raise
    
    async def disconnect(self):
        """断开 Telegram 连接"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            logger.info(f"Telegram 客户端 {self.account_config.account_id} 已断开")
    
    async def fetch_messages(
        self,
        chat_identifier: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100
    ) -> List[UnifiedMessage]:
        """
        获取指定时间范围内的消息
        
        Args:
            chat_identifier: 群组标识符（用户名、ID 或链接）
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大消息数量
            
        Returns:
            UnifiedMessage 列表
        """
        if not self.is_connected:
            await self.connect()
        
        messages = []
        try:
            # 尝试解析标识符，增强容错性
            target = chat_identifier
            if isinstance(chat_identifier, str):
                if chat_identifier.startswith("@"):
                    target = chat_identifier
                elif chat_identifier.replace("-", "").isdigit():
                    # 纯数字标识符，转为整数
                    target = int(chat_identifier)
                elif "|" in chat_identifier:
                    # 如果包含了名字，只取最后一部分标识符
                    target = chat_identifier.split("|")[-1].strip()
                    if target.replace("-", "").isdigit():
                        target = int(target)
            
            # 获取聊天实体
            try:
                chat = await self.client.get_entity(target)
            except ValueError:
                # 如果找不到实体（通常是数字 ID 未缓存），尝试拉取对话列表刷新缓存
                logger.info(f"账号 {self.account_config.account_id} 正在通过对话列表刷新实体缓存...")
                await self.client.get_dialogs()
                chat = await self.client.get_entity(target)
            
            # 获取消息
            # reverse=False (默认): 从 offset_date 向过去扫描
            # offset_date: 扫描的起点
            async for message in self.client.iter_messages(
                chat,
                offset_date=end_time,
                reverse=False,
                limit=limit
            ):
                if not isinstance(message, TelethonMessage):
                    continue
                    
                # 【关键修复】处理时区转换
                # Telegram 返回的是 UTC 时间，需要转换为本地时间进行比较
                message_time_utc = message.date
                # 转换为本地时间 (CST/北京时间)
                message_time = message_time_utc.astimezone().replace(tzinfo=None)
                
                # 如果消息比开始时间还早，说明已经扫完窗口了
                if message_time < start_time:
                    logger.debug(f"消息时间 {message_time} 早于开始时间 {start_time}，停止扫描")
                    break
                
                if message_time > end_time:
                    continue
                
                # 转换为统一消息格式
                unified_msg = self._convert_to_unified_message(message, chat_identifier)
                # 确保统一消息里的时间也是本地时间
                unified_msg.timestamp = message_time
                messages.append(unified_msg)
                
            logger.info(f"账号 {self.account_config.account_id} 从 {chat_identifier} 获取到 {len(messages)} 条消息")
            
        except FloodWaitError as e:
            logger.warning(f"触发 FloodWait ({self.account_config.account_id}): 等待 {e.seconds} 秒")
            await asyncio.sleep(e.seconds)
            # 重试一次
            return await self.fetch_messages(chat_identifier, start_time, end_time, limit)
        except Exception as e:
            logger.error(f"获取消息失败 {chat_identifier} (账号 {self.account_config.account_id}): {e}")
        
        return messages
    
    def _convert_to_unified_message(
        self,
        message: TelethonMessage,
        source_chat: str
    ) -> UnifiedMessage:
        """将 Telethon 消息转换为统一消息格式"""
        
        # 提取消息文本
        text = message.message or ""
        
        # 提取链接
        links = []
        if message.entities:
            for entity in message.entities:
                if hasattr(entity, 'url') and entity.url:
                    links.append(entity.url)
        
        # 获取群组/频道名称
        chat_name = "Unknown Chat"
        if hasattr(message.chat, 'title'):
            chat_name = message.chat.title
        elif hasattr(message.chat, 'first_name'):
            chat_name = message.chat.first_name
            
        # 获取作者名称
        author_name = "Unknown"
        if message.sender:
            if hasattr(message.sender, 'title'):
                author_name = message.sender.title
            elif hasattr(message.sender, 'first_name'):
                first = message.sender.first_name or ""
                last = getattr(message.sender, 'last_name', "") or ""
                author_name = f"{first} {last}".strip() or "Unknown"

        # 创建统一消息 (严格匹配 src/models.py)
        return UnifiedMessage(
            id=f"{self.account_config.account_id}:{message.id}",
            platform=Platform.TELEGRAM,
            external_id=str(message.id),
            content=text,
            author_id=str(message.sender_id) if message.sender_id else "unknown",
            author_name=author_name,
            timestamp=message.date.astimezone().replace(tzinfo=None),
            chat_id=str(message.chat_id),
            chat_name=chat_name,
            urls=links,
            raw_metadata={
                'collector_account': self.account_config.account_id,
                'views': message.views or 0,
                'forwards': message.forwards or 0,
                'reply_to': message.reply_to_msg_id if message.reply_to else None
            }
        )
    
    async def send_to_channel(
        self,
        text: str,
        channel_identifier: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        发送消息到 Telegram 频道
        
        Args:
            text: 消息文本
            channel_identifier: 频道标识符（用户名或ID）
            parse_mode: 解析模式（HTML/Markdown）
            
        Returns:
            是否发送成功
        """
        if not self.is_connected:
            await self.connect()
        
        try:
            # 获取频道实体
            channel = await self.client.get_entity(channel_identifier)
            
            # 发送消息
            await self.client.send_message(
                channel,
                text,
                parse_mode=parse_mode
            )
            
            logger.info(f"账号 {self.account_config.account_id} 消息已发送到频道 {channel_identifier}")
            return True
            
        except Exception as e:
            logger.error(f"发送消息到频道失败 ({self.account_config.account_id}): {e}")
            return False


class TelegramMultiAccountAdapter:
    """多账号 Telegram 适配器"""
    
    def __init__(self):
        """初始化多账号适配器"""
        self.collector_sessions: Dict[str, TelegramClientSession] = {}
        self.main_session: Optional[TelegramClientSession] = None
        self._init_sessions()
        
    def _init_sessions(self):
        """初始化所有会话"""
        # 初始化采集账号会话
        for account_config in config.collector_accounts:
            self.collector_sessions[account_config.account_id] = TelegramClientSession(account_config)
        
        # 初始化主账号会话（用于推送）
        self.main_session = TelegramClientSession(config.main_account)
    
    async def connect_all(self):
        """连接所有会话"""
        connect_tasks = []
        
        # 连接采集会话
        for session in self.collector_sessions.values():
            connect_tasks.append(session.connect())
        
        # 连接主会话
        if self.main_session:
            connect_tasks.append(self.main_session.connect())
        
        results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        # 检查连接结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"连接失败: {result}")
    
    async def disconnect_all(self):
        """断开所有会话连接"""
        disconnect_tasks = []
        
        # 断开采集会话
        for session in self.collector_sessions.values():
            disconnect_tasks.append(session.disconnect())
        
        # 断开主会话
        if self.main_session:
            disconnect_tasks.append(self.main_session.disconnect())
        
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
    
    async def fetch_messages_concurrently(
        self,
        chat_identifiers: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit_per_chat: int = 100
    ) -> List[UnifiedMessage]:
        """
        并发从多个账号获取消息，并进行去重
        
        Args:
            chat_identifiers: 群组标识符列表。如果为 None，则使用各账号配置的群组。
            start_time: 开始时间。如果为 None，默认为 24 小时前。
            end_time: 结束时间。如果为 None，默认为现在。
            limit_per_chat: 每个群组最大消息数量
            
        Returns:
            去重后的 UnifiedMessage 列表
        """
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(hours=24)
            
        all_messages = []
        fetch_tasks = []

        for account_id, session in self.collector_sessions.items():
            # 确定该账号要采集的群组
            target_chats = []
            if chat_identifiers:
                # 如果外部传入了列表，则所有账号都采集这个列表
                target_chats = chat_identifiers
            else:
                # 否则使用账号专属列表，如果没有，则使用全局列表
                target_chats = session.account_config.monitored_chats
                if not target_chats:
                    target_chats = config.collector_config.monitored_chats
            
            if not target_chats:
                logger.warning(f"账号 {account_id} 没有配置监控群组，跳过")
                continue

            for chat_identifier in target_chats:
                fetch_tasks.append(
                    session.fetch_messages(chat_identifier, start_time, end_time, limit_per_chat)
                )
        
        if not fetch_tasks:
            logger.info("没有采集任务需要执行")
            return []

        # 并发执行所有采集任务
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        # 收集所有消息
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"采集任务失败: {result}")
                continue
            if isinstance(result, list):
                all_messages.extend(result)
        
        # 去重处理
        deduplicated_messages = self._deduplicate_messages(all_messages)
        
        logger.info(f"采集完成: 原始消息 {len(all_messages)} 条，去重后 {len(deduplicated_messages)} 条")
        return deduplicated_messages
    
    def _deduplicate_messages(self, messages: List[UnifiedMessage]) -> List[UnifiedMessage]:
        """
        消息去重
        
        去重策略:
        1. 按内容哈希去重（如果配置启用）
        2. 按URL哈希去重（如果配置启用）
        3. 保留时间最早的消息
        """
        if not messages:
            return []
        
        # 创建去重键到消息的映射
        dedup_map: Dict[str, UnifiedMessage] = {}
        
        for message in messages:
            # 生成去重键
            dedup_key = self._generate_deduplication_key(message)
            
            # 检查是否已存在
            if dedup_key in dedup_map:
                existing_msg = dedup_map[dedup_key]
                # 保留时间最早的消息
                if message.timestamp < existing_msg.timestamp:
                    dedup_map[dedup_key] = message
            else:
                dedup_map[dedup_key] = message
        
        return list(dedup_map.values())
    
    def _generate_deduplication_key(self, message: UnifiedMessage) -> str:
        """生成去重键"""
        keys = []
        
        # 按内容去重
        if config.collector_config.deduplicate_by_content and message.content:
            content_hash = hashlib.md5(message.content.encode()).hexdigest()
            keys.append(f"content:{content_hash}")
        
        # 按URL去重
        if config.collector_config.deduplicate_by_url and message.urls:
            url_hash = hashlib.md5('|'.join(sorted(message.urls)).encode()).hexdigest()
            keys.append(f"url:{url_hash}")
        
        # 如果没有任何去重条件，使用消息ID
        if not keys:
            keys.append(f"id:{message.id}")
        
        return '|'.join(keys)
    
    async def send_digest_to_channel(
        self,
        digest_text: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        发送每日简报到 Telegram 频道
        
        Args:
            digest_text: 简报文本
            parse_mode: 解析模式（HTML/Markdown）
            
        Returns:
            是否发送成功
        """
        if not self.main_session:
            logger.error("主会话未初始化")
            return False
        
        # 获取频道标识符
        channel_identifier = config.push_config.channel_username or config.push_config.channel_id
        if not channel_identifier:
            logger.error("未配置频道标识符")
            return False
        
        return await self.main_session.send_to_channel(digest_text, channel_identifier, parse_mode)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect_all()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect_all()


# 向后兼容的单账号适配器
class TelegramAdapter:
    """向后兼容的单账号适配器（使用采集账号1）"""
    
    def __init__(self, api_id: Optional[int] = None, api_hash: Optional[str] = None):
        """初始化单账号适配器"""
        # 如果提供了参数，使用参数；否则使用配置中的采集账号1
        if api_id and api_hash:
            self.account_config = TelegramAccountConfig(
                account_id="legacy",
                api_id=api_id,
                api_hash=api_hash,
                phone="",  # 需要从环境变量获取
                session_name="legacy_session"
            )
        else:
            # 使用采集账号1
            collector_accounts = config.collector_accounts
            if not collector_accounts:
                raise ValueError("未配置采集账号")
            self.account_config = collector_accounts[0]
        
        self.session = TelegramClientSession(self.account_config)
    
    async def fetch_messages_between(
        self,
        chat_identifiers: List[str],
        start_time: datetime,
        end_time: datetime,
        limit_per_chat: int = 100
    ) -> List[UnifiedMessage]:
        """
        获取指定时间范围内的消息（向后兼容）
        
        Args:
            chat_identifiers: 群组标识符列表
            start_time: 开始时间
            end_time: 结束时间
            limit_per_chat: 每个群组最大消息数量
            
        Returns:
            UnifiedMessage 列表
        """
        all_messages = []
        
        for chat_identifier in chat_identifiers:
            messages = await self.session.fetch_messages(chat_identifier, start_time, end_time, limit_per_chat)
            all_messages.extend(messages)
        
        return all_messages
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.session.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.session.disconnect()