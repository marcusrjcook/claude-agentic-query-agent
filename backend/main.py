import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import get_connection, init_db
from agent import run_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Claude Agentic Query Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard():
    conn = get_connection()
    revenue = conn.execute(
        "SELECT ROUND(SUM(total),2) as total, COUNT(*) as orders FROM orders"
    ).fetchone()
    pending = conn.execute(
        "SELECT ROUND(SUM(total),2) as value, COUNT(*) as count FROM orders WHERE status='pending'"
    ).fetchone()
    top_customers = conn.execute("""
        SELECT c.name, c.segment, ROUND(SUM(o.total),2) as spend
        FROM customers c JOIN orders o ON o.customer_id=c.id
        GROUP BY c.id ORDER BY spend DESC LIMIT 5
    """).fetchall()
    low_stock = conn.execute(
        "SELECT name, category, stock FROM products WHERE stock < 25 ORDER BY stock ASC"
    ).fetchall()
    recent_orders = conn.execute("""
        SELECT o.order_date, c.name as customer, p.name as product,
               o.status, o.total
        FROM orders o
        JOIN customers c ON c.id=o.customer_id
        JOIN products  p ON p.id=o.product_id
        ORDER BY o.order_date DESC LIMIT 8
    """).fetchall()
    conn.close()
    return {
        "revenue":       dict(revenue),
        "pending":       dict(pending),
        "top_customers": [dict(r) for r in top_customers],
        "low_stock":     [dict(r) for r in low_stock],
        "recent_orders": [dict(r) for r in recent_orders],
    }


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    return StreamingResponse(
        run_agent(req.message, req.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# Serve the frontend
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
