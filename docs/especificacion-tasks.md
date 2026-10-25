# Especificación del recurso `tasks`

## Objetivo

Registrar tareas operativas del equipo, opcionalmente asignadas a un usuario
existente, para reducir el trabajo no registrado y mejorar la trazabilidad.

## Alcance

**Incluye:**

- Crear una tarea (`POST /tasks`), con soporte opcional de idempotencia.
- Consultar una tarea por id (`GET /tasks/{task_id}`).
- Listar todas las tareas, o filtrarlas por usuario asignado (`GET /tasks`).

**No incluye** (fuera de este alcance): modificar, borrar o completar tareas, estados,
paginación y autenticación.

El recurso sigue el mismo patrón que `users/` (`routes.py`, `service.py`,
`schemas.py`, `repository.py`) y guarda los datos en memoria.

## Modelo de entrada: `TaskCreate`

| Campo         | Tipo     | Obligatorio | Regla                                                         | Si se incumple |
|---------------|----------|-------------|---------------------------------------------------------------|----------------|
| `title`       | `str`    | Sí          | Se recortan los espacios de los extremos y se guarda recortado. Después del recorte, entre 3 y 120 caracteres. Un título de solo espacios es inválido. | 422 |
| `description` | `str`    | No          | Se recortan los espacios de los extremos; si queda vacía (`""` o solo espacios) se guarda como `null`. Después del recorte, máximo 1000 caracteres. | 422 |
| `due_date`    | `date`   | Sí          | Solo texto con formato exacto `YYYY-MM-DD`: se rechazan números (timestamps Unix), texto numérico y fechas con hora. Hoy o posterior (ver "Fecha actual"). No lleva `strict=True`: FastAPI valida el cuerpo ya convertido en `dict` de Python, y en modo estricto un `date` rechaza también el texto `"2026-10-24"`. El formato lo exige un validador previo (`mode="before"`) en `TaskCreate`. | 422 |
| `priority`    | `int`    | No          | De 1 a 5. Por defecto `3`. `strict=True`: rechaza booleanos y texto (`true`, `"5"`). | 422 |
| `assignee_id` | `int`    | No          | Mayor que 0 (`gt=0`) y `strict=True` (rechaza booleanos y texto). Si se envía, el usuario debe existir. | 422 si es ≤ 0 o no es entero; 404 si no existe |

Los campos que no están en el modelo se ignoran (igual que en `users`).

## Modelo de salida: `Task`

Los campos de `TaskCreate` ya normalizados (título y descripción recortados,
`priority` resuelta, `description` y `assignee_id` en `null` si no se enviaron) más:

- `id` (`int`): autoincremental, empieza en 1.
- `created_at` (`datetime`, UTC): momento de creación.

## Endpoints

### `POST /tasks` → 201

Crea la tarea y devuelve la tarea creada (incluye `id` y `created_at`).

Header opcional `Idempotency-Key`:

- **Misma clave + mismo cuerpo** → 201 con la misma tarea (mismo `id` y mismo
  `created_at`), sin crear un duplicado.
- **Misma clave + cuerpo distinto** → 409.

Reglas de idempotencia:

- La clave es global para `POST /tasks`.
- Una clave vacía o de solo espacios se trata como ausente: la petición se procesa
  sin idempotencia.
- "Mismo cuerpo" se decide comparando el cuerpo **ya validado y normalizado**. Son
  equivalentes, por ejemplo: omitir `priority` y enviar `priority: 3`; un título con
  espacios sobrantes y el mismo título recortado; omitir `description` y enviar
  `""`; enviar o no un campo que no está en el modelo.
- Solo se registran las peticiones que terminan en 201. Una petición que falla
  (422, 404) no consume la clave.
- La búsqueda de la clave ocurre **antes** de las reglas de dominio (fecha pasada,
  asignado inexistente). **Es un comportamiento intencional:** un reintento con la
  misma clave devuelve la respuesta original aunque `due_date` ya haya vencido.

### `GET /tasks/{task_id}` → 200

Devuelve la tarea. 404 si no existe. El parámetro se declara con `Path(gt=0)`: un
valor ≤ 0 es un dato mal formado y da 422.

### `GET /tasks` → 200

Devuelve todas las tareas en orden de creación (`id` ascendente). Lista vacía si no
hay ninguna.

### `GET /tasks?assignee_id=<id>` → 200

Devuelve las tareas de ese usuario, en orden de creación (lista vacía si no tiene).
404 si el usuario no existe. El parámetro se declara con `Query(gt=0)`: un valor ≤ 0
es 422.

`strict=True` se aplica solo a los campos del cuerpo. Los parámetros de ruta y de
consulta llegan como texto y FastAPI los convierte, así que no llevan `strict`.

## Decisiones de diseño

1. **Validación de formato en `schemas.py`** con Pydantic: longitudes, rangos, tipos
   estrictos, formato de fecha, recorte de espacios y título de solo espacios.
2. **Reglas de dominio en `service.py`** con `core.errors`: fecha pasada (422,
   `invalid_request`), asignado inexistente (404, `not_found`) y conflicto de
   idempotencia (409, `conflict`). La regla de fecha pasada **no** va en el schema:
   debe usar `current_date()` para que los tests puedan fijar "hoy".
3. **Fecha actual.** En `tasks/service.py`:
   - `BUSINESS_TIMEZONE = ZoneInfo("America/Mexico_City")`: constante del módulo. Se
     resuelve al importar, así que si falta la base de zonas el error aparece de
     inmediato y es claro.
   - `local_date(instant: datetime) -> date`: función pura que convierte un instante
     a la fecha en `BUSINESS_TIMEZONE`. Es la que prueba CA-14.
   - `current_date() -> date`: devuelve `local_date(datetime.now(timezone.utc))`. Es
     la única vía para obtener "hoy"; la lógica nunca llama `date.today()` ni
     `datetime.now()` directamente. Los tests la sustituyen.
   - La lógica del servicio llama `current_date()` por su nombre dentro del módulo.
     Ningún otro módulo hace `from tasks.service import current_date`, porque esa
     copia no se vería afectada al sustituirla en los tests.
   - **Dependencia `tzdata`.** En Windows `zoneinfo` no trae la base de zonas
     horarias del sistema, y `ZoneInfo("America/Mexico_City")` falla sin ella.
     Por eso `tzdata` está en `requirements.txt`.
   - `created_at` sigue siendo UTC; la zona solo afecta a la comparación con
     `due_date`.
4. **Usuarios solo vía `users.service`.** `tasks/service.py` valida al usuario con
   `users.service.get_user`, nunca con `users.repository`.
5. **Nuevo error `conflict(message)` en `core/errors.py`.** Ninguna función actual
   encaja con el 409 de idempotencia (`already_exists` genera el mensaje "<recurso>
   ya existe: <id>"). Se añade `conflict(message: str)`, que devuelve 409 con el
   mensaje en español recibido. Mensaje previsto: "La clave de idempotencia ya se usó
   con un cuerpo distinto".
6. **Mensaje neutro en `not_found`.** El mensaje actual, "<recurso> no encontrado:
   <id>", no concuerda con recursos en femenino ("tarea no encontrado"). Se cambia a
   **"No se encontró <recurso>: <id>"** para todos los recursos. Es un cambio
   transversal: también cambia el mensaje de `users` ("No se encontró usuario: 999")
   y obliga a actualizar el assert de `tests/test_users.py`, que hoy busca
   "no encontrado".
7. **Repositorio en memoria con `reset()`.** `tasks/repository.py` guarda dos cosas,
   y `reset()` deja ambas vacías:
   - las tareas y el contador `_next_id`, que vuelve a 1. **No hay datos semilla**;
   - el registro de claves de idempotencia (clave → cuerpo normalizado e `id` de la
     tarea). Vive en el repositorio, y no en el servicio, para que `reset()` lo
     limpie junto con las tareas: si sobreviviera entre tests, una clave podría dar
     un 409 ajeno o apuntar a una tarea ya borrada.

## Orden de validación

FastAPI valida el esquema antes de entrar al servicio. Por tanto, **un cuerpo inválido
devuelve 422 antes de evaluar la clave de idempotencia**, incluso si esa clave ya se
usó: un cuerpo inválido no es un reintento válido.

Orden en `POST /tasks`:

1. Validación de formato (Pydantic): 422.
2. Búsqueda de la `Idempotency-Key`, si no está vacía: misma clave y mismo cuerpo,
   201 con la tarea guardada; misma clave y cuerpo distinto, 409.
3. Fecha pasada: 422. Va antes que el asignado porque es una regla local que no
   consulta otro recurso.
4. Asignado inexistente: 404.
5. Creación de la tarea y registro de la clave.

Consecuencias: con dos reglas de dominio incumplidas a la vez gana la fecha (422), y
con una clave reusada con otro cuerpo gana el 409 aunque el cuerpo nuevo incumpla
reglas de dominio.

En `GET /tasks/{task_id}` y `GET /tasks?assignee_id=`: primero el formato del
parámetro (422) y después la existencia (404).

## Criterios de aceptación

Los identificadores `CA-xx` nombran los tests. Todas las fechas relativas (`hoy`,
`hoy+1`, `hoy−1`) se calculan a partir de la fecha fijada por la fixture `today` (ver
"Infraestructura de tests").

### Creación

| ID    | Caso                                   | Petición                                                                       | Respuesta esperada |
|-------|----------------------------------------|--------------------------------------------------------------------------------|--------------------|
| CA-01 | Crear con solo los campos obligatorios | `POST /tasks` `{"title": "Revisar logs", "due_date": <hoy+1>}`                 | 201; `id` = 1, `created_at` presente, `priority` = 3, `description` = null, `assignee_id` = null |
| CA-02 | Crear con todos los campos             | `POST /tasks` `{"title": "  Revisar logs  ", "description": "Detalle", "due_date": <hoy+1>, "priority": 5, "assignee_id": 1}` | 201; `title` = "Revisar logs", `description` = "Detalle", `due_date` = hoy+1, `priority` = 5, `assignee_id` = 1, `id` y `created_at` presentes |
| CA-03 | Valores en los límites                 | `POST /tasks` con título de 3 caracteres, de 120, y de 120 con espacios en los extremos; `priority` 1 y 5; `description` de 1000 caracteres | 201 en cada caso |
| CA-04 | Título de solo espacios                | `POST /tasks` `{"title": "     ", "due_date": <hoy+1>}`                         | 422 |
| CA-05 | Título demasiado corto                 | `POST /tasks` `{"title": "ab", "due_date": <hoy+1>}`                           | 422 |
| CA-06 | Título corto tras recortar             | `POST /tasks` `{"title": "  ab  ", "due_date": <hoy+1>}`                       | 422 |
| CA-07 | Título demasiado largo                 | `POST /tasks` con título de 121 caracteres                                     | 422 |
| CA-08 | Descripción demasiado larga            | `POST /tasks` con `description` de 1001 caracteres                             | 422 |
| CA-09 | Descripción normalizada                | `POST /tasks` con `description` `"  Detalle  "`, `""` y `"   "`                | 201; `description` = "Detalle", null y null |
| CA-10 | Falta `due_date`                       | `POST /tasks` `{"title": "Revisar logs"}`                                      | 422 |
| CA-11 | `due_date` con formato inválido        | `POST /tasks` con `"due_date": "24/10/2026"`                                   | 422 |
| CA-12 | `due_date` en el pasado                | `POST /tasks` con `due_date` = hoy−1                                           | 422 |
| CA-13 | `due_date` de hoy                      | `POST /tasks` con `due_date` = hoy                                             | 201 |
| CA-14 | "Hoy" se calcula en `America/Mexico_City` | `local_date(datetime(2026, 10, 25, 3, 0, tzinfo=timezone.utc))` (21:00 del 24 en Ciudad de México) | Devuelve `date(2026, 10, 24)` |
| CA-15 | Prioridad por debajo del rango         | `POST /tasks` con `priority: 0`                                                | 422 |
| CA-16 | Prioridad por encima del rango         | `POST /tasks` con `priority: 6`                                                | 422 |
| CA-17 | Prioridad booleana                     | `POST /tasks` con `priority: true`                                             | 422 |
| CA-18 | Asignado inexistente                   | `POST /tasks` con `assignee_id: 999`                                           | 404; `detail` = "No se encontró usuario: 999" |
| CA-19 | Asignado con id no positivo            | `POST /tasks` con `assignee_id: 0` (y con `-1`)                                | 422 |
| CA-20 | Asignado booleano                      | `POST /tasks` con `assignee_id: true`                                          | 422 (no se asigna al usuario 1) |
| CA-21 | Fecha pasada y asignado inexistente    | `POST /tasks` con `due_date` = hoy−1 y `assignee_id: 999`                      | 422 (la fecha se evalúa primero) |
| CA-42 | `due_date` fuera del formato `YYYY-MM-DD` | `POST /tasks` con `due_date` = timestamp Unix de hoy+7 a medianoche UTC (entero, decimal y texto numérico), `"<hoy+7>T00:00:00"` y `"<hoy+7>T00:00:00Z"` | 422 con la lista de errores de Pydantic sobre `due_date` (error de formato, no de dominio) |

### Idempotencia

| ID    | Caso                                           | Petición                                                                          | Respuesta esperada |
|-------|------------------------------------------------|-----------------------------------------------------------------------------------|--------------------|
| CA-22 | Misma clave y mismo cuerpo                     | Dos `POST /tasks` iguales con `Idempotency-Key: k1`                               | Ambas 201 con el mismo `id` y el mismo `created_at`; `GET /tasks` devuelve 1 tarea |
| CA-23 | Misma clave y cuerpo distinto                  | `POST /tasks` con `k1` y un cuerpo; otro `POST /tasks` con `k1` y distinto título | La segunda 409; `GET /tasks` devuelve 1 tarea |
| CA-24 | Cuerpo equivalente tras normalizar             | Pares de `POST /tasks` con `k1`: sin `priority` / `priority: 3`; título con espacios / recortado; sin `description` / `description: ""`; sin campo extra / con `"extra": 1` | En cada par, ambas 201 con el mismo `id` |
| CA-25 | Fallo de dominio no consume la clave           | `POST /tasks` con `k1` y `assignee_id: 999` (404); luego `POST /tasks` con `k1` y `assignee_id: 1` | La primera 404; la segunda **201, no 409** |
| CA-26 | Cuerpo inválido con una clave ya usada         | `POST /tasks` válido con `k1`; luego `POST /tasks` con `k1` y `priority: 9`       | La segunda 422 (no 409) |
| CA-27 | Clave reusada, cuerpo nuevo con fecha pasada   | `POST /tasks` válido con `k1`; luego `k1` con otro título y `due_date` = hoy−1    | La segunda 409 (la clave se evalúa antes que la fecha) |
| CA-28 | Clave reusada, cuerpo nuevo con asignado inexistente | `POST /tasks` válido con `k1`; luego `k1` con otro título y `assignee_id: 999` | La segunda 409 (la clave se evalúa antes que el asignado) |
| CA-29 | Reintento tras vencer la fecha                 | `POST /tasks` con `k1` y `due_date` = hoy; avanzar `today` un día; repetir la misma petición con `k1` | Ambas 201 con el mismo `id` (comportamiento intencional) |
| CA-30 | Claves distintas con el mismo cuerpo           | Dos `POST /tasks` iguales, con `k1` y `k2`                                        | Ambas 201 con `id` distintos |
| CA-31 | Sin clave, sin idempotencia                    | Dos `POST /tasks` iguales sin header                                              | Ambas 201 con `id` distintos |
| CA-32 | Clave vacía o de solo espacios                 | Dos `POST /tasks` iguales con `Idempotency-Key: ""` (y con `"   "`)               | Se tratan como ausentes: ambas 201 con `id` distintos |

### Consulta

| ID    | Caso                                        | Petición                                  | Respuesta esperada |
|-------|---------------------------------------------|-------------------------------------------|--------------------|
| CA-33 | Obtener tarea existente                     | `GET /tasks/{id}` de una tarea creada     | 200 con la misma tarea que devolvió el `POST` |
| CA-34 | Obtener tarea inexistente                   | `GET /tasks/999`                          | 404; `detail` = "No se encontró tarea: 999" |
| CA-35 | Obtener con id no positivo                  | `GET /tasks/0` (y `/tasks/-1`)            | 422 |
| CA-36 | Listar sin tareas                           | `GET /tasks` sin haber creado ninguna     | 200 `[]` |
| CA-37 | Listar con tareas                           | `GET /tasks` tras crear 2 tareas          | 200 con 2 elementos, `id` 1 y 2 en ese orden |
| CA-38 | Filtrar por usuario con tareas              | `GET /tasks?assignee_id=1` con 1 tarea de ese usuario y 1 del usuario 2 | 200 con solo la del usuario 1 |
| CA-39 | Filtrar por usuario sin tareas              | `GET /tasks?assignee_id=2` sin tareas suyas | 200 `[]` |
| CA-40 | Filtrar por usuario inexistente             | `GET /tasks?assignee_id=999`              | 404 |
| CA-41 | Filtrar con id no positivo                  | `GET /tasks?assignee_id=0` (y con `-1`)   | 422 |

## Infraestructura de tests

- **`tests/conftest.py`**: la fixture autouse llama `reset()` de los dos repositorios,
  antes y después de cada test. Se importan con alias para que no choquen:
  `from users import repository as user_repository` y
  `from tasks import repository as task_repository`.
- **Fixture `today`** (autouse, en `tests/test_tasks.py`): fija "hoy" en
  `date(2026, 10, 24)` sustituyendo `tasks.service.current_date` con `monkeypatch`.
  Devuelve un objeto cuya fecha se puede cambiar dentro del test (CA-29). Siempre con
  `monkeypatch`, nunca con asignación directa, para que se deshaga al terminar.
- **Helper `valid_payload(**changes)`**: arma un cuerpo válido con fechas calculadas a
  partir de `today`. Los tests nunca usan `date.today()` ni fechas fijas en el futuro,
  que acabarían quedando en el pasado.
- `created_at` no se compara con un valor fijo, solo entre respuestas (CA-22).
- Los CA con varias variantes ("y con …") se escriben con `pytest.mark.parametrize`.

## Limitaciones conocidas

- **Claves globales.** La `Idempotency-Key` no se asocia a un usuario ni a un cliente:
  es la misma para todo `POST /tasks`. Dos clientes que usen la misma clave chocarán.
- **Claves sin caducidad.** El registro de claves crece sin límite; es aceptable en un
  almacén en memoria, pero no en producción.
- **Sin atomicidad.** Dos peticiones simultáneas con la misma clave podrían crear dos
  tareas, porque la comprobación y el registro de la clave no son una operación
  atómica. Con un único proceso y el almacén en memoria el riesgo es bajo.
- **Base de zonas del sistema.** En Linux, `zoneinfo` usa primero la base de zonas
  del sistema y solo recurre a `tzdata` si no la encuentra. Una base anterior a 2022
  aplicaría el horario de verano que México eliminó. CA-14 no se ve afectado: su
  instante da 24 de octubre con ambas reglas.

## Plan de implementación (completado)

Los siete pasos están hechos y CA-01 a CA-42 pasan. CA-42 se añadió después, al
corregir un defecto: `due_date` aceptaba timestamps Unix y fechas con hora.

1. Ejecutar `pip install -r requirements.txt`: `tzdata` aún no está instalado en
   `.venv`, y sin él importar `tasks.service` falla y con ello toda la suite.
2. `core/errors.py`:
   - ✅ **Hecho:** el mensaje de `not_found` es ahora "No se encontró <recurso>: <id>"
     y el assert de `tests/test_users.py` espera "No se encontró usuario: 999".
   - ✅ **Hecho:** `conflict(message)` (409).
3. Crear el paquete `tasks/` (`__init__.py`, `routes.py`, `service.py`, `schemas.py`,
   `repository.py`), con el registro de claves y `reset()` en el repositorio.
4. Declarar `priority` y `assignee_id` con `strict=True`, `assignee_id` con
   `Field(gt=0)`; `task_id` con `Path(gt=0)` y el filtro con `Query(gt=0)`.
5. **Montar el router de `tasks` en `main.py`.**
6. **Llamar `tasks.repository.reset()` en la fixture de `tests/conftest.py`**, con los
   imports con alias.
7. Escribir `tests/test_tasks.py` cubriendo CA-01 a CA-41, con el criterio en el
   docstring de cada test.
