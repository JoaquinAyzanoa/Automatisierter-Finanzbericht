import { useAuth } from "./context/AuthContext";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";

export function App() {
  const { user, loading, token } = useAuth();

  // Restoring an existing session.
  if (loading && token) {
    return (
      <div
        style={{
          display: "grid",
          placeItems: "center",
          height: "100%",
          color: "var(--text-muted)",
        }}
      >
        Cargando…
      </div>
    );
  }

  return user ? <Dashboard /> : <Login />;
}
