"""Tests del PR que añade la exportación de reportes.

Están en verde: el PR "funciona". El ejercicio de la Clase 4 es revisarlo y
decidir si se merge así (no).
"""
from fastapi.testclient import TestClient

from reports.export import EXPORT_API_TOKEN


def test_export_con_token_valido_devuelve_ruta(client: TestClient) -> None:
    client.post("/reports", json={"user_id": 1, "title": "Incidencia", "body": "x"})

    response = client.get("/reports/export", params={"token": EXPORT_API_TOKEN})

    assert response.status_code == 200
    assert "ruta" in response.json()


def test_export_sin_token_devuelve_error(client: TestClient) -> None:
    response = client.get("/reports/export")

    assert response.status_code == 200
    assert "error" in response.json()
