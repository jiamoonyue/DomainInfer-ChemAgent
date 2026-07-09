"""Tools router — MCP-compatible tool registry, execution, and audit."""

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import GetDB, OptionalUser
from app.modules.tools.models import ToolDefinition, ToolCallLog
from app.modules.tools.engine import execute_tool, TOOL_DEFINITIONS

router = APIRouter(prefix="/tools", tags=["Tools"])


class ToolInfo(BaseModel):
    name: str
    description: str
    tool_type: str
    input_schema: dict
    is_active: bool


class ToolCallRequest(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)
    agent_id: str | None = None


class ToolCallResponse(BaseModel):
    result: str
    error: bool


# ---- Seed default tools on first access ----

async def _seed_tools(db: AsyncSession):
    """Ensure default tool definitions exist in the database."""
    existing = await db.scalar(select(func.count(ToolDefinition.id)))
    if existing and existing > 0:
        return

    for td in TOOL_DEFINITIONS:
        tool = ToolDefinition(
            name=td["name"],
            description=td["description"],
            tool_type=td["tool_type"],
            input_schema=td["input_schema"],
        )
        db.add(tool)
    await db.flush()
    print(f"[Tools] Seeded {len(TOOL_DEFINITIONS)} default tools")


# ---- Endpoints ----

@router.get("", response_model=list[ToolInfo])
async def list_tools(db: GetDB):
    """List all registered tools (MCP tools/list)."""
    await _seed_tools(db)
    result = await db.execute(
        select(ToolDefinition).where(ToolDefinition.is_active == True).order_by(ToolDefinition.name)
    )
    return [
        ToolInfo(name=t.name, description=t.description, tool_type=t.tool_type,
                 input_schema=t.input_schema, is_active=t.is_active)
        for t in result.scalars().all()
    ]


@router.post("/call", response_model=ToolCallResponse)
async def call_tool(req: ToolCallRequest, user: OptionalUser, db: GetDB):
    """Execute a tool (MCP tools/call)."""
    t0 = time.time()
    result = execute_tool(req.name, req.args)
    is_error = result.startswith("ERROR")
    latency_ms = round((time.time() - t0) * 1000, 1)

    # Audit log
    try:
        log = ToolCallLog(
            user_id=user.id if user else None,
            agent_id=req.agent_id,
            tool_name=req.name,
            tool_args=req.args,
            tool_result=result[:500],
            latency_ms=latency_ms,
            is_error=is_error,
        )
        db.add(log)
        await db.flush()
    except Exception:
        pass

    return ToolCallResponse(result=result, error=is_error)


@router.get("/audit", response_model=list[dict])
async def tool_audit_log(db: GetDB, limit: int = 50):
    """Recent tool call audit trail."""
    result = await db.execute(
        select(ToolCallLog).order_by(ToolCallLog.created_at.desc()).limit(limit)
    )
    return [
        {
            "id": str(log.id),
            "tool_name": log.tool_name,
            "tool_args": log.tool_args,
            "latency_ms": log.latency_ms,
            "is_error": log.is_error,
            "created_at": log.created_at.isoformat() if log.created_at else "",
        }
        for log in result.scalars().all()
    ]


@router.get("/ping")
async def tools_ping():
    return {"module": "tools", "status": "active", "engine": "MCP+Audit"}
