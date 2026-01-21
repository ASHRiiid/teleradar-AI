# Telegram 信息自动化整理系统设计方案

## 1. 核心目标
构建一个高度可扩展的自动化流水线，定时从多个社交平台（首发 Telegram）获取信息，抓取链接内容，利用 AI 进行深度归纳，并多端推送。

## 2. 架构设计 (分层架构)

为了保证后续支持微信、飞书、Discord 等平台，系统采用**插件化/适配器模式**并引入**异步解耦**。

### A. 数据采集层 (Ingestion Layer) - 生产者
- **Unified Message Model**: 采用多态模型标准化不同平台的信息。
  ```python
  class UnifiedMessage:
      id: str           # 内部唯一 ID
      platform: str     # telegram/wechat/feishu
      content: str      # 消息原文
      urls: List[str]   # 提取的链接
      timestamp: datetime
      metadata: Dict    # 原始平台元数据
  ```
- **Source Adapters**:
    - `TelegramAdapter`: 使用 Telethon (UserBot 模式)，监控多群组。
    - `FutureAdapters`: 为微信、飞书预留的 Hook 接口。

### B. 信息处理层 (Processing Layer) - 消费者
- **Queue System**: 使用 `asyncio.Queue` 或 `Redis` 解耦抓取与耗时处理任务。
- **Content Scraper**: 
    - 优先使用 `Jina Reader API` (https://r.jina.ai/) 将网页内容转化为 Markdown 友好格式。
- **AI Engine**: 
    - 采用 GPT-4o-mini 进行摘要、分类与标签提取。

### C. 交付层 (Delivery Layer)
- **Obsidian Git Sync (推荐)**: 
    - 程序将生成的消息 MD 文件写入本地目录并自动 `git commit & push`。
    - 用户端 Obsidian 通过 `Obsidian Git` 插件自动同步。
- **TG Bot**: 同步发送精简版日报。

## 3. 技术选型建议
- **语言**: Python (生态最成熟)。
- **任务调度**: 
    - 短期: `APScheduler` 或 `GitHub Actions` (如果不需要常驻)。
    - 长期: `Temporal` 或 `Celery`。
- **数据库**: SQLite (轻量，记录已处理的消息 ID，防止重复处理)。

## 4. 扩展性考虑
- **接口契约**: 定义标准的 `Message` 类（包含 `source`, `raw_text`, `links`, `author`, `timestamp`）。
- **Pipeline 模式**: 使用责任链模式处理信息，每一级处理（清洗 -> 爬虫 -> AI -> 格式化）都可以独立增减。

## 5. 开发路线图
1. **Phase 1**: 实现 Telegram 消息监听与基础文本 AI 归纳，输出到本地 Markdown。
2. **Phase 2**: 加入网页链接内容爬取与深度分析。
3. **Phase 3**: 增加推送机器人与 Obsidian 自动同步。
4. **Phase 4**: 扩展其他数据源（微信、飞书）。
