"""Ambiente Jinja — separado de main.py para evitar import circular entre
os módulos de rota (mesmo padrão do app/web.py do ERP ContFácil)."""
from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

RAIZ_TEMPLATES = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(RAIZ_TEMPLATES))
templates.env.autoescape = True


def _data_br(valor_iso: str, com_hora: bool = True) -> str:
    if not valor_iso:
        return ""
    try:
        dt = datetime.fromisoformat(valor_iso)
    except ValueError:
        return valor_iso
    return dt.strftime("%d/%m/%Y %H:%M") if com_hora else dt.strftime("%d/%m/%Y")


def _iniciais(nome: str) -> str:
    partes = (nome or "?").strip().split()
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()


templates.env.filters["data_br"] = _data_br
templates.env.filters["iniciais"] = _iniciais


def render(request, nome_template: str, contexto: dict | None = None) -> HTMLResponse:
    contexto = dict(contexto or {})
    contexto["request"] = request
    return templates.TemplateResponse(nome_template, contexto)
