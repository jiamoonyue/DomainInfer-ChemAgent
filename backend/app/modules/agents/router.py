"""Agents router — chat endpoint with SSE streaming."""

import json
import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.modules.agents.service import AgentEngine, AgentConfig

router = APIRouter(prefix="/agents", tags=["Agents"])


class ChatRequest(BaseModel):
    messages: list[dict] = Field(default_factory=list)
    system_prompt: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048
    tools: list[dict] = Field(default_factory=list)


SYSTEM_PROMPT = """You are AgentForge, a versatile AI Agent.

You have access to tools for calculations and data retrieval. When the user asks a question that requires a tool, you MUST call the appropriate tool rather than guessing.

Key rules:
- For calculations, always use the provided tools
- For factual queries, rely on the conversation context
- Respond in the user's language
- Be concise and accurate"""


@router.post("/chat")
async def chat(req: ChatRequest):
    """Chat with the Agent — Server-Sent Events stream."""

    engine = AgentEngine(
        config=AgentConfig(
            name="AgentForge",
            system_prompt=req.system_prompt or SYSTEM_PROMPT,
            tools=req.tools,
            max_iterations=5,
        )
    )

    # Extract user message
    user_msg = ""
    for m in reversed(req.messages):
        if m.get("role") == "user" and m.get("content", "").strip():
            user_msg = m["content"]
            break

    async def event_stream():
        async for event in engine.run(user_msg, history=req.messages[:-1] if len(req.messages) > 1 else None):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)  # flush

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/ping")
async def agents_ping():
    return {"module": "agents", "status": "active", "engine": "ReAct+SSE"}
