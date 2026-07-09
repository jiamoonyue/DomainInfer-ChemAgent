"""Auth service — registration, login, token and API key management."""

import hashlib
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.modules.auth.models import User, ApiKey
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
)
from app.core.exceptions import UnauthorizedException, NotFoundException, ValidationException
from app.core.config import settings


class AuthService:
    """Handles user authentication and API key management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, req: RegisterRequest) -> UserResponse:
        """Register a new user. First user becomes admin."""
        # Check uniqueness
        existing = await self.db.execute(
            select(User).where(
                (User.username == req.username) | (User.email == req.email)
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationException("Username or email already exists")

        # First user is admin
        user_count = await self.db.execute(select(User.id))
        role = "admin" if not user_count.scalars().first() else "user"

        user = User(
            username=req.username,
            email=req.email,
            password_hash=hash_password(req.password),
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return UserResponse.model_validate(user)

    async def login(self, req: LoginRequest) -> TokenResponse:
        """Authenticate user and return JWT tokens."""
        result = await self.db.execute(
            select(User).where(User.email == req.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(req.password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedException("Account is disabled")

        token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Issue a new access token from a valid refresh token."""
        payload = decode_token(refresh_token)
        if payload is None:
            raise UnauthorizedException("Invalid or expired refresh token")
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Not a refresh token")

        user_id = payload.get("sub")
        result = await self.db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or disabled")

        token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

    async def create_api_key(self, user_id: uuid.UUID, name: str) -> ApiKeyCreatedResponse:
        """Create a new API key. The raw key is only returned once."""
        raw_key = f"af_{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = ApiKey(user_id=user_id, key_hash=key_hash, name=name)
        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)

        return ApiKeyCreatedResponse(
            id=api_key.id,
            name=api_key.name,
            api_key=raw_key,
            created_at=api_key.created_at,
        )

    async def list_api_keys(self, user_id: uuid.UUID) -> list[ApiKeyResponse]:
        """List API keys for a user (never returns raw key)."""
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
        )
        return [ApiKeyResponse.model_validate(k) for k in result.scalars().all()]

    async def delete_api_key(self, user_id: uuid.UUID, key_id: uuid.UUID):
        """Delete an API key."""
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        key = result.scalar_one_or_none()
        if not key:
            raise NotFoundException("API key not found")
        await self.db.delete(key)

    async def get_user(self, user_id: uuid.UUID) -> UserResponse:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User not found")
        return UserResponse.model_validate(user)


# ---- Bootstrap admin ----

async def bootstrap_admin(db: AsyncSession):
    """Create the initial admin user if no users exist."""
    result = await db.execute(select(User.id))
    if result.scalars().first() is None:
        admin = User(
            username="admin",
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role="admin",
        )
        db.add(admin)
        await db.flush()
        print(f"[Auth] Admin user created: {settings.ADMIN_EMAIL}")
