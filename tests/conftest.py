"""Fixtures compartidas por la suite de tests."""
import pytest
from fastapi.testclient import TestClient

from main import app
from tasks import repository as task_repository
from users import repository as user_repository


@pytest.fixture(autouse=True)
def _reset_data():
    """Cada test arranca con los datos iniciales y no contamina a los demás.

    `users` vuelve a sus datos semilla; `tasks` vuelve vacío (sin semilla)."""
    user_repository.reset()
    task_repository.reset()
    yield
    user_repository.reset()
    task_repository.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
