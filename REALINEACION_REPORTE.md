# Realineación doc↔código — Reporte

> Fecha: 2026-08-28 (tarde) · Continúa y cierra `PODA_REPORTE.md`.
> **Base de verificación:** `fitogenix-server` **`a0428bd`** (punta de `main` local; está
> **1 commit adelante de `origin/main` `5712b36`, sin pushear**) y `fitogenix-native`
> **`b7715b8`** (= `origin/main`). Sin cambios respecto de la sesión anterior, así que
> ninguna conclusión de `PODA_REPORTE.md` quedó invalidada por commits nuevos.
> Notas: el `git fetch` de `fitogenix-native` falla por credenciales (se usó el ref local);
> `fitogenix-server` tiene un untracked, `scripts/score-histogram.ts`.

## Convención de estados

`CONTEXT.md` ya tenía ✅/⚠️/🔴. Se **amplió a cuatro** en vez de introducir un sistema
paralelo: se sumó **🟡 = decidido, no implementado**. La distinción que importa y que no
existía: **⚠️ es "no verificado"; 🟡 es "verificado como ausente, y ya decidido"**. Un ✅ sin
ruta de archivo no es ✅. Un 🟡 nunca se escribe en presente.

---

## FASE 1 — Los dos archivos que nadie había mirado

### 00-orquestador.md

| Referencia | Caso | Acción | Verificado contra |
|---|---|---|---|
| Identidad: "sos el agente principal de **la migración**" | (c) | Reescrito: es el coordinador del producto. La migración terminó | `fitogenix-native` sin `src/infrastructure/` ni `src/app/api/` |
| `POST /products/lookup` "orquesta todo: cache → OFF/OBF/Edamam → Claude" (L73) | (c) — C-07 | Eliminado. Reemplazado por catalog-only, con la consecuencia de priorización | `productLookupService.ts` docstring + `resolveByBarcode`/`resolveByName` |
| Tabla de archivos críticos: `productLookupService.ts` = "Redis→Supabase→catálogo→OFF/OBF/Edamam→Claude" (L139) | (c) — C-07 | Corregido | ídem |
| Bandas transcritas `≥75 · 50–74 · 25–49 · 0–24` (L23) | duplicación | Podado a `CONTEXT.md §3`. **Era la última transcripción de bandas del set** | `scoring/constants.ts` `TIERS` |
| Bloque "Arquitectura actual (el problema)": `+api.ts`, `analyze+api.ts`, queries directas a Supabase | (c) | Eliminado. Describía el estado pre-Fase 0 como presente | `fitogenix-native/src/app/` — no existe `api/` |
| "Plan de migración" (6 fases, ~90 líneas) | (c) | Eliminado del prompt. Lo abierto → `CONTEXT.md §8`; la historia → `BITACORA_DECISIONES.md` | — |
| "Estado actual de la migración" con checklist, fechas y SHAs (C-05) | (c) | Eliminado. Un changelog dentro de un system prompt se desactualiza el primer día | `AUDITORIA_SETUP_AGENTICO.md` C-05 |
| Fase 3: "escribir tests para `lookupProduct.ts`" | (c) | Eliminado — ese archivo del cliente ya no tiene lógica | `fitogenix-native/src/domain/product/lookupProduct.ts` = solo tipos |
| Contexto de negocio B2C + freemium duplicado | duplicación | Podado a `CONTEXT.md §4` | — |
| 🔴 C-02 al pie del archivo | (a)→decidido | Reescrito como 🟡 con estado de hoy y destino | `src/routes/products/lookup.ts` |
| Protocolo de reversión · formato de handoff · reglas inamovibles | (b) | Conservados. Es lo mejor del archivo | — |

**Decisión de diseño que tomé y justifico:** la auditoría proponía partir el orquestador en
tres documentos (rol · plan · estado). **No creé documentos nuevos.** El estado abierto ya
tiene dueño y changelog en `CONTEXT.md §8`, y la historia en `BITACORA_DECISIONES.md`; un
tercer archivo habría sido un cuarto lugar donde el estado puede divergir — exactamente el
problema que esta tarea cierra.

### 02-agente-frontend.md

Fechado el **3 de julio**. Nunca revisado. **Reescrito completo**, no corregido: no había
sección salvable de la mitad arquitectónica.

| Referencia | Caso | Acción | Verificado contra |
|---|---|---|---|
| `src/infrastructure/` con 4 clientes HTTP | (c) | Eliminado — el directorio no existe | `ls fitogenix-native/src/` |
| `src/app/api/` con rutas `+api.ts` "NO tocar" | (c) | Eliminado — no existe | `find src/app` |
| `ftgEngine.ts` "~900 líneas, CERO tests, NO TOCAR" | (c) | Corregido: shim DEPRECATED de 455 B que reexporta `lib/contracts/product.ts` | `cat src/domain/product/ftgEngine.ts` |
| `lookupProduct.ts` "orquestador: cache→OFF→Claude→imagen" y `scoring.ts` | (c) | Eliminados. El primero es solo tipos; el segundo no existe | `head src/domain/product/lookupProduct.ts` |
| "Contexto de la migración: en Fase 1 el backend se separa… el Orquestador te va a avisar" | (c) | Eliminado. Ya pasó | — |
| Instrucción "crear `src/api/client.ts`" como trabajo futuro | (c) | Corregido: **existe**, y se documenta su contrato y sus errores tipados | `src/api/client.ts` |
| 8 dependencias "candidatas a eliminar en Fase 2" | (c) | **Ya se eliminaron.** Ninguna está en `package.json`, cero usos. Registrado como B-14 | `package.json` + grep |
| `expo-image` "instalada pero sin usar" | (b) — sigue válido | Conservado como pendiente | instalada, **0 imports** |
| React Query + persister sobre AsyncStorage | (b) | Conservado como pendiente. Hoy la persistencia es AsyncStorage a mano | sin `@tanstack/*`; `scanResultStore.tsx` |
| "Vitest, `src/**/*.test.ts`" | (c) matiz | Corregido: **cero tests en el cliente**, y es deliberado (`passWithNoTests: true`) | `vitest.config.ts`; `find src -name '*.test.ts*'` → vacío |
| Estado global: dos Context | (b) | Conservado y ampliado con lo que hace `scanResultStore` hoy | `src/presentation/scanResultStore.tsx` |
| Permisos, analytics | (b) | Conservados. Se ató `scan_failed` a distinguir "fuera de catálogo" de error de red | `api/client.ts` (`ProductNotInCatalogError`) |

---

## FASE 2 — Las tres decisiones aplicadas

### 2.1 · Los tres huecos entraron a `CONTEXT.md` — sin renumerar nada

| Ítem | Dónde fue | Por qué ahí |
|---|---|---|
| Selección de modelo Haiku vs Sonnet Vision | **§5.7** (nuevo) | Es arquitectura/stack, no criterio de producto. §2 habría mezclado "cómo puntuamos" con "con qué modelo pedimos datos" |
| Estado real de pantallas y features | **§1.6** (nuevo) | Es estado del producto; §1 es "el producto y su usuario" |
| Stack del cliente y restricciones de UX | **§5.8** (nuevo) | Continúa §5.1/§5.2, que cubren la arquitectura pero deliberadamente no bajan a librerías |

**Ninguna sección existente se movió ni se renumeró.** §1→§9 intactas; las tres nuevas se
agregaron al final de su sección padre. Los punteros `§X` de los 8 agentes siguen válidos
(verificado: 0 rotos).

Podas de origen: la regla de modelo salió de `03-agente-backend.md` (queda puntero + lo que
sí es del rol: documentar la elección en el call site); la tabla de pantallas salió de
`01-agente-ux.md`; `05` y `06` ahora apuntan a §5.7 en vez de a `03`; `04` apunta a §1.6.

**Verificar la tabla de pantallas antes de moverla cambió su contenido por completo.** Lo
que `01-agente-ux.md` afirmaba y era falso:

| Decía | Realidad ✅ |
|---|---|
| "Comunidad" es un tab placeholder que ocupa lugar valioso | **Ese tab ya no existe.** Las 5 pestañas son Inicio · Historial · Escanear · Guía · Perfil (`src/app/(tabs)/_layout.tsx`) |
| Historial = "un único slot en memoria" | Pantalla real con recientes y guardados, hidratada de AsyncStorage y sincronizada con el backend (`HistoryScreen.tsx`, `scanResultStore.tsx`) |
| "¿Olvidaste tu contraseña?" no hace nada | Funciona (`ForgotPasswordScreen.tsx` → `supabase.auth.resetPasswordForEmail`) |
| Google y Facebook decorativos | **Google funciona** (`lib/googleAuth.ts`). Facebook no existe |
| "Datos personales" sin acción | Tiene pantalla propia, más Privacidad y Ayuda |

**Además, un dato de UX que había caducado:** "el análisis tarda 2–8 s por la llamada a
Anthropic". Con el request catalog-only **no hay llamada a IA en el camino de request** — la
latencia es de Redis/Supabase. El caso borde que lo reemplaza es más difícil y no estaba
diseñado: **el producto que no está en el catálogo no se resuelve**, sin fallback. Quedó
escrito en §5.8 y como trabajo de UX en `01`.

### 2.2 · C-02 — el lookup va con cuota (🟡, no ✅)

- `CONTEXT.md §4.3`: reescrito. Encabezado con la decisión, **estado de hoy ✅** (endpoint
  público, cero cuotas — `grep` de `user_quotas`/`credits_used`/`quota` en `src/` y
  `migrations/`: 0 coincidencias) y **destino 🟡** con los **7 ítems** que faltan para ✅.
- `CONTEXT.md §8` B-1: de 🔴 abierto a 🟡 decidido.
- `03-agente-backend.md`: la sección de cuotas lleva encabezado de estado; la "excepción
  deliberada" de `Bug 2` pasa a tener **fecha de vencimiento** — sigue el "no toques el
  endpoint", pero por el motivo nuevo (falta el contrato), no porque sea permanente.
- `00-orquestador.md`: dice lo mismo. **La contradicción entre los dos archivos está
  cerrada.**
- `04-agente-qa.md`: 7 casos de test especificados como pendientes, incluido el de
  concurrencia (dos requests, un crédito → pasa uno) que es el que prueba la atomicidad.

**Sub-decisión que sigue abierta y bloquea la implementación:** qué pasa con el usuario
anónimo. Está marcada como tal en los cuatro archivos.

### 2.3 · NOVA — resultado del mapeo

**Fue el caso 2 y el caso 3 a la vez.** No se borró nada.

```
SERVER — se ingiere y se persiste:
  offService.ts:8,12 · openBeautyFactsApi.ts:12   ← se pide a la API
  cacheService.ts:79,200 · migrations/001,008     ← se persiste en products.nova_group
  scripts/etl/adapters/offAdapter.ts:90 · lib/merge.ts:125 · jobs/runMerge.ts:76
  scoring/types.ts:290-298  ← "sigue en la entrada porque viene en el payload y se
                               expone como información, pero desde v2.1 NO participa
                               del cálculo"
SERVER — el motor NO lo lee:
  steps.ts · pipeline.ts · rubric/   → CERO referencias
SERVER — se usa como señal de CALIDAD (uso que ningún documento registraba):
  scripts/audit-scores.ts:84-109 — "NOVA ya no entra al puntaje en v2.1, así que este
  contraste es una señal": NOVA 4 puntuando ≥75 se flaguea; NOVA 1 por debajo de 50 también
NATIVE — se le nombra al USUARIO:
  src/screens/HelpScreen.tsx:18
```

Acción: se documentó el hecho exacto en `CONTEXT.md §8`, y **B-4 se desdobló** en **B-4**
(C-08, la composición del score) y **B-4b** (C-09, NOVA). B-4b queda 🔴 escalado a producto,
no cerrado: como el copy se lo nombra al usuario, si NOVA se retira hay que sacarlo también
de la pantalla; y si se sostiene, hay que explicar en qué sentido participa. La limpieza de
código —columna, migración, adapters, tipos— queda propuesta como tarea aparte, no ejecutada.

---

## FASE 3 — Los otros seis

`01` · `03` · `04` · `05` · `06` ajustados (detalle arriba y en las tablas de 2.1/2.2).
**`07-agente-devops.md`: sin cambios** — se revisó contra el código y no tenía ninguna
afirmación desalineada; sus hallazgos (sin `Dockerfile`, sin `engines.node`, rate limit en
memoria) siguen siendo ciertos y ya están en `CONTEXT.md §8` B-9.

**Instrucciones reescritas, no solo descripciones corregidas** (era el pedido específico):

- `03-agente-backend.md`: *"que `enrichWithAI` y `aiLookupProduct` se llamen en el punto
  correcto de la cascada"* era una instrucción sobre un flujo que no existe. Reemplazada por
  las tres responsabilidades reales de hoy: validar lo que devuelve Claude antes de
  persistir, que `data_source`/`ai_enriched` reflejen fielmente el origen, y coordinar con
  ETL cualquier cambio de firma —porque es **su** pipeline el que se rompe, no una request.
- `00-orquestador.md`: "actualizá el estado del plan de migración" → priorizar
  `CONTEXT.md §8`, que tiene dueño y changelog.
- `02-agente-frontend.md`: "creá `src/api/client.ts`" → "existe, y este es su contrato".

---

## FASE 4 — El resto de la documentación

| Documento | Hallazgo | Acción |
|---|---|---|
| **`fitogenix-server/README.md`** | 🔴 **El peor caso que quedaba.** Documentaba la cascada `OFF→OBF→Edamam→Claude` como *la* arquitectura del lookup, con tabla de niveles 1a/1b/2/3, y usaba `mapOFFToProduct`. También decía "Unit tests (119)" y describía tests de cascada que ya no existen | Reescrita la sección de arquitectura a catalog-only con la nota de por qué; conteo de tests corregido; la verificación e2e del 7-8/7 marcada como **anterior** al rediseño y conservada como registro histórico de los adapters (que es lo que hoy le importa al ETL) |
| `scripts/etl/README.md` | Limpio | Sin cambios — el rename ya se había aplicado en `a0428bd` |
| `LEEME.md` | Se llamaba "Agentes de **Migración**"; mantenía su propio "orden de prioridad actual" (cuarto lugar donde el estado podía divergir) | Retitulado; la prioridad ahora remite a `CONTEXT.md §8`; se agregó `CONTEXT.md` como primera fila de la tabla |
| `README.md` (set de agentes) | No mencionaba `CONTEXT.md`, hablaba de "la migración" | Corregido |
| `AUDITORIA_SETUP_AGENTICO.md` | Ver abajo | Encabezado de estado agregado |
| `CONVENCIONES_EQUIPO.md` · `DICCIONARIO_DOMINIO.md` · `BITACORA_DECISIONES.md` | Sin desalineaciones nuevas | Sin cambios |
| `fitogenix-native/CLAUDE.md`, `AGENTS.md`, `README.md` | 1 y 3 líneas; el README sin afirmaciones de arquitectura desactualizadas | Sin cambios |

### Qué sigue vigente de `AUDITORIA_SETUP_AGENTICO.md`

Se revisó entera y se le agregó un encabezado de estado. Resumen:

- **Cerrados:** C-01 (con corrección: acusaba a `03` de bandas que `03` no tenía), C-03
  (verificado: 0 citas a archivos inexistentes), C-04, C-05, C-06.
- **Decidido, no implementado:** C-02.
- **Siguen vigentes sin avanzar:** su §4 (nadie auditó los datos que ya están en la base),
  su §5 (falta dueño de la nutrición = B-12), su §6 (`architect` y `nutrition` no existen).
- **Su plan de acción:** pasos 1, 3, 4, 5 hechos; 2 decidido; 6 (harness LangGraph) y 7
  (auditoría de `products`) sin empezar.
- **No vio dos cosas:** C-07 y C-14.
- **Su estimación de tamaños** quedó ~22% por debajo de lo medido.

---

## FASE 5 — Verificación

| # | Chequeo | Resultado |
|---|---|---|
| 1 | Punteros de archivo | **122 rutas únicas** citadas en los 8 agentes + `CONTEXT.md`, resueltas por sufijo contra los dos repos. **0 rotas.** Las 4 que no resuelven son deliberadas: `+api.ts` y `scoring.ts` citados como *"lo que ya NO existe"*, y `service-account*.json` como patrón hipotético de `.gitignore` |
| 2 | Punteros de sección | **0 rotos.** §1–§9 y todas sus subsecciones existen; las tres nuevas (§1.6, §5.7, §5.8) no desplazaron ninguna |
| 3 | Duplicación | Bandas: **1 coincidencia**, en `03` (`"banda Excelente (≥75, ver scoring/constants.ts)"`) — cita al código, no re-declaración. `mapOFFToProduct`: **0 usos como nombre vigente** (3 menciones, todas "renombrada desde"). Cascada: **0 descripciones** como camino de request |
| 4 | Consistencia entre agentes | Catalog-only: coherente en los 6 archivos donde aplica, contradicho en 0. Cuota: `00`, `03`, `04` y `CONTEXT.md` dicen lo mismo con el mismo estado. NOVA: `03` y `04` coinciden y ambos apuntan a B-4b |
| 5 | Estados | 0 🔴 sin puntero a §8/B-/C-. 0 🟡 escritos en presente (se corrigió uno en `00`: *"va CON CUOTA"* → *"VA A REQUERIR CUOTA — decidido, sin implementar"*). Los ✅ agregados citan archivo |

**Una inconsistencia propia detectada y corregida durante la verificación:** `CONTEXT.md`
§5.3 y §8 B-5 seguían diciendo que `03` y `00` documentaban la cascada. Después de
corregirlos, esa afirmación pasó a ser falsa. C-07 quedó cerrado en ambos lugares.

**Lo que NO se pudo verificar:** `npm test` / `npx vitest run` **no corre en este entorno**
(`MODULE_NOT_FOUND` en el binding nativo de `rolldown`). El conteo de tests que se publicó
es **estático**: 27 archivos, ~345 casos `it()`. La nota histórica de "416 tests en verde"
sigue sin reproducirse. No es un fallo del proyecto; es una limitación de la VM.

---

## Tamaños — dato, no métrica

| Archivo | Antes | Después | Δ |
|---|---|---|---|
| `00-orquestador.md` | 20.811 | 9.895 | **−10.916 (−52%)** |
| `01-agente-ux.md` | 11.932 | 12.445 | +513 |
| `02-agente-frontend.md` | 12.238 | 11.277 | −961 |
| `03-agente-backend.md` | 26.389 | 27.836 | +1.447 |
| `04-agente-qa.md` | 5.487 | 7.493 | +2.006 |
| `05-agente-datos.md` | 9.931 | 9.986 | +55 |
| `06-agente-etl-data.md` | 19.204 | 19.304 | +100 |
| `07-agente-devops.md` | 9.147 | 9.147 | 0 |
| **8 agentes** | **115.139** | **107.383** | **−7.756 (−6,7%)** |
| `CONTEXT.md` | 24.032 | 36.363 | +12.331 |

El único recorte grande es el orquestador, y no salió de podar duplicación: salió de sacar
un plan de migración terminado y un checklist de estado que no debían vivir en un system
prompt. `04` creció un 37% porque le faltaban criterios de aceptación, no porque sobrara.
