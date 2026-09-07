# Slack-ClawdBot (Python Edition) 🚀

> **Advanced Slack AI Assistant built natively in Python with RAG Semantic Search, Long-Term User Memory (Mem0), and Model Context Protocol (MCP) Tool Execution.**

---

## ✨ Features

- **⚡ Native Agent Execution Loop:** Direct, transparent multi-step tool calling loop using OpenAI / Anthropic SDKs (no bloated orchestration frameworks like LangChain or LangGraph).
- **🔍 RAG Slack History Knowledge Base:** Embeds and searches company discussions, decisions, and threads with local vector similarity search and metadata filtering.
- **🧠 Personalized Long-Term Memory (Mem0):** Automatically extracts and remembers user preferences, ongoing projects, and facts across conversations.
- **🔌 Model Context Protocol (MCP):** Connects to external MCP servers (e.g. GitHub, Notion, Linear) via stdio JSON-RPC and dynamically exposes their tools to the LLM.
- **💬 Slack Bolt Socket Mode:** Instant WebSocket connection to Slack events (`@mention`, Direct Messages, threads) with no public URL or ngrok required.
- **⏰ Task Scheduling & Cron:** Schedule one-off reminders or recurring team broadcasts using standard cron syntax.
- **🗄️ SQLite Session Management:** Persistent conversation history, thread mapping, and DM pairing code security in local WAL-mode SQLite.

---

## 📁 Project Structure

```
slack_clawdbot_py/
├── requirements.txt            # Python dependencies
├── .env.example                # Template for environment variables
├── mcp-config.example.json     # MCP server configuration template
├── scripts/
│   ├── setup_db.py             # SQLite schema initializer
│   └── run_indexer.py          # CLI indexer for Slack channels
└── src/
    ├── main.py                 # Application entrypoint & graceful shutdown
    ├── config.py               # Pydantic configuration & environment loader
    ├── utils/
    │   └── logger.py           # Colorized module logger
    ├── memory/
    │   └── database.py         # SQLite storage (sessions, messages, tasks, pairing)
    ├── memory_ai/
    │   └── mem0_client.py      # Mem0 memory integration
    ├── rag/
    │   ├── embeddings.py       # OpenAI embeddings & cosine similarity
    │   ├── vectorstore.py      # Persistent local vector store
    │   ├── retriever.py        # Semantic search with Slack filters
    │   └── indexer.py          # Channel message indexer & sync
    ├── mcp/
    │   ├── config.py           # MCP server configs
    │   ├── client.py           # Subprocess stdio JSON-RPC MCP client
    │   └── tool_converter.py   # Converts MCP tools to OpenAI function schemas
    ├── tools/
    │   ├── slack_actions.py    # Slack WebClient operations
    │   └── scheduler.py        # Cron & one-off task execution
    ├── agents/
    │   ├── prompts.py          # System prompts & instructions
    │   └── agent.py            # The core native tool-calling loop
    └── channels/
        └── slack.py            # Slack Bolt App & Socket Mode event handlers
```

---

## 🚀 Quickstart Guide

### 1. Installation
Create a virtual environment and install the dependencies:
```bash
cd slack_clawdbot_py
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Key requirements:
- `SLACK_BOT_TOKEN` (`xoxb-...`)
- `SLACK_APP_TOKEN` (`xapp-...` with `connections:write` scope for Socket Mode)
- `OPENAI_API_KEY` (`sk-...`)

### 3. Initialize SQLite Database
```bash
python3 scripts/setup_db.py
```

### 4. (Optional) Configure MCP Tools
Copy `mcp-config.example.json` to `mcp-config.json` to enable GitHub or Notion tools:
```bash
cp mcp-config.example.json mcp-config.json
```

### 5. Start the Bot
```bash
python3 -m src.main
```

---

## 🛠️ Slack Bot Scopes Needed

In your Slack App settings at [api.slack.com/apps](https://api.slack.com/apps):
1. **Enable Socket Mode** under **Settings > Socket Mode**.
2. **Bot Token Scopes (`xoxb-`)**:
   - `app_mentions:read`
   - `chat:write`
   - `channels:history`, `channels:read`
   - `groups:history`, `groups:read`
   - `im:history`, `im:read`, `im:write`
   - `reactions:read`, `reactions:write`
   - `users:read`, `users:read.email`
3. **Event Subscriptions**:
   - `app_mention`
   - `message.im`
