import { useEffect, useState } from "react";

import {
  listarProcesos,
  renombrarProceso,
  type ProcesoResumen,
} from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import "./Historial.css";

interface Props {
  onVer: (id: string) => void;
}

function formatoFechaHora(iso: string): string {
  return new Date(iso).toLocaleString("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function rangoFechas(p: ProcesoResumen): string {
  if (!p.fecha_inicio && !p.fecha_final) return "—";
  return `${p.fecha_inicio ?? "…"} → ${p.fecha_final ?? "…"}`;
}

export function Historial({ onVer }: Props) {
  const { token } = useAuth();
  const [procesos, setProcesos] = useState<ProcesoResumen[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    listarProcesos(token)
      .then((ps) => {
        if (!cancelled) setProcesos(ps);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar el historial.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  function setNombreLocal(id: string, nombre: string) {
    setProcesos((prev) =>
      prev.map((p) => (p.id === id ? { ...p, nombre } : p))
    );
  }

  async function guardarNombre(p: ProcesoResumen) {
    if (!token) return;
    const nombre = (p.nombre ?? "").trim();
    try {
      await renombrarProceso(token, p.id, nombre);
    } catch {
      setError("No se pudo guardar el nombre.");
    }
  }

  return (
    <section className="panel">
      <p className="panel__lead">
        Procesos guardados. Abre uno para verlo en «Informes».
      </p>

      {error && <div className="historial__msg">{error}</div>}

      {loading ? (
        <div className="historial__msg">Cargando…</div>
      ) : procesos.length === 0 ? (
        <div className="historial__msg">
          Aún no hay procesos. Genera uno en «Entrada de información».
        </div>
      ) : (
        <div className="historial__tablaWrap">
          <table className="historial__tabla">
            <thead>
              <tr>
                <th>Proceso</th>
                <th>Nombre</th>
                <th>Última edición</th>
                <th>Rango de fechas</th>
                <th className="historial__num">Filas</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {procesos.map((p) => (
                <tr key={p.id}>
                  <td className="historial__id">{p.id}</td>
                  <td>
                    <input
                      type="text"
                      className="historial__nombre"
                      placeholder="Sin nombre"
                      value={p.nombre ?? ""}
                      onChange={(e) => setNombreLocal(p.id, e.target.value)}
                      onBlur={() => guardarNombre(p)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") e.currentTarget.blur();
                      }}
                    />
                  </td>
                  <td>{formatoFechaHora(p.updated_at)}</td>
                  <td>{rangoFechas(p)}</td>
                  <td className="historial__num">{p.n_filas}</td>
                  <td className="historial__acciones">
                    <button
                      type="button"
                      className="historial__ver"
                      onClick={() => onVer(p.id)}
                    >
                      Ver
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
