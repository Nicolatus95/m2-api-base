# Bitácora automática de prompts

Generada por los hooks de Claude Code (`.claude/hooks/registrar_bitacora.py`).
No editar a mano: las notas y decisiones van en `docs/bitacora.md`.

---

## 2026-10-24 20:06:09 · Prompt

```text
Lee CLAUDE.md y resúmeme las convenciones del proyecto
```

### 2026-10-24 20:06:15 · Respuesta

Resumen de las convenciones de `CLAUDE.md` (el contenido ya venía cargado en el contexto, así que no hizo falta abrir el archivo).

## Arquitectura por capas
Cada recurso (por ejemplo `users/`) sigue el mismo patrón:
- **`routes.py`**: solo rutas HTTP, sin lógica de negocio. Delega en `service.py`.
- **`service.py`**: la lógica de negocio y las decisiones de error. Es la única capa que habla con `repository.py`.
- **`schemas.py`**: modelos Pydantic de entrada (`*Create`) y de salida.
- **`repository.py`**: acceso a datos, aquí un `dict` en memoria.

## Reglas de código
- Las rutas declaran `response_model=` y devuelven modelos Pydantic, nunca `dict` crudos.
- Los errores se levantan con `not_found`, `invalid_request` o `already_exists` de `core/errors.py`, nunca con `HTTPException` a mano.
- Los identificadores van en inglés y en `snake_case`, sin abreviaturas.
- Los mensajes de error van en español.
- Las rutas específicas se declaran antes que las que llevan parámetro. Por ejemplo, `/users/search` va **antes** de `/users/{user_id}`.

## Tests
- Hay un archivo por recurso: `tests/test_<recurso>.py`.
- Cada endpoint nuevo lleva su test, con al menos un caso feliz y un caso de error.

## Comandos
- `uvicorn main:app --reload` levanta la API en `http://127.0.0.1:8000`. `/docs` abre el Swagger.
- `pytest` corre los tests. Con `--cov=. --cov-report=term-missing` mide la cobertura.
- `ruff check .` ejecuta el linter.

## Fuera de límites
- No se modifican `migrations/` ni `legacy/`.

El proyecto no usa base de datos y corre sin infraestructura.
