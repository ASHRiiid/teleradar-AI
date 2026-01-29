#!/usr/bin/env python3
"""
测试和修复Gemini API配置
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_current_config():
    """测试当前配置"""
    print("=" * 60)
    print("测试当前Gemini配置")
    print("=" * 60)
    
    try:
        # 导入配置
        from src.config import config
        
        print(f"Python版本: {sys.version}")
        print(f"使用Gemini: {config.ai_config.use_gemini}")
        print(f"Gemini模型: {config.ai_config.gemini_model}")
        print(f"Gemini API密钥: {config.ai_config.gemini_api_key[:10]}...{config.ai_config.gemini_api_key[-10:]}")
        
        # 测试导入google.generativeai
        try:
            import google.generativeai as genai
            print(f"✅ google.generativeai版本: {genai.__version__}")
            
            # 测试配置
            genai.configure(api_key=config.ai_config.gemini_api_key)
            print("✅ Gemini配置成功")
            
            # 测试列出可用模型
            try:
                models = genai.list_models()
                available_models = [model.name for model in models]
                
                print(f"✅ 成功连接到Gemini API")
                print(f"可用模型数量: {len(available_models)}")
                
                # 检查我们的模型是否在列表中
                target_model = f"models/{config.ai_config.gemini_model}"
                if target_model in available_models:
                    print(f"✅ 目标模型 '{config.ai_config.gemini_model}' 可用")
                else:
                    print(f"❌ 目标模型 '{config.ai_config.gemini_model}' 不在可用模型列表中")
                    print(f"可用模型示例:")
                    for model in available_models[:10]:
                        print(f"  - {model}")
                    
                    # 建议可用的模型
                    flash_models = [m for m in available_models if 'flash' in m.lower()]
                    if flash_models:
                        print(f"\n建议使用以下Flash模型:")
                        for model in flash_models[:5]:
                            model_name = model.replace('models/', '')
                            print(f"  - {model_name}")
                
                return True, available_models
                
            except Exception as e:
                print(f"❌ 无法列出模型: {e}")
                return False, []
                
        except ImportError as e:
            print(f"❌ 无法导入google.generativeai: {e}")
            return False, []
            
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False, []

def test_model_initialization():
    """测试模型初始化"""
    print("\n" + "=" * 60)
    print("测试模型初始化")
    print("=" * 60)
    
    try:
        from src.config import config
        import google.generativeai as genai
        
        # 配置API密钥
        genai.configure(api_key=config.ai_config.gemini_api_key)
        
        # 尝试初始化模型
        try:
            model = genai.GenerativeModel(config.ai_config.gemini_model)
            print(f"✅ 模型初始化成功: {config.ai_config.gemini_model}")
            
            # 测试简单的生成
            try:
                response = model.generate_content("Hello, world!")
                print(f"✅ 模型调用成功: {response.text[:50]}...")
                return True
            except Exception as e:
                print(f"❌ 模型调用失败: {e}")
                return False
                
        except Exception as e:
            print(f"❌ 模型初始化失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def check_sdk_version():
    """检查SDK版本"""
    print("\n" + "=" * 60)
    print("检查SDK版本")
    print("=" * 60)
    
    try:
        import google.generativeai as genai
        print(f"当前SDK版本: {genai.__version__}")
        
        # 检查是否为旧版SDK
        if hasattr(genai, 'GenerativeModel'):
            print("✅ 使用的是旧版SDK (google-generativeai)")
            print("注意: 旧版SDK已标记为Legacy，建议迁移到google-genai")
            return "legacy"
        else:
            print("❓ 无法确定SDK版本")
            return "unknown"
            
    except ImportError:
        print("❌ google.generativeai未安装")
        return "not_installed"

def suggest_fixes(available_models):
    """提供修复建议"""
    print("\n" + "=" * 60)
    print("修复建议")
    print("=" * 60)
    
    # 检查当前模型
    from src.config import config
    current_model = config.ai_config.gemini_model
    
    print(f"当前配置的模型: {current_model}")
    
    # 查找可用的Flash模型
    flash_models = []
    if available_models:
        flash_models = [m.replace('models/', '') for m in available_models if 'flash' in m.lower()]
    
    if flash_models:
        print(f"\n可用的Flash模型:")
        for model in flash_models[:10]:
            print(f"  - {model}")
        
        # 建议最佳模型
        if 'gemini-1.5-flash' in flash_models:
            print(f"\n✅ 建议使用: gemini-1.5-flash")
        elif 'gemini-2.0-flash-exp' in flash_models:
            print(f"\n✅ 建议使用: gemini-2.0-flash-exp (实验版)")
        elif 'gemini-3-flash-preview' in flash_models:
            print(f"\n✅ 建议使用: gemini-3-flash-preview (预览版)")
        else:
            print(f"\n✅ 建议使用: {flash_models[0]}")
    else:
        print("❌ 未找到可用的Flash模型")
        
        # 检查是否有其他模型
        if available_models:
            other_models = [m.replace('models/', '') for m in available_models[:10]]
            print(f"\n其他可用模型:")
            for model in other_models:
                print(f"  - {model}")

def main():
    """主测试函数"""
    print("Gemini API配置诊断")
    print("=" * 60)
    
    # 运行测试
    print("\n1. 测试当前配置...")
    config_ok, available_models = test_current_config()
    
    print("\n2. 检查SDK版本...")
    sdk_version = check_sdk_version()
    
    print("\n3. 测试模型初始化...")
    init_ok = test_model_initialization()
    
    # 提供修复建议
    suggest_fixes(available_models)
    
    # 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    if config_ok and init_ok:
        print("✅ 当前配置工作正常")
        print("\n下一步:")
        print("1. 运行 process_24h_report.py 进行完整测试")
        print("2. 监控系统日志，确保没有错误发生")
    else:
        print("❌ 配置存在问题")
        print("\n建议操作:")
        print("1. 更新.env文件中的模型名称")
        print("2. 确保API密钥有效")
        print("3. 检查网络连接")
        
        if sdk_version == "legacy":
            print("\n注意: 你使用的是旧版SDK，建议:")
            print("  1. 升级到Python 3.10+")
            print("  2. 安装新SDK: pip install google-genai")
            print("  3. 更新代码使用新API")

if __name__ == "__main__":
    main()