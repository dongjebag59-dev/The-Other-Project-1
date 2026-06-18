"""테스트 공통 fixture."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient를 반환합니다."""
    return TestClient(app)
