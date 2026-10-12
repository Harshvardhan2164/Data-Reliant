"""Unit tests for the FastAPI application and health endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.main import app
from datareliant.common.database import Base, get_db_session


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client(db_session: AsyncSession):
    """Create a test client for the FastAPI app with DB dependency override."""

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    transport = ASGITransport(app=app)
    c = AsyncClient(transport=transport, base_url="http://test")
    yield c
    app.dependency_overrides.clear()


class TestHealthEndpoints:
    """Test health and readiness endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Health endpoint should return 200 with status healthy."""
        async with client as c:
            response = await c.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert data["service"] == "datareliant-api"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client):
        """Readiness endpoint should return 200."""
        async with client as c:
            response = await c.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_openapi_docs(self, client):
        """OpenAPI spec should be accessible."""
        async with client as c:
            response = await c.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "DataReliant API"

    @pytest.mark.asyncio
    async def test_dataset_stub(self, client):
        """Dataset list stub should return empty list."""
        async with client as c:
            response = await c.get("/api/v1/datasets")
        assert response.status_code == 200
        data = response.json()
        assert data["datasets"] == []

    @pytest.mark.asyncio
    async def test_incidents_stub(self, client):
        """Incidents list stub should return empty list."""
        async with client as c:
            response = await c.get("/api/v1/incidents")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_id_header(self, client):
        """Response should include X-Request-ID header."""
        async with client as c:
            response = await c.get("/health")
        assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_dataset_register_and_profile(self, client, tmp_path):
        """Register a CSV dataset via API and fetch its profile."""
        csv_file = tmp_path / "test_api_data.csv"
        csv_file.write_text("id,val,category\n1,10.5,A\n2,20.0,B\n3,30.5,A\n")

        async with client as c:
            reg_resp = await c.post(
                "/api/v1/datasets/register",
                json={
                    "name": "api_test_dataset",
                    "file_path": str(csv_file),
                    "description": "API Test",
                },
            )
            assert reg_resp.status_code == 200
            reg_data = reg_resp.json()
            assert reg_data["status"] == "success"
            ds_id = reg_data["dataset"]["id"]
            assert reg_data["profile"]["dataset_stats"]["row_count"] == 3

            # Fetch dataset profile
            prof_resp = await c.get(f"/api/v1/datasets/{ds_id}/profile")
            assert prof_resp.status_code == 200
            prof_data = prof_resp.json()
            assert prof_data["status"] == "success"
            assert prof_data["profile"]["dataset_stats"]["row_count"] == 3

            # List datasets
            list_resp = await c.get("/api/v1/datasets")
            assert list_resp.status_code == 200
            list_data = list_resp.json()
            assert list_data["total"] == 1
            assert list_data["datasets"][0]["name"] == "api_test_dataset"
