from app.services.detalle_export import _agrupar_agentes

RELACIONADO = "20605123741"   # p. ej. un operador logístico en 'relacionados'
AGENTE = "20213635531"


def _fila(ruc, prov, oc, pos=7, manual=False, tipo="01"):
    return {"RUC": ruc, "PROVEEDOR": prov, "ORD_COMPRA": oc, "MONEDA": "USD",
            "TIPO": tipo, "__pos": pos, "__manual": manual}


def test_relacionado_vigente_consolida_la_oc():
    filas = [
        _fila(RELACIONADO, "OZEAN PERU SAC", "31637-4"),
        _fila("831197135", "NOURYON LLC", "31637-4"),
    ]
    ocs, _nombres, _rucs, grupos = _agrupar_agentes(filas, [AGENTE], [RELACIONADO])
    assert ocs == {"31637-4"}
    assert len(grupos[("31637-4", "USD")]) == 2


def test_factura_pasada_a_otros_no_arrastra_a_su_oc():
    """Si la factura del relacionado se pasó a 'Otros' (no se paga ahora), la
    importación de la misma O/C sigue en su operación y no va a agentes."""
    for relacionado in (
        _fila(RELACIONADO, "OZEAN PERU SAC", "31637-4", pos=None, manual=True),  # a mano
        _fila(RELACIONADO, "OZEAN PERU SAC", "31637-4", pos=None),               # sin operación
    ):
        filas = [relacionado, _fila("831197135", "NOURYON LLC", "31637-4")]
        ocs, _nombres, _rucs, grupos = _agrupar_agentes(filas, [AGENTE], [RELACIONADO])
        assert ocs == set()
        assert grupos == {}


def test_tipo_21_sigue_yendo_a_agentes_por_si_sola():
    filas = [_fila("7066921000", "COSCO SHIPPING", "", tipo="21")]
    _ocs, _nombres, _rucs, grupos = _agrupar_agentes(filas, [AGENTE], [RELACIONADO])
    assert list(grupos) == [("", "USD")]
