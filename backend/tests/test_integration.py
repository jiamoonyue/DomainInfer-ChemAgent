"""Integration tests — API endpoints via TestClient."""

import sys
import os
os.environ["USE_API"] = "true"
os.environ["DEEPSEEK_API_KEY"] = "test-key"

import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app


@pytest.fixture
def client():
    """Return an async test client."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_module_pings():
    """All module pings should return active status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        modules = ["agents", "rag", "tools", "knowledge", "observability"]
        for mod in modules:
            resp = await client.get(f"/api/{mod}/ping")
            assert resp.status_code == 200, f"{mod}/ping failed: {resp.status_code}"
            data = resp.json()
            assert data["status"] == "active", f"{mod}/ping status: {data}"


@pytest.mark.asyncio
async def test_tools_list():
    """GET /api/tools should return 10 tools (6 local + 4 external API)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/tools")
        assert resp.status_code == 200
        tools = resp.json()
        assert len(tools) == 10, f"Expected 10 tools, got {len(tools)}"
        names = [t["name"] for t in tools]
        assert "calculate_molecular_weight" in names
        assert "pubchem_search" in names
        assert "arxiv_search" in names


@pytest.mark.asyncio
async def test_tool_call():
    """POST /api/tools/call should execute a tool correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/tools/call",
            json={"name": "calculate_molecular_weight", "args": {"formula": "NaCl"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "58" in data["result"]


@pytest.mark.asyncio
async def test_tool_call_external_api():
    """POST /api/tools/call should handle external API tools."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/tools/call",
            json={"name": "pubchem_search", "args": {"query": "water"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should return PubChem data or graceful error — not crash
        assert "result" in data


@pytest.mark.asyncio
async def test_knowledge_namespaces():
    """GET /api/knowledge/namespaces should return available domains."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/knowledge/namespaces")
        assert resp.status_code == 200
        namespaces = resp.json()
        assert "chem" in namespaces


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """GET /metrics should return Prometheus metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_conversations_unauthorized():
    """Conversations endpoint should require auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/conversations")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_register_endpoint():
    """POST /api/auth/register should exist and be accessible without auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # DB unavailable — expect 500 (not 401 = auth rejected)
        resp = await client.post(
            "/api/auth/register",
            json={"username": "t", "email": "t@t.com", "password": "test123"},
        )
        # Should either succeed (200/201) or fail with DB error (500) — NOT 401
        assert resp.status_code != 401


@pytest.mark.asyncio
async def test_auth_login_endpoint():
    """POST /api/auth/login should be accessible without auth (DB may be unavailable)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/login",
            json={"email": "t@t.com", "password": "test123"},
        )
        # Must not be 401 (auth middleware bypass). DB may be 500 or 422.
        assert resp.status_code != 401


@pytest.mark.asyncio
async def test_agents_route_exists():
    """GET /api/agents should exist (lists YAML-configured agents)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
