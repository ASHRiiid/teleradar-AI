#!/usr/bin/env python3
"""
Telegram 告警集成模块
支持严重告警和警告告警，支持多账号推送和重试机制。
"""

import asyncio
import os
import sys
import argparse
import logging
from datetime import datetime
from typing import Optional, List

# 确保可以从 src 导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import config
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("TelegramAlerter")

class TelegramAlerter:
    def __init__(self):
        self.adapter = TelegramMultiAccountAdapter()

    async def _send_via_session(self, session, text: str, targets: List[str]) -> bool:
        """使用特定会话发送消息到多个目标"""
        if not session:
            return False
            
        success_any = False
        for target in targets:
            try:
                # 尝试发送
                res = await session.send_to_channel(text, target, parse_mode="HTML")
                if res:
                    logger.info(f"账号 {session.account_config.account_id} 成功发送到 {target}")
                    success_any = True
            except Exception as e:
                logger.error(f"账号 {session.account_config.account_id} 发送到 {target} 失败: {e}")
        return success_any

    async def send_alert(self, 
                         level: str, 
                         problem: str, 
                         status: str, 
                         log_path: Optional[str] = None, 
                         suggestion: Optional[str] = None,
                         use_all_accounts: bool = False) -> bool:
        """
        发送告警消息
        
        Args:
            level: 'critical' 或 'warning'
            problem: 问题描述
            status: 当前状态
            log_path: 日志路径 (critical)
            suggestion: 建议 (warning)
            use_all_accounts: 是否使用所有配置的账号发送 (提高可靠性)
        """
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if level.lower() == "critical":
            emoji = "🔴"
            title = "【严重告警】自动化系统异常"
            extra_label = "日志"
            extra_value = log_path if log_path else "未提供"
        else:
            emoji = "⚠️"
            title = "【系统警告】自动化系统检测到问题"
            extra_label = "建议"
            extra_value = suggestion if suggestion else "检查系统状态"

        # 构造 HTML 格式的消息 (Telegram 支持 HTML)
        message = (
            f"<b>{emoji}{title}</b>\n"
            f"时间: {time_str}\n"
            f"问题: {problem}\n"
            f"状态: {status}\n"
            f"{extra_label}: {extra_value}"
        )

        # 确定推送目标
        targets = []
        if config.push_config.channel_username:
            targets.append(config.push_config.channel_username)
        if config.push_config.channel_id:
            targets.append(str(config.push_config.channel_id))
        if config.push_config.user_id:
            targets.append(str(config.push_config.user_id))
            
        if not targets:
            logger.error("未配置任何推送目标 (CHANNEL_ID/CHANNEL_USERNAME/USER_ID)")
            return False

        async with self.adapter as adapter:
            # 待使用的会话列表
            sessions_to_use = []
            if adapter.main_session:
                sessions_to_use.append(adapter.main_session)
            
            if use_all_accounts:
                sessions_to_use.extend(adapter.collector_sessions.values())
            
            if not sessions_to_use:
                logger.error("没有可用的 Telegram 会话")
                return False

            overall_success = False
            for session in sessions_to_use:
                # 带有重试机制的发送
                for attempt in range(3):
                    try:
                        if await self._send_via_session(session, message, targets):
                            overall_success = True
                            if not use_all_accounts:
                                return True # 只要主账号成功且不要求全部发送，就返回
                            break # 当前账号成功，跳出重试
                    except Exception as e:
                        logger.warning(f"账号 {session.account_config.account_id} 尝试 {attempt+1} 失败: {e}")
                        await asyncio.sleep(1)
                
            return overall_success

async def main():
    parser = argparse.ArgumentParser(description="Telegram 告警集成模块")
    parser.add_argument("--level", choices=["critical", "warning"], default="warning", help="告警级别 (默认: warning)")
    parser.add_argument("--problem", required=True, help="问题描述")
    parser.add_argument("--status", required=True, help="当前状态")
    parser.add_argument("--log", help="日志路径 (用于严重告警)")
    parser.add_argument("--suggestion", help="建议操作 (用于警告告警)")
    parser.add_argument("--all-accounts", action="store_true", help="使用所有配置账号发送告警以提高可靠性")

    args = parser.parse_args()

    alerter = TelegramAlerter()
    try:
        success = await alerter.send_alert(
            level=args.level,
            problem=args.problem,
            status=args.status,
            log_path=args.log,
            suggestion=args.suggestion,
            use_all_accounts=args.all_accounts
        )
        
        if success:
            logger.info("告警任务执行成功")
            sys.exit(0)
        else:
            logger.error("告警任务执行失败")
            sys.exit(1)
    except Exception as e:
        logger.error(f"运行告警模块时发生未处理的错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
