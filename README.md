# m2-api-base

API REST de usuarios usada como base en el **Módulo 2 · Clase 1 — Generación de código con IA**.

Es un proyecto pequeño pero completo: tiene convenciones, capas separadas, catálogo
de errores y una suite de tests que pasa. Le falta **una** feature — la que vas a
construir en el laboratorio.

## Requisitos

- Python 3.10 o superior
- (Recomendado) Claude Code instalado

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
uvicorn main:app --reload          # http://127.0.0.1:8000  ·  Swagger en /docs
```

Endpoints actuales:

| Método | Ruta              | Descripción                     |
|--------|-------------------|---------------------------------|
| GET    | `/health`         | Estado del servicio             |
| GET    | `/users`          | Lista de usuarios               |
| GET    | `/users/{id}`     | Un usuario por id (404 si no existe) |
| POST   | `/users`          | Crea un usuario (409 si el email ya existe) |
| GET    | `/tasks`          | Lista las tareas en orden de creación; `?assignee_id=<id>` filtra por usuario (404 si no existe, 422 si es ≤ 0) |
| GET    | `/tasks/{id}`     | Una tarea por id (404 si no existe, 422 si el id es ≤ 0) |
| POST   | `/tasks`          | Crea una tarea (201); header opcional `Idempotency-Key` para reintentos seguros |

## Recurso `tasks`

Tareas operativas del equipo, opcionalmente asignadas a un usuario existente. Los
datos viven en memoria (se pierden al reiniciar) y no hay tareas de ejemplo. La
fuente de verdad, con los criterios de aceptación CA-01 a CA-42, es
[`docs/especificacion-tasks.md`](docs/especificacion-tasks.md).

### Reglas de validación (`POST /tasks`)

| Campo         | Obligatorio | Regla |
|---------------|-------------|-------|
| `title`       | Sí          | Se recortan los espacios; entre 3 y 120 caracteres después del recorte. |
| `description` | No          | Se recorta; máximo 1000 caracteres. Vacía o de solo espacios se guarda como `null`. |
| `due_date`    | Sí          | Texto `YYYY-MM-DD` exacto (no se aceptan timestamps ni fechas con hora). Hoy o posterior; "hoy" se calcula en `America/Mexico_City`. |
| `priority`    | No          | Entero de 1 a 5, por defecto `3`. No se aceptan booleanos ni texto. |
| `assignee_id` | No          | Entero mayor que 0 de un usuario existente. No se aceptan booleanos ni texto. |

Los campos desconocidos se ignoran. La respuesta incluye además `id` (autoincremental
desde 1) y `created_at` (UTC).

### Códigos de respuesta

| Código | Cuándo |
|--------|--------|
| 201    | Tarea creada, o reintento idempotente (devuelve la tarea original). |
| 404    | `assignee_id` no corresponde a ningún usuario (en `POST /tasks` y en `GET /tasks?assignee_id=`), o la tarea de `GET /tasks/{id}` no existe. Mensaje: `No se encontró <recurso>: <id>`. |
| 409    | La `Idempotency-Key` ya se usó con un cuerpo distinto. |
| 422    | Formato inválido (título, `due_date`, prioridad, ids ≤ 0 o de tipo incorrecto) o fecha límite en el pasado. El `detail` es una lista de errores de Pydantic si falla el formato, y un texto si falla una regla de dominio. |

Orden de las comprobaciones en `POST /tasks`: formato (422) → `Idempotency-Key`
(201 repetido o 409) → fecha pasada (422) → asignado inexistente (404).

### `Idempotency-Key`

Header opcional para reintentar un `POST /tasks` sin duplicar la tarea.

- Misma clave y mismo cuerpo → 201 con la misma tarea (mismo `id` y `created_at`).
  "Mismo cuerpo" se decide tras normalizar: omitir `priority` equivale a `priority: 3`,
  y un título con espacios sobrantes equivale al recortado.
- Misma clave y cuerpo distinto → 409.
- La clave es global (no se asocia a un cliente), y una clave vacía o de solo espacios
  se trata como ausente.
- Solo se registran las peticiones que terminan en 201: un 404 o un 422 no consume la
  clave.
- Un reintento con la misma clave devuelve la tarea original aunque `due_date` ya haya
  vencido (comportamiento intencional).

### Ejemplos

Con la API en `http://127.0.0.1:8000` (los usuarios 1 a 4 existen de inicio).

**curl:**

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: revisar-logs-001" \
  -d '{"title": "Revisar logs", "due_date": "2030-12-31", "priority": 4, "assignee_id": 1}'

curl http://127.0.0.1:8000/tasks
curl "http://127.0.0.1:8000/tasks?assignee_id=1"
curl http://127.0.0.1:8000/tasks/1
```

**PowerShell:**

```powershell
$body = @{ title = "Revisar logs"; due_date = "2030-12-31"; priority = 4; assignee_id = 1 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/tasks `
  -ContentType "application/json" -Headers @{ "Idempotency-Key" = "revisar-logs-001" } -Body $body

Invoke-RestMethod http://127.0.0.1:8000/tasks
Invoke-RestMethod "http://127.0.0.1:8000/tasks?assignee_id=1"
Invoke-RestMethod http://127.0.0.1:8000/tasks/1
```

Respuesta (201):

```json
{
  "title": "Revisar logs",
  "description": null,
  "due_date": "2030-12-31",
  "priority": 4,
  "assignee_id": 1,
  "id": 1,
  "created_at": "2026-10-25T15:04:05.123456Z"
}
```

Respuesta 404 (usuario inexistente) y 409 (clave reusada con otro cuerpo):

```json
{ "detail": "No se encontró usuario: 999" }
{ "detail": "La clave de idempotencia ya se usó con un cuerpo distinto" }
```

En PowerShell, `Invoke-RestMethod` lanza una excepción con los códigos 4xx; el
cuerpo del error está en `$_.ErrorDetails.Message`. Las fechas de los ejemplos deben
ser de hoy o posteriores: ajústalas si ya pasaron.

## Tests y calidad

```bash
pytest                                       # correr la suite
pytest --cov=. --cov-report=term-missing     # con cobertura
ruff check .                                 # linter
```

### Mutation testing con Cosmic Ray (Windows)

Mide si los tests detectan cambios en el código de `tasks/`. Los mutantes se aplican
**sobre los archivos en disco**: haz commit (o copia `tasks/`) antes de empezar.

Requisitos: entorno virtual activo y su carpeta `.venv\Scripts` en el `PATH`. El
`test-command` usa `pytest` a secas y no `python -m pytest`, porque en Windows
`CreateProcess` busca `python` junto al proceso padre real (el Python base, sin las
dependencias) antes que en el `PATH`. Detalles en `cosmic-ray.toml`.

```powershell
.venv\Scripts\activate
cosmic-ray baseline cosmic-ray.toml                        # la suite debe pasar sin mutar
cosmic-ray init cosmic-ray.toml cosmic-ray.sqlite          # genera los mutantes
cr-filter-operators cosmic-ray.sqlite cosmic-ray.toml      # omite los de `|` (equivalentes)
cosmic-ray exec cosmic-ray.toml cosmic-ray.sqlite          # los ejecuta
cr-report cosmic-ray.sqlite --show-pending                 # resumen en consola
cr-html cosmic-ray.sqlite | Out-File -Encoding utf8 cosmic-ray-report.html   # reporte navegable
```

Para el reporte HTML usa `Out-File -Encoding utf8` y no `>`: en Windows PowerShell 5.1
`>` guarda en UTF-16 y el navegador muestra el texto roto.

- Los resultados quedan en `cosmic-ray.sqlite` (sesión) y `cosmic-ray-report.html`
  (reporte), ambos en la raíz del proyecto y fuera de git. Para empezar de cero,
  borra el `.sqlite` antes de `init`.
- Los reportes del reto están en `docs/mutacion/`: `reporte-inicial.html` (primera
  corrida), `reporte-final.html` (tras corregir los supervivientes) y
  `reporte-refactor.html` (tras refactorizar `tasks/`).
- Último resultado: 205 mutantes, 121 omitidos por el filtro, 84 ejecutados, 82
  muertos y 2 supervivientes. Los dos son equivalentes (quitar `@classmethod` de un
  validador de Pydantic no cambia nada).

## Estructura del proyecto (onboarding)

```
main.py            app FastAPI; monta los routers
core/errors.py     catálogo de errores (not_found, invalid_request, already_exists, conflict)
users/             recurso de ejemplo: routes · service · schemas · repository
tasks/             recurso de tareas, mismo patrón
tests/             un archivo por recurso (test_users.py, test_tasks.py) y conftest.py
docs/              especificación y bitácoras
```

Cada recurso sigue el mismo patrón: las rutas delegan en `service.py` (la lógica y
los errores), que es la única capa que habla con `repository.py` (un `dict` en memoria).

Para empezar a leer:

- [`CLAUDE.md`](CLAUDE.md) — convenciones del proyecto y reglas del recurso `tasks`.
- [`docs/especificacion-tasks.md`](docs/especificacion-tasks.md) — campos, endpoints y
  criterios de aceptación CA-01 a CA-42.
- [`docs/bitacora.md`](docs/bitacora.md) — decisiones, resultados y evidencia del
  proceso.
- [`CHANGELOG.md`](CHANGELOG.md) — cambios por versión.

## Ramas del módulo

`main` es la base de la **Clase 1**. Cada clase tiene su rama de trabajo y su
rama de solución:

| Clase | Rama de trabajo | Solución | Qué añade |
|-------|-----------------|----------|-----------|
| 1 · Generación | `main` | `solucion-clase1` | La base. Falta `GET /users/search`. |
| 2 · Testing | `clase2-testing` | `solucion-clase2` | `users/validation.py` sin tests → llévalo a >80%. |
| 3 · Debugging | `clase3-debugging` | `solucion-clase3` | Recurso `reports/` con 3 bugs plantados. |
| 4 · Review | `clase4-review` | `solucion-clase4` | PR de `GET /reports/export` con issues (verde). |

```bash
git switch clase2-testing     # o la que toque
```

## Tarea del laboratorio (Clase 1)

Añadir `GET /users/search?email=<email>`:

- **200** con el usuario si existe
- **422** si el formato del email es inválido
- **404** si no hay ningún usuario con ese email
- con su test en `tests/test_users.py`, siguiendo el estilo del archivo

Lee `CLAUDE.md` antes de empezar: ahí están las convenciones que tu código debe respetar.
