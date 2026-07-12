import { useState } from "react";

import { Sidebar, type NavKey } from "../components/Sidebar";
import { useAuth } from "../context/AuthContext";
import { Configuracion } from "./sections/Configuracion";
import { EntradaInformacion } from "./sections/EntradaInformacion";
import { Informes } from "./sections/Informes";
import "./Dashboard.css";

const SECTIONS: Record<NavKey, { title: string; body: string }> = {
  entrada: {
    title: "Entrada de información",
    body: "Captura y carga los datos financieros que alimentarán tus informes. Este módulo estará disponible próximamente.",
  },
  informes: {
    title: "Informes",
    body: "Genera, consulta y exporta informes financieros en Excel. Este módulo estará disponible próximamente.",
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
  const section = SECTIONS[active];

  return (
    <div className="app">
      <Sidebar active={active} onSelect={setActive} />

      <div className="app__content">
        <header className="app__topbar">
          <h1>{section.title}</h1>
        </header>

        <main className="app__main">
          {active === "entrada" ? (
            <EntradaInformacion />
          ) : active === "informes" ? (
            <Informes />
          ) : active === "configuracion" ? (
            <Configuracion />
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
      </div>
    </div>
  );
}
