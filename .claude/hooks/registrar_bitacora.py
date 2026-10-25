"""Registra en docs/bitacora-prompts.md cada prompt y cada respuesta de Claude Code.

Lo invocan los hooks de .claude/settings.json:
  - UserPromptSubmit -> python registrar_bitacora.py prompt
  - Stop             -> python registrar_bitacora.py respuesta

Claude Code envía por stdin un JSON con los datos del evento. Este script solo usa
la biblioteca estándar y nunca debe interrumpir la sesión: ante cualquier error,
sale en silencio con código 0.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

LIMITE_RESPUESTA = 2000  # caracteres; las respuestas largas se recortan
HERRAMIENTAS_DE_ARCHIVO = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def leer_evento() -> dict:
    datos = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    return json.loads(datos) if datos.strip() else {}


def ruta_bitacora(evento: dict) -> Path:
    raiz = os.environ.get("CLAUDE_PROJECT_DIR") or evento.get("cwd") or "."
    ruta = Path(raiz) / "docs" / "bitacora-prompts.md"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not ruta.exists():
        ruta.write_text(
            "# Bitácora automática de prompts\n\n"
            "Generada por los hooks de Claude Code (`.claude/hooks/registrar_bitacora.py`).\n"
            "No editar a mano: las notas y decisiones van en `docs/bitacora.md`.\n",
            encoding="utf-8",
        )
    return ruta


def ultima_respuesta(transcript_path: str) -> tuple[str, list[str]]:
    """Devuelve el texto de la última respuesta y los archivos que modificó."""
    entradas = []
    with open(transcript_path, encoding="utf-8", errors="replace") as archivo:
        for linea in archivo:
            try:
                entradas.append(json.loads(linea))
            except json.JSONDecodeError:
                continue

    # Retrocede hasta el último prompt escrito por la persona.
    textos: list[str] = []
    archivos: list[str] = []
    for entrada in reversed(entradas):
        mensaje = entrada.get("message") or {}
        contenido = mensaje.get("content")
        if entrada.get("type") == "user" and isinstance(contenido, str):
            break
        if entrada.get("type") != "assistant" or not isinstance(contenido, list):
            continue
        for bloque in reversed(contenido):
            if bloque.get("type") == "text" and bloque.get("text", "").strip():
                textos.insert(0, bloque["text"].strip())
            elif bloque.get("type") == "tool_use" and bloque.get("name") in HERRAMIENTAS_DE_ARCHIVO:
                ruta = (bloque.get("input") or {}).get("file_path")
                if ruta and ruta not in archivos:
                    archivos.insert(0, ruta)
    return "\n\n".join(textos), archivos


def registrar_prompt(evento: dict) -> None:
    prompt = (evento.get("prompt") or "").strip()
    if not prompt:
        return
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with ruta_bitacora(evento).open("a", encoding="utf-8") as bitacora:
        bitacora.write(f"\n---\n\n## {marca} · Prompt\n\n```text\n{prompt}\n```\n")


def registrar_respuesta(evento: dict) -> None:
    if evento.get("stop_hook_active"):
        return
    transcript = evento.get("transcript_path")
    if not transcript or not Path(transcript).exists():
        return
    texto, archivos = ultima_respuesta(transcript)
    if not texto and not archivos:
        return
    if len(texto) > LIMITE_RESPUESTA:
        texto = texto[:LIMITE_RESPUESTA] + "\n\n[… respuesta recortada …]"
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with ruta_bitacora(evento).open("a", encoding="utf-8") as bitacora:
        bitacora.write(f"\n### {marca} · Respuesta\n\n{texto}\n")
        if archivos:
            lista = "\n".join(f"- `{ruta}`" for ruta in archivos)
            bitacora.write(f"\n**Archivos modificados:**\n\n{lista}\n")


def main() -> None:
    try:
        evento = leer_evento()
        modo = sys.argv[1] if len(sys.argv) > 1 else ""
        if modo == "prompt":
            registrar_prompt(evento)
        elif modo == "respuesta":
            registrar_respuesta(evento)
    except Exception:  # noqa: BLE001 — la bitácora nunca debe frenar a Claude Code
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
