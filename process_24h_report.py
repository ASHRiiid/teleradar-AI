import asyncio
import os
import sys
import logging
import re
import json
from datetime import datetime, timedelta

# Ensure we can import from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.config import config
from src.processors.summarizer import AISummarizer
from src.adapters.telegram_adapter_v2 import TelegramMultiAccountAdapter
from src.models import UnifiedMessage, Platform

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def estimate_token_count(text):
    """粗略估计文本的token数量（英文单词数 + 中文字符数 * 2）"""
    # 简单估算：英文单词数 + 中文字符数 * 2
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 其他字符（标点、数字等）按0.5倍计算
    other_chars = len(text) - english_words - chinese_chars
    return english_words + chinese_chars * 2 + int(other_chars * 0.5)

def chunk_messages_by_tokens(message_list, max_tokens_per_chunk=100000):
    """
    将消息列表按token数分块，确保每块不超过限制
    返回分块列表，每块包含消息和起始ID
    """
    if not message_list:
        return []
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    current_start_id = 0
    
    for idx, msg in enumerate(message_list):
        # 优化消息格式：只保留ID，去掉用户名
        message_text = f"[ID:{idx}] {msg.content}"
        message_tokens = estimate_token_count(message_text)
        
        # 如果当前块为空或添加这条消息不会超过限制，就添加到当前块
        if not current_chunk or current_tokens + message_tokens <= max_tokens_per_chunk:
            current_chunk.append((idx, msg))
            current_tokens += message_tokens
        else:
            # 当前块已满，保存并开始新块
            chunks.append({
                'start_id': current_start_id,
                'messages': current_chunk.copy(),
                'estimated_tokens': current_tokens
            })
            current_chunk = [(idx, msg)]
            current_tokens = message_tokens
            current_start_id = idx
    
    # 添加最后一个块
    if current_chunk:
        chunks.append({
            'start_id': current_start_id,
            'messages': current_chunk,
            'estimated_tokens': current_tokens
        })
    
    logger.info(f"消息分块完成：共 {len(message_list)} 条消息，分成 {len(chunks)} 个块")
    for i, chunk in enumerate(chunks):
        logger.info(f"  块 {i+1}: {len(chunk['messages'])} 条消息，估计 {chunk['estimated_tokens']} tokens")
    
    return chunks

async def generate_chunk_summary(summarizer, chunk_data, chunk_index, total_chunks, start_time, end_time):
    """生成单个分块的摘要"""
    # 读取 setting_AI.md
    try:
        with open("setting_AI.md", "r", encoding="utf-8") as f:
            setting_ai_content = f.read()
    except Exception as e:
        logger.error(f"读取 setting_AI.md 失败: {e}")
        setting_ai_content = "无法读取 setting_AI.md，请检查文件是否存在。"

    # 格式化时间范围
    time_range_str = f"{start_time.strftime('%m%d %H:%M')} - {end_time.strftime('%m%d %H:%M')}"

    # 准备分块消息文本
    messages_with_ids = []
    for original_id, msg in chunk_data['messages']:
        # 使用相对ID，从0开始
        relative_id = original_id - chunk_data['start_id']
        messages_with_ids.append(f"[ID:{relative_id}] {msg.content}")
    
    messages_text = "\n".join(messages_with_ids)
    
    prompt = f"""
    你是一个专业的区块链投研助手。请根据以下从多个 Telegram 群组采集到的碎片化信息，整理出这部分信息的摘要。

    这是第 {chunk_index + 1}/{total_chunks} 个分块。

    请严格遵循以下设定（setting_AI.md）：
    {setting_ai_content}

    当前简报的时间范围是：{time_range_str}

    采集到的原始信息如下（每条消息都有ID标记）：
    {messages_text}

    请返回一个JSON对象，格式如下：
    {{
      "summary": "这部分信息的摘要内容，重点关注：1) 主要讨论主题 2) 重要趋势 3) 风险提示 4) 投资机会",
      "basic_question_ids": [0, 1, 2, ...]  // 基础操作问题的ID列表（相对ID），如果没有则为空数组[]
    }}
    """
    
    try:
        # 使用新的summarizer接口
        result = await summarizer.generate_json_response(
            prompt=prompt,
            system_prompt="你是一个专业的区块链投研助手，严格按照给定的整理逻辑生成分块摘要，并返回JSON格式的结果。",
            temperature=0.3
        )
        
        # 将相对ID转换回原始ID
        if result.get("basic_question_ids"):
            original_ids = []
            for relative_id in result["basic_question_ids"]:
                original_id = chunk_data['start_id'] + relative_id
                original_ids.append(original_id)
            result["basic_question_ids"] = original_ids
        
        return result
    except Exception as e:
        logger.error(f"分块 {chunk_index + 1} AI 生成摘要失败: {e}")
        return {"summary": f"分块 {chunk_index + 1} AI 摘要生成失败: {e}", "basic_question_ids": []}

async def generate_global_summary(summarizer, aggregated_text, message_list, start_time, end_time):
    """调用 AI 生成全局摘要，使用分块处理策略"""
    # 读取 setting_AI.md
    try:
        with open("setting_AI.md", "r", encoding="utf-8") as f:
            setting_ai_content = f.read()
    except Exception as e:
        logger.error(f"读取 setting_AI.md 失败: {e}")
        setting_ai_content = "无法读取 setting_AI.md，请检查文件是否存在。"

    # 格式化时间范围
    time_range_str = f"{start_time.strftime('%m%d %H:%M')} - {end_time.strftime('%m%d %H:%M')}"

    if not message_list:
        logger.warning("没有可用的消息进行摘要生成")
        return {"summary": f"📊 {time_range_str}\n\n⚠️ 没有足够的信息生成简报", "basic_question_ids": []}

    logger.info(f"开始处理 {len(message_list)} 条消息的摘要生成")
    
    # 1. 将消息分块
    chunks = chunk_messages_by_tokens(message_list, max_tokens_per_chunk=100000)
    
    if not chunks:
        logger.warning("消息分块失败")
        return {"summary": f"📊 {time_range_str}\n\n⚠️ 消息处理失败", "basic_question_ids": []}
    
    # 2. 并行生成分块摘要
    chunk_summaries = []
    all_basic_question_ids = []
    
    for chunk_index, chunk_data in enumerate(chunks):
        logger.info(f"处理分块 {chunk_index + 1}/{len(chunks)}")
        chunk_result = await generate_chunk_summary(
            summarizer, chunk_data, chunk_index, len(chunks), start_time, end_time
        )
        chunk_summaries.append(chunk_result)
        
        # 收集基础操作问题ID
        if chunk_result.get("basic_question_ids"):
            all_basic_question_ids.extend(chunk_result["basic_question_ids"])
    
    # 3. 聚合所有分块摘要
    if len(chunks) == 1:
        # 如果只有一个分块，直接使用其摘要
        final_summary = chunk_summaries[0]["summary"]
    else:
        # 如果有多个分块，需要聚合
        final_summary = await aggregate_chunk_summaries(
            summarizer, chunk_summaries, start_time, end_time, setting_ai_content
        )
    
    # 4. 确保摘要格式正确
    if not final_summary.startswith("📊"):
        final_summary = f"📊 {time_range_str}\n\n{final_summary}"
    
    return {
        "summary": final_summary,
        "basic_question_ids": all_basic_question_ids
    }

async def aggregate_chunk_summaries(summarizer, chunk_summaries, start_time, end_time, setting_ai_content):
    """聚合多个分块摘要为全局摘要"""
    # 格式化时间范围
    time_range_str = f"{start_time.strftime('%m%d %H:%M')} - {end_time.strftime('%m%d %H:%M')}"
    
    # 准备所有分块摘要
    chunk_summary_texts = []
    for i, chunk_result in enumerate(chunk_summaries):
        chunk_summary_texts.append(f"=== 分块 {i+1} 摘要 ===\n{chunk_result['summary']}")
    
    all_chunk_summaries = "\n\n".join(chunk_summary_texts)
    
    prompt = f"""
    你是一个专业的区块链投研助手。请根据以下多个分块的摘要，整理出一份完整的深度简报。

    请严格遵循以下设定（setting_AI.md）：
    {setting_ai_content}

    当前简报的时间范围是：{time_range_str}
    请确保简报开头严格按照设定中的格式：📊 {time_range_str}

    以下是 {len(chunk_summaries)} 个分块的摘要：
    {all_chunk_summaries}

    请生成一份完整的全局简报，要求：
    1. 整合所有分块的关键信息
    2. 识别整体趋势和模式
    3. 突出最重要的投资机会和风险
    4. 保持setting_AI.md中要求的格式和结构
    5. 避免重复信息，进行去重和整合

    请直接返回完整的简报内容（不需要JSON格式）。
    """
    
    try:
        # 使用新的summarizer接口
        final_summary = await summarizer.generate_summary_with_prompt(
            prompt=prompt,
            system_prompt="你是一个专业的区块链投研助手，擅长整合多个分块摘要，生成完整、连贯的全局简报。",
            temperature=0.3,
            json_format=False
        )
        
        # 确保格式正确
        if not final_summary.startswith("📊"):
            final_summary = f"📊 {time_range_str}\n\n{final_summary}"
        
        logger.info(f"全局摘要聚合完成，长度：{len(final_summary)} 字符")
        return final_summary
    except Exception as e:
        logger.error(f"全局摘要聚合失败: {e}")
        # 如果聚合失败，回退到拼接所有分块摘要
        fallback_summary = f"📊 {time_range_str}\n\n"
        for i, chunk_result in enumerate(chunk_summaries):
            fallback_summary += f"\n=== 分块 {i+1} ===\n{chunk_result['summary']}\n"
        return fallback_summary

def get_last_launch_time():
    """从简报文件名中获取上次启动时间"""
    vault_path = config.obsidian_vault_path
    if not vault_path or not os.path.exists(vault_path):
        return None
    
    # 查找所有简报文件
    pattern = re.compile(r'简报_(\d{10})_-(\d{10})(?:_\d+)?\.md')
    last_time = None
    
    for filename in os.listdir(vault_path):
        match = pattern.match(filename)
        if match:
            end_time_str = match.group(2)  # 文件名中的结束时间
            try:
                # 解析时间：YYMMDDHHMM
                end_time = datetime.strptime(end_time_str, "%y%m%d%H%M")
                if last_time is None or end_time > last_time:
                    last_time = end_time
            except ValueError:
                continue
    
    return last_time

def generate_filename(start_time, end_time, index=None):
    """生成简报文件名"""
    start_str = start_time.strftime("%y%m%d%H%M")
    end_str = end_time.strftime("%y%m%d%H%M")
    
    if index is None:
        return f"简报_{start_str}_-{end_str}.md"
    else:
        return f"简报_{start_str}_-{end_str}_{index}.md"

def is_basic_operation_question(content):
    """判断是否为基础操作问题"""
    basic_keywords = [
        # 交易所相关
        '下载交易所', '交易所app', '交易所下载', '交易所安装',
        '币安下载', 'okx下载', '火币下载', 'gate下载',
        '币安app', 'okx app', '火币app',
        # Telegram相关
        'telegram中文', 'tg中文', 'telegram设置中文', 'tg设置中文',
        'telegram语言', 'tg语言', 'telegram怎么', 'tg怎么',
        # Uniswap相关
        '下载uniswap', 'uniswap app', 'uniswap下载', 'uniswap安装',
        'uniswap怎么',
        # 通用操作
        '怎么下载', '如何下载', '怎么安装', '如何安装',
        '怎么用', '如何使用', '怎么操作', '如何操作',
        '新手教程', '入门教程', '基础教程', '教程',
        # 钱包相关
        '下载钱包', '钱包app', '钱包下载', '钱包安装',
        'metamask下载', '小狐狸下载', 'tp钱包下载',
        '钱包怎么',
    ]
    
    content_lower = content.lower()
    for keyword in basic_keywords:
        if keyword in content_lower:
            return True
    return False

def count_basic_operation_questions(messages):
    """统计基础操作问题的数量"""
    count = 0
    for msg in messages:
        if is_basic_operation_question(msg.content):
            count += 1
    return count

def filter_basic_operation_questions(messages):
    """过滤掉基础操作问题"""
    filtered_messages = []
    for msg in messages:
        if not is_basic_operation_question(msg.content):
            filtered_messages.append(msg)
    return filtered_messages

def save_report_stats(start_time, end_time, basic_op_count, filename):
    """保存简报统计数据"""
    stats_dir = "data/report_stats"
    if not os.path.exists(stats_dir):
        os.makedirs(stats_dir)
    
    stats_file = os.path.join(stats_dir, "report_stats.json")
    
    # 计算统计小时数
    hours = (end_time - start_time).total_seconds() / 3600
    
    # 创建统计记录
    stats_record = {
        "filename": filename,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "hours": round(hours, 2),
        "basic_operation_count": basic_op_count,
        "basic_operation_density": round(basic_op_count / hours, 4) if hours > 0 else 0,
        "created_at": datetime.now().isoformat()
    }
    
    # 读取现有统计数据
    all_stats = []
    if os.path.exists(stats_file):
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                all_stats = json.load(f)
        except:
            all_stats = []
    
    # 添加新记录
    all_stats.append(stats_record)
    
    # 只保留最近100条记录
    if len(all_stats) > 100:
        all_stats = all_stats[-100:]
    
    # 保存到文件
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    
    return stats_record

def save_training_data(messages, basic_question_ids):
    """保存训练数据到CSV文件，用于机器学习模型训练"""
    import csv
    from datetime import datetime
    
    # 创建训练数据目录
    training_dir = "data/training_data"
    os.makedirs(training_dir, exist_ok=True)
    
    # 训练数据文件
    training_file = os.path.join(training_dir, "basic_questions_training.csv")
    
    # 检查文件是否存在，如果不存在则创建并写入表头
    file_exists = os.path.exists(training_file)
    
    with open(training_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # 如果文件不存在，写入表头
        if not file_exists:
            writer.writerow(['message_id', 'message_text', 'is_basic_question', 'timestamp'])
        
        # 保存所有消息的训练数据
        for idx, msg in enumerate(messages):
            is_basic = 1 if idx in basic_question_ids else 0
            writer.writerow([
                f"{datetime.now().strftime('%Y%m%d')}_{idx}",
                msg.content[:500],  # 限制长度，避免CSV问题
                is_basic,
                datetime.now().isoformat()
            ])
    
    logger.info(f"已保存 {len(messages)} 条训练数据到 {training_file}")

def get_previous_report_stats():
    """获取上次简报的统计数据"""
    stats_file = "data/report_stats/report_stats.json"
    if not os.path.exists(stats_file):
        return None
    
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            all_stats = json.load(f)
        
        if not all_stats:
            return None
        
        # 返回最近的一条记录（排除当前正在处理的）
        return all_stats[-1]
    except:
        return None

def calculate_basic_op_density_change(current_stats, previous_stats):
    """计算基础操作问题密度变化"""
    if previous_stats is None:
        # 第一次简报，上次密度为0
        previous_density = 0
    else:
        previous_density = previous_stats.get("basic_operation_density", 0)
    
    current_density = current_stats.get("basic_operation_density", 0)
    
    # 计算变化：当前密度 - 上次密度
    density_change = current_density - previous_density
    
    # 返回格式化后的结果（保留两位小数）
    return f"{density_change:+.2f}" if density_change >= 0 else f"{density_change:.2f}"

def create_empty_report_file(start_time, end_time, index=None):
    """创建空简报文件（用于提前占位）"""
    filename = generate_filename(start_time, end_time, index)
    vault_path = config.obsidian_vault_path
    if not vault_path:
        logger.warning("未配置 OBSIDIAN_VAULT_PATH，跳过创建空文件")
        return None

    if not os.path.exists(vault_path):
        os.makedirs(vault_path)

    file_path = os.path.join(vault_path, filename)
    empty_content = f"""# 📊 {start_time.strftime('%m%d %H:%M')} - {end_time.strftime('%m%d %H:%M')}

> 简报生成中，请稍候...

*创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(empty_content)
    logger.info(f"已创建空简报文件: {file_path}")
    return file_path

def update_report_file(file_path, content, filename=None):
    """更新简报文件内容"""
    if file_path and os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"已更新简报文件: {file_path}")

    # 同时保存到 Obsidian
    if filename:
        vault_path = config.obsidian_vault_path
        if not vault_path:
            logger.warning("未配置 OBSIDIAN_VAULT_PATH，跳过保存")
            return
        if not os.path.exists(vault_path):
            os.makedirs(vault_path)

        obsidian_path = os.path.join(vault_path, filename)
        with open(obsidian_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"报告已保存到 Obsidian: {obsidian_path}")

async def main():
    logger.info("开始生成深度简报...")
    
    # 调试：检查配置是否正确加载
    for acc in config.collector_accounts:
        logger.info(f"账号 {acc.account_id} 监控群组数量: {len(acc.monitored_chats) if acc.monitored_chats else 0}")
    
    # 获取当前时间
    current_time = datetime.now()
    logger.info(f"当前时间: {current_time}")
    
    # 获取上次启动时间
    last_launch_time = get_last_launch_time()
    
    # 确定时间窗口
    if last_launch_time is None:
        # 第一次启动：统计前24小时
        logger.info("第一次启动，统计前24小时内容")
        end_time = current_time
        start_time = current_time - timedelta(hours=24)
        time_windows = [(start_time, end_time)]
    else:
        # 计算时间间隔（小时）
        time_diff = (current_time - last_launch_time).total_seconds() / 3600
        logger.info(f"距离上次启动时间: {time_diff:.2f} 小时")
        
        if time_diff <= 48:
            # 情况1：间隔 ≤ 48小时
            logger.info("时间间隔 ≤ 48小时，生成1份简报")
            start_time = last_launch_time
            end_time = current_time
            time_windows = [(start_time, end_time)]
        elif time_diff <= 120:
            # 情况2：间隔 > 48小时 且 ≤ 120小时
            logger.info("时间间隔 48-120小时，生成2份简报")
            split_time = current_time - timedelta(hours=48)
            time_windows = [
                (last_launch_time, split_time),  # 第一份：上次启动时间 → 48小时前
                (split_time, current_time)       # 第二份：48小时前 → 当前时间
            ]
        else:
            # 情况3：间隔 > 120小时
            logger.info("时间间隔 > 120小时，生成1份简报（最近48小时）")
            start_time = current_time - timedelta(hours=48)
            end_time = current_time
            time_windows = [(start_time, end_time)]
    
    # 记录时间窗口
    for i, (start, end) in enumerate(time_windows):
        logger.info(f"时间窗口 {i+1}: {start} 至 {end}")

    # 先创建空简报文件（提前占位）
    created_files = []
    for i, (start, end) in enumerate(time_windows):
        empty_file = create_empty_report_file(start, end, i+1 if len(time_windows) > 1 else None)
        if empty_file:
            created_files.append((i, empty_file))

    # 初始化 AI 总结器
    summarizer = AISummarizer(
        api_key=config.ai_config.deepseek_api_key, 
        base_url=config.ai_config.openai_base_url
    )
    
    async with TelegramMultiAccountAdapter() as adapter:
        # 处理每个时间窗口
        for i, (start_time, end_time) in enumerate(time_windows):
            logger.info(f"正在处理时间窗口 {i+1}/{len(time_windows)}: {start_time} 至 {end_time}")
            
            logger.info("正在并发采集消息...")
            
            # limit_per_chat 根据时间间隔调整
            hours_diff = (end_time - start_time).total_seconds() / 3600
            limit_per_chat = min(300, int(hours_diff * 12.5))  # 大约每小时12.5条
            
            unified_messages = await adapter.fetch_messages_concurrently(
                start_time=start_time,
                end_time=end_time,
                limit_per_chat=limit_per_chat
            )
            
            if not unified_messages:
                logger.info(f"时间窗口 {i+1} 内没有抓取到新消息")
                continue

            # 统计基础操作问题数量
            basic_op_count = count_basic_operation_questions(unified_messages)
            logger.info(f"检测到基础操作问题数量: {basic_op_count}")
            
            # 过滤掉基础操作问题
            filtered_messages = filter_basic_operation_questions(unified_messages)
            logger.info(f"过滤后剩余消息数量: {len(filtered_messages)}")

            chat_contents = {}
            for msg in filtered_messages:
                chat_name = msg.chat_name or msg.chat_id
                if chat_name not in chat_contents:
                    chat_contents[chat_name] = []
                chat_contents[chat_name].append(msg.content)
                
            aggregated_input = ""
            total_messages_count = 0

            for chat_name, contents in chat_contents.items():
                # 不再限制每个群组的消息数量，使用所有消息
                chat_slice = contents  # 使用所有消息
                aggregated_input += f"### Group: {chat_name}\n" + "\n".join(chat_slice) + "\n\n"
                total_messages_count += len(chat_slice)
            
            logger.info(f"成功抓取 {len(unified_messages)} 条去重后的消息，过滤后剩余 {len(filtered_messages)} 条，将处理所有 {total_messages_count} 条消息")
            
            logger.info("正在调用 AI 生成深度简报...")
            # 传递完整的消息列表给AI，让AI识别基础操作问题
            summary_result = await generate_global_summary(summarizer, aggregated_input, unified_messages, start_time, end_time)
            
            # 从JSON结果中提取简报内容和基础问题ID列表
            report_content = summary_result.get('summary', '')
            basic_question_ids = summary_result.get('basic_question_ids', [])
            
            # 计算基础问题密度（程序计算，确保准确）
            total_messages = len(unified_messages)
            basic_op_count = len(basic_question_ids)
            basic_op_density = basic_op_count / total_messages if total_messages > 0 else 0
            
            logger.info(f"AI识别基础操作问题数量: {basic_op_count} (密度: {basic_op_density:.2%})")
            
            # 保存训练数据
            save_training_data(unified_messages, basic_question_ids)
            
            # 生成文件名（处理同一天多次启动的情况）
            filename = generate_filename(start_time, end_time, i+1 if len(time_windows) > 1 else None)
            
            # 获取上次简报统计数据
            previous_stats = get_previous_report_stats()
            
            # 保存本次简报统计数据
            current_stats = save_report_stats(start_time, end_time, basic_op_count, filename)
            
            # 计算基础操作问题密度变化
            density_change = calculate_basic_op_density_change(current_stats, previous_stats)
            
            # 在报告内容后添加基础操作问题密度统计
            density_stats = f"""
## 📊 基础操作问题统计
- 总消息数: {total_messages}
- 基础操作问题数: {basic_op_count}
- 基础问题密度: {basic_op_density:.2%}
- 密度变化: {density_change}
"""
            enhanced_report_content = f"{report_content}\n\n{density_stats}"
            
            # 保存到 Obsidian（更新已创建的空文件）
            for idx, file_path in created_files:
                if idx == i:
                    update_report_file(file_path, enhanced_report_content, filename)
                    break
            
            # 推送到 Telegram
            await adapter.send_digest_to_channel(enhanced_report_content)
            logger.info(f"简报 {i+1} 已推送到 Telegram 频道")

if __name__ == "__main__":
    asyncio.run(main())
