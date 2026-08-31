# Reporte — aplicación de las tres decisiones del 2026-08-31

> Continúa `PODA_REPORTE.md` y `REALINEACION_REPORTE.md`. Como ellos, es **registro
> fechado**: describe un momento y no pretende seguir siendo cierto. El estado vigente
> está en `CONTEXT.md`; la historia de las decisiones, en `BITACORA_DECISIONES.md`.

## 0 · Estado de los repos — el delta contra lo documentado

La sesión arrancó con una discrepancia de SHAs, y el delta resultó ser **hacia adelante**:
la Fase 0 del prompt de decisiones ya se había ejecutado y pusheado.

| Repo | Documentado | Real al arrancar | Lectura |
|---|---|---|---|
| fitogenix-agents | `01369b8`, árbol sucio | `1ab31c3`, limpio, `== origin` | La poda + realineación del 28/8 quedó commiteada el 30/8 23:01 (14 archivos, +1146/−504) |
| fitogenix-server | `a0428bd`, README sucio | `d73f378`, `== origin` | Ídem, mismo minuto |
| fitogenix-native | `b7715b8`, limpio | `b7715b8` ✅ | Coincide |

`git fetch` real contra `origin` en agents y server: **0 ahead, 0 behind**. `fitogenix-native`
no se pudo fetchear (sin credenciales HTTPS para la org `fitogenix` desde esta sesión); su
`main` local coincide con lo documentado.

### Los locks — el mecanismo de los commits que fallaban en silencio

| Lock | Antigüedad | Efecto |
|---|---|---|
| `fitogenix-native/.git/index.lock` | 13 días (18/8 19:57, el mismo minuto que `b7715b8`) | **Bloquea cualquier `git add`/`git commit`** |
| `fitogenix-server/.git/objects/maintenance.lock` | 18/8 20:03 | Bloquea mantenimiento en background |

Los dos borrados. El de `native` explica la nota de `BITACORA_DECISIONES.md` ADR-002 parte 2:
*"quedaron como stubs sin uso porque no se pudieron `git rm` en la sesión que hizo el cambio"*.
No fue un olvido: el índice estaba trabado.

**Se reprodujo en vivo durante esta sesión.** Un `git status` propio dejó un `index.lock`
nuevo en `fitogenix-agents` que el sandbox no podía borrar. Es un modo de falla real y
recurrente de este entorno, no una anécdota: conviene chequear `find .git -name '*.lock'`
antes de dar un commit por hecho.

---

## 1 · Las tres decisiones

### Decisión 1 — tier inicial gratuito (ADR-003)

`POST /products/lookup` queda **abierto y sin cuota**. Pasa de 🟡 con siete ítems de gap a
**✅ sin ticket**: el código ya cumple la decisión. El encuadre cambia de **deuda a diseño**
— el endpoint público deja de tener "fecha de vencimiento".

Rastro de cuota reescrito, archivo por archivo:

| Archivo | Qué decía | Qué dice |
|---|---|---|
| `CONTEXT.md §4.1` | "Beta abierta ⚠️" | Tier inicial gratuito ✅, con `lookup.ts` como evidencia |
| `CONTEXT.md §4.2` | El freemium, sin marcar | Encabezado explícito: **nada de esta sección está vigente**; un agente que la lea como estado actual va a proponer trabajo que no hay que hacer |
| `CONTEXT.md §4.3` | `🟡 C-02 … VA CON CUOTA` + 7 ítems de gap | `✅ Tier inicial gratuito`, reescrita entera. Los 7 ítems eliminados |
| `CONTEXT.md §8` B-1 | 🟡 con gap de implementación | Cerrado ✅ |
| `CONTEXT.md §9` | Entrada del 28/8 "va con cuota" | **Eliminada.** La evolución vive en la bitácora, no en dos lugares |
| `03-agente-backend.md` | "Excepción deliberada **con fecha de vencimiento 🟡**" | Diseño del MVP ✅ + "no le agregues auth". La § Lógica de Cuotas pasa a **no-MVP, no la implementes**, con el punto de extensión en una línea |
| `04-agente-qa.md` | 7 casos de test de cuota | **Eliminados**, reemplazados por los de anónimo y fuera-de-catálogo |
| `00-orquestador.md` | B-1 como pendiente prioritario | Sección nueva: *"Lo que ya NO es una decisión pendiente — no lo reabras"* |
| `01-agente-ux.md` | § Gestión del Paywall como trabajo | Marcada **no es el MVP, no lo diseñes todavía** |
| `02-agente-frontend.md` | "cuando se implemente la cuota…" | "no hay cuota ni paywall en el MVP", y los 3 eventos de paywall no se instrumentan |
| `05-agente-datos.md` | "freemium con 10 análisis/mes" como acotador de costo | Corregido: no hay tope por usuario; lo acota el catálogo (§4.4) |
| `AUDITORIA_SETUP_AGENTICO.md` | C-02 "decidido, falta implementar" | Cerrado ✅, con el hallazgo original marcado como ya ejecutado |
| `CONVENCIONES_EQUIPO.md` | "scoring, cuotas, umbrales" | "cualquier regla de consumo que exista en el futuro" |

**Punto de extensión, y nada más:** el descuento entraría en el handler de
`src/routes/products/lookup.ts`, antes de `lookupProduct`. Sin tablas, RPC, RLS ni flags.

**Sub-decisión cerrada:** los escaneos de un anónimo **se migran** a su historial si se
registra en esa misma sesión. El prompt de decisiones la daba por abierta 🔴 y el de
orquestación por tomada; se tomó la segunda por ser posterior y traer camino de
implementación.

### Decisión 2 — NOVA se sostiene (ADR-004)

`CONTEXT.md §2.4` reescrita con las tres formas en que NOVA participa, y ninguna es el
puntaje. `§8` B-4b cerrado como *sostenido*. La limpieza de código queda descartada.

**Lo que ningún documento registraba, y es la razón operativa más fuerte para conservar el
campo:** `scripts/audit-scores.ts` usa `nova_group` como **señal de calidad del puntaje** —
flaguea un NOVA 4 que puntúa ≥75 y un NOVA 1 que puntúa por debajo de 50. Un desacuerdo
entre la clasificación de procesamiento de OFF y el motor v2.1 es la forma más barata de
detectar un puntaje probablemente mal. Documentado en `05-agente-datos.md`.

**Desbloquea B-13**, que estaba 🔴 esperando justamente esta decisión.

### Decisión 3 — pantalla de producto fuera de catálogo (ADR-005)

Ver §3: lo que se encontró al verificar cambió el alcance.

---

## 2 · El copy de `HelpScreen.tsx` — veredicto

**Miente.** Textual del FAQ *"¿Cómo se calcula el puntaje?"*:

> "Combinamos la calidad de los ingredientes, la información nutricional, **el nivel de
> procesamiento (NOVA)** y la transparencia de los datos disponibles."

El motor v2.1 **no lee `nova_group`** (`steps.ts`/`pipeline.ts`/`rubric/`: cero referencias).
Lo que sí hace es penalizar marcadores de ultraprocesado en el texto de ingredientes.

El segundo FAQ, *"¿Por qué no encuentra mi producto?"*, sigue prometiendo *"Buscamos primero
en Open Food Facts y completamos lo que falta con IA"* — la cascada retirada el 18/8.

**Un FAQ que sí está bien y conviene no tocar:** *"¿Necesito una cuenta para escanear
productos?"* → *"No. Podés escanear y ver resultados sin crear una cuenta. La cuenta sirve
para guardar tu historial y preferencias."* Coincide exactamente con la decisión nueva. El
copy de la app ya decía lo correcto sobre el tier gratuito **tres días antes de que se
decidiera**.

---

## 3 · El recorrido real de fuera-de-catálogo, y el error que se corrigió

**Lo que se documentó primero, en esta misma sesión, era falso.** Se escribió que el 404 del
lookup se tipifica como `ProductNotInCatalogError` y que ningún archivo de la UI lo consume.

Lo verificado contra el call site:

- `lookupProduct()` **devuelve `null`** en el 404. No lanza.
- `ProductNotInCatalogError` lo lanza **únicamente `saveProductRemote()`**, en otro camino:
  intentar guardar un producto que no está en el catálogo.
- Los dos hooks de lookup (`useScanFlow`, `useProductSearch`) **sí detectaban** el `null` y
  ponían un mensaje propio.

El error venía de `REALINEACION_REPORTE.md` (28/8), que ató `scan_failed` a
`ProductNotInCatalogError`, y se propagó sin verificarse contra el código.

**Así que B-16 no era "no hay nada". Era "se detecta bien y se presenta mal":**

1. En `useScanFlow` los dos casos caían en el mismo `state: "error"` → ícono de alerta y
   botón *"Volver a intentar"* para algo que reintentar no puede cambiar.
2. El copy decía *"Estamos sumando productos todo el tiempo — probá de nuevo más adelante"*,
   exactamente la promesa que ADR-005 prohíbe: el catálogo se puebla por ETL en batch, sin
   cola por pedido.

⚠️ **`scan_failed` no existe en el código.** Cero coincidencias en `fitogenix-native/src/`,
aunque `02-agente-frontend.md` lo daba por atado a esta distinción.

---

## 4 · Anónimo vs logueado — qué se encontró y qué se implementó

**Estado que se encontró:** `scanResultStore.tsx` hidrataba `history` y `saved` desde
AsyncStorage en un `useEffect` **al montar, sin mirar la sesión**. No distinguía anónimo de
logueado: el anónimo persistía.

**El backend no tiene agujero** — verificado: `/users/me/history` registra `requireAuth` y
expone **solo `GET`**, y `recordScan` solo corre con un `userId` resuelto. El cambio es
exclusivamente del cliente.

**Implementado** (`fitogenix-native`, rama `decisiones/anonimo-y-fuera-de-catalogo`):

- Hidratación desde AsyncStorage: espera a `sessionReady` y **solo corre si hay usuario**.
  Esperar es deliberado — hidratar antes de saber si hay sesión le muestra a un anónimo, por
  un instante, el historial del último que usó ese teléfono.
- Los efectos de persistencia no escriben sin sesión.
- **Por eso `SIGNED_OUT` ahora borra el disco explícitamente.** Antes alcanzaba con el
  `setState([])`, porque los efectos escribían `[]`; con la guarda nueva, sin ese
  `multiRemove` el historial del que se desloguea **quedaría en el teléfono**. Es la parte
  del cambio que más fácil se pasaba por alto, y la única con consecuencia de privacidad.
- No leer el disco sin sesión también protege un dato ajeno: `migrateLocalSavedIfNeeded()`
  lee la clave de guardados directo de AsyncStorage. Si un anónimo hidratara vacío y después
  persistiera, borraría los guardados pre-Fase-2 antes de que esa migración one-shot corra.
- **Migración anónimo→logueado:** los hooks pasan la query a `setResult`, que sin sesión la
  retiene en memoria. Al iniciar sesión se re-emiten los lookups con el token — el backend
  registra el escaneo dentro del propio `POST /products/lookup` (`recordScan`, upsert
  idempotente), y no hay endpoint de escritura de historial. En serie y de la más vieja a la
  más nueva, para que el orden del historial del servidor sea el orden real.

**Copy:** todo el texto nuevo vive en `src/constants/scanCopy.ts`, con las restricciones de
ADR-005 escritas al lado. **Es provisorio: el copy final lo define UX.** Cambiar el texto no
requiere tocar lógica.

---

## 5 · Tests

**`fitogenix-server`: 410 tests en 27 archivos, todos en verde. `tsc --noEmit` limpio.**

Es la primera vez que la suite se corre desde que se documentó. Cierra el *"416 tests en
verde"* que arrastraba ⚠️ sin reproducir desde el 18/8. El conteo estático del 28/8 (~345
casos `it()`) subestimaba: no cuenta los casos generados dentro de tablas.

**Nota de entorno, importante para no sacar la conclusión equivocada:** `npm test` falla en
un shell Linux contra el `node_modules` de esta Mac, porque solo está instalado
`@rolldown/binding-darwin-arm64`. Ese binding **sí está presente** (16 MB), así que en macOS
la suite debería correr sin problema — la nota de *"npm test falla por el binding nativo de
rolldown"* probablemente ya no aplica. Los 410 se corrieron con un `npm ci` limpio sobre el
mismo `package-lock.json`, fuera del repo.

**`fitogenix-native`: 14 tests nuevos, todos en verde. `tsc --noEmit` limpio.**

Son los **primeros tests del cliente** (`vitest.config.ts` declara `passWithNoTests: true` a
propósito). Cubren `src/presentation/anonScanMigration.ts`, que es la lógica que puede
perder datos del usuario en silencio: orden de re-emisión, cap conservando las más recientes,
tolerancia a fallas, y que la re-emisión sea en serie y no en paralelo. El módulo recibe el
`lookup` por parámetro justamente para poder testearse sin React Native ni red.

⚠️ **Lo que no tiene test:** las guardas de persistencia y el `multiRemove` del `SIGNED_OUT`.
Testearlas requiere renderizar el Provider, y `@testing-library/react-native` no está
instalado. Agregarlo es una decisión de Jere, no una que corresponda tomar de costado.

---

## 6 · Costo de contexto — medido, no estimado

Base de hoy: `CONTEXT.md` **47.439 B** (creció desde 36.363 por §1.6, §2.4, §4.3, §8 y §9),
los 8 agentes **118.536 B**.

Bytes por sección de `CONTEXT.md`:

| §1 | §2 | §3 | §4 | §5 | §6 | §7 | §8 | §9 | encabezado |
|---|---|---|---|---|---|---|---|---|---|
| 8.022 | 5.758 | 1.734 | 5.067 | 6.896 | 3.732 | 1.916 | 5.332 | 6.337 | 2.645 |

Proyección con un cargador por sección, usando **las secciones que cada agente cita hoy**:

| Agente | Hoy (SSOT entero) | Con loader | Ahorro |
|---|---|---|---|
| `00-orquestador` | 58.860 | 58.860 | **0%** |
| `01-agente-ux` | 63.333 | 43.945 | 31% |
| `02-agente-frontend` | 61.291 | 46.124 | 25% |
| `03-agente-backend` | 75.321 | 63.336 | 16% |
| `04-agente-qa` | 57.236 | 41.527 | 27% |
| `05-agente-datos` | 58.678 | 37.778 | 36% |
| `06-agente-etl-data` | 66.743 | 39.524 | 41% |
| `07-agente-devops` | 56.586 | 20.338 | **64%** |
| **Total, 8 invocaciones** | **498.048** | **351.432** | **29%** |

**La conclusión importante para la Fase 5:** el cargador solo, sin tocar los agentes, da
−29%. No alcanza para el −44%/−65% de PampaGrow, y el motivo se ve en las dos filas
extremas. `07-devops` cita `§1` y `§5.1` y ahorra **64%**. El orquestador cita las nueve
secciones y ahorra **0%** — cargar "todo por puntero" es cargar todo. `03-agente-backend`
cita seis secciones de nivel 2 y solo ahorra 16%.

**El ahorro no lo da el mecanismo: lo da podar qué cita cada agente.** El mecanismo es la
condición para poder podar. Las dos palancas concretas:

1. **Bajar de nivel 2 a nivel 3.** `03` cita `§5` entero (6.896 B) cuando probablemente
   necesita `§5.2`, `§5.3` y `§5.6`. `04` cita `§5` entero y `§4` entero.
2. **El orquestador no debería cargar `§9`** (6.337 B, el changelog) en cada invocación: es
   historia, se consulta, no se precarga. Lo mismo `§6` si la tarea no es de datos.

También conviene mirar `03-agente-backend.md`: con **27.882 B** es más del doble que la
mediana de los otros siete, y su propio archivo pesa más que la mitad del SSOT.

---

## 7 · Ramas y commits

| Repo | Rama | Commit | Qué |
|---|---|---|---|
| fitogenix-agents | `decisiones/tier-gratuito-nova-fuera-catalogo` | `8ddcee0` | Convención de citas al código |
| | | `e9ce408` | Las tres decisiones, en documentación |
| | | `3196c79` | La suite corrida: 410 en verde |
| | | `150a8e8` | Corrección del puntero de fuera-de-catálogo |
| fitogenix-native | `decisiones/anonimo-y-fuera-de-catalogo` | `01c6b0c` | El código de B-15 y B-16 + 14 tests |
| fitogenix-server | `tooling/score-histogram` | `415577c` | `scripts/score-histogram.ts` |

Cada commit verificado con `git log -1`. **Ninguna rama pusheada** — quedan locales a la
espera de revisión.

`PODA_REPORTE.md` y `REALINEACION_REPORTE.md` no se tocaron.

---

## 8 · Verificaciones

| # | Chequeo | Resultado |
|---|---|---|
| 1 | Punteros de archivo en los 8 agentes + `CONTEXT.md` | **236 resueltos, 0 rotos.** Las 2 excepciones son deliberadas: `02-agente-frontend.md` cita `scoring.ts` para decir que **no** existe |
| 2 | Punteros `§X` | **0 rotos.** §1–§9 presentes, ninguna sección renumerada |
| 3 | Rastro de cuota | Cada coincidencia es la decisión nueva, el futuro marcado no-MVP, el punto de extensión, o registro histórico. **Cero pendientes de implementación** |
| 4 | Una sola decisión | `grep "va con cuota"` en `CONTEXT.md`: **0**. La historia está en `BITACORA_DECISIONES.md` ADR-003 |
| 5 | Consistencia entre agentes | Los 8 dicen lo mismo sobre las tres decisiones |
| 6 | Estados | 0 🔴 sin puntero a §8 · 0 🟡 escritos en presente · los ✅ citan archivo |
| 7 | Tests | Server **410/410** ✅ · Native **14/14** ✅ · `tsc` limpio en los dos |
| 8 | El código nuevo tiene tests | **Parcial** ⚠️ — la migración anónimo→logueado sí; las guardas de persistencia y el borrado en `SIGNED_OUT` no (falta `@testing-library/react-native`) |

---

## 9 · C-14 — qué es

Aparecía citado como *"no visto por la auditoría"* y sin identificar.

**C-14 = B-13: el copy in-app de `HelpScreen.tsx` que le miente al usuario.** Está
documentado en `CONTEXT.md §1.6` y `§8` B-13, y citado por `01-agente-ux.md` y
`02-agente-frontend.md`. La frase que lo hacía parecer un cabo suelto sale de
`REALINEACION_REPORTE.md`: *"No vio dos cosas: C-07 y C-14"* — **la auditoría** del 28/8 no
los vio; la sesión de realineación del mismo día sí. **No hay nada pendiente de identificar.**

---

## 10 · Lo que queda abierto

**Sin tocar, como corresponde:** C-08 / B-4 (composición del score), C-11 / B-2 (puntaje sin
cobertura), B-8 (`REDIS_KEY_PREFIX` por `ENGINE_VERSION`), B-9 (Dockerfile / `engines.node`),
B-12 (dueño de la nutrición), y la auditoría de los datos ya cargados en `products`.

**Nuevo, y esperando a UX:** las tres piezas de copy de `01-agente-ux.md` — fuera de
catálogo, estado vacío del historial anónimo, y los dos FAQs de `HelpScreen.tsx`.

**Nuevo, y esperando decisión:**

1. **`scan_failed` no existe.** Es la métrica que dice cuánto le falta al catálogo medido con
   usuarios reales — probablemente el dato más valioso del MVP. Quedaron TODOs en los cuatro
   call sites en vez de inventar el módulo `src/analytics/`, que `02-agente-frontend.md` ya
   tiene contratado.
2. **`@testing-library/react-native`**, o el cliente se queda sin poder testear su UI.
3. **`REVISION_diff_rescate.md`** quedó en `Desktop/Fitogenix project/` para revisión. Se
   puede borrar.

**Del entorno agéntico (Fases 2–6):** sin empezar. La Fase 1 era la precondición — construir
la orquestación sobre documentación que todavía decía "va con cuota" habría horneado el error
adentro. La medición de §6 es el insumo de la Fase 5, y ya dice que el trabajo grande no es
el cargador sino podar qué cita cada agente.
