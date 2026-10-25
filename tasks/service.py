"""Lógica de negocio del recurso `tasks`.

Las rutas no acceden al repositorio directamente: pasan por aquí. Esta capa es la
única que conoce `repository.py` y la que decide cuándo algo es un error de
dominio (usando `core.errors`).
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = ZoneInfo("America/Mexico_City")


def local_date(instant: datetime) -> date:
    """Fecha que corresponde a un instante en la zona de negocio."""
    return instant.astimezone(BUSINESS_TIMEZONE).date()


def current_date() -> date:
    """Única vía para obtener "hoy"; los tests la sustituyen."""
    return local_date(datetime.now(timezone.utc))
