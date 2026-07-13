from app.core.security import hash_password
from app.models.user import User
from app.services import sharepoint
from app.services.sharepoint_config_service import DEFAULT_MESES

_LINK = (
    "https://renasa2021-my.sharepoint.com/personal/j_onmicrosoft_com/"
    "_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fj%5Fonmicrosoft%5Fcom%2F"
    "Documents%2FCompras%2F2026%2F1%2E%20COMPRAS"
)


def test_link_factura_usa_carpeta_del_mes_del_registro():
    julio = sharepoint.link_factura(_LINK, DEFAULT_MESES, "2026070022")
    junio = sharepoint.link_factura(_LINK, DEFAULT_MESES, "2026060343")
    assert julio.endswith("/7.%20JULIO/2026070022.pdf")
    assert junio.endswith("/6.%20JUNIO/2026060343.pdf")


def test_link_factura_sin_config_o_mes_devuelve_none():
    assert sharepoint.link_factura(None, DEFAULT_MESES, "2026070022") is None
    assert sharepoint.link_factura(_LINK, {}, "2026070022") is None  # mes sin carpeta
    assert sharepoint.link_factura(_LINK, DEFAULT_MESES, "") is None


def _auth_headers(client) -> dict:
    from app.api.deps import get_db

    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    db.add(
        User(username="sp", hashed_password=hash_password("s3cret"), is_admin=True)
    )
    db.commit()
    try:
        next(gen)
    except StopIteration:
        pass
    resp = client.post(
        "/api/v1/auth/login", json={"username": "sp", "password": "s3cret"}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_sharepoint_config_get_defaults_and_save(client):
    headers = _auth_headers(client)

    # Por defecto trae los 12 meses y sin link.
    cfg = client.get("/api/v1/sharepoint", headers=headers).json()
    assert cfg["link_principal"] is None
    assert cfg["meses"]["7"] == "7. JULIO"

    # Guardar y releer.
    nuevo = {"link_principal": _LINK, "meses": {**DEFAULT_MESES, "7": "07 JULIO"}}
    saved = client.put("/api/v1/sharepoint", headers=headers, json=nuevo).json()
    assert saved["link_principal"] == _LINK
    assert saved["meses"]["7"] == "07 JULIO"
    releido = client.get("/api/v1/sharepoint", headers=headers).json()
    assert releido["meses"]["7"] == "07 JULIO"
