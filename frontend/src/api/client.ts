const API_URL = import.meta.env.VITE_API_URL ?? "";
const BASE = `${API_URL}/api/v1`;

export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
  } catch {
    /* ignore */
  }
  return `Request failed (${res.status})`;
}

export async function login(
  username: string,
  password: string
): Promise<string> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

export async function fetchMe(token: string): Promise<User> {
  const res = await fetch(`${BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as User;
}

export interface ProcesarReporteadorResult {
  rows: number;
  mensaje: string;
}

export async function procesarReporteador(
  token: string,
  archivo: File
): Promise<ProcesarReporteadorResult> {
  const form = new FormData();
  form.append("archivo", archivo);
  const res = await fetch(`${BASE}/reporteador/procesar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as ProcesarReporteadorResult;
}

export async function descargarAvanceReporteador(token: string): Promise<Blob> {
  const res = await fetch(`${BASE}/reporteador/avance`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return await res.blob();
}

export async function procesarProveedores(
  token: string,
  dolares: File,
  soles: File
): Promise<ProcesarReporteadorResult> {
  const form = new FormData();
  form.append("dolares", dolares);
  form.append("soles", soles);
  const res = await fetch(`${BASE}/proveedores/procesar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as ProcesarReporteadorResult;
}

export async function descargarAvanceProveedores(token: string): Promise<Blob> {
  const res = await fetch(`${BASE}/proveedores/avance`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return await res.blob();
}

export async function procesarMerge(
  token: string
): Promise<ProcesarReporteadorResult> {
  const res = await fetch(`${BASE}/merge/procesar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as ProcesarReporteadorResult;
}

export async function descargarAvanceMerge(token: string): Promise<Blob> {
  const res = await fetch(`${BASE}/merge/avance`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return await res.blob();
}

export type Moneda = "SOL" | "USD";

export interface Operacion {
  id: number;
  texto: string;
  moneda: Moneda;
  created_at: string;
}

export async function listarOperaciones(token: string): Promise<Operacion[]> {
  const res = await fetch(`${BASE}/operaciones`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as Operacion[];
}

export async function crearOperacion(
  token: string,
  data: { texto: string; moneda: Moneda }
): Promise<Operacion> {
  const res = await fetch(`${BASE}/operaciones`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as Operacion;
}

export async function actualizarOperacion(
  token: string,
  id: number,
  data: { texto?: string; moneda?: Moneda }
): Promise<Operacion> {
  const res = await fetch(`${BASE}/operaciones/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as Operacion;
}

export async function eliminarOperacion(
  token: string,
  id: number
): Promise<void> {
  const res = await fetch(`${BASE}/operaciones/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
}

export async function reemplazarOperaciones(
  token: string,
  items: { texto: string; moneda: Moneda }[]
): Promise<Operacion[]> {
  const res = await fetch(`${BASE}/operaciones`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(items),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as Operacion[];
}

/** Dispara la descarga de un Blob en el navegador. */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
