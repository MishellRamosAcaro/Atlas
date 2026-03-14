"""API tests for auth endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client. Note: endpoints requiring DB need PostgreSQL running."""
    return TestClient(app)


def test_auth_router_mount(client: TestClient):
    """Auth router is mounted; token and register routes exist."""
    # 405 Method Not Allowed for GET on POST-only routes indicates route exists
    response = client.get("/auth/register")
    assert response.status_code == 405
    response = client.get("/auth/token")
    assert response.status_code == 405
