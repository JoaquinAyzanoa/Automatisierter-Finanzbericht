# Automatización del Informe de Pagos a Proveedores

**Presentación a Gerencia de Finanzas** · 10 minutos

---

## 1. De qué se trata

Convertimos en una **aplicación** el informe de pagos a proveedores que hasta ahora
se armaba **a mano en Excel**.

Hoy el sistema ya cubre cerca del **80% del trabajo manual diario**.

> ⏱️ *1 min*

---

## 2. El punto de partida

Armar el informe significaba, todas las veces:

- Descargar y limpiar el **Reporteador**
- Combinar los archivos de **proveedores en soles y en dólares**
- Cruzarlos factura por factura
- Clasificar cada factura en su tipo de pago
- Calcular **detracciones, retenciones y montos netos**
- Copiar y pegar todo en la plantilla del informe
- Revisar que los totales cuadren

**Riesgos:** tiempo, errores de copiado, criterios que dependían de quién lo hacía.

> ⏱️ *1.5 min*

---

## 3. Qué se construyó

Una aplicación de escritorio que se abre con **doble clic** y tiene cuatro secciones:

| Sección | Para qué sirve |
|---|---|
| **Entrada de información** | Se cargan los 3 archivos de origen |
| **Informes** | Se revisa la clasificación y se descarga el Excel |
| **Historial** | Quedan guardadas todas las versiones generadas |
| **Configuración** | Se definen las reglas del negocio |

**No requiere conocimientos técnicos para usarla.**

> ⏱️ *1 min*

---

## 4. Cómo funciona: 3 pasos

### 1️⃣ Cargar
Se suben los tres archivos: Reporteador, Proveedores en Soles y Proveedores en Dólares.

### 2️⃣ Revisar
El sistema cruza la información y **clasifica cada factura automáticamente**.
En pantalla se puede corregir cualquier clasificación con un clic.

### 3️⃣ Descargar
Se genera el Excel final, ya con el formato del informe y sus fórmulas.

> ⏱️ *1.5 min*

---

## 5. Lo que el sistema decide solo

Cada factura se clasifica según reglas que **nosotros definimos**:

- **Moneda y origen** — soles o dólares, proveedor nacional o del exterior
- **Proveedores específicos** — RUCs asignados a un tipo de pago determinado
- **Tipo de comprobante** — por ejemplo, recibos por honorarios
- **Agentes de aduana** — las facturas de una misma Orden de Compra se agrupan
  y se consolidan para pagarle al agente

Lo que el sistema no puede decidir, lo **marca visiblemente** para que una persona
lo complete.

> ⏱️ *1.5 min*

---

## 6. Los cálculos que ya no se hacen a mano

| Cálculo | Cómo se resuelve |
|---|---|
| **Detracción** | Se aplica la tasa que viene en el reporteador |
| **Retención (3%)** | Se aplica solo cuando corresponde según SUNAT |
| **Neto a pagar** | Saldo menos detracción y retención |
| **Plazo de crédito** | Se ajusta al plazo pactado más cercano: 1, 7, 15, 30, 45 o 60 días |

**Sobre la retención**, el sistema respeta las excepciones del negocio:
no aplica a servicios, ni a proveedores del exterior, ni a agentes de retención,
ni a montos menores a S/ 700. Además se puede **activar o desactivar**.

> ⏱️ *2 min*

---

## 7. El resultado: un Excel con 3 hojas

### 📄 Resumen
La hoja ejecutiva: cuánto se paga por cada tipo de operación, saldos por banco,
saldo proyectado y **alertas de acción** (si hace falta vender o transferir dólares).

### 📄 Detalle
Todas las facturas ordenadas por tipo de pago, con **enlace directo al PDF de cada
factura** en SharePoint.

### 📄 Detalle de agentes
El desglose de los agentes de aduana, agrupado por Orden de Compra.

> ⏱️ *1.5 min*

---

## 8. Las reglas las controla Finanzas, no un programador

Todo esto se cambia desde la pantalla de **Configuración**, sin depender de nadie:

- Los tipos de operación y sus nombres
- Qué proveedores van a qué operación
- Los RUCs de los agentes de aduana
- Los agentes de retención y el tipo de cambio
- Las carpetas de SharePoint donde están las facturas

> ⏱️ *1 min*

---

## 9. Control y trazabilidad

- **Historial de versiones:** cada informe generado queda guardado y se le puede
  poner nombre para identificarlo
- **Se puede volver a descargar** cualquier versión anterior
- **Enlaces a las facturas:** desde el informe se abre el PDF de respaldo
- Los cambios manuales que se hacen en pantalla **quedan registrados**

> ⏱️ *1 min*

---

## 10. Qué sigue siendo manual

Con transparencia, esto todavía lo completa una persona:

- Los **saldos disponibles por banco** y el ingreso estimado en el Resumen
- Los **pagos anticipados**
- El nombre del agente cuando no hay factura suya en la Orden de Compra
- La **revisión final** antes de enviar

> ⏱️ *30 seg*

---

## 11. En resumen

✅ Lo que antes tomaba **horas de trabajo manual**, hoy se genera en **minutos**

✅ Los criterios de clasificación y los cálculos son **siempre los mismos**

✅ Las reglas las maneja **Finanzas**, sin depender de sistemas

✅ Cada informe queda **guardado y trazable**

**Próximo paso:** cerrar el 20% restante y afinar lo que el uso diario vaya pidiendo.

> ⏱️ *30 seg*

---

## Preguntas

*Gracias.*
