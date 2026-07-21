from sqlalchemy.orm import Session

from app.models.retencion_config import RetencionConfig
from app.services.agente_config_service import normalizar_ruc

DEFAULT_TIPO_CAMBIO = 3.75


class RetencionConfigService:
    """Gestiona la fila única de configuración de retención."""

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> RetencionConfig:
        cfg = self.db.get(RetencionConfig, 1)
        if cfg is None:
            cfg = RetencionConfig(
                id=1, activo=True, rucs=[], tipo_cambio=DEFAULT_TIPO_CAMBIO
            )
            self.db.add(cfg)
            self.db.commit()
            self.db.refresh(cfg)
        return cfg

    def save(self, activo, rucs: list[str], tipo_cambio) -> RetencionConfig:
        cfg = self.get()
        cfg.activo = bool(activo)
        limpios: list[str] = []
        for r in rucs or []:
            n = normalizar_ruc(r)
            if n and n not in limpios:
                limpios.append(n)
        cfg.rucs = limpios
        try:
            tc = float(tipo_cambio)
        except (TypeError, ValueError):
            tc = DEFAULT_TIPO_CAMBIO
        cfg.tipo_cambio = tc if tc > 0 else DEFAULT_TIPO_CAMBIO
        self.db.commit()
        self.db.refresh(cfg)
        return cfg

    def as_dict(self) -> dict:
        cfg = self.get()
        return {
            "activo": bool(cfg.activo),
            "rucs": list(cfg.rucs or []),
            "tipo_cambio": float(cfg.tipo_cambio or DEFAULT_TIPO_CAMBIO),
        }
