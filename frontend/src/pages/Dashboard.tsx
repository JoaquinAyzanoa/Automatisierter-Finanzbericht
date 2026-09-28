import { useState } from "react";

import { Sidebar, type NavKey } from "../components/Sidebar";
import { useAuth } from "../context/AuthContext";
import { Configuracion } from "./sections/Configuracion";
import { EntradaInformacion } from "./sections/EntradaInformacion";
import { Historial } from "./sections/Historial";
import { Informes } from "./sections/Informes";
import { PagosMasivos } from "./sections/PagosMasivos";
import "./Dashboard.css";

/** Datos de contacto que se muestran en «Acerca de» y en el pie de página. */
export const DESARROLLADORA = {
  autora: "AngieAyzanoa",
  nombre: "Angie Ayzanoa",
  correo: "betsayzanoa@gmail.com",
};

const SECTIONS: Record<NavKey, { title: string; body: string }> = {
  entrada: {
    title: "Entrada de información",
    body: "Captura y carga los datos financieros que alimentarán tus informes. Este módulo estará disponible próximamente.",
  },
  informes: {
    title: "Informes",
    body: "Genera, consulta y exporta informes financieros en Excel. Este módulo estará disponible próximamente.",
  },
  pagos: {
    title: "Pagos masivos",
    body: "Macros de pago masivo del BCP.",
  },
  historial: {
    title: "Historial",
    body: "Procesos guardados.",
  },
  acerca: {
    title: "Acerca de",
    body: "Información de la aplicación y contacto.",
  },
  configuracion: {
    title: "Configuración",
    body: "Administra los ajustes de la plataforma y tus preferencias. Este módulo estará disponible próximamente.",
  },
  cuenta: {
    title: "Cuenta",
    body: "Consulta los detalles de tu cuenta.",
  },
};

export function Dashboard() {
  const { user } = useAuth();
  const [active, setActive] = useState<NavKey>("entrada");
  // Proceso a mostrar en Informes: null = el último.
  const [procesoId, setProcesoId] = useState<string | null>(null);
  const section = SECTIONS[active];

  function verProceso(id: string) {
    setProcesoId(id);
    setActive("informes");
  }

  return (
    <div className="app">
      <Sidebar active={active} onSelect={setActive} />

      <div className="app__content">
        <header className="app__topbar">
          <h1>{section.title}</h1>
        </header>

        <main className="app__main">
          {active === "entrada" ? (
            <EntradaInformacion onProcesado={verProceso} />
          ) : active === "informes" ? (
            <Informes procesoId={procesoId} />
          ) : active === "pagos" ? (
            <PagosMasivos />
          ) : active === "historial" ? (
            <Historial onVer={verProceso} />
          ) : active === "configuracion" ? (
            <Configuracion />
          ) : active === "acerca" ? (
            <section className="panel">
              <p className="panel__lead">
                Automatización de Informes Financieros: genera el informe
                semanal de pagos a proveedores y las macros de pago masivo del
                banco a partir de los archivos de origen.
              </p>
              <dl className="account">
                <div>
                  <dt>Desarrollado por</dt>
                  <dd>{DESARROLLADORA.nombre}</dd>
                </div>
                <div>
                  <dt>Correo</dt>
                  <dd>
                    <a href={`mailto:${DESARROLLADORA.correo}`}>
                      {DESARROLLADORA.correo}
                    </a>
                  </dd>
                </div>
              </dl>
            </section>
          ) : (
            <section className="panel">
              <p className="panel__lead">{section.body}</p>

              {active === "cuenta" && user && (
                <dl className="account">
                  <div>
                    <dt>Usuario</dt>
                    <dd>{user.username}</dd>
                  </div>
                  <div>
                    <dt>Rol</dt>
                    <dd>{user.is_admin ? "Administrador" : "Usuario"}</dd>
                  </div>
                  <div>
                    <dt>Estado</dt>
                    <dd>{user.is_active ? "Activo" : "Inactivo"}</dd>
                  </div>
                </dl>
              )}
            </section>
          )}
        </main>

        <footer className="app__footer">
          <span>
            {DESARROLLADORA.autora} · Automatización de Informes Financieros
          </span>
          <span className="app__footerSep">·</span>
          <button
            type="button"
            className="app__footerLink"
            onClick={() => setActive("acerca")}
          >
            Acerca de
          </button>
          <span className="app__footerSep">·</span>
          <a href={`mailto:${DESARROLLADORA.correo}`}>{DESARROLLADORA.correo}</a>
        </footer>
      </div>
    </div>
  );
}
