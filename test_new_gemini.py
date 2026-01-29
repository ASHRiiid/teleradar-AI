#!/usr/bin/env python3
"""
测试新版Gemini SDK (google-genai) 和 gemini-3-flash-preview 模型
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_python_version():
    """测试Python版本"""
    print("=" * 60)
    print("测试Python版本")
    print("=" * 60)
    
    version = sys.version_info
    print(f"Python版本: {sys.version}")
    print(f"主版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 10:
        print("✅ Python版本符合要求 (>= 3.10)")
        return True
    else:
        print(f"❌ Python版本不符合要求，需要 >= 3.10，当前是 {version.major}.{version.minor}")
        return False

def test_new_sdk():
    """测试新版SDK"""
    print("\n" + "=" * 60)
    print("测试新版Gemini SDK (google-genai)")
    print("=" * 60)
    
    try:
        import google.genai as genai
        print(f"✅ google.genai 导入成功")
        
        # 检查版本
        try:
            print(f"✅ google-genai 版本: {genai.__version__}")
        except AttributeError:
            print("ℹ️  无法获取版本号")
        
        # 检查是否有Client类
        if hasattr(genai, 'Client'):
            print("✅ 找到 genai.Client 类 (新版SDK)")
            return True, genai
        else:
            print("❌ 未找到 genai.Client 类")
            return False, None
            
    except ImportError as e:
        print(f"❌ 无法导入 google.genai: {e}")
        print("\n安装命令:")
        print("  pip uninstall google-generativeai")
        print("  pip install google-genai")
        return False, None

def test_config():
    """测试配置"""
    print("\n" + "=" * 60)
    print("测试配置")
    print("=" * 60)
    
    try:
        from src.config import config
        
        print(f"使用Gemini: {config.ai_config.use_gemini}")
        print(f"Gemini模型: {config.ai_config.gemini_model}")
        print(f"Gemini API密钥: {config.ai_config.gemini_api_key[:10]}...{config.ai_config.gemini_api_key[-10:]}")
        
        if config.ai_config.gemini_model == "gemini-3-flash-preview":
            print("✅ 模型名称正确: gemini-3-flash-preview")
        else:
            print(f"⚠️ 模型名称不是 gemini-3-flash-preview: {config.ai_config.gemini_model}")
            
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_api_connection(genai_module):
    """测试API连接"""
    print("\n" + "=" * 60)
    print("测试Gemini API连接")
    print("=" * 60)
    
    try:
        from src.config import config
        
        # 创建客户端
        client = genai_module.Client(api_key=config.ai_config.gemini_api_key)
        print("✅ Gemini客户端创建成功")
        
        # 测试列出模型
        try:
            models = client.models.list()
            available_models = [model.name for model in models]
            
            print(f"✅ 成功连接到Gemini API")
            print(f"可用模型数量: {len(available_models)}")
            
            # 检查目标模型是否可用
            target_model = f"models/{config.ai_config.gemini_model}"
            if target_model in available_models:
                print(f"✅ 目标模型 '{config.ai_config.gemini_model}' 可用")
            else:
                print(f"❌ 目标模型 '{config.ai_config.gemini_model}' 不在可用模型列表中")
                print(f"可用模型示例:")
                for model in available_models[:10]:
                    print(f"  - {model}")
                    
            return True, available_models
            
        except Exception as e:
            print(f"❌ 无法列出模型: {e}")
            return False, []
            
    except Exception as e:
        print(f"❌ API连接测试失败: {e}")
        return False, []

def test_model_generation(genai_module):
    """测试模型生成"""
    print("\n" + "=" * 60)
    print("测试模型生成")
    print("=" * 60)
    
    try:
        from src.config import config
        
        # 创建客户端
        client = genai_module.Client(api_key=config.ai_config.gemini_api_key)
        
        # 测试生成内容
        test_prompt = "Hello, world! 请用中文回复。"
        
        print(f"测试提示: {test_prompt}")
        print("正在调用模型...")
        
        response = client.models.generate_content(
            model=config.ai_config.gemini_model,
            contents=test_prompt
        )
        
        print(f"✅ 模型调用成功")
        print(f"响应: {response.text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型生成测试失败: {e}")
        return False

def test_summarizer():
    """测试摘要器"""
    print("\n" + "=" * 60)
    print("测试摘要器")
    print("=" * 60)
    
    try:
        from src.processors.summarizer import AISummarizer
        
        summarizer = AISummarizer()
        
        print(f"使用Gemini: {summarizer.use_gemini}")
        print(f"Gemini模型: {summarizer.gemini_model_name}")
        
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
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("新版Gemini SDK集成测试")
    print("=" * 60)
    
    # 运行测试
    tests = [
        ("Python版本", test_python_version),
        ("新版SDK", lambda: test_new_sdk()[0]),
        ("配置测试", test_config),
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
    
    # 如果基础测试通过，继续测试API
    if all(success for _, success in results):
        print("\n基础测试通过，继续测试API连接...")
        
        # 获取genai模块
        sdk_ok, genai_module = test_new_sdk()
        if sdk_ok and genai_module:
            api_tests = [
                ("API连接", lambda: test_api_connection(genai_module)[0]),
                ("模型生成", lambda: test_model_generation(genai_module)),
                ("摘要器", test_summarizer),
            ]
            
            for test_name, test_func in api_tests:
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
        print("\n🎉 所有测试通过！新版Gemini SDK集成成功。")
        print("\n下一步:")
        print("1. 运行 process_24h_report.py 进行完整测试")
        print("2. 监控系统日志，确保没有错误发生")
        print("3. 检查生成的简报质量")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败")
        
        # 提供具体建议
        print("\n具体建议:")
        if not test_python_version():
            print("1. 升级Python到3.10或更高版本")
        
        sdk_ok, _ = test_new_sdk()
        if not sdk_ok:
            print("2. 安装新版SDK: pip install google-genai")
            
        if not test_config():
            print("3. 检查.env文件配置")

if __name__ == "__main__":
    main()