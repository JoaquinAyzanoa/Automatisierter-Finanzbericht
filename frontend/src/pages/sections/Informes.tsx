import { useState } from "react";

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

export function Informes() {
  const [busqueda, setBusqueda] = useState("");
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFinal, setFechaFinal] = useState("");

  return (
    <section className="panel panel--compact">
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

        <button type="button" className="informes__download">
          <span className="informes__downloadIcon">{downloadIcon}</span>
          Descargar
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
      </div>
    </section>
  );
}
