from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.cache import monitor_fetcher, get_status_data
from app.i18n import t, TRANSLATIONS
from app.kuma_reader import read_kuma_instance
from app.ws import ws_manager
from app.schemas import (
    InstanceCreate, InstanceUpdate,
    IncidentCreate, IncidentUpdate, IncidentOut,
    FooterItemCreate, FooterItemUpdate, FooterItemOut, FooterReorder,
    HiddenMonitorToggle, SettingUpdate, InstanceReorder, IncidentReorder,
)
from app.services import instance_service, incident_service, settings_service, monitor_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- Admin page ---

@router.get("/", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "t": t,
        "translations": TRANSLATIONS,
        "user": request.headers.get("X-Forwarded-User", ""),
        "email": request.headers.get("X-Forwarded-Email", ""),
    })


# --- Instances ---

@router.get("/api/instances")
async def api_list_instances(db: Session = Depends(get_db)):
    instances = instance_service.list_instances(db)
    status_data = await get_status_data()
    reachability = {inst["id"]: inst["reachable"] for inst in status_data.get("instances", [])}

    return [
        {
            "id": inst.id,
            "name": inst.name,
            "api_url": inst.api_url,
            "reachable": reachability.get(inst.id),
            "position": inst.position,
        }
        for inst in instances
    ]


@router.post("/api/instances")
async def api_create_instance(data: InstanceCreate, db: Session = Depends(get_db)):
    inst, api_key = instance_service.create_instance(db, data.model_dump())
    await monitor_fetcher.force_fetch()
    return {"id": inst.id, "name": inst.name, "api_key": api_key}


@router.put("/api/instances/{instance_id}")
async def api_update_instance(instance_id: int, data: InstanceUpdate, db: Session = Depends(get_db)):
    inst = instance_service.update_instance(db, instance_id, data.model_dump(exclude_unset=True))
    if not inst:
        raise HTTPException(404)
    await monitor_fetcher.force_fetch()
    return {"id": inst.id, "name": inst.name}


@router.delete("/api/instances/{instance_id}")
async def api_delete_instance(instance_id: int, db: Session = Depends(get_db)):
    if not instance_service.delete_instance(db, instance_id):
        raise HTTPException(404)
    await monitor_fetcher.force_fetch()
    return {"ok": True}


@router.post("/api/instances/{instance_id}/test")
async def api_test_instance(instance_id: int, db: Session = Depends(get_db)):
    inst = instance_service.get_instance(db, instance_id)
    if not inst:
        raise HTTPException(404)
    api_key = instance_service.decrypt_api_key(inst.api_key)
    result = await read_kuma_instance(api_url=inst.api_url, api_key=api_key)
    return {
        "reachable": result.reachable,
        "monitor_count": len(result.monitors),
        "error": result.error,
    }


@router.post("/api/instances/{instance_id}/regenerate-key")
async def api_regenerate_key(instance_id: int, db: Session = Depends(get_db)):
    inst = instance_service.get_instance(db, instance_id)
    if not inst:
        raise HTTPException(404)
    new_key = instance_service.generate_api_key()
    inst.api_key = instance_service.encrypt_api_key(new_key)
    db.commit()
    return {"api_key": new_key}


@router.post("/api/instances/reorder")
async def api_reorder_instances(data: InstanceReorder, db: Session = Depends(get_db)):
    instance_service.reorder_instances(db, data.instance_ids)
    await monitor_fetcher.force_fetch()
    return {"ok": True}


# --- Monitors (visibility) ---


@router.get("/api/monitors")
async def api_list_monitors(db: Session = Depends(get_db)):
    """List ALL monitors from all Kuma instances (including hidden) for admin."""
    hidden_set = monitor_service.get_hidden_set(db)
    instances = instance_service.list_instances(db)

    result = []
    for inst in instances:
        api_key = instance_service.decrypt_api_key(inst.api_key)
        data = await read_kuma_instance(api_url=inst.api_url, api_key=api_key)
        if not data.reachable:
            continue

        # Build tree from ALL monitors (not filtered by hidden)
        all_by_id = {m.id: m for m in data.monitors}
        children_map: dict[int | None, list] = {}
        for m in data.monitors:
            children_map.setdefault(m.parent, []).append(m)

        def collect(parent_id, depth=0):
            for m in sorted(children_map.get(parent_id, []), key=lambda x: x.name.lower()):
                hb = data.heartbeats.get(m.id)
                status = {0: "down", 1: "up", 2: "pending", 3: "maintenance"}.get(hb.status, "unknown") if hb else "unknown"
                if m.type == "group":
                    status = "group"
                result.append({
                    "id": f"{inst.id}-{m.id}",
                    "kuma_id": m.id,
                    "instance_id": inst.id,
                    "instance_name": inst.name,
                    "name": m.name,
                    "status": status,
                    "hidden": (inst.id, m.id) in hidden_set,
                    "depth": depth,
                    "has_children": m.id in children_map,
                })
                collect(m.id, depth + 1)

        collect(None)
    return result


@router.post("/api/monitors/hide")
async def api_hide_monitor(data: HiddenMonitorToggle, db: Session = Depends(get_db)):
    monitor_service.hide_monitor(db, data.instance_id, data.kuma_monitor_id)
    await monitor_fetcher.force_fetch()
    return {"ok": True}


@router.delete("/api/monitors/hide")
async def api_unhide_monitor(data: HiddenMonitorToggle, db: Session = Depends(get_db)):
    monitor_service.unhide_monitor(db, data.instance_id, data.kuma_monitor_id)
    await monitor_fetcher.force_fetch()
    return {"ok": True}


# --- Incidents ---

@router.get("/api/incidents")
def api_list_incidents(db: Session = Depends(get_db)):
    return [
        IncidentOut.model_validate(inc)
        for inc in incident_service.list_incidents(db)
    ]


@router.post("/api/incidents")
async def api_create_incident(data: IncidentCreate, db: Session = Depends(get_db)):
    inc = incident_service.create_incident(db, data.model_dump())
    await _broadcast_incident("created", inc)
    return IncidentOut.model_validate(inc)


@router.put("/api/incidents/{incident_id}")
async def api_update_incident(incident_id: int, data: IncidentUpdate, db: Session = Depends(get_db)):
    inc = incident_service.update_incident(db, incident_id, data.model_dump(exclude_unset=True))
    if not inc:
        raise HTTPException(404)
    await _broadcast_incident("updated", inc)
    return IncidentOut.model_validate(inc)


@router.delete("/api/incidents/{incident_id}")
async def api_delete_incident(incident_id: int, db: Session = Depends(get_db)):
    if not incident_service.delete_incident(db, incident_id):
        raise HTTPException(404)
    await ws_manager.broadcast({"type": "incident", "action": "deleted", "id": incident_id})
    return {"ok": True}


async def _broadcast_incident(action: str, inc):
    await ws_manager.broadcast({
        "type": "incident",
        "action": action,
        "incident": IncidentOut.model_validate(inc).model_dump(),
    })


@router.post("/api/incidents/reorder")
async def api_reorder_incidents(data: IncidentReorder, db: Session = Depends(get_db)):
    incident_service.reorder_incidents(db, data.incident_ids)
    return {"ok": True}


# --- Footer ---

@router.get("/api/footer")
def api_list_footer(db: Session = Depends(get_db)):
    return [FooterItemOut.model_validate(f) for f in settings_service.list_footer_items(db)]


@router.post("/api/footer")
async def api_create_footer(data: FooterItemCreate, db: Session = Depends(get_db)):
    item = settings_service.create_footer_item(db, data.model_dump())
    return FooterItemOut.model_validate(item)


@router.put("/api/footer/{item_id}")
async def api_update_footer(item_id: int, data: FooterItemUpdate, db: Session = Depends(get_db)):
    item = settings_service.update_footer_item(db, item_id, data.model_dump(exclude_unset=True))
    if not item:
        raise HTTPException(404)
    return FooterItemOut.model_validate(item)


@router.delete("/api/footer/{item_id}")
async def api_delete_footer(item_id: int, db: Session = Depends(get_db)):
    if not settings_service.delete_footer_item(db, item_id):
        raise HTTPException(404)
    return {"ok": True}


@router.post("/api/footer/reorder")
async def api_reorder_footer(data: FooterReorder, db: Session = Depends(get_db)):
    settings_service.reorder_footer_items(db, data.item_ids)
    return {"ok": True}


# --- Settings ---

@router.get("/api/settings")
def api_get_settings(db: Session = Depends(get_db)):
    return settings_service.get_all_settings(db)


@router.put("/api/settings")
async def api_update_setting(data: SettingUpdate, db: Session = Depends(get_db)):
    settings_service.set_setting(db, data.key, data.value)
    return {"ok": True}



@router.post("/api/settings/logo/{variant}")
async def api_upload_logo(variant: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if variant not in ("light", "dark"):
        raise HTTPException(400, "variant must be 'light' or 'dark'")
    content = await file.read()
    path = settings_service.save_logo(file.filename, content, variant)
    settings_service.set_setting(db, f"logo_{variant}", path)
    await monitor_fetcher.force_fetch()
    return {"path": path}
