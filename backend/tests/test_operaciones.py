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
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_crud_operaciones(client):
    headers = _auth_headers(client)

    # Vacío al inicio.
    assert client.get("/api/v1/operaciones", headers=headers).json() == []

    # Crear.
    resp = client.post(
        "/api/v1/operaciones",
        headers=headers,
        json={"texto": "Compras locales", "moneda": "USD", "ambito": "Exterior"},
    )
    assert resp.status_code == 201
    op = resp.json()
    assert op["texto"] == "Compras locales"
    assert op["moneda"] == "USD"
    assert op["ambito"] == "Exterior"
    op_id = op["id"]

    # Listar.
    lista = client.get("/api/v1/operaciones", headers=headers).json()
    assert len(lista) == 1

    # Actualizar.
    resp = client.put(
        f"/api/v1/operaciones/{op_id}",
        headers=headers,
        json={"texto": "Compras nacionales", "moneda": "SOL", "ambito": "Nacional"},
    )
    assert resp.status_code == 200
    assert resp.json()["texto"] == "Compras nacionales"
    assert resp.json()["moneda"] == "SOL"
    assert resp.json()["ambito"] == "Nacional"

    # Eliminar.
    assert client.delete(f"/api/v1/operaciones/{op_id}", headers=headers).status_code == 204
    assert client.get("/api/v1/operaciones", headers=headers).json() == []


def test_reemplazar_todas(client):
    headers = _auth_headers(client)
    client.post(
        "/api/v1/operaciones",
        headers=headers,
        json={"texto": "vieja", "moneda": "SOL"},
    )

    # Reemplazar toda la lista de una vez (guardado en bloque).
    resp = client.put(
        "/api/v1/operaciones",
        headers=headers,
        json=[
            {"texto": "A", "moneda": "SOL"},
            {"texto": "B", "moneda": "USD"},
        ],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert [o["texto"] for o in data] == ["A", "B"]
    assert [o["moneda"] for o in data] == ["SOL", "USD"]

    # Persistió.
    assert len(client.get("/api/v1/operaciones", headers=headers).json()) == 2

    # Lista vacía borra todo.
    assert client.put("/api/v1/operaciones", headers=headers, json=[]).json() == []


def test_operaciones_requiere_auth(client):
    assert client.get("/api/v1/operaciones").status_code == 401


def test_moneda_invalida_rechazada(client):
    headers = _auth_headers(client)
    resp = client.post(
        "/api/v1/operaciones",
        headers=headers,
        json={"texto": "X", "moneda": "EUR"},
    )
    assert resp.status_code == 422
