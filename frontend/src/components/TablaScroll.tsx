import { useEffect, useRef, useState, type ReactNode } from "react";

import "./TablaScroll.css";

/**
 * Envuelve una tabla ancha y muestra una barra de scroll horizontal ARRIBA
 * (además de la de abajo), sincronizada con el contenido.
 */
export function TablaScroll({ children }: { children: ReactNode }) {
  const topRef = useRef<HTMLDivElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const syncing = useRef(false);
  const [ancho, setAncho] = useState(0);

  useEffect(() => {
    const body = bodyRef.current;
    const contenido = body?.firstElementChild as HTMLElement | null;
    if (!body || !contenido) return;
    const medir = () => setAncho(contenido.scrollWidth);
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(contenido);
    return () => ro.disconnect();
  }, [children]);

  const onTop = () => {
    if (syncing.current) {
      syncing.current = false;
      return;
    }
    if (bodyRef.current && topRef.current) {
      syncing.current = true;
      bodyRef.current.scrollLeft = topRef.current.scrollLeft;
    }
  };

  const onBody = () => {
    if (syncing.current) {
      syncing.current = false;
      return;
    }
    if (bodyRef.current && topRef.current) {
      syncing.current = true;
      topRef.current.scrollLeft = bodyRef.current.scrollLeft;
    }
  };

  return (
    <div className="tablaScroll">
      <div className="tablaScroll__top" ref={topRef} onScroll={onTop}>
        <div style={{ width: ancho }} />
      </div>
      <div className="tablaScroll__body" ref={bodyRef} onScroll={onBody}>
        {children}
      </div>
    </div>
  );
}
