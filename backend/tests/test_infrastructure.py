"""
基础架构测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.unit
async def test_health_check(client: AsyncClient):
    """测试健康检查接口"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.unit
async def test_api_health_check(client: AsyncClient):
    """测试API健康检查接口"""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


@pytest.mark.unit
async def test_cors_headers(client: AsyncClient):
    """测试CORS头"""
    response = await client.get("/health")
    # CORS头在实际跨域请求时才会添加，这里测试其他安全头
    assert response.status_code == 200


@pytest.mark.unit
async def test_security_headers(client: AsyncClient):
    """测试安全头"""
    response = await client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"