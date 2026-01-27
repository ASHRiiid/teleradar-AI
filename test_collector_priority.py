#!/usr/bin/env python3
"""
测试采集账号优先级逻辑

测试场景：
1. 模拟账号1和账号2采集同一频道的消息
2. 验证去重逻辑优先保留账号1的消息
3. 验证账号2的逻辑保持不变
"""

import asyncio
from datetime import datetime, timedelta
from src.models import UnifiedMessage, Platform

def test_deduplication_priority():
    """测试去重优先级逻辑"""
    print("🧪 测试采集账号优先级逻辑...")
    
    # 创建测试消息
    base_time = datetime.now()
    
    # 消息1：来自账号1，时间较晚
    msg1 = UnifiedMessage(
        id="collector1:1001",
        platform=Platform.TELEGRAM,
        external_id="1001",
        content="测试消息1",
        author_id="user1",
        author_name="用户1",
        timestamp=base_time - timedelta(minutes=10),  # 较晚
        chat_id="-1001234567890",
        chat_name="测试频道",
        urls=[],
        raw_metadata={'collector_account': 'collector1', 'views': 100}
    )
    
    # 消息2：来自账号2，时间较早（同一内容）
    msg2 = UnifiedMessage(
        id="collector2:1002",
        platform=Platform.TELEGRAM,
        external_id="1002",
        content="测试消息1",  # 相同内容
        author_id="user1",
        author_name="用户1",
        timestamp=base_time - timedelta(minutes=20),  # 较早
        chat_id="-1001234567890",
        chat_name="测试频道",
        urls=[],
        raw_metadata={'collector_account': 'collector2', 'views': 50}
    )
    
    # 消息3：来自账号2，不同内容
    msg3 = UnifiedMessage(
        id="collector2:1003",
        platform=Platform.TELEGRAM,
        external_id="1003",
        content="测试消息2",  # 不同内容
        author_id="user2",
        author_name="用户2",
        timestamp=base_time - timedelta(minutes=15),
        chat_id="-1001234567890",
        chat_name="测试频道",
        urls=[],
        raw_metadata={'collector_account': 'collector2', 'views': 30}
    )
    
    # 消息4：来自账号1，不同内容
    msg4 = UnifiedMessage(
        id="collector1:1004",
        platform=Platform.TELEGRAM,
        external_id="1004",
        content="测试消息3",  # 不同内容
        author_id="user3",
        author_name="用户3",
        timestamp=base_time - timedelta(minutes=5),
        chat_id="-1001234567890",
        chat_name="测试频道",
        urls=[],
        raw_metadata={'collector_account': 'collector1', 'views': 80}
    )
    
    # 导入并测试去重逻辑
    from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter
    
    # 创建适配器实例（需要模拟配置）
    class MockConfig:
        class collector_config:
            deduplicate_by_content = True
            deduplicate_by_url = False
    
    import sys
    sys.modules['src.config'].config = MockConfig()
    
    adapter = TelegramMultiAccountAdapter()
    
    # 测试去重
    messages = [msg1, msg2, msg3, msg4]
    deduped = adapter._deduplicate_messages(messages)
    
    print(f"📊 原始消息数量: {len(messages)}")
    print(f"📊 去重后消息数量: {len(deduped)}")
    
    # 验证结果
    success = True
    
    # 检查是否保留了账号1的消息（即使时间较晚）
    msg1_kept = any(msg.id == "collector1:1001" for msg in deduped)
    msg2_kept = any(msg.id == "collector2:1002" for msg in deduped)
    
    if msg1_kept and not msg2_kept:
        print("✅ 测试通过：账号1的消息被保留（优先级更高）")
    else:
        print("❌ 测试失败：账号1的消息未被优先保留")
        success = False
    
    # 检查不同内容的消息都被保留
    msg3_kept = any(msg.id == "collector2:1003" for msg in deduped)
    msg4_kept = any(msg.id == "collector1:1004" for msg in deduped)
    
    if msg3_kept and msg4_kept:
        print("✅ 测试通过：不同内容的消息都被保留")
    else:
        print("❌ 测试失败：不同内容的消息未被正确保留")
        success = False
    
    # 显示去重后的消息
    print("\n📋 去重后消息列表:")
    for msg in deduped:
        account = msg.raw_metadata.get('collector_account', 'unknown')
        print(f"  - {msg.id} ({account}): {msg.content[:30]}...")
    
    return success

def test_list_collector1_script():
    """测试list_collector1_dialogs.py脚本"""
    print("\n🧪 测试list_collector1_dialogs.py脚本...")
    
    # 检查脚本是否存在
    import os
    script_path = "scripts/list_collector1_dialogs.py"
    
    if not os.path.exists(script_path):
        print(f"❌ 脚本不存在: {script_path}")
        return False
    
    # 检查脚本内容
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查是否包含更新.env文件的函数
    if "update_env_file" in content:
        print("✅ 脚本包含update_env_file函数")
    else:
        print("❌ 脚本缺少update_env_file函数")
        return False
    
    # 检查是否包含fix_id_format函数
    if "fix_id_format" in content:
        print("✅ 脚本包含fix_id_format函数")
    else:
        print("❌ 脚本缺少fix_id_format函数")
        return False
    
    # 检查主函数逻辑
    if "update_env_file(monitored_chats)" in content:
        print("✅ 脚本直接更新.env文件")
    else:
        print("❌ 脚本未直接更新.env文件")
        return False
    
    return True

def main():
    """主测试函数"""
    print("🚀 开始测试采集账号逻辑...")
    
    all_passed = True
    
    # 测试1：去重优先级逻辑
    if test_deduplication_priority():
        print("✅ 去重优先级测试通过")
    else:
        print("❌ 去重优先级测试失败")
        all_passed = False
    
    # 测试2：list_collector1脚本
    if test_list_collector1_script():
        print("✅ list_collector1脚本测试通过")
    else:
        print("❌ list_collector1脚本测试失败")
        all_passed = False
    
    # 总结
    print("\n" + "="*50)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查代码")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)