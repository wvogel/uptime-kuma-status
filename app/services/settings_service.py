from pathlib import Path
from sqlalchemy.orm import Session
from app.models import Setting, FooterItem
from app.config import DATA_DIR


LOGO_DIR = DATA_DIR / "logos"


def get_setting(db: Session, key: str) -> str | None:
    s = db.query(Setting).filter(Setting.key == key).first()
    return s.value if s else None


def get_all_settings(db: Session) -> dict[str, str]:
    return {s.key: s.value for s in db.query(Setting).all()}


def set_setting(db: Session, key: str, value: str | None):
    s = db.query(Setting).filter(Setting.key == key).first()
    if s:
        s.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB


def save_logo(filename: str, content: bytes, variant: str) -> str:
    if len(content) > MAX_LOGO_SIZE:
        raise ValueError("Logo file too large (max 2 MB)")
    ext = Path(filename).suffix.lower() or ".png"
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        raise ValueError(f"Invalid file type: {ext}")
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    dest = LOGO_DIR / f"logo_{variant}{ext}"
    dest.write_bytes(content)
    return f"/data/logos/logo_{variant}{ext}"


# Footer items

def list_footer_items(db: Session) -> list[FooterItem]:
    return db.query(FooterItem).order_by(FooterItem.position).all()


def create_footer_item(db: Session, data: dict) -> FooterItem:
    max_pos = db.query(FooterItem.position).order_by(FooterItem.position.desc()).first()
    position = (max_pos[0] + 1) if max_pos else 0
    item = FooterItem(position=position, **data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_footer_item(db: Session, item_id: int, data: dict) -> FooterItem | None:
    item = db.query(FooterItem).filter(FooterItem.id == item_id).first()
    if not item:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_footer_item(db: Session, item_id: int) -> bool:
    item = db.query(FooterItem).filter(FooterItem.id == item_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def reorder_footer_items(db: Session, item_ids: list[int]):
    for pos, item_id in enumerate(item_ids):
        item = db.query(FooterItem).filter(FooterItem.id == item_id).first()
        if item:
            item.position = pos
    db.commit()
