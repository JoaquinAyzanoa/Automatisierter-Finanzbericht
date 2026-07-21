import { useEffect, useRef, useState } from "react";

import {
  guardarAgentesConfig,
  guardarRetencionConfig,
  guardarSharepointConfig,
  listarOperaciones,
  obtenerAgentesConfig,
  obtenerRetencionConfig,
  obtenerSharepointConfig,
  reemplazarOperaciones,
  type Ambito,
  type Moneda,
} from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import "./Configuracion.css";

const MESES: { n: string; nombre: string }[] = [
  { n: "1", nombre: "Enero" },
  { n: "2", nombre: "Febrero" },
  { n: "3", nombre: "Marzo" },
  { n: "4", nombre: "Abril" },
  { n: "5", nombre: "Mayo" },
  { n: "6", nombre: "Junio" },
  { n: "7", nombre: "Julio" },
  { n: "8", nombre: "Agosto" },
  { n: "9", nombre: "Septiembre" },
  { n: "10", nombre: "Octubre" },
  { n: "11", nombre: "Noviembre" },
  { n: "12", nombre: "Diciembre" },
];

interface FilaOp {
  id: number;
  texto: string;
  moneda: Moneda;
  ambito: Ambito;
  tags: string[];
  respetaFiltro: boolean;
}

const trashIcon = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" width={17} height={17}>
    <path d="M4 7h16M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m2 0v12a2 2 0 01-2 2H8a2 2 0 01-2-2V7" />
    <path d="M10 11v6M14 11v6" />
  </svg>
);

export function Configuracion() {
  const { token } = useAuth();
  const [operaciones, setOperaciones] = useState<FilaOp[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tempId = useRef(-1);

  // ---- Sharepoint ----
  const [spLink, setSpLink] = useState("");
  const [spMeses, setSpMeses] = useState<Record<string, string>>({});
  const [spSaving, setSpSaving] = useState(false);
  const [spDirty, setSpDirty] = useState(false);
  const [spSaved, setSpSaved] = useState(false);

  // ---- Agentes de aduana ----
  const [agRucs, setAgRucs] = useState<string[]>([]);
  const [agRel, setAgRel] = useState<string[]>([]);
  const [agSaving, setAgSaving] = useState(false);
  const [agDirty, setAgDirty] = useState(false);
  const [agSaved, setAgSaved] = useState(false);

  // ---- Retención ----
  const [retActivo, setRetActivo] = useState(true);
  const [retRucs, setRetRucs] = useState<string[]>([]);
  const [retTC, setRetTC] = useState("3.75");
  const [retSaving, setRetSaving] = useState(false);
  const [retDirty, setRetDirty] = useState(false);
  const [retSaved, setRetSaved] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    listarOperaciones(token)
      .then((ops) => {
        if (!cancelled) {
          setOperaciones(
            ops.map((o) => ({
              id: o.id,
              texto: o.texto,
              moneda: o.moneda,
              ambito: o.ambito,
              tags: o.tags ?? [],
              respetaFiltro: o.respeta_filtro ?? true,
            }))
          );
        }
      })
      .catch(() => {
        if (!cancelled) setError("No se pudieron cargar las operaciones.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    obtenerSharepointConfig(token)
      .then((cfg) => {
        if (!cancelled) {
          setSpLink(cfg.link_principal ?? "");
          setSpMeses(cfg.meses ?? {});
        }
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar la configuración de Sharepoint.");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    obtenerAgentesConfig(token)
      .then((cfg) => {
        if (!cancelled) {
          setAgRucs(cfg.rucs ?? []);
          setAgRel(cfg.relacionados ?? []);
        }
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar la configuración de agentes.");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    obtenerRetencionConfig(token)
      .then((cfg) => {
        if (!cancelled) {
          setRetActivo(cfg.activo ?? true);
          setRetRucs(cfg.rucs ?? []);
          setRetTC(String(cfg.tipo_cambio ?? 3.75));
        }
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar la configuración de retención.");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  function marcarRet() {
    setRetDirty(true);
    setRetSaved(false);
  }

  function setRetRuc(index: number, valor: string) {
    setRetRucs((prev) => prev.map((r, i) => (i === index ? valor : r)));
    marcarRet();
  }

  function agregarRetRuc() {
    setRetRucs((prev) => [...prev, ""]);
    marcarRet();
  }

  function quitarRetRuc(index: number) {
    setRetRucs((prev) => prev.filter((_, i) => i !== index));
    marcarRet();
  }

  async function guardarRetencion() {
    if (!token) return;
    setRetSaving(true);
    setError(null);
    try {
      const cfg = await guardarRetencionConfig(token, {
        activo: retActivo,
        rucs: retRucs.map((r) => r.trim()).filter((r) => r),
        tipo_cambio: parseFloat(retTC) || 3.75,
      });
      setRetActivo(cfg.activo ?? true);
      setRetRucs(cfg.rucs ?? []);
      setRetTC(String(cfg.tipo_cambio ?? 3.75));
      setRetDirty(false);
      setRetSaved(true);
    } catch {
      setError("No se pudo guardar la configuración de retención.");
    } finally {
      setRetSaving(false);
    }
  }

  function setMes(n: string, valor: string) {
    setSpMeses((prev) => ({ ...prev, [n]: valor }));
    setSpDirty(true);
    setSpSaved(false);
  }

  function setRuc(index: number, valor: string) {
    setAgRucs((prev) => prev.map((r, i) => (i === index ? valor : r)));
    setAgDirty(true);
    setAgSaved(false);
  }

  function agregarRuc() {
    setAgRucs((prev) => [...prev, ""]);
    setAgDirty(true);
    setAgSaved(false);
  }

  function quitarRuc(index: number) {
    setAgRucs((prev) => prev.filter((_, i) => i !== index));
    setAgDirty(true);
    setAgSaved(false);
  }

  function setRel(index: number, valor: string) {
    setAgRel((prev) => prev.map((r, i) => (i === index ? valor : r)));
    setAgDirty(true);
    setAgSaved(false);
  }

  function agregarRel() {
    setAgRel((prev) => [...prev, ""]);
    setAgDirty(true);
    setAgSaved(false);
  }

  function quitarRel(index: number) {
    setAgRel((prev) => prev.filter((_, i) => i !== index));
    setAgDirty(true);
    setAgSaved(false);
  }

  async function guardarAgentes() {
    if (!token) return;
    setAgSaving(true);
    setError(null);
    try {
      const cfg = await guardarAgentesConfig(token, {
        rucs: agRucs.map((r) => r.trim()).filter((r) => r),
        relacionados: agRel.map((r) => r.trim()).filter((r) => r),
      });
      setAgRucs(cfg.rucs ?? []);
      setAgRel(cfg.relacionados ?? []);
      setAgDirty(false);
      setAgSaved(true);
    } catch {
      setError("No se pudo guardar la configuración de agentes.");
    } finally {
      setAgSaving(false);
    }
  }

  async function guardarSharepoint() {
    if (!token) return;
    setSpSaving(true);
    setError(null);
    try {
      const cfg = await guardarSharepointConfig(token, {
        link_principal: spLink.trim() || null,
        meses: spMeses,
      });
      setSpLink(cfg.link_principal ?? "");
      setSpMeses(cfg.meses ?? {});
      setSpDirty(false);
      setSpSaved(true);
    } catch {
      setError("No se pudo guardar la configuración de Sharepoint.");
    } finally {
      setSpSaving(false);
    }
  }

  function markDirty() {
    setDirty(true);
    setSaved(false);
  }

  function agregar() {
    setOperaciones((prev) => [
      ...prev,
      {
        id: tempId.current--,
        texto: "",
        moneda: "SOL",
        ambito: "Nacional",
        tags: [],
        respetaFiltro: true,
      },
    ]);
    markDirty();
  }

  function setLocal(id: number, patch: Partial<FilaOp>) {
    setOperaciones((prev) =>
      prev.map((o) => (o.id === id ? { ...o, ...patch } : o))
    );
    markDirty();
  }

  function eliminar(id: number) {
    setOperaciones((prev) => prev.filter((o) => o.id !== id));
    markDirty();
  }

  function agregarTag(id: number, raw: string) {
    const tag = raw.trim();
    if (!tag) return;
    setOperaciones((prev) =>
      prev.map((o) =>
        o.id === id && !o.tags.includes(tag)
          ? { ...o, tags: [...o.tags, tag] }
          : o
      )
    );
    markDirty();
  }

  function quitarTag(id: number, tag: string) {
    setOperaciones((prev) =>
      prev.map((o) =>
        o.id === id ? { ...o, tags: o.tags.filter((t) => t !== tag) } : o
      )
    );
    markDirty();
  }

  async function guardar() {
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      const items = operaciones.map((o) => ({
        texto: o.texto,
        moneda: o.moneda,
        ambito: o.ambito,
        tags: o.tags,
        respeta_filtro: o.respetaFiltro,
      }));
      const result = await reemplazarOperaciones(token, items);
      setOperaciones(
        result.map((o) => ({
          id: o.id,
          texto: o.texto,
          moneda: o.moneda,
          ambito: o.ambito,
          tags: o.tags ?? [],
          respetaFiltro: o.respeta_filtro ?? true,
        }))
      );
      setDirty(false);
      setSaved(true);
    } catch {
      setError("No se pudieron guardar las operaciones.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <p className="panel__lead">
        Define las operaciones disponibles y guarda los cambios.
      </p>

      {error && <div className="config__error">{error}</div>}

      <div className="config__container">
        <div className="config__containerHead">
          <h3>Operaciones</h3>
          <button type="button" className="config__add" onClick={agregar}>
            + Agregar
          </button>
        </div>

        {loading ? (
          <p className="config__empty">Cargando…</p>
        ) : operaciones.length === 0 ? (
          <p className="config__empty">
            No hay operaciones. Usa «Agregar» para crear la primera.
          </p>
        ) : (
          <ul className="config__list">
            {operaciones.map((op, index) => (
              <li key={op.id} className="config__row">
                <span className="config__label">Operación {index + 1}</span>

                <input
                  type="text"
                  className="config__text"
                  placeholder="Descripción de la operación"
                  value={op.texto}
                  onChange={(e) => setLocal(op.id, { texto: e.target.value })}
                />

                <select
                  className="config__select"
                  value={op.moneda}
                  onChange={(e) =>
                    setLocal(op.id, { moneda: e.target.value as Moneda })
                  }
                >
                  <option value="SOL">SOL</option>
                  <option value="USD">USD</option>
                </select>

                <select
                  className="config__select"
                  value={op.ambito}
                  onChange={(e) =>
                    setLocal(op.id, { ambito: e.target.value as Ambito })
                  }
                >
                  <option value="Nacional">Nacional</option>
                  <option value="Exterior">Exterior</option>
                </select>

                <button
                  type="button"
                  className="config__delete"
                  onClick={() => eliminar(op.id)}
                  aria-label={`Eliminar Operación ${index + 1}`}
                >
                  {trashIcon}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="config__container">
        <div className="config__containerHead">
          <h3>Asignaciones especiales</h3>
        </div>

        {operaciones.length === 0 ? (
          <p className="config__empty">
            Primero crea operaciones para asignarles tags.
          </p>
        ) : (
          <ul className="config__list">
            {operaciones.map((op, index) => (
              <li key={op.id} className="config__tagRow">
                <span className="config__tagLabel">
                  {index + 1} - {op.texto || "(sin nombre)"} - {op.moneda}
                </span>
                <select
                  className="config__filtroSelect"
                  value={op.respetaFiltro ? "si" : "no"}
                  onChange={(e) =>
                    setLocal(op.id, { respetaFiltro: e.target.value === "si" })
                  }
                >
                  <option value="si">Respetar filtro de fecha</option>
                  <option value="no">No respetar filtro de fecha</option>
                </select>
                <div className="config__tags">
                  {op.tags.map((tag) => (
                    <span key={tag} className="config__tag">
                      {tag}
                      <button
                        type="button"
                        className="config__tagRemove"
                        onClick={() => quitarTag(op.id, tag)}
                        aria-label={`Quitar ${tag}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                  <input
                    type="text"
                    className="config__tagInput"
                    placeholder="+ tag"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        agregarTag(op.id, e.currentTarget.value);
                        e.currentTarget.value = "";
                      }
                    }}
                    onBlur={(e) => {
                      agregarTag(op.id, e.currentTarget.value);
                      e.currentTarget.value = "";
                    }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="config__actions">
        {saved && !dirty && (
          <span className="config__saved">Cambios guardados</span>
        )}
        <button
          type="button"
          className="config__save"
          onClick={guardar}
          disabled={!dirty || saving}
        >
          {saving ? "Guardando…" : "Guardar"}
        </button>
      </div>

      <div className="config__container">
        <div className="config__containerHead">
          <h3>Agentes de aduana</h3>
          <button type="button" className="config__add" onClick={agregarRuc}>
            + Agregar
          </button>
        </div>

        <p className="config__spHint">
          RUCs de los agentes aduaneros. Cuando las facturas de una misma Orden de
          Compra (N° O/C-O/S) incluyen a uno de estos RUCs, el grupo completo se
          consolida y se deposita al agente.
        </p>

        {agRucs.length === 0 ? (
          <p className="config__empty">
            No hay agentes. Usa «Agregar» para añadir un RUC.
          </p>
        ) : (
          <ul className="config__list">
            {agRucs.map((ruc, index) => (
              <li key={index} className="config__row">
                <span className="config__label">Agente {index + 1}</span>
                <input
                  type="text"
                  className="config__text"
                  placeholder="RUC del agente (11 dígitos)"
                  value={ruc}
                  onChange={(e) => setRuc(index, e.target.value)}
                />
                <button
                  type="button"
                  className="config__delete"
                  onClick={() => quitarRuc(index)}
                  aria-label={`Eliminar Agente ${index + 1}`}
                >
                  {trashIcon}
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="config__containerHead" style={{ marginTop: "1.25rem" }}>
          <h3>Proveedores relacionados con agentes</h3>
          <button type="button" className="config__add" onClick={agregarRel}>
            + Agregar
          </button>
        </div>

        <p className="config__spHint">
          RUCs de proveedores relacionados con agentes (flete, puerto,
          agenciamiento, etc.). Si una Orden de Compra incluye a uno de estos
          RUCs, todo el grupo se consolida en «Detalle de agentes». Si no hay una
          factura de un agente en esa O/C, el nombre queda como «Colocar nombre de
          agente manualmente».
        </p>

        {agRel.length === 0 ? (
          <p className="config__empty">
            No hay proveedores relacionados. Usa «Agregar» para añadir un RUC.
          </p>
        ) : (
          <ul className="config__list">
            {agRel.map((ruc, index) => (
              <li key={index} className="config__row">
                <span className="config__label">Relacionado {index + 1}</span>
                <input
                  type="text"
                  className="config__text"
                  placeholder="RUC del proveedor relacionado (11 dígitos)"
                  value={ruc}
                  onChange={(e) => setRel(index, e.target.value)}
                />
                <button
                  type="button"
                  className="config__delete"
                  onClick={() => quitarRel(index)}
                  aria-label={`Eliminar Relacionado ${index + 1}`}
                >
                  {trashIcon}
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="config__actions">
          {agSaved && !agDirty && (
            <span className="config__saved">Cambios guardados</span>
          )}
          <button
            type="button"
            className="config__save"
            onClick={guardarAgentes}
            disabled={!agDirty || agSaving}
          >
            {agSaving ? "Guardando…" : "Guardar agentes"}
          </button>
        </div>
      </div>

      <div className="config__container">
        <div className="config__containerHead">
          <h3>Retención</h3>
          {retActivo && (
            <button type="button" className="config__add" onClick={agregarRetRuc}>
              + Agregar
            </button>
          )}
        </div>

        <div className="config__spField">
          <label htmlFor="ret-activo">Aplicar retención</label>
          <select
            id="ret-activo"
            className="config__filtroSelect"
            value={retActivo ? "si" : "no"}
            onChange={(e) => {
              setRetActivo(e.target.value === "si");
              marcarRet();
            }}
          >
            <option value="si">Sí, calcular retención</option>
            <option value="no">No aplicar retención</option>
          </select>
        </div>

        {!retActivo ? (
          <p className="config__spHint">
            La retención está <strong>desactivada</strong>: %RET y RET quedan en 0.
            Actívala para volver a calcularla.
          </p>
        ) : (
        <>
        <p className="config__spHint">
          Se retiene el <strong>3% del IMPORTE</strong> a las facturas de bienes
          que superan <strong>S/ 700</strong> (o su equivalente en dólares según
          el tipo de cambio). No se retiene si la factura tiene detracción (es
          servicio) ni a los proveedores de la lista (agentes de retención).
        </p>

        <div className="config__spField">
          <label htmlFor="ret-tc">Tipo de cambio (USD → S/)</label>
          <input
            id="ret-tc"
            type="number"
            step="0.001"
            min="0"
            className="config__text"
            placeholder="3.75"
            value={retTC}
            onChange={(e) => {
              setRetTC(e.target.value);
              marcarRet();
            }}
          />
        </div>

        <p className="config__spHint">
          RUCs de proveedores que son agentes de retención (a ellos no se les
          retiene):
        </p>

        {retRucs.length === 0 ? (
          <p className="config__empty">
            No hay proveedores exceptuados. Usa «Agregar» para añadir un RUC.
          </p>
        ) : (
          <ul className="config__list">
            {retRucs.map((ruc, index) => (
              <li key={index} className="config__row">
                <span className="config__label">Exceptuado {index + 1}</span>
                <input
                  type="text"
                  className="config__text"
                  placeholder="RUC del agente de retención (11 dígitos)"
                  value={ruc}
                  onChange={(e) => setRetRuc(index, e.target.value)}
                />
                <button
                  type="button"
                  className="config__delete"
                  onClick={() => quitarRetRuc(index)}
                  aria-label={`Eliminar Exceptuado ${index + 1}`}
                >
                  {trashIcon}
                </button>
              </li>
            ))}
          </ul>
        )}
        </>
        )}

        <div className="config__actions">
          {retSaved && !retDirty && (
            <span className="config__saved">Cambios guardados</span>
          )}
          <button
            type="button"
            className="config__save"
            onClick={guardarRetencion}
            disabled={!retDirty || retSaving}
          >
            {retSaving ? "Guardando…" : "Guardar retención"}
          </button>
        </div>
      </div>

      <div className="config__container">
        <div className="config__containerHead">
          <h3>Sharepoint</h3>
        </div>

        <div className="config__spBody">
          <div className="config__spField">
            <label htmlFor="sp-link">Link principal</label>
            <input
              id="sp-link"
              type="text"
              className="config__text"
              placeholder="URL de la carpeta general (ej. …/2026/1. COMPRAS)"
              value={spLink}
              onChange={(e) => {
                setSpLink(e.target.value);
                setSpDirty(true);
                setSpSaved(false);
              }}
            />
          </div>

          <p className="config__spHint">
            Nombre de la carpeta de cada mes (tal como aparece en Sharepoint):
          </p>
          <div className="config__spMeses">
            {MESES.map((m) => (
              <div className="config__spMes" key={m.n}>
                <label htmlFor={`sp-mes-${m.n}`}>
                  {m.n} · {m.nombre}
                </label>
                <input
                  id={`sp-mes-${m.n}`}
                  type="text"
                  className="config__text"
                  placeholder={`${m.n}. ${m.nombre.toUpperCase()}`}
                  value={spMeses[m.n] ?? ""}
                  onChange={(e) => setMes(m.n, e.target.value)}
                />
              </div>
            ))}
          </div>
        </div>

        <div className="config__actions">
          {spSaved && !spDirty && (
            <span className="config__saved">Cambios guardados</span>
          )}
          <button
            type="button"
            className="config__save"
            onClick={guardarSharepoint}
            disabled={!spDirty || spSaving}
          >
            {spSaving ? "Guardando…" : "Guardar Sharepoint"}
          </button>
        </div>
      </div>
    </section>
  );
}
