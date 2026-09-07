"""Tests de la exportación de reportes (versión corregida tras el review)."""
import pytest
from fastapi.testclient import TestClient

_TOKEN = "token-de-prueba"


@pytest.fixture(autouse=True)
def _export_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EXPORT_API_TOKEN", _TOKEN)
    monkeypatch.setattr("reports.export._EXPORT_DIR", tmp_path)


def test_export_sin_token_devuelve_401(client: TestClient) -> None:
    response = client.get("/reports/export")

    assert response.status_code == 401


def test_export_token_incorrecto_devuelve_401(client: TestClient) -> None:
    response = client.get("/reports/export", headers={"X-Export-Token": "mal"})

    assert response.status_code == 401


def test_export_con_token_valido_devuelve_filename(client: TestClient) -> None:
    client.post("/reports", json={"user_id": 1, "title": "Incidencia", "body": "x"})

    response = client.get("/reports/export", headers={"X-Export-Token": _TOKEN})

    assert response.status_code == 200
    assert response.json() == {"filename": "reports.csv"}


def test_export_formato_no_soportado_devuelve_422(client: TestClient) -> None:
    response = client.get(
        "/reports/export", params={"fmt": "pdf"}, headers={"X-Export-Token": _TOKEN}
    )

    assert response.status_code == 422


def test_render_escapa_comas_del_titulo(client: TestClient) -> None:
    from reports.export import render

    client.post(
        "/reports", json={"user_id": 1, "title": "hola, mundo", "body": "x"}
    )

    salida = render("csv")

    assert '"hola, mundo"' in salida
