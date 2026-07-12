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
  const [otrosOpen, setOtrosOpen] = useState(false);
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
        setFechaInicio(d.fecha_inicio ?? "");
        setFechaFinal(d.fecha_final ?? "");
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

  function etiquetaGrupo(pos: number | null): string {
    if (pos == null) return "Sin categoría";
    const op = opByPos.get(pos);
    return op ? `${pos} - ${op.texto} - ${op.moneda}` : `Operación ${pos}`;
  }

  const { grupos, otros } = useMemo<{ grupos: Grupo[]; otros: FilaInforme[] }>(() => {
    if (!data) return { grupos: [], otros: [] };
    const q = busqueda.trim().toLowerCase();
    const usaFecha = !!data.fecha_columna && !!(fechaInicio || fechaFinal);

    const enRango = (f: FilaInforme) => {
      const fec = String(f["__fec_vcto"] ?? "");
      if (!fec) return false;
      if (fechaInicio && fec < fechaInicio) return false;
      if (fechaFinal && fec > fechaFinal) return false;
      return true;
    };

    const dentro: FilaInforme[] = [];
    const fuera: FilaInforme[] = [];
    for (const f of data.filas) {
      if (q) {
        const match = Object.entries(f).some(
          ([k, v]) => !k.startsWith("__") && String(v).toLowerCase().includes(q)
        );
        if (!match) continue;
      }
      if (usaFecha && !enRango(f)) fuera.push(f);
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
  }, [data, busqueda, fechaInicio, fechaFinal, overrides, opByPos]);

  function reasignar(id: number, pos: number) {
    setOverrides((prev) => ({ ...prev, [id]: pos }));
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

  function tabla(filas: FilaInforme[]): ReactNode {
    return (
      <TablaScroll>
        <table className="informes__tabla">
          <thead>
            <tr>
              <th className="informes__opCol">Op.</th>
              {columnas.map((c) => (
                <th key={c}>{etiquetaColumna(c)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => {
              const id = f["__id"] as number;
              const eff =
                id in overrides ? overrides[id] : (f["__pos"] as number | null);
              return (
                <tr key={id}>
                  <td className="informes__opCol">
                    <OperacionSelect
                      value={eff}
                      options={operaciones}
                      onChange={(pos) => reasignar(id, pos)}
                    />
                  </td>
                  {columnas.map((c) => (
                    <td key={c}>{mostrarCelda(f[c])}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </TablaScroll>
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
              onChange={(e) => {
                setFechaInicio(e.target.value);
                setCambios((c) => c + 1);
              }}
            />
          </label>
          <label className="informes__field">
            <span>Fecha final</span>
            <input
              type="date"
              value={fechaFinal}
              min={fechaInicio || undefined}
              onChange={(e) => {
                setFechaFinal(e.target.value);
                setCambios((c) => c + 1);
              }}
            />
          </label>
        </div>
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
                      Otros (fuera del rango de fechas)
                    </span>
                    <span className="informes__grupoMeta">
                      {otros.length} filas · Total{" "}
                      {formatoMonto(totalMonto(otros))}
                    </span>
                  </button>
                  {otrosAbierto && tabla(otros)}
                </div>
              );
            })()}
        </div>
      )}
    </section>
  );
}
