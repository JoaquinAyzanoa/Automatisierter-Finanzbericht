# Automatización de Informes Financieros

Aplicación web para **automatizar la generación de informes de finanzas en Excel**.
El usuario carga los archivos de origen (Reporteador y Proveedores SOL/USD), la app
los limpia, cruza y clasifica por operación, y genera un Excel con el formato de la
empresa (Detalle, Resumen y links a las facturas en SharePoint).

- **Backend:** Python 3.13 + FastAPI + SQLite (gestionado con [uv](https://docs.astral.sh/uv/)).
- **Frontend:** React + Vite + TypeScript (en español).

---

## Requisitos

Instala una vez en la máquina:

1. **Python + uv** — el gestor `uv` (instala y administra Python 3.13 solo):
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
2. **Node.js 20+** — descárgalo de <https://nodejs.org> (incluye `npm`).

Verifica que estén disponibles abriendo una terminal nueva:
```powershell
uv --version
node --version
```

---

## Puesta en marcha rápida (recomendada)

Tres archivos `.bat` en la raíz del proyecto:

1. **`setup.bat`** — ejecútalo **una sola vez**. Crea `backend/.env` desde la plantilla
   e instala las dependencias del backend (`uv sync`) y del frontend (`npm install`).
2. **`crear-acceso-directo.bat`** — ejecútalo una vez. Crea un lanzador
   **«Iniciar Finanzbericht.bat» en tu Escritorio** (con la ruta a esta carpeta ya
   incrustada), para arrancar la app con doble clic desde cualquier lado.
3. **`iniciar.bat`** — arranca la app: abre el **backend** (<http://localhost:8000>) y el
   **frontend** (<http://localhost:3000>) en ventanas separadas y abre el navegador.

Uso típico:

```
1) doble clic  setup.bat                  (solo la primera vez)
2) doble clic  crear-acceso-directo.bat   (crea el acceso en el Escritorio)
3) doble clic  "Iniciar Finanzbericht"    (en el Escritorio, cada vez que uses la app)
```

Para **detener** la app, cierra las dos ventanas de terminal que se abrieron
("Backend (8000)" y "Frontend (3000)").

### Credenciales de administrador

El usuario admin se crea en la base de datos al primer arranque a partir de
`backend/.env`. Edita estas líneas antes (o después) de iniciar:

```env
ADMIN_USER=tu_usuario
ADMIN_PASSWORD=tu_contraseña
```

---

## Puesta en marcha manual

Si prefieres controlar cada servicio por separado:

**Backend** (puerto 8000):
```powershell
cd backend
copy .env.example .env   # solo la primera vez; luego edita ADMIN_USER/ADMIN_PASSWORD
uv sync                  # instala dependencias
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend** (puerto 3000), en otra terminal:
```powershell
cd frontend
npm install              # solo la primera vez
npm run dev
```

Abre <http://localhost:3000>.

### Con `just` (opcional)

Si tienes [`just`](https://github.com/casey/just) instalado:
```powershell
just install       # instala backend + frontend
just run-backend   # arranca el backend
just run-frontend  # arranca el frontend (en otra terminal)
just test-backend  # corre los tests
```

---

## Estructura

```
Automatisierter-Finanzbericht/
├── setup.bat            # Instalación (una vez): .env + dependencias
├── crear-acceso-directo.bat  # Crea el lanzador en el Escritorio
├── iniciar.bat          # Arranca backend + frontend (doble clic)
├── justfile             # Recetas de desarrollo (opcional)
├── backend/             # FastAPI + SQLite (capas API -> Servicios -> Repos -> Modelos)
│   ├── app/
│   ├── tests/
│   ├── .env.example
│   └── pyproject.toml
└── frontend/            # React + Vite + TypeScript
    ├── src/
    └── package.json
```

---

## Flujo de uso

1. **Entrada de información:** sube Reporteador + DOLARES/SOLES PROVEEDORES y pulsa **Procesar**.
   Al terminar te lleva a **Informes** con el proceso creado.
2. **Configuración:** define las **operaciones** (moneda/ámbito/tags) y el **Sharepoint**
   (link principal + nombre de la carpeta de cada mes) para los enlaces a facturas.
3. **Informes:** revisa/reasigna filas por operación, aplica el filtro de fechas y **descarga**
   el Excel con el formato de la empresa.
4. **Historial:** cada proceso queda guardado; puedes volver a abrirlo y editarlo.

---

## Puertos

| Servicio | URL                        |
| -------- | -------------------------- |
| Backend  | http://localhost:8000      |
| Frontend | http://localhost:3000      |
| API docs | http://localhost:8000/docs |

---

## Tests

```powershell
cd backend
uv run pytest
```
