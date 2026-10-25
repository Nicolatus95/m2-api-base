"""Fixtures compartidas por la suite de tests."""
import pytest
from fastapi.testclient import TestClient

from main import app
from tasks import repository as task_repository
from users import repository as user_repository


@pytest.fixture(autouse=True)
def _reset_data():
    """Cada test arranca con los datos semilla y no contamina a los demás."""
    user_repository.reset()
    task_repository.reset()
    yield
    user_repository.reset()
    task_repository.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
