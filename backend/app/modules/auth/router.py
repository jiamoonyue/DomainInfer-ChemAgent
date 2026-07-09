"""Auth router — registration, login, token refresh, API key management."""

import uuid

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import GetDB, CurrentUser
from app.modules.auth.service import AuthService
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    CreateApiKeyRequest,
    TokenResponse,
    UserResponse,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(req: RegisterRequest, db: GetDB):
    """Register a new user account. First user becomes admin."""
    svc = AuthService(db)
    return await svc.register(req)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: GetDB):
    """Login and receive JWT access + refresh tokens."""
    svc = AuthService(db)
    return await svc.login(req)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: GetDB):
    """Refresh an expired access token using a refresh token."""
    svc = AuthService(db)
    return await svc.refresh_token(req.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: CurrentUser):
    """Get the currently authenticated user."""
    return UserResponse.model_validate(user)


# ---- API Keys ----

@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(req: CreateApiKeyRequest, user: CurrentUser, db: GetDB):
    """Create a new API key. The raw key is only shown once."""
    svc = AuthService(db)
    return await svc.create_api_key(user.id, req.name)


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(user: CurrentUser, db: GetDB):
    """List all API keys for the current user (without raw keys)."""
    svc = AuthService(db)
    return await svc.list_api_keys(user.id)


@router.delete("/api-keys/{key_id}", status_code=204)
async def delete_api_key(key_id: uuid.UUID, user: CurrentUser, db: GetDB):
    """Delete an API key."""
    svc = AuthService(db)
    await svc.delete_api_key(user.id, key_id)
