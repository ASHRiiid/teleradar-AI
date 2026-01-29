#!/usr/bin/env python3
"""
简化版Gemini API集成测试
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """测试基本导入"""
    print("=" * 60)
    print("测试基本导入")
    print("=" * 60)
    
    try:
        from src.config import config
        print("✅ src.config 导入成功")
        
        from src.processors.summarizer import AISummarizer
        print("✅ AISummarizer 导入成功")
        
        from src.models import UnifiedMessage, Platform
        print("✅ 模型导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_config():
    """测试配置"""
    print("\n" + "=" * 60)
    print("测试配置")
    print("=" * 60)
    
    try:
        from src.config import config
        
        print(f"使用Gemini: {config.ai_config.use_gemini}")
        print(f"Gemini模型: {config.ai_config.gemini_model}")
        print(f"Gemini API密钥: {'已设置' if config.ai_config.gemini_api_key else '未设置'}")
        
        if config.ai_config.gemini_api_key == "your-gemini-api-key-here":
            print("⚠️ 警告: 使用的是示例API密钥，请替换为实际密钥")
        
        return True
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_summarizer_init():
    """测试摘要器初始化"""
    print("\n" + "=" * 60)
    print("测试摘要器初始化")
    print("=" * 60)
    
    try:
        from src.processors.summarizer import AISummarizer
        
        summarizer = AISummarizer()
        print(f"✅ 摘要器初始化成功")
        print(f"使用Gemini: {summarizer.use_gemini}")
        
        if summarizer.use_gemini:
            print("✅ Gemini客户端初始化成功")
        else:
            print("⚠️ 未使用Gemini，将使用DeepSeek")
            
        return True
    except Exception as e:
        print(f"❌ 摘要器初始化失败: {e}")
        return False

def test_dependencies():
    """测试依赖包"""
    print("\n" + "=" * 60)
    print("测试依赖包")
    print("=" * 60)
    
    dependencies = [
        ("google.generativeai", "google-generativeai"),
        ("openai", "openai"),
        ("tiktoken", "tiktoken"),
        ("loguru", "loguru"),
        ("pydantic", "pydantic"),
    ]
    
    all_ok = True
    for module_name, package_name in dependencies:
        try:
            module = __import__(module_name)
            print(f"✅ {package_name}: 已安装")
        except ImportError as e:
            print(f"❌ {package_name}: 未安装 ({e})")
            all_ok = False
    
    return all_ok

def main():
    """主测试函数"""
    print("开始测试Gemini集成系统")
    print("=" * 60)
    
    # 检查.env文件
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"✅ 找到.env文件: {env_file}")
    else:
        print(f"❌ 未找到.env文件")
        return
    
    # 运行测试
    tests = [
        ("依赖包测试", test_dependencies),
        ("基本导入测试", test_basic_imports),
        ("配置测试", test_config),
        ("摘要器初始化", test_summarizer_init),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n运行测试: {test_name}")
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ 测试 '{test_name}' 异常: {e}")
            results.append((test_name, False))
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统已准备好使用。")
        print("\n下一步:")
        print("1. 将.env文件中的GEMINI_API_KEY替换为实际的API密钥")
        print("2. 运行 process_24h_report.py 进行完整测试")
        print("3. 监控系统日志，确保没有错误发生")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查上述问题。")
        
    # 提供具体建议
    print("\n" + "=" * 60)
    print("具体建议")
    print("=" * 60)
    
    if not env_file.exists():
        print("1. 创建.env文件并添加必要的配置")
    
    # 检查Gemini API密钥
    try:
        from src.config import config
        if config.ai_config.gemini_api_key == "your-gemini-api-key-here":
            print("2. 将.env文件中的GEMINI_API_KEY替换为实际的API密钥")
    except:
        pass
    
    print("3. 确保所有依赖包已正确安装: pip install -r requirements.txt")
    print("4. 如果遇到protobuf版本冲突，尝试: pip install protobuf==3.*")

if __name__ == "__main__":
    main()