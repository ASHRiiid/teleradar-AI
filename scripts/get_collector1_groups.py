#!/usr/bin/env python3
"""
动态获取采集账号1加入的所有群组
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import load_config
from src.telegram_client import create_telegram_client

async def get_collector1_groups():
    """获取采集账号1加入的所有群组"""
    config = load_config()
    
    # 创建采集账号1的客户端
    client = await create_telegram_client(
        api_id=config.COLLECTOR1_API_ID,
        api_hash=config.COLLECTOR1_API_HASH,
        phone=config.COLLECTOR1_PHONE,
        session_name="collector1"
    )
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("采集账号1未授权，请先登录")
            return []
        
        print("正在获取采集账号1的群组列表...")
        
        # 获取所有对话（包括群组、频道、私聊）
        dialogs = await client.get_dialogs()
        
        # 过滤出群组和频道（排除私聊）
        groups = []
        for dialog in dialogs:
            # 检查是否是群组或频道
            if hasattr(dialog.entity, 'megagroup') or hasattr(dialog.entity, 'broadcast'):
                group_info = {
                    'id': dialog.entity.id,
                    'title': dialog.entity.title,
                    'username': getattr(dialog.entity, 'username', None),
                    'is_channel': hasattr(dialog.entity, 'broadcast'),
                    'is_group': hasattr(dialog.entity, 'megagroup'),
                }
                groups.append(group_info)
        
        print(f"找到 {len(groups)} 个群组/频道")
        
        # 按标题排序
        groups.sort(key=lambda x: x['title'].lower())
        
        # 打印群组列表
        for i, group in enumerate(groups, 1):
            group_type = "频道" if group['is_channel'] else "群组"
            username_str = f" (@{group['username']})" if group['username'] else ""
            print(f"{i:3d}. {group['title']}{username_str} [{group_type}]")
        
        return groups
        
    except Exception as e:
        print(f"获取群组列表失败: {e}")
        return []
    finally:
        await client.disconnect()

def update_env_file(groups):
    """更新.env文件中的MONITORED_CHATS_COLLECTOR1配置"""
    env_file = project_root / ".env"
    
    if not env_file.exists():
        print(f".env文件不存在: {env_file}")
        return False
    
    try:
        # 读取.env文件内容
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 构建新的群组列表字符串
        group_ids = [str(group['id']) for group in groups]
        new_value = ','.join(group_ids)
        
        # 更新或添加MONITORED_CHATS_COLLECTOR1配置
        updated = False
        new_lines = []
        
        for line in lines:
            if line.strip().startswith('MONITORED_CHATS_COLLECTOR1='):
                # 更新现有配置
                new_lines.append(f'MONITORED_CHATS_COLLECTOR1={new_value}\n')
                updated = True
            else:
                new_lines.append(line)
        
        if not updated:
            # 添加新配置
            new_lines.append(f'\n# ======================\n')
            new_lines.append(f'# 监控配置 (由脚本自动同步)\n')
            new_lines.append(f'# ======================\n')
            new_lines.append(f'MONITORED_CHATS_COLLECTOR1={new_value}\n')
        
        # 写入更新后的文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"已更新.env文件中的MONITORED_CHATS_COLLECTOR1配置")
        print(f"监控群组数量: {len(group_ids)}")
        
        return True
        
    except Exception as e:
        print(f"更新.env文件失败: {e}")
        return False

async def main():
    """主函数"""
    print("=== 动态获取采集账号1群组列表 ===")
    
    # 获取群组列表
    groups = await get_collector1_groups()
    
    if not groups:
        print("未找到任何群组，退出")
        return
    
    # 询问是否更新.env文件
    print(f"\n是否更新.env文件中的MONITORED_CHATS_COLLECTOR1配置？")
    response = input("输入 'y' 确认更新，其他任意键取消: ").strip().lower()
    
    if response == 'y':
        if update_env_file(groups):
            print("✅ 配置更新成功")
        else:
            print("❌ 配置更新失败")
    else:
        print("取消更新，保持现有配置")

if __name__ == "__main__":
    asyncio.run(main())