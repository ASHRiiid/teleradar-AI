"""
基础功能测试脚本
验证配置加载和基本连接
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_config_loading():
    """测试配置加载"""
    print("=== 配置加载测试 ===")
    
    # 检查关键配置
    required_configs = [
        ("TELEGRAM_COLLECTOR1_API_ID", "采集账号1 API ID"),
        ("TELEGRAM_COLLECTOR1_API_HASH", "采集账号1 API Hash"),
        ("TELEGRAM_COLLECTOR1_PHONE", "采集账号1 手机号"),
        ("MONITORED_CHATS", "监控群组"),
    ]
    
    all_ok = True
    for var_name, description in required_configs:
        value = os.getenv(var_name)
        if value and value != "your_" + var_name.lower().split('_')[-1]:
            print(f"✅ {description}: 已配置")
        else:
            print(f"❌ {description}: 未配置或为默认值")
            all_ok = False
    
    # 检查可选配置
    optional_configs = [
        ("TELEGRAM_MAIN_API_ID", "主账号 API ID"),
        ("TELEGRAM_MAIN_API_HASH", "主账号 API Hash"),
        ("TELEGRAM_MAIN_PHONE", "主账号 手机号"),
        ("TELEGRAM_CHANNEL_USERNAME", "频道用户名"),
        ("TELEGRAM_BOT_TOKEN", "Bot Token"),
        ("DEEPSEEK_API_KEY", "DeepSeek API Key"),
    ]
    
    print("\n=== 可选配置检查 ===")
    for var_name, description in optional_configs:
        value = os.getenv(var_name)
        if value and value != "your_" + var_name.lower().split('_')[-1]:
            print(f"✅ {description}: 已配置")
        else:
            print(f"⚠️ {description}: 未配置（可选）")
    
    return all_ok

def test_imports():
    """测试模块导入"""
    print("\n=== 模块导入测试 ===")
    
    try:
        from src.config import config
        print("✅ 配置模块导入成功")
        
        # 检查配置对象
        print(f"采集账号数量: {len(config.collector_accounts)}")
        if config.collector_accounts:
            acc = config.collector_accounts[0]
            print(f"第一个采集账号: {acc.account_id}")
            print(f"API ID: {acc.api_id}")
        
        print(f"监控群组: {config.collector_config.monitored_chats}")
        
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("开始基础功能测试...\n")
    
    # 测试配置加载
    config_ok = test_config_loading()
    
    if not config_ok:
        print("\n❌ 配置检查失败，请完善 .env 文件")
        print("需要填写的配置:")
        print("1. TELEGRAM_COLLECTOR1_API_ID - 从 https://my.telegram.org 获取")
        print("2. TELEGRAM_COLLECTOR1_API_HASH - 从 https://my.telegram.org 获取")
        print("3. TELEGRAM_COLLECTOR1_PHONE - 您的手机号（带国家代码，如 +86 13800138000）")
        print("4. MONITORED_CHATS - 监控的群组链接（如 https://t.me/sntp_emby_lite_v2）")
        return False
    
    # 测试模块导入
    import_ok = test_imports()
    
    if not import_ok:
        print("\n❌ 模块导入失败，请检查依赖安装")
        print("运行: pip install -r requirements.txt")
        return False
    
    print("\n✅ 基础功能测试通过！")
    print("\n下一步:")
    print("1. 运行 'python3 collect_raw_data.py' 进行首次数据采集")
    print("2. 如果采集成功，系统会自动保存消息到数据库")
    print("3. 然后可以运行数据分析脚本")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)