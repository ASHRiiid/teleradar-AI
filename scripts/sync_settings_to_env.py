import os
import re

def fix_id_format(identifier: str) -> str:
    """处理标识符，如果是 10 位纯正整数则添加 -100 前缀"""
    identifier = identifier.strip()
    # 仅当它是恰好 10 位数字的正整数时才添加 -100 (超级群组常见格式)
    if identifier.isdigit() and len(identifier) == 10:
        return f"-100{identifier}"
    return identifier

def extract_from_md(file_path: str) -> list:
    """从 MD 文件提取未注释的标识符"""
    monitored_chats = []
    if not os.path.exists(file_path):
        return []
        
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "|" in line:
                parts = line.split("|")
                identifier = parts[-1].strip()
                # 移除行尾的注释（如果有的话）
                if '#' in identifier:
                    identifier = identifier.split('#')[0].strip()
                monitored_chats.append(fix_id_format(identifier))
    return monitored_chats

def sync_md_to_env():
    c2_md = "setting_collector2.md"  # 账号2仍然使用md文件
    env_file = ".env"
    
    # 1. 从.env文件读取账号1的现有配置
    list1 = []
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(r"^#?\s*MONITORED_CHATS_COLLECTOR1\s*=\s*(.+)$", line)
                if match:
                    chats_str = match.group(1).strip()
                    if chats_str:
                        list1 = [fix_id_format(chat.strip()) for chat in chats_str.split(",")]
                    break
    
    # 2. 从md文件提取账号2的配置
    list2_raw = extract_from_md(c2_md)
    
    # 3. 优先级逻辑：如果账号 1 已经监控了，账号 2 就排除掉
    final_list1 = list1
    final_list2 = [chat for chat in list2_raw if chat not in list1]
    
    print(f"📊 账号 1 监控: {len(final_list1)} 个频道（从.env文件读取）")
    print(f"📊 账号 2 监控: {len(final_list2)} 个频道（从setting_collector2.md读取）")
    print(f"⚠️  注意：账号1的配置已由list_collector1_dialogs.py自动更新")
    print(f"👉 如需修改账号1配置，请运行：python3 scripts/list_collector1_dialogs.py")

    # 3. 更新 .env 文件 (逐行处理更安全)
    if not os.path.exists(env_file):
        print(f"❌ 找不到 .env 文件")
        return

    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    found_c1 = False
    found_c2 = False
    
    c1_str = ",".join(final_list1)
    c2_str = ",".join(final_list2)

    for line in lines:
        if re.match(r"^#?\s*MONITORED_CHATS_COLLECTOR1\s*=", line):
            new_lines.append(f"MONITORED_CHATS_COLLECTOR1={c1_str}\n")
            found_c1 = True
        elif re.match(r"^#?\s*MONITORED_CHATS_COLLECTOR2\s*=", line):
            new_lines.append(f"MONITORED_CHATS_COLLECTOR2={c2_str}\n")
            found_c2 = True
        else:
            new_lines.append(line)

    if not found_c1:
        new_lines.append(f"\nMONITORED_CHATS_COLLECTOR1={c1_str}\n")
    if not found_c2:
        new_lines.append(f"MONITORED_CHATS_COLLECTOR2={c2_str}\n")

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    
    print(f"🚀 .env 同步完成")

if __name__ == "__main__":
    sync_md_to_env()
