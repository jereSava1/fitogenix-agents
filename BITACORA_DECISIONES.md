# Bitácora de Decisiones — Fitogenix

Registro de decisiones de arquitectura del proyecto, en formato **ADR** (Architecture Decision Record). Cada decisión relevante —de arquitectura, de stack, de modelo de negocio con impacto técnico, o de reversión tras un fallo— se registra acá.

Un ADR es inmutable una vez aceptado: no se edita, se **supersede** con uno nuevo que lo referencie. Así queda el rastro de por qué el sistema es como es.

**Cuándo registrar un ADR:** al elegir entre alternativas técnicas con consecuencias a largo plazo (framework, base de datos, límite de un servicio), al cambiar una decisión previa, o al revertir una tarea fallida tras 2 iteraciones (Protocolo de Reversión del Orquestador).

---

## Plantilla ADR

Copiar este bloque para cada decisión nueva. Numeración incremental (`ADR-002`, `ADR-003`, ...).

```markdown
## ADR-NNN: [Título corto y descriptivo de la decisión]

- **Fecha:** AAAA-MM-DD
- **Estado:** Propuesto | Aceptado | Rechazado | Supersedido por ADR-XXX
- **Decididores:** [agentes / roles involucrados]

### Contexto
Cuál es el problema o la fuerza que motiva esta decisión. Las restricciones
relevantes (técnicas, de negocio, de tiempo). Qué es verdad hoy que obliga a decidir.

### Decisión
Qué se decidió hacer, en una afirmación clara y directa. "Vamos a X."

### Alternativas consideradas
- **Opción A:** descripción · por qué se descartó.
- **Opción B:** descripción · por qué se descartó.

### Consecuencias
- **Positivas:** qué mejora, qué habilita.
- **Negativas / costos:** qué se paga, qué se vuelve más difícil, qué deuda se asume.
- **Neutras / seguimiento:** qué hay que vigilar, qué queda pendiente de revisar.
```

---

## ADR-001: Separar el Backend de Expo a un servidor Node.js + Fastify

- **Fecha:** 2026-07-01
- **Estado:** Aceptado
- **Decididores:** Orquestador (Tech Lead), Agente Backend

### Contexto
La primera versión de Fitogenix corría toda la lógica dentro de la app Expo, usando las rutas API de Expo Router (`+api.ts`) como "backend". Ese modelo tenía problemas estructurales serios:

- Las rutas `+api.ts` corren en el runtime de Expo Router, una caja negra sin control de infraestructura: no se puede agregar Redis, ni rate limiting real, ni observabilidad propia, ni escalar el backend independientemente del cliente.
- Endpoints sensibles quedaban expuestos sin autenticación (`/api/analyze` proxy a Anthropic, `/api/cache-product` con service role de Supabase), permitiendo quemar API keys o envenenar el caché.
- La lógica de negocio (motor de scoring, orquestación de OFF/Claude) vivía duplicada o mezclada con la UI, con riesgo de divergencia entre lo que calcula el cliente y lo que debería ser autoritativo.
- El proyecto apunta a decenas de miles de usuarios mensuales y a un modelo Freemium con cuotas server-side: nada de eso es viable sin un backend propio y controlable.

### Decisión
Separar el backend a un proyecto independiente **`fitogenix-server`**, construido con **Node.js + Fastify + TypeScript**, desplegable por su cuenta. La app Expo queda como cliente puro (UI + llamadas al backend propio con JWT). Toda la lógica de negocio, las integraciones con servicios externos (Open Food Facts, Anthropic, SerpAPI, remove.bg) y el acceso a Supabase con service role viven exclusivamente en el servidor.

### Alternativas consideradas
- **Seguir con las rutas `+api.ts` de Expo Router, agregándoles auth:** descartada. Resuelve la autenticación pero no el problema de fondo — seguís sin control de infraestructura, sin Redis, sin poder escalar el backend aparte, y sin observabilidad. Es maquillaje sobre una arquitectura que no da para el objetivo de escala.
- **Backend serverless (funciones lambda):** descartada para esta etapa. La orquestación del pipeline (caché → OFF → Claude → imágenes) con estado de caché caliente (Redis) y deduplicación in-flight se modela mejor en un servicio persistente. Serverless agregaría complejidad de cold starts y de estado compartido sin beneficio claro a esta escala.
- **Framework Express en vez de Fastify:** descartada. Fastify ofrece mejor rendimiento, validación de esquemas nativa y un sistema de plugins más limpio, sin costo de adopción relevante para el equipo.

### Consecuencias
- **Positivas:**
  - Control total de la infraestructura: se habilitan Redis (caché caliente), rate limiting, JWT en todos los endpoints, y observabilidad propia.
  - Las API keys y el service role de Supabase quedan estrictamente server-side; el cliente nunca los ve.
  - Una única fuente de verdad para el scoring y las reglas de negocio (el servidor), eliminando la divergencia cliente/servidor.
  - Se habilita el modelo Freemium: la lógica de cuotas y el descuento de créditos pueden vivir transaccionalmente en el backend.
  - Backend y cliente escalan y se despliegan por separado.
- **Negativas / costos:**
  - Dos repos que mantener y coordinar, con un contrato de API entre ellos.
  - El motor de scoring (`ftgEngine.ts`) y sus tipos se comparten conceptualmente entre repos; hay que mantenerlos en sync (por ahora, copia + tipos en el cliente; a futuro, evaluar paquete compartido).
  - Costo de infraestructura y de deploy del nuevo servicio (Railway/Render + Upstash).
- **Neutras / seguimiento:**
  - Migración por fases para no romper lo que funciona: crear el backend, migrar el cliente, agregar Redis/auth/rate-limit, y features de negocio.
  - Revisar a futuro si conviene extraer el dominio compartido (`ftgEngine`) a un paquete npm privado para eliminar la duplicación de código entre repos.

---

## ADR-002: Reescribir el motor de puntuación como función pura de la lista de ingredientes (v2.1)

- **Fecha:** 2026-08-15
- **Estado:** Aceptado
- **Decididores:** Jere (producto), Agente Backend

### Contexto

El motor v2 (`ftg-rubric-v2`) calculaba el puntaje con una base compuesta de 71, penalizaciones acumuladas con retornos decrecientes (factor 0,75), un modificador NOVA, un modificador nutricional y una regresión a neutro proporcional a la cobertura. Funcionaba, pero tenía tres problemas que el testeo con catálogo real hizo evidentes:

1. **No era reconstruible.** Ningún usuario —ni nosotros— podía seguir la cuenta. Un producto daba 46 y la única forma de saber por qué era leer el código. El decaimiento exponencial y la regresión por cobertura son operaciones que no se explican en una pantalla de celular.
2. **Lo desconocido era neutro.** Un ingrediente que no reconocíamos no restaba, así que la opacidad del fabricante no tenía costo. La regresión por cobertura mitigaba el síntoma sin atacar la causa.
3. **Demasiadas perillas.** 20 coeficientes, 6 techos y 5 niveles de impacto: cada uno era una oportunidad de fallar y ninguno se podía calibrar por separado.

El documento de producto `fitogenix_scoring_engine_v2_1.md` responde a esto con un sistema deliberadamente más chico: **6 coeficientes, 3 niveles de impacto, 1 mecanismo de techo, 6 anulaciones**, y una tabla de ingredientes que puede crecer sin agregar complejidad al motor. Su principio de diseño: *"pocas reglas, muchos ingredientes"*.

### Decisión

Reemplazamos el motor in situ por el pipeline de v2.1:

```
§1 fuera de alcance / sin datos  →  no se emite puntaje (score: null)
§6 limpiar la lista              →  alérgenos, certificaciones, y/o, paréntesis
§5 anulaciones                   →  20 − 6×n (−4 si va a niños)
§2 Paso 1  base 75  |  ancla §3  →  el ancla es terminal
§2 Paso 2  restas por impacto y posición
§2 Paso 3  modificador de procesamiento por marcadores
     ·     modificador nutricional (decisión de producto, ver abajo)
§2 Paso 4  techos 74 / 59 / 49, vale el más bajo
§2 Paso 5  clamp 0-100
```

El puntaje pasa a ser una función pura de la lista de ingredientes limpia. Desaparecen NOVA como insumo del cálculo, el promedio ponderado de cuatro ejes y la regresión por cobertura.

La salida del motor cambia de forma: `breakdown.components` (los cuatro ejes) se reemplaza por `breakdown.steps[]`, la cuenta paso por paso. **El desglose no es telemetría: es la salida principal**, y hay un test que verifica producto por producto que la suma de los pasos dé el puntaje.

Se agrega `src/domain/product/ingredientCleaning.ts` para todo lo de §6, que antes vivía mezclado con el scoring.

### Alternativas consideradas

- **Motor v2.1 nuevo al lado del v2, detrás de un feature flag:** descartada. Permitiría A/B y rollback, pero duplica ~1.500 líneas de dominio y obliga a mantener dos criterios de producto en paralelo justo cuando el objetivo es tener uno solo y defendible. El rollback real acá es `git revert`.
- **Refactor incremental sección por sección:** descartada. Los pasos de §2 son interdependientes (la posición depende de la limpieza, el techo depende de la clasificación), así que los estados intermedios habrían sido inconsistentes sin ganar nada.
- **Cambiar solo la lógica de cálculo y dejar el payload como estaba:** descartada. Habría preservado la app sin tocarla, pero pierde la regla 1 del documento —el puntaje tiene que ser reconstruible—, que es la razón principal del cambio.
- **Puntaje puramente ingrediente, con los octógonos como dato informativo:** descartada por decisión de producto. Ver abajo.

### Divergencias deliberadas respecto del documento

Tres, todas anotadas en el código con su motivo:

1. **El panel nutricional sigue restando.** §2 de v2.1 no tiene paso nutricional. Se conserva el cruce con los octógonos de la Ley 27.642 y con la grasa trans declarada, porque atrapa lo que la lista sola no ve: un producto de ingredientes correctos con un panel desastroso. Va como **paso propio del desglose**, con su propio número, así no rompe la reconstruibilidad; puede bajar el puntaje pero nunca subirlo, y no puede llevarlo por debajo de 15 (la banda 0-14 queda para las anulaciones de §5 y las anclas de fondo).
2. **La regla del 30% de no identificados se aplica desde 2.** Tomada literal ("3 o más, o más del 30% de la lista"), cualquier lista de 3 ingredientes con uno solo sin reconocer caería en "sin datos" —y eso volvería inalcanzables los techos de 74 y 49 que §2 Paso 4 define justamente para 1 y 2 no identificados.
3. **Las anclas no tienen un tope global de 2 ingredientes.** §2 Paso 1 dice "1 o 2 ingredientes", pero la tabla de §3 incluye filas que se describen por composiciones de 3-5 (queso simple, pan de masa madre, pasta seca, conservas al natural). El tope es por fila.

Además, `ingredientData.ts` (271 registros con la prosa por ingrediente) se sigue consultando **después** de la rúbrica y **antes** de declarar algo NO IDENTIFICADO. §4 dice que la tabla de ingredientes "crece sin agregar complejidad" y que "el motor consulta, no clasifica": ese archivo es esa tabla crecida. Sin ese respaldo, media góndola argentina caería en "sin datos" por la regla de los 3 no identificados.

### Consecuencias

- **Positivas:**
  - Cada puntaje viene con su cuenta. Es auditable por el usuario, por soporte y por nosotros, y hace diagnosticable cualquier resultado raro sin abrir el código.
  - La opacidad tiene costo: −8 por término no identificado, más techo, más cola de curaduría (`breakdown.unidentified`) que alimenta el crecimiento de la tabla.
  - El sistema crece por datos, no por reglas: sumar ingredientes a `IMPACT_TABLE` no toca el motor.
  - Casos que antes devolvían un número inventado ahora devuelven `null` con su motivo (§1): fuera de alcance, sin datos, lista no identificable.
  - Los pasos 1-5 son una función pura y determinista, sin dependencia de caché ni de modelo.
- **Negativas / costos:**
  - **Los puntajes de v2 no son comparables.** Hay que recomputar la caché de `products` (`ENGINE_VERSION` pasa a `ftg-rubric-v2.1`).
  - **El payload cambió** (`score: number | null`, `components` → `steps`, se va `subscores`). La app native todavía puntúa con su copia local del motor v1/v2 y hay que migrarla — ver ADR-001, "Neutras / seguimiento".
  - Va a subir la proporción de productos "sin datos suficientes": es más honesto, pero se ve como catálogo incompleto hasta que la curaduría avance.
  - Productos de góndola muy comunes (pan lactal blanco, galletitas dulces) caen a la banda Malo. Es la postura declarada de la marca aplicada con consistencia, no un error de calibración — pero conviene mirarlo con datos reales antes de publicar.
- **Neutras / seguimiento:**
  - `npm run audit:scores` sobre el catálogo real, mirando la distribución por banda (§9: si más del 40% cae en una sola, hay que mover los cortes) y la frecuencia de los NO IDENTIFICADO.
  - Migrar el cliente al scoring del servidor y borrar `fitogenix-native/src/lib/ftgEngine.ts`, en vez de portar v2.1 a una segunda copia.
  - Revisar el ancla de pasta seca (70-80 → 75): el punto medio cae exactamente sobre el corte Bueno/Excelente.

### Nota de implementación (2026-08-18)

El motor descripto arriba se había escrito sobre un clon de `fitogenix-server` en el Desktop, no sobre el repo real (`~/fitogenix-server`) — quedó 10 commits de ETL y todo el WIP del motor sin llegar nunca a `main` ni a GitHub. Se rescató como ramas git (`rescate/etl-desktop-ago9`, `rescate/wip-desktop-completo`) y se mergeó a `main` del repo real (commit `a0560ca`), junto con el refactor a módulos de responsabilidad única (`src/domain/product/scoring/`, `scoring/rubric/`). 416 tests en verde, `tsc` limpio. ~~Pendiente: `git push`~~ → pusheado, ver nota siguiente.

### Nota de implementación (2026-08-18, parte 2) — búsqueda catalog-only + cierre de la migración de contrato

Con el motor ya en `main`, se completó lo que quedaba pendiente de esta ADR y se cerró además un rediseño de búsqueda que surgió en la misma sesión:

- **`fitogenix-native` migrado al contrato v2.1.** Nuevo `src/lib/contracts/product.ts` (sin `breakdown`/`subscores`, `score: number | null`); `ScoreDial` ahora es null-safe y no interactivo. `ScoreBreakdownSheet` se sacó del árbol de render — decisión de producto: el desglose paso-a-paso no aporta valor al usuario final, y mantenerlo sincronizado con cada cambio del motor era costo sin beneficio.
- **`breakdown` se dejó de mandar por la red, en los dos lados.** El servidor lo sigue computando internamente (`ftgScoreWithBreakdown`) pero `lookupSchema.ts`/`FitogenixProduct` ya no lo exponen — decisión de producto explícita: "que solo se envíe la información que nos sea relevante".
- **Búsqueda por texto rediseñada de punta a punta** (motivo: catálogo mucho más grande post-ETL, y las llamadas en vivo a OFF/terceros eran el cuello de botella de latencia): `productLookupService.lookupProduct` deja de tener cascada externa — solo lee de Supabase (cache) y Redis, tanto para texto como para barcode. Un miss de catálogo devuelve `null` → 404 "todavía no tenemos este producto en nuestro catálogo" en vez de resolver contra OFF/IA. `offService`/`claudeService`/`imageService`/`openBeautyFactsApi`/`fallbackFoodApi` quedan reservados exclusivamente a `scripts/etl/`.
- **Migración 014** (`products_search_trgm`, pg_trgm + índice GIN + RPC `search_products_by_name`) reemplaza el `ILIKE` sin índice + `order(updated_at)` por ranking real de similitud en Postgres. Aplicada en Supabase y validada contra la base real con `scripts/test-search-rpc.ts` (match exacto/parcial/mayúsculas, negativos, guard de longitud, barcode hit/miss) — todos los casos se comportaron como se esperaba.
- Rename `mapOFFToProduct` → `mapRawToProduct` en todo el codebase (ya no mapea exclusivamente datos recién bajados de OFF).
- `cacheService.test.ts` se actualizó para mockear `.rpc('search_products_by_name', ...)` en vez de la cadena vieja `.ilike().order().limit()`.

**Commits:**
- `fitogenix-server`: `6f1ffaf` (rediseño de búsqueda + baja de breakdown), `629bc6b` (prestart hook, rescatado de `agents/pre-deploy-command-for-render`), `5712b36` (smoke test), `a0428bd` (doc). Todos pusheados a `origin/main`.
- `fitogenix-native`: `b7715b8` (contrato v2.1 + baja de ScoreBreakdownSheet). Pusheado a `origin/main`.

**Pendiente (menor, no bloqueante):** borrar `ScoreBreakdownSheet.tsx` y `ftgEngine.ts` (native) del repo — quedaron como stubs sin uso porque no se pudieron `git rm` en la sesión que hizo el cambio; y limpiar la rama local `agents/pre-deploy-command-for-render` (ya mergeada, el worktree ya se sacó).

---

## ADR-003: El tier inicial de Fitogenix es gratuito — el lookup queda abierto y sin cuota

- **Fecha:** 2026-08-31
- **Estado:** Aceptado
- **Decididores:** Jere (producto)

### Contexto

`POST /products/lookup` nunca tuvo `requireAuth`. Durante meses eso se documentó como
**deuda**: `03-agente-backend.md` lo llamaba "Bug 2 — excepción deliberada", y la auditoría
del 28/8/2026 lo levantó como la contradicción **C-02**, porque `00-orquestador.md` afirmaba
en paralelo que *"cada análisis consumido debe poder atribuirse a un usuario para el
descuento de crédito"*. Las dos cosas no podían ser ciertas a la vez.

**El 28/8/2026 se decidió cerrarla al revés de como queda ahora:** que el lookup fuera con
cuota. Esa decisión se aplicó a la documentación (`CONTEXT.md §4.3` reescrita con siete
ítems de gap, `§8` B-1 en 🟡, siete casos de test especificados en `04-agente-qa.md`) pero
**nunca llegó a una línea de código**. Tres días después, al revisarla contra la etapa real
del producto, se dio vuelta.

Lo que hizo cambiar el criterio: el MVP tiene que validar el **criterio Fitogénico y la
calidad del puntaje**. Cualquier fricción de login o de cuota puesta antes de esa validación
mide otra cosa —conversión, tolerancia al paywall— y contamina justamente el dato que se
está buscando. Además, el costo que la cuota iba a proteger ya no existe donde se creía: la
cascada a Claude salió del camino de request el 18/8 (ADR-002, parte 2), así que un lookup
no gasta tokens de IA. Lo que acota el gasto es el catálogo, no un tope por usuario.

### Decisión

**El tier inicial es gratuito.** `POST /products/lookup` es **abierto y sin límite de uso**:
no requiere cuenta, no descuenta nada, no tiene cuota. El modelo de tiers sigue existiendo
como concepto de producto; **la infraestructura de cuotas se implementa cuando exista un tier
pago, no antes** — cero tablas, RPC, RLS, columnas o flags por adelantado.

**Usuario anónimo:** puede escanear y ver resultados. Sus escaneos viven en la sesión y **se
migran a su historial si se registra en esa misma sesión**; si cierra la app sin registrarse,
se pierden. Esto cierra la sub-decisión que el 28/8 había quedado explícitamente abierta.

**El encuadre cambia de deuda a diseño.** El endpoint público deja de tener fecha de
vencimiento. Un agente que lo lea como bug va a proponer arreglarlo; no hay nada que arreglar.

### Alternativas consideradas

- **Lookup con cuota (la decisión del 28/8/2026).** Descartada: la infraestructura que exige
  —descuento atómico, RLS, payload de paywall, reseteo por período— es cara, y protege un
  costo de IA que el request ya no tiene. Medir conversión antes de validar el criterio es
  medir la pregunta equivocada.
- **Login obligatorio sin cuota.** Descartada: fricción sin contrapartida. El escaneo sin
  cuenta es parte del valor, y el copy de la app ya se lo promete al usuario.
- **Cuota solo para anónimos.** Descartada: es infraestructura de cuotas completa con un
  caso menos, no una versión más barata.

### Consecuencias

- **Positivas:** cero trabajo de backend — el código ya cumple la decisión. Se cierra C-02
  como ✅ en vez de arrastrar un 🟡. Se evita construir código muerto con acceso a la base.
- **Negativas / costos:** se descarta trabajo de documentación del 28/8 hecho de buena fe
  (§4.3 con sus siete ítems, siete casos de test de QA). **Sin límite por usuario no hay tope
  natural de gasto** si aparece abuso — hoy lo contienen el rate limit global de 60 req/min y
  el hecho de que un lookup no llame a IA; si eso cambia, la decisión se revisa.
- **Neutras / seguimiento:** el único rastro admitido de la cuota es el **punto de extensión**
  documentado en `03-agente-backend.md`: el descuento entraría en el handler de
  `src/routes/products/lookup.ts`, antes de `lookupProduct`. Una línea, sin código.
- **Queda pendiente en el cliente**, no en el servidor: hoy `scanResultStore.tsx` hidrata
  desde AsyncStorage sin mirar la sesión, o sea el anónimo persiste. Ver `CONTEXT.md §8` B-15.

**Supersede** la decisión del 2026-08-28 sobre C-02, que no llegó a tener ADR propio.

---

## ADR-004: NOVA se sostiene como vocabulario del producto, fuera del puntaje

- **Fecha:** 2026-08-31
- **Estado:** Aceptado
- **Decididores:** Jere (producto)

### Contexto

El motor v2.1 (ADR-002) eliminó el modificador NOVA del cálculo: hoy penaliza **marcadores
de ultraprocesado en el texto de ingredientes**, no `nova_group`. Pero el campo siguió vivo
en todo lo demás, y la auditoría del 28/8 lo levantó como **C-09**: `DICCIONARIO_DOMINIO.md`
lo declaraba componente del score, la app se lo nombra al usuario, y nadie sabía si el campo
tenía que quedarse o irse. Se había propuesto una limpieza de código (columna, migración,
adapters, tipos).

Al mapearlo apareció el dato que faltaba: `scripts/audit-scores.ts` usa `nova_group` como
**señal de calidad del puntaje** —flaguea un NOVA 4 que puntúa ≥75 y un NOVA 1 que puntúa
por debajo de 50—, y **ningún documento lo registraba**.

### Decisión

**NOVA se sostiene. No se borra de ningún lado** — ni del código, ni de la base, ni de la
documentación. Participa de tres formas, y ninguna es el puntaje: se ingiere y se persiste en
`products.nova_group`; se expone como información en la entrada del motor; y es la señal de
calidad de `audit-scores.ts`. **La limpieza de código propuesta queda descartada.**

### Alternativas consideradas

- **Retirarlo por completo** (columna, migración, adapters, tipos, copy). Descartada: se
  perdería la señal de calidad de `audit-scores.ts`, que hoy es la forma más barata de
  detectar un puntaje probablemente mal, y NOVA es vocabulario que el usuario reconoce.
- **Reincorporarlo al puntaje.** Descartada: v2.1 lo sacó por una razón (ADR-002) y esta
  decisión no la revisa. La composición del score sigue abierta como C-08 / `§8` B-4.

### Consecuencias

- **Positivas:** se cierra C-09 sin tocar código. La señal de calidad queda documentada por
  primera vez, en `05-agente-datos.md`.
- **Negativas / costos:** se sostiene un campo que el motor no lee, lo que va a volver a
  parecer código muerto a quien lo mire sin contexto. Por eso está escrito con precisión en
  `CONTEXT.md §2.4`, con las tres formas y sus archivos.
- **Neutras / seguimiento:** desbloquea B-13 — el copy de `HelpScreen.tsx` estaba esperando
  esta decisión y ahora se puede reescribir. **El copy actual afirma que NOVA cuenta para el
  puntaje, y es falso:** se corrige, lo redacta UX.

---

## ADR-005: Pantalla propia para producto fuera de catálogo, distinta del error de red

- **Fecha:** 2026-08-31
- **Estado:** Aceptado
- **Decididores:** Jere (producto)

### Contexto

El rediseño catalog-only del 18/8 (ADR-002, parte 2) hizo que un miss de catálogo devuelva
`null` → 404 en vez de resolver contra OFF/IA. Eso abrió un hueco que quedó sin cubrir: el
servidor devuelve el 404 con mensaje, `src/api/client.ts` lo tipifica como
`ProductNotInCatalogError` — y **ningún archivo de la UI lo consume**. El usuario que escanea
un producto que no está en el catálogo no ve nada diseñado.

### Decisión

Se muestra una **pantalla propia** con el sentido de *"Lo sentimos, el producto no está
disponible para escanear por ahora. Probá con otro."* — eso es la intención, no el literal:
**el copy final lo define el agente de UX.**

La pantalla es **distinta del error de red**, y esa distinción no es cosmética: en el error
de red reintentar sirve, en el fuera de catálogo no. Dos mensajes, dos comportamientos.

El evento `scan_failed` tiene que separar los dos casos en su `reason`.

### Alternativas consideradas

- **Reutilizar el error genérico de red.** Descartada: le ofrece al usuario un reintento que
  no puede funcionar, y borra la métrica de cobertura de catálogo.
- **Volver a resolver contra OFF/IA en el miss.** Descartada: revierte ADR-002 parte 2, que
  se tomó por latencia y costo.

### Consecuencias

- **Positivas:** el `reason` de `scan_failed` mide, con usuarios reales, cuánto le falta al
  catálogo — probablemente el dato más valioso del MVP, y directamente la palanca de
  `CONTEXT.md §4.4`.
- **Negativas / costos:** una pantalla más que mantener, y un dato que va a ser incómodo de
  mirar al principio.
- **Neutras / seguimiento:** ⚠️ `scan_failed` **no existe hoy en el código**
  (cero coincidencias en `fitogenix-native/src/`), aunque `02-agente-frontend.md` lo daba por
  atado a esta distinción. Se implementa junto con la pantalla. Si los dos casos nacen
  compartiendo `reason`, el dato no se recupera hacia atrás.
