"""Exportación de reportes a texto (CSV) y, opcionalmente, a un archivo.

El token de acceso se lee de la variable de entorno ``EXPORT_API_TOKEN``; no se
guarda en el código. La escritura a disco se limita a un directorio permitido.
"""
import csv
import hmac
import io
import os
from pathlib import Path

from core import errors
from reports import repository

_EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports")).resolve()


def check_token(provided: str) -> bool:
    """Compara el token recibido con el configurado, en tiempo constante.

    Devuelve ``False`` si no hay token configurado en el entorno.
    """
    expected = os.getenv("EXPORT_API_TOKEN")
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided, expected)


def render(fmt: str) -> str:
    """Serializa todos los reportes al formato pedido.

    Args:
        fmt: ``"csv"``. Cualquier otro valor levanta ``invalid_request``.

    Returns:
        El contenido serializado como texto.
    """
    if fmt != "csv":
        raise errors.invalid_request(f"formato no soportado: {fmt!r}")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "user_id", "title"])
    for report in repository.list_all():
        writer.writerow([report.id, report.user_id, report.title])
    return buffer.getvalue()


def export_to_file(fmt: str) -> str:
    """Escribe la exportación en ``EXPORT_DIR`` y devuelve solo el nombre del archivo.

    No acepta rutas del cliente: el destino es siempre el directorio permitido.
    """
    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    nombre = f"reports.{fmt}"
    (_EXPORT_DIR / nombre).write_text(render(fmt), encoding="utf-8")
    return nombre
