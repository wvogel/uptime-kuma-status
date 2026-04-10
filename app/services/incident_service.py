from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Incident, IncidentUpdate


def list_incidents(db: Session, active_only: bool = False) -> list[Incident]:
    q = db.query(Incident)
    if active_only:
        q = q.filter(Incident.active == True)
    return q.order_by(Incident.position, Incident.occurred_at.desc()).all()


def get_incident(db: Session, incident_id: int) -> Incident | None:
    return db.query(Incident).filter(Incident.id == incident_id).first()


def create_incident(db: Session, data: dict) -> Incident:
    max_pos = db.query(Incident.position).order_by(Incident.position.desc()).first()
    position = (max_pos[0] + 1) if max_pos else 0
    if "occurred_at" not in data or not data["occurred_at"]:
        data["occurred_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
    inc = Incident(position=position, **data)
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return inc


def update_incident(db: Session, incident_id: int, data: dict) -> Incident | None:
    inc = get_incident(db, incident_id)
    if not inc:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(inc, key, value)
    inc.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(inc)
    return inc


def delete_incident(db: Session, incident_id: int) -> bool:
    inc = get_incident(db, incident_id)
    if not inc:
        return False
    db.delete(inc)
    db.commit()
    return True


def reorder_incidents(db: Session, incident_ids: list[int]):
    for pos, inc_id in enumerate(incident_ids):
        inc = db.query(Incident).filter(Incident.id == inc_id).first()
        if inc:
            inc.position = pos
    db.commit()


def list_updates(db: Session, incident_id: int) -> list[IncidentUpdate]:
    return db.query(IncidentUpdate).filter(
        IncidentUpdate.incident_id == incident_id
    ).order_by(IncidentUpdate.created_at).all()


def create_update(db: Session, incident_id: int, data: dict) -> IncidentUpdate | None:
    inc = get_incident(db, incident_id)
    if not inc:
        return None
    if "created_at" not in data or not data.get("created_at"):
        data["created_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
    upd = IncidentUpdate(incident_id=incident_id, **data)
    db.add(upd)
    inc.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(upd)
    return upd


def delete_update(db: Session, update_id: int) -> bool:
    upd = db.query(IncidentUpdate).filter(IncidentUpdate.id == update_id).first()
    if not upd:
        return False
    db.delete(upd)
    db.commit()
    return True
