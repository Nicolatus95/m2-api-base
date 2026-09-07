"""Rutas HTTP del recurso `reports`."""
import tempfile

from fastapi import APIRouter, Query, status

from reports import export, service
from reports.schemas import Report, ReportCreate

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[Report])
def list_reports(user_id: int | None = Query(default=None)) -> list[Report]:
    return service.list_reports(user_id=user_id)


@router.get("/export")
def export_reports(fmt: str = "csv", dest: str = tempfile.gettempdir(), token: str = ""):
    if not export.check_token(token):
        return {"error": "token invalido"}
    try:
        ruta = export.export_to_disk(fmt, dest)
    except Exception:
        return {"error": "fallo la exportacion"}
    return {"ruta": ruta}


@router.get("/{report_id}", response_model=Report)
def get_report(report_id: int) -> Report:
    return service.get_report(report_id)


@router.post("", response_model=Report, status_code=status.HTTP_201_CREATED)
def create_report(data: ReportCreate) -> Report:
    return service.create_report(data)
