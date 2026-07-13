import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.operacion import Operacion
from app.models.proceso import Proceso
from app.repositories.proceso_repository import ProcesoRepository
from app.services import clasificacion_service, detalle_export, merge_service
from app.services.excel_utils import ProcesamientoError
from app.services.sharepoint_config_service import SharepointConfigService

DESCARGA_FILENAME = "informe_clasificado.xlsx"


class ProcesoNotFoundError(Exception):
    """Raised when a proceso does not exist."""


class ProcesoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProcesoRepository(db)

    # ---- Creación (al Procesar) --------------------------------------------
    def crear_desde_merge(self, operaciones: list[Operacion]) -> Proceso:
        path = merge_service.avance_path()
        if not path.exists():
            raise ProcesamientoError("No hay un merge para guardar.")

        data = clasificacion_service.clasificar_merge(path, operaciones)
        for i, fila in enumerate(data["filas"]):
            fila["__id"] = i

        payload = json.dumps(data, ensure_ascii=False)
        now = datetime.now(timezone.utc)
        proceso_id = hashlib.sha256(
            f"{now.isoformat()}-{payload}".encode("utf-8")
        ).hexdigest()[:12]

        proceso = Proceso(
            id=proceso_id,
            created_at=now,
            updated_at=now,
            n_filas=len(data["filas"]),
            payload=payload,
        )
        return self.repo.create(proceso)

    # ---- Lectura ------------------------------------------------------------
    def _detalle(self, proceso: Proceso) -> dict:
        data = json.loads(proceso.payload)
        return {
            "id": proceso.id,
            "created_at": proceso.created_at,
            "updated_at": proceso.updated_at,
            "fecha_inicio": proceso.fecha_inicio,
            "fecha_final": proceso.fecha_final,
            **data,
        }

    def obtener(self, proceso_id: str) -> dict:
        proceso = self.repo.get(proceso_id)
        if proceso is None:
            raise ProcesoNotFoundError(proceso_id)
        return self._detalle(proceso)

    def latest(self) -> dict | None:
        proceso = self.repo.latest()
        return self._detalle(proceso) if proceso else None

    def list(self) -> list[Proceso]:
        return self.repo.list()

    # ---- Guardar (autoguardado) --------------------------------------------
    def guardar(
        self,
        proceso_id: str,
        fecha_inicio: str | None,
        fecha_final: str | None,
        overrides: dict[str, int | None],
    ) -> Proceso:
        proceso = self.repo.get(proceso_id)
        if proceso is None:
            raise ProcesoNotFoundError(proceso_id)

        data = json.loads(proceso.payload)

        # Aplicar reasignaciones manuales sobre __pos.
        ov = {int(k): v for k, v in overrides.items()}
        for fila in data["filas"]:
            if fila.get("__id") in ov:
                fila["__pos"] = ov[fila["__id"]]

        proceso.payload = json.dumps(data, ensure_ascii=False)
        proceso.fecha_inicio = fecha_inicio or None
        proceso.fecha_final = fecha_final or None
        proceso.updated_at = datetime.now(timezone.utc)
        return self.repo.save(proceso)

    # ---- Guardar + descargar ------------------------------------------------
    def guardar_y_generar_xlsx(
        self,
        proceso_id: str,
        fecha_inicio: str | None,
        fecha_final: str | None,
        overrides: dict[str, int],
    ) -> Path:
        proceso = self.guardar(proceso_id, fecha_inicio, fecha_final, overrides)
        data = json.loads(proceso.payload)
        output_path = Path(settings.REPORTS_DIR) / DESCARGA_FILENAME
        sharepoint_cfg = SharepointConfigService(self.db).as_dict()
        return detalle_export.construir_detalle(
            data,
            proceso.fecha_inicio,
            proceso.fecha_final,
            output_path,
            sharepoint_cfg,
        )
