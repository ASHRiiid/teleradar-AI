# 项目状态：Telegram 信息自动化整理系统

## 1. 项目目标
构建一个高度可扩展的自动化流水线，每天定时从多个 Telegram 群组（未来扩展至微信、飞书、Discord）抓取信息，抓取链接内容，利用 AI 归纳整理，并通过 Telegram Bot 和 Obsidian Markdown 文档双端推送。

## 2. 核心设计原则
- **安全性优先**：UserBot 采用“隐身模式”，不触发已读回执、不显示在线状态、不干扰主账号社交体验。
- **数据驱动**：先采集原始数据入库（SQLite），分析特征后再制定 AI 归纳策略。
- **模块化与可扩展**：采用适配器模式，统一消息模型 (`UnifiedMessage`)，便于未来接入新平台。
- **精准时间窗口**：采集范围为北京时间前一天 08:00 至当天 08:00。

## 3. 当前架构与已完成模块

### 3.1 数据模型 (`src/models.py`)
- `UnifiedMessage`: 标准化消息格式，支持多平台。
- `ScrapedContent`: 网页抓取内容模型。

### 3.2 数据采集层
- **`src/adapters/telegram_adapter.py`**:
    - 使用 Telethon (UserBot 模式)。
    - 支持链接/用户名/私有邀请链接自动解析 (`resolve_chat`)。
    - 实现防封控逻辑：随机延迟、FloodWait 处理、消息长度过滤。
    - 新增 `fetch_messages_between` 方法，支持精准时间窗口抓取。

### 3.3 数据处理层
- **`src/processors/scraper.py`**: 集成 Jina Reader API，将网页链接转为 Markdown。
- **`src/processors/summarizer.py`**: 支持 DeepSeek API (OpenAI 兼容模式) 进行 AI 归纳。

### 3.4 数据存储与交付
- **`src/storage.py`**: SQLite 数据库，用于持久化存储原始消息，支持去重。
- **`src/delivery/obsidian.py`**: 将 AI 归纳结果按日期写入 Obsidian Markdown 文件。
- **Telegram Bot 推送**: 配置已就绪，代码待实现。

### 3.5 入口脚本
- **`collect_raw_data.py`**: 原始数据采集脚本（不跑 AI），严格按北京时间窗口抓取。
- **`main.py`**: 完整流水线入口（抓取 → 爬虫 → AI → 交付）。

## 4. 配置文件 (`.env`)
**待用户填写**:
- `API_ID`, `API_HASH`: Telegram UserBot 凭证 (来自 my.telegram.org)。
- `DEEPSEEK_API_KEY`: DeepSeek API 密钥。
- `OPENAI_BASE_URL`: `https://api.deepseek.com`。
- `OBSIDIAN_VAULT_PATH`: 本地 Obsidian 仓库绝对路径。
- `MONITORED_CHATS`: 监控的群组链接/ID，逗号分隔。
- `TELEGRAM_BOT_TOKEN`: 推送简报的 Bot Token (来自 @BotFather)。
- `TELEGRAM_USER_ID`: 接收简报的个人用户 ID (来自 @userinfobot)。

## 5. 用户指令 (`user_instructions.md`)
**必须遵守**:
- 禁止在回复中输出 DCP 相关系统通知。
- 禁止展示详细的工具调用日志 (`⚙ background_task`, `[Pasted ~X lines]` 等)。
- 响应保持简洁。
- 优先使用 DeepSeek API。
- 交付方式为 Telegram Bot + Obsidian Markdown。
- **隐身模式**：严禁触发已读回执、打字状态；模拟人类行为；私密内容仅存本地。

## 6. 下一步待办事项 (优先级排序)

### 高优先级
1.  **用户配置完成**: 等待用户填写 `.env` 中的所有必要凭证。
2.  **原始数据采集与分析**: 运行 `collect_raw_data.py`，采集首批数据。
3.  **数据分析脚本**: 编写脚本分析原始数据特征（高频词、链接分布、频道活跃度），为币圈/美股分类提供依据。
4.  **实现 Telegram Bot 推送**: 在 `src/delivery/` 下创建 `telegram_bot.py`，集成到主流水线。

### 中优先级
5.  **完善主流水线**: 在 `main.py` 中整合数据库读取、AI 归纳、双端交付。
6.  **制定过滤与分类规则**: 基于数据分析结果，设计硬过滤规则（如关键词、垃圾广告模式）和 AI 提示词优化。
7.  **测试完整流程**: 运行 `main.py` 进行端到端测试。

### 低优先级
8.  **调度与自动化**: 研究部署方案（本地 cron / GitHub Actions / 云服务器）。
9.  **扩展性预留**: 为微信、飞书适配器预留接口。

## 7. 多账号架构升级完成

### ✅ 已完成的功能升级

1. **多账号配置支持**：
   - 更新了 `.env` 配置文件结构，支持主账号和多个采集账号
   - 创建了 `src/config.py` 配置管理模块
   - 支持灵活的账号配置和扩展

2. **多账号并发采集**：
   - 创建了 `src/adapters/telegram_adapter_v2.py` 支持多账号并发采集
   - 实现了 `TelegramMultiAccountAdapter` 类管理多个客户端会话
   - 支持并发抓取相同群组，提高采集效率

3. **智能消息去重**：
   - 实现了基于内容哈希和URL哈希的去重算法
   - 可配置的去重策略（按内容/按URL）
   - 保留时间最早的消息，避免重复采集

4. **频道推送集成**：
   - 支持使用主账号向 Telegram 频道发送简报
   - 灵活的频道标识符配置（用户名或ID）
   - 支持 HTML/Markdown 解析模式

5. **向后兼容性**：
   - 保留了原有的 `TelegramAdapter` 类用于单账号场景
   - 更新了 `collect_raw_data.py` 使用新的多账号适配器
   - 创建了测试脚本验证功能

### 🔧 当前配置状态
- ✅ 采集账号1已配置（API ID: 33981268）
- ✅ 主账号已配置（用于频道推送）
- ✅ 监控群组已配置
- ✅ AI 服务密钥已配置
- ⚠️ 频道推送配置需要验证权限

## 8. 重启后行动指南
1.  **首先阅读** `user_instructions.md` 和本文件 (`project_status.md`)。
2.  **检查用户进度**: 询问用户 `.env` 配置是否已完成。
3.  **如果配置未完成**: 协助用户获取剩余凭证。
4.  **如果配置已完成**: 引导用户运行 `collect_raw_data.py` 进行首次数据采集。
5.  **采集完成后**: 编写并运行数据分析脚本，与用户讨论特征，共同制定归纳策略。
6.  **接着实现** Telegram Bot 推送模块，并测试完整流水线。

## 9. 当前进展与认证问题

### ✅ 已完成的工作

#### 1. **多账号架构升级** 
- **需求分析**：用户需要从两个 Telegram 账号同时采集信息，汇总后从主账号建立的频道推送简报
- **架构设计**：设计了多账号并发采集 → 消息去重汇总 → 主账号频道推送的架构
- **配置更新**：更新了 `.env` 文件支持多账号配置

#### 2. **代码实现**
- **配置模块**：创建了 `src/config.py` 管理多账号配置
- **多账号适配器**：创建了 `src/adapters/telegram_adapter_v2.py` 支持：
  - 多账号并发采集
  - 智能消息去重（基于内容和URL哈希）
  - 频道推送功能
- **更新采集脚本**：修改了 `collect_raw_data.py` 使用新的多账号适配器
- **测试脚本**：创建了多个测试脚本验证功能

#### 3. **当前配置状态**
- **主账号**：已配置（用于频道推送）
- **采集账号1**：已配置（API ID: 33981268）
- **监控群组**：`https://t.me/RaccoonDegen`
- **推送频道**：`HDXSradar`
- **AI 服务**：DeepSeek API 密钥已配置

### ⚠️ **遇到的认证问题**
- **验证码限制**：Telegram 对验证码请求有频率限制
- **会话文件**：已创建 `collector1_session.session` 和 `main_session.session` 文件
- **当前障碍**：验证码请求被限制，用户只收到过两次验证码，之后未再收到
- **替代方案**：已创建 `try_alternative_auth.py` 使用 `send_code_request` + `sign_in` 方法

### 📋 **修改的文件列表**
```
.env                            # 多账号配置
src/config.py                   # 配置管理模块
src/adapters/telegram_adapter_v2.py  # 多账号适配器
collect_raw_data.py             # 更新使用新适配器
test_basic.py                   # 基础功能测试
test_single_account.py          # 单账号测试
test_existing_session.py        # 会话文件测试
try_alternative_auth.py         # 替代认证方法
```

## 10. 下一步行动计划

### 短期方案（立即执行）
1. **运行替代认证脚本**：`python3 try_alternative_auth.py`
   - 如果成功获取验证码，完成认证
   - 如果仍然被限制，等待24小时

2. **验证认证成功后**：
   - 运行 `python3 collect_raw_data.py` 进行首次数据采集
   - 测试频道推送功能

### 中期方案（24小时后）
1. **重新尝试认证**：等待24小时解除限制
2. **测试双账号采集**：当获得第二个账号 API 信息时启用

### 长期方案
1. **数据分析脚本**：分析采集的数据特征
2. **AI 归纳实现**：集成 DeepSeek API 生成简报
3. **自动化部署**：设置定时任务

## 11. 重启后继续操作指南

### 如果认证未完成：
1. **检查验证码状态**：询问用户是否收到新的验证码
2. **运行替代认证**：`python3 try_alternative_auth.py`
3. **如果被限制**：建议等待24小时再尝试
4. **等待期间**：可以开发数据分析脚本或完善其他模块

### 如果认证已完成：
1. **测试数据采集**：`python3 collect_raw_data.py`
2. **验证频道推送**：检查 `HDXSradar` 频道是否收到测试消息
3. **运行完整流程**：测试从采集到推送的完整链路

### 关键信息需要记住：
1. **用户需求**：双账号采集 → 汇总去重 → 频道推送
2. **当前配置**：使用单账号（主账号兼采集账号）进行测试
3. **监控群组**：`https://t.me/RaccoonDegen`
4. **推送频道**：`HDXSradar`
5. **技术架构**：已完成多账号支持，等待认证完成即可测试
6. **当前障碍**：Telegram 验证码频率限制，需要等待或使用替代方法

## 8. 技术栈
- **语言**: Python
- **核心库**: Telethon, Pydantic, OpenAI (DeepSeek), SQLite3, pytz, httpx
- **工具**: Jina Reader API (网页转 Markdown)

---
*文档最后更新: 2026-01-22*
