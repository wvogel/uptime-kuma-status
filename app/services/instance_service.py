import logging
import secrets
from datetime import datetime
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app import config
from app.models import KumaInstance

log = logging.getLogger(__name__)


def _fernet() -> Fernet | None:
    try:
        key = config.SECRET_KEY.encode() if isinstance(config.SECRET_KEY, str) else config.SECRET_KEY
        return Fernet(key)
    except Exception:
        log.warning("SECRET_KEY is not a valid Fernet key - API keys stored unencrypted")
        return None


def encrypt_api_key(api_key: str) -> str:
    f = _fernet()
    if f:
        return f.encrypt(api_key.encode()).decode()
    return api_key


def decrypt_api_key(encrypted: str) -> str:
    f = _fernet()
    if f:
        try:
            return f.decrypt(encrypted.encode()).decode()
        except Exception:
            return encrypted
    return encrypted


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def list_instances(db: Session) -> list[KumaInstance]:
    return db.query(KumaInstance).order_by(KumaInstance.position, KumaInstance.name).all()


def get_instance(db: Session, instance_id: int) -> KumaInstance | None:
    return db.query(KumaInstance).filter(KumaInstance.id == instance_id).first()


def create_instance(db: Session, data: dict) -> tuple[KumaInstance, str]:
    """Returns (instance, plaintext_api_key)."""
    max_pos = db.query(KumaInstance.position).order_by(KumaInstance.position.desc()).first()
    position = (max_pos[0] + 1) if max_pos else 0
    api_key = generate_api_key()
    inst = KumaInstance(
        name=data["name"],
        api_url=data["api_url"],
        api_key=encrypt_api_key(api_key),
        position=position,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst, api_key


def update_instance(db: Session, instance_id: int, data: dict) -> KumaInstance | None:
    inst = get_instance(db, instance_id)
    if not inst:
        return None
    for key, value in data.items():
        if value is None:
            continue
        if key == "api_key":
            setattr(inst, key, encrypt_api_key(value))
        else:
            setattr(inst, key, value)
    inst.updated_at = datetime.utcnow().isoformat()
    db.commit()
    db.refresh(inst)
    return inst


def delete_instance(db: Session, instance_id: int) -> bool:
    inst = get_instance(db, instance_id)
    if not inst:
        return False
    db.delete(inst)
    db.commit()
    return True


def reorder_instances(db: Session, instance_ids: list[int]):
    for pos, inst_id in enumerate(instance_ids):
        inst = db.query(KumaInstance).filter(KumaInstance.id == inst_id).first()
        if inst:
            inst.position = pos
    db.commit()
