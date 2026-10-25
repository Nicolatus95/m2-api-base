# API de usuarios — guía del proyecto

API REST de ejemplo (FastAPI + Pydantic v2). Almacén en memoria, sin base de datos:
el proyecto corre sin infraestructura.

## Estructura

- `main.py` — crea la app y monta los routers.
- `users/` — recurso de ejemplo. Cada recurso sigue el mismo patrón:
  - `routes.py` — rutas HTTP. Sin lógica de negocio: delega en `service.py`.
  - `service.py` — lógica de negocio. Única capa que habla con `repository.py`.
  - `schemas.py` — modelos Pydantic de entrada (`*Create`) y salida.
  - `repository.py` — acceso a datos (aquí, un `dict` en memoria).
- `core/errors.py` — catálogo de errores. Toda respuesta de error sale de aquí.
- `tests/` — un archivo por recurso: `test_<recurso>.py`.

## Convenciones

- Las rutas declaran `response_model=` y devuelven modelos Pydantic, nunca `dict` crudos.
- Los errores se levantan con las funciones de `core/errors.py`
  (`not_found`, `invalid_request`, `already_exists`), no con `HTTPException` a mano.
- La ruta delega en `service.py`; la lógica y las decisiones de error viven ahí.
- Los 404 usan el mensaje neutro "No se encontró <recurso>: <id>" (vía
  `errors.not_found`), para concordar con recursos en masculino y femenino.
- Identificadores en inglés y `snake_case`, sin abreviaturas. Mensajes de error en español.
- Cada endpoint nuevo lleva su test en el archivo del recurso, con al menos un caso
  feliz y un caso de error.
- Rutas específicas antes que rutas con parámetro: `/users/search` debe declararse
  **antes** de `/users/{user_id}`.

## Recurso `tasks/`

Fuente de verdad: `docs/especificacion-tasks.md` (campos, endpoints y criterios de
aceptación CA-xx). Sigue el mismo patrón que `users/`.

- Validación de formato (longitudes, rangos, tipos, recorte de espacios) en
  `schemas.py`; reglas de dominio (fecha pasada, asignado inexistente, conflicto de
  idempotencia) en `service.py`. La fecha pasada nunca se valida en el schema.
- `title` y `description` se recortan; una `description` vacía se guarda como `null`.
  Las longitudes se miden después del recorte.
- `priority` y `assignee_id` llevan `strict=True` (rechazan booleanos y texto).
  `due_date` no: se acepta en modo laxo (ver "Limitaciones conocidas" de la
  especificación).
- Ids ≤ 0 son datos mal formados (422, no 404): `Field(gt=0)` en `assignee_id`,
  `Path(gt=0)` en `task_id` y `Query(gt=0)` en el filtro de `GET /tasks`. Los
  parámetros de ruta y de consulta no llevan `strict`.
- "Hoy" se calcula en `America/Mexico_City` (`BUSINESS_TIMEZONE`, constante del módulo
  con `zoneinfo`; en Windows exige `tzdata`, que está en `requirements.txt`).
  `local_date(instant)` es una función pura que convierte un instante a esa zona;
  `current_date()` devuelve `local_date(datetime.now(timezone.utc))` y es la única vía
  para obtener "hoy". La lógica nunca llama `date.today()` ni `datetime.now()`, y nadie
  importa `current_date` con `from tasks.service import ...`.
- Orden en `POST /tasks`: formato (422), `Idempotency-Key` (201 repetido o 409), fecha
  pasada (422), asignado inexistente (404).
- `Idempotency-Key`: clave global; vacía o de solo espacios cuenta como ausente. Se
  compara el cuerpo normalizado. Solo se registran las peticiones con 201. Un
  reintento con la misma clave devuelve la respuesta original aunque `due_date` ya
  haya vencido (intencional).
- `tasks/service.py` consulta usuarios con `users.service`, nunca con `users.repository`.
- El 409 de idempotencia se levanta con `errors.conflict(message)`; no se usa
  `HTTPException` directamente.
- `not_found` pasa a un mensaje neutro, "No se encontró <recurso>: <id>", para todos
  los recursos (cambio transversal que también afecta a `users` y a `test_users.py`).
- Los listados salen en orden de creación (`id` ascendente).
- `tasks/repository.py` guarda las tareas **y** el registro de claves de idempotencia,
  sin datos semilla. `reset()` deja ambos vacíos y `_next_id` en 1.
  `tests/conftest.py` llama los dos `reset()` en su fixture, importando los
  repositorios con alias (`user_repository`, `task_repository`).
- Los tests van en `tests/test_tasks.py`, con el estilo de `test_users.py`. Cada test
  menciona en su docstring el criterio (CA-xx) que cubre. "Hoy" se fija con una
  fixture autouse `today` (`monkeypatch` sobre `tasks.service.current_date`) y los
  cuerpos se arman con `valid_payload(**changes)`; nunca `date.today()` ni fechas fijas.

## Cómo ejecutar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn main:app --reload          # API en http://127.0.0.1:8000  ·  /docs para el Swagger
pytest                             # tests
pytest --cov=. --cov-report=term-missing   # cobertura
ruff check .                       # linter
```

## Fuera de límites

- `migrations/` y `legacy/` — no modificar.
