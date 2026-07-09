import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import "./Login.css";

export function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Usuario o contraseña incorrectos.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("No se pudo conectar con el servidor. Inténtalo de nuevo.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login">
      <aside className="login__brand">
        <div className="login__brandTop">
          <span className="login__monogram">AF</span>
          <span className="login__brandName">
            Automatización de Informes Financieros
          </span>
        </div>

        <div className="login__brandBody">
          <div className="login__rule" />
          <h2>Informes financieros precisos, listos en minutos.</h2>
          <p>
            Plataforma corporativa para la generación y consolidación
            automática de reportes financieros en Excel.
          </p>
        </div>

        <div className="login__brandFooter">
          © 2026 · Plataforma de uso interno autorizado
        </div>
      </aside>

      <main className="login__main">
        <div className="login__card">
          <div className="login__mobileBrand">
            <span className="login__monogram login__monogram--sm">AF</span>
            <span>Automatización de Informes Financieros</span>
          </div>

          <div className="login__header">
            <h1>Iniciar sesión</h1>
            <p>Accede con tus credenciales corporativas.</p>
          </div>

          <form className="login__form" onSubmit={handleSubmit} noValidate>
            {error && (
              <div className="login__error" role="alert">
                {error}
              </div>
            )}

            <label className="login__field">
              <span>Usuario</span>
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="nombre.apellido"
                autoFocus
                required
              />
            </label>

            <label className="login__field">
              <span>Contraseña</span>
              <div className="login__passwordWrap">
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  className="login__toggle"
                  onClick={() => setShowPassword((s) => !s)}
                  aria-label={
                    showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                  }
                >
                  {showPassword ? "Ocultar" : "Mostrar"}
                </button>
              </div>
            </label>

            <button
              type="submit"
              className="login__submit"
              disabled={submitting || !username || !password}
            >
              {submitting ? "Iniciando sesión…" : "Iniciar sesión"}
            </button>
          </form>

          <p className="login__footer">Acceso seguro · Conexión cifrada</p>
        </div>
      </main>
    </div>
  );
}
