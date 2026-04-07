from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.cache import get_status_data
from app.i18n import t, TRANSLATIONS
from app.services.settings_service import get_setting
from app.database import SessionLocal

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def status_page(request: Request):
    db = SessionLocal()
    try:
        default_lang = get_setting(db, "default_lang") or "en"
    finally:
        db.close()

    data = await get_status_data()

    # Determine overall status
    all_statuses = []
    for inst in data.get("instances", []):
        _collect_statuses(inst.get("groups", []), all_statuses)

    if not all_statuses:
        overall = "unknown"
    elif any(s == "down" for s in all_statuses):
        overall = "down"
    elif any(s in ("pending", "degraded", "unreachable") for s in all_statuses):
        overall = "degraded"
    else:
        overall = "up"

    # Detect oauth2-proxy user (present when accessed via SSO)
    proxy_user = request.headers.get("X-Forwarded-Email") or request.headers.get("X-Forwarded-User") or ""

    return templates.TemplateResponse("status.html", {
        "request": request,
        "data": data,
        "overall": overall,
        "default_lang": default_lang,
        "t": t,
        "translations": TRANSLATIONS,
        "proxy_user": proxy_user,
    })


@router.get("/api/status")
async def status_api():
    return await get_status_data()


def _collect_statuses(nodes, out: list):
    for n in nodes:
        out.append(n.get("status", "unknown"))
        _collect_statuses(n.get("children", []), out)
