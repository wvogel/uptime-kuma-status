from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class KumaInstance(Base):
    __tablename__ = "kuma_instance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    api_url = Column(Text, nullable=False)
    api_key = Column(Text, nullable=False)  # Fernet-encrypted
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(Text, nullable=False, server_default="(datetime('now'))")
    updated_at = Column(Text, nullable=False, server_default="(datetime('now'))")


class HiddenMonitor(Base):
    __tablename__ = "hidden_monitor"
    __table_args__ = (
        UniqueConstraint("instance_id", "kuma_monitor_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("kuma_instance.id", ondelete="CASCADE"), nullable=False)
    kuma_monitor_id = Column(Integer, nullable=False)


class Incident(Base):
    __tablename__ = "incident"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title_de = Column(Text, nullable=False)
    title_en = Column(Text, nullable=False)
    content_de = Column(Text, nullable=False, default="")
    content_en = Column(Text, nullable=False, default="")
    severity = Column(Text, nullable=False, default="warning")  # info, warning, critical
    active = Column(Boolean, nullable=False, default=True)
    occurred_at = Column(Text, nullable=False, server_default="(datetime('now'))")
    resolved_at = Column(Text, nullable=True)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(Text, nullable=False, server_default="(datetime('now'))")
    updated_at = Column(Text, nullable=False, server_default="(datetime('now'))")


class IncidentUpdate(Base):
    __tablename__ = "incident_update"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incident.id", ondelete="CASCADE"), nullable=False)
    message_de = Column(Text, nullable=False, default="")
    message_en = Column(Text, nullable=False, default="")
    severity = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False, server_default="(datetime('now'))")


class Setting(Base):
    __tablename__ = "setting"

    key = Column(Text, primary_key=True)
    value = Column(Text)


class FooterItem(Base):
    __tablename__ = "footer_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label_de = Column(Text, nullable=False)
    label_en = Column(Text, nullable=False)
    url = Column(Text, nullable=False, default="")
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(Text, nullable=False, server_default="(datetime('now'))")
