import pandas as pd

from app.services.proveedores_service import avance_path, process_proveedores


def test_combina_y_agrega_moneda(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.REPORTS_DIR", str(tmp_path))

    dolares = (
        "PROVEEDOR\tRUC\tMONTO\n"
        "PROVEEDOR DEMO A\t20100000001\t100\n"
        "PROVEEDOR DEMO B\t20100000002\t200\n"
    ).encode("utf-8")
    soles = (
        "PROVEEDOR\tRUC\tMONTO\n"
        "PROVEEDOR DEMO C\t20100000003\t300\n"
    ).encode("utf-8")

    result = process_proveedores(
        "DOLARES PROVEEDORES.csv", dolares, "SOLES PROVEEDORES.csv", soles
    )
    assert result["rows"] == 3
    assert result["dolares_rows"] == 2
    assert result["soles_rows"] == 1

    df = pd.read_excel(avance_path(), dtype=str).fillna("")
    # MONEDA como primera columna, seguida de las columnas originales.
    assert list(df.columns) == ["MONEDA", "PROVEEDOR", "RUC", "MONTO"]
    assert list(df["MONEDA"]) == ["USD", "USD", "SOL"]
    assert list(df["PROVEEDOR"]) == [
        "PROVEEDOR DEMO A",
        "PROVEEDOR DEMO B",
        "PROVEEDOR DEMO C",
    ]


def test_moneda_existente_se_reemplaza(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.REPORTS_DIR", str(tmp_path))

    # El archivo ya trae una columna MONEDA con otro valor; debe reemplazarse.
    dolares = "MONEDA\tPROVEEDOR\nX\tPROVEEDOR DEMO A\n".encode("utf-8")
    soles = "MONEDA\tPROVEEDOR\nY\tPROVEEDOR DEMO C\n".encode("utf-8")

    process_proveedores("dolares.csv", dolares, "soles.csv", soles)

    df = pd.read_excel(avance_path(), dtype=str).fillna("")
    assert list(df.columns) == ["MONEDA", "PROVEEDOR"]
    assert list(df["MONEDA"]) == ["USD", "SOL"]
