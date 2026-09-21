import json
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.macro_archivo import MacroArchivo
from app.repositories.proceso_repository import ProcesoRepository
from app.services import detalle_export, macro_bcp
from app.services.excel_utils import ProcesamientoError
from app.services.proceso_service import ProcesoNotFoundError, ProcesoService

TIPOS = ("plantilla_SOL", "plantilla_USD", "bd_SOL", "bd_USD")
MONEDAS = ("SOL", "USD")
_NOMBRE_TIPO = {"plantilla": "la plantilla de la macro", "bd": "la base de cuentas"}
_ETIQUETA_MONEDA = {"SOL": "Soles", "USD": "Dolares"}
# Las operaciones de pago masivo se reconocen por su nombre en Configuración.
_PAGO_MASIVO = "PAGO MASIVO"


def nombre_archivo(moneda: str, fecha: date) -> str:
    """Mismo nombre que se venía usando: 'Pago proveedores BCP Soles _150926.xlsm'."""
    return f"Pago proveedores BCP {_ETIQUETA_MONEDA[moneda]} _{fecha.strftime('%d%m%y')}.xlsm"


class MacroService:
    """Archivos de las macros de pago masivo del BCP y su generación a partir de
    un proceso ya guardado."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Archivos ---------------------------------------------------------------
    def estado(self) -> list[dict]:
        guardados = {a.tipo: a for a in self.db.query(MacroArchivo).all()}
        return [
            {
                "tipo": tipo,
                "nombre": guardados[tipo].nombre if tipo in guardados else None,
                "detalle": guardados[tipo].detalle if tipo in guardados else "",
                "subido_en": guardados[tipo].subido_en if tipo in guardados else None,
            }
            for tipo in TIPOS
        ]

    def subir(self, tipo: str, nombre: str, contenido: bytes) -> dict:
        """Valida el archivo según su tipo y lo guarda (reemplaza al anterior)."""
        if tipo not in TIPOS:
            raise ProcesamientoError(f"Tipo de archivo desconocido: {tipo}.")
        if tipo.startswith("plantilla"):
            detalle = f"admite {macro_bcp.validar_plantilla(contenido)} filas"
        else:
            cuentas = macro_bcp.leer_base_cuentas(contenido)
            if not cuentas:
                raise ProcesamientoError("La base de cuentas no tiene ningún RUC.")
            detalle = f"{len(cuentas)} cuentas"
        archivo = self.db.get(MacroArchivo, tipo) or MacroArchivo(tipo=tipo)
        archivo.nombre = nombre or tipo
        archivo.contenido = contenido
        archivo.detalle = detalle
        archivo.subido_en = datetime.now(timezone.utc)
        self.db.add(archivo)
        self.db.commit()
        return next(e for e in self.estado() if e["tipo"] == tipo)

    def _contenido(self, tipo: str) -> bytes | None:
        archivo = self.db.get(MacroArchivo, tipo)
        return archivo.contenido if archivo else None

    # ---- Abonos -----------------------------------------------------------------
    def _facturas_pago_masivo(self, proceso_id: str) -> dict[str, list[tuple[dict, float]]]:
        """Facturas de 'Pago masivo proveedores' por moneda, con su Neto: el mismo
        cálculo y el mismo orden (por proveedor) que en el informe."""
        proceso = ProcesoRepository(self.db).get(proceso_id)
        if proceso is None:
            raise ProcesoNotFoundError(proceso_id)
        data = json.loads(proceso.payload)
        calc = detalle_export.preparar_calculo(
            data, tipo_cambio=proceso.tipo_cambio,
            **ProcesoService(self.db).contexto_calculo(),
        )
        operaciones = {o["pos"]: o for o in data.get("operaciones", [])}
        por_moneda: dict[str, list[dict]] = {m: [] for m in MONEDAS}
        for pos, filas in calc["grupos"].items():
            op = operaciones.get(pos) or {}
            moneda = str(op.get("moneda") or "").strip().upper()
            if _PAGO_MASIVO in str(op.get("texto") or "").upper() and moneda in por_moneda:
                por_moneda[moneda].extend(filas)
        return {
            moneda: [
                (f, detalle_export._neto(f, calc["ret_cfg"]))
                for f in sorted(filas, key=detalle_export._key_prov)
            ]
            for moneda, filas in por_moneda.items()
        }

    def _abonos(self, proceso_id: str) -> dict[str, list[macro_bcp.Abono]]:
        facturas = self._facturas_pago_masivo(proceso_id)
        abonos = {}
        for moneda in MONEDAS:
            base = self._contenido(f"bd_{moneda}")
            cuentas = macro_bcp.leer_base_cuentas(base) if base else {}
            abonos[moneda] = macro_bcp.armar_abonos(facturas[moneda], cuentas)
        return abonos

    def vista_previa(self, proceso_id: str) -> dict:
        abonos = self._abonos(proceso_id)
        monedas = []
        for moneda in MONEDAS:
            lista = abonos[moneda]
            faltan = [
                _NOMBRE_TIPO[t] for t in ("plantilla", "bd")
                if self._contenido(f"{t}_{moneda}") is None
            ]
            monedas.append({
                "moneda": moneda,
                "abonos": [
                    {
                        "ruc": a.ruc, "nombre": a.nombre, "tipo_cuenta": a.tipo_cuenta,
                        "cuenta": a.cuenta, "en_bd": a.en_bd, "total": a.total,
                        "documentos": [{"numero": d.numero, "monto": d.monto} for d in a.documentos],
                    }
                    for a in lista
                ],
                "total": round(sum(a.total for a in lista), 2),
                "n_documentos": sum(len(a.documentos) for a in lista),
                "sin_cuenta": sum(1 for a in lista if not a.en_bd),
                "faltan": faltan,
            })
        return {"proceso_id": proceso_id, "monedas": monedas}

    def generar(self, proceso_id: str, moneda: str, fecha: date) -> tuple[bytes, str]:
        plantilla = self._contenido(f"plantilla_{moneda}")
        if plantilla is None:
            raise ProcesamientoError(
                f"Falta subir la plantilla de la macro en {_ETIQUETA_MONEDA[moneda].lower()}."
            )
        abonos = self._abonos(proceso_id)[moneda]
        if not abonos:
            raise ProcesamientoError(
                f"El proceso no tiene pagos masivos en {_ETIQUETA_MONEDA[moneda].lower()}."
            )
        contenido = macro_bcp.generar_macro(plantilla, abonos, moneda, fecha)
        return contenido, nombre_archivo(moneda, fecha)
