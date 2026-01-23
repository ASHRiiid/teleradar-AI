import os
import re

import os
import re

def fix_id_format(identifier: str) -> str:
    """处理标识符，如果是纯数字则添加 -100 前缀"""
    identifier = identifier.strip()
    if identifier.isdigit() and not identifier.startswith("-"):
        if len(identifier) >= 8:
            return f"-100{identifier}"
    return identifier

def sync_md_to_env():
    md_file = "setting_collector2.md"
    env_file = ".env"
    
    if not os.path.exists(md_file):
        print(f"❌ 找不到文件: {md_file}")
        return

    # 1. 从 MD 提取未注释的标识符
    monitored_chats = []
    with open(md_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "|" in line:
                parts = line.split("|")
                identifier = parts[-1].strip()
                monitored_chats.append(fix_id_format(identifier))

    chats_str = ",".join(monitored_chats)
    print(f"✅ 从 MD 提取到 {len(monitored_chats)} 个监控频道")

    # 2. 读取现有的 .env
    if not os.path.exists(env_file):
        print(f"❌ 找不到 .env 文件")
        return

    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 使用正则替换，确保即使被注释掉也能正确替换并启用
    # 替换 COLLECTOR 2
    pattern2 = r"#?\s*MONITORED_CHATS_COLLECTOR2\s*=.*"
    if re.search(pattern2, content):
        content = re.sub(pattern2, f"MONITORED_CHATS_COLLECTOR2={chats_str}", content)
    else:
        content += f"\nMONITORED_CHATS_COLLECTOR2={chats_str}\n"

    # 修复 COLLECTOR 1
    def replace_collector1(match):
        old_val = match.group(2)
        fixed = ",".join([fix_id_format(c) for c in old_val.split(",") if c.strip()])
        return f"MONITORED_CHATS_COLLECTOR1={fixed}"

    pattern1 = r"(#?\s*MONITORED_CHATS_COLLECTOR1\s*=\s*)(.*)"
    content = re.sub(pattern1, replace_collector1, content)

    with open(env_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"🚀 .env 已更新并修复了所有数字 ID 的格式")

if __name__ == "__main__":
    sync_md_to_env()

if __name__ == "__main__":
    sync_md_to_env()
