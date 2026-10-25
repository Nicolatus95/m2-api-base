"""Schemas Pydantic del recurso `tasks`.

Aquí vive solo la validación de formato (longitudes, rangos, tipos, recorte de
espacios). Las reglas de dominio (fecha pasada, asignado inexistente) viven en
`service.py`.
"""
import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# `[0-9]` y no `\d`: `\d` acepta dígitos de cualquier alfabeto Unicode.
DUE_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class TaskBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    due_date: date
    priority: int = Field(default=3, ge=1, le=5, strict=True)
    assignee_id: int | None = Field(default=None, gt=0, strict=True)

    @field_validator("description")
    @classmethod
    def empty_description_is_none(cls, value: str | None) -> str | None:
        return value or None


class TaskCreate(TaskBase):
    """Cuerpo de entrada para crear una tarea."""

    @field_validator("due_date", mode="before")
    @classmethod
    def due_date_is_iso_text(cls, value: object) -> object:
        """Solo texto `YYYY-MM-DD`. Sin esto, el modo laxo de Pydantic convierte
        timestamps Unix (número o texto) y fechas con hora a medianoche. No va en
        `TaskBase` porque el repositorio crea `Task` con un `date` ya validado."""
        if not isinstance(value, str) or not DUE_DATE_PATTERN.fullmatch(value):
            raise ValueError("La fecha límite debe tener el formato YYYY-MM-DD")
        return value


class Task(TaskBase):
    """Tarea tal como la devuelve la API."""

    id: int
    created_at: datetime
