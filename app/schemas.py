from pydantic import BaseModel


class InstanceCreate(BaseModel):
    name: str
    api_url: str


class InstanceUpdate(BaseModel):
    name: str | None = None
    api_url: str | None = None
    api_key: str | None = None


class HiddenMonitorToggle(BaseModel):
    instance_id: int
    kuma_monitor_id: int


class IncidentCreate(BaseModel):
    title_de: str
    title_en: str
    content_de: str = ""
    content_en: str = ""
    severity: str = "warning"
    active: bool = True
    occurred_at: str | None = None


class IncidentUpdate(BaseModel):
    title_de: str | None = None
    title_en: str | None = None
    content_de: str | None = None
    content_en: str | None = None
    severity: str | None = None
    active: bool | None = None
    occurred_at: str | None = None


class IncidentOut(BaseModel):
    id: int
    title_de: str
    title_en: str
    content_de: str
    content_en: str
    severity: str
    active: bool
    occurred_at: str
    position: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class IncidentReorder(BaseModel):
    incident_ids: list[int]

    class Config:
        from_attributes = True


class FooterItemCreate(BaseModel):
    label_de: str
    label_en: str
    url: str = ""


class FooterItemUpdate(BaseModel):
    label_de: str | None = None
    label_en: str | None = None
    url: str | None = None


class FooterItemOut(BaseModel):
    id: int
    label_de: str
    label_en: str
    url: str
    position: int

    class Config:
        from_attributes = True


class FooterReorder(BaseModel):
    item_ids: list[int]


class InstanceReorder(BaseModel):
    instance_ids: list[int]


class SettingUpdate(BaseModel):
    key: str
    value: str | None = None
