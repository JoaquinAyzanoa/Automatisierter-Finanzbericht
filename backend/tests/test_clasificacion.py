import pandas as pd

from app.models.operacion import Operacion
from app.services.clasificacion_service import (
    clasificar_dataframe,
    clasificar_merge,
    es_ruc_nacional,
)
from app.services.excel_utils import write_xlsx


def _operaciones() -> list[Operacion]:
    textos = [
        "Pago masivo proveedores",  # 1
        "Pago masivo proveedores",  # 2
        "Pagos varios",  # 3
        "Pagos varios",  # 4
        "Pagos servicios",  # 5
        "Materia Prima Exterior",  # 6
    ]
    return [Operacion(texto=t, moneda="SOL", ambito="Nacional") for t in textos]


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
        "Operación 6 - Materia Prima Exterior",
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
    }
    assert len(result["operaciones"]) == 6
