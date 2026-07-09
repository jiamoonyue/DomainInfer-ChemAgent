"""Tools models — ToolDefinition (MCP registry) and ToolCallLog (audit trail)."""

import uuid

from sqlalchemy import String, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import BaseModel


class ToolDefinition(BaseModel):
    __tablename__ = "tool_definitions"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tool_type: Mapped[str] = mapped_column(String(32), default="local")  # local | external_api | custom
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=False)  # JSON Schema
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self):
        return f"<Tool {self.name} ({self.tool_type})>"


class ToolCallLog(BaseModel):
    __tablename__ = "tool_call_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tool_args: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    is_error: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self):
        return f"<ToolCall {self.tool_name} {'ERR' if self.is_error else 'OK'}>"
