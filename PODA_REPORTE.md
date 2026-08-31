# Poda de agentes a punteros de CONTEXT.md — Reporte

> Fecha: 2026-08-28 · Alcance: `01-agente-ux.md`, `03-agente-backend.md`, `04-agente-qa.md`,
> `05-agente-datos.md`, `06-agente-etl-data.md`, `07-agente-devops.md`. **No se tocaron**
> `00-orquestador.md` ni `02-agente-frontend.md` (van aparte, por instrucción explícita).
>
> Verificado contra: `~/fitogenix-server` `main` `a0428bd` (el mismo commit contra el que se
> verificó `CONTEXT.md`) y `~/fitogenix-native` `main` `b7715b8`. `CONTEXT.md` no se editó —
> es de escritura exclusiva del Orquestador; todo lo que le falta queda en la lista (a) más
> abajo, como propuesta, sin aplicar.

## Cómo leer este reporte

Cada agente tiene una tabla con una fila por referencia relevante (bloque de negocio, stack,
bandas, flujo, archivo citado, umbral, endpoint), clasificada en una de cuatro:

- **(a) Falta en el SSOT** — negocio vigente, `CONTEXT.md` no lo cubre. Se dejó en el agente,
  sin tocar `CONTEXT.md`. Es propuesta para el Orquestador.
- **(b) Es del rol** — detalle operativo exclusivo de este agente (o compartido solo con un
  agente fuera de alcance, como Frontend). No se movió.
- **(c) Ya no aplica** — retirado, renombrado o muerto. Se corrigió o se redefinió, con qué
  se verificó.
- **(d) Contradice al SSOT** — el agente dice una cosa, `CONTEXT.md` otra, sin poder
  verificar directo contra el código cuál tiene razón. **No quedó ninguna abierta en esta
  poda**: todo lo que parecía (d) se pudo verificar contra el repo y cayó en (c) — ver el
  detalle en cada tabla y la lista consolidada al final.

---

## 01-agente-ux.md

| Referencia | Caso | Acción tomada | Verificado contra |
|---|---|---|---|
| Bloque `## El producto: Fitogenix` (qué es, usuario, promesa) | duplicado con SSOT | Podado a puntero `CONTEXT.md §1`, `§2` | `CONTEXT.md §1.1-§1.3`, `§2` |
| "React Native + Expo, misma base iOS/Android" (stack) | duplicado con SSOT | Podado a puntero `CONTEXT.md §5.1`, `§5.2` | `CONTEXT.md §5.1` |
| Expo Router, RN StyleSheet, expo-camera, expo-blur, lucide-react-native, ScoreDial+react-native-svg, latencia IA "2-8s" | (a) falta en el SSOT — es contexto de negocio/producto que necesitaría también Frontend (fuera de alcance), y `CONTEXT.md` explícitamente no baja a nivel de librería | Se queda en el agente, sin tocar `CONTEXT.md` | — |
| Tabla "Pantallas actuales y su estado real" (7 pantallas, estado + problemas conocidos) | (a) falta en el SSOT — estado de producto que necesitarían también Frontend y QA | Se queda en el agente | — |
| "Features no implementadas" ítems 1-4, 6-7 (login social, recuperar contraseña, historial real, foto de etiqueta, editar perfil, notificaciones) | (b) rol — inventario de trabajo específico de UX | Sin cambios | — |
| "Features no implementadas" ítem 5: campo `alternatives` = "productos alternativos más saludables" | (c) ya no aplica — el campo real es texto de ambigüedad por ingrediente ("aceite de girasol o soja"), no una recomendación de producto | Corregido: se tachó la feature, se explicó qué es `alternatives` de verdad | `fitogenix-server/src/domain/product/scoring/types.ts:184` (`readonly alternatives?: readonly string[]`), `cleaning.ts` (`alternativesOf`), `classify.ts` |
| "Contexto de la migración: el proyecto está en proceso de separar el backend" | (c) ya no aplica — la separación (Fase 1) ya terminó | Corregido a "ya se separó", con puntero a `CONTEXT.md §5.1`/`§5.2` | `fitogenix-native`: no existen `src/infrastructure/` ni `src/app/api/`; `ftgEngine.ts` es shim DEPRECATED que reexporta `src/lib/contracts/product.ts` |
| Oportunidad de UX "cache de resultados recientes" vía React Query | (b) rol — propuesta de UX todavía no implementada, no una afirmación de estado actual | Sin cambios (se agregó nota "todavía no instalado") | `fitogenix-native/package.json`: sin `react-query`/`@tanstack/*` |
| Oportunidad de UX "notificaciones push" | (b) rol — propuesta abierta | Sin cambios | — |
| Paywall: "10 análisis/mes en el plan Free" | (a)/consistente — `CONTEXT.md §4.2` declara la cuota mensual sin transcribir el número, y remite explícitamente a `00-orquestador.md`/`03-agente-backend.md` como dueños de la cifra. No es una omisión de `CONTEXT.md`, es su diseño declarado | Sin cambios | `CONTEXT.md §4.2` |
| Accesibilidad (WCAG AA, no-solo-color, 44pt, Dynamic Type, TEA) | (b) rol — checklist exclusivo de UX/QA, `CONTEXT.md` solo dice que la accesibilidad es requisito, no el detalle | Sin cambios | — |

**Tamaño:** 11.904 B → 11.932 B (+28 B, +0,2%).

---

## 03-agente-backend.md

| Referencia | Caso | Acción tomada | Verificado contra |
|---|---|---|---|
| Bloque `## El producto: Fitogenix` con flujo de 6 pasos ("busca en OFF... llama a Claude") | duplicado con SSOT **y** (c) ya no aplica — el flujo de 6 pasos es la cascada retirada (C-07) | Podado a puntero `CONTEXT.md §1`, `§2`, `§4`, `§5` | `productLookupService.ts` (docstring: "decisión de producto, 2026-08-18... catalog-only") |
| Párrafo "Score Fitogenix: las bandas son ≥75.../ no hay banda Peligroso" | duplicado con SSOT (aunque, a diferencia de lo que reporta `AUDITORIA_SETUP_AGENTICO.md` C-01, esta copia YA tenía los números correctos: 75/50/25/0, sin "Peligroso") | Podado a puntero `CONTEXT.md §3` | `scoring/constants.ts` `TIERS` = 75/50/25/0 (4 bandas + `NO_DATA_TIER`) — coincide |
| Sección "Cascada de fuentes de datos crudos" completa (OFF→OBF→Edamam→Claude como camino de request) | (c) ya no aplica — C-07 | Redefinida: los 4 servicios existen y los mantiene Backend, pero hoy los invoca el ETL en batch, no el request | `productLookupService.ts` (imports: no importa `claudeService`; docstring explícito) |
| "`enrichWithAI`/`aiLookupProduct` se llaman en el punto correcto de la cascada de `productLookupService.ts`" | (c) ya no aplica — ninguna de las dos funciones se llama desde ahí | Corregido: ahora se llaman desde `scripts/etl/jobs/runMerge.ts` y `scripts/etl/lib/qualityAI.ts` | `grep -rl "enrichWithAI\|aiLookupProduct" src/ scripts/` → solo `claudeService.ts` (definición), `nutrientPlausibility.ts`, `scripts/etl/lib/qualityAI.ts`, `scripts/etl/jobs/runMerge.ts` |
| Diagrama "Cache en niveles" (rama barcode con `OFF → OBF → Edamam → Claude (2-8s)`) | (c) ya no aplica — C-07 | Redibujado contra el código real: `lookupProduct`/`resolveByBarcode`/`resolveByName`, miss = `null` en ambas ramas | `productLookupService.ts` líneas ~144-241 (`resolveByBarcode`, `resolveByName`, `lookupProduct`) |
| "`mapOFFToProduct(raw)`" (regla de oro de `products`, y en el diagrama de cache) | (c) ya no aplica — renombrada | Corregido a `mapRawToProduct` en ambos lugares | `git log`: `"docs: actualizar README del ETL (mapOFFToProduct -> mapRawToProduct)"`; función real: `productLookupService.ts:94 export function mapRawToProduct(...)` |
| Árbol de archivos: `productLookupService.ts ← orquestador: Redis→Supabase→catálogo→OFF/OBF/Edamam→Claude` | (c) ya no aplica — C-07 | Corregido a "Redis→Supabase (catalog-only, ver §5.3)" | igual que arriba |
| Caso de test: "Score de un producto NOVA 4 → debe penalizar el componente de procesamiento" | (c) ya no aplica — el motor v2.1 no lee `nova_group` para el modificador de procesamiento, usa marcadores de texto de ultraprocesado. Nota: el rol de NOVA como vocabulario del producto sigue **abierto** en `CONTEXT.md §8` B-4 (C-09) — eso no lo resuelve esta poda, solo el hecho técnico de qué input usa el motor hoy | Corregido a "marcadores de ultraprocesado en el texto" + nota 🔴 C-09 con puntero | `scoring/steps.ts` (usa `PROCESSING`, `markerCount`; cero referencias a `nova_group`), `scoring/constants.ts` `PROCESSING` |
| Bloque "Dependencias del servidor" (JSON completo de `package.json`) | duplicado con SSOT — `CONTEXT.md §5.1` señala explícitamente esta transcripción como la que "se poda en el paso siguiente" | Podado a puntero a `fitogenix-server/package.json` | `CONTEXT.md §5.1`; versiones confirmadas iguales al `package.json` real antes de podar |
| Schema completo de `products` (columnas, tipos) | (b) rol — detalle de implementación exclusivo de Backend; `CONTEXT.md §5.5` cubre el principio de identidad, no el DDL completo | Sin cambios | Columnas verificadas contra las migraciones `001`-`008` (existen) |
| Bugs históricos (Bug 1/2/3, Fase 0) | (b) rol — bitácora técnica de Backend | Sin cambios | — |
| Endpoints (`POST /products/lookup`, `DELETE /users/me`, etc.) | (b) rol — `CONTEXT.md §5.6` remite explícitamente a este archivo como dueño del contrato | Sin cambios | `find src/routes` → coincide exactamente: `lookup.ts`, `image.ts`, `deleteMe.ts`, `saved.ts`, `history.ts` |
| Redis TTL (604800/259200/2592000 s) y `REDIS_KEY_PREFIX` estático | (b) rol / consistente — `CONTEXT.md §5.4` dice explícitamente "no se transcriben acá", cita el código como fuente. No es un hueco, es diseño de `CONTEXT.md` | Sin cambios | `redisService.ts` — TTLs y prefijo coinciden exactamente |
| Selección de modelo Haiku vs Sonnet Vision (regla completa) | (a) falta en el SSOT — la usan Backend, Datos y ETL (3 agentes), y hoy vive completa solo acá | Se queda en el agente, sin tocar `CONTEXT.md` | — |
| Lógica de Cuotas Freemium (esquema propuesto, RPC, RLS) | (a)/consistente — `CONTEXT.md §4.2` remite explícitamente a este archivo como dueño de "cifras y esquema propuesto" | Sin cambios | `CONTEXT.md §4.2` |
| Bug 2 / excepción de auth en `/products/lookup` | consistente con SSOT — este es el mismo hecho que sostiene el 🔴 C-02 de `CONTEXT.md §4.3`/`§8` B-1 (bloqueante abierto, decisión de Jere) | Sin cambios — la contradicción C-02 es entre este archivo y `00-orquestador.md` (fuera de alcance), no algo que este agente deba resolver | `src/routes/products/lookup.ts` — confirma que no registra `requireAuth` |

**Tamaño:** 26.225 B → 26.389 B (+164 B, +0,6%). El bloque removido (~1,4 KB de flujo/bandas/JSON de deps) quedó compensado y superado por las correcciones C-07/C-09/rename, que son contenido nuevo y necesario, no duplicación — este es el archivo con más hallazgos (c) de los seis.

---

## 04-agente-qa.md

| Referencia | Caso | Acción tomada | Verificado contra |
|---|---|---|---|
| Párrafo `## El producto: Fitogenix` (stack completo + freemium) | duplicado con SSOT | Podado a puntero `CONTEXT.md §1`, `§4`, `§5` | — |
| "gates, NOVA 4, ingredientes prohibidos, umbrales de tier" (ejemplo de edge cases a testear) | (c) matiz — no es una afirmación de arquitectura tan fuerte como la de Backend, pero sigue nombrando "NOVA 4" como si fuera un input real del motor | Se agregó aclaración "no `nova_group`: el motor v2.1 no lo usa" + puntero a C-09 | `scoring/steps.ts` (sin `nova_group`) |
| Protocolo de auditoría (TDD, manejo de errores, a11y, TEA) | (b) rol — es el contenido central del agente | Sin cambios | — |
| Formato de veredicto estructurado | (b) rol | Sin cambios | — |

**Tamaño:** 5.601 B → 5.487 B (−114 B, −2,0%). El más chico y con menos duplicación real; coincide con el veredicto de la auditoría ("Conservar").

---

## 05-agente-datos.md

| Referencia | Caso | Acción tomada | Verificado contra |
|---|---|---|---|
| Bloque `## El producto: Fitogenix` (Claude completa/construye datos "cuando OFF no alcanza") | duplicado con SSOT **y** matiz C-07 — la frase original sugiere una intervención reactiva en vivo | Podado a puntero `CONTEXT.md §1`, `§2`, `§5` + nota explícita: Claude corre en batch vía ETL, no en el request | `CONTEXT.md §5.3` |
| "`mapOFFToProduct(raw)`" (sección de invalidación por `ENGINE_VERSION`) | (c) ya no aplica — renombrada | Corregido a `mapRawToProduct` | igual que en 03/06 — `git log`, `productLookupService.ts:94` |
| TTLs de Redis (7d/3d/30d) y propuesta de versionar `REDIS_KEY_PREFIX` por `ENGINE_VERSION` | (b) rol / consistente con `CONTEXT.md §8` B-8 (bloqueante abierto: "no está aplicada") | Sin cambios | `redisService.ts` — prefijo sigue estático, coincide con B-8 |
| Presupuesto de tokens, pricing de Haiku ($1/$5 por millón) | (b) rol — cifras de referencia exclusivas de este agente, `CONTEXT.md` no transcribe pricing por diseño | Sin cambios | — |
| Regla Haiku (texto) vs Sonnet Vision (imagen) | ver fila equivalente en 03-agente-backend.md — (a) compartida por 3 agentes, no en el SSOT | Sin cambios, ya referencia a `03-agente-backend.md` como dueño de la regla | — |

**Tamaño:** 9.830 B → 9.931 B (+101 B, +1,0%).

---

## 06-agente-etl-data.md

| Referencia | Caso | Acción tomada | Verificado contra |
|---|---|---|---|
| Bloque `## El producto: Fitogenix` (regla de oro del catálogo, identidad de fila) | duplicado con SSOT | Podado a puntero `CONTEXT.md §1`, `§2`, `§5.4`, `§5.5` | — |
| "reusar `RawOFFProduct`, `buildCachePayload`, `mapOFFToProduct`, `enrichWithAI`, `ftgEngine`" | (c) ya no aplica — renombrada | Corregido a `mapRawToProduct` | igual que 03/05 |
| "Por qué existe este agente": usuario paga "el costo completo de la cascada en frío (OFF→OBF→Edamam→Claude, 2-8s)" en su primera búsqueda | (c) ya no aplica — C-07. Además la corrección **fortalece** el argumento del agente: hoy no hay cascada lenta de respaldo, hay `null` directo | Corregido: sin catálogo, la búsqueda no devuelve nada (`null`/404), sin fallback online | `productLookupService.ts` docstring |
| Pipeline `products_staging` (adapters, merge campo a campo, gate de completitud, `run_id`/`merged_into`) | (b) rol — `CONTEXT.md §6.2` remite explícitamente a este archivo ("detalle del diseño en `06-agente-etl-data.md`, el documento mejor calificado de la auditoría") | Sin cambios | `migrations/009_products_staging.sql` existe |
| Scripts npm citados (`etl:off`, `etl:vtex`, `etl:merge`, `etl:stats`) | (b) rol, consistente | Sin cambios | `package.json` scripts — los 4 existen tal cual |
| Archivos de `scripts/etl/` citados (adapters, jobs, lib) | (b) rol | Sin cambios | `find scripts/etl` — todos existen |
| "Fuera de tu alcance: pipeline de imágenes" | (b) rol, consistente con `03-agente-backend.md` ("fuera de alcance esta etapa" en `image.ts`/`imageService.ts`) | Sin cambios | — |

**Tamaño:** 19.372 B → 19.204 B (−168 B, −0,9%).

---

## 07-agente-devops.md

| Referencia | Caso | Acción tomada | Verificado contra |
|---|---|---|---|
| Bloque `## El producto: Fitogenix` (stack + "sin Dockerfile todavía") | duplicado con SSOT | Podado a puntero `CONTEXT.md §1`, `§5.1` | — |
| "No existe Dockerfile/railway.toml/render.yaml", "sin `engines.node`" | (b) rol, consistente con `CONTEXT.md §8` B-9 | Sin cambios | Confirmado: sin `Dockerfile`/`railway.toml`/`render.yaml`; `grep engines package.json` → sin match |
| Rate limit `60 req/min` en memoria, riesgo de escalado horizontal (N instancias) | (b) rol | Sin cambios | `main.ts`: `rateLimit, { max: 60 }`, en memoria (sin `store` de Redis) |
| Variables de entorno requeridas/opcionales | (b) rol | Sin cambios | `src/config.ts` — coincide exactamente (`required`: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SERPAPI_API_KEY`; `optional`: el resto) |
| Auditoría de secretos, `.gitignore` | (b) rol | Sin cambios | — |

**Tamaño:** 9.276 B → 9.147 B (−129 B, −1,4%).

---

## Verificación (las cuatro)

**1. Punteros de archivo — cero rotos.** Se extrajeron por regex todas las rutas citadas
entre backticks en los 6 archivos (43 rutas únicas) y se verificó su existencia contra
`~/fitogenix-server` y `~/fitogenix-native` con `find`/test de archivo. Las rutas
agregadas en esta poda (`scripts/etl/jobs/runMerge.ts`, `scripts/etl/lib/qualityAI.ts`,
`scoring/types.ts`) también se verificaron. **0 rotas.**

**2. Punteros de sección — cero rotos.** Se extrajeron todas las citas `§X`/`§X.Y`
introducidas (`§1, §2, §2.4, §3, §4, §5, §5.1, §5.2, §5.3, §5.4, §5.5, §8`) y se
confirmó que las 12 existen en `CONTEXT.md` (que llega hasta `§9`). **0 rotas.**

**3. Cero duplicación.** Grep de bandas transcritas (`≥75`, `50–74`, `25–49`, `0–24`,
`≥85`, etc.) tras la poda: **una sola coincidencia**, en `03-agente-backend.md`, y es un
ejemplo de test ("banda Excelente ≥75, ver `scoring/constants.ts`") que cita el archivo,
no re-declara la tabla — no es la duplicación que se pedía eliminar. Grep de la cascada
vieja (`OFF/OBF`, `cascada`) tras la poda: todas las coincidencias restantes están dentro
de las notas 🔴→corregido o de descripciones de servicios que siguen existiendo (ETL), no
de un camino de request. Grep de `mapOFFToProduct`: 0 coincidencias en los 6 archivos.

**4. Reducción medida.**

| Archivo | Antes (B) | Después (B) | Δ |
|---|---|---|---|
| 01-agente-ux.md | 11.904 | 11.932 | +28 (+0,2%) |
| 03-agente-backend.md | 26.225 | 26.389 | +164 (+0,6%) |
| 04-agente-qa.md | 5.601 | 5.487 | −114 (−2,0%) |
| 05-agente-datos.md | 9.830 | 9.931 | +101 (+1,0%) |
| 06-agente-etl-data.md | 19.372 | 19.204 | −168 (−0,9%) |
| 07-agente-devops.md | 9.276 | 9.147 | −129 (−1,4%) |
| **Total** | **82.208** | **82.090** | **−118 (−0,1%)** |

Tres notas sobre este número, dichas sin adornarlas:

- **La estimación de partida del pedido ("~64 KB") no coincide con lo medido.** El total
  real de los 6 archivos, medido antes de tocar nada, era ~82,2 KB (80,3 KiB), no 64 KB —
  una diferencia de ~22%. No se investigó de dónde salió el 64, se reporta el número real.
- **La reducción neta es casi nula (−0,1%), y tres archivos crecieron.** Lo que se sacó
  (bloque "El producto", bandas transcritas, JSON de dependencias — ~2,3 KB en total) se
  compensó y en algunos archivos se superó con contenido nuevo y necesario: las
  correcciones C-07 (cascada retirada, la más pesada — solo en `03` son ~5 párrafos
  nuevos), el rename `mapOFFToProduct→mapRawToProduct` en tres archivos, y la nota C-09 en
  `03`/`04`. Esto no es duplicación remanente — es la clase de contenido que un agente SÍ
  necesita para no seguir mintiendo sobre el código. `03-agente-backend.md`, que tenía la
  mayor duplicación de origen, es también el que más creció neto (+164 B): tenía la mayor
  cantidad de hallazgos (c) que exigían explicación, no solo poda.
- **Ningún archivo quedó por debajo de la mitad de su tamaño original** (el que más bajó,
  `04-agente-qa.md`, un 2,0%) — no aplica la sospecha de poda excesiva que pide el pedido.
  Si la expectativa era una reducción de bulto notable, esta poda no la entrega: el
  problema real que encontró (duplicación de bloques de negocio) pesaba menos en KB que
  la deriva doc↔código que apareció al verificar contra el repo, y corregir la deriva
  costó más bytes de los que ahorró la poda.

---

## (a) Lo que le falta a CONTEXT.md — propuesta, sin aplicar

Test de suficiencia del SSOT, medido contra esta poda. Ninguno de estos ítems se escribió
en `CONTEXT.md` — es de escritura exclusiva del Orquestador.

1. **Selección de modelo Haiku (texto) vs Sonnet Vision (imagen).** La regla completa vive
   en `03-agente-backend.md` ("Selección de Modelo") y la aplican tres agentes: Backend
   (implementa los call sites), Datos (la hace cumplir y tunea prompts) y ETL (la usa en
   batch vía `enrichWithAI`/`aiLookupProduct`). Es el caso más claro de "dos-o-más agentes
   la necesitan" que hoy no tiene un único dueño en el SSOT.
2. **Estado real de las pantallas de la app y features no implementadas** (tabla completa
   en `01-agente-ux.md`: Home, Scan, Resultado, Guía, Comunidad, Perfil, Welcome/Sign-up +
   7 features pendientes). Lo necesitarían también Frontend (fuera de alcance de esta
   poda) y QA para saber qué auditar.
3. **Stack de librerías del cliente y restricciones de UX** (Expo Router, expo-camera,
   expo-blur, lucide-react-native, sin animaciones complejas salvo `ScoreDial` con
   `react-native-svg`, latencia real de un análisis IA ~2-8s). `CONTEXT.md §5.1`/`§5.2`
   cubre la arquitectura general del cliente pero deliberadamente no baja a este nivel; UX
   y Frontend (fuera de alcance) lo necesitan igual.

No se proponen más ítems: el resto de las referencias "compartidas" (TTLs de Redis,
pricing de Claude, cuotas freemium, contrato de API) ya tienen dueño explícito señalado
por el propio `CONTEXT.md` (§4.2, §5.4, §5.6) — no son huecos, son diseño.

## (c) Lo que se borró o corrigió por obsoleto

Cada uno con el archivo/commit contra el que se verificó (detalle completo en las tablas
por agente, arriba):

1. **La cascada `OFF → OBF → Edamam → Claude` como camino de request (C-07)** — descrita
   como vigente en `03-agente-backend.md` (bloque "El producto", sección de cascada
   completa, diagrama de cache, árbol de archivos, callsite de `enrichWithAI`) y en
   `06-agente-etl-data.md` ("Por qué existe este agente"). Verificado contra el docstring
   y el código de `productLookupService.ts`: el request es catalog-only desde el
   2026-08-18, esos 4 servicios ahora los invoca el ETL en batch.
2. **`mapOFFToProduct` → `mapRawToProduct`** — la función fue renombrada en el mismo
   commit (`a0428bd`, mensaje: "docs: actualizar README del ETL"). Corregido en
   `03-agente-backend.md` (2 lugares), `05-agente-datos.md` (1 lugar) y
   `06-agente-etl-data.md` (1 lugar).
3. **El caso de test "NOVA 4 → penaliza el componente de procesamiento" (C-09, parcial)**
   en `03-agente-backend.md` — el motor v2.1 no lee `nova_group` para el modificador de
   procesamiento (usa marcadores de texto de ultraprocesado, `PROCESSING` en
   `constants.ts`/`steps.ts`). Se corrigió el hecho técnico puntual; el rol de NOVA como
   vocabulario del producto en general sigue abierto en `CONTEXT.md §8` B-4 — eso no lo
   resuelve esta poda.
4. **El campo `alternatives` como "productos alternativos más saludables" (`01-agente-ux.md`)**
   — no existe ese campo. `alternatives` en el modelo real es texto de ambigüedad por
   ingrediente ("aceite de girasol o soja"), verificado contra `scoring/types.ts:184` y
   `scoring/cleaning.ts`. Se descartó la feature propuesta sobre esa base incorrecta.
5. **"El proyecto está en proceso de separar el backend de la app Expo" (`01-agente-ux.md`)**
   — la separación (Fase 1) ya terminó. Verificado: `fitogenix-native` no tiene
   `src/infrastructure/` ni `src/app/api/`, y `ftgEngine.ts` es un shim DEPRECATED.

## (d) Contradicciones abiertas

**Ninguna.** Todo lo que en un primer paso parecía un conflicto agente-vs-`CONTEXT.md` se
pudo verificar directo contra el código en esta sesión (mismo commit `a0428bd` que usó
`CONTEXT.md`) y resultó ser (c) — un hecho verificable, no una decisión de producto
pendiente. Las contradicciones de producto genuinamente abiertas (C-02 lookup público vs
cuotas, C-08 composición del score, C-09 rol de NOVA en general, C-11 puntaje sin
cobertura) ya están correctamente escaladas en `CONTEXT.md §8` y no se duplicaron acá.
