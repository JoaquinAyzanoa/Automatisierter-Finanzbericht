import { useEffect, useRef, useState } from "react";

import {
  listarOperaciones,
  reemplazarOperaciones,
  type Ambito,
  type Moneda,
} from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import "./Configuracion.css";

interface FilaOp {
  id: number;
  texto: string;
  moneda: Moneda;
  ambito: Ambito;
  tags: string[];
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

  function markDirty() {
    setDirty(true);
    setSaved(false);
  }

  function agregar() {
    setOperaciones((prev) => [
      ...prev,
      { id: tempId.current--, texto: "", moneda: "SOL", ambito: "Nacional", tags: [] },
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
      }));
      const result = await reemplazarOperaciones(token, items);
      setOperaciones(
        result.map((o) => ({
          id: o.id,
          texto: o.texto,
          moneda: o.moneda,
          ambito: o.ambito,
          tags: o.tags ?? [],
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
    </section>
  );
}
