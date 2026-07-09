"""Conversations router — CRUD + history search."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import GetDB, CurrentUser
from app.modules.conversations.models import Conversation, Message
from app.modules.auth.models import User

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: str

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse] = []


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=256)


class AddMessageRequest(BaseModel):
    role: str = Field(pattern="^(user|assistant|system|tool|summary)$")
    content: str


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(req: CreateConversationRequest, user: CurrentUser, db: GetDB):
    conv = Conversation(user_id=user.id, title=req.title)
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return _conv_to_response(conv)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(user: CurrentUser, db: GetDB, limit: int = 50):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return [_conv_to_response(c) for c in result.scalars().all()]


@router.get("/{conv_id}", response_model=ConversationDetail)
async def get_conversation(conv_id: uuid.UUID, user: CurrentUser, db: GetDB):
    conv = await db.scalar(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return ConversationDetail(
        **_conv_to_response(conv).model_dump(),
        messages=[
            MessageResponse(
                id=m.id, role=m.role, content=m.content,
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
            for m in conv.messages
        ],
    )


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(conv_id: uuid.UUID, user: CurrentUser, db: GetDB):
    conv = await db.scalar(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    if not conv:
        raise HTTPException(404, "Conversation not found")
    await db.delete(conv)


@router.post("/{conv_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(conv_id: uuid.UUID, req: AddMessageRequest, user: CurrentUser, db: GetDB):
    conv = await db.scalar(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    if not conv:
        raise HTTPException(404, "Conversation not found")

    msg = Message(conversation_id=conv.id, role=req.role, content=req.content)
    db.add(msg)

    # Auto-title from first user message
    if req.role == "user":
        msg_count = await db.scalar(
            select(func.count(Message.id)).where(
                Message.conversation_id == conv.id, Message.role == "user"
            )
        )
        if msg_count and msg_count <= 1:
            conv.title = req.content[:60]

    await db.flush()
    await db.refresh(msg)
    return MessageResponse(
        id=msg.id, role=msg.role, content=msg.content,
        created_at=msg.created_at.isoformat() if msg.created_at else "",
    )


@router.get("/search", response_model=list[ConversationResponse])
async def search_conversations(q: str, user: CurrentUser, db: GetDB):
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user.id,
            Conversation.title.ilike(f"%{q}%"),
        ).order_by(Conversation.updated_at.desc()).limit(20)
    )
    return [_conv_to_response(c) for c in result.scalars().all()]


def _conv_to_response(c: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=c.id,
        title=c.title,
        created_at=c.created_at.isoformat() if c.created_at else "",
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    )
