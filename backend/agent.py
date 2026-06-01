"""
Claude agentic loop with SSE streaming.
Claude autonomously decides which tools to call and in how many rounds
to fully answer the user's question.
"""
import json
import os
from typing import Generator

import anthropic
from dotenv import load_dotenv
from tools import TOOL_DEFINITIONS, handle_tool

load_dotenv()

_client = None

SYSTEM_PROMPT = """You are a business intelligence assistant for Meridian Supply Co., a B2B industrial equipment distributor.

You have access to live data on customers, orders, products, and revenue. When a user asks a question:
1. Call the relevant tools to gather the data you need — you may call multiple tools across multiple rounds
2. Reason over the results
3. Deliver a clear, specific, data-driven answer

Always cite actual numbers. Never estimate when you can query. If a question requires multiple data points, gather all of them before answering.
Format responses with markdown — headers, bullets, bold numbers — it renders in the UI."""

# Cache the system prompt — it never changes between requests
SYSTEM = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _safe_history(history: list[dict], limit: int = 10) -> list[dict]:
    """Trim history without splitting a tool_use/tool_result pair."""
    trimmed = history[-limit:]
    # if the first message is a tool_result, drop it — it has no matching tool_use
    while trimmed and trimmed[0]["role"] == "user" and isinstance(trimmed[0]["content"], list):
        trimmed = trimmed[1:]
    return trimmed


def run_agent(message: str, history: list[dict]) -> Generator[str, None, None]:
    """
    Agentic loop — yields SSE strings.
    Runs up to 5 tool-call rounds before forcing a final response.
    """
    client = get_client()

    messages = _safe_history(history) + [{"role": "user", "content": message}]

    for _round in range(5):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        text_parts = []
        tool_uses  = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        if text_parts:
            yield f"data: {json.dumps({'type': 'text', 'content': ''.join(text_parts)})}\n\n"

        if not tool_uses or response.stop_reason == "end_turn":
            break

        # Notify frontend which tools are being called
        for tool in tool_uses:
            yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool.name, 'input': tool.input})}\n\n"

        # Execute tools and collect results
        tool_results = []
        for tool in tool_uses:
            try:
                result = handle_tool(tool.name, tool.input)
            except Exception as e:
                result = json.dumps({"error": f"Tool {tool.name} failed: {str(e)}"})
            yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool.name})}\n\n"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool.id,
                "content": result,
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user",      "content": tool_results})

    yield f"data: {json.dumps({'type': 'done'})}\n\n"
