# Information AI - Telegram Multi-Channel Intelligence System

A powerful, modular system designed to monitor, collect, and analyze information from multiple Telegram groups and channels. It leverages advanced AI (DeepSeek) to provide structured summaries, real-time alerts, and long-term knowledge management via Obsidian.

## 🌟 Project Overview

This project provides a comprehensive solution for "information overload" in the Telegram ecosystem. It automatically tracks dozens of crypto-related groups and channels, filters out noise, and delivers high-signal intelligence through multiple delivery channels.

## 🚀 Core Features

- **Automated Collection**: Stealthy monitoring of 44+ Telegram groups and channels using Telethon (MTProto).
- **AI-Powered Analysis**: DeepSeek-integrated analysis for single-message summarization and multi-source global sentiment/trend synthesis.
- **Multi-Channel Push**: Immediate updates delivered to a dedicated Telegram radar channel (@HDXSradar).
- **Obsidian Integration**: Automated generation of daily newsletters and real-time reports in Markdown format for your personal knowledge base.
- **Web Dashboard**: Interactive Streamlit-based interface to visualize data, monitor database status, and review AI insights.

## 🛠 Setup & Quick Start

### Prerequisites
- Python 3.10+
- Telegram API Credentials (API ID & Hash)
- DeepSeek API Key

### Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your `.env` file (see `src/config.py` for required variables).

### Common Commands

**1. Run Real-Time Global Analysis (Recommended)**
Collects data from the past hour across all monitored chats, generates a synthesis report, and pushes to the Telegram channel.
```bash
python3 process_past_hour.py
```

**2. Start the Web Dashboard**
Launch the interactive visualization tool.
```bash
streamlit run web/dashboard.py
```

**3. Full Collection & Analysis Flow**
Performs basic collection, per-message AI analysis, and generates Obsidian reports.
```bash
python3 collect_compatible.py
```

## 📂 Directory Structure

```text
├── src/                    # Core source code
│   ├── adapters/           # Telegram connection logic (v1 & v2)
│   ├── delivery/           # Delivery mechanisms (Obsidian, etc.)
│   ├── processors/         # AI analysis and scraping logic
│   ├── config.py           # Configuration management
│   ├── models.py           # Data models
│   └── storage.py          # Database operations
├── web/                    # Streamlit dashboard
├── data/                   # Local SQLite database (raw_messages.db)
├── obsidian-tem/           # Generated reports and newsletters
├── test/                   # Comprehensive test suite
├── requirements.txt        # Project dependencies
└── README.md               # Project documentation
```

## 📊 Current Status & Roadmap

### Current Status (as of 2026-01-23)
- ✅ **System Ready**: All authentication and core modules are production-ready.
- ✅ **Extensive Monitoring**: 44+ active crypto groups/channels being tracked.
- ✅ **Real-Time Synthesis**: `process_past_hour.py` provides high-quality global snapshots.
- ✅ **Robust Handling**: Proper UTC timezone management and ID resolution.

### Roadmap
- [ ] **Web Content Extraction**: Integrate Jina Reader to crawl links within messages.
- [ ] **Interactive Dashboard**: Add search, filtering, and manual trigger buttons to the Web UI.
- [ ] **Multi-Modal Support**: AI analysis for images (K-line charts, screenshots).
- [ ] **Custom Templates**: Flexible templates for different report formats.

---
*Maintained with 🎯 for high-signal intelligence gathering.*
