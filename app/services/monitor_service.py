from sqlalchemy.orm import Session
from app.models import HiddenMonitor


def list_hidden(db: Session, instance_id: int | None = None) -> list[HiddenMonitor]:
    q = db.query(HiddenMonitor)
    if instance_id is not None:
        q = q.filter(HiddenMonitor.instance_id == instance_id)
    return q.all()


def hide_monitor(db: Session, instance_id: int, kuma_monitor_id: int) -> HiddenMonitor:
    existing = db.query(HiddenMonitor).filter(
        HiddenMonitor.instance_id == instance_id,
        HiddenMonitor.kuma_monitor_id == kuma_monitor_id,
    ).first()
    if existing:
        return existing
    h = HiddenMonitor(instance_id=instance_id, kuma_monitor_id=kuma_monitor_id)
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def unhide_monitor(db: Session, instance_id: int, kuma_monitor_id: int) -> bool:
    h = db.query(HiddenMonitor).filter(
        HiddenMonitor.instance_id == instance_id,
        HiddenMonitor.kuma_monitor_id == kuma_monitor_id,
    ).first()
    if not h:
        return False
    db.delete(h)
    db.commit()
    return True


def get_hidden_set(db: Session) -> set[tuple[int, int]]:
    return {
        (h.instance_id, h.kuma_monitor_id)
        for h in db.query(HiddenMonitor).all()
    }
