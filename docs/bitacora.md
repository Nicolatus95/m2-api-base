# Bitácora del reto · Módulo 2

Registro manual del proceso. Los prompts y respuestas completos se guardan solos en
[`bitacora-prompts.md`](bitacora-prompts.md); aquí van las **decisiones**, los
**resultados** y la **evidencia** que después se pasa a la plantilla de entrega.

Cada sección corresponde a la sección del mismo número en el formato de entrega.

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

> Nota: las elecciones de las preguntas de opción múltiple de Claude Code (409 y
> "mismo cuerpo") no quedan en `bitacora-prompts.md`, porque no son prompts; por eso
> se registran aquí.

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

---

## 3. Tests y cobertura

- **Unitarios:**
- **Edge cases cubiertos:**
- **Mocks utilizados:**
- **Integración:**
- **Cobertura final:**
- **Mutation testing:**
- **Evidencia:**

---

## 4. Debugging y refactorización

### Bug N · <descripción>

- **Síntoma / stack trace:**
- **Hipótesis propuestas por la IA:**
- **Hipótesis correcta y fix aplicado:**
- **Validación (tests):**

### Refactorización N · <code smell>

- **Code smell detectado:**
- **Cambio realizado:**
- **Tests antes / después:**

---

## 5. Documentación

- [ ] Docstrings en funciones clave
- [ ] README actualizado (endpoints, uso, pruebas)
- [ ] CHANGELOG.md

---

## Reflexión

### Qué funcionó

### Qué no funcionó

### Qué mejoraría

### Qué me llevo a mi trabajo
