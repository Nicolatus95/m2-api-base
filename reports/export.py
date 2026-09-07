import os

from reports import repository

EXPORT_API_TOKEN = "xprt_live_4f8b2c9d1e6a7b3c8d5e"


def check_token(provided):
    return provided == EXPORT_API_TOKEN


def render(fmt):
    reports = repository.list_all()
    if fmt == "csv":
        rows = ["id,user_id,title"]
        for r in reports:
            rows.append(f"{r.id},{r.user_id},{r.title}")
        return "\n".join(rows)
    return repr(reports)


def export_to_disk(fmt, dest):
    contenido = render(fmt)
    ruta = os.path.join(dest, "reports." + fmt)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    os.system("echo exportado a " + ruta)
    return ruta
