import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import type { OperacionOpcion } from "../api/client";
import "./OperacionSelect.css";

interface Props {
  value: number | null;
  options: OperacionOpcion[];
  onChange: (pos: number) => void;
}

const chevron = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={12} height={12}>
    <path d="M6 9l6 6 6-6" />
  </svg>
);

export function OperacionSelect({ value, options, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0, minWidth: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);

  useLayoutEffect(() => {
    if (!open || !btnRef.current) return;
    const r = btnRef.current.getBoundingClientRect();
    setCoords({ top: r.bottom + 4, left: r.left, minWidth: Math.max(r.width, 240) });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    // Cerrar al hacer scroll (el menú es position: fixed y no seguiría al botón).
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    document.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        className="opsel__btn"
        onClick={() => setOpen((o) => !o)}
        title="Cambiar operación"
      >
        <span>{value ?? "–"}</span>
        {chevron}
      </button>

      {open &&
        createPortal(
          <>
            <div className="opsel__backdrop" onClick={() => setOpen(false)} />
            <ul
              className="opsel__menu"
              style={{
                top: coords.top,
                left: coords.left,
                minWidth: coords.minWidth,
              }}
            >
              {options.map((o) => (
                <li key={o.pos}>
                  <button
                    type="button"
                    className={
                      "opsel__item" + (o.pos === value ? " is-active" : "")
                    }
                    onClick={() => {
                      onChange(o.pos);
                      setOpen(false);
                    }}
                  >
                    <span className="opsel__num">{o.pos}</span>
                    <span className="opsel__texto">{o.texto || "(sin nombre)"}</span>
                    <span className="opsel__moneda">{o.moneda}</span>
                  </button>
                </li>
              ))}
            </ul>
          </>,
          document.body
        )}
    </>
  );
}
