"""Rutas HTTP del recurso `reports`."""
from fastapi import APIRouter, Header, Query, status
from pydantic import BaseModel

from core import errors
from reports import export, service
from reports.schemas import Report, ReportCreate

router = APIRouter(prefix="/reports", tags=["reports"])


class ExportResult(BaseModel):
    filename: str


@router.get("", response_model=list[Report])
def list_reports(user_id: int | None = Query(default=None)) -> list[Report]:
    return service.list_reports(user_id=user_id)


@router.get("/export", response_model=ExportResult, summary="Exporta los reportes a un archivo")
def export_reports(
    fmt: str = Query(default="csv"),
    x_export_token: str = Header(default=""),
) -> ExportResult:
    """Genera un archivo de exportación en el directorio del servidor.

    Requiere la cabecera ``X-Export-Token``. Devuelve solo el nombre del archivo
    generado, nunca su ruta completa.
    """
    if not export.check_token(x_export_token):
        raise errors.unauthorized("token de exportación inválido")
    return ExportResult(filename=export.export_to_file(fmt))


@router.get("/{report_id}", response_model=Report)
def get_report(report_id: int) -> Report:
    return service.get_report(report_id)


@router.post("", response_model=Report, status_code=status.HTTP_201_CREATED)
def create_report(data: ReportCreate) -> Report:
    return service.create_report(data)
