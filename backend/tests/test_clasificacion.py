import pandas as pd

from app.models.operacion import Operacion
from app.services.clasificacion_service import (
    clasificar_dataframe,
    clasificar_merge,
    es_ruc_nacional,
)
from app.services.excel_utils import write_xlsx


def _operaciones() -> list[Operacion]:
    definicion = [
        ("Pago masivo proveedores", "SOL", "Nacional"),
        ("Pago masivo proveedores", "USD", "Nacional"),
        ("Pagos varios", "SOL", "Nacional"),
        ("Pagos varios", "USD", "Nacional"),
        ("Pagos servicios", "SOL", "Nacional"),
        ("Materia Prima Exterior", "USD", "Exterior"),
    ]
    return [
        Operacion(posicion=i, texto=texto, moneda=moneda, ambito=ambito)
        for i, (texto, moneda, ambito) in enumerate(definicion, start=1)
    ]


def test_es_ruc_nacional():
    assert es_ruc_nacional("10075701158")
    assert es_ruc_nacional("20550372640")
    assert not es_ruc_nacional("12345")  # muy corto
    assert not es_ruc_nacional("30550372640")  # no empieza con 10/20
    assert not es_ruc_nacional("2055037264X")  # no numérico
    assert not es_ruc_nacional("205503726400")  # 12 dígitos


def test_clasificar_dataframe():
    df = pd.DataFrame(
        {
            "MONEDA": ["SOL", "USD", "SOL", "USD"],
            "RUC": [
                "20550372640",  # nacional
                "10075701158",  # nacional
                "44444444444",  # 11 dígitos pero empieza 44 -> exterior
                "999",  # exterior
            ],
            "MONTO": ["100", "200", "300", "400"],
        }
    )
    out = clasificar_dataframe(df, _operaciones())
    assert out.columns[0] == "OPERACION"
    assert list(out["OPERACION"]) == [
        "Operación 1 - Pago masivo proveedores",
        "Operación 2 - Pago masivo proveedores",
        # Exterior + SOL: ninguna operación combina ese ámbito con esa moneda.
        "Sin categoría",
        "Operación 6 - Materia Prima Exterior",
    ]


def test_clasificar_merge_parsea_fec_vcto(tmp_path):
    df = pd.DataFrame(
        {
            "MONEDA": ["SOL", "USD"],
            "RUC": ["20550372640", "10075701158"],
            "MONTO": ["100", "200"],
            "FEC. VCTO": ["03/04/2026", "15/12/2026"],
        }
    )
    path = tmp_path / "merge.xlsx"
    write_xlsx(df, path, "Merge")

    result = clasificar_merge(path, _operaciones())
    assert result["fecha_columna"] == "FEC. VCTO"
    # dd/mm/yyyy -> ISO
    assert result["filas"][0]["__fec_vcto"] == "2026-04-03"
    assert result["filas"][1]["__fec_vcto"] == "2026-12-15"
    # Posición asignada por fila.
    assert result["filas"][0]["__pos"] == 1  # nacional + SOL
    assert result["filas"][1]["__pos"] == 2  # nacional + USD
    # Lista de operaciones para el desplegable.
    assert result["operaciones"][0] == {
        "pos": 1,
        "texto": "Pago masivo proveedores",
        "moneda": "SOL",
        "ambito": "Nacional",
        "respeta_filtro": True,
        "aplica_retencion": True,
    }
    assert len(result["operaciones"]) == 6


def test_tag_prevalece_respetando_moneda(tmp_path):
    ops = [
        Operacion(posicion=1, texto="Pago masivo", moneda="SOL", ambito="Nacional", tags=[]),
        Operacion(posicion=2, texto="Pago masivo", moneda="USD", ambito="Nacional", tags=[]),
        Operacion(
            posicion=3,
            texto="Pagos servicios",
            moneda="SOL",
            ambito="Nacional",
            tags=["transporte"],
        ),
        Operacion(posicion=4, texto="X", moneda="SOL", ambito="Nacional", tags=[]),
        Operacion(posicion=5, texto="Y", moneda="SOL", ambito="Nacional", tags=[]),
        Operacion(posicion=6, texto="Exterior", moneda="USD", ambito="Exterior", tags=[]),
    ]
    df = pd.DataFrame(
        {
            "MONEDA": ["SOL", "USD"],
            "RUC": ["20550372640", "20550372640"],  # ambos nacionales
            "PRODUCTO": [
                "SERVICIO DE TRANSPORTE LOCAL",
                "SERVICIO DE TRANSPORTE LOCAL",
            ],
            "MONTO": ["100", "200"],
        }
    )
    path = tmp_path / "merge.xlsx"
    write_xlsx(df, path, "Merge")

    result = clasificar_merge(path, ops)
    # SOL + tag "transporte" -> op 3 (prevalece sobre el default op 1).
    assert result["filas"][0]["__pos"] == 3
    # USD: la op con ese tag es SOL, no aplica -> default nacional+USD -> op 2.
    assert result["filas"][1]["__pos"] == 2
