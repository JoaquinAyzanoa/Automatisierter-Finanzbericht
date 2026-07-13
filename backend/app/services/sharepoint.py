"""Construcción de enlaces a las facturas (PDF) en SharePoint/OneDrive.

El usuario pega la URL de la carpeta del mes (la vista `onedrive.aspx?id=...`).
De ahí extraemos el host y la ruta de la carpeta, y como cada PDF se llama igual
que el N° de Registro, el enlace de una factura es:

    https://{host}{ruta_carpeta}/{registro}.pdf   (URL-encoded)
"""

from urllib.parse import parse_qs, quote, urlparse


def carpeta_desde_url(folder_url: str | None) -> tuple[str, str] | None:
    """Devuelve (host, ruta_carpeta) desde la URL de la carpeta, o None.

    Acepta tanto la vista `...onedrive.aspx?id=<ruta>` como una URL directa a
    la carpeta (usa entonces el propio path).
    """
    if not folder_url or not folder_url.strip():
        return None
    u = urlparse(folder_url.strip())
    if not u.netloc:
        return None
    ruta = None
    qs = parse_qs(u.query)
    if "id" in qs and qs["id"]:
        ruta = qs["id"][0]  # parse_qs ya decodifica el %2F -> /
    elif u.path:
        ruta = u.path
    if not ruta:
        return None
    return u.netloc, ruta.rstrip("/")


def mes_de_registro(registro: str) -> int | None:
    """Mes (1-12) codificado en el registro AAAAMM...., o None."""
    solo_digitos = "".join(c for c in str(registro) if c.isdigit())
    if len(solo_digitos) < 6:
        return None
    try:
        mes = int(solo_digitos[4:6])
    except ValueError:
        return None
    return mes if 1 <= mes <= 12 else None


def link_factura(
    link_principal: str | None, meses: dict, registro: str
) -> str | None:
    """Enlace al PDF `{registro}.pdf` dentro de la carpeta del mes que le toca.

    Usa la carpeta general (`link_principal`) + el nombre de carpeta del mes del
    registro (según `meses`). Devuelve None si falta configuración o el mes no
    está mapeado (en ese caso la celda SUSTENTO queda en blanco).
    """
    base = carpeta_desde_url(link_principal)
    if base is None or not registro:
        return None
    mes = mes_de_registro(registro)
    if mes is None:
        return None
    carpeta_mes = (meses or {}).get(str(mes))
    if not carpeta_mes:
        return None
    host, ruta = base
    return f"https://{host}{quote(f'{ruta}/{carpeta_mes}/{registro}.pdf')}"
