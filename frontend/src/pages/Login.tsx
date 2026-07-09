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
      <div className="login__panel">
        <div className="login__brand">
          <div className="login__logo" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="26" height="26" fill="none">
              <path
                d="M4 19V5m0 14h16M8 15l3-4 3 3 4-6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span className="login__brandName">
            Automatización de Informes Financieros
          </span>
        </div>

        <div className="login__header">
          <h1>Bienvenido de nuevo</h1>
          <p>Inicia sesión para generar tus informes financieros.</p>
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
              placeholder="tu.usuario"
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

        <p className="login__footer">
          Informes financieros automatizados · Acceso seguro
        </p>
      </div>
    </div>
  );
}
