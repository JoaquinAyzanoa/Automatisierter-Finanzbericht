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
export type Ambito = "Nacional" | "Exterior";

export interface Operacion {
  id: number;
  texto: string;
  moneda: Moneda;
  ambito: Ambito;
  tags: string[];
  respeta_filtro: boolean;
  aplica_retencion: boolean;
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
  data: { texto: string; moneda: Moneda; ambito: Ambito }
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
  data: { texto?: string; moneda?: Moneda; ambito?: Ambito }
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
  items: {
    texto: string;
    moneda: Moneda;
    ambito: Ambito;
    tags: string[];
    respeta_filtro: boolean;
    aplica_retencion: boolean;
  }[]
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

export interface OperacionOpcion {
  pos: number;
  texto: string;
  moneda: Moneda;
  ambito: Ambito;
  respeta_filtro: boolean;
}

export type FilaInforme = Record<string, string | number | null>;

export interface MergeClasificado {
  columnas: string[];
  filas: FilaInforme[];
  operaciones: OperacionOpcion[];
  fecha_columna: string | null;
}

export async function obtenerMergeClasificado(
  token: string
): Promise<MergeClasificado> {
  const res = await fetch(`${BASE}/informes/merge`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as MergeClasificado;
}

export async function descargarInformeClasificado(
  token: string
): Promise<Blob> {
  const res = await fetch(`${BASE}/informes/merge/descargar`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return await res.blob();
}

// ---- Sharepoint -----------------------------------------------------------

export interface SharepointConfig {
  link_principal: string | null;
  meses: Record<string, string>;
}

export async function obtenerSharepointConfig(
  token: string
): Promise<SharepointConfig> {
  const res = await fetch(`${BASE}/sharepoint`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as SharepointConfig;
}

export async function guardarSharepointConfig(
  token: string,
  config: SharepointConfig
): Promise<SharepointConfig> {
  const res = await fetch(`${BASE}/sharepoint`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as SharepointConfig;
}

// ---- Agentes de aduana ----------------------------------------------------

export interface AgentesConfig {
  rucs: string[];
  relacionados: string[];
}

export async function obtenerAgentesConfig(
  token: string
): Promise<AgentesConfig> {
  const res = await fetch(`${BASE}/agentes`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as AgentesConfig;
}

export async function guardarAgentesConfig(
  token: string,
  config: AgentesConfig
): Promise<AgentesConfig> {
  const res = await fetch(`${BASE}/agentes`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as AgentesConfig;
}

// ---- Retención ------------------------------------------------------------

export interface RetencionConfig {
  activo: boolean;
  rucs: string[];
}

export async function obtenerRetencionConfig(
  token: string
): Promise<RetencionConfig> {
  const res = await fetch(`${BASE}/retencion`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as RetencionConfig;
}

export async function guardarRetencionConfig(
  token: string,
  config: RetencionConfig
): Promise<RetencionConfig> {
  const res = await fetch(`${BASE}/retencion`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as RetencionConfig;
}

// ---- Procesos / Historial -------------------------------------------------

export interface ProcesoResumen {
  id: string;
  nombre: string | null;
  created_at: string;
  updated_at: string;
  fecha_inicio: string | null;
  fecha_final: string | null;
  n_filas: number;
}

export async function renombrarProceso(
  token: string,
  id: string,
  nombre: string
): Promise<{ id: string; nombre: string | null }> {
  const res = await fetch(`${BASE}/procesos/${id}/nombre`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ nombre }),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as { id: string; nombre: string | null };
}

export interface ProcesoDetalle extends MergeClasificado {
  id: string;
  created_at: string;
  updated_at: string;
  fecha_inicio: string | null;
  fecha_final: string | null;
  tipo_cambio: number | null;
}

export async function crearProceso(token: string): Promise<{ id: string }> {
  const res = await fetch(`${BASE}/procesos`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as { id: string };
}

export async function listarProcesos(token: string): Promise<ProcesoResumen[]> {
  const res = await fetch(`${BASE}/procesos`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as ProcesoResumen[];
}

export async function obtenerProcesoLatest(
  token: string
): Promise<ProcesoDetalle> {
  const res = await fetch(`${BASE}/procesos/latest`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as ProcesoDetalle;
}

export async function obtenerProceso(
  token: string,
  id: string
): Promise<ProcesoDetalle> {
  const res = await fetch(`${BASE}/procesos/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as ProcesoDetalle;
}

export async function guardarProceso(
  token: string,
  id: string,
  body: {
    fecha_inicio: string | null;
    fecha_final: string | null;
    tipo_cambio?: number | null;
    overrides: Record<string, number | null>;
  }
): Promise<{ id: string; updated_at: string }> {
  const res = await fetch(`${BASE}/procesos/${id}/guardar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as { id: string; updated_at: string };
}

export async function guardarYDescargarProceso(
  token: string,
  id: string,
  body: {
    fecha_inicio: string | null;
    fecha_final: string | null;
    tipo_cambio?: number | null;
    overrides: Record<string, number | null>;
  }
): Promise<Blob> {
  const res = await fetch(`${BASE}/procesos/${id}/descargar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return await res.blob();
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

// ---- Macros de pago masivo (BCP) ------------------------------------------

export type MonedaMacro = "SOL" | "USD";
export type TipoArchivoMacro =
  | "plantilla_SOL"
  | "plantilla_USD"
  | "bd_SOL"
  | "bd_USD";

export interface ArchivoMacro {
  tipo: TipoArchivoMacro;
  nombre: string | null;
  detalle: string;
  subido_en: string | null;
}

export interface AbonoMacro {
  ruc: string;
  nombre: string;
  tipo_cuenta: string;
  cuenta: string;
  en_bd: boolean;
  total: number;
  documentos: { numero: string; monto: number }[];
}

export interface MacroMoneda {
  moneda: MonedaMacro;
  abonos: AbonoMacro[];
  total: number;
  n_documentos: number;
  sin_cuenta: number;
  faltan: string[];
}

export async function listarArchivosMacro(
  token: string
): Promise<ArchivoMacro[]> {
  const res = await fetch(`${BASE}/macros/archivos`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as ArchivoMacro[];
}

export async function subirArchivoMacro(
  token: string,
  tipo: TipoArchivoMacro,
  archivo: File
): Promise<ArchivoMacro> {
  const form = new FormData();
  form.append("archivo", archivo);
  const res = await fetch(`${BASE}/macros/archivos/${tipo}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as ArchivoMacro;
}

export async function vistaPreviaMacros(
  token: string,
  procesoId: string
): Promise<{ proceso_id: string; monedas: MacroMoneda[] }> {
  const res = await fetch(`${BASE}/macros/procesos/${procesoId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return (await res.json()) as { proceso_id: string; monedas: MacroMoneda[] };
}

/** `fecha` en formato YYYY-MM-DD. */
export async function descargarMacro(
  token: string,
  procesoId: string,
  moneda: MonedaMacro,
  fecha: string
): Promise<Blob> {
  const params = new URLSearchParams({ moneda, fecha });
  const res = await fetch(
    `${BASE}/macros/procesos/${procesoId}/descargar?${params}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }
  return await res.blob();
}
