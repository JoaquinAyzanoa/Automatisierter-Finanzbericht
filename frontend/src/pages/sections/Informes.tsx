import { useEffect, useMemo, useState, type ReactNode } from "react";

import {
  ApiError,
  guardarProceso,
  guardarYDescargarProceso,
  obtenerProceso,
  obtenerProcesoLatest,
  triggerBlobDownload,
  type FilaInforme,
  type ProcesoDetalle,
} from "../../api/client";
import { OperacionSelect } from "../../components/OperacionSelect";
import { TablaScroll } from "../../components/TablaScroll";
import { useAuth } from "../../context/AuthContext";
import "./Informes.css";

const searchIcon = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" width={18} height={18}>
    <circle cx="11" cy="11" r="7" />
    <path d="M21 21l-4.3-4.3" />
  </svg>
);

const downloadIcon = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" width={18} height={18}>
    <path d="M12 3v12m0 0l-4-4m4 4l4-4" />
    <path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
  </svg>
);

const chevron = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={16} height={16}>
    <path d="M9 6l6 6-6 6" />
  </svg>
);

// Columnas que van primero en la tabla (si existen).
const COLUMNAS_PRIORIDAD = ["MONEDA", "PROVEEDOR", "PRODUCTO"];

// Renombrado de encabezados solo para mostrar.
const ETIQUETAS_COLUMNA: Record<string, string> = {
  NUMERO: "N° DOCUMENTO",
};

function etiquetaColumna(c: string): string {
  return ETIQUETAS_COLUMNA[c.trim().toUpperCase()] ?? c;
}

interface Grupo {
  pos: number | null;
  label: string;
  filas: FilaInforme[];
  total: number;
}

function parseMonto(valor: unknown): number {
  const n = parseFloat(String(valor ?? "").replace(/,/g, ""));
  return Number.isFinite(n) ? n : 0;
}

// Quita la hora de valores tipo "2025-06-15 00:00:00" -> "2025-06-15".
function mostrarCelda(valor: unknown): string {
  const s = String(valor ?? "");
  const m = /^(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}:\d{2}/.exec(s);
  return m ? m[1] : s;
}

// RUC nacional: 11 dígitos que empiezan con 10 o 20.
function esRucNacional(ruc: unknown): boolean {
  const r = String(ruc ?? "")
    .trim()
    .replace(/\.0$/, "");
  return r.length === 11 && /^\d+$/.test(r) && (r.startsWith("10") || r.startsWith("20"));
}

// Columna de fecha de vencimiento (posibles nombres).
const FEC_VCTO_ALIASES = [
  "FEC. VCTO",
  "FEC.VCTO",
  "FEC VCTO",
  "F. VCTO",
  "F VCTO",
  "FECHA VCTO",
  "FECHA DE VENCIMIENTO",
  "FECHA VENCIMIENTO",
];

function normCol(s: string): string {
  return s.replace(/\s+/g, " ").trim().toUpperCase();
}

// Valor de celda de fecha a ISO (YYYY-MM-DD). Soporta ISO y dd/mm/yyyy.
function fechaISO(valor: unknown): string {
  const s = mostrarCelda(valor);
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  return "";
}

function totalMonto(filas: FilaInforme[]): number {
  return filas.reduce((acc, f) => acc + parseMonto(f["MONTO"]), 0);
}

function formatoMonto(n: number): string {
  return n.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

interface Props {
  /** Proceso a mostrar; si es null se carga el último. */
  procesoId?: string | null;
}

export function Informes({ procesoId }: Props) {
  const { token } = useAuth();
  const [data, setData] = useState<ProcesoDetalle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [descargando, setDescargando] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFinal, setFechaFinal] = useState("");
  // Rango aplicado (solo al pulsar "Filtrar").
  const [fechaInicioApl, setFechaInicioApl] = useState("");
  const [fechaFinalApl, setFechaFinalApl] = useState("");
  const [otrosOpen, setOtrosOpen] = useState(false);
  // Buscador, filtros por columna y rango de fechas, propios de "Otros".
  const [otrosBusqueda, setOtrosBusqueda] = useState("");
  const [otrosColFiltros, setOtrosColFiltros] = useState<Record<string, string>>(
    {}
  );
  const [otrosFechaInicio, setOtrosFechaInicio] = useState("");
  const [otrosFechaFinal, setOtrosFechaFinal] = useState("");
  // Reasignaciones manuales: id de fila -> posición de operación.
  const [overrides, setOverrides] = useState<Record<number, number>>({});
  // Autoguardado: contador de cambios del usuario + estado.
  const [cambios, setCambios] = useState(0);
  const [guardado, setGuardado] = useState<
    "idle" | "guardando" | "guardado" | "error"
  >("idle");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const cargar = procesoId
      ? obtenerProceso(token, procesoId)
      : obtenerProcesoLatest(token);
    cargar
      .then((d) => {
        if (cancelled) return;
        d.filas = d.filas.map((f, i) => ({ ...f, __id: i }));
        setData(d);
        setOverrides({});
        setBusqueda("");
        setOtrosBusqueda("");
        setOtrosColFiltros({});
        setOtrosFechaInicio("");
        setOtrosFechaFinal("");
        setFechaInicio(d.fecha_inicio ?? "");
        setFechaFinal(d.fecha_final ?? "");
        // El filtro NO se aplica al cargar; solo con el botón "Filtrar".
        setFechaInicioApl("");
        setFechaFinalApl("");
        setCambios(0);
        setGuardado("idle");
      })
      .catch((err) => {
        if (cancelled) return;
        setData(null);
        if (err instanceof ApiError && err.status === 404) {
          setError(
            "Aún no hay datos. Procesa los archivos en «Entrada de información»."
          );
        } else {
          setError("No se pudo cargar el informe.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, procesoId]);

  const operaciones = data?.operaciones ?? [];

  // Reordena las columnas: MONEDA, PROVEEDOR, PRODUCTO primero; el resto después.
  const columnas = useMemo(() => {
    const todas = data?.columnas ?? [];
    const norm = (s: string) => s.trim().toUpperCase();
    const primeras: string[] = [];
    for (const p of COLUMNAS_PRIORIDAD) {
      const encontrada = todas.find((c) => norm(c) === p);
      if (encontrada) primeras.push(encontrada);
    }
    const resto = todas.filter((c) => !primeras.includes(c));
    return [...primeras, ...resto];
  }, [data]);

  const opByPos = useMemo(() => {
    const m = new Map<number, (typeof operaciones)[number]>();
    for (const o of operaciones) m.set(o.pos, o);
    return m;
  }, [operaciones]);

  // Columna FEC. VCTO visible (los filtros de fecha operan sobre ella).
  const fecVctoCol = useMemo(() => {
    const set = new Set(FEC_VCTO_ALIASES.map(normCol));
    return (data?.columnas ?? []).find((c) => set.has(normCol(c))) ?? null;
  }, [data]);

  function etiquetaGrupo(pos: number | null): string {
    if (pos == null) return "Sin categoría";
    const op = opByPos.get(pos);
    return op ? `${pos} - ${op.texto} - ${op.moneda}` : `Operación ${pos}`;
  }

  const { grupos, otros } = useMemo<{ grupos: Grupo[]; otros: FilaInforme[] }>(() => {
    if (!data) return { grupos: [], otros: [] };
    const q = busqueda.trim().toLowerCase();
    const usaFecha = !!fecVctoCol && !!(fechaInicioApl || fechaFinalApl);

    const enRango = (f: FilaInforme) => {
      const fec = fecVctoCol ? fechaISO(f[fecVctoCol]) : "";
      if (!fec) return false;
      if (fechaInicioApl && fec < fechaInicioApl) return false;
      if (fechaFinalApl && fec > fechaFinalApl) return false;
      return true;
    };

    // Operaciones que NO respetan el filtro de fechas (sus filas nunca van a "Otros").
    const noRespeta = new Map<number, boolean>();
    for (const o of operaciones) noRespeta.set(o.pos, !o.respeta_filtro);

    const dentro: FilaInforme[] = [];
    const fuera: FilaInforme[] = [];
    for (const f of data.filas) {
      if (q) {
        const match = Object.entries(f).some(
          ([k, v]) => !k.startsWith("__") && String(v).toLowerCase().includes(q)
        );
        if (!match) continue;
      }
      const id = f["__id"] as number;
      const hasOverride = id in overrides;
      const eff = hasOverride ? overrides[id] : (f["__pos"] as number | null);
      const exenta = eff != null && noRespeta.get(eff) === true;
      // Fuera del filtro va a "Otros", salvo que esté exenta o ya reasignada.
      if (usaFecha && !exenta && !hasOverride && !enRango(f)) fuera.push(f);
      else dentro.push(f);
    }

    const mapa = new Map<number | "sin", FilaInforme[]>();
    for (const f of dentro) {
      const id = f["__id"] as number;
      const eff = id in overrides ? overrides[id] : (f["__pos"] as number | null);
      const key = eff ?? "sin";
      if (!mapa.has(key)) mapa.set(key, []);
      mapa.get(key)!.push(f);
    }

    const grupos = [...mapa.entries()]
      .map(([key, filas]) => {
        const pos = key === "sin" ? null : key;
        return { pos, label: etiquetaGrupo(pos), filas, total: totalMonto(filas) };
      })
      .sort((a, b) => (a.pos ?? Infinity) - (b.pos ?? Infinity));

    return { grupos, otros: fuera };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, busqueda, fechaInicioApl, fechaFinalApl, overrides, opByPos, fecVctoCol]);

  const otrosFiltrados = useMemo(() => {
    const q = otrosBusqueda.trim().toLowerCase();
    const cols = Object.entries(otrosColFiltros).filter(
      ([, v]) => v.trim() !== ""
    );
    const usaFecha = !!fecVctoCol && !!(otrosFechaInicio || otrosFechaFinal);
    return otros.filter((f) => {
      if (q) {
        const match = Object.entries(f).some(
          ([k, v]) => !k.startsWith("__") && String(v).toLowerCase().includes(q)
        );
        if (!match) return false;
      }
      for (const [col, val] of cols) {
        if (!mostrarCelda(f[col]).toLowerCase().includes(val.trim().toLowerCase())) {
          return false;
        }
      }
      if (usaFecha) {
        const fec = fecVctoCol ? fechaISO(f[fecVctoCol]) : "";
        if (!fec) return false;
        if (otrosFechaInicio && fec < otrosFechaInicio) return false;
        if (otrosFechaFinal && fec > otrosFechaFinal) return false;
      }
      return true;
    });
  }, [otros, otrosBusqueda, otrosColFiltros, otrosFechaInicio, otrosFechaFinal, fecVctoCol]);

  function reasignar(id: number, pos: number) {
    setOverrides((prev) => ({ ...prev, [id]: pos }));
    setCambios((c) => c + 1);
  }

  function aplicarFiltro() {
    setFechaInicioApl(fechaInicio);
    setFechaFinalApl(fechaFinal);
    setCambios((c) => c + 1);
  }

  // Autoguardado con debounce tras cada cambio del usuario.
  useEffect(() => {
    if (cambios === 0 || !token || !data) return;
    const id = data.id;
    const t = setTimeout(() => {
      setGuardado("guardando");
      guardarProceso(token, id, {
        fecha_inicio: fechaInicio || null,
        fecha_final: fechaFinal || null,
        overrides,
      })
        .then((r) => {
          setGuardado("guardado");
          setData((prev) =>
            prev && prev.id === id ? { ...prev, updated_at: r.updated_at } : prev
          );
        })
        .catch(() => setGuardado("error"));
    }, 800);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cambios]);

  async function handleDescargar() {
    if (!token || !data) return;
    setDescargando(true);
    setError(null);
    try {
      // Guarda todo (reasignaciones + rango de fechas) y descarga.
      const blob = await guardarYDescargarProceso(token, data.id, {
        fecha_inicio: fechaInicio || null,
        fecha_final: fechaFinal || null,
        overrides: Object.fromEntries(
          Object.entries(overrides).map(([k, v]) => [k, v])
        ),
      });
      triggerBlobDownload(blob, "informe_clasificado.xlsx");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("Aún no hay datos para descargar.");
      } else {
        setError("No se pudo descargar el informe.");
      }
    } finally {
      setDescargando(false);
    }
  }

  function renderFila(f: FilaInforme, sinCategoria: boolean): ReactNode {
    const id = f["__id"] as number;
    const eff = id in overrides ? overrides[id] : (f["__pos"] as number | null);
    // En "Otros" la fila se muestra sin categoría (hasta que se asigne).
    const valor = sinCategoria ? null : eff;
    // Solo categorías del mismo ámbito (Nacional/Exterior) y, dentro, misma moneda.
    const rowMoneda = String(f["MONEDA"] ?? "").trim().toUpperCase();
    const rowAmbito = esRucNacional(f["RUC"]) ? "Nacional" : "Exterior";
    const porAmbito = operaciones.filter((o) => o.ambito === rowAmbito);
    const porMoneda = porAmbito.filter(
      (o) => String(o.moneda).toUpperCase() === rowMoneda
    );
    const opcionesFila = porMoneda.length > 0 ? porMoneda : porAmbito;
    return (
      <tr key={id}>
        <td className="informes__opCol">
          <OperacionSelect
            value={valor}
            options={opcionesFila}
            onChange={(pos) => reasignar(id, pos)}
          />
        </td>
        {columnas.map((c) => (
          <td key={c}>{mostrarCelda(f[c])}</td>
        ))}
      </tr>
    );
  }

  function tabla(filas: FilaInforme[], sinCategoria = false): ReactNode {
    return (
      <TablaScroll topScroll={filas.length > 12}>
        <table className="informes__tabla">
          <thead>
            <tr>
              <th className="informes__opCol">Op.</th>
              {columnas.map((c) => (
                <th key={c}>{etiquetaColumna(c)}</th>
              ))}
            </tr>
          </thead>
          <tbody>{filas.map((f) => renderFila(f, sinCategoria))}</tbody>
        </table>
      </TablaScroll>
    );
  }

  function tablaOtros(filas: FilaInforme[]): ReactNode {
    return (
      <div className="informes__otrosBody">
        <div className="informes__otrosToolbar">
          <div className="informes__otrosSearch">
            <span className="informes__searchIcon">{searchIcon}</span>
            <input
              type="text"
              className="informes__searchInput"
              placeholder="Buscar en Otros…"
              value={otrosBusqueda}
              onChange={(e) => setOtrosBusqueda(e.target.value)}
            />
          </div>
          <label className="informes__field">
            <span>Fecha inicio</span>
            <input
              type="date"
              value={otrosFechaInicio}
              max={otrosFechaFinal || undefined}
              onChange={(e) => setOtrosFechaInicio(e.target.value)}
            />
          </label>
          <label className="informes__field">
            <span>Fecha final</span>
            <input
              type="date"
              value={otrosFechaFinal}
              min={otrosFechaInicio || undefined}
              onChange={(e) => setOtrosFechaFinal(e.target.value)}
            />
          </label>
        </div>
        <TablaScroll topScroll={filas.length > 12}>
          <table className="informes__tabla">
            <thead>
              <tr>
                <th className="informes__opCol">Op.</th>
                {columnas.map((c) => (
                  <th key={c}>{etiquetaColumna(c)}</th>
                ))}
              </tr>
              <tr className="informes__filtroRow">
                <th className="informes__opCol"></th>
                {columnas.map((c) => (
                  <th key={c}>
                    <input
                      type="text"
                      className="informes__colFiltro"
                      placeholder="Filtrar"
                      value={otrosColFiltros[c] ?? ""}
                      onChange={(e) =>
                        setOtrosColFiltros((prev) => ({
                          ...prev,
                          [c]: e.target.value,
                        }))
                      }
                    />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>{filas.map((f) => renderFila(f, true))}</tbody>
          </table>
        </TablaScroll>
      </div>
    );
  }

  const hayDatos = !!data && data.filas.length > 0;

  return (
    <section className="panel panel--compact panel--wide">
      <div className="informes__toolbar">
        <div className="informes__search">
          <span className="informes__searchIcon">{searchIcon}</span>
          <input
            type="text"
            className="informes__searchInput"
            placeholder="Buscar…"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </div>

        <button
          type="button"
          className="informes__download"
          onClick={handleDescargar}
          disabled={descargando || !hayDatos}
        >
          <span className="informes__downloadIcon">{downloadIcon}</span>
          {descargando ? "Descargando…" : "Descargar"}
        </button>

        <div className="informes__dates">
          <label className="informes__field">
            <span>Fecha inicio</span>
            <input
              type="date"
              value={fechaInicio}
              max={fechaFinal || undefined}
              onChange={(e) => setFechaInicio(e.target.value)}
            />
          </label>
          <label className="informes__field">
            <span>Fecha final</span>
            <input
              type="date"
              value={fechaFinal}
              min={fechaInicio || undefined}
              onChange={(e) => setFechaFinal(e.target.value)}
            />
          </label>
        </div>

        <button
          type="button"
          className="informes__filtrar"
          onClick={aplicarFiltro}
        >
          Filtrar
        </button>
      </div>

      {data && (
        <div className="informes__proceso">
          Proceso <strong>{data.id}</strong> · última edición{" "}
          {new Date(data.updated_at).toLocaleString("es-PE")}
          {guardado === "guardando" && (
            <span className="informes__guardado">· Guardando…</span>
          )}
          {guardado === "guardado" && (
            <span className="informes__guardado informes__guardado--ok">
              · Guardado
            </span>
          )}
          {guardado === "error" && (
            <span className="informes__guardado informes__guardado--error">
              · No se pudo guardar
            </span>
          )}
        </div>
      )}

      {error && <div className="informes__msg">{error}</div>}

      {loading ? (
        <div className="informes__msg">Cargando…</div>
      ) : !error && grupos.length === 0 && otros.length === 0 ? (
        <div className="informes__msg">Sin resultados.</div>
      ) : (
        <div className="informes__grupos">
          {grupos.map((g) => (
            <div className="informes__grupo" key={g.pos ?? "sin"}>
              <div className="informes__grupoHead">
                <span className="informes__grupoTitulo">{g.label}</span>
                <span className="informes__grupoMeta">
                  {g.filas.length} filas · Total {formatoMonto(g.total)}
                </span>
              </div>
              {tabla(g.filas)}
            </div>
          ))}

          {otros.length > 0 &&
            (() => {
              // Con búsqueda activa, "Otros" se abre para mostrar coincidencias.
              const buscando = busqueda.trim().length > 0;
              const otrosAbierto = otrosOpen || buscando;
              return (
                <div className="informes__grupo">
                  <button
                    type="button"
                    className="informes__grupoHead informes__otrosHead"
                    onClick={() => setOtrosOpen((o) => !o)}
                    aria-expanded={otrosAbierto}
                    disabled={buscando}
                  >
                    <span className="informes__grupoTitulo">
                      <span
                        className={
                          "informes__otrosChevron" +
                          (otrosAbierto ? " is-open" : "")
                        }
                      >
                        {chevron}
                      </span>
                      Otros (fuera del filtro inicial)
                    </span>
                    <span className="informes__grupoMeta">
                      {otrosFiltrados.length} filas · Total{" "}
                      {formatoMonto(totalMonto(otrosFiltrados))}
                    </span>
                  </button>
                  {otrosAbierto && tablaOtros(otrosFiltrados)}
                </div>
              );
            })()}
        </div>
      )}
    </section>
  );
}
