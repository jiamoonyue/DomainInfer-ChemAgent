"""FastAPI dependencies — auth, database."""

import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db as _get_db
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.security import decode_token
from app.modules.auth.models import User, ApiKey

# Standard dependency
GetDB = Annotated[AsyncSession, Depends(_get_db)]


async def get_current_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(_get_db),
) -> User:
    """Extract and validate JWT token, return current user."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise UnauthorizedException("Missing authorization header")

    # Try JWT first
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        user_id = payload.get("sub")
        if user_id:
            result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user

    # Try API Key
    import hashlib
    key_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    if api_key:
        result = await db.execute(select(User).where(User.id == api_key.user_id))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            from datetime import datetime, timezone
            api_key.last_used_at = datetime.now(timezone.utc)
            await db.flush()
            return user

    raise UnauthorizedException("Invalid or expired token")


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(_get_db),
) -> User | None:
    """Extract user from token if present, otherwise return None. Never raises."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        return await get_current_user(authorization=authorization, db=db)
    except (UnauthorizedException, Exception):
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


async def get_current_admin(current_user: CurrentUser) -> User:
    """Require admin role."""
    if current_user.role != "admin":
        raise ForbiddenException("Admin access required")
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
