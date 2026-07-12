import { useEffect, useState } from "react";

import {
  listarProcesos,
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
