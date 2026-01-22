# Telegram 信息自动化系统 (Teleradar AI)

这是一个功能强大、模块化的 Telegram 信息监测与智能分析系统。通过集成 DeepSeek AI，系统能够自动监控 44+ 个热门加密货币/技术群组，过滤噪音，并生成结构化的情报简报、实时警报以及 Obsidian 长期知识库。

## 🚀 核心功能

-   **自动化采集**：基于 Telethon (MTProto) 协议，隐秘且高效地监控 44+ 个 Telegram 热门群组和频道。
-   **DeepSeek AI 深度分析**：
    *   **单条消息摘要**：自动提取长消息核心点。
    *   **全局简报合成**：实时聚合多源信息，分析讨论主题、市场情绪、行情走势及热门项目。
-   **实时频道推送**：精炼的情报将自动推送至指定的 Telegram 频道 (@HDXSradar)。
-   **Obsidian 知识库同步**：自动生成 Markdown 格式的每小时报告、每日简报，无缝接入个人第二大脑。
-   **Web 数据看板**：基于 Streamlit 的可视化界面，实时查看数据库状态、AI 洞察及历史情报。

## 🛠 快速开始

### 环境要求
- Python 3.10+
- Telegram API 凭据 (API ID & Hash)
- DeepSeek API Key

### 安装与运行
1. **安装依赖**：
    ```bash
    pip install -r requirements.txt
    ```
2. **配置环境**：
    参考 `src/config.py`，在根目录创建 `.env` 文件并填入相关密钥。

3. **运行实时简报 (核心逻辑)**：
    采集过去一小时的所有监控数据，生成 AI 深度合成报告并推送到频道。
    ```bash
    python3 process_past_hour.py
    ```

4. **启动 Web 看板**：
    启动交互式可视化工具，查看实时数据和 AI 结果。
    ```bash
    streamlit run web/dashboard.py
    ```

## 📂 目录结构说明

```text
├── src/                    # 核心源代码
│   ├── adapters/           # Telegram 连接与协议适配 (v1/v2)
│   ├── delivery/           # 数据交付模块 (Obsidian 同步等)
│   ├── processors/         # AI 处理器、内容摘要与爬虫逻辑
│   ├── config.py           # 配置管理中心
│   ├── models.py           # 数据库模型与数据结构
│   └── storage.py          # 数据库持久化操作 (SQLite)
├── web/                    # Streamlit Web 看板代码
├── data/                   # 本地数据库存储 (raw_messages.db)
├── obsidian-tem/           # 自动生成的 Obsidian Markdown 报告
├── test/                   # 完善的测试套件
├── requirements.txt        # 项目依赖清单
└── README.md               # 项目文档
```

## ⚠️ 安全提醒

本系统涉及敏感凭据，请务必妥善保管以下文件：
-   **`.env`**：包含 API 密钥、数据库路径等核心隐私，**严禁上传至公开 Git 仓库**。
-   **`.session` 文件**：Telegram 的登录会话凭证，泄露可能导致账号被盗。
-   **`data/*.db`**：本地存储的采集原始数据，包含聊天记录详情。

## 🗺 未来路线图

- [ ] **网页内容提取**：集成 Jina Reader，自动抓取并分析消息中包含的网页链接内容。
- [ ] **看板增强**：在 Web UI 中增加搜索、过滤以及手动触发采集的功能。
- [ ] **多模态支持**：引入 AI 对图片（如 K 线图、截图）的自动识别与分析。
- [ ] **自定义模版**：支持根据不同需求自定义报告的 Markdown 模版。

---
*保持专注，只捕捉高价值信号。*
