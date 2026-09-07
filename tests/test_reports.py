"""Tests del recurso `reports`."""
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from reports import repository as reports_repository


def _payload(user_id: int = 1, title: str = "Incidencia", body: str = "algo pasó") -> dict:
    return {"user_id": user_id, "title": title, "body": body}


def test_create_report_devuelve_201(client: TestClient) -> None:
    response = client.post("/reports", json=_payload())

    assert response.status_code == 201
    assert response.json()["title"] == "Incidencia"


def test_create_report_body_muy_largo_devuelve_422(client: TestClient) -> None:
    response = client.post("/reports", json=_payload(body="x" * 600))

    assert response.status_code == 422


def test_get_report_inexistente_devuelve_404(client: TestClient) -> None:
    response = client.get("/reports/999")

    assert response.status_code == 404


def test_list_reports_filtra_por_user_id(client: TestClient) -> None:
    client.post("/reports", json=_payload(user_id=1, title="de user 1"))
    client.post("/reports", json=_payload(user_id=2, title="de user 2"))

    response = client.get("/reports", params={"user_id": 1})

    assert response.status_code == 200
    cuerpos = response.json()
    assert len(cuerpos) == 1
    assert cuerpos[0]["user_id"] == 1


def test_ids_unicos_bajo_concurrencia() -> None:
    """Crear 30 reportes en paralelo debe producir 30 ids distintos."""
    reports_repository.reset()
    n = 30

    with ThreadPoolExecutor(max_workers=n) as pool:
        futuros = [
            pool.submit(reports_repository.add, user_id=1, title=f"r{i}", body="")
            for i in range(n)
        ]
        creados = [f.result() for f in futuros]

    ids = {r.id for r in creados}
    assert len(ids) == n, f"se esperaban {n} ids únicos, hubo {n - len(ids)} colisiones"
