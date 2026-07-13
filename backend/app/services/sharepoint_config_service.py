from sqlalchemy.orm import Session

from app.models.sharepoint_config import SharepointConfig

DEFAULT_MESES: dict[str, str] = {
    "1": "1. ENERO",
    "2": "2. FEBRERO",
    "3": "3. MARZO",
    "4": "4. ABRIL",
    "5": "5. MAYO",
    "6": "6. JUNIO",
    "7": "7. JULIO",
    "8": "8. AGOSTO",
    "9": "9. SEPTIEMBRE",
    "10": "10. OCTUBRE",
    "11": "11. NOVIEMBRE",
    "12": "12. DICIEMBRE",
}


class SharepointConfigService:
    """Gestiona la fila única de configuración de SharePoint."""

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> SharepointConfig:
        cfg = self.db.get(SharepointConfig, 1)
        if cfg is None:
            cfg = SharepointConfig(id=1, link_principal=None, meses=dict(DEFAULT_MESES))
            self.db.add(cfg)
            self.db.commit()
            self.db.refresh(cfg)
        return cfg

    def save(self, link_principal: str | None, meses: dict[str, str]) -> SharepointConfig:
        cfg = self.get()
        cfg.link_principal = (link_principal or "").strip() or None
        cfg.meses = meses or dict(DEFAULT_MESES)
        self.db.commit()
        self.db.refresh(cfg)
        return cfg

    def as_dict(self) -> dict:
        cfg = self.get()
        return {"link_principal": cfg.link_principal, "meses": cfg.meses or {}}
