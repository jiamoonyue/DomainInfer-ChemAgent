"""Agents router — 设计文档 5.2: POST /chat (SSE), GET /agents, GET /agents/{id}/config

完整请求链路:
  User message → AgentEngine.run()
    → LangGraph(think → [tool?] → execute_tool → observe → think → respond)
    → RAG context injected before think
    → Tools auto-registered from TOOL_DEFINITIONS
    → SSE streaming output
"""

import json
import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.modules.agents.service import AgentEngine, get_agent_engine

router = APIRouter(prefix="/agents", tags=["Agents"])


class ChatRequest(BaseModel):
    messages: list[dict] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 2048


@router.post("/chat")
async def chat(req: ChatRequest):
    """Agent chat with SSE streaming. Full pipeline: RAG → Tools → Agent."""

    # Extract user message
    user_msg = ""
    for m in reversed(req.messages):
        if m.get("role") == "user" and m.get("content", "").strip():
            user_msg = m["content"]
            break

    engine = get_agent_engine()

    async def event_stream():
        async for event in engine.run(user_msg):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)  # flush SSE

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("")
async def list_agents():
    """List all registered agents."""
    from app.core.agent_config import list_agents as la
    agents_list = la()
    return {"agents": agents_list}


@router.get("/{agent_id}/config")
async def get_agent_config(agent_id: str):
    """Get a specific agent's YAML configuration."""
    from app.core.agent_config import load_agent_config
    config = load_agent_config(agent_id)
    if config is None:
        return {"error": f"Agent '{agent_id}' not found"}
    return config


@router.get("/ping")
async def agents_ping():
    return {"module": "agents", "status": "active", "engine": "LangGraph+ReAct+Tools+RAG"}
