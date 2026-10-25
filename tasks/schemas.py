"""Schemas Pydantic del recurso `tasks`.

Aquí vive solo la validación de formato (longitudes, rangos, tipos, recorte de
espacios). Las reglas de dominio (fecha pasada, asignado inexistente) viven en
`service.py`.
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class Task(TaskBase):
    """Tarea tal como la devuelve la API."""

    id: int
    created_at: datetime
