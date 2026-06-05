# Claude Agentic Query Agent

![python](https://img.shields.io/badge/Python-3.11+-3b82f6) ![claude](https://img.shields.io/badge/Claude-Sonnet%204.6-d97757) [![Live Demo](https://img.shields.io/badge/live%20demo-render-46E3B7?logo=render&logoColor=white)](https://claude-agentic-query-agent.onrender.com)

**[Live Demo](https://claude-agentic-query-agent.onrender.com)** — free tier, first load after idle takes ~30 seconds

Built this to explore what it actually looks like when you give an LLM real database access and let it figure out the rest. You type a plain English question, Claude decides which tools to call, pulls the data, and streams back a real answer — no hand-holding, no pre-written queries.

The demo runs against a fictional B2B distributor called Meridian Supply Co. Ask it something like *"which product category is driving the most revenue?"* and watch it chain multiple tool calls together to get there.

## How it works

Claude gets a set of named tools — things like `get_top_customers` or `get_revenue_by_category`. When you ask a question, it figures out which ones it needs, calls them (sometimes across multiple rounds if the question is complex), reasons over what came back, and returns a formatted answer. The whole thing streams via SSE so you see tool calls firing in real time before the response arrives.

The loop caps at 5 rounds to prevent runaway calls, and the system prompt is cached so repeated queries don't re-process it every time.

```
User ──► FastAPI /chat/stream ──► Agentic Loop (Claude Sonnet 4.6)
                                       │
                          ┌────────────┴──────────────┐
                          │        Tools (6)           │
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

## Stack

| Layer | Tech |
|---|---|
| AI | Claude Sonnet 4.6 — Tool Use API |
| Backend | Python, FastAPI, Uvicorn |
| Streaming | Server-Sent Events |
| Database | SQLite (easy to swap for Postgres or MSSQL) |
| Frontend | Vanilla JS — split dashboard + chat layout |

## Project layout

```
claude-agentic-query-agent/
├── backend/
│   ├── agent.py        # the agentic loop — SSE streaming, multi-round tool use
│   ├── tools.py        # tool definitions + parameterized SQL handlers
│   ├── database.py     # SQLite init + seed data
│   └── main.py         # FastAPI — /chat/stream + /api/dashboard
├── frontend/
│   └── index.html      # dashboard left, AI chat right
├── .env.example
├── requirements.txt
└── README.md
```

## Running it locally

```bash
git clone https://github.com/marcusrjcook/claude-agentic-query-agent.git
cd claude-agentic-query-agent
pip install -r requirements.txt

cp .env.example .env
# add your Anthropic API key to .env

cd backend
uvicorn main:app --reload
```

Open `http://localhost:8000`. The database seeds itself on first run.

## The demo dataset

Meridian Supply Co. is a made-up B2B industrial equipment distributor — 8 customers, 10 products across 5 categories, 20 orders from Jan–Apr 2026. Small enough to be readable, varied enough to make multi-tool questions interesting.

Things worth trying:
- Who are our top 5 customers by spend?
- What's our total revenue this year?
- Which products are running low on stock?
- Show me all pending orders
- Which product category drives the most revenue?

## A couple things I was intentional about

**Claude never touches raw SQL.** Every tool is a named Python function with typed parameters. Claude calls `get_top_customers(limit=5, segment="Enterprise")` — it has no idea what the query looks like underneath. Keeps injection impossible and the query logic in one place.

**The agentic loop is explicit.** No framework magic. It's a plain for-loop in `agent.py` — send message, check for tool calls, execute them, append results, repeat. Easy to read, easy to modify.

**Swapping the database is one function.** Change `get_connection()` in `database.py` and point it at Postgres, MSSQL, whatever — the rest doesn't care.

## Extending it

- Add a tool: new entry in `TOOL_DEFINITIONS` + a handler function in `tools.py`. Claude picks it up automatically on the next request.
- Connect real data: update `get_connection()` in `database.py`.
- Different model: one line change in `agent.py`.

## License

MIT
