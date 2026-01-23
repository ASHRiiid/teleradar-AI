# 区块链信息自动化系统 (Teleradar AI)

这是一个功能强大、模块化的 Telegram 信息监测与智能分析系统。通过集成 DeepSeek AI，系统能够自动监控 78+ 个热门加密货币群组，过滤噪音，并生成结构化的深度简报、实时警报以及 Obsidian 长期知识库。

## 🚀 核心功能

-   **多账号并发采集**：基于 Telethon (MTProto) 协议，使用 2 个采集账号同时监控 78+ 个 Telegram 热门群组和频道。
-   **DeepSeek AI 深度分析**：
    *   **智能信息整理**：按照 `setting_AI.md` 逻辑进行消息分类、去重和聚合。
    *   **全局简报合成**：实时聚合多源信息，分析市场动态、项目研报、链上异动及社区情绪。
-   **实时频道推送**：精炼的深度简报将自动推送至指定的 Telegram 频道 (@HDXSradar)。
-   **Obsidian 知识库同步**：自动生成 Markdown 格式的每日简报，无缝接入个人第二大脑。
-   **桌面一键运行**：提供 macOS 桌面脚本，双击即可运行完整简报生成流程。
-   **智能配置管理**：自动检测配置更新并同步到环境变量，支持优先级去重。

## 🛠 快速开始

### 环境要求
- Python 3.10+
- Telegram API 凭据 (API ID & Hash)
- DeepSeek API Key

### 安装与运行

#### 方式一：桌面一键运行（推荐）
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 3. 设置桌面脚本
chmod +x generate_briefing.command

# 4. 运行（三种方式任选）
#    a) 双击桌面脚本（复制到桌面后双击）
#    b) 命令行运行: ./generate_briefing.command
#    c) 定时任务: 0 0 * * * cd /path/to/project && ./generate_briefing.command
```

#### 方式二：传统命令行运行
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 3. 配置监控群组
# 编辑 setting_collector1.md 和 setting_collector2.md
# 编辑 setting_AI.md 定义AI整理逻辑

# 4. 运行24小时深度简报
python3 process_24h_report.py

# 5. 启动 Web 看板（可选）
streamlit run web/dashboard.py
```

### 桌面脚本功能特点
- ✅ **一键运行**：双击即可执行完整流程
- ✅ **详细日志**：每个步骤都有状态输出
- ✅ **配置同步**：自动检测并同步配置更新
- ✅ **错误处理**：友好的错误提示和恢复建议
- ✅ **虚拟环境支持**：自动检测并激活虚拟环境

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
- [ ] **AI身份**：根据微信等聊天记录训练不同的ai身份，完成更具感性的协作。
- [ ] **微博、雪球等网页聚合**：聚合爱说话的一些私募大佬的公开发言。

---
*保持专注，只捕捉高价值信号。*
