# Automatización del Informe de Pagos a Proveedores

Documentación funcional y técnica del sistema.

---

## Índice

**Parte I — Perspectiva de Finanzas**
1. [Qué resuelve el sistema](#1-qué-resuelve-el-sistema)
2. [Los insumos y su cruce](#2-los-insumos-y-su-cruce)
3. [La orden de compra y el producto](#3-la-orden-de-compra-y-el-producto)
4. [Clasificación de facturas en operaciones](#4-clasificación-de-facturas-en-operaciones)
5. [Agentes de aduana: consolidación por orden de compra](#5-agentes-de-aduana-consolidación-por-orden-de-compra)
6. [Detracción, retención y neto](#6-detracción-retención-y-neto)
7. [Plazo de crédito](#7-plazo-de-crédito)
8. [Tipo de cambio](#8-tipo-de-cambio)
9. [Filtro de fechas y la categoría "Otros"](#9-filtro-de-fechas-y-la-categoría-otros)
10. [El informe entregado](#10-el-informe-entregado)
11. [Enlaces a las facturas](#11-enlaces-a-las-facturas)
12. [Lo que sigue siendo manual](#12-lo-que-sigue-siendo-manual)

**Parte II — Arquitectura del backend**
13. [Stack y organización](#13-stack-y-organización)
14. [Configuración y arranque](#14-configuración-y-arranque)
15. [Persistencia y modelo de datos](#15-persistencia-y-modelo-de-datos)
16. [Autenticación](#16-autenticación)
17. [Catálogo de endpoints](#17-catálogo-de-endpoints)
18. [Servicios: la cadena de procesamiento](#18-servicios-la-cadena-de-procesamiento)
19. [Generación del Excel](#19-generación-del-excel)

**Parte III — Frontend**
20. [Stack y estructura](#20-stack-y-estructura)
21. [Autenticación y navegación](#21-autenticación-y-navegación)
22. [Las cuatro secciones](#22-las-cuatro-secciones)
23. [Cliente de API y componentes](#23-cliente-de-api-y-componentes)

**Parte IV — Operación**
24. [Puesta en marcha](#24-puesta-en-marcha)
25. [Decisiones de diseño y sus motivos](#25-decisiones-de-diseño-y-sus-motivos)

---

# Parte I — Perspectiva de Finanzas

## 1. Qué resuelve el sistema

El informe semanal de **Pagos a Proveedores** se armaba manualmente en Excel:
descargar reportes, cruzarlos, clasificar cada factura según su tipo de pago,
calcular detracciones y retenciones, y volcar todo en una plantilla.

El sistema automatiza esa cadena completa: recibe los archivos de origen, cruza
la información, clasifica, calcula y entrega el Excel final con el formato de
siempre. Lo que antes eran horas de trabajo repetitivo hoy son minutos de carga
y revisión.

El principio de diseño es que **las reglas del negocio las controla Finanzas**,
no el código: qué operaciones existen, qué proveedores van a cada una, quiénes
son agentes de aduana o de retención, y el tipo de cambio se editan desde la
propia aplicación.

## 2. Los insumos y su cruce

El proceso arranca con **tres archivos**:

| Archivo | Contenido |
|---|---|
| **Reporteador** | Datos de compras: orden de compra, producto, registro y tasa de detracción |
| **Proveedores — Dólares** | Facturas pendientes en dólares |
| **Proveedores — Soles** | Facturas pendientes en soles |

El sistema los procesa en cadena:

1. **Reporteador** — se limpia: se conservan solo las columnas necesarias
   (número de documento, orden de compra, producto, registro, RUC, detracción),
   se extrae la orden de compra y se eliminan duplicados exactos.
2. **Proveedores** — los dos archivos se combinan en uno solo, agregando una
   columna **MONEDA** (`SOL` o `USD`) según su origen.
3. **Cruce (merge)** — el archivo combinado de proveedores **manda**: se le
   agregan las columnas del reporteador mediante un cruce por **RUC + N° de
   documento**.

Dos precisiones importantes:

- El cruce es **por la izquierda**: el resultado conserva **todas** las facturas
  de proveedores y solo esas. Si una factura no encuentra su par en el
  reporteador, igual aparece —sin orden de compra ni producto—, no se pierde.
- Antes del cruce se elimina cualquier duplicado del reporteador por esa misma
  llave, para que una factura no se multiplique.

Si el archivo de proveedores no trae las columnas llave, el sistema **se detiene
con un mensaje claro** en lugar de generar un informe incompleto.

## 3. La orden de compra y el producto

En el reporteador, la orden de compra suele venir **incrustada al inicio de la
descripción del producto**, no en su propia columna:

```
"30959-A ALCOHOL ISOAMILICO THC"
 └──┬──┘ └──────────┬──────────┘
  O/C            producto
```

El sistema separa ambas partes tomando el primer bloque de la descripción cuando
es un código válido:

| Descripción original | N° O/C-O/S | Producto |
|---|---|---|
| `31015 SERVICIO Y` | `10031015` | `SERVICIO Y` |
| `31116-1 SERVICIO X` | `31116-1` | `SERVICIO X` |
| `30959-A ALCOHOL ISOAMILICO THC` | `30959-A` | `ALCOHOL ISOAMILICO THC` |
| `ALCOHOL SIN CODIGO` | *(vacío)* | `ALCOHOL SIN CODIGO` |

Hay una regla propia del negocio: cuando el código es **solo numérico**, se le
antepone `100` (`31015` → `10031015`); cuando ya trae guiones o sufijos, se
respeta tal cual. Si la columna de orden de compra ya viene con un valor, no se
toca.

Esta separación no es cosmética: la orden de compra es la llave con la que luego
se consolidan los pagos a agentes de aduana.

## 4. Clasificación de facturas en operaciones

Una **operación** es una categoría de pago (por ejemplo *Pago masivo
proveedores*, *Pagos varios*, *Materia Prima Exterior*). Cada una se define en
Configuración con su **nombre**, **moneda** y **ámbito** (Nacional o Exterior).

Cada factura se asigna siguiendo este orden de prioridad:

**1. Asignaciones especiales (tienen prioridad).** A cada operación se le pueden
agregar *tags*, que son de dos tipos:

- **Un RUC o texto** — si aparece en la fila, esa factura va a esa operación.
- **`tipo:NN`** — se compara contra el tipo de comprobante. Por ejemplo,
  `tipo:02` envía todos los recibos por honorarios a *Pagos varios*.

Los tags respetan la **moneda** de la operación, pero **no el ámbito**: un
proveedor con RUC extranjero puede asignarse a una operación nacional si así se
configuró. Esto fue necesario porque hay proveedores del exterior que
operativamente se pagan como nacionales.

**2. Regla por defecto.** Si ningún tag coincide, la factura cae en la primera
operación cuyo **ámbito y moneda** coincidan con los suyos. El ámbito se deduce
del RUC: se considera **nacional** un RUC de 11 dígitos que empiece con `10` o
`20`; todo lo demás es **exterior**.

**3. Sin coincidencia.** Si no hay operación compatible, la factura queda **sin
categoría** y aparece en el grupo *Otros*, fuera del informe, hasta que alguien
la asigne manualmente.

En pantalla, cualquier clasificación se corrige con un desplegable. Esas
correcciones **quedan guardadas** y prevalecen sobre la clasificación automática.

## 5. Agentes de aduana: consolidación por orden de compra

Las importaciones generan varias facturas de distintos proveedores (flete,
puerto, agenciamiento, comisión) que **se pagan de forma consolidada al agente de
aduana**. El sistema las agrupa por **N° de Orden de Compra**.

Una orden de compra se consolida cuando ocurre cualquiera de estas condiciones:

| Disparador | Descripción |
|---|---|
| **RUC de agente de aduana** | Alguna factura de esa O/C es del agente |
| **RUC de proveedor relacionado** | Alguna factura es de un proveedor vinculado (flete, puerto, agenciamiento) |
| **Tipo de comprobante 21** | La factura va a agentes por sí sola, tenga o no O/C |

Cuando se dispara, **todas** las facturas de esa orden de compra salen de su
operación normal y pasan a la sección de agentes: se depositará el total al
agente, no a cada proveedor por separado.

**El nombre del agente** se resuelve así: si en la orden de compra hay una
factura de un agente configurado, se usa su nombre. Si la O/C se consolidó solo
por proveedores relacionados o por tipo 21, no hay forma de saber el agente y el
sistema escribe **"Colocar nombre de agente manualmente"** — un marcador visible
en lugar de un dato inventado.

Las órdenes de compra repetidas que **no** involucran agentes ni proveedores
relacionados **no se consolidan**: se quedan en su operación.

Desde la pantalla de Informes se puede sacar una factura de esta sección y
mandarla a otra operación; esa decisión se respeta en la descarga.

## 6. Detracción, retención y neto

### Detracción

La tasa viene en el reporteador. El monto se calcula como:

```
DET = IMPORTE × %DET
```

### Retención de IGV

Se aplica el **3% del IMPORTE**, pero solo cuando corresponde. El sistema
descarta la retención en estos casos:

| Excepción | Motivo |
|---|---|
| La operación está marcada **"No aplica retención"** | Servicios básicos, transferencias, planilla |
| El proveedor es **del exterior** | La retención es a bienes nacionales |
| La factura **tiene detracción** | Es un servicio, no un bien |
| El proveedor es **agente de retención** | Excepción de SUNAT, lista configurable |
| El importe **no supera S/ 700** | Por debajo del umbral no aplica |

Para facturas en dólares el umbral se evalúa convirtiendo con el tipo de cambio
vigente. La tasa (3%) y el umbral (S/ 700) están fijos por norma; la lista de
agentes de retención y el interruptor general se manejan desde Configuración.

### Neto a pagar

El neto contempla que la detracción **puede haberse pagado ya**:

| Situación | Neto |
|---|---|
| Sin detracción | `SALDO − RET` |
| Con detracción, aún no pagada | `SALDO − DET − RET` |
| Con detracción ya pagada (el pagado coincide con la detracción) | `SALDO − RET` |

Esta lógica va como **fórmula viva en el Excel**, de modo que si se corrige un
importe a mano, el neto se recalcula solo. La misma fórmula se usa en la hoja de
detalle y en la de agentes, para que los totales cuadren entre ambas.

## 7. Plazo de crédito

El plazo se obtiene restando `FEC.VCTO − FEC.DOC`, pero la resta cruda produce
valores que no corresponden a ningún plazo pactado (6, 14, 31 días).

El sistema **ajusta al plazo establecido más cercano** entre 1, 7, 15, 30, 45 y
60 días:

| Días reales | Plazo mostrado |
|---|---|
| 6 | **7** |
| 14 | **15** |
| 31 | **30** |
| más de 60 | **60** |

Si falta alguna de las dos fechas, la celda queda vacía en lugar de mostrar un
error.

## 8. Tipo de cambio

Se edita en la pantalla de **Informes** y queda guardado junto al proceso, de
modo que cada informe conserva el tipo de cambio con el que se generó.

Cumple dos funciones: evalúa el umbral de retención de las facturas en dólares y
alimenta la celda del **TOTAL CONSOLIDADO** en la hoja Resumen.

## 9. Filtro de fechas y la categoría "Otros"

El informe corresponde a un rango de fechas. Al aplicar el filtro, las facturas
cuya fecha de vencimiento queda fuera del rango se mueven a **Otros** y no entran
al Excel.

Hay una excepción configurable: una operación puede marcarse como **"No respetar
filtro de fecha"**. Sus facturas se mantienen aunque venzan fuera del rango —
pensado para servicios básicos y pagos recurrentes que deben incluirse siempre.

El grupo *Otros* es desplegable y tiene su propio buscador y filtros por columna,
para revisar qué quedó fuera y recuperar algo si hace falta.

## 10. El informe entregado

Un archivo Excel con **tres hojas**.

### Resumen

La hoja ejecutiva, estructurada en cinco bloques:

| Bloque | Contenido |
|---|---|
| **I. Pagos a realizar** | Importe por operación, con su banco y moneda, y los totales en soles, dólares y consolidado |
| **II. Saldos disponibles por banco** | Se completa a mano |
| **III. Saldo proyectado** | Saldo actual + ingresos − pagos programados |
| **IV. Estado de liquidez** | Excedente o déficit por cuenta |
| **V. Alertas y acciones** | Qué hacer: vender dólares, transferir, o liquidez suficiente |

Al final, una **banda de estado de liquidez** resume la situación: el estado
(*"Se necesita vender y transferir dólares"*), el total de venta requerida, el
saldo disponible y el proyectado. Los importes por operación son **fórmulas** que
apuntan a los totales de la hoja Detalle, de modo que todo se recalcula solo.

### Detalle

Todas las facturas agrupadas por operación, con su cabecera, sus filas y un TOTAL
por sección. Las secciones fijas (*Agentes de Aduanas*, *Pagos al Personal*,
*Pagos Anticipados*) tienen sus propias listas.

Dentro de cada operación las filas van **ordenadas alfabéticamente por
proveedor**. Se muestran: proveedor, RUC, tipo, número de documento, las tres
fechas, importe, pagado, saldo, plazo, detracción, retención, neto, detalle,
orden de compra, registro y el enlace a la factura.

### Detalle de agentes

El desglose de lo consolidado en la sección de agentes: todas las facturas
agrupadas **por orden de compra**, separadas por moneda (soles primero, luego
dólares), con subtotal por O/C y total por moneda. Los totales de la hoja
Detalle **jalan por fórmula** desde aquí.

## 11. Enlaces a las facturas

Cada PDF de factura se llama igual que su **N° de Registro** y vive en una
carpeta de SharePoint organizada por mes. Como el registro codifica el año y mes
en sus primeros seis dígitos (`AAAAMM…`), el sistema deduce a qué carpeta
corresponde y arma el enlace.

En Configuración se define la carpeta general y el nombre de la carpeta de cada
mes. En el informe, la columna SUSTENTO queda como **hipervínculo** al PDF. Si
falta configuración o el mes no está mapeado, la celda queda en blanco en lugar
de generar un enlace roto.

## 12. Lo que sigue siendo manual

Con transparencia, estas partes las completa una persona:

- **Saldos disponibles por banco** e ingresos estimados en el Resumen
- **Pagos anticipados** (la sección queda con filas en blanco para llenar)
- El **nombre del agente** cuando no hay factura suya en la orden de compra
- La **revisión final** y las reasignaciones de criterio

---

# Parte II — Arquitectura del backend

## 13. Stack y organización

API REST en **Python 3.13** con **FastAPI**, **SQLAlchemy** sobre **SQLite**,
**pandas** para el procesamiento de datos y **openpyxl** para generar el Excel.

La organización es por capas, cada una con una responsabilidad:

```
app/
├── api/v1/endpoints/   Capa HTTP: valida entrada, delega, responde
├── services/           Lógica de negocio (el corazón del sistema)
├── repositories/       Acceso a datos
├── models/             Tablas (SQLAlchemy)
├── schemas/            Contratos de entrada/salida (Pydantic)
├── core/               Configuración, seguridad, logging
└── db/                 Sesión y creación de tablas
```

La regla que se respeta en todo el proyecto: **los endpoints no contienen lógica
de negocio**. Reciben la petición, llaman a un servicio y devuelven el resultado.
Toda la inteligencia vive en `services/`.

## 14. Configuración y arranque

La configuración se centraliza en `core/config.py` y se carga desde variables de
entorno o un archivo `.env`: base de datos, clave y expiración del token,
orígenes CORS permitidos, carpeta de reportes y credenciales del administrador
inicial.

Al arrancar, la aplicación:
1. Configura el logging
2. Crea las tablas que falten y aplica **mini-migraciones** (columnas nuevas)
3. Siembra el usuario administrador si está definido en la configuración
4. Registra el router bajo el prefijo `/api/v1`

**Sobre las migraciones:** el proyecto no usa Alembic. Al agregar columnas se
emplea una función que verifica si la columna existe y, si no, la agrega. Es
suficiente para el alcance actual (base local de un solo usuario) y evita
introducir una herramienta más; si el esquema creciera, correspondería migrar a
Alembic.

## 15. Persistencia y modelo de datos

Base **SQLite** local. Las tablas:

| Tabla | Rol |
|---|---|
| `users` | Usuarios y contraseñas cifradas |
| `operaciones` | Las categorías de pago y sus reglas |
| `procesos` | Cada informe generado, con su snapshot completo |
| `agente_aduana_config` | RUCs de agentes de aduana y proveedores relacionados |
| `retencion_config` | Interruptor de retención y RUCs exceptuados |
| `sharepoint_config` | Carpeta general y nombres de carpetas por mes |
| `reports` | Registro genérico de reportes |

**`operaciones`** guarda por cada una: texto, moneda, ámbito, tags (JSON), si
respeta el filtro de fechas y si aplica retención.

**`procesos`** es la pieza central de la trazabilidad. Cada proceso guarda un
**snapshot en JSON** con las filas ya clasificadas y la configuración de
operaciones vigente al momento de procesar, más el rango de fechas, el tipo de
cambio y un nombre editable. Esto permite volver a descargar un informe anterior
tal como se generó.

Las tablas de configuración (`agente_aduana_config`, `retencion_config`,
`sharepoint_config`) son de **fila única** (`id=1`): guardan ajustes globales, no
colecciones.

## 16. Autenticación

**JWT con OAuth2 Bearer.** El usuario se autentica y recibe un token que expira a
las 8 horas; el frontend lo envía en la cabecera `Authorization` de cada
petición. Las contraseñas se almacenan cifradas con **bcrypt**.

La dependencia `CurrentUser` protege los endpoints: valida el token, busca al
usuario y verifica que esté activo. Basta declararla como parámetro para que el
endpoint quede protegido.

## 17. Catálogo de endpoints

Todos bajo el prefijo `/api/v1` y protegidos, salvo los de autenticación y salud.

### Autenticación — `/auth`
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/auth/login` | Login con JSON, devuelve el token |
| `POST` | `/auth/token` | Login con formulario (estándar OAuth2) |
| `GET` | `/auth/me` | Datos del usuario autenticado |

### Procesamiento de archivos
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/reporteador/procesar` | Sube y limpia el Reporteador |
| `GET` | `/reporteador/avance` | Descarga el resultado intermedio |
| `POST` | `/proveedores/procesar` | Sube y combina los archivos de soles y dólares |
| `GET` | `/proveedores/avance` | Descarga el combinado |
| `POST` | `/merge/procesar` | Cruza proveedores con reporteador |
| `GET` | `/merge/avance` | Descarga el cruce |

Cada paso deja su resultado en disco, lo que permite **auditar la cadena**:
si un dato sale mal, se puede ver en qué etapa se desvió.

### Informes y procesos
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/informes/merge` | Cruce clasificado, listo para mostrar |
| `GET` | `/informes/merge/descargar` | Excel del cruce clasificado |
| `POST` | `/procesos` | Crea un proceso (snapshot) desde el cruce |
| `GET` | `/procesos` | Lista el historial |
| `GET` | `/procesos/latest` | Último proceso |
| `GET` | `/procesos/{id}` | Un proceso concreto |
| `POST` | `/procesos/{id}/nombre` | Renombra el proceso |
| `POST` | `/procesos/{id}/guardar` | Guarda fechas, tipo de cambio y reasignaciones |
| `POST` | `/procesos/{id}/descargar` | Guarda y genera el Excel final |

### Configuración
| Método | Ruta | Descripción |
|---|---|---|
| `GET` `POST` `PUT` `DELETE` | `/operaciones` | CRUD de operaciones (el `PUT` sin id reemplaza toda la lista) |
| `GET` `PUT` | `/agentes` | RUCs de agentes de aduana y proveedores relacionados |
| `GET` `PUT` | `/retencion` | Interruptor y RUCs exceptuados |
| `GET` `PUT` | `/sharepoint` | Carpeta general y carpetas por mes |

### Otros
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Verificación de estado |
| `GET` `POST` `DELETE` | `/reports` | Registro genérico de reportes |
| `GET` | `/finance/sample` | Datos de ejemplo |

## 18. Servicios: la cadena de procesamiento

El flujo completo, servicio por servicio:

```
reporteador_service ─┐
                     ├─► merge_service ─► clasificacion_service ─► proceso_service ─► detalle_export
proveedores_service ─┘
```

| Servicio | Responsabilidad |
|---|---|
| `reporteador_service` | Limpia el reporteador y extrae la orden de compra del producto |
| `proveedores_service` | Combina soles y dólares agregando la columna MONEDA |
| `merge_service` | Cruza por RUC + N° documento, resolviendo alias de nombres de columna |
| `clasificacion_service` | Asigna cada fila a su operación (tags → regla por defecto) |
| `proceso_service` | Crea y guarda los snapshots, aplica reasignaciones manuales |
| `detalle_export` | Genera el Excel final sobre la plantilla |
| `agente_config_service` | Agentes de aduana y proveedores relacionados |
| `retencion_config_service` | Configuración de retención |
| `sharepoint_config_service` | Configuración de SharePoint |
| `sharepoint` | Construye los enlaces a los PDF |
| `excel_utils` | Lectura tolerante de archivos y escritura de hojas |

Dos detalles de robustez:

- **`excel_utils.read_table`** acepta `.xlsx`, `.xls` y `.csv`, y ante un archivo
  inválido lanza un error de negocio que el endpoint traduce a un mensaje claro
  para el usuario.
- **`merge_service`** resuelve las columnas llave por **alias**: acepta `RUC`,
  `R.U.C.`, `N° DOCUMENTO`, `NRO DOCUMENTO` y otras variantes, normalizando
  espacios y mayúsculas. Los archivos de origen no siempre llegan con
  encabezados idénticos.

**Sobre las reasignaciones manuales:** cuando el usuario cambia la operación de
una fila, esa fila se marca internamente para que el sistema **respete su
decisión** y no vuelva a moverla por las reglas automáticas (por ejemplo, no la
devuelve a la sección de agentes).

**Sobre la configuración al descargar:** el proceso guarda un snapshot, pero al
generar el Excel se consulta la configuración **vigente** de retención, agentes y
SharePoint. Así, cambiar una regla se refleja al volver a descargar, sin
reprocesar.

## 19. Generación del Excel

`detalle_export` es el servicio más extenso, y por una razón: no genera un Excel
desde cero, sino que **rellena la plantilla del usuario** conservando sus colores,
formatos y fórmulas.

El procedimiento: se lee la plantilla, se detectan sus secciones por el texto de
sus títulos, y se reconstruye cada hoja fila por fila copiando estilos de las
filas modelo e inyectando los datos.

Algunas particularidades que resolver:

- **Columna insertada.** La salida agrega una columna **RUC** que la plantilla no
  tiene, por lo que todas las columnas siguientes se desplazan. Un mapeo
  centralizado traduce las posiciones y **traslada las fórmulas** al nuevo
  destino.
- **Secciones reordenadas.** *Pagos al Personal* y *Pagos Anticipados* se emiten
  al final, y las operaciones que existen en Configuración pero no en la
  plantilla se agregan tras la última — con sus filas en blanco si no tienen
  facturas.
- **Filas insertadas o borradas en el Resumen.** openpyxl no ajusta fórmulas,
  celdas combinadas ni formato condicional al mover filas. Una función propia se
  encarga de las cuatro cosas: traslada fórmulas, y desarma y rearma las celdas
  combinadas y los rangos de formato condicional en su nueva posición.
- **Fórmulas vivas.** Plazo, retención, neto y los totales se escriben como
  fórmulas de Excel, no como valores calculados. El informe sigue siendo un
  documento de trabajo: al corregir un importe, todo lo demás se recalcula.

---

# Parte III — Frontend

## 20. Stack y estructura

**React 18 + TypeScript**, empaquetado con **Vite**. Sin librerías de UI ni de
estado: los estilos son CSS propio y el estado se maneja con los hooks de React.

```
src/
├── api/client.ts       Todas las llamadas al backend
├── components/         Componentes reutilizables
├── context/            Sesión del usuario
├── pages/
│   ├── Login.tsx
│   ├── Dashboard.tsx   Layout con menú lateral
│   └── sections/       Las cuatro pantallas
└── main.tsx
```

La decisión de no incorporar dependencias adicionales es deliberada: la
aplicación tiene cuatro pantallas y un flujo lineal. Agregar un router o un
gestor de estado habría añadido complejidad sin beneficio.

## 21. Autenticación y navegación

`AuthContext` mantiene la sesión: guarda el token, lo persiste para sobrevivir a
recargas y expone al usuario. `App.tsx` decide qué mostrar — **Login** o
**Dashboard** — según haya sesión.

La navegación es por estado local: `Dashboard` mantiene qué sección está activa y
`Sidebar` la cambia. No hay rutas en la URL.

## 22. Las cuatro secciones

### Entrada de información

Tres campos de archivo. Al procesar, encadena las llamadas en orden —
reporteador, proveedores, cruce— y finalmente crea el proceso. Informa el
resultado de cada etapa (filas procesadas) o el error si algo falla.

### Informes

La pantalla principal. Muestra las facturas **agrupadas por operación**, cada
grupo con su conteo y total.

Funcionalidades:

- **Buscador** global sobre todas las columnas
- **Reasignación** de la operación de cada fila mediante un desplegable
- **Rango de fechas** y botón para aplicar el filtro
- **Tipo de cambio** editable
- **Sección de agentes de aduana**, calculada en vivo con la misma lógica que la
  descarga, de modo que la pantalla y el Excel coinciden
- **Grupo "Otros"** desplegable, con buscador propio y filtros por columna
- **Descarga** del Excel

Dos comportamientos que vale la pena señalar:

- **Autoguardado.** Los cambios se guardan solos tras una pausa, y también al
  salir de la sección, para no perder trabajo al navegar.
- **Opciones acotadas.** El desplegable de cada fila ofrece solo las operaciones
  de su misma moneda, para evitar reasignaciones incoherentes.

### Historial

Lista de procesos generados, con fecha y número de filas. Permite **renombrarlos**
—de ahí nombres como `2407_VF_SINCAMBIOS`— y volver a abrir cualquiera.

### Configuración

Donde se define todo el comportamiento del sistema:

| Bloque | Qué se configura |
|---|---|
| **Operaciones** | Nombre, moneda y ámbito de cada una; se agregan, ordenan y eliminan |
| **Asignaciones especiales** | Tags por operación, si respeta el filtro de fechas y si aplica retención |
| **Agentes de aduana** | RUCs de agentes y de proveedores relacionados |
| **Retención** | Interruptor general y RUCs exceptuados |
| **Sharepoint** | Carpeta general y nombre de la carpeta de cada mes |

Cada bloque se guarda por separado y el botón permanece deshabilitado si no hay
cambios pendientes.

## 23. Cliente de API y componentes

**`api/client.ts`** concentra todas las llamadas al backend. Expone los tipos de
datos, adjunta el token, y traduce los errores a un tipo propio con su código y
mensaje, que las pantallas usan para mostrar avisos comprensibles.

**Componentes:**

| Componente | Función |
|---|---|
| `Sidebar` | Menú lateral con las cuatro secciones |
| `OperacionSelect` | Desplegable para reasignar la operación de una fila |
| `TablaScroll` | Contenedor de tabla con barra de desplazamiento superior |

`TablaScroll` responde a un detalle práctico: las tablas tienen veinte columnas y
la barra de desplazamiento inferior obliga a bajar hasta el final para moverse en
horizontal. El componente agrega una barra **arriba** cuando la tabla es larga.

`OperacionSelect` se despliega fuera del flujo de la tabla para que el menú no
quede recortado, y se cierra al desplazar o presionar Escape.

---

# Parte IV — Operación

## 24. Puesta en marcha

El proyecto incluye archivos para arrancar sin conocimientos técnicos:

| Archivo | Para qué |
|---|---|
| `setup.bat` | Instala las dependencias por primera vez |
| `iniciar.bat` | Levanta backend y frontend y abre el navegador |
| `crear-acceso-directo.bat` | Crea el acceso directo en el Escritorio |

El uso diario es hacer **doble clic** en el acceso directo del Escritorio.

Herramientas: **uv** para las dependencias de Python y **npm** para las del
frontend. La base de datos SQLite y los archivos intermedios se generan solos en
el primer arranque.

## 25. Decisiones de diseño y sus motivos

| Decisión | Motivo |
|---|---|
| **Rellenar la plantilla** en vez de generar el Excel desde cero | El informe conserva el formato que Finanzas ya conoce y aprobó |
| **Fórmulas vivas** en vez de valores calculados | El Excel sigue siendo un documento de trabajo: se corrige un dato y todo se ajusta |
| **Reglas configurables** en vez de escritas en el código | Renombrar una operación o agregar un agente no requiere un programador |
| **Snapshot por proceso** | Un informe pasado se reproduce tal como se generó |
| **Guardar cada etapa** en disco | Si un dato sale mal, se puede rastrear en qué paso se desvió |
| **SQLite y sin dependencias pesadas** | Es una herramienta local para un equipo pequeño; la simplicidad es una ventaja |
| **Marcadores visibles** ante datos faltantes | Es preferible un *"Colocar nombre de agente manualmente"* que un dato inventado |

---

*Documentación del proyecto **Automatisierter Finanzbericht**.*
