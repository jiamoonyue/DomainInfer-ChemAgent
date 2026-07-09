"""Tools router — MCP-compatible tool registry, execution, and audit."""

import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

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


@router.get("", response_model=list[ToolInfo])
async def list_tools():
    """List all registered tools (MCP tools/list). Always returns built-in tools."""
    return [
        ToolInfo(name=t["name"], description=t["description"], tool_type=t["tool_type"],
                 input_schema=t["input_schema"], is_active=True)
        for t in TOOL_DEFINITIONS
    ]


@router.post("/call", response_model=ToolCallResponse)
async def call_tool(req: ToolCallRequest):
    """Execute a tool (MCP tools/call). Pure Python, no DB needed."""
    t0 = time.time()
    result = execute_tool(req.name, req.args)
    is_error = result.startswith("ERROR")
    return ToolCallResponse(result=result, error=is_error)


@router.get("/ping")
async def tools_ping():
    return {"module": "tools", "status": "active", "engine": "MCP+Audit"}
