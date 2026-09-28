"""Carga de la lista de agentes de retención desde un archivo."""
import io

import openpyxl

from app.core.security import hash_password
from app.models.user import User


def _auth_headers(client) -> dict:
    from app.api.deps import get_db

    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    db.add(User(username="tester", hashed_password=hash_password("s3cret"), is_admin=True))
    db.commit()
    try:
        next(gen)
    except StopIteration:
        pass
    resp = client.post("/api/v1/auth/login", json={"username": "tester", "password": "s3cret"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_importar_rucs_de_un_excel(client):
    """La lista de agentes de retención se carga desde un Excel: se toman los
    RUC de cualquier columna, sin repetir, y se descarta lo demás."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["N°", "RUC", "Razón social"])
    ws.append([1, "20100047218", "BANCO DE CREDITO"])
    ws.append([2, 20100053455, "INTERBANK"])          # como número
    ws.append([3, " 20100047218 ", "REPETIDO"])
    ws.append([4, "10078481", "DNI de 8 dígitos, no es RUC"])
    ws.append([5, "53", "muy corto"])
    ws.append([6, 2.34075e12, "del exterior, guardado como número por Excel"])
    buf = io.BytesIO()
    wb.save(buf)

    headers = _auth_headers(client)
    r = client.post(
        "/api/v1/retencion/rucs/importar",
        headers=headers,
        files={"archivo": ("padron.xlsx", buf.getvalue())},
    )
    assert r.status_code == 200
    datos = r.json()
    # Entran todos los identificadores de la columna, tengan o no 11 dígitos:
    # los proveedores del exterior no usan RUC peruano.
    assert datos["rucs"] == [
        "20100047218", "20100053455", "10078481", "53", "2340750000000",
    ]
    assert datos["repetidos"] == 1          # el que venía repetido
    # Los que no son de 11 dígitos se marcan para revisarlos.
    assert datos["dudosos"] == ["10078481", "53", "2340750000000"]

    # Un archivo sin ningún RUC se rechaza con un mensaje claro.
    vacio = openpyxl.Workbook()
    vacio.active.append(["sin rucs"])
    buf2 = io.BytesIO()
    vacio.save(buf2)
    r = client.post(
        "/api/v1/retencion/rucs/importar",
        headers=headers,
        files={"archivo": ("x.xlsx", buf2.getvalue())},
    )
    assert r.status_code == 422 and "RUC" in r.json()["detail"]
