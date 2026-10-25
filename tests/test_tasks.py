"""Tests del recurso `tasks`.

Fuente de verdad: docs/especificacion-tasks.md (criterios CA-01 a CA-41).
Mismo estilo que test_users.py, con estas diferencias:
  - el docstring de cada test lleva el criterio (CA-xx) que cubre
  - "hoy" está fijado por la fixture autouse `today`; nunca se usa `date.today()`
  - los cuerpos se arman con `valid_payload(**changes)`
  - `tasks` no se importa a nivel de módulo: se importa dentro de la fixture o del test

Secciones: API (CA-01 a CA-41), unitarios de `tasks/service.py` con dependencias
simuladas e integración con `users`. Los unitarios y la integración no tienen un CA
propio: su docstring indica los CA con los que se relacionan.
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

FIXED_TODAY = date(2026, 10, 24)


class Clock:
    """Fecha de "hoy" que ve el servicio. Se puede avanzar dentro de un test."""

    def __init__(self, value: date) -> None:
        self.value = value

    def advance(self, days: int) -> None:
        self.value += timedelta(days=days)


_clock = Clock(FIXED_TODAY)


@pytest.fixture(autouse=True)
def today(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Fija "hoy" en 2026-10-24 sustituyendo `current_date` del servicio."""
    from tasks import service

    _clock.value = FIXED_TODAY
    monkeypatch.setattr(service, "current_date", lambda: _clock.value)
    return _clock


def valid_payload(**changes: object) -> dict[str, object]:
    """Cuerpo válido mínimo; las fechas salen de la fecha fijada por `today`."""
    payload: dict[str, object] = {
        "title": "Revisar logs",
        "due_date": (_clock.value + timedelta(days=1)).isoformat(),
    }
    payload.update(changes)
    return payload


def past_date() -> str:
    return (_clock.value - timedelta(days=1)).isoformat()


def post_task(
    client: TestClient, payload: dict[str, object], key: str | None = None
):
    headers = {} if key is None else {"Idempotency-Key": key}
    return client.post("/tasks", json=payload, headers=headers)


# --- Creación ---------------------------------------------------------------


def test_create_task_solo_obligatorios_devuelve_201_y_valores_por_defecto(
    client: TestClient,
) -> None:
    """CA-01: crear con solo los campos obligatorios."""
    response = client.post("/tasks", json=valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert "created_at" in body
    assert body["priority"] == 3
    assert body["description"] is None
    assert body["assignee_id"] is None


def test_create_task_con_todos_los_campos_devuelve_201_y_los_normaliza(
    client: TestClient,
) -> None:
    """CA-02: crear con todos los campos."""
    payload = valid_payload(
        title="  Revisar logs  ",
        description="Detalle",
        priority=5,
        assignee_id=1,
    )

    response = client.post("/tasks", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Revisar logs"
    assert body["description"] == "Detalle"
    assert body["due_date"] == payload["due_date"]
    assert body["priority"] == 5
    assert body["assignee_id"] == 1
    assert "id" in body
    assert "created_at" in body


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "abc"},
        {"title": "a" * 120},
        {"title": "  " + "a" * 120 + "  "},
        {"priority": 1},
        {"priority": 5},
        {"description": "a" * 1000},
    ],
    ids=[
        "titulo_3",
        "titulo_120",
        "titulo_120_con_espacios",
        "priority_1",
        "priority_5",
        "description_1000",
    ],
)
def test_create_task_valores_en_los_limites_devuelve_201(
    client: TestClient, changes: dict[str, object]
) -> None:
    """CA-03: valores en los límites."""
    response = client.post("/tasks", json=valid_payload(**changes))

    assert response.status_code == 201


def test_create_task_titulo_de_solo_espacios_devuelve_422(
    client: TestClient,
) -> None:
    """CA-04: título de solo espacios."""
    response = client.post("/tasks", json=valid_payload(title="     "))

    assert response.status_code == 422


def test_create_task_titulo_demasiado_corto_devuelve_422(
    client: TestClient,
) -> None:
    """CA-05: título demasiado corto."""
    response = client.post("/tasks", json=valid_payload(title="ab"))

    assert response.status_code == 422


def test_create_task_titulo_corto_tras_recortar_devuelve_422(
    client: TestClient,
) -> None:
    """CA-06: título corto tras recortar."""
    response = client.post("/tasks", json=valid_payload(title="  ab  "))

    assert response.status_code == 422


def test_create_task_titulo_demasiado_largo_devuelve_422(
    client: TestClient,
) -> None:
    """CA-07: título demasiado largo."""
    response = client.post("/tasks", json=valid_payload(title="a" * 121))

    assert response.status_code == 422


def test_create_task_descripcion_demasiado_larga_devuelve_422(
    client: TestClient,
) -> None:
    """CA-08: descripción demasiado larga."""
    response = client.post("/tasks", json=valid_payload(description="a" * 1001))

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("description", "expected"),
    [("  Detalle  ", "Detalle"), ("", None), ("   ", None)],
    ids=["recorta_espacios", "vacia_a_null", "solo_espacios_a_null"],
)
def test_create_task_descripcion_se_normaliza(
    client: TestClient, description: str, expected: str | None
) -> None:
    """CA-09: descripción normalizada."""
    response = client.post("/tasks", json=valid_payload(description=description))

    assert response.status_code == 201
    assert response.json()["description"] == expected


def test_create_task_sin_due_date_devuelve_422(client: TestClient) -> None:
    """CA-10: falta `due_date`."""
    response = client.post("/tasks", json={"title": "Revisar logs"})

    assert response.status_code == 422


def test_create_task_due_date_con_formato_invalido_devuelve_422(
    client: TestClient,
) -> None:
    """CA-11: `due_date` con formato inválido."""
    response = client.post("/tasks", json=valid_payload(due_date="24/10/2026"))

    assert response.status_code == 422


def test_create_task_due_date_en_el_pasado_devuelve_422(
    client: TestClient,
) -> None:
    """CA-12: `due_date` en el pasado."""
    response = client.post("/tasks", json=valid_payload(due_date=past_date()))

    assert response.status_code == 422
    # Error de dominio (mensaje de texto), no de formato (lista de Pydantic).
    assert isinstance(response.json()["detail"], str)


def test_create_task_due_date_de_hoy_devuelve_201(client: TestClient) -> None:
    """CA-13: `due_date` de hoy."""
    payload = valid_payload(due_date=_clock.value.isoformat())

    response = client.post("/tasks", json=payload)

    assert response.status_code == 201


def test_local_date_usa_la_zona_america_mexico_city() -> None:
    """CA-14: "hoy" se calcula en `America/Mexico_City`."""
    from tasks.service import local_date

    instant = datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc)

    assert local_date(instant) == date(2026, 10, 24)


def test_create_task_prioridad_por_debajo_del_rango_devuelve_422(
    client: TestClient,
) -> None:
    """CA-15: prioridad por debajo del rango."""
    response = client.post("/tasks", json=valid_payload(priority=0))

    assert response.status_code == 422


def test_create_task_prioridad_por_encima_del_rango_devuelve_422(
    client: TestClient,
) -> None:
    """CA-16: prioridad por encima del rango."""
    response = client.post("/tasks", json=valid_payload(priority=6))

    assert response.status_code == 422


def test_create_task_prioridad_booleana_devuelve_422(client: TestClient) -> None:
    """CA-17: prioridad booleana."""
    response = client.post("/tasks", json=valid_payload(priority=True))

    assert response.status_code == 422


def test_create_task_asignado_inexistente_devuelve_404(client: TestClient) -> None:
    """CA-18: asignado inexistente."""
    response = client.post("/tasks", json=valid_payload(assignee_id=999))

    assert response.status_code == 404
    assert response.json()["detail"] == "No se encontró usuario: 999"


@pytest.mark.parametrize("assignee_id", [0, -1])
def test_create_task_asignado_con_id_no_positivo_devuelve_422(
    client: TestClient, assignee_id: int
) -> None:
    """CA-19: asignado con id no positivo."""
    response = client.post("/tasks", json=valid_payload(assignee_id=assignee_id))

    assert response.status_code == 422


def test_create_task_asignado_booleano_devuelve_422(client: TestClient) -> None:
    """CA-20: asignado booleano (no se asigna al usuario 1)."""
    response = client.post("/tasks", json=valid_payload(assignee_id=True))

    assert response.status_code == 422


def test_create_task_fecha_pasada_y_asignado_inexistente_gana_la_fecha(
    client: TestClient,
) -> None:
    """CA-21: fecha pasada y asignado inexistente: 422, la fecha va primero."""
    payload = valid_payload(due_date=past_date(), assignee_id=999)

    response = client.post("/tasks", json=payload)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


# --- Idempotencia -----------------------------------------------------------


def test_idempotencia_misma_clave_y_mismo_cuerpo_devuelve_la_misma_tarea(
    client: TestClient,
) -> None:
    """CA-22: misma clave y mismo cuerpo."""
    payload = valid_payload()

    first = post_task(client, payload, key="k1")
    second = post_task(client, payload, key="k1")

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["created_at"] == first.json()["created_at"]
    assert len(client.get("/tasks").json()) == 1


def test_idempotencia_misma_clave_y_cuerpo_distinto_devuelve_409(
    client: TestClient,
) -> None:
    """CA-23: misma clave y cuerpo distinto."""
    first = post_task(client, valid_payload(), key="k1")

    second = post_task(client, valid_payload(title="Otro título"), key="k1")

    assert first.status_code == 201
    assert second.status_code == 409
    assert (
        second.json()["detail"]
        == "La clave de idempotencia ya se usó con un cuerpo distinto"
    )
    assert len(client.get("/tasks").json()) == 1


@pytest.mark.parametrize(
    ("first_changes", "second_changes"),
    [
        ({}, {"priority": 3}),
        ({"title": "  Revisar logs  "}, {"title": "Revisar logs"}),
        ({}, {"description": ""}),
        ({}, {"extra": 1}),
    ],
    ids=["priority_por_defecto", "titulo_recortado", "descripcion_vacia", "campo_extra"],
)
def test_idempotencia_cuerpo_equivalente_tras_normalizar_devuelve_la_misma_tarea(
    client: TestClient,
    first_changes: dict[str, object],
    second_changes: dict[str, object],
) -> None:
    """CA-24: cuerpo equivalente tras normalizar."""
    first = post_task(client, valid_payload(**first_changes), key="k1")

    second = post_task(client, valid_payload(**second_changes), key="k1")

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_idempotencia_fallo_de_dominio_no_consume_la_clave(
    client: TestClient,
) -> None:
    """CA-25: un fallo de dominio no consume la clave."""
    first = post_task(client, valid_payload(assignee_id=999), key="k1")

    second = post_task(client, valid_payload(assignee_id=1), key="k1")

    assert first.status_code == 404
    assert second.status_code == 201


def test_idempotencia_cuerpo_invalido_con_clave_usada_devuelve_422(
    client: TestClient,
) -> None:
    """CA-26: cuerpo inválido con una clave ya usada: 422, no 409."""
    post_task(client, valid_payload(), key="k1")

    response = post_task(client, valid_payload(priority=9), key="k1")

    assert response.status_code == 422


def test_idempotencia_clave_reusada_con_fecha_pasada_devuelve_409(
    client: TestClient,
) -> None:
    """CA-27: clave reusada, cuerpo nuevo con fecha pasada: 409."""
    post_task(client, valid_payload(), key="k1")
    payload = valid_payload(title="Otro título", due_date=past_date())

    response = post_task(client, payload, key="k1")

    assert response.status_code == 409


def test_idempotencia_clave_reusada_con_asignado_inexistente_devuelve_409(
    client: TestClient,
) -> None:
    """CA-28: clave reusada, cuerpo nuevo con asignado inexistente: 409."""
    post_task(client, valid_payload(), key="k1")
    payload = valid_payload(title="Otro título", assignee_id=999)

    response = post_task(client, payload, key="k1")

    assert response.status_code == 409


def test_idempotencia_reintento_tras_vencer_la_fecha_devuelve_la_original(
    client: TestClient, today: Clock
) -> None:
    """CA-29: reintento tras vencer la fecha (comportamiento intencional)."""
    payload = valid_payload(due_date=today.value.isoformat())
    first = post_task(client, payload, key="k1")

    today.advance(1)
    second = post_task(client, payload, key="k1")

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_idempotencia_claves_distintas_con_el_mismo_cuerpo_crean_dos_tareas(
    client: TestClient,
) -> None:
    """CA-30: claves distintas con el mismo cuerpo."""
    payload = valid_payload()

    first = post_task(client, payload, key="k1")
    second = post_task(client, payload, key="k2")

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]


def test_idempotencia_sin_clave_crea_dos_tareas(client: TestClient) -> None:
    """CA-31: sin clave, sin idempotencia."""
    payload = valid_payload()

    first = post_task(client, payload)
    second = post_task(client, payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]


@pytest.mark.parametrize("key", ["", "   "], ids=["vacia", "solo_espacios"])
def test_idempotencia_clave_vacia_se_trata_como_ausente(
    client: TestClient, key: str
) -> None:
    """CA-32: clave vacía o de solo espacios."""
    payload = valid_payload()

    first = post_task(client, payload, key=key)
    second = post_task(client, payload, key=key)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]


# --- Consulta ---------------------------------------------------------------


def test_get_task_existente_devuelve_200(client: TestClient) -> None:
    """CA-33: obtener tarea existente."""
    created = client.post("/tasks", json=valid_payload()).json()

    response = client.get(f"/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_task_inexistente_devuelve_404(client: TestClient) -> None:
    """CA-34: obtener tarea inexistente."""
    response = client.get("/tasks/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "No se encontró tarea: 999"


@pytest.mark.parametrize("task_id", [0, -1])
def test_get_task_con_id_no_positivo_devuelve_422(
    client: TestClient, task_id: int
) -> None:
    """CA-35: obtener con id no positivo."""
    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 422


def test_list_tasks_sin_tareas_devuelve_lista_vacia(client: TestClient) -> None:
    """CA-36: listar sin tareas."""
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_devuelve_las_tareas_en_orden_de_creacion(
    client: TestClient,
) -> None:
    """CA-37: listar con tareas."""
    client.post("/tasks", json=valid_payload(title="Primera tarea"))
    client.post("/tasks", json=valid_payload(title="Segunda tarea"))

    response = client.get("/tasks")

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [1, 2]


def test_list_tasks_filtra_por_usuario_con_tareas(client: TestClient) -> None:
    """CA-38: filtrar por usuario con tareas."""
    client.post("/tasks", json=valid_payload(assignee_id=1))
    client.post("/tasks", json=valid_payload(assignee_id=2))

    response = client.get("/tasks", params={"assignee_id": 1})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["assignee_id"] == 1


def test_list_tasks_filtra_por_usuario_sin_tareas_devuelve_lista_vacia(
    client: TestClient,
) -> None:
    """CA-39: filtrar por usuario sin tareas (otro usuario sí tiene)."""
    client.post("/tasks", json=valid_payload(assignee_id=1))

    response = client.get("/tasks", params={"assignee_id": 2})

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_filtra_por_usuario_inexistente_devuelve_404(
    client: TestClient,
) -> None:
    """CA-40: filtrar por usuario inexistente."""
    response = client.get("/tasks", params={"assignee_id": 999})

    assert response.status_code == 404
    assert response.json()["detail"] == "No se encontró usuario: 999"


@pytest.mark.parametrize("assignee_id", [0, -1])
def test_list_tasks_filtra_con_id_no_positivo_devuelve_422(
    client: TestClient, assignee_id: int
) -> None:
    """CA-41: filtrar con id no positivo."""
    response = client.get("/tasks", params={"assignee_id": assignee_id})

    assert response.status_code == 422


# --- Unitarios de tasks/service.py (dependencias simuladas) -----------------


@pytest.fixture
def get_user(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Simula `users.service.get_user`, la única vía de `tasks` hacia `users`."""
    from tasks import service

    mock = Mock()
    monkeypatch.setattr(service.users_service, "get_user", mock)
    return mock


@pytest.fixture
def add_spy(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Espía `repository.add` conservando su comportamiento real."""
    from tasks import service

    spy = Mock(wraps=service.repository.add)
    monkeypatch.setattr(service.repository, "add", spy)
    return spy


def task_create(**changes: object):
    from tasks.schemas import TaskCreate

    return TaskCreate(**valid_payload(**changes))


def test_service_create_task_sin_asignado_no_consulta_usuarios(
    get_user: Mock,
) -> None:
    """Unitario (CA-01): sin `assignee_id` no se llama a `get_user`."""
    from tasks import service

    service.create_task(task_create())

    get_user.assert_not_called()


def test_service_create_task_con_asignado_consulta_el_usuario_una_vez(
    get_user: Mock,
) -> None:
    """Unitario (CA-02, CA-18): con `assignee_id` se llama a `get_user` con ese id."""
    from tasks import service

    service.create_task(task_create(assignee_id=3))

    get_user.assert_called_once_with(3)


def test_service_create_task_con_fecha_pasada_no_consulta_usuarios_ni_guarda(
    get_user: Mock, add_spy: Mock
) -> None:
    """Unitario (CA-12, CA-21): la fecha pasada corta antes de `get_user` y `add`."""
    from tasks import service

    data = task_create(due_date=past_date(), assignee_id=1)

    with pytest.raises(HTTPException) as error:
        service.create_task(data)

    assert error.value.status_code == 422
    get_user.assert_not_called()
    add_spy.assert_not_called()


def test_service_create_task_reintento_con_la_misma_clave_no_vuelve_a_guardar(
    add_spy: Mock,
) -> None:
    """Unitario (CA-22): el reintento devuelve la tarea guardada sin llamar a `add`."""
    from tasks import service

    first = service.create_task(task_create(), "k1")
    second = service.create_task(task_create(), "k1")

    add_spy.assert_called_once()
    assert second == first


def test_current_date_devuelve_la_fecha_de_mexico_para_el_instante_actual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unitario (CA-14): `current_date()` devuelve la fecha local del instante actual."""
    from tasks import service

    monkeypatch.undo()  # quita el reloj falso de `today`: aquí se prueba la real
    fake_datetime = Mock()
    fake_datetime.now.return_value = datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(service, "datetime", fake_datetime)

    result = service.current_date()

    assert result == date(2026, 10, 24)


def test_repository_list_by_assignee_compara_ids_grandes_por_valor() -> None:
    """Unitario (CA-38): el filtro por asignado compara por valor, no por identidad.

    Los ids se generan en tiempo de ejecución (`int("1000")`): CPython reutiliza
    el mismo objeto solo para enteros pequeños, así que con ids como 1 o 2 una
    comparación por identidad pasaría inadvertida.
    """
    from tasks import repository

    for assignee_id in (int("1000"), int("1001")):
        repository.add(
            title="Revisar logs",
            description=None,
            due_date=FIXED_TODAY,
            priority=3,
            assignee_id=assignee_id,
        )

    result = repository.list_by_assignee(int("1000"))

    assert [task.assignee_id for task in result] == [1000]


# --- Integración entre recursos ---------------------------------------------


def test_integracion_usuario_creado_por_api_recibe_y_lista_su_tarea(
    client: TestClient,
) -> None:
    """Integración users ↔ tasks (relacionado con CA-02, CA-33 y CA-38).

    Integra los dos routers con sus repositorios reales y sin simulaciones:
    `POST /users` crea al usuario, `tasks` lo valida a través de `users.service`
    al asignarle una tarea, y la tarea se recupera por el filtro `assignee_id` y
    por su id.
    """
    user = client.post(
        "/users", json={"name": "Margaret Hamilton", "email": "margaret@example.com"}
    ).json()
    created = client.post("/tasks", json=valid_payload(assignee_id=user["id"])).json()

    listed = client.get("/tasks", params={"assignee_id": user["id"]})
    fetched = client.get(f"/tasks/{created['id']}")

    assert created["assignee_id"] == user["id"]
    assert listed.status_code == 200
    assert listed.json() == [created]
    assert fetched.status_code == 200
    assert fetched.json() == created
