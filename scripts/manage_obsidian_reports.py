#!/usr/bin/env python3
"""
管理 Obsidian 简报文件：将超过一周的简报移动到 Oldsletters 文件夹
"""

import os
import re
from datetime import datetime, timedelta
import shutil
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_filename_date(filename):
    """
    从简报文件名中解析日期时间
    
    文件名格式：简报_YYMMDDHHMM_-YYMMDDHHMM.md
    返回：datetime 对象（使用结束时间作为文件时间）
    """
    # 匹配文件名中的时间戳
    pattern = r'简报_(\d{10})_-(\d{10})(?:_\d+)?\.md'
    match = re.match(pattern, filename)
    
    if not match:
        # 尝试匹配旧格式：简报_YYMMDD_to_YYYYMMDD.md
        pattern_old = r'简报_(\d{6})_to_(\d{8})\.md'
        match = re.match(pattern_old, filename)
        if match:
            start_str = match.group(1)  # YYMMDD
            end_str = match.group(2)    # YYYYMMDD
            try:
                # 解析结束时间（旧格式只有日期，没有时间）
                if len(end_str) == 8:  # YYYYMMDD
                    end_time = datetime.strptime(end_str, "%Y%m%d")
                else:  # YYMMDD
                    end_time = datetime.strptime(end_str, "%y%m%d")
                return end_time
            except ValueError:
                return None
        return None
    
    try:
        # 解析结束时间（文件名中的第二个时间戳）
        end_time_str = match.group(2)  # YYMMDDHHMM
        end_time = datetime.strptime(end_time_str, "%y%m%d%H%M")
        return end_time
    except ValueError:
        return None

def move_old_reports(obsidian_dir, days_threshold=7):
    """
    将超过指定天数的简报文件移动到 Oldsletters 文件夹
    
    Args:
        obsidian_dir: Obsidian 目录路径
        days_threshold: 天数阈值，超过这个天数的文件将被移动
    """
    # 确保 Oldsletters 文件夹存在
    oldsletters_dir = os.path.join(obsidian_dir, "Oldsletters")
    if not os.path.exists(oldsletters_dir):
        os.makedirs(oldsletters_dir)
        logger.info(f"创建 Oldsletters 文件夹: {oldsletters_dir}")
    
    # 获取当前时间
    current_time = datetime.now()
    
    # 计算阈值时间
    threshold_time = current_time - timedelta(days=days_threshold)
    
    # 遍历 obsidian_dir 下的所有文件
    moved_count = 0
    for filename in os.listdir(obsidian_dir):
        # 跳过目录和非简报文件
        if not filename.endswith('.md') or not filename.startswith('简报_'):
            continue
        
        file_path = os.path.join(obsidian_dir, filename)
        
        # 跳过目录
        if os.path.isdir(file_path):
            continue
        
        # 解析文件时间
        file_time = parse_filename_date(filename)
        
        if file_time is None:
            logger.warning(f"无法解析文件名时间: {filename}")
            continue
        
        # 检查文件时间是否超过阈值
        if file_time < threshold_time:
            # 目标路径
            target_path = os.path.join(oldsletters_dir, filename)
            
            # 如果目标文件已存在，添加后缀避免冲突
            counter = 1
            while os.path.exists(target_path):
                name, ext = os.path.splitext(filename)
                target_path = os.path.join(oldsletters_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            # 移动文件
            try:
                shutil.move(file_path, target_path)
                moved_count += 1
                logger.info(f"移动文件: {filename} -> Oldsletters/")
            except Exception as e:
                logger.error(f"移动文件失败 {filename}: {e}")
    
    return moved_count

def main():
    """主函数"""
    # 获取 obsidian-tem 目录路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    obsidian_dir = os.path.join(project_root, "obsidian-tem")
    
    if not os.path.exists(obsidian_dir):
        logger.error(f"Obsidian 目录不存在: {obsidian_dir}")
        return 1
    
    logger.info(f"开始管理 Obsidian 简报文件，目录: {obsidian_dir}")
    
    # 移动超过一周的简报
    moved_count = move_old_reports(obsidian_dir, days_threshold=7)
    
    if moved_count > 0:
        logger.info(f"成功移动 {moved_count} 个旧简报文件到 Oldsletters 文件夹")
    else:
        logger.info("没有需要移动的旧简报文件")
    
    return 0

if __name__ == "__main__":
    exit(main())