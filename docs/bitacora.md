# Bitácora del reto · Módulo 2

Registro manual del proceso. Los prompts y respuestas completos se guardan solos en
[`bitacora-prompts.md`](bitacora-prompts.md); aquí van las **decisiones**, los
**resultados** y la **evidencia** que después se pasa a la plantilla de entrega.

Cada sección corresponde a la sección del mismo número en el formato de entrega.

---

## Convención de evidencias

Todas las capturas de tests se toman con el mismo comando, para que sean comparables
entre sí:

```powershell
pytest --cov=. --cov-report=term-missing --tb=no -rN
```

- `--cov=. --cov-report=term-missing`: tabla de cobertura por archivo, con las líneas
  que faltan.
- `--tb=no -rN`: oculta los tracebacks y la lista de fallos, para que la captura
  muestre solo el resumen.
- Las capturas se guardan en `capturas/` con un prefijo numérico en orden
  (`00-linea-base.png`, `01-tests-rojo.png`, …).

---

## 0. Línea base

- **Fecha:** 2026-10-24 · Python 3.14.6 (Windows)
- **Rama:** `feature/tasks`
- **Tests:** 6 pasando
- **Cobertura inicial:** 98 %
- **Linter (`ruff check .`):** sin errores
- **Evidencia:** `capturas/00-linea-base.png`

---

## 1. Especificación y preparación de contexto

### 1a. Funcionalidad y criterios de aceptación

- **Feature:** recurso `tasks` (crear con idempotencia opcional, consultar por id y
  listar o filtrar por asignado).
- **Fuente de verdad:** [`especificacion-tasks.md`](especificacion-tasks.md), con
  objetivo, alcance, orden de validación, limitaciones y los criterios CA-xx.
- **Mis decisiones de alcance:** `assignee_id` opcional; misma `Idempotency-Key` con
  otro cuerpo responde 409; prioridad de 1 a 5, título de 3 a 120 caracteres y
  `due_date` de hoy en adelante.
- **Prompts:** `bitacora-prompts.md`, 20:20 (especificación inicial) y 20:34
  (decisiones sobre las 8 dudas de Claude).

### 1b. Contexto para la IA

- **Archivos con @file:** `CLAUDE.md`, `core/errors.py`, los cuatro archivos de
  `users/` como patrón de referencia y `tests/test_users.py` como estilo de tests.
- **CLAUDE.md:** agregué la sección "Recurso `tasks/`" con las reglas de diseño, para
  que todas las sesiones siguientes partan de las mismas convenciones.
- **Dos rondas de revisión de la especificación:**

| Ronda | Modelo y esfuerzo | Prompt | Resultado |
|---|---|---|---|
| 1 | Sonnet 5.5 | "lista cualquier duda o riesgo" (20:20) | 8 ambigüedades del documento (zona horaria, clave vacía, ids no positivos…). Cerró con "No queda ninguna duda abierta". |
| 2 | Opus, esfuerzo high | revisar la especificación "como si fueras a escribir y ejecutar los tests": testabilidad, aislamiento, combinaciones y determinismo (20:47) | 16 problemas. 3 críticos: claves de idempotencia que se filtraban entre tests, CA-13 imposible de probar y fecha pasada + asignado inexistente sin orden definido. Además verificó que `tzdata` no estaba instalado en el `.venv`. |

- **Lo que aprendí:** la primera revisión leyó el documento como texto; la segunda
  simuló el paso siguiente (escribir los tests) y por eso encontró lo que no se podía
  probar. La perspectiva que pides en el prompt pesa tanto como el modelo.

### 1c. Patrón de generación

**Test-first.**

- Los criterios CA-xx ya describen petición y respuesta esperada, así que se
  traducen casi directo a tests.
- La fase roja demuestra que los tests detectan la ausencia de la funcionalidad
  antes de que exista código.
- Cada test lleva en su docstring el CA que cubre: trazabilidad de requisito a test.

---

## 2. Generación de código

### Decisiones clave (2c)

| Decisión | Opciones | Elegí | Por qué |
|---|---|---|---|
| Error para el 409 de idempotencia | `conflict(message)`, `idempotency_conflict(key)`, reutilizar `already_exists` | `conflict(message)` en `core/errors.py` | Simetría con `invalid_request(message)` y reutilizable. `already_exists` diría "ya existe", que no describe el problema. |
| "Mismo cuerpo" en la idempotencia | Comparar el cuerpo validado (normalizado) o el JSON crudo | Normalizado; solo se registran peticiones exitosas | Omitir `priority` y mandar `priority: 3` es la misma intención. Un intento fallido no debe "quemar" la clave. |
| Zona horaria de "hoy" | UTC o `America/Mexico_City` | `America/Mexico_City` + `tzdata` | El equipo trabaja en México: con UTC, una tarea que vence "hoy" capturada después de las 18:00 se rechazaría. En Windows `zoneinfo` necesita `tzdata`. |
| `assignee_id` ≤ 0 | 404 o 422 | 422 (`Field(gt=0)`, `Query(gt=0)`) | Un id no positivo es un dato mal formado, no un usuario inexistente. |
| Modelo para revisar la especificación | Seguir con Sonnet o subir a Opus | Opus, esfuerzo high | Los errores de la especificación se propagan a tests y código; revisar cuesta pocos tokens. |
| Mensaje "tarea no encontrado" (P7) | Aceptarlo o cambiar `not_found` | Mensaje neutro: "No se encontró <recurso>: <id>" | La redacción correcta también se evalúa. Claude recomendaba aceptarlo para no tocar `users`; preferí corregirlo de raíz en el catálogo. Costo asumido: cambia el mensaje de `users` y un assert de `test_users.py`, que se documentará en el CHANGELOG. |
| Modo estricto de Pydantic (P11) | En los tres campos o solo en algunos | Solo `priority` y `assignee_id` | En `due_date` podría rechazar también `"2026-10-24"`, porque FastAPI valida un `dict` de Python. Lo del timestamp queda como limitación. |
| Herramienta de mutation testing | `mutmut` (solo Linux/WSL), Cosmic Ray, `pytest-gremlins` | Cosmic Ray | `mutmut` necesita `fork()` y no corre en Windows nativo. Aunque instalé WSL, elegí Cosmic Ray porque corre en el mismo entorno que el resto de las evidencias (Windows, Python 3.14) y Claude Code puede ejecutarlo, analizar los sobrevivientes y proponer tests en el mismo ciclo. `pytest-gremlins` es más nuevo y la comparación que lo recomienda es de sus autores. |

> Nota: las elecciones de las preguntas de opción múltiple de Claude Code (409 y
> "mismo cuerpo") no quedan en `bitacora-prompts.md`, porque no son prompts; por eso
> se registran aquí.

### Progresión de la suite

Una fila por iteración, con el comando de la convención de evidencias.

| Momento | Passed | Failed | Errors | Cobertura total | Captura |
|---|---|---|---|---|---|
| Línea base | 6 | 0 | 0 | 98 % | `00-linea-base.png` |
| Iteración 2 · tests en rojo | 6 | 0 | 55 | 51 % | `01-tests-rojo.png` |
| Iteración 3 · base del recurso | 7 | 54 | 0 | 86 % | `02-iteracion-1.png` |
| Iteración 4 · crear y consultar | 52 | 9 | 0 | 98 % | `03-iteracion-2.png` |
| Iteración 5 · idempotencia (verde) | 61 | 0 | 0 | 99 % | `04-verde.png` |
| Iteración 6 · unitarios e integración | 67 | 0 | 0 | 99 % (`tasks/` 100 %) | `05-suite-completa.png` |
| Iteración 7 · mutation testing (refactor + test de ids grandes) | 68 | 0 | 0 | 99 % (`tasks/` 100 %) | `11-suite-tras-mutacion.png` |
| Bug 2 · `due_date` solo `YYYY-MM-DD` (CA-42) | 73 | 0 | 0 | 99 % (`tasks/` 100 %) | `14-bug-verde.png` |
| Refactorización 2 · tests | 73 | 0 | 0 | 99 % (`tasks/` 100 %) | `15-refactor-tests.png` |
| Refactorización 3 · servicio y repositorio | 73 | 0 | 0 | 99 % (`tasks/` 100 %) | `16-refactor-produccion.png` |

### Iteraciones

<!-- Plantilla por iteración:
### Iteración N · <título corto>
- **Objetivo:**
- **Prompt:** ver `bitacora-prompts.md` (hora)
- **Resultado:**
- **Aceptado / rechazado y por qué:**
- **Tests y linter:**
- **Commit:**
-->

### Iteración 1 · Mensaje neutro en `not_found`

- **Objetivo:** corregir la concordancia de género de los 404 ("tarea no encontrado")
  antes de crear el recurso `tasks`.
- **Modelo:** Sonnet 5.5, esfuerzo medium.
- **Prompt:** ver `bitacora-prompts.md` (21:10).
- **Resultado:** test-first en miniatura.
  1. Rojo: cambié el assert de `tests/test_users.py` → 1 falló y 5 pasaron
     (`'usuario no encontrado: 999' == 'No se encontró usuario: 999'`).
  2. Verde: una línea en `core/errors.py` (`f"No se encontró {resource}: {identifier}"`)
     → 6 pasaron.
  3. Viñeta nueva en "Convenciones" de `CLAUDE.md`, porque el cambio afecta a todo el
     proyecto.
- **Aceptado / rechazado y por qué:** aceptado tal cual; el diff son dos líneas de
  código. Claude Code detectó que el plan de la especificación quedó desactualizado,
  pero no lo tocó porque el prompt decía "no toques nada más": respetó el alcance.
- **Tests y linter:** 6/6 · `ruff check .`: sin errores. Verificado también por mí en
  PowerShell.
- **Commit:** `refactor(errors): mensaje neutro en not_found`

### Iteración 2 · Tests de aceptación en rojo (test-first)

- **Objetivo:** escribir `tests/test_tasks.py` con los 41 criterios antes de que exista
  el paquete `tasks/`.
- **Modelo:** Sonnet 5.5, esfuerzo high.
- **Prompt:** ver `bitacora-prompts.md` (prompt posterior a las 21:10).
- **Resultado:**
  - 552 líneas; 41 CA → 55 casos gracias a `pytest.mark.parametrize`.
  - Fase roja: **6 passed, 55 errors**, todos `ModuleNotFoundError: No module named
    'tasks'` en la fixture `today`. Ningún test falla por otra razón; los de `users`
    siguen en verde.
  - Infraestructura: fixture autouse `today` con un objeto `Clock` que se puede avanzar
    (CA-29), helper `valid_payload(**changes)` y dos helpers extra que no pedía la
    especificación: `past_date()` y `post_task(client, payload, key)`.
  - Buen detalle: en CA-12 y CA-21 verifica que `detail` sea texto y no la lista de
    errores de Pydantic, así el test exige que la fecha pasada la valide el servicio
    y no el schema.
- **Revisión externa (chat de Claude, antes de implementar):**
  - Faltaba verificar el mensaje en el 409 (CA-23) y en el 404 del filtro (CA-40): sin
    eso, un mensaje equivocado pasaría los tests. → Se agregan al inicio de la
    implementación.
  - `_clock` es un objeto global del módulo que `today` reinicia en cada test. Funciona
    mientras los tests no corran en paralelo, pero es un code smell. → Candidato para
    la refactorización de la Fase 4.
  - Todos los tests son de API (pasan por ruta → servicio → repositorio), salvo CA-14.
    Faltan unit tests del servicio con `users.service` simulado (mock) y un test de
    integración entre recursos (crear usuario con `POST /users` → asignarle tarea →
    filtrar). → Se agregan en la Fase 3.
  - Claude Code avisó que no pudo comprobar si el cliente de pruebas envía los headers
    `""` y `"   "` tal cual (CA-32). → Se verá al implementar.
- **Aceptado / rechazado y por qué:** aceptado con los ajustes de arriba.
- **Tests y linter:** 6 passed, 55 errors (esperado) · `ruff check .`: sin errores.
- **Cobertura en rojo:** TOTAL 51 % (337 sentencias, 166 sin ejecutar). Baja respecto
  al 98 % porque `--cov=.` también mide `tests/test_tasks.py` (28 %): sus tests truenan
  en la fixture antes de ejecutarse. `users/` y `core/` siguen igual que en la línea base.
- **Evidencia:** `capturas/01-tests-rojo.png`
- **Commit:** `test(tasks): tests de aceptación CA-01 a CA-41 (fase roja)`

### Iteración 3 · Ajuste de tests y base del recurso

- **Objetivo:** cerrar los huecos de la revisión externa en los tests y crear la base
  del paquete `tasks/`, todavía sin rutas.
- **Modelo:** Sonnet 5.5, esfuerzo medium.
- **Prompt:** "Prompt C" (implementación por iteraciones con parada obligatoria), ver
  `bitacora-prompts.md`. Esta entrada cubre sus iteraciones 0 y 1.
- **Resultado:**
  - Tests: CA-23 ahora exige el mensaje exacto del 409 ("La clave de idempotencia ya se
    usó con un cuerpo distinto") y CA-40 el del 404 ("No se encontró usuario: 999").
    No cambió nada más de los tests.
  - `core/errors.py`: nueva `conflict(message)` (409), con docstring en el mismo formato
    que las demás; `CLAUDE.md` la agrega a la lista del catálogo.
  - `tasks/schemas.py`: `str_strip_whitespace` recorta `title` y `description`; un
    validador convierte la descripción vacía en `null`; `strict=True` solo en
    `priority` y `assignee_id`, como se decidió.
  - `tasks/repository.py`: tareas y registro de claves en el mismo módulo; `reset()`
    vacía ambos (resuelve P1 y P8).
  - `tasks/service.py`: `BUSINESS_TIMEZONE`, `local_date()` (función pura) y
    `current_date()` (resuelve P2).
  - `tests/conftest.py`: imports con alias y reset de ambos repositorios (resuelve P9).
  - Los 55 *errors* pasaron a 54 *failed*: los tests ya se ejecutan y fallan por la
    razón esperada (aún no hay rutas). CA-14 pasa.
- **Revisión (chat de Claude):**
  - El código respeta el patrón de `users/` y las decisiones de la especificación.
  - El docstring de la fixture de `conftest.py` sigue diciendo "datos semilla", pero
    `tasks` arranca vacío. Detalle menor de documentación.
  - El commit quedó como `test(tasks)` aunque agrega código de la feature; el tipo
    correcto sería `feat(tasks)`. Lo mismo en la iteración 4.
- **Aceptado / rechazado y por qué:** aceptado.
- **Tests y linter:** 7 passed, 54 failed (esperado) · cobertura 86 %.
- **Evidencia:** `capturas/02-iteracion-1.png`
- **Commit:** `test(tasks): base del recurso` (25cb0b3)

### Iteración 4 · Crear, consultar y listar (sin idempotencia)

- **Objetivo:** lógica de negocio, rutas y montaje del router; la idempotencia queda
  para la siguiente iteración.
- **Modelo:** Sonnet 5.5, esfuerzo medium.
- **Prompt:** "sigue" (iteración 2 del Prompt C), ver `bitacora-prompts.md` (21:44).
- **Resultado:**
  - `tasks/service.py`: `create_task` valida primero la fecha (422,
    `invalid_request`), luego el asignado vía `users.service.get_user` (404) y al final
    crea; `get_task` (404 con `not_found("tarea", …)`); `list_tasks` comprueba el
    usuario cuando hay filtro.
  - `tasks/routes.py`: `GET /tasks`, `GET /tasks/{task_id}` y `POST /tasks` con
    `response_model=`; `Query(gt=0)` en el filtro y `Path(gt=0)` en el id.
  - `main.py`: monta el router de `tasks`.
  - Fallan solo 9 tests, todos de idempotencia: CA-22, CA-23, los 4 casos de CA-24,
    CA-27, CA-28 y CA-29.
- **Hallazgo:** 5 tests de idempotencia (CA-25, 26, 30, 31 y 32) **pasan sin que exista
  la lógica de claves**, porque sin idempotencia el comportamiento por defecto ya
  coincide. No prueban que la funcionalidad exista: protegen contra regresiones una vez
  que exista (por ejemplo, que una clave vacía no empiece a deduplicar). Es un buen
  caso para el mutation testing de la Fase 3.
- **Revisión (chat de Claude):**
  - El orden de validación coincide con la especificación (formato → fecha →
    asignado) y `tasks` consulta usuarios solo vía `users.service`.
  - Las rutas usan `Annotated[...]`, estilo más moderno que el de `users/`; es
    compatible con el linter y no rompe la convención.
  - `main.py` sigue con el título "API de usuarios" aunque ya expone tareas. → Para la
    fase de documentación.
- **Aceptado / rechazado y por qué:** aceptado.
- **Tests y linter:** 52 passed, 9 failed (esperado) · `ruff check .`: sin errores ·
  cobertura 98 %.
- **Evidencia:** `capturas/03-iteracion-2.png`
- **Commit:** `test(tasks): Crear y consultar sin idempotencia` (6b8150a)

### Iteración 5 · Idempotencia: suite en verde

- **Objetivo:** implementar `Idempotency-Key` en `POST /tasks`.
- **Modelo:** Sonnet 5.5, esfuerzo medium.
- **Prompt:** "sigue" (iteración 3 del Prompt C), ver `bitacora-prompts.md` (21:49).
- **Resultado:**
  - `tasks/routes.py`: `POST /tasks` lee el header con `Header()` y lo pasa al servicio.
  - `tasks/service.py`: `create_task(data, idempotency_key=None)` sigue el orden de la
    especificación: clave vacía = ausente → clave registrada (mismo cuerpo normalizado
    devuelve la tarea guardada; cuerpo distinto, `conflict` con el mensaje en la
    constante `IDEMPOTENCY_CONFLICT_MESSAGE`) → fecha pasada → asignado → crear y
    registrar la clave solo si todo salió bien.
  - Actualizó el plan de la especificación (todo completado).
  - **61 passed, 99 %.** Las únicas líneas sin cubrir son el cuerpo de `current_date()`
    (los tests siempre la sustituyen) y `/health` en `main.py`, que ya existía.
  - No modificó ningún test después de la iteración 0 y no reportó ninguno incorrecto.
- **Revisión (chat de Claude):**
  - La lógica es correcta y respeta el orden de validación.
  - `create_task` ya mezcla tres responsabilidades (idempotencia, reglas de dominio y
    creación) con `if` anidados. → Segundo candidato para la refactorización de la
    Fase 4 (extraer la parte de idempotencia y la de validación).
  - **La IA reportó mal el estado del repo:** dijo que `docs/` y `.claude/` estaban sin
    seguimiento, pero ya estaban en commits anteriores. Lo verifiqué con `git status`.
    Lección: el estado de git se comprueba, no se le cree a la IA.
- **Aceptado / rechazado y por qué:** aceptado. El commit lo hice yo, no Claude Code.
- **Tests y linter:** 61/61 · `ruff check .`: sin errores · cobertura 99 %.
- **Evidencia:** `capturas/04-verde.png`
- **Commit:** `feat(tasks): idempotencia en POST /tasks` (dd29821)

### Iteración 6 · Unitarios con mocks e integración entre recursos (Fase 3)

- **Objetivo:** completar la suite con lo que faltaba según la revisión de la
  Iteración 2: unitarios del servicio con dependencias simuladas y un test de
  integración `users` ↔ `tasks`.
- **Modelo:** Sonnet 5.5, esfuerzo high.
- **Prompt:** "Prompt D", ver `bitacora-prompts.md`.
- **Resultado:**
  - Todo en `tests/test_tasks.py`; no hizo falta un archivo aparte (se respetó "un
    archivo por recurso").
  - Fixtures nuevas: `get_user` (un `Mock` que sustituye `users.service.get_user`) y
    `add_spy` (un espía con `Mock(wraps=...)` sobre `repository.add` que conserva el
    comportamiento real).
  - 5 unitarios: sin asignado no consulta usuarios; con asignado llama a `get_user`
    una vez con ese id; con fecha pasada no consulta usuarios ni guarda (usa
    `assignee_id=1` para que el assert no sea trivial); un reintento con la misma
    clave no vuelve a llamar a `add`; `current_date()` usa `local_date()` sobre el
    instante actual.
  - 1 test de integración: crea un usuario con `POST /users`, le asigna una tarea, la
    recupera por el filtro y por id. Sin simulaciones.
  - **67 passed**; `tasks/` queda al 100 % de cobertura.
- **Revisión (chat de Claude):**
  - Los unitarios y la integración están bien planteados.
  - **El test de `current_date()` está sobre-simulado:** simula a la vez `datetime` y
    `local_date`, así que verifica *cómo* está escrita la función (qué llama y con qué
    argumentos) y no *qué* devuelve. Si `current_date()` se reescribiera de otra forma
    equivalente, el test fallaría sin que haya un bug. Es mejor simular solo el
    instante (03:00 UTC) y comprobar con el `local_date` real que el resultado es el
    24 de octubre.
  - `monkeypatch.undo()` quita el reloj falso de la fixture autouse `today`. Funciona,
    pero es un rodeo que nace del mismo problema que el `_clock` global: la fixture
    `today` se aplica a todo el archivo. → Se suma al candidato de refactorización de
    la Fase 4.
  - Los unitarios no tienen un CA propio; Claude Code usó "Unitario (CA-xx)" y
    "relacionado con CA-xx". Conviene escribir esa regla en `CLAUDE.md`.
- **Corrección aplicada:**
  - El test de `current_date()` ahora simula solo `datetime.now` (2026-10-25 03:00
    UTC), usa el `local_date` real y verifica únicamente el resultado (24 de
    octubre). Claude Code además lo renombró a
    `test_current_date_devuelve_la_fecha_de_mexico_para_el_instante_actual`, porque
    el nombre anterior describía la implementación.
  - `CLAUDE.md` documenta la regla de docstrings para unitarios ("Unitario (CA-xx)")
    e integración ("relacionado con CA-xx").
- **Aceptado / rechazado y por qué:** aceptado tras las correcciones.
- **Tests y linter:** 67/67 · `ruff check .`: sin errores · `tasks/` al 100 %.
- **Evidencia:** `capturas/05-suite-completa.png`
- **Commit:** `test(tasks): unitarios del servicio e integración entre recursos`

### Iteración 7 · Mutation testing con Cosmic Ray (primera corrida)

- **Objetivo:** medir si los tests detectan errores, no solo si ejecutan el código.
- **Modelo:** Sonnet 5.5, esfuerzo high.
- **Prompt:** "Prompt E", ver `bitacora-prompts.md`.
- **Configuración:** `cosmic-ray>=8.7` (instalada la 8.7.0) en `requirements.txt`;
  `cosmic-ray.toml` muta solo `tasks/`, `timeout = 30`,
  `test-command = "pytest -x -q --tb=no -p no:cacheprovider"`; la sesión
  (`cosmic-ray.sqlite`) va en `.gitignore`.
- **Resultado:** 188 mutantes · **96 muertos (51 %)** · 92 sobrevivientes · 0 con
  timeout. Detalle y análisis en la sección 3.
- **Mis decisiones sobre los sobrevivientes:** grupo 3 → corregir el diseño (no un
  test); grupo 4 → unitario con ids grandes; grupo 1 → filtrar el operador `|`;
  grupo 2 → dejarlo como equivalente documentado.
- **Segunda corrida:** 186 mutantes · 110 omitidos por el filtro · 76 ejecutados ·
  **75 muertos (98,7 %)** · 1 sobreviviente (el `@classmethod`, equivalente
  documentado). Ver sección 3.
- **Detalles que reportó Claude Code:**
  - `cr-report` dice "surviving mutants: 1 (0.54%)", pero divide entre los 186,
    incluidos los omitidos; el valor honesto es 1 de 76 (1,3 %).
  - Guardó una copia de `tasks/` antes de correr y verificó que los cinco archivos
    quedaron idénticos tras las 76 ejecuciones.
- **Aceptado / rechazado y por qué:** aceptado.
- **Tests y linter:** 68/68 · `ruff check .`: sin errores.
- **Evidencia:** `mutacion/reporte-final.html`, `capturas/09-mutacion-final.png`
  (resumen) y `capturas/10-ultimo-sobreviviente.png` (job 108: quitar `@classmethod`).
- **Commit:** `test(tasks): mutation testing al 98,7 % (Cosmic Ray)`

---

## 3. Tests y cobertura

- **Unitarios:**
- **Edge cases cubiertos:**
- **Mocks utilizados:**
- **Integración:**
- **Cobertura final:**
- **Mutation testing (Cosmic Ray 8.7, solo `tasks/`):**

  Primera corrida: 188 mutantes, 96 muertos (51 %), 92 sobrevivientes. Claude Code
  clasificó cada sobreviviente como (a) hueco real o (b) equivalente, y verificó sus
  afirmaciones con pruebas puntuales:

  | Grupo | Mutantes | Qué cambia | Clasificación | Por qué |
  |---|---|---|---|---|
  | 1 | 88 | El `\|` de las anotaciones de tipo (`str \| None`) por otro operador (`+`, `&`, `^`…) | (b) Equivalente | En Python 3.14 las anotaciones de función no se evalúan al definirla (`def f(x: int + None)` no falla). En 3.13 o anterior estos mutantes fallarían al importar y morirían. |
  | 2 | 1 | Quitar `@classmethod` del validador de `description` | (b) Equivalente | Pydantic envuelve el validador por sí mismo; verificado: sin el decorador, `""` sigue dando `None`. |
  | 3 | 2 | `_next_id = 1` pasa a `0` o `2` en `repository.py` | (a) Hueco real | `reset()` fija `_next_id = 1` antes de cada test, así que ningún test ve el valor inicial. `users/repository.py` evita la duplicación llamando a `reset()` al importar; `tasks` no. |
  | 4 | 1 | `==` pasa a `is` al filtrar por `assignee_id` | (a) Hueco real, bajo riesgo | CPython reutiliza los enteros hasta 256, así que con los ids de los tests (1–5) `is` funciona igual. Con un usuario de id > 256 el filtro devolvería siempre una lista vacía. |

  Sin los 89 equivalentes: **96 de 99 mutantes que pueden morir (97 %)**.

  Evidencia: reporte navegable `mutacion/reporte-inicial.html` y capturas:
  - `capturas/06-mutacion-inicial.png`: resumen (188 mutantes, 92 sobrevivientes).
  - `capturas/07-mutante-sobreviviente.png`: job 61, `==` → `is` en
    `list_by_assignee`. **Sobrevive**: todos los tests pasan.
  - `capturas/08-mutante-muerto.png`: job 60, `==` → `>=` en la misma línea.
    **Muere**: lo detecta `test_list_tasks_filtra_por_usuario_con_tareas`.
  - Misma línea, dos mutantes: uno se detecta y el otro se escapa. La diferencia
    está en los datos del test (ids pequeños), no en la línea cubierta.

  **Segunda corrida (después de mis decisiones):**

  | | Mutantes |
  |---|---|
  | Total de la sesión | 186 (2 menos: la línea de `_next_id = 1` ya no existe) |
  | Omitidos por el filtro de `\|` | 110 |
  | Ejecutados | 76 |
  | Muertos | **75 (98,7 %)** |
  | Sobrevivientes | 1: quitar `@classmethod` (equivalente documentado) |

  Evidencia: `mutacion/reporte-final.html`; `capturas/09-mutacion-final.png` (el
  reporte muestra "1 (0.54%)" porque divide entre 186; el valor real es 1 de 76) y
  `capturas/10-ultimo-sobreviviente.png` (el único sobreviviente).

  - Grupo 3 se resolvió con un refactor (ver sección 4, Refactorización 1).
  - Grupo 4 lo mata `test_repository_list_by_assignee_compara_ids_grandes_por_valor`,
    con ids `int("1000")` e `int("1001")` creados en tiempo de ejecución.
  - **Costo del filtro:** de los 110 omitidos, 22 sí morían antes (las anotaciones
    de `routes.py`, que FastAPI sí evalúa). El filtro actúa por operador y no por
    archivo, así que Cosmic Ray ya no vigila esas anotaciones. Lo acepto: el
    comportamiento de esas rutas lo cubren los tests de API (CA-26, CA-32, CA-41).

  **Lecciones:**
  - El 100 % de cobertura convivía con 3 huecos reales que la cobertura no puede ver.
  - Un mismo mutante es equivalente o no según la versión de Python (grupo 1): el
    puntaje bruto engaña si no se analiza.
  - El grupo 4 es un error que ningún test con ids pequeños detectaría nunca.
- **Evidencia:**

---

## 4. Debugging y refactorización

<!-- Plantilla por bug:
### Bug N · <descripción>
- **Síntoma / stack trace:**
- **Hipótesis propuestas por la IA:**
- **Hipótesis correcta y fix aplicado:**
- **Validación (tests):**
-->

### Bug 1 · El baseline de Cosmic Ray fallaba en silencio en Windows

- **Síntoma:** con `test-command = "python -m pytest ..."`, el baseline de Cosmic Ray
  fallaba sin ningún mensaje de error, aunque `pytest` pasaba en la terminal.
- **Diagnóstico de la IA (Claude Code):** el proceso hijo no tenía las dependencias.
  En Windows, `CreateProcess` busca `python` primero junto al proceso padre real (el
  Python base, `C:\Python314`, sin FastAPI) y no en el `PATH` del entorno virtual.
  Cosmic Ray solo muestra la salida estándar, así que el error de importación no se
  veía.
- **Fix aplicado:** usar `pytest` a secas en el `test-command` (el ejecutable
  `pytest.exe` del `.venv` sí se resuelve por el `PATH`) y documentar el motivo en
  `cosmic-ray.toml`.
- **Validación:** el baseline pasa y la sesión completa corre sin timeouts.
- **Nota:** este bug fue de herramientas, no del código de la feature, y la IA lo
  resolvió sola dentro del prompt. No hubo un intercambio de "hipótesis antes que
  soluciones" conmigo; eso queda para el bug de la aplicación.

### Bug 2 · `due_date` acepta un timestamp Unix

Protocolo en tres pasos separados, para que la IA no salte directo a la solución:
reproducir → pedir hipótesis sin tocar código → verificar, corregir y validar.

- **Paso 1 · Reproducción** (Sonnet, esfuerzo medium):
  - Test nuevo `test_create_task_due_date_como_timestamp_unix_devuelve_422` (CA-42):
    envía `due_date` como el timestamp Unix de una fecha futura (hoy + 7 días) a
    medianoche UTC, para que la regla de fecha pasada no interfiera.
  - **Síntoma:** `assert 201 == 422` en `tests/test_tasks.py:576`
    (`AssertionError`). La API crea la tarea aunque la especificación exige el
    formato `YYYY-MM-DD`.
  - Evidencia: `capturas/12-bug-rojo.png` (traceback completo).
- **Paso 2 · Hipótesis de la IA** (Opus, esfuerzo high). Le di stack trace, contexto
  y comportamiento esperado, y le pedí hipótesis sin tocar código. Propuso tres,
  cada una con un experimento para verificarla sin cambiar producción:

  | # | Hipótesis | Cómo verificarla |
  |---|---|---|
  | H1 (más probable) | Pydantic, en modo laxo, convierte el entero en fecha porque `due_date` no es estricto. Solo acepta timestamps exactos a medianoche UTC (el caso del test); con parte horaria daría `date_from_datetime_inexact`. | `TypeAdapter(date).validate_python(ts)` y variantes (`ts + 1`, milisegundos, `float`, `str`). |
  | H2 | FastAPI valida el cuerpo en modo Python (ya convertido a `dict`), así que nada distingue un número JSON de un texto JSON. Es la premisa de la decisión P11: `strict=True` en modo Python rechazaría también `"2026-10-24"`. | `TypeAdapter(Annotated[date, Field(strict=True)])` en modo Python y JSON, y una app mínima con `TestClient` en un directorio temporal. |
  | H3 (menos probable) | El test no envía lo que creemos (por ejemplo, `valid_payload` no sobrescribe `due_date`). | Imprimir el payload y el `due_date` de la respuesta. |

  - **Observación de la IA:** el comportamiento esperado contradice la especificación
    vigente, que documenta los timestamps como "limitación conocida". No es un fallo
    de implementación sino un requisito que cambia: hay que decidir si CA-42
    reemplaza esa limitación.
  - **Mi evaluación:** verificar H1 (causa directa) y H2 (decide cómo se puede
    corregir). H3 no hace falta: el experimento de H1 ya prueba que el test envía lo
    que creemos. Sobre el requisito: CA-42 reemplaza la limitación, porque la
    especificación se contradecía (`YYYY-MM-DD` en la tabla de campos, timestamps
    aceptados en las limitaciones) y resuelvo a favor del formato declarado.
- **Paso 3a · Verificación** (Opus, esfuerzo high; experimentos fuera del repo, sin
  tocar producción; pydantic 2.14.1, fastapi 0.162.0):
  - **H1 confirmada:** `TaskCreate` convierte `1793404800` en `2026-10-31`. Un segundo
    después de medianoche da `date_from_datetime_inexact`. También se aceptan
    milisegundos, decimales y, **hallazgo nuevo**, el texto `"1793404800"` y las
    fechas con hora (`"2026-10-31T00:00:00"`, con o sin `Z`).
  - **H2 confirmada:** con un `date` estricto, una app mínima de FastAPI rechaza
    también `"2026-10-31"` (`date_type`), porque el cuerpo se valida como `dict` de
    Python. `strict=True` queda descartado como fix: la premisa de P11 sigue en pie.
  - La IA comparó cinco variantes sobre 12 valores de prueba y propuso tres fixes,
    todos con un validador previo (`mode="before"`) en el schema:

  | Opción | Qué hace | Ventaja | Desventaja |
  |---|---|---|---|
  | **B · texto con formato exacto** | Exige `str` y `re.fullmatch` de `AAAA-MM-DD` | Es literalmente la especificación; cierra todos los huecos de la tabla | Introduce una expresión regular |
  | C · `date.fromisoformat` | Exige `str` y usa la biblioteca estándar | Sin regex | Desde Python 3.11 acepta `20261031` y `2026-W44-6`: contradice el formato declarado |
  | A · solo texto | Rechaza lo que no sea `str` | Cambio mínimo | Deja pasar `"1793404800"` y las fechas con hora |

  - Detalle técnico que señaló la IA: el validador debe ir en `TaskCreate` y no en
    `TaskBase`, porque `Task` hereda de `TaskBase` y el repositorio lo construye con
    un objeto `date`.
- **Mi decisión:** opción B, con dos ajustes:
  - Ampliar CA-42 con `parametrize` para que el test fije los huecos encontrados
    (entero, decimal, texto numérico, fecha con hora), no solo el entero.
  - **Hallazgo de la revisión externa (chat de Claude):** en Python, `\d` acepta
    dígitos de cualquier alfabeto Unicode (por ejemplo, `٢٠٢٦`), no solo del 0 al 9.
    La expresión regular debe usar `[0-9]` para ser exactamente `AAAA-MM-DD`.
- **Paso 3b · Fix y validación** (Opus, esfuerzo high; lo usé sin querer, para un fix
  así de acotado bastaba Sonnet):
  - **Test:** CA-42 ampliado con `parametrize` a 5 casos (entero, decimal, texto
    numérico, fecha con hora y fecha con hora UTC) y renombrado a
    `test_create_task_due_date_fuera_del_formato_yyyy_mm_dd_devuelve_422`. Además
    verifica que el 422 sea un error de formato (lista de Pydantic sobre
    `due_date`), no de dominio.
  - **Fix:** validador previo (`mode="before"`) en `TaskCreate` (no en `TaskBase`)
    que exige texto y `re.fullmatch` con `[0-9]{4}-[0-9]{2}-[0-9]{2}`; mensaje en
    español: "La fecha límite debe tener el formato YYYY-MM-DD". Un comentario en el
    código explica por qué `[0-9]` y no `\d`.
  - **Documentación:** la especificación agrega CA-42, explica en la fila de
    `due_date` por qué no lleva `strict=True` y elimina la limitación de los
    timestamps; `CLAUDE.md` actualiza la regla.
  - **Proceso:** Claude Code aplicó el fix sin detenerse después de ampliar el test,
    porque mi prompt no le pedía parar. Lección: si quiero evidencia de cada fase,
    el prompt debe pedir explícitamente la pausa.
  - **Fase roja reconstruida:** aparté el fix con `git stash push -- tasks/schemas.py`,
    corrí el test ampliado contra el código anterior (**5 failed**, los cinco con
    `assert 201 == 422`) y lo regresé con `git stash pop`. Evidencia:
    `capturas/13-bug-test-ampliado.png`.
  - **Validación:** 73 passed (68 + 5 casos de CA-42), cobertura 99 %, `tasks/` al
    100 %; `ruff check .` sin errores.
  - Evidencia: `capturas/14-bug-verde.png`.
- **Paso 3 · Fix y validación:** pendiente.

<!-- Plantilla por refactorización:
### Refactorización N · <code smell>
- **Code smell detectado:**
- **Cambio realizado:**
- **Tests antes / después:**
-->

### Refactorización 1 · Estado inicial duplicado en `tasks/repository.py`

- **Code smell detectado:** el valor inicial de `_next_id` vivía en dos lugares: en
  la declaración del módulo (`_next_id: int = 1`) y en `reset()`. Lo reveló el
  mutation testing: cambiar el `1` de la declaración por `0` o `2` no hacía fallar
  ningún test, porque la fixture llama a `reset()` antes de cada uno. En la
  aplicación real, ese cambio haría que la primera tarea no tuviera id 1.
- **Cambio realizado:** igual que `users/repository.py`, el módulo declara
  `_next_id: int` sin valor y llama a `reset()` al importarse. El estado inicial
  vive solo en `reset()`. Además queda coherente con el proyecto base.
- **Tests antes / después:** 67 en verde antes; 68 en verde después (se sumó el
  unitario del grupo 4). Los mutantes dentro de `reset()` mueren con los tests
  existentes (CA-01 exige `id == 1`).

### Revisión de code smells (antes de las refactorizaciones 2 y 3)

- **Modelo:** Opus, esfuerzo high. Prompt de solo lectura: archivo y líneas, nombre
  del smell, por qué importa aquí y qué refactorización propone; ordenados por
  impacto, separando los que vale la pena hacer de los que no.
- **Resultado:** 9 smells a corregir y 8 que no vale la pena tocar, cada uno
  justificado. Por ejemplo: los tests 422 casi idénticos son una convención
  deliberada (un test por CA da trazabilidad) y los literales repetidos en los tests
  fijan el contrato a propósito.
- **Comparación con la revisión externa (chat de Claude):** encontró los tres puntos
  que yo tenía anotados (`create_task` con tres responsabilidades, el
  `monkeypatch.undo()` y el `_clock` global) y seis más. Añadió matices que no
  teníamos: la condición `if key:` repetida en `create_task`, y que `undo()` deshace
  todos los parches del test, no solo el reloj. Esta vez la autorrevisión funcionó
  porque el prompt pedía una perspectiva concreta.
- **Mis decisiones de alcance:**

  | # | Smell | Decisión |
  |---|---|---|
  | 1 | `monkeypatch.undo()` en un test (fragile test) | Hacer (refactorización 2) |
  | 4 | Reloj global con dos formas de acceso | Hacer, versión mínima (refactorización 2) |
  | 5 | Imports de `tasks` repetidos dentro de los tests | Hacer (refactorización 2). La regla venía del ciclo test-first, cuando `tasks/` no existía |
  | 7 | CA-42 y un test del repositorio en la sección equivocada | Hacer (refactorización 2) |
  | 8 | Helpers de tests sin anotar | Hacer (refactorización 2) |
  | 2 | `create_task` con tres responsabilidades | Hacer (refactorización 3) |
  | 9 | `get_user` llamado solo por su efecto (lanzar 404) | Hacer (refactorización 3) |
  | 6 | Tupla posicional en el registro de idempotencia | Hacer (refactorización 3) |
  | 3 | `repository.add(**data.model_dump())` (data clump) | **No hacer:** rompe la simetría con `users.repository.add` y obliga a cambiar un test. Queda como deuda técnica documentada |

### Refactorización 2 · Infraestructura de `tests/test_tasks.py`

- **Code smells:** 1, 4, 5, 7 y 8 de la revisión.
- **Cambio realizado** (Sonnet, esfuerzo medium):
  - Sin `monkeypatch.undo()`: la función real se captura al cargar el módulo
    (`REAL_CURRENT_DATE`) y el test de `current_date()` la restaura con
    `monkeypatch.setattr`, así que ya no revierte otros parches. Claude Code descartó
    el marcador `real_clock` que había propuesto, porque exigía tocar
    `pyproject.toml` y el prompt limitaba el cambio a los tests.
  - Un solo acceso al reloj: CA-13 y CA-42 reciben el parámetro `today`, como CA-29.
  - `tasks` se importa a nivel de módulo; se quitaron 8 imports locales.
  - CA-42 y `unix_timestamp` pasan a "Creación"; la sección de unitarios se llama
    "Unitarios de `tasks/`".
  - `post_task` y `task_create` anotan su tipo de retorno.
  - El docstring del módulo y `CLAUDE.md` actualizan las reglas.
- **Tests antes / después:** 73 passed antes y después, con los mismos nombres y
  aserciones. `tests/test_tasks.py` baja de 303 a 296 sentencias; `ruff check .` sin
  errores.
- **Evidencia:** `capturas/15-refactor-tests.png`
- **Commit:** `refactor(tests): fixture today sin undo(), imports a nivel de módulo y secciones ordenadas` (e1da43d)

### Refactorización 3 · `create_task`, `_require_user` e `IdempotencyRecord`

- **Code smells:** 2, 9 y 6 de la revisión.
- **Cambio realizado** (Sonnet, esfuerzo medium; sin modificar ningún test):
  - `_replay(key, data)`: busca la clave y devuelve la tarea original, `None` si la
    clave es nueva, o lanza el 409. `create_task` queda con una anidación menos.
  - `_require_user(user_id)`: nombra la intención de "fallar con 404 si el usuario
    no existe". Lo usan `create_task` y `list_tasks`.
  - `IdempotencyRecord(NamedTuple)` con `body` y `task_id`: el servicio usa
    `record.body` y `record.task_id` en lugar de desempaquetar una tupla por
    posición.
  - Limitación reconocida por Claude Code: `create_task` mantiene dos `if key:` (al
    inicio y al final). Quitar el segundo exigía cambiar el orden de pasos de la
    especificación, y prefirió no hacerlo.

  ```python
  # Después
  def create_task(data: TaskCreate, idempotency_key: str | None = None) -> Task:
      key = (idempotency_key or "").strip()
      if key:
          replayed = _replay(key, data)
          if replayed is not None:
              return replayed
      if data.due_date < current_date():
          raise errors.invalid_request("La fecha límite no puede estar en el pasado")
      if data.assignee_id is not None:
          _require_user(data.assignee_id)
      task = repository.add(**data.model_dump())
      if key:
          repository.remember_key(key, data, task.id)
      return task
  ```
- **Tests antes / después:** 73 passed antes y después, sin tocar ningún test;
  `ruff check .` sin errores; `tasks/` al 100 %.
- **Red de seguridad extra: mutation testing tras el refactor.** Sesión de Cosmic
  Ray desde cero: 205 mutantes (más código nuevo), 121 omitidos por el filtro, 84
  ejecutados, **82 muertos (97,6 %)**. Los 2 sobrevivientes son el mismo caso
  equivalente: quitar `@classmethod` en los dos validadores de `schemas.py` (el de
  `description` y el nuevo de `due_date`). Sin equivalentes: 82 de 82. La
  refactorización no debilitó la suite.
- **Evidencia:** `capturas/16-refactor-produccion.png` (suite),
  `mutacion/reporte-refactor.html` y `capturas/17-mutacion-refactor.png` (resumen de
  Cosmic Ray: 205 mutantes, 2 sobrevivientes; el "0.98%" divide entre 205, el valor
  real es 2 de 84).
- **Commit:** `refactor(tasks): create_task como lista de pasos; _replay, _require_user e IdempotencyRecord`

---

## 5. Documentación

- [x] Docstrings en funciones clave
- [x] README actualizado (endpoints, uso, pruebas)
- [x] CHANGELOG.md

### Iteración de documentación

- **Modelo:** Sonnet 5.5, esfuerzo medium. Sin cambios de comportamiento ni de tests.
- **Resultado:**
  - **Docstrings** en las funciones públicas de `tasks/service.py` (con el orden de
    las reglas y los errores que lanza cada una) y en las rutas de `tasks/routes.py`,
    escritas para quien consume la API: FastAPI las muestra como descripción en
    Swagger.
  - **Ejemplo en Swagger:** `TaskCreate` lleva un cuerpo de ejemplo válido
    (`json_schema_extra`).
  - **README:** endpoints de `tasks` en la tabla; sección "Recurso tasks" con reglas
    de validación, tabla de códigos de respuesta, `Idempotency-Key` y ejemplos con
    `curl` e `Invoke-RestMethod`; cómo correr Cosmic Ray en Windows; sección de
    onboarding con la estructura del proyecto y enlaces a `CLAUDE.md`, la
    especificación, la bitácora y el CHANGELOG.
  - **CHANGELOG.md** (Keep a Changelog): 0.2.0 con Añadido, Cambiado y Deuda técnica
    conocida, más una entrada mínima de 0.1.0 como origen.
  - **Pendientes menores:** título "API de usuarios y tareas" y versión 0.2.0 en
    `main.py` y `pyproject.toml`; docstring de `conftest.py` corregido ("datos
    semilla"); comentario de `cosmic-ray.toml` corregido (las anotaciones de
    `routes.py` sí las evalúa FastAPI); comandos de Cosmic Ray en `CLAUDE.md`.
  - Claude Code verificó con `app.openapi()` que el título, la versión, el ejemplo y
    las descripciones aparecen en el esquema OpenAPI.
- **Revisión (chat de Claude):**
  - **CHANGELOG:** "Cambiado" incluía el formato de `due_date` (el recurso `tasks` no
    existía en 0.1.0, así que no es un cambio para nadie) y refactorizaciones
    internas (`IdempotencyRecord`, tests), que no le importan a quien consume la API.
    → La regla de `due_date` pasa a "Añadido" y las refactorizaciones internas salen.
  - **README:** el comando `cr-html ... > archivo.html` guarda en UTF-16 en Windows
    PowerShell, el mismo problema que ya habíamos encontrado. → Usar
    `Out-File -Encoding utf8` y mencionar los reportes de `docs/mutacion/`.
  - **Fechas de los ejemplos:** `2026-12-31` queda en el pasado en dos meses y el
    ejemplo de Swagger empezaría a dar 422 (Claude Code lo advirtió). → Usar una
    fecha lejana, como `2030-12-31`.
- **Aceptado / rechazado y por qué:** aceptado con los tres ajustes de arriba, ya
  aplicados: "Cambiado" solo lista el mensaje de `not_found` y el título; el README
  usa `Out-File -Encoding utf8` y apunta a los reportes de `docs/mutacion/`; los
  ejemplos usan `2030-12-31`.
- **Tests y linter:** 73/73 · `ruff check .`: sin errores.
- **Evidencia:** `capturas/18-documentacion.png` (suite) y `capturas/19-swagger.png`
  (`POST /tasks` en Swagger: descripción con los códigos de respuesta, header
  `Idempotency-Key` y cuerpo de ejemplo). Para levantar el servidor usé
  `--port 5050`: el 8000 dio `WinError 10013`, probablemente porque Windows reservó
  ese rango al instalar WSL/Docker.
  Prueba de punta a punta desde Swagger ("Try it out" con el ejemplo):
  `capturas/20-swagger-respuesta.png`, **201** con la tarea creada (`id` y
  `created_at` generados por el servidor).
  Prueba de idempotencia en vivo: `capturas/21-swagger-409.png`, misma clave
  (`prueba-1`) con otro título → **409** con el mensaje "La clave de idempotencia
  ya se usó con un cuerpo distinto".
- **Hallazgo en la prueba manual:** Swagger marcó el 409 como **"Undocumented"**.
  FastAPI solo documenta por sí mismo el 201 y el 422; el 404 y el 409 aparecían en
  la descripción, pero no como respuestas formales del esquema OpenAPI. Una prueba
  manual encontró un hueco que los tests automáticos no podían ver.
- **Corrección:** `responses=` en las tres rutas de `tasks/routes.py` (404 en las
  tres, 409 en `POST /tasks`), cada una con descripción en español y un ejemplo
  del `detail` real. Claude Code agregó un helper `_error_response` y tomó el
  ejemplo del 409 de la constante del servicio, para que no se desfase si cambia el
  mensaje. Lo verificó con `app.openapi()`. Ruff marcó dos líneas largas (E501) en
  la primera pasada y las corrigió. 73 passed, `tasks/` al 100 %.
  - No volví a correr Cosmic Ray: el cambio solo agrega metadatos de documentación.
    Si se corre, los literales de esos ejemplos generarán mutantes que sobreviven,
    porque no cambian el comportamiento de la API.
  - Evidencia: `capturas/22-swagger-409-documentado.png`.
- **Commit:** `docs: README, CHANGELOG 0.2.0, docstrings y respuestas documentadas en Swagger`

---

## Reflexión

### Qué funcionó

### Qué no funcionó

### Qué mejoraría

### Qué me llevo a mi trabajo
