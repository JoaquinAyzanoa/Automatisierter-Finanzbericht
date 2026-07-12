import pandas as pd

from app.services.merge_service import avance_path, process_merge
from app.services.proveedores_service import process_proveedores
from app.services.reporteador_service import process_reporteador


def test_merge_por_ruc_y_numero(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.REPORTS_DIR", str(tmp_path))

    # Reporteador limpiado: F001-0001 (cruza) y F001-0002 (solo reporteador).
    rep = (
        "NUMERO\tORD_COMPRA\tPRODUCTO\tREGISTRO\tRUC\tDETRACCION\n"
        "F001-0001\t\t40001 SERVICIO A\t2026010001\t20100000001\t12\n"
        "F001-0002\t\t40002 SERVICIO B\t2026010002\t20100000002\t7\n"
    ).encode("utf-8")
    process_reporteador("reporteador.csv", rep)

    # Proveedores: una fila que cruza (USD) y otra que no (SOL).
    dolares = (
        "NUMERO\tRUC\tMONTO\n"
        "F001-0001\t20100000001\t100\n"
    ).encode("utf-8")
    soles = (
        "NUMERO\tRUC\tMONTO\n"
        "F001-9999\t20999999999\t50\n"
    ).encode("utf-8")
    process_proveedores("dolares.csv", dolares, "soles.csv", soles)

    result = process_merge()
    # Left (manda Proveedores): solo las 2 filas de proveedores.
    assert result["rows"] == 2

    df = pd.read_excel(avance_path(), dtype=str).fillna("")
    assert "MONEDA" in df.columns
    assert "ORD_COMPRA" in df.columns
    assert "PRODUCTO" in df.columns
    assert "DETRACCION" in df.columns

    # Fila que cruza (USD) recibe datos del reporteador.
    fila_match = df[df["NUMERO"] == "F001-0001"].iloc[0]
    assert fila_match["MONEDA"] == "USD"
    assert fila_match["ORD_COMPRA"] == "10040001"
    assert fila_match["PRODUCTO"] == "SERVICIO A"
    assert fila_match["DETRACCION"] == "12"

    # Fila de proveedores que no cruza queda sin datos del reporteador,
    # pero DETRACCION se completa con 0.
    fila_prov = df[df["NUMERO"] == "F001-9999"].iloc[0]
    assert fila_prov["MONEDA"] == "SOL"
    assert fila_prov["ORD_COMPRA"] == ""
    assert fila_prov["PRODUCTO"] == ""
    assert fila_prov["DETRACCION"] == "0"

    # La fila que solo existe en el reporteador NO se agrega (manda proveedores).
    assert "F001-0002" not in list(df["NUMERO"])


def test_merge_no_multiplica_filas_de_proveedores(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.REPORTS_DIR", str(tmp_path))

    # Reporteador con la MISMA llave (RUC+NUMERO) repetida en dos filas.
    rep = (
        "NUMERO\tORD_COMPRA\tPRODUCTO\tREGISTRO\tRUC\tDETRACCION\n"
        "F001-0001\t\t40001 SERVICIO A\t2026010001\t20100000001\t12\n"
        "F001-0001\t99\tOTRO PRODUCTO\t2026010009\t20100000001\t99\n"
    ).encode("utf-8")
    process_reporteador("reporteador.csv", rep)

    dolares = (
        "NUMERO\tRUC\tMONTO\nF001-0001\t20100000001\t100\n"
    ).encode("utf-8")
    soles = (
        "NUMERO\tRUC\tMONTO\nF001-0002\t20100000002\t50\n"
    ).encode("utf-8")
    process_proveedores("dolares.csv", dolares, "soles.csv", soles)

    result = process_merge()
    # 2 filas de proveedores -> 2 filas en el merge (no se duplican).
    assert result["rows"] == 2


def test_merge_acepta_alias_n_documento(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.REPORTS_DIR", str(tmp_path))

    rep = (
        "NUMERO\tORD_COMPRA\tPRODUCTO\tREGISTRO\tRUC\tDETRACCION\n"
        "F001-0001\t\t40001 SERVICIO A\t2026010001\t20100000001\t12\n"
    ).encode("utf-8")
    process_reporteador("reporteador.csv", rep)

    # Proveedores con la columna "N° DOCUMENTO" en vez de NUMERO.
    dolares = (
        "N° DOCUMENTO\tRUC\tMONTO\n"
        "F001-0001\t20100000001\t100\n"
    ).encode("utf-8")
    soles = (
        "N° DOCUMENTO\tRUC\tMONTO\n"
        "F001-0002\t20100000002\t50\n"
    ).encode("utf-8")
    process_proveedores("dolares.csv", dolares, "soles.csv", soles)

    result = process_merge()
    assert result["rows"] == 2

    df = pd.read_excel(avance_path(), dtype=str).fillna("")
    # La columna llave se normaliza a NUMERO.
    assert "NUMERO" in df.columns
    fila = df[df["NUMERO"] == "F001-0001"].iloc[0]
    assert fila["MONEDA"] == "USD"
    assert fila["ORD_COMPRA"] == "10040001"
    assert fila["PRODUCTO"] == "SERVICIO A"
