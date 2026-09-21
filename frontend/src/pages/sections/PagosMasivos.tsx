import { useEffect, useState, type ChangeEvent } from "react";

import {
  ApiError,
  descargarMacro,
  fechaHoyISO,
  listarArchivosMacro,
  listarProcesos,
  nombreArchivoMacro,
  subirArchivoMacro,
  triggerBlobDownload,
  vistaPreviaMacros,
  type ArchivoMacro,
  type MacroMoneda,
  type MonedaMacro,
  type ProcesoResumen,
  type TipoArchivoMacro,
} from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import "./PagosMasivos.css";

const MONEDAS: { key: MonedaMacro; label: string; simbolo: string }[] = [
  { key: "SOL", label: "Soles", simbolo: "S/" },
  { key: "USD", label: "Dólares", simbolo: "US$" },
];

const SLOTS: { prefijo: "plantilla" | "bd"; label: string; accept: string }[] = [
  { prefijo: "plantilla", label: "Plantilla de la macro", accept: ".xlsm" },
  { prefijo: "bd", label: "Base de cuentas", accept: ".xlsx" },
];

function formatoMonto(v: number): string {
  return v.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatoFecha(iso: string): string {
  return new Date(iso).toLocaleString("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function etiquetaProceso(p: ProcesoResumen): string {
  const rango =
    p.fecha_inicio || p.fecha_final
      ? ` · ${p.fecha_inicio ?? "…"} → ${p.fecha_final ?? "…"}`
      : "";
  return `${p.nombre || formatoFecha(p.updated_at)}${rango}`;
}

function mensaje(err: unknown, porDefecto: string): string {
  return err instanceof ApiError ? err.message : porDefecto;
}

export function PagosMasivos() {
  const { token } = useAuth();
  const [archivos, setArchivos] = useState<ArchivoMacro[]>([]);
  const [subiendo, setSubiendo] = useState<TipoArchivoMacro | null>(null);
  const [procesos, setProcesos] = useState<ProcesoResumen[]>([]);
  const [procesoId, setProcesoId] = useState<string>("");
  const [fecha, setFecha] = useState<string>(fechaHoyISO());
  const [monedas, setMonedas] = useState<MacroMoneda[] | null>(null);
  const [cargando, setCargando] = useState(false);
  const [descargando, setDescargando] = useState<MonedaMacro | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    listarArchivosMacro(token)
      .then(setArchivos)
      .catch(() => setError("No se pudieron cargar los archivos de las macros."));
    listarProcesos(token)
      .then((ps) => {
        setProcesos(ps);
        // El más reciente primero (ya vienen ordenados así).
        if (ps.length) setProcesoId((actual) => actual || ps[0].id);
      })
      .catch(() => setError("No se pudo cargar el historial de procesos."));
  }, [token]);

  // Los archivos subidos cambian los pagos (cuentas encontradas), así que la
  // vista previa se recalcula también cuando cambian.
  useEffect(() => {
    if (!token || !procesoId) return;
    let cancelled = false;
    setCargando(true);
    vistaPreviaMacros(token, procesoId)
      .then((r) => {
        if (!cancelled) setMonedas(r.monedas);
      })
      .catch((err) => {
        if (!cancelled) setError(mensaje(err, "No se pudieron calcular los pagos."));
      })
      .finally(() => {
        if (!cancelled) setCargando(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, procesoId, archivos]);

  async function subir(tipo: TipoArchivoMacro, e: ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0];
    e.target.value = ""; // permite volver a elegir el mismo archivo
    if (!archivo || !token) return;
    setSubiendo(tipo);
    setError(null);
    try {
      const nuevo = await subirArchivoMacro(token, tipo, archivo);
      setArchivos((prev) => prev.map((a) => (a.tipo === tipo ? nuevo : a)));
    } catch (err) {
      setError(mensaje(err, "No se pudo subir el archivo."));
    } finally {
      setSubiendo(null);
    }
  }

  async function descargar(moneda: MonedaMacro) {
    if (!token || !procesoId || !fecha) return;
    setDescargando(moneda);
    setError(null);
    try {
      const blob = await descargarMacro(token, procesoId, moneda, fecha);
      triggerBlobDownload(blob, nombreArchivoMacro(moneda, fecha));
    } catch (err) {
      setError(mensaje(err, "No se pudo generar la macro."));
    } finally {
      setDescargando(null);
    }
  }

  const archivo = (tipo: TipoArchivoMacro) => archivos.find((a) => a.tipo === tipo);

  return (
    <section className="panel">
      <p className="panel__lead">
        Genera las macros de pago masivo del BCP a partir de un informe ya
        procesado. Entran «Pago masivo proveedores» y los pagos a agentes de
        aduana, con el Neto del informe.
      </p>

      {error && <div className="pagos__error">{error}</div>}

      <div className="pagos__container">
        <div className="pagos__head">
          <h3>Archivos</h3>
          <span className="pagos__hint">
            Se suben una vez; vuelve a subir la base cuando cambien las cuentas.
          </span>
        </div>
        <div className="pagos__archivos">
          {MONEDAS.map((m) => (
            <div className="pagos__moneda" key={m.key}>
              <h4>{m.label}</h4>
              {SLOTS.map((slot) => {
                const tipo = `${slot.prefijo}_${m.key}` as TipoArchivoMacro;
                const a = archivo(tipo);
                return (
                  <div className={"pagos__slot" + (a?.nombre ? " is-ok" : "")} key={tipo}>
                    <div className="pagos__slotInfo">
                      <span className="pagos__slotLabel">{slot.label}</span>
                      {a?.nombre ? (
                        <>
                          <span className="pagos__slotNombre" title={a.nombre}>
                            {a.nombre}
                          </span>
                          <span className="pagos__slotMeta">
                            {a.detalle}
                            {a.subido_en ? ` · ${formatoFecha(a.subido_en)}` : ""}
                          </span>
                        </>
                      ) : (
                        <span className="pagos__slotMeta">Sin subir</span>
                      )}
                    </div>
                    <label className="pagos__btn pagos__btn--sec">
                      <input
                        type="file"
                        accept={slot.accept}
                        onChange={(e) => subir(tipo, e)}
                        disabled={subiendo !== null}
                      />
                      {subiendo === tipo ? "Subiendo…" : a?.nombre ? "Reemplazar" : "Subir"}
                    </label>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      <div className="pagos__container">
        <div className="pagos__head">
          <h3>Generar macros</h3>
        </div>
        <div className="pagos__filtros">
          <label className="pagos__campo">
            <span>Proceso</span>
            <select value={procesoId} onChange={(e) => setProcesoId(e.target.value)}>
              {procesos.length === 0 && <option value="">No hay procesos</option>}
              {procesos.map((p) => (
                <option key={p.id} value={p.id}>
                  {etiquetaProceso(p)}
                </option>
              ))}
            </select>
          </label>
          <label className="pagos__campo pagos__campo--fecha">
            <span>Fecha de proceso</span>
            <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
          </label>
        </div>

        {cargando && !monedas ? (
          <p className="pagos__vacio">Calculando pagos…</p>
        ) : (
          monedas?.map((mm) => {
            const info = MONEDAS.find((m) => m.key === mm.moneda)!;
            const faltaPlantilla = mm.faltan.some((f) => f.includes("plantilla"));
            return (
              <div className="pagos__resultado" key={mm.moneda}>
                <div className="pagos__resHead">
                  <div>
                    <h4>{info.label}</h4>
                    <span className="pagos__resMeta">
                      {mm.abonos.length} proveedores · {mm.n_documentos} documentos ·{" "}
                      <strong>
                        {info.simbolo} {formatoMonto(mm.total)}
                      </strong>
                    </span>
                  </div>
                  <button
                    type="button"
                    className="pagos__btn"
                    onClick={() => descargar(mm.moneda)}
                    disabled={
                      faltaPlantilla || mm.abonos.length === 0 || !fecha || descargando !== null
                    }
                  >
                    {descargando === mm.moneda ? "Generando…" : `Descargar macro ${info.label}`}
                  </button>
                </div>

                {mm.faltan.length > 0 && (
                  <div className="pagos__aviso">
                    Falta subir {mm.faltan.join(" y ")} en {info.label.toLowerCase()}.
                  </div>
                )}
                {mm.sin_cuenta > 0 && (
                  <div className="pagos__aviso">
                    {mm.sin_cuenta === 1
                      ? "1 proveedor no está en la base de cuentas"
                      : `${mm.sin_cuenta} proveedores no están en la base de cuentas`}
                    : van en la macro con la cuenta en blanco para completarla a mano.
                  </div>
                )}
                {mm.omitidos.length > 0 && (
                  <div className="pagos__aviso">
                    No entran en la macro por no tener agente identificado
                    («Colocar nombre de agente manualmente»):
                    <ul>
                      {mm.omitidos.map((o) => (
                        <li key={o.oc}>
                          O/C {o.oc} — {o.proveedores.join(", ")} — {info.simbolo}{" "}
                          {formatoMonto(o.total)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {mm.abonos.length === 0 ? (
                  <p className="pagos__vacio">
                    Este proceso no tiene pagos masivos en {info.label.toLowerCase()}.
                  </p>
                ) : (
                  <div className="pagos__tablaWrap">
                    <table className="pagos__tabla">
                      <thead>
                        <tr>
                          <th>Proveedor</th>
                          <th>RUC</th>
                          <th>Tipo</th>
                          <th>Cuenta</th>
                          <th>Documentos</th>
                          <th className="num">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {mm.abonos.map((a) => (
                          <tr key={a.ruc || a.nombre} className={a.en_bd ? "" : "is-sinCuenta"}>
                            <td>
                              {a.nombre}
                              {a.agente && <span className="pagos__tag">Agente</span>}
                            </td>
                            <td>{a.ruc}</td>
                            <td>{a.tipo_cuenta || "—"}</td>
                            <td>{a.en_bd ? a.cuenta : "Sin cuenta"}</td>
                            <td
                              title={a.documentos
                                .map((d) => `${d.numero}: ${formatoMonto(d.monto)}`)
                                .join("\n")}
                            >
                              {a.documentos.map((d) => d.numero).join(", ")}
                            </td>
                            <td className="num">{formatoMonto(a.total)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
