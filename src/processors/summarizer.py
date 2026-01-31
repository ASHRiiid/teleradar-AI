import json
import asyncio
from typing import List, Optional, Dict, Any
from loguru import logger

try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-genai 包未安装，Gemini功能将不可用")

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai 包未安装，DeepSeek功能将不可用")

from src.models import UnifiedMessage, ScrapedContent
from src.config import config


def _extract_text_from_response(response) -> str:
    """
    从Gemini响应中安全提取文本，处理非文本部分的情况

    Args:
        response: Gemini响应对象

    Returns:
        提取的文本字符串
    """
    # 方法1：尝试直接获取 text 属性
    try:
        text = response.text
        if isinstance(text, str) and text:
            return text
    except (AttributeError, TypeError):
        pass

    # 方法2：尝试从 candidates 中提取
    try:
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                parts = candidate.content.parts
                if parts:
                    # 收集所有文本类型的parts
                    text_parts = []
                    for part in parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                        elif hasattr(part, 'inline_data'):  # 跳过二进制数据
                            continue
                    if text_parts:
                        return '\n'.join(text_parts)
    except (IndexError, AttributeError, TypeError) as e:
        logger.debug(f"从candidates提取文本失败: {e}")

    # 方法3：尝试遍历所有属性找text
    try:
        for attr_name in ['text', 'Text', 'content', 'output']:
            if hasattr(response, attr_name):
                text = getattr(response, attr_name)
                if isinstance(text, str) and text:
                    return text
                # 如果是list，尝试提取
                if isinstance(text, list) and text:
                    for item in text:
                        if isinstance(item, str):
                            return item
    except Exception as e:
        logger.debug(f"遍历属性提取文本失败: {e}")

    # 兜底：返回空字符串，让上层处理
    logger.warning(f"无法从Gemini响应中提取文本，响应类型: {type(response)}")
    return ""


class AISummarizer:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化AI摘要器，支持Gemini和DeepSeek
        
        Args:
            api_key: 可选的API密钥（如果为None则使用配置中的密钥）
            base_url: 可选的base_url（仅用于DeepSeek）
        """
        self.ai_config = config.ai_config
        
        # 初始化Gemini客户端
        if GEMINI_AVAILABLE and self.ai_config.use_gemini:
            gemini_api_key = api_key or self.ai_config.gemini_api_key
            self.gemini_client = genai.Client(api_key=gemini_api_key)
            self.gemini_model_name = self.ai_config.gemini_model
            self.use_gemini = True
            logger.info(f"使用Gemini模型: {self.ai_config.gemini_model}")
        else:
            self.gemini_client = None
            self.gemini_model_name = None
            self.use_gemini = False
            if self.ai_config.use_gemini and not GEMINI_AVAILABLE:
                logger.warning("Gemini配置了但google-genai包未安装，将使用DeepSeek")
        
        # 初始化DeepSeek客户端（作为备选）
        if OPENAI_AVAILABLE and not self.use_gemini:
            deepseek_api_key = api_key or self.ai_config.deepseek_api_key
            deepseek_base_url = base_url or self.ai_config.openai_base_url
            self.deepseek_client = AsyncOpenAI(
                api_key=deepseek_api_key, 
                base_url=deepseek_base_url
            )
            logger.info("使用DeepSeek模型")
        else:
            self.deepseek_client = None
            if not self.use_gemini and not OPENAI_AVAILABLE:
                logger.error("没有可用的AI服务，请安装google-generativeai或openai包")
    
    async def summarize_message(self, message: UnifiedMessage, scraped_contents: List[ScrapedContent] = []) -> dict:
        """
        结合消息原文和爬取到的网页内容生成归纳
        返回格式: {"summary": str, "tags": List[str]}
        """
        context = f"Message: {message.content}\n\n"
        for i, sc in enumerate(scraped_contents):
            context += f"Link {i+1} ({sc.url}) Content Snippet:\n{sc.markdown[:2000]}\n\n"

        prompt = f"""
        你是一个专门负责整理 Telegram 群组信息的 AI 助手。请根据以下消息内容（以及可能的网页链接内容），提取核心信息并生成一份结构化的简报。

        要求：
        1. 摘要（summary）：简洁明了地说明这条信息在讲什么，核心价值在哪里。200字以内。
        2. 标签（tags）：给出 3-5 个关键词标签。

        输出格式必须为 JSON：
        {{
            "summary": "这里是摘要内容",
            "tags": ["标签1", "标签2", "标签3"]
        }}

        输入内容：
        {context}
        """
        
        try:
            if self.use_gemini and self.gemini_model:
                # 使用Gemini API
                response = await asyncio.to_thread(
                    self.gemini_model.generate_content,
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        response_mime_type="application/json"
                    )
                )
                content = response.text
            elif self.deepseek_client:
                # 使用DeepSeek API
                response = await self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={'type': 'json_object'},
                    temperature=0.3
                )
                content = response.choices[0].message.content
            else:
                raise RuntimeError("没有可用的AI服务")
            
            return json.loads(content)
        except Exception as e:
            logger.error(f"AI Summary failed: {e}")
            return {
                "summary": "AI 归纳失败。",
                "tags": ["error"]
            }
    
    async def generate_summary_with_prompt(self, prompt: str, system_prompt: Optional[str] = None,
                                          temperature: float = 0.3, json_format: bool = False,
                                          max_retries: int = 3, retry_delay: float = 2.0) -> str:
        """
        通用AI调用方法，支持Gemini和DeepSeek，支持重试机制

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            temperature: 温度参数
            json_format: 是否要求JSON格式输出
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）

        Returns:
            AI生成的文本
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                if self.use_gemini and self.gemini_client:
                    # 构建完整的提示词（Gemini不支持独立的system消息）
                    full_prompt = ""
                    if system_prompt:
                        full_prompt += f"System: {system_prompt}\n\n"
                    full_prompt += prompt

                    generation_config = {
                        "temperature": temperature,
                    }
                    if json_format:
                        generation_config["response_mime_type"] = "application/json"

                    response = await asyncio.to_thread(
                        self.gemini_client.models.generate_content,
                        model=self.gemini_model_name,
                        contents=full_prompt,
                        config=generation_config
                    )
                    # 安全的文本提取，处理非文本部分的情况
                    response_text = _extract_text_from_response(response)
                    if not isinstance(response_text, str):
                        raise ValueError(f"Gemini返回了非文本格式: {type(response_text)}")
                    return response_text
                elif self.deepseek_client:
                    # 使用DeepSeek API
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})

                    request_params = {
                        "model": "deepseek-chat",
                        "messages": messages,
                        "temperature": temperature
                    }
                    if json_format:
                        request_params["response_format"] = {'type': 'json_object'}

                    response = await self.deepseek_client.chat.completions.create(**request_params)
                    return response.choices[0].message.content
                else:
                    raise RuntimeError("没有可用的AI服务")
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"AI调用失败，{retry_delay}秒后重试 ({attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(retry_delay)
                continue

        logger.error(f"AI调用失败，已重试 {max_retries} 次: {last_error}")
        raise last_error
    
    async def generate_json_response(self, prompt: str, system_prompt: Optional[str] = None,
                                    temperature: float = 0.3, max_retries: int = 3) -> Dict[str, Any]:
        """
        生成JSON格式的AI响应

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            temperature: 温度参数
            max_retries: 最大重试次数

        Returns:
            解析后的JSON字典
        """
        response_text = None
        try:
            response_text = await self.generate_summary_with_prompt(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                json_format=True,
                max_retries=max_retries
            )

            # 清理和提取有效的JSON内容
            cleaned_text = self._extract_valid_json(response_text)
            logger.debug(f"清理后的JSON内容: {cleaned_text[:100]}...")

            # 解析JSON
            parsed = json.loads(cleaned_text)

            # 处理 AI 返回数组的情况 [{}, {}]，提取第一个对象
            if isinstance(parsed, list):
                if len(parsed) > 0 and isinstance(parsed[0], dict):
                    logger.warning(f"AI返回了JSON数组，已自动提取第一个元素")
                    parsed = parsed[0]
                else:
                    raise ValueError(f"AI返回了空数组或无效格式")

            # 确保返回的是字典对象
            if not isinstance(parsed, dict):
                logger.error(f"AI返回了无效JSON格式: {type(parsed)}, 内容: {response_text[:200]}")
                raise ValueError(f"AI返回了无效的JSON格式: 期望对象，得到 {type(parsed).__name__}")

            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 响应文本: {response_text[:300] if response_text else 'N/A'}")
            raise

    def _extract_valid_json(self, text: str) -> str:
        """
        从AI返回的文本中提取有效的JSON内容
        处理AI返回多个JSON对象、附带思考过程等特殊情况
        """
        if not text:
            return text

        text = text.strip()

        # 情况1：已经是有效的单一JSON对象
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # 情况2：查找第一个 { 和最后一个 }，提取JSON对象
        first_brace = text.find('{')
        last_brace = text.rfind('}')

        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                json.loads(candidate)
                logger.warning(f"从文本中提取到有效JSON，已清理多余内容")
                return candidate
            except json.JSONDecodeError:
                pass

        # 情况3：尝试查找 markdown 代码块格式
        import re
        # 匹配 ```json 或 ``` 包裹的JSON
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            candidate = code_block_match.group(1).strip()
            try:
                json.loads(candidate)
                logger.warning(f"从代码块中提取到有效JSON")
                return candidate
            except json.JSONDecodeError:
                pass

        # 兜底：返回原始文本，让后面的错误处理捕获
        logger.warning(f"无法清理JSON格式，返回原始文本")
        return text
        except Exception as e:
            logger.error(f"生成JSON响应失败: {e}")
            raise