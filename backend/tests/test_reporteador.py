import pandas as pd

from app.services.reporteador_service import (
    _clean_ord_and_producto,
    avance_path,
    process_reporteador,
)


def test_caso_a_numero_simple_antepone_100():
    ord_compra, producto = _clean_ord_and_producto(
        "", "40001 SERVICIO DE PRUEBA  UNO"
    )
    assert ord_compra == "10040001"
    # Se conservan los espacios internos del texto.
    assert producto == "SERVICIO DE PRUEBA  UNO"


def test_caso_b_numero_con_guiones_no_cambia():
    ord_compra, producto = _clean_ord_and_producto("", "40002-3 PRODUCTO DEMO DOS")
    assert ord_compra == "40002-3"
    assert producto == "PRODUCTO DEMO DOS"


def test_caso_c_sin_numero_queda_vacio():
    ord_compra, producto = _clean_ord_and_producto("", "SERVICIO SIN CODIGO DEMO")
    assert ord_compra == ""
    assert producto == "SERVICIO SIN CODIGO DEMO"


def test_ord_compra_existente_no_se_modifica():
    ord_compra, producto = _clean_ord_and_producto("55500", "40001 SERVICIO DEMO")
    assert ord_compra == "55500"
    assert producto == "SERVICIO DEMO"


def test_process_reporteador_pipeline_con_duplicados(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.REPORTS_DIR", str(tmp_path))

    # La columna de detracción llega como DETRA_TASA en el origen.
    header = "MONEDA\tNUMERO\tORD_COMPRA\tPRODUCTO\tPROVEEDOR\tREGISTRO\tRUC\tTOTAL_DOCU\tDETRA_TASA"
    filas = [
        # Caso A
        "DOLARES AMERICANOS\tF001-0001\t\t40001 SERVICIO DE PRUEBA  UNO\tPROVEEDOR DEMO UNO S.A.\t2026010001\t20100000001\t100\t12",
        # Caso B
        "SOLES\tF001-0002\t\t40002-3 PRODUCTO DEMO DOS\tPROVEEDOR DEMO DOS E.I.R.L.\t2026010002\t20200000002\t200\t8",
        # Caso C
        "SOLES\tF001-0003\t\tSERVICIO SIN CODIGO DEMO\tPROVEEDOR DEMO TRES S.A.C.\t2026010003\t20300000003\t300\t",
        # Duplicado exacto del Caso A -> debe eliminarse
        "DOLARES AMERICANOS\tF001-0001\t\t40001 SERVICIO DE PRUEBA  UNO\tPROVEEDOR DEMO UNO S.A.\t2026010001\t20100000001\t100\t12",
    ]
    content = ("\n".join([header, *filas])).encode("utf-8")

    result = process_reporteador("reporteador.csv", content)
    assert result["rows"] == 3
    assert result["duplicates_removed"] == 1

    df = pd.read_excel(avance_path(), dtype=str).fillna("")
    assert list(df.columns) == [
        "NUMERO",
        "ORD_COMPRA",
        "PRODUCTO",
        "REGISTRO",
        "RUC",
        "DETRACCION",
    ]
    assert len(df) == 3

    assert df.iloc[0]["NUMERO"] == "F001-0001"
    assert df.iloc[0]["ORD_COMPRA"] == "10040001"
    assert df.iloc[0]["PRODUCTO"] == "SERVICIO DE PRUEBA  UNO"
    assert df.iloc[0]["REGISTRO"] == "2026010001"
    assert df.iloc[0]["RUC"] == "20100000001"
    # DETRACCION viene del Reporteador; vacía -> 0.
    assert df.iloc[0]["DETRACCION"] == "12"
    assert df.iloc[1]["DETRACCION"] == "8"
    assert df.iloc[2]["DETRACCION"] == "0"

    assert df.iloc[1]["ORD_COMPRA"] == "40002-3"
    assert df.iloc[1]["PRODUCTO"] == "PRODUCTO DEMO DOS"

    assert df.iloc[2]["ORD_COMPRA"] == ""
    assert df.iloc[2]["PRODUCTO"] == "SERVICIO SIN CODIGO DEMO"
