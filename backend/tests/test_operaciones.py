from app.core.security import hash_password
from app.models.user import User


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


def _crear(client, headers, textos: list[str]) -> list[dict]:
    for texto in textos:
        client.post(
            "/api/v1/operaciones",
            headers=headers,
            json={"texto": texto, "moneda": "SOL", "ambito": "Nacional"},
        )
    return client.get("/api/v1/operaciones", headers=headers).json()


def test_posicion_se_asigna_al_crear(client):
    headers = _auth_headers(client)
    ops = _crear(client, headers, ["A", "B", "C"])
    assert [o["posicion"] for o in ops] == [1, 2, 3]
    assert [o["texto"] for o in ops] == ["A", "B", "C"]


def test_reordenar_conserva_los_ids(client):
    headers = _auth_headers(client)
    ops = _crear(client, headers, ["A", "B", "C"])
    ids = {o["texto"]: o["id"] for o in ops}

    # Se manda la lista al revés: cambia la posición, no el id.
    payload = [
        {
            "id": o["id"],
            "posicion": i,
            "texto": o["texto"],
            "moneda": o["moneda"],
            "ambito": o["ambito"],
            "tags": o["tags"],
            "respeta_filtro": o["respeta_filtro"],
            "aplica_retencion": o["aplica_retencion"],
        }
        for i, o in enumerate(reversed(ops), start=1)
    ]
    result = client.put("/api/v1/operaciones", headers=headers, json=payload).json()

    assert [o["texto"] for o in result] == ["C", "B", "A"]
    assert [o["posicion"] for o in result] == [1, 2, 3]
    assert {o["texto"]: o["id"] for o in result} == ids


def test_eliminar_renumera_sin_huecos(client):
    headers = _auth_headers(client)
    ops = _crear(client, headers, ["A", "B", "C"])

    client.delete(f"/api/v1/operaciones/{ops[1]['id']}", headers=headers)
    result = client.get("/api/v1/operaciones", headers=headers).json()

    assert [(o["texto"], o["posicion"]) for o in result] == [("A", 1), ("C", 2)]


def test_mover_una_operacion_corre_las_demas(client):
    headers = _auth_headers(client)
    ops = _crear(client, headers, ["A", "B", "C"])

    # C pasa a la primera posición; A y B bajan un lugar.
    client.put(
        f"/api/v1/operaciones/{ops[2]['id']}", headers=headers, json={"posicion": 1}
    )
    result = client.get("/api/v1/operaciones", headers=headers).json()

    assert [(o["texto"], o["posicion"]) for o in result] == [
        ("C", 1), ("A", 2), ("B", 3)
    ]
