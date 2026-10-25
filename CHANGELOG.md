# Changelog

Todos los cambios relevantes del proyecto se documentan aquí. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[versionado semántico](https://semver.org/lang/es/).

## [0.2.0] - 2026-10-25

### Añadido

- Recurso `tasks`: `POST /tasks`, `GET /tasks/{id}` y `GET /tasks` (con filtro
  `?assignee_id=`). Almacén en memoria, sin datos de ejemplo.
- Soporte de idempotencia en `POST /tasks` con el header opcional `Idempotency-Key`.
- Respuesta 409 para una clave de idempotencia reusada con otro cuerpo
  (`core.errors.conflict`).
- Fecha límite validada contra "hoy" en la zona `America/Mexico_City` (dependencia
  `tzdata`).
- Especificación `docs/especificacion-tasks.md` con los criterios CA-01 a CA-42, y su
  suite en `tests/test_tasks.py` (pruebas de API, unitarias de `tasks/` e integración
  con `users`).
- `due_date` solo acepta texto con formato exacto `YYYY-MM-DD`: se rechazan los
  timestamps Unix (número o texto) y las fechas con hora (422).
- Mutation testing con Cosmic Ray sobre `tasks/` (`cosmic-ray.toml`).
- Ejemplo de cuerpo válido de `TaskCreate` en Swagger, descripciones de las rutas de
  `tasks` y documentación de uso en el README.

### Cambiado

- **El mensaje de 404 cambia para todos los recursos**: de `<recurso> no encontrado: <id>`
  a `No se encontró <recurso>: <id>`. Es visible para quien consume la API; por ejemplo,
  `GET /users/999` ahora responde `{"detail": "No se encontró usuario: 999"}`.
  Quien compare ese texto debe actualizarse.
- Título de la API: "API de usuarios y tareas".

### Deuda técnica conocida

- `tasks.repository.add` repite los campos de la tarea (`title`, `description`,
  `due_date`, `priority`, `assignee_id`) en su firma, y el servicio lo llama con
  `**data.model_dump()`. Añadir un campo exige tocar `TaskBase`, `add` y la
  construcción de `Task`. Se dejó así para mantener la simetría con
  `users.repository.add`; la alternativa es `add(data: TaskCreate)`.
- Las claves de idempotencia son globales, no caducan y su comprobación no es atómica
  (ver "Limitaciones conocidas" en la especificación).
- El filtro de Cosmic Ray oculta también los mutantes de `|` en las anotaciones de
  `routes.py`, que FastAPI sí evalúa (ver `cosmic-ray.toml`).

## [0.1.0]

- API de usuarios base: `GET /health`, `GET /users`, `GET /users/{id}` y `POST /users`.
