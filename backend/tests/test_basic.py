import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient


def test_pytest_works():
    """Test that pytest is working."""
    assert True


@pytest.mark.asyncio
async def test_database_fixture(test_db: AsyncSession):
    """Test that database fixture works."""
    assert test_db is not None
    result = await test_db.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_client_fixture(client: AsyncClient):
    """Test that client fixture works."""
    assert client is not None
    response = await client.get("/health")
    response = await client.get("/docs")
    assert response.status_code in [200, 404]
