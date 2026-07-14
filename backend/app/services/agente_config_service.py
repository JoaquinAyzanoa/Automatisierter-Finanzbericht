import re

from sqlalchemy.orm import Session

from app.models.agente_config import AgenteAduanaConfig

# RUCs de agentes aduaneros por defecto (se pueden editar en Configuración).
DEFAULT_RUCS: list[str] = ["20510541724", "20213635531", "20563315068"]


def normalizar_ruc(ruc) -> str:
    """RUC como texto sin decimales sobrantes ni espacios ('20510541724.0' -> '20510541724')."""
    return re.sub(r"\.0$", "", str(ruc).strip())


class AgenteConfigService:
    """Gestiona la fila única de configuración de agentes de aduana."""

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> AgenteAduanaConfig:
        cfg = self.db.get(AgenteAduanaConfig, 1)
        if cfg is None:
            cfg = AgenteAduanaConfig(id=1, rucs=list(DEFAULT_RUCS), relacionados=[])
            self.db.add(cfg)
            self.db.commit()
            self.db.refresh(cfg)
        return cfg

    @staticmethod
    def _limpiar(rucs: list[str]) -> list[str]:
        """Normaliza, quita vacíos y duplicados conservando el orden."""
        limpios: list[str] = []
        for r in rucs or []:
            n = normalizar_ruc(r)
            if n and n not in limpios:
                limpios.append(n)
        return limpios

    def save(self, rucs: list[str], relacionados: list[str]) -> AgenteAduanaConfig:
        cfg = self.get()
        cfg.rucs = self._limpiar(rucs)
        cfg.relacionados = self._limpiar(relacionados)
        self.db.commit()
        self.db.refresh(cfg)
        return cfg

    def as_list(self) -> list[str]:
        return list(self.get().rucs or [])

    def relacionados_list(self) -> list[str]:
        return list(self.get().relacionados or [])
