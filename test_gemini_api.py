#!/usr/bin/env python3
"""
测试Gemini API密钥有效性
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_gemini_api_key():
    """测试Gemini API密钥有效性"""
    print("=" * 60)
    print("测试Gemini API密钥有效性")
    print("=" * 60)
    
    try:
        # 导入配置
        from src.config import config
        
        api_key = config.ai_config.gemini_api_key
        model_name = config.ai_config.gemini_model
        
        print(f"API密钥: {api_key[:10]}...{api_key[-10:]}")
        print(f"模型名称: {model_name}")
        
        # 检查密钥格式
        if not api_key or api_key == "your-gemini-api-key-here":
            print("❌ API密钥未设置或为示例密钥")
            return False
            
        if not api_key.startswith("AIza"):
            print("❌ API密钥格式不正确，应以'AIza'开头")
            return False
            
        print("✅ API密钥格式正确")
        
        # 尝试导入google.generativeai
        try:
            import google.generativeai as genai
            
            # 配置Gemini
            genai.configure(api_key=api_key)
            print("✅ Gemini客户端配置成功")
            
            # 列出可用模型（测试连接）
            try:
                models = genai.list_models()
                available_models = [model.name for model in models]
                
                print(f"✅ 成功连接到Gemini API")
                print(f"可用模型数量: {len(available_models)}")
                
                # 检查目标模型是否可用
                target_model = f"models/{model_name}"
                if target_model in available_models:
                    print(f"✅ 目标模型 '{model_name}' 可用")
                else:
                    print(f"⚠️ 目标模型 '{model_name}' 不在可用模型列表中")
                    print(f"可用模型示例: {available_models[:5]}...")
                    
                return True
                
            except Exception as e:
                print(f"❌ 无法列出模型（可能权限问题）: {e}")
                print("尝试直接测试模型调用...")
                
                # 尝试简单的生成调用
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content("Hello")
                    print(f"✅ 模型调用成功: {response.text[:50]}...")
                    return True
                except Exception as e2:
                    print(f"❌ 模型调用失败: {e2}")
                    return False
                    
        except ImportError as e:
            print(f"❌ 无法导入google.generativeai: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        return False

def test_summarizer_with_gemini():
    """测试使用Gemini的摘要器"""
    print("\n" + "=" * 60)
    print("测试使用Gemini的摘要器")
    print("=" * 60)
    
    try:
        from src.processors.summarizer import AISummarizer
        
        summarizer = AISummarizer()
        
        print(f"使用Gemini: {summarizer.use_gemini}")
        print(f"Gemini模型: {summarizer.gemini_model}")
        
        if summarizer.use_gemini:
            print("✅ 摘要器配置为使用Gemini")
            
            # 测试简单的摘要生成
            test_content = "比特币今天上涨了5%，以太坊上涨了3%。加密货币市场整体表现良好。"
            
            try:
                # 注意：这里只是测试摘要器的初始化，不实际调用API
                print("✅ 摘要器初始化成功")
                print("提示: 实际摘要生成将在process_24h_report.py中测试")
                return True
            except Exception as e:
                print(f"❌ 摘要器测试失败: {e}")
                return False
        else:
            print("⚠️ 摘要器未配置为使用Gemini")
            return False
            
    except Exception as e:
        print(f"❌ 摘要器测试失败: {e}")
        return False

def check_system_readiness():
    """检查系统准备状态"""
    print("\n" + "=" * 60)
    print("检查系统准备状态")
    print("=" * 60)
    
    checks = []
    
    # 检查.env文件
    env_file = project_root / ".env"
    if env_file.exists():
        print("✅ .env文件存在")
        checks.append(True)
    else:
        print("❌ .env文件不存在")
        checks.append(False)
    
    # 检查依赖包
    dependencies = ["google.generativeai", "openai", "tiktoken", "loguru", "pydantic"]
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep} 已安装")
            checks.append(True)
        except ImportError:
            print(f"❌ {dep} 未安装")
            checks.append(False)
    
    # 检查配置文件
    try:
        from src.config import config
        print("✅ 配置文件可导入")
        checks.append(True)
    except Exception as e:
        print(f"❌ 配置文件导入失败: {e}")
        checks.append(False)
    
    return all(checks)

def main():
    """主测试函数"""
    print("Gemini API集成测试")
    print("=" * 60)
    
    # 运行测试
    tests = [
        ("系统准备状态", check_system_readiness),
        ("Gemini API密钥", test_gemini_api_key),
        ("摘要器配置", test_summarizer_with_gemini),
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
        print("\n🎉 所有测试通过！系统已完全准备好。")
        print("\n下一步:")
        print("1. 运行 process_24h_report.py 进行完整测试")
        print("2. 监控系统日志，确保没有错误发生")
        print("3. 检查生成的简报质量")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败")
        
        # 提供具体建议
        print("\n具体建议:")
        if not all(check_system_readiness()):
            print("1. 确保所有依赖包已安装: pip install -r requirements.txt")
        
        # 检查Gemini API密钥
        try:
            from src.config import config
            if not config.ai_config.gemini_api_key or config.ai_config.gemini_api_key == "your-gemini-api-api-key-here":
                print("2. 确保.env文件中的GEMINI_API_KEY已正确设置")
        except:
            pass

if __name__ == "__main__":
    main()