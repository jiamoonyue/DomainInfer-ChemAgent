"""Observability router — metrics, traces, cost reporting."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import GetDB, CurrentUser
from app.modules.auth.models import User
from app.modules.observability.models import TokenUsageLog

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/cost/daily")
async def daily_cost(user: CurrentUser, db: GetDB, days: int = Query(default=7, ge=1, le=90)):
    """Get daily token cost breakdown."""
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")

    result = await db.execute(
        select(
            cast(TokenUsageLog.created_at, Date).label("day"),
            func.sum(TokenUsageLog.input_tokens).label("total_input"),
            func.sum(TokenUsageLog.output_tokens).label("total_output"),
            func.sum(TokenUsageLog.cost).label("total_cost"),
            func.count(TokenUsageLog.id).label("requests"),
        )
        .where(TokenUsageLog.created_at >= func.now() - func.make_interval(days=days))
        .group_by("day")
        .order_by("day")
    )
    rows = result.all()
    return {
        "days": days,
        "data": [
            {
                "date": str(row.day),
                "input_tokens": row.total_input,
                "output_tokens": row.total_output,
                "cost": round(float(row.total_cost or 0), 6),
                "requests": row.requests,
            }
            for row in rows
        ],
    }


@router.get("/cost/by-user")
async def cost_by_user(user: CurrentUser, db: GetDB, days: int = Query(default=30, ge=1, le=90)):
    """Get cost breakdown by user (admin only)."""
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")

    result = await db.execute(
        select(
            TokenUsageLog.user_id,
            func.sum(TokenUsageLog.input_tokens).label("total_input"),
            func.sum(TokenUsageLog.output_tokens).label("total_output"),
            func.sum(TokenUsageLog.cost).label("total_cost"),
            func.count(TokenUsageLog.id).label("requests"),
        )
        .where(TokenUsageLog.created_at >= func.now() - func.make_interval(days=days))
        .group_by(TokenUsageLog.user_id)
        .order_by(func.sum(TokenUsageLog.cost).desc())
    )
    rows = result.all()
    return {
        "days": days,
        "data": [
            {
                "user_id": str(row.user_id) if row.user_id else "anonymous",
                "input_tokens": row.total_input,
                "output_tokens": row.total_output,
                "cost": round(float(row.total_cost or 0), 6),
                "requests": row.requests,
            }
            for row in rows
        ],
    }


@router.get("/overview")
async def overview(db: GetDB):
    """Quick system overview metrics."""
    from app.modules.conversations.models import Conversation, Message
    from app.modules.auth.models import User as UserModel
    from app.modules.rag.models import Document, Chunk

    user_count = await db.scalar(select(func.count(UserModel.id)))
    conv_count = await db.scalar(select(func.count(Conversation.id)))
    msg_count = await db.scalar(select(func.count(Message.id)))
    doc_count = await db.scalar(select(func.count(Document.id)))
    chunk_count = await db.scalar(select(func.count(Chunk.id)))

    today_reqs = await db.scalar(
        select(func.count(TokenUsageLog.id)).where(
            TokenUsageLog.created_at >= func.now() - func.make_interval(days=1)
        )
    )
    today_cost = await db.scalar(
        select(func.sum(TokenUsageLog.cost)).where(
            TokenUsageLog.created_at >= func.now() - func.make_interval(days=1)
        )
    )

    return {
        "users": user_count or 0,
        "conversations": conv_count or 0,
        "messages": msg_count or 0,
        "documents": doc_count or 0,
        "chunks": chunk_count or 0,
        "today_requests": today_reqs or 0,
        "today_cost": round(float(today_cost or 0), 6),
    }


@router.get("/ping")
async def observability_ping():
    return {"module": "observability", "status": "active"}
