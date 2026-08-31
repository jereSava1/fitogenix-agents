# CONTEXT.md — Fitogenix

> **Qué es este documento.** La fuente única de verdad **de negocio** de Fitogenix.
> Los agentes lo citan por puntero (`CONTEXT.md §4.2`), no lo copian.
>
> **Qué NO es.** No es documentación técnica ni un espejo del código. **Ningún umbral,
> versión, nombre de archivo o contrato se transcribe acá**: se cita por puntero al
> archivo real. Si un número vive en CONTEXT.md y en el código, ya perdiste — esa
> duplicación es la causa raíz de la contradicción C-01 (bandas del score mal en tres
> documentos a la vez, ver `AUDITORIA_SETUP_AGENTICO.md`).
>
> **Cómo se lee cada afirmación:**
>
> | Marca | Significa |
> |---|---|
> | ✅ | Verificado contra el código en esta sesión. Se nombra el archivo. |
> | ⚠️ | Declarado en algún `.md` del setup, sin confirmar contra código ni con el cliente. |
> | 🟡 | **Decidido, no implementado.** Se nombra quién decidió, cuándo, y qué falta para que sea ✅. |
> | 🔴 | Contradicción abierta entre fuentes. No la resuelve un agente por criterio propio. |
>
> Un ✅ sin ruta de archivo no es ✅: es 🔴 hasta que se verifique. Un 🟡 **nunca se escribe
> en presente** — se escribe como destino ("va a requerir"), con el estado de hoy al lado.
> Un ⚠️ es distinto de un 🟡: ⚠️ es *no verificado*, 🟡 es *verificado como ausente y ya
> decidido*.
>
> **Cómo se cita el código: archivo + símbolo o texto, nunca número de línea.** Un
> `HelpScreen.tsx:18` deja de ser cierto en cuanto alguien inserta una línea más arriba, y
> **falla en silencio**: el puntero sigue pareciendo válido. Peor todavía, un número de
> línea correcto puede sobrevivir a un archivo equivocado — `ENGINE_VERSION` se citó como
> `ftgEngine.ts:24` cuando vive en `scoring/constants.ts:24`, y la coincidencia del 24
> escondió el error. Se cita **`HelpScreen.tsx` → FAQ *"¿Cómo se calcula el puntaje?"***, o
> **`audit-scores.ts` → `CURATION_QUEUE`**: un símbolo o una cita textual se puede volver a
> encontrar con `grep` después de cualquier edición. Los rangos de línea se admiten **solo
> dentro de un reporte fechado** (`PODA_REPORTE.md`, `REALINEACION_REPORTE.md`), que es
> registro de un momento y no pretende seguir siendo cierto.
>
> **Sesión de verificación:** 2026-08-31, contra `~/fitogenix-server` (`main`, `d73f378`)
> y `~/fitogenix-native` (`main`, `b7715b8`). Una marca ✅ vale para ese commit; si el
> código se movió, se re-verifica antes de citarla.
>
> **Dueño del documento:** el Orquestador. Único escritor del §9. Cualquier agente puede
> proponer un cambio; ninguno lo escribe solo.

---

## §1 — El producto y su usuario

### §1.1 Qué es

Fitogenix es un **escáner de productos de consumo** (alimentos, bebidas, cosméticos,
higiene personal, suplementos): el usuario ingresa un nombre o escanea un código de
barras y recibe un puntaje de salud de 0 a 100 más la lista de ingredientes clasificada
por severidad, según el **criterio Fitogénico** (§2), que es propietario de la marca. ⚠️

Existe como app mobile (React Native + Expo) en **fase Beta**. ⚠️

### §1.2 Quién lo usa

Personas de 25–45 años con interés en salud, nutrición o consumo consciente. **No son
nutricionistas:** quieren un veredicto rápido y claro, no tecnicismos. El contexto de uso
es el supermercado — una mano, mala luz, distracción, conexión pobre. ⚠️

El público incluye personas neurodivergentes y con discapacidad visual; la accesibilidad
es requisito de aprobación, no una fase posterior (ver `01-agente-ux.md` y
`04-agente-qa.md`, ambos conservados sin cambios por la auditoría). ⚠️

### §1.3 La promesa

1. **Directitud** — el veredicto es inmediato y sin ambigüedad.
2. **Confianza ganada** — el puntaje se justifica con los ingredientes listados, no es
   una caja negra.
3. **Sin culpa** — informar, no juzgar.
4. **Honestidad de capa** — cuando habla la filosofía y no la evidencia regulatoria, se
   dice (§2.1). ⚠️ *(declarado en `DICCIONARIO_DOMINIO.md`; el encuadre existe en código,
   ver §2.5)*

### §1.4 El límite declarado

El producto declara explícitamente que **no es consejo médico ni nutricional**, que no
contempla alergias ni condiciones de salud, y que su puntaje es *"una postura declarada,
no una medición médica"*.
✅ El texto exacto vive en `scoring/constants.ts` → `DISCLAIMER` (`framing` y `footer`).
No se reescribe en copy sin pasar por ese archivo.

### §1.5 Flujo principal, hoy

Ingreso (nombre o barcode) → resolución **contra el catálogo propio** → recomposición del
producto con el motor vigente → pantalla de resultado.
✅ `src/services/productLookupService.ts`. **Ya no hay cascada a proveedores externos en
el camino de request** — ver §5.3 y el 🔴 C-07 en §8.

### §1.6 Estado real de la app — pantallas y features

Lo necesitan UX (qué rediseñar), Frontend (qué existe) y QA (qué auditar). **Envejece
rápido:** verificado contra `fitogenix-native` `b7715b8`, y se re-verifica antes de citarlo
como vigente.

| Pantalla | Estado | Ruta |
|---|---|---|
| Inicio (búsqueda por nombre) | Funcional ✅ | `src/screens/HomeScreen.tsx` · tab `index` |
| Historial ("Mis productos": recientes + guardados) | Funcional ✅ | `src/screens/HistoryScreen.tsx` · tab `historial` |
| Escanear (cámara / código de barras) | Funcional ✅ | `src/screens/ScanScreen.tsx` |
| Resultado | Funcional ✅ — la más trabajada | `src/screens/ScanResultScreen.tsx` |
| Guía (contenido estático) | Funcional ✅ | `src/screens/GuideScreen.tsx` |
| Perfil | Funcional ✅ | `src/screens/ProfileScreen.tsx` |
| Datos personales · Privacidad · Ayuda | Funcionales ✅ | `personal-data.tsx` · `privacy.tsx` · `help.tsx` |
| Welcome · Sign-up (email + Google) | Funcional ✅ | `src/screens/WelcomeScreen.tsx`, `SignUpEmailScreen.tsx`, `SignUpDetailsScreen.tsx` |
| Recuperar / resetear contraseña | Funcional ✅ | `ForgotPasswordScreen.tsx` (`supabase.auth.resetPasswordForEmail`), `ResetPasswordScreen.tsx` |

**La pestaña "Comunidad" ya no existe.** ✅ Las cinco pestañas son Inicio · Historial ·
Escanear · Guía · Perfil (`src/app/(tabs)/_layout.tsx`). El lugar que ocupaba el
placeholder lo tomó Historial.

**Features todavía no implementadas** ✅ verificadas una por una:

| Feature | Estado real |
|---|---|
| Login con Facebook | No existe. Google sí funciona (`src/lib/googleAuth.ts`) |
| Notificaciones | Ítem de menú que abre `Alert('Próximamente')` (`ProfileScreen.tsx` → `handleMenuPress`) |
| Foto de etiqueta | **No existe**, pero el copy de la Guía la promete: *"Buscá por nombre o fotografiá la etiqueta"* (`GuideScreen.tsx` → subtítulo del encabezado). Copy a corregir o feature a construir |
| Alternativas de producto | No existe, y el campo `alternatives` **no sirve para eso**: es texto de ambigüedad por ingrediente ("aceite de girasol o soja") ✅ `scoring/types.ts` → campo `alternatives` de la entrada |
| ~~Sin tests en el cliente~~ | **Ya no.** ✅ Desde el 31/8/2026 el cliente tiene suite propia: **49 tests en verde**, incluidos tests de UI con `@testing-library/react` + `jsdom` y `react-native` aliasado a `react-native-web`. La lógica de dominio sigue testeándose en el servidor; acá se testea presentación, guardas de persistencia y analítica |

🟡 **C-14 — el copy in-app contradice al motor y al flujo.** `src/screens/HelpScreen.tsx`
le dice al usuario dos cosas que ya no son ciertas (**decidido el 31/8 que se corrige**; el
copy lo redacta UX, ver §8 B-13):

- FAQ *"¿Cómo se calcula el puntaje?"*: el puntaje *"combina la calidad de los ingredientes,
  la información nutricional, el nivel de procesamiento (NOVA) y la transparencia"* — es la
  descripción del motor **v2**, el de cuatro componentes ponderados que v2.1 reemplazó
  (§2.2). ✅
- FAQ *"¿Por qué no encuentra mi producto?"*: *"Buscamos primero en Open Food Facts y
  completamos lo que falta con IA"* — es la cascada retirada del request el 2026-08-18
  (§5.3). ✅

Es la contradicción de mayor alcance del set: no vive en un prompt de agente, la lee el
usuario. Ver §8 B-13.

**Un FAQ que sí está bien y conviene no tocar:** *"¿Necesito una cuenta para escanear
productos?"* → *"No. Podés escanear y ver resultados sin crear una cuenta. La cuenta sirve
para guardar tu historial y preferencias."* ✅ Coincide exactamente con §4.3.

✅ **El anónimo ya no persiste — implementado y testeado el 31/8/2026** (§4.3, §8 B-15).
Los escaneos de un usuario sin cuenta viven en memoria de sesión: no se leen ni se escriben
en AsyncStorage, y se pierden al reiniciar. **Se migran a su historial si se registra en esa
misma sesión**, re-emitiendo los lookups con el token — `recordScan` es un upsert
idempotente, así que re-emitir no duplica. ✅ `src/presentation/scanResultStore.tsx` ·
`src/presentation/anonScanMigration.ts`.

**El deslogueo borra el disco explícitamente** (`multiRemove`). Es la parte con consecuencia
de privacidad: como los efectos de persistencia ya no escriben `[]` al quedarse sin sesión,
sin ese borrado el historial del que se desloguea le quedaría al siguiente que use el
teléfono. Tiene test de regresión.

🟡 **Lo único pendiente es el copy** del estado vacío del historial anónimo: el texto que hay
es provisorio y vive aislado en `src/constants/scanCopy.ts`. **Lo define UX**
(`01-agente-ux.md`).

✅ **El backend no tiene agujero por acá — verificado.** `recordScan` solo corre cuando
`resolveUserIdFromToken` devuelve un `userId` (`lookup.ts`), y `/users/me/history` registra
`requireAuth` y expone **solo `GET`** (`src/routes/users/history.ts`). No hay forma de
escribir historial sin usuario. El cambio es exclusivamente del cliente.

✅ **Producto fuera de catálogo: cartel propio — implementado y testeado el 31/8/2026**
(§5.3, §8 B-16). El servidor devuelve `404` (`src/routes/products/lookup.ts`) y
`lookupProduct()` devuelve **`null`** — no lanza. `ProductNotInCatalogError` **no participa
de este camino**: lo lanza únicamente `saveProductRemote()` al guardar un producto que no
está en el catálogo ✅.

`ProductNotInCatalogCard` se muestra sobre la cámara en `ScanScreen` y bajo la búsqueda en
`HomeScreen`. **No es un cartel de error, y esa es toda la idea:** sin ícono de alerta, sin
color de peligro, y con *"Escanear otro producto"* en vez de *"Volver a intentar"* — porque
reintentar el mismo producto no cambia nada. Muestra además **qué** fue lo que no se
encontró, que al escanear el usuario nunca tipeó. El error de red sigue siendo otro mensaje,
con reintento.

🟡 **Lo único pendiente es el copy**, provisorio y aislado en `src/constants/scanCopy.ts`.
**Lo define UX** (`01-agente-ux.md`).

✅ **`scan_failed` existe desde el 31/8/2026.** Vive en `src/analytics/`, el primer módulo
de analítica del cliente, con el contrato que `02-agente-frontend.md` ya tenía escrito: una
sola función tipada, `snake_case`, cero PII, y **no-op real si el usuario rechaza analítica**.
Registra `query` (el barcode o el nombre del producto), `queryKind` (`barcode` o `text`, con
el mismo criterio de 8–14 dígitos del servidor), `reason`, `source` y `scannedAt` en ISO 8601
UTC. ⚠️ **El sink todavía no está conectado a ningún SDK** — ver §8 B-17.

---

## §2 — El criterio Fitogénico

### §2.1 Las dos capas

- **Capa A — Regulatoria/toxicológica.** Responde *"¿hay evidencia de daño?"*, con base en
  organismos reguladores (IARC, EFSA, JECFA). ⚠️
- **Capa B — Filosofía Fitogenix.** Responde *"¿esto se parece a comida real?"*. Acá un
  aceite de semilla industrial puede ser cuestionable aunque la Capa A no marque riesgo. ⚠️

**Regla de comunicación:** una evaluación de Capa B que difiere del consenso regulatorio
se comunica como *"la mirada Fitogenix"*, nunca como hecho regulatorio. ⚠️

Definiciones estrictas: `DICCIONARIO_DOMINIO.md` → *Criterio Fitogénico*.

### §2.2 Cómo se construye el puntaje (v2.1)

El puntaje es una **función de la lista de ingredientes**: parte de una base, resta por
impacto y por posición del ingrediente, aplica un modificador de procesamiento, después
techos, y clampea.
✅ Documentado y coeficientado en `scoring/constants.ts`; ejecutado en
`scoring/steps.ts` + `scoring/pipeline.ts`.

**Todos los coeficientes viven en un solo archivo y se citan por puntero:**
`fitogenix-server/src/domain/product/scoring/constants.ts` — base, niveles de impacto y
sus deducciones, frontera de "primeros ingredientes", modificador de procesamiento,
techos, regla de dominancia, anulaciones y umbrales de "sin datos". ✅
**Nunca se transcriben acá.** El propio archivo declara la regla de reconstruibilidad: si
un puntaje no se puede rearmar sumando entradas de esa tabla, el motor está mal, y hay un
test que lo verifica producto por producto. ✅

🔴 **C-08 — La composición del score en el diccionario describe el motor v2, no el v2.1.**
`DICCIONARIO_DOMINIO.md` declara cuatro componentes ponderados (Toxicidad 35% · Nutrición
25% · Procesamiento 25% · Alineación 15%) y gates por ingrediente crítico. El comentario
de `ENGINE_VERSION` en `constants.ts` dice literalmente que en v2.1 *"desaparecen el
promedio ponderado de ejes, el modificador NOVA y la regresión a neutro por cobertura"*, y
que **los puntajes de v2 no son comparables con los de v2.1**. ✅ verificado contra
`scoring/constants.ts` y `scoring/steps.ts`. Ver §8.

### §2.3 Severidad de ingredientes

Cada ingrediente lleva **dos** severidades: una de Capa B (la que se muestra) y una de
Capa A (regulatoria, interna). Pueden diferir legítimamente. ⚠️
La escala de colores, sus significados y la regla de "nunca solo por color":
`DICCIONARIO_DOMINIO.md` → *Severidad de Ingredientes*.

**Un ingrediente que no está en la base no se inventa:** se marca como sin clasificar. ⚠️
La base y sus alias: ✅ `src/domain/product/ingredientData.ts`.

### §2.4 NOVA

> **Decisión (Jere, 2026-08-31): NOVA se sostiene.** Sigue siendo vocabulario del producto:
> se pide, se ingiere, se persiste y se le nombra al usuario. **No se borra de ningún lado**
> — ni del código, ni de la base, ni de la documentación.

**En qué sentido participa, con precisión — porque participa de tres formas y ninguna es el
puntaje:**

| Dónde | Qué hace | Marca |
|---|---|---|
| `offService.ts`, `openBeautyFactsApi.ts`, `cacheService.ts`, `migrations/001` y `008`, `scripts/etl/*` | Se pide, se ingiere y se persiste en `products.nova_group` | ✅ |
| `scoring/types.ts` → campo `nova_group` de la entrada | Está en la entrada y **se expone como información**; desde v2.1 **no participa del cálculo** (lo dice el comentario del propio campo) | ✅ |
| `steps.ts`, `pipeline.ts`, `rubric/` | **Cero referencias.** El motor no lo lee | ✅ |
| `scripts/audit-scores.ts` → chequeos `nova_group === 4` y `=== 1` | **Señal de calidad:** un NOVA 4 puntuando ≥75, o un NOVA 1 por debajo de 50, se flaguean para revisión | ✅ |
| `fitogenix-native/src/screens/HelpScreen.tsx` | **Se le nombra al usuario** — ver el 🟡 de abajo | ✅ |

Lo que el motor v2.1 sí usa en su lugar es un **modificador de procesamiento por marcadores
de ultraprocesado en el texto de ingredientes**, no por `nova_group`. ✅ `PROCESSING` en
`constants.ts`.

**La razón operativa más fuerte para conservar el campo es la cuarta fila**, y no estaba
registrada en ningún documento hasta hoy: `audit-scores.ts` lo usa para detectar puntajes
que probablemente estén mal. Ver `05-agente-datos.md`.

🟡 **El copy de la app dice que NOVA cuenta para el puntaje, y es falso.** El FAQ *"¿Cómo se
calcula el puntaje?"* de `HelpScreen.tsx` afirma que el puntaje *"combina la calidad de los
ingredientes, la información nutricional, el nivel de procesamiento (NOVA) y la
transparencia"* ✅. El motor v2.1 no lee `nova_group`. **Decidido que hay que corregirlo; el
copy nuevo lo redacta UX** (`01-agente-ux.md`) y lo implementa mobile. Ver §8 B-13.

**Lo que NO se hace:** la limpieza de código que se había propuesto — sacar la columna, la
migración, los adapters y los tipos — **queda descartada** por esta decisión.

### §2.5 Lo que el usuario puede verificar

Los **octógonos de advertencia** de la Ley 27.642 / Decreto 151/2022 se **calculan**, no
se leen de la fuente, porque el campo "sellos" de los retailers trae certificaciones
positivas, no advertencias. Son el único dato del producto que el usuario puede
contrastar mirando el envase. ✅ `scoring/seals.ts`, con sus umbrales y el razonamiento
en el encabezado del archivo.

⚠️ El propio archivo advierte que los umbrales deberían contrastarse contra el texto del
decreto **antes de publicitarlos como "los sellos oficiales"**. Nadie lo hizo. Ver §8.

**Ojo con el nombre:** "sello" es ambiguo en este proyecto — los octógonos oficiales
(§2.5) y el sello Fitogénico (§3.2) son cosas distintas. En documentos y prompts se
escribe *octógono* o *sello Fitogénico*, nunca "sello" a secas.

---

## §3 — Bandas, sello y estado

### §3.1 Regla dura

Las bandas, el sello Fitogénico y el estado del producto salen **del mismo lugar y con los
mismos cortes**. Fuente única:
`fitogenix-server/src/domain/product/scoring/constants.ts` → `TIERS`, `EXCELLENT_FROM`,
`BAD_BELOW`. ✅

**Los umbrales no se transcriben en ningún documento, prompt, copy ni test.** Se citan por
puntero a ese archivo.

**Por qué esta regla existe, en palabras del propio código:** *"Antes había tres criterios
distintos para la misma decisión —75/50/25 acá, 70/50 en `resolveProductStatus`, 75/25 en
el sello— y un producto de 72 salía 'Bueno' con sello 'Fitogénico'"*. ✅ comentario de
`TIERS` en `constants.ts` y encabezado de `scoring/presentation.ts`. Ya pasó una vez.

### §3.2 Derivación

Label, color, tagline, sello y estado se derivan de `TIERS` por construcción — el sello y
el estado **coinciden siempre**, no por disciplina sino porque comparten los mismos dos
umbrales. ✅ `scoring/presentation.ts` (`getScoreLabel`, `getScoreTagline`, `getSello`,
`resolveProductStatus`).

### §3.3 `null` es una banda, no un cero

Un producto sin datos suficientes **no se puntúa** y no se coerciona a 0, porque 0 se
leería como "el peor producto posible". Tiene su propia banda y su propio mensaje. ✅
`NO_DATA_TIER` en `constants.ts`; tratamiento en `presentation.ts`. Sin puntaje tampoco
hay sello. ✅

### §3.4 Quién puede recalcular

Solo el backend. El cliente **renderiza los campos derivados que le llegan, nunca los
recalcula**. ✅ el cliente ya no tiene motor: `fitogenix-native/src/domain/product/ftgEngine.ts`
es un shim que reexporta el contrato de tipos y está marcado DEPRECATED en el propio
archivo.

---

## §4 — Modelo de negocio

### §4.1 Fase actual — tier inicial gratuito

**El tier inicial es gratuito.** `POST /products/lookup` es abierto y sin límite de uso: no
requiere cuenta, no descuenta nada, no tiene cuota. El foco del MVP es validar el criterio
Fitogénico y la calidad del puntaje, y cualquier fricción de pago o de login antes de eso
mide otra cosa. ✅ `src/routes/products/lookup.ts` — no registra `requireAuth`, y lo dice en
un comentario propio.

**Esto es diseño del MVP, no deuda.** Ver §4.3.

### §4.2 Fase siguiente — Freemium (**no es el MVP**)

> **Nada de esta sección está vigente.** Describe el modelo al que el producto puede ir
> cuando exista un tier pago. Hoy rige §4.1: tier inicial gratuito, sin cuotas. Un agente
> que lea esta sección como estado actual va a proponer trabajo que **no hay que hacer**.

- **Free:** cuota mensual de análisis; agotada, aparece el paywall con dos salidas
  (upgrade o esperar el reseteo). ⚠️
- **Plus:** ilimitado + features premium. ⚠️
- El **contador de créditos es autoritativo en el backend**, transaccional, y el cliente
  solo lo refleja. ⚠️
- Reseteo mensual por usuario. ⚠️

Cifras y esquema propuesto: `00-orquestador.md` (contexto B2C) y `03-agente-backend.md`
(§ Lógica de Cuotas, marcada como no-MVP). **Cuando exista implementación, esos números se
citan por puntero al código, no acá.**

✅ **Hoy no existe ninguna implementación de cuotas, y no se construye ninguna.** Cero
coincidencias de `user_quotas`, `credits_used` o `quota` en `src/` y en `migrations/` de
`fitogenix-server`. **No se crean tablas, RPC, RLS, columnas ni flags por adelantado:** la
infraestructura de cuotas se implementa cuando exista un tier pago, no antes. El único
rastro admitido es el punto de extensión documentado en `03-agente-backend.md`.

### §4.3 ✅ Tier inicial gratuito

> **Decisión (Jere, 2026-08-31).** El tier inicial es **gratuito**. `POST /products/lookup`
> es **abierto y sin límite de uso**. El modelo de tiers existe como concepto de producto;
> **la infraestructura de cuotas se implementa cuando exista un tier pago, no antes.**
>
> **Usuario anónimo:** puede escanear y ver resultados sin cuenta. Sus escaneos viven en la
> sesión y **se migran a su historial si se registra en esa misma sesión**; si cierra la app
> sin registrarse, se pierden.

**Esto es ✅, no 🟡: el endpoint ya cumple la decisión.** No hay gap de implementación en el
servidor y no hay ticket abierto. ✅ `src/routes/products/lookup.ts` no registra
`requireAuth` — solo lee el Bearer si viene, para registrar el escaneo en el historial del
usuario en background (`recordScan`, upsert idempotente). Todas las rutas de `users/` sí
registran `requireAuth`.

**El encuadre cambió: de deuda a diseño.** Durante meses el endpoint público se documentó
como excepción con fecha de vencimiento — `Bug 2`, "excepción deliberada", y desde el
28/8/2026 como 🟡 pendiente de ponerle cuota. **Ya no.** Es la forma que el producto eligió
para el MVP. Un agente que lo lea como deuda va a proponer arreglarlo; no hay nada que
arreglar. **No agregues `requireAuth` a este endpoint.**

**Punto de extensión, si algún día hay tier pago:** el único lugar donde entraría el
descuento de cuota es el handler de `src/routes/products/lookup.ts`, antes de llamar a
`lookupProduct`. Está documentado en `03-agente-backend.md` en una línea, y eso es todo lo
que existe: **cero código muerto, cero tablas por adelantado.**

**Lo que esta decisión cierra.** C-02 era la contradicción entre dos afirmaciones del setup
que no podían ser ciertas a la vez:

- `00-orquestador.md`: *"Cada análisis consumido debe poder atribuirse a un usuario para el
  descuento de crédito"*.
- `03-agente-backend.md`: *"`POST /products/lookup` NO tiene `requireAuth` … Excepción
  deliberada, no bug … rompería el flujo anónimo"*.

Gana la segunda: **no hay descuento de crédito que atribuir.** La primera describe el modelo
futuro de §4.2, no el MVP. La historia de cómo se llegó acá — incluida la decisión opuesta
del 28/8 — está en `BITACORA_DECISIONES.md`, no acá.

**Lo que sí queda por hacer, y es del cliente, no del servidor:** hoy `scanResultStore.tsx`
hidrata historial y guardados desde AsyncStorage **al montar, sin distinguir sesión** — o
sea, el anónimo persiste. Ver §1.6 y `02-agente-frontend.md`.

### §4.4 La palanca de costo

El costo de IA a escala no lo mueve el precio por token: lo mueve la **tasa de cache-hit
del producto** — cada búsqueda servida desde el catálogo es 100% del costo evitado, no una
fracción. Por eso el poblamiento previo del catálogo (§6) es la palanca económica más
grande del sistema. ⚠️ *(razonamiento de `05-agente-datos.md` y `06-agente-etl-data.md`;
correcto en su lógica, sin medición de cache-hit real que lo respalde)*

Esta lógica se volvió **estructural**, no solo económica: desde el rediseño de búsqueda,
si el catálogo no tiene el producto, no hay resultado (§5.3).

---

## §5 — Arquitectura y stack

### §5.1 Dos repos

| Repo | Qué es | Verificación |
|---|---|---|
| `fitogenix-server` | Node + Fastify + TypeScript. Dominio, servicios, rutas, migraciones y ETL | ✅ `~/fitogenix-server`, `main` `a0428bd` |
| `fitogenix-native` | Cliente Expo / React Native. **Solo UI + contrato de tipos** | ✅ `~/fitogenix-native`, `main` limpio |

Versiones exactas de dependencias: ✅ `package.json` de cada repo. **No se transcriben acá**
(el `03-agente-backend.md` sí las transcribe hoy — se poda en el paso siguiente).

### §5.2 Regla absoluta de frontera

El cliente **nunca** habla directo con Supabase (salvo auth), Anthropic, OFF, SerpAPI ni
remove.bg. Todo pasa por el backend propio.
✅ verificado: en `fitogenix-native` ya no existen `src/infrastructure/` ni `src/app/api/`;
la comunicación va por `src/api/client.ts` y el dominio quedó reducido a tipos
reexportados desde `src/lib/contracts/product.ts`.

### §5.3 Resolución de un lookup — **catalog-only**

```
query → ¿barcode? → Redis → Supabase (catálogo)      → si no está: null
      → ¿nombre?  → Redis → catálogo por similitud   → si no está: null
```

✅ `src/services/productLookupService.ts`. El docstring del archivo lo declara decisión de
producto del 2026-08-18 (ver `BITACORA_DECISIONES.md`, ADR-002 nota parte 2): la cascada
externa se retiró del camino de request porque agregaba round-trips secuenciales y
duplicaba trabajo que el ETL ya hace en batch. **`offService`, `claudeService`,
`openBeautyFactsApi` y `fallbackFoodApi` siguen existiendo y los usa el ETL**, no el
request path. ✅

✅ **C-07 — cerrado el 28/8/2026.** `03-agente-backend.md`, `06-agente-etl-data.md`,
`00-orquestador.md` y el `README.md` de `fitogenix-server` documentaban la cascada
`OFF → OBF → Edamam → Claude` como contrato vigente del lookup. Los cuatro están corregidos
y verificados: cero descripciones remanentes de una cascada en el camino de request.

### §5.4 Caché en niveles

- **Redis (Upstash)** — capa caliente, TTLs distintos según origen del dato y una clave
  aparte para texto→barcode. ✅ valores en `src/services/redisService.ts` y en
  `productLookupService.ts`. No se transcriben acá.
- **Supabase (`products`)** — caché persistente y catálogo.

**Regla de oro:** `products` guarda **datos crudos, no el puntaje**. Cada lectura recompone
el producto con el motor vigente; las columnas de puntaje son denormalizados para listar,
nunca la fuente de verdad. ✅ `src/services/cacheService.ts` + `productRowMapper.ts`.
Consecuencia: un bump de versión del motor **no requiere migrar datos**.

⚠️ **Redis sí puede servir un puntaje viejo** — cachea el producto ya serializado. La
invalidación recomendada por `05-agente-datos.md` es versionar el prefijo de la clave con
la versión del motor. ✅ **No está aplicada:** el prefijo en `redisService.ts` sigue siendo
estático. Ver §8.

### §5.5 Identidad de producto

Identidad estable por `id` (uuid); `barcode` y `name_key` son **atributos de búsqueda
alternativos sobre la misma identidad**, no identidades en sí. Un producto resuelto por
nombre que después se escanea por código **actualiza la misma fila** en vez de duplicarla,
para no romper favoritos ni historial. ✅ contrato en `cacheService.ts` y en
`migrations/006_product_identity.sql`.

### §5.6 Contrato de API

El contrato vigente de endpoints (método, auth, body, respuestas) se cita por puntero a
`fitogenix-server/src/routes/` y a `03-agente-backend.md`, que lo mantiene. ✅ rutas
verificadas: `products/lookup`, `products/image`, `users/deleteMe`, `users/saved`,
`users/history`. **Regla:** un endpoint nuevo se agrega al contrato en el mismo commit que
lo implementa.

### §5.7 Selección de modelo de IA

Regla del proyecto, aplicada por tres agentes (Backend implementa los call sites, Datos la
hace cumplir y tunea los prompts, ETL la consume en batch). Vive acá porque ninguno de los
tres es su dueño exclusivo.

**¿La entrada incluye una imagen a interpretar? → Sonnet Vision. ¿Es solo texto o barcode?
→ Haiku.** Nunca Sonnet donde alcanza Haiku: el costo importa a escala.

- **Haiku — texto estructurado. Es el default del proyecto.** Enriquecer un producto con
  campos faltantes, construir uno desde su nombre o barcode, traducir ingredientes. Salida
  JSON determinista, system prompt cacheado. ✅ el modelo, la temperatura y los `max_tokens`
  vigentes viven en `src/services/claudeService.ts`; los valores **no se transcriben acá**.
- **Sonnet Vision — solo cuando hay imagen.** Leer la etiqueta o la tabla nutricional desde
  una foto. 🟡 **Decidido como regla, sin call site:** hoy no existe análisis por foto en el
  producto (§1.6) — la regla está escrita para cuando exista, no describe código de hoy.

**Dónde corre esto hoy ✅:** en el ETL, en batch (`scripts/etl/jobs/runMerge.ts`,
`scripts/etl/lib/qualityAI.ts`), **no en el camino de request** (§5.3).

El tuning de prompts, el presupuesto de tokens y el pricing son dominio de
`05-agente-datos.md`, que los mantiene con las cifras vigentes.

### §5.8 Stack del cliente y restricciones que impone

Lo comparten UX (qué se puede diseñar) y Frontend (con qué se implementa). Versiones
exactas: ✅ `fitogenix-native/package.json` — **no se transcriben acá**.

- **Expo + React Native**, una base para iOS y Android. Navegación **file-based con Expo
  Router**, con rutas tipadas. ✅
- **Estilos con `StyleSheet` por pantalla.** No hay CSS ni framework de estilos: los tokens
  de diseño viven en `src/constants/theme.ts`. ✅
- **`expo-camera`** para el escaneo de códigos de barras. ✅ `src/screens/ScanScreen.tsx`.
  No hay captura de foto de etiqueta (§1.6).
- **`expo-blur`** en el tab bar, **`lucide-react-native`** para los íconos. ✅
- **Animación:** el `ScoreDial` usa `react-native-svg` con la `Animated` API de React
  Native. ✅ `src/components/ScoreDial.tsx`. `react-native-reanimated` está instalado. No
  hay otras animaciones complejas.
- **Persistencia local:** `@react-native-async-storage/async-storage` — historial y
  guardados se hidratan desde ahí al abrir. ✅ `src/presentation/scanResultStore.tsx`.
- **Estado global:** dos Context (`scanResultStore`, `signUpStore`). **No hay React
  Query.** ✅ (sin `@tanstack/*` en `package.json`).

**Latencia — el dato cambió y el copy de UX no lo siguió.** ⚠️→✅ La cifra "un análisis
tarda 2-8 segundos porque hay una llamada a Anthropic" describía la cascada retirada. Desde
que el request es catalog-only (§5.3) **no hay llamada a IA en el camino de request**: la
latencia es la de Redis y Supabase. ✅ `productLookupService.ts` no importa `claudeService`.
El estado de carga sigue siendo necesario, pero dimensionarlo contra "8 segundos de IA" es
diseñar para un flujo que ya no existe.

---

## §6 — Datos: fuentes, pipeline y calidad medida

### §6.1 Fuentes

Open Food Facts (dump y API), Open Beauty Facts, Edamam, scrapers de retailers argentinos
(APIs tipo VTEX cuando existen), enriquecimiento por IA, y pre-población sintética de
búsquedas frecuentes. ✅ los adaptadores y jobs existen bajo `scripts/etl/`; los comandos
reales están en los scripts npm del repo (`etl:*`, `audit:*`) — no se transcriben acá.

### §6.2 Pipeline — nada entra directo

```
adapter → products_staging → merge por barcode (campo a campo)
        → gate de completitud → enriquecimiento de gaps → products
```

✅ `migrations/009_products_staging.sql`; detalle del diseño en `06-agente-etl-data.md`
(el documento mejor calificado de la auditoría). Cada fila cruda queda trazable hasta el
producto final al que contribuyó, con su corrida de origen. ✅

**Regla:** el gate de completitud es el **mismo criterio** que usa el caché para decidir si
una fila sirve — no uno nuevo y paralelo. ⚠️ *(declarado; no re-verificado línea a línea
en esta sesión)*

### §6.3 Estado de calidad **medido** — 28/8/2026

Números de `npm run audit:scores` + `scripts/score-histogram.ts` contra el catálogo real,
tomados de `tareas/FTG-001-calidad-de-datos.md`. ✅ medidos, con fecha. **No se recalculan
ni se redondean: se citan como están, con la fecha.**

| Métrica | Valor (28/8/2026) |
|---|---|
| Productos con lista de ingredientes | 13.737 |
| Puntuados | 9.800 |
| Sin puntaje | 3.937 |
| — de ellos, `sin-identificar` (bucket defectuoso) | 2.484 (18,1%) |
| — de ellos, `fuera-de-alcance` (comportamiento correcto) | 1.287 |
| Términos distintos sin identificar | 8.991 |
| Apariciones totales de esos términos | 20.290 |
| Cobertura del top 40 de la cola | 18,6% |
| Productos con 0% de cobertura | 1.453 |
| Cobertura promedio de los sin puntaje | 44,3% |

### §6.4 Los tres defectos, medidos

- **A — Ingredientes reales sin alias.** El motor no los ve y **calcula mal** el puntaje.
  Caso testigo: `jmaf` en 322 productos. ✅ `src/domain/product/ingredientData.ts` → entrada `"jarabe de maíz"` — la
  sigla figura en la descripción (`desc`), no en los `aliases`.
- **B — Fragmentos de rotulado tratados como ingredientes** (dosis `N mg/kg`, `CONTIENE`,
  códigos INS pegados a su nombre): ≈740 apariciones de nada, que hunden la cobertura
  artificialmente. ✅ medido.
- **C — Se emite puntaje sin haber entendido la etiqueta.** El más grave: es un aval de
  marca sobre datos no comprendidos. Ejemplo real medido: `89 Excelente cob=0% Té común`. ✅

Detalle completo, criterios de aceptación y reparto por agente:
`tareas/FTG-001-calidad-de-datos.md`.

### §6.5 Lo que ya existe y lo que no

✅ **Existe y está testeado:** heurísticas de calidad (boilerplate de rotulado, marca en el
nombre), validación de plausibilidad nutricional por rangos fisiológicos, gate de
completitud, merge campo a campo, staging con trazabilidad, verificación asistida por IA, y
jobs de auditoría y de fix. ✅ inventario verificado en la auditoría; `audit:scores` y los
`etl:*-quality` están en los scripts del repo.

🔴 **No existe:** constraints en la base que impidan que un dato sucio vuelva a entrar, y
un **criterio versionado de qué es un dato sucio** en términos de dominio (no de patrón de
texto). ✅ verificado: la cola de curaduría **se calcula y se descarta** —
`CURATION_QUEUE` se puebla en `scripts/audit-scores.ts` (el `for` sobre `bd.unidentified`) y nunca se imprime.
Ver §8 B-3 (la cola) y B-12 (el dueño que falta para definir "dato sucio").

**Conclusión:** el ETL guarda bien la puerta de entrada. **Nadie auditó lo que ya está
adentro.**

---

## §7 — Roles y dueños

Un artefacto sin dueño es un artefacto que se rompe sin que nadie se entere: es
exactamente lo que pasó con la tabla de ingredientes (§6.4 A).

| Artefacto | Dueño | Regla |
|---|---|---|
| Este documento · §9 · orden de las tareas | **orchestrator** | Único escritor del changelog |
| Esquema, constraints, ADRs, dónde vive cada gate | **architect** 🆕 | No clasifica sustancias |
| Valores nutricionales, rúbrica, claims regulatorios, alias de ingredientes, definición de dato sucio | **nutrition** 🆕 | **No escribe código.** Ningún alias entra sin que declare qué sustancia es y con qué fundamento |
| Motor, rutas, schema en código, tests del dominio | **backend** | No decide qué impacto lleva un ingrediente |
| Cliente Expo, contrato consumido, analytics | **mobile** | No recalcula nada del puntaje |
| System prompts, parámetros de inferencia, política de caché de IA | **data-ai** | **Único** autorizado a tocar prompts |
| Ingesta, scrapers, staging, medición del catálogo | **etl** | Importa el motor, nunca lo modifica |
| Veredicto de "listo", a11y, tests que rompen | **qa** | No implementa lo que audita |
| Flujos, copy, estados de UI, paywall | **ux** *(bajo demanda)* | Especifica todos los estados o no se implementa |
| Contenedor, despliegue, secretos, rate limit de infra | **devops** *(bajo demanda)* | No toca lógica de negocio |

✅ **`nutrition` existe desde el 31/8/2026:** `09-agente-nutricion.md`, con su SSOT propio
en `nutricion/NUTRICION.md`. Nace **vacío de conocimiento y con contrato duro**: toda
afirmación cita fuente primaria o sale 🔴, y su schema no admite un ✅ sin cita. Eso lo hace
seguro de crear antes de tener la base de datos cargada — ver §8 B-12.

🟡 **`architect` sigue sin existir.** Decidido el 31/8 que se crea (dueño del contrato de
producto cross-repo y de las migraciones); el archivo `08-agente-arquitecto.md` está
reservado y sin escribir.

**Regla de dominios exclusivos:** dos agentes nunca tocan el mismo archivo en paralelo, y
ningún agente edita un artefacto del que no es dueño — se lo pide al dueño.

---

## §8 — Bloqueantes activos

Ordenados por costo de seguir sin resolverlos.

| # | Bloqueante | Estado | Quién decide |
|---|---|---|---|
| ~~**B-1**~~ | ✅ **C-02 cerrado (31/8/2026): tier inicial gratuito** (§4.3). El lookup es abierto y sin cuota — **decisión de producto, no deuda**. El código ya la cumple, así que no queda gap de implementación en el servidor ni ticket abierto. Reemplaza la decisión del 28/8 (el ida y vuelta está en `BITACORA_DECISIONES.md`) | ✅ `src/routes/products/lookup.ts` | — |
| **B-2** | 🔴 **C-11** — el motor **emite puntaje sin entender la etiqueta**: 1.453 productos con 0% de cobertura, casos "Excelente" entre ellos (§6.4 C) | Medido 28/8 ✅ · sin gate | nutrition define el umbral · architect dónde vive · backend implementa |
| **B-3** | 🔴 **C-10** — cola de curaduría de **8.991 términos** que se calcula y se tira (§6.5) | ✅ `audit-scores.ts` → `CURATION_QUEUE` | nutrition (clasifica) · backend (imprime) |
| **B-4** | 🔴 **C-08** — el criterio documentado (4 componentes ponderados) **no es el motor v2.1** (§2.2) | ✅ contra `constants.ts` | nutrition + orchestrator: qué se corrige, el doc o la expectativa |
| ~~**B-4b**~~ | ✅ **C-09 cerrado (31/8/2026): NOVA se sostiene.** Sigue siendo vocabulario del producto — se ingiere, se persiste en `products.nova_group`, lo mergea el ETL, `audit-scores.ts` lo usa como señal de calidad y se le nombra al usuario. El motor v2.1 **no lo lee para el puntaje** ✅, y eso ahora está dicho con precisión en §2.4. **No se borra nada; la limpieza de código queda descartada.** Lo único que queda vivo es el copy que dice lo contrario → B-13 | ✅ mapeado 28/8, decidido 31/8 | — |
| ~~**B-5**~~ | ✅ **C-07 cerrado (28/8/2026).** La cascada externa ya no se documenta como camino de request en ningún archivo del set ni en el `README.md` del servidor (§5.3) | Verificado por grep en los 8 agentes + `CONTEXT.md` + READMEs | — |
| **B-6** | 🔴 Migraciones que **se corren a mano en el SQL Editor** de Supabase — `013_score_nullable.sql` y `014_product_search_trgm.sql` están marcadas NO APLICADAS en su propio archivo ✅. No hay forma automática de saber qué esquema está vivo | devops + architect |
| **B-7** | ⚠️ **Umbral del sello a 70** — decidido, ~40 productos afectados, ticket aparte; hoy sigue derivado de `TIERS` ✅. Cuando se aplique, se cambia **en `constants.ts` y en ningún otro lado** | orchestrator (prioriza) |
| **B-8** | ⚠️ Redis puede servir puntajes viejos: el prefijo de clave **no está versionado** por versión del motor ✅ (`redisService.ts`) | data-ai propone · backend aplica |
| **B-9** | ⚠️ **En `fitogenix-server`:** sin `Dockerfile`, sin config de despliegue, sin `engines.node` en `package.json` ✅. Rate limit en memoria: con N instancias el límite real es N veces el nominal. **En `fitogenix-native` la mitad de `engines.node` se cerró el 31/8** — ver B-18, que muestra lo que cuesta no declararla | devops |
| **B-10** | ⚠️ Sin observabilidad conectada (Sentry/Datadog). El contrato de logging está escrito; no tiene a dónde reportar | devops + backend |
| **B-11** | 🟡 **4 de 5 umbrales verificados el 31/8.** Azúcares, grasas saturadas, grasas totales y sodio **coinciden exactamente** con el perfil de OPS, que es la fuente que la ley adopta ✅. Queda 🔴 **el umbral de calorías** (275/70): no sale de OPS —su modelo no define criterio de energía— sino del Anexo II del Decreto 151/2022, **que no está disponible online**. Verificado además que la ausencia de octógono de grasas trans es correcta ✅ | nutrition |
| **B-12** | 🟡 **El rol existe desde el 31/8** (`09-agente-nutricion.md`), pero **su base de conocimiento está vacía**: `nutricion/NUTRICION.md §N7` lista tres fuentes primarias que faltan, y sin ellas B-2, B-3 y B-4 terminan en `blocked`. Crear el agente movió el problema de *"no hay a quién preguntarle"* a *"hay a quién preguntarle y todavía no tiene con qué responder"* — que es progreso real, pero no es cierre | Jere: conseguir las fuentes de §N7 |
| **B-13** | 🟡 **C-14 — el copy in-app le miente al usuario** (§1.6, §2.4). El FAQ *"¿Cómo se calcula el puntaje?"* de `HelpScreen.tsx` nombra a NOVA como componente del puntaje (falso desde v2.1) y el FAQ *"¿Por qué no encuentra mi producto?"* promete la cascada OFF→IA retirada el 18/8. Es deriva doc↔código que llegó a la pantalla. **Ya no está bloqueado:** B-4b se cerró el 31/8 y NOVA se sostiene, así que el copy nuevo ya se puede escribir. Es cambio de código, no de documentación | ✅ `HelpScreen.tsx` → los dos FAQs | ux redacta el copy · mobile lo implementa |
| **B-14** | 🟡 **La Fase 2 del plan está a medias y nadie lo anotó.** Las 8 dependencias sin usar **ya se eliminaron** ✅ (no están en `package.json`, cero usos). Siguen pendientes: `expo-image` instalada con cero imports ✅, y React Query ausente ✅ | Verificado 28/8 | mobile |
| ~~**B-15**~~ | ✅ **Cerrado el 31/8/2026: el anónimo ya no persiste.** Implementado y testeado — sin sesión no se lee ni se escribe AsyncStorage, y el deslogueo borra el disco con `multiRemove` (la parte con consecuencia de privacidad, con test de regresión). La migración anónimo→logueado re-emite los lookups con token. **Queda 🟡 solo el copy** del estado vacío, a cargo de UX | ✅ `scanResultStore.tsx` · `anonScanMigration.ts` · 7 tests | ux escribe el copy |
| ~~**B-16**~~ | ✅ **Cerrado el 31/8/2026: cartel propio de fuera de catálogo.** `ProductNotInCatalogCard` en `ScanScreen` y `HomeScreen`, con estado separado del error de red, sin ícono de alerta y con *"Escanear otro producto"* en vez de reintentar. Emite `scan_failed` con el `reason` distinguido. **Queda 🟡 solo el copy**, a cargo de UX | ✅ `ProductNotInCatalogCard.tsx` · `useScanFlow.ts` · 8 tests | ux escribe el copy |
| **B-17** | ⚠️ **La analítica no tiene a dónde reportar.** `src/analytics/` existe y emite `scan_failed` ✅, pero **no hay SDK conectado**: sin `setAnalyticsSink()` en el arranque, los eventos se descartan. Es el mismo hueco que B-10 en el backend, ahora también en el cliente. Mientras siga así, la métrica de cobertura de catálogo **no se está midiendo** | ✅ `src/analytics/index.ts` | Jere elige la herramienta · mobile la conecta |
| ~~**B-18**~~ | ✅ **Cerrado el 31/8/2026: CI de `fitogenix-native` corría en una versión de Node que sus propias dependencias no soportan.** El workflow fijaba `node-version: 20` y `jsdom@30` declara `^22.22.2 || ^24.15.0 || >=26.0.0`; `undici@8`, `>=22.19.0`. Los tres tests de UI no arrancaban el worker (`markAsUncloneable is not a function`) y CI daba verde en los otros dos, con exit 1. **`npm ci` no protesta porque `engines` no se valida sin `engine-strict`** — la declaración sirve para que se vea al instalar, no para que falle. Resuelto con `.nvmrc` + `node-version-file` + `engines.node`, y se sumó `tsc --noEmit` al pipeline | ✅ `.github/workflows/test.yml` · `package.json` · `.nvmrc` | — |

---

## §9 — Changelog

> **Único escritor: el Orquestador.** Un cambio de este documento se registra acá con
> fecha, qué sección cambió y contra qué se verificó. Una decisión de arquitectura además
> se registra como ADR en `BITACORA_DECISIONES.md`; acá va la línea de que se registró.

| Fecha | Cambio | Verificado contra |
|---|---|---|
| 2026-08-28 | Creación. §1–§8 armados desde `AUDITORIA_SETUP_AGENTICO.md`, `DICCIONARIO_DOMINIO.md` (ya corregido) y `tareas/FTG-001`. Números de §6 tomados de FTG-001 sin recalcular | `~/fitogenix-server` `main` `a0428bd` · `~/fitogenix-native` `main` |
| 2026-08-28 | Contradicciones nuevas encontradas en la verificación de esta sesión: **C-07** (cascada retirada, docs desactualizados), **C-08** (composición del score describe v2), **C-09** (rol de NOVA), **C-10** (cola de curaduría descartada), **C-11** (puntaje sin cobertura). Todas en §8 | `productLookupService.ts` · `scoring/constants.ts` · `scripts/audit-scores.ts` |
| 2026-08-28 | **Convención de marcas ampliada a cuatro:** se suma 🟡 (decidido, no implementado) a ✅/⚠️/🔴. ⚠️ = no verificado; 🟡 = verificado como ausente y ya decidido | — |
| 2026-08-28 | **Tres huecos del SSOT cerrados** (autorizados por Jere): §1.6 estado real de pantallas y features · §5.7 selección de modelo de IA · §5.8 stack del cliente. **Ninguna sección existente se renumeró** — los punteros `§X` de los 8 agentes siguen válidos | `fitogenix-native` `b7715b8` · `claudeService.ts` |
| 2026-08-28 | **C-09 mapeado, no cerrado:** NOVA se ingiere, se persiste, lo usa `audit-scores.ts` como señal de calidad y se le nombra al usuario, pero el motor no lo lee. B-4 se desdobla en B-4 (C-08) y B-4b (C-09) | `steps.ts`/`pipeline.ts` · `audit-scores.ts` (chequeos `nova_group === 4` / `=== 1`) · `HelpScreen.tsx` |
| 2026-08-28 | **C-07 cerrado.** Corregido en `00-orquestador.md` (reescrito), `02-agente-frontend.md` (reescrito), `03`, `06` y el `README.md` de `fitogenix-server` — que documentaba la cascada como *la* arquitectura y decía "Unit tests (119)" cuando hay 27 archivos y ~345 casos | grep en los 9 documentos + `productLookupService.test.ts` |
| 2026-08-28 | **C-14 nuevo (B-13):** el copy de `HelpScreen.tsx` describe el motor v2 y la cascada retirada. Primer caso de deriva que llegó al usuario final. **C-15 nuevo (B-14):** la poda de dependencias de la Fase 2 ya se hizo sin registrarse | `HelpScreen.tsx` · `fitogenix-native/package.json` |
| 2026-08-31 | **Convención de citas al código:** archivo + símbolo o cita textual, nunca número de línea. Se convirtieron los 10 punteros con línea del set vivo. Encontrado al aplicarla: `ENGINE_VERSION` se citaba como `ftgEngine.ts:24` y vive en `scoring/constants.ts:24` — archivo equivocado, número correcto, error invisible durante tres días. Los rangos de línea quedan permitidos solo en reportes fechados | `HelpScreen.tsx` · `ProfileScreen.tsx` · `ingredientData.ts` · `audit-scores.ts` · `scoring/constants.ts` |
| 2026-08-31 | **Decisión 1 — tier inicial gratuito.** §4.3 reescrita entera: de 🟡 *lookup con cuota* a ✅ *tier inicial gratuito*. El encuadre pasa de **deuda a diseño del MVP** — el endpoint público ya no tiene fecha de vencimiento. §4.1 y §4.2 alineadas (§4.2 marcada explícitamente como no-MVP), §8 B-1 cerrado, los 7 ítems del gap eliminados. **Revierte la decisión del 28/8**, cuya entrada sale de este changelog: la evolución vive en `BITACORA_DECISIONES.md` | ✅ `src/routes/products/lookup.ts` · `src/routes/users/history.ts` |
| 2026-08-31 | **Decisión 2 — NOVA se sostiene.** §2.4 reescrita: las tres formas en que NOVA participa, y ninguna es el puntaje. §8 B-4b cerrado como *sostenido*. Se registra por primera vez el uso de `audit-scores.ts` como señal de calidad — la razón operativa más fuerte para conservar el campo, que ningún documento tenía. **La limpieza de código queda descartada.** B-13 se desbloquea (era 🔴 bloqueado por B-4b, ahora 🟡) | ✅ `steps.ts`/`pipeline.ts`/`rubric/` · `audit-scores.ts` · `scoring/types.ts` |
| 2026-08-31 | **Decisión 3 — pantalla de producto fuera de catálogo.** Nuevo §8 B-16, documentado en §1.6. Hallazgo al verificar: `scan_failed`, que `02-agente-frontend.md` daba por atado a esa distinción, **no existe en el código** | ✅ `client.ts` · `lookup.ts` · grep en `fitogenix-native/src/` |
| 2026-08-31 | **Corrección de un error de esta misma sesión, y anterior a ella.** Se había escrito que el 404 del lookup se tipifica como `ProductNotInCatalogError` y que nadie lo consume. **Es falso:** `lookupProduct()` devuelve `null`, y ese error lo lanza solo `saveProductRemote()`. El caso fuera-de-catálogo **sí se detecta** en los dos hooks; lo que fallaba era la presentación y el copy. El error venía de `REALINEACION_REPORTE.md` (28/8), que ató `scan_failed` a `ProductNotInCatalogError`, y se propagó sin verificarse contra el call site | ✅ `client.ts` → `lookupProduct` / `saveProductRemote` · `useScanFlow.ts` · `useProductSearch.ts` |
| 2026-08-31 | **Nuevo §8 B-15 — el anónimo persiste y no debería.** `scanResultStore.tsx` hidrata desde AsyncStorage sin mirar sesión. Se cierra además la sub-decisión que el 28/8 quedó viva: los escaneos de la sesión **se migran** al historial si el anónimo se registra en esa sesión. Verificado que el backend no acepta escrituras de historial sin usuario | ✅ `scanResultStore.tsx` · `users/history.ts` (requireAuth, solo GET) |
| 2026-08-31 | **B-15 y B-16 cerrados: el código, no solo la documentación.** El anónimo ya no persiste, el deslogueo borra el disco con `multiRemove`, y la migración anónimo→logueado re-emite los lookups con token. Fuera de catálogo tiene cartel propio, separado del error de red. **Queda 🟡 solo el copy de las dos pantallas**, a cargo de UX | ✅ `scanResultStore.tsx` · `anonScanMigration.ts` · `ProductNotInCatalogCard.tsx` · `useScanFlow.ts` |
| 2026-08-31 | **Primer módulo de analítica del cliente (`src/analytics/`) y `scan_failed` implementado.** Una sola función tipada, `snake_case`, cero PII, no-op real sin consentimiento. El evento registra el barcode o nombre del producto, su tipo, el motivo, el origen y la fecha del escaneo. **Nuevo B-17:** el sink no está conectado a ningún SDK, así que la métrica de cobertura de catálogo todavía no se mide | ✅ `src/analytics/index.ts` · `analytics-events.ts` |
| 2026-08-31 | **El cliente dejó de no tener tests: 49 en verde.** `@testing-library/react` + `jsdom`, con `react-native` aliasado a `react-native-web` (que ya era dependencia). No se usó `@testing-library/react-native`: necesita `react-test-renderer`, deprecado en React 19, y que el runner transforme el Flow sin transpilar de `react-native`. **Testea render web, no plataforma nativa** — no reemplaza device ni Detox | ✅ `vitest.config.ts` · 5 archivos de test |
| 2026-08-31 | **CI de `fitogenix-native` roto por el Node del runner, y arreglado** (§8 B-18). El workflow corría Node 20 y `jsdom@30` pide `^22.22.2` — los tres tests de UI no arrancaban el worker. Es deuda preexistente que se hizo visible ahora: `react-native@0.85` ya pedía Node 20.19.4+ y el repo no tenía `engines` para decirlo. La versión pasa a vivir en `.nvmrc`, no en un literal del YAML que se desincroniza en silencio | ✅ `npm ci` limpio sobre el mismo `package-lock`: 49 en verde, `tsc` limpio |
| 2026-08-31 | **Nace el Agente de Nutrición** (`09-agente-nutricion.md`) con su SSOT propio `nutricion/NUTRICION.md` (§N1–§N7). Cierra el rol que §7 marcaba como faltante y que B-12 señala como causa raíz de otros cuatro bloqueantes. Nace **vacío y con contrato duro**: cita fuente primaria o devuelve 🔴, y distingue ✅ (primaria) de 📄 (prensa) — un 📄 nunca alcanza para cambiar código | `Ley 27.642` art. 7 · perfil de nutrientes de OPS · `scoring/seals.ts` |
| 2026-08-31 | **B-11 avanza: 4 de 5 umbrales de octógonos verificados** contra el perfil de OPS. Los cuatro coinciden exactamente; el de calorías queda 🔴 porque el Anexo II del Decreto 151/2022 no está accesible. Verificado además que la ausencia de octógono de grasas trans **es correcta** (la ley no lo incluye; OPS sí). Registrado en el encabezado de `seals.ts`, donde se usa | `fitogenix-server` `0712f2d` |
| 2026-08-31 | **Corrección de un error de análisis, registrada porque el método importa.** Se reportó que `seals.ts` no implementaba la excepción del art. 7. **Es falso:** está en `steps.ts` → `applyNutrition`, un nivel más arriba. El error salió de concluir sobre un archivo aislado sin verificar el call site — el mismo método que produjo C-07 y C-14. Es el caso que justifica el contrato del agente nuevo, y está citado en su prompt | ✅ `scoring/steps.ts` |
| 2026-08-31 | **La suite se corrió, por primera vez desde que se documentó: 410 tests en 27 archivos, todos en verde, y `tsc --noEmit` limpio.** Cierra el *"416 tests en verde"* que arrastraba ⚠️ desde el 18/8 sin reproducir. El conteo estático del 28/8 (~345 `it()`) subestimaba: no contaba los casos generados dentro de tablas | `vitest run` + `npm ci` limpio sobre el `package-lock.json` de `d73f378` |

### Pendiente inmediato (fuera de este documento)

**Poda de los 8 agentes a punteros §X.** Este documento tenía que existir primero. Cada
agente pierde su `## El producto: Fitogenix`, su copia del stack y su copia de las bandas,
y en su lugar cita `CONTEXT.md §1`, `§5`, `§3`. Es la cura de C-06 — la duplicación en
ocho lugares que causó C-01 y C-03.
