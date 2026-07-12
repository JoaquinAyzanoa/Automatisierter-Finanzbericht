import pandas as pd

from app.core.security import hash_password
from app.models.user import User
from app.services import merge_service
from app.services.excel_utils import write_xlsx


def _auth_headers(client) -> dict:
    from app.api.deps import get_db

    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    db.add(
        User(username="tester", hashed_password=hash_password("s3cret"), is_admin=True)
    )
    db.commit()
    try:
        next(gen)
    except StopIteration:
        pass

    resp = client.post(
        "/api/v1/auth/login", json={"username": "tester", "password": "s3cret"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _crear_merge_avance():
    df = pd.DataFrame(
        {
            "MONEDA": ["SOL", "USD"],
            "NUMERO": ["F001-0001", "F001-0002"],
            "RUC": ["20550372640", "10075701158"],
            "MONTO": ["100", "200"],
            "FEC. VCTO": ["03/04/2026", "15/12/2026"],
        }
    )
    write_xlsx(df, merge_service.avance_path(), "Merge")


def test_flujo_proceso(client):
    headers = _auth_headers(client)

    # Operaciones (posiciones 1..6).
    for i in range(6):
        client.post(
            "/api/v1/operaciones",
            headers=headers,
            json={"texto": f"Op {i + 1}", "moneda": "SOL", "ambito": "Nacional"},
        )

    # Sin merge aún: no se puede crear proceso.
    assert client.post("/api/v1/procesos", headers=headers).status_code == 422

    _crear_merge_avance()

    # Crear proceso.
    resp = client.post("/api/v1/procesos", headers=headers)
    assert resp.status_code == 200
    proceso_id = resp.json()["id"]
    assert len(proceso_id) == 12

    # Aparece en el historial.
    lista = client.get("/api/v1/procesos", headers=headers).json()
    assert len(lista) == 1
    assert lista[0]["id"] == proceso_id
    assert lista[0]["n_filas"] == 2

    # latest y detalle traen las filas clasificadas.
    latest = client.get("/api/v1/procesos/latest", headers=headers).json()
    assert latest["id"] == proceso_id
    assert latest["filas"][0]["__pos"] == 1  # nacional + SOL
    assert latest["filas"][1]["__pos"] == 2  # nacional + USD

    # Autoguardado (sin descarga): reasignar una y mover otra a "Otros" (null).
    g = client.post(
        f"/api/v1/procesos/{proceso_id}/guardar",
        headers=headers,
        json={
            "fecha_inicio": "2026-02-01",
            "fecha_final": None,
            "overrides": {"1": 4, "0": None},
        },
    )
    assert g.status_code == 200
    assert "updated_at" in g.json()
    guardado = client.get(f"/api/v1/procesos/{proceso_id}", headers=headers).json()
    assert guardado["fecha_inicio"] == "2026-02-01"
    assert guardado["filas"][1]["__pos"] == 4
    assert guardado["filas"][0]["__pos"] is None  # movida a "Otros"

    # Guardar (reasignar fila 0 -> op 3) + rango de fechas y descargar.
    dl = client.post(
        f"/api/v1/procesos/{proceso_id}/descargar",
        headers=headers,
        json={
            "fecha_inicio": "2026-01-01",
            "fecha_final": "2026-06-30",
            "overrides": {"0": 3},
        },
    )
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("application/vnd.openxmlformats")

    # El estado quedó guardado.
    actualizado = client.get(f"/api/v1/procesos/{proceso_id}", headers=headers).json()
    assert actualizado["fecha_inicio"] == "2026-01-01"
    assert actualizado["fecha_final"] == "2026-06-30"
    assert actualizado["filas"][0]["__pos"] == 3  # reasignación persistida
