# Claude Agentic Query Agent

A production-ready agentic AI demo that lets business users query a live database in plain English. Claude Sonnet autonomously decides which tools to call, executes multi-round reasoning, and streams a data-driven answer back to the user — no SQL required.

![screenshot](https://img.shields.io/badge/status-live%20demo-22c55e) ![python](https://img.shields.io/badge/Python-3.11+-3b82f6) ![claude](https://img.shields.io/badge/Claude-Sonnet%204.6-d97757)

## What It Does

Ask a question like *"Which product category drives the most revenue?"* and the agent will:

1. Determine which database tools are needed
2. Call them autonomously — in sequence or parallel rounds
3. Reason over the results
4. Return a formatted, cited answer streamed token-by-token

The agent can chain up to 5 tool-call rounds before forcing a final answer, handling questions that require joining multiple data sources (e.g., customers + orders + products).

## Architecture

```
User ──► FastAPI /chat/stream ──► Agentic Loop (Claude Sonnet 4.6)
                                       │
                          ┌────────────┴──────────────┐
                          │   Tool Definitions (6)     │
                          │   ├── get_revenue_summary  │
                          │   ├── get_top_customers    │
                          │   ├── get_orders           │
                          │   ├── get_inventory        │
                          │   ├── get_customer_detail  │
                          │   └── get_revenue_by_category│
                          └────────────┬──────────────┘
                                       │
                                   SQLite DB
                              (Meridian Supply Co.)
```

**Streaming:** Server-Sent Events (SSE) deliver tool-call indicators, partial text, and completion signals to the frontend in real time.

**Prompt caching:** The system prompt is cached with `cache_control: ephemeral`, cutting token costs on repeated queries.

## Tech Stack

| Layer | Technology |
|---|---|
| AI | Anthropic Claude Sonnet 4.6, Tool Use API |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Streaming | Server-Sent Events (SSE) |
| Database | SQLite (drop-in; swap for Postgres/MSSQL) |
| Frontend | Vanilla JS, dark-theme chat UI |
| Config | python-dotenv |

## Project Structure

```
claude-agentic-query-agent/
├── backend/
│   ├── agent.py        # Agentic loop — SSE streaming, multi-round tool use
│   ├── tools.py        # Tool definitions + parameterized SQL handlers
│   ├── database.py     # SQLite init + Meridian Supply Co. seed data
│   └── main.py         # FastAPI app — /chat/stream endpoint
├── frontend/
│   └── index.html      # Single-file dark chat UI
├── .env.example
├── requirements.txt
└── README.md
```

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/marcusjco/claude-agentic-query-agent.git
cd claude-agentic-query-agent
pip install -r requirements.txt

# 2. Add your API key
cp .env.example .env
# edit .env → ANTHROPIC_API_KEY=sk-ant-...

# 3. Run
cd backend
uvicorn main:app --reload

# 4. Open http://localhost:8000
```

The SQLite database is created and seeded automatically on first run. No migrations needed.

## Demo Dataset — Meridian Supply Co.

Fictional B2B industrial equipment distributor with 8 customers, 10 products across 5 categories, and 20 orders spanning Jan–Apr 2026. Enough variety to demonstrate multi-tool reasoning.

**Try these questions:**
- Who are our top 5 customers by spend?
- What's our total revenue this year?
- Which products are running low on stock?
- Show me all pending orders
- Which product category drives the most revenue?

## Key Implementation Details

### Agentic Loop (`backend/agent.py`)

The loop runs up to 5 rounds. Each round:
- Sends the full message history + available tools to Claude
- Yields SSE events for any tool calls (`tool_call`) and their results (`tool_result`)
- If Claude returns `end_turn` with no tool calls, yields the final `text` and exits
- Otherwise appends assistant + tool result messages and loops

```python
for _round in range(5):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        tools=TOOL_DEFINITIONS,
        messages=messages,
    )
    # ... stream tool calls → execute → append → repeat
    if not tool_uses or response.stop_reason == "end_turn":
        break
```

### Tool Design (`backend/tools.py`)

Claude never writes raw SQL. Each tool is a named, parameterized Python function. This gives Claude a typed interface while keeping SQL injection impossible and query logic centralized.

### Swap the Database

Replace SQLite with any backend by changing `get_connection()` in `database.py`. The tool handlers are pure Python — no ORM coupling.

## Extending This

- **Add a tool:** Add an entry to `TOOL_DEFINITIONS` and a handler in `tools.py`. Claude discovers it automatically.
- **Connect real data:** Update `get_connection()` to point at your Postgres, MSSQL, or MySQL instance.
- **Add auth:** Drop an API key middleware into `main.py`.
- **Swap the model:** Change `model="claude-sonnet-4-6"` in `agent.py` to any Claude model.

## License

MIT
