import { useAuth } from "../context/AuthContext";

export function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <div
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: "48px 24px",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 32,
        }}
      >
        <h1 style={{ margin: 0, fontSize: 22 }}>Automatización de Informes Financieros</h1>
        <button
          onClick={logout}
          style={{
            border: "1px solid var(--border)",
            background: "var(--surface)",
            color: "var(--text)",
            borderRadius: 8,
            padding: "8px 14px",
            cursor: "pointer",
          }}
        >
          Cerrar sesión
        </button>
      </header>

      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 14,
          padding: 28,
          boxShadow: "var(--shadow)",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Bienvenido, {user?.username} 👋</h2>
        <p style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
          Has iniciado sesión{user?.is_admin ? " como administrador" : ""}. Aquí
          estará la interfaz de generación de informes — selecciona datos
          financieros y exporta informes en Excel.
        </p>
      </div>
    </div>
  );
}
