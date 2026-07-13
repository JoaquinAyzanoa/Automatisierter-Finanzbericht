import { useState, type ChangeEvent, type FormEvent } from "react";

import {
  ApiError,
  crearProceso,
  procesarMerge,
  procesarProveedores,
  procesarReporteador,
} from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import "./EntradaInformacion.css";

const FILE_ACCEPT = ".xls,.xlsx,.csv";

const FILE_FIELDS = [
  { key: "reporteador", label: "Reporteador" },
  { key: "dolaresProveedores", label: "DOLARES PROVEEDORES" },
  { key: "solesProveedores", label: "SOLES PROVEEDORES" },
] as const;

type FileKey = (typeof FILE_FIELDS)[number]["key"];

type Status = { type: "ok" | "error"; msg: string } | null;

const fileIcon = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" width={18} height={18}>
    <path d="M13 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V9z" />
    <path d="M13 3v6h6" />
  </svg>
);

const checkIcon = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" width={18} height={18}>
    <path d="M20 6L9 17l-5-5" />
  </svg>
);

interface Props {
  onProcesado?: (procesoId: string) => void;
}

export function EntradaInformacion({ onProcesado }: Props) {
  const { token } = useAuth();
  const [files, setFiles] = useState<Record<FileKey, File | null>>({
    reporteador: null,
    dolaresProveedores: null,
    solesProveedores: null,
  });
  const [status, setStatus] = useState<Status>(null);
  const [processing, setProcessing] = useState(false);

  function onFileChange(key: FileKey, e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setFiles((prev) => ({ ...prev, [key]: file }));
    setStatus(null);
  }

  const allFilesSelected = FILE_FIELDS.every((f) => files[f.key] !== null);
  const canProcess = allFilesSelected && !processing;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canProcess || !token) return;

    setProcessing(true);
    setStatus(null);
    try {
      // 1) Reporteador (limpieza) 2) Proveedores (combinar USD/SOL)
      // 3) Merge (proveedores + reporteador por RUC y NUMERO).
      const reporteador = await procesarReporteador(token, files.reporteador!);
      const proveedores = await procesarProveedores(
        token,
        files.dolaresProveedores!,
        files.solesProveedores!
      );
      const merge = await procesarMerge(token);
      // Registrar el proceso en el historial (ID/hash + snapshot).
      const proceso = await crearProceso(token);
      onProcesado?.(proceso.id);
      setStatus({
        type: "ok",
        msg: `Procesado correctamente — Reporteador: ${reporteador.rows} · Proveedores: ${proveedores.rows} · Merge: ${merge.rows} filas. Proceso ${proceso.id}. Revísalo en «Informes».`,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setStatus({ type: "error", msg: err.message });
      } else {
        setStatus({
          type: "error",
          msg: "No se pudo procesar la información. Inténtalo de nuevo.",
        });
      }
    } finally {
      setProcessing(false);
    }
  }

  return (
    <section className="panel">
      <p className="panel__lead">
        Carga los tres archivos de origen para generar el informe. Configura el
        Sharepoint en «Configuración».
      </p>

      <form className="entrada" onSubmit={handleSubmit} noValidate>
        <div className="entrada__files">
          {FILE_FIELDS.map((field) => {
            const file = files[field.key];
            return (
              <div className="filefield" key={field.key}>
                <span className="filefield__label">{field.label}</span>
                <label
                  className={
                    "filefield__drop" + (file ? " is-filled" : "")
                  }
                >
                  <input
                    type="file"
                    accept={FILE_ACCEPT}
                    onChange={(e) => onFileChange(field.key, e)}
                  />
                  <span className="filefield__icon">
                    {file ? checkIcon : fileIcon}
                  </span>
                  <span className="filefield__text">
                    {file ? file.name : "Selecciona un archivo"}
                  </span>
                  <span className="filefield__hint">.xls · .xlsx · .csv</span>
                </label>
              </div>
            );
          })}
        </div>

        {status && (
          <div className={"entrada__status entrada__status--" + status.type}>
            {status.msg}
          </div>
        )}

        <div className="entrada__actions">
          <button
            type="submit"
            className="entrada__submit"
            disabled={!canProcess}
          >
            {processing ? "Procesando…" : "Procesar"}
          </button>
        </div>
      </form>
    </section>
  );
}
