import type { ReactNode } from "react";

import { useAuth } from "../context/AuthContext";
import "./Sidebar.css";

export type NavKey = "entrada" | "informes" | "configuracion" | "cuenta";

interface NavItem {
  key: NavKey;
  label: string;
  icon: ReactNode;
}

const iconProps = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  width: 20,
  height: 20,
};

const NAV: NavItem[] = [
  {
    key: "entrada",
    label: "Entrada de información",
    icon: (
      <svg {...iconProps}>
        <path d="M12 3v12m0 0l-4-4m4 4l4-4" />
        <path d="M4 15v3a2 2 0 002 2h12a2 2 0 002-2v-3" />
      </svg>
    ),
  },
  {
    key: "informes",
    label: "Informes",
    icon: (
      <svg {...iconProps}>
        <path d="M4 20V4M4 20h16" />
        <path d="M8 16v-4M12 16V8M16 16v-6" />
      </svg>
    ),
  },
  {
    key: "configuracion",
    label: "Configuración",
    icon: (
      <svg {...iconProps}>
        <path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h7M15 18h5" />
        <circle cx="15" cy="6" r="2" />
        <circle cx="9" cy="12" r="2" />
        <circle cx="13" cy="18" r="2" />
      </svg>
    ),
  },
];

const accountIcon = (
  <svg {...iconProps}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 20c0-4 3.5-6 8-6s8 2 8 6" />
  </svg>
);

const logoutIcon = (
  <svg {...iconProps}>
    <path d="M15 12H4m0 0l4-4m-4 4l4 4" />
    <path d="M14 4h4a2 2 0 012 2v12a2 2 0 01-2 2h-4" />
  </svg>
);

interface SidebarProps {
  active: NavKey;
  onSelect: (key: NavKey) => void;
}

export function Sidebar({ active, onSelect }: SidebarProps) {
  const { user, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__monogram">AF</span>
        <span className="sidebar__brandName">
          Automatización de Informes Financieros
        </span>
      </div>

      <nav className="sidebar__nav">
        {NAV.map((item) => (
          <button
            key={item.key}
            type="button"
            className={
              "sidebar__item" + (active === item.key ? " is-active" : "")
            }
            aria-current={active === item.key ? "page" : undefined}
            onClick={() => onSelect(item.key)}
          >
            <span className="sidebar__icon">{item.icon}</span>
            <span className="sidebar__label">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar__footer">
        <button
          type="button"
          className={
            "sidebar__item sidebar__account" +
            (active === "cuenta" ? " is-active" : "")
          }
          aria-current={active === "cuenta" ? "page" : undefined}
          onClick={() => onSelect("cuenta")}
        >
          <span className="sidebar__icon">{accountIcon}</span>
          <span className="sidebar__accountInfo">
            <span className="sidebar__accountName">{user?.username}</span>
            <span className="sidebar__accountRole">
              {user?.is_admin ? "Administrador" : "Usuario"}
            </span>
          </span>
        </button>

        <button
          type="button"
          className="sidebar__item sidebar__logout"
          onClick={logout}
        >
          <span className="sidebar__icon">{logoutIcon}</span>
          <span className="sidebar__label">Salir</span>
        </button>
      </div>
    </aside>
  );
}
