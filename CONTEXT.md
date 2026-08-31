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
| Sin tests en el cliente | ✅ cero archivos `*.test.ts` en `fitogenix-native/src/`; `vitest.config.ts` declara `passWithNoTests: true` a propósito — la lógica se testea en el servidor |

🔴 **C-14 — el copy in-app contradice al motor y al flujo.** `src/screens/HelpScreen.tsx`
le dice al usuario dos cosas que ya no son ciertas:

- FAQ *"¿Cómo se calcula el puntaje?"*: el puntaje *"combina la calidad de los ingredientes,
  la información nutricional, el nivel de procesamiento (NOVA) y la transparencia"* — es la
  descripción del motor **v2**, el de cuatro componentes ponderados que v2.1 reemplazó
  (§2.2). ✅
- FAQ *"¿Por qué no encuentra mi producto?"*: *"Buscamos primero en Open Food Facts y
  completamos lo que falta con IA"* — es la cascada retirada del request el 2026-08-18
  (§5.3). ✅

Es la contradicción de mayor alcance del set: no vive en un prompt de agente, la lee el
usuario. Ver §8 B-13.

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

🔴 **C-09 — El rol de NOVA está sin resolver.** `DICCIONARIO_DOMINIO.md` lo declara
componente del score con un aporte numérico por grupo; el v2.1 eliminó el modificador
NOVA. ✅ (`constants.ts`, comentario de `ENGINE_VERSION`). Lo que existe hoy en su lugar
es un **modificador de procesamiento por marcadores de ultraprocesado**, no por
`nova_group`. ✅ `PROCESSING` en `constants.ts`. Falta decidir si NOVA sigue siendo
vocabulario del producto (se sigue consumiendo y mostrando) o se retira. Ver §8.

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

### §4.1 Fase actual

**Beta abierta:** análisis ilimitados, sin fricción de pago. El foco es validar el criterio
Fitogénico y la calidad del puntaje. ⚠️

### §4.2 Fase siguiente — Freemium

- **Free:** cuota mensual de análisis; agotada, aparece el paywall con dos salidas
  (upgrade o esperar el reseteo). ⚠️
- **Plus:** ilimitado + features premium. ⚠️
- El **contador de créditos es autoritativo en el backend**, transaccional, y el cliente
  solo lo refleja. ⚠️
- Reseteo mensual por usuario. ⚠️

Cifras y esquema propuesto: `00-orquestador.md` (contexto B2C) y `03-agente-backend.md`
(§ Lógica de Cuotas). **Cuando exista implementación, esos números se citan por puntero al
código, no acá.**

✅ **Hoy no existe ninguna implementación de cuotas.** Cero coincidencias de `user_quotas`,
`credits_used` o `quota` en `src/` y en `migrations/` de `fitogenix-server`.

### §4.3 🟡 C-02 — Lookup público vs atribución de consumo — **DECIDIDO**

> **Decisión (Jere, 2026-08-28): `POST /products/lookup` VA CON CUOTA.** La atribución de
> consumo gana; el flujo anónimo sin límite se retira. **Esto es 🟡, no ✅** — hoy el
> endpoint sigue siendo público y no hay cuotas. Ver el gap de implementación abajo.

Contexto de la contradicción que esta decisión cierra — dos afirmaciones que no podían ser
ciertas a la vez:

- `00-orquestador.md`: *"Cada análisis consumido debe poder atribuirse a un usuario para el
  descuento de crédito"*.
- `03-agente-backend.md`: *"`POST /products/lookup` NO tiene `requireAuth` … Excepción
  deliberada, no bug … rompería el flujo anónimo"*.

✅ El código confirma la excepción: `src/routes/products/lookup.ts` no registra
`requireAuth` (lo dice en un comentario propio) y solo lee el Bearer si viene, para
registrar el escaneo; todas las rutas de `users/` sí lo registran.

**Estado de hoy ✅:** el endpoint es público, no descuenta nada, y no existe tabla de
cuotas (`grep` de `user_quotas`/`credits_used`/`quota` en `src/` y `migrations/`: cero).

**Destino 🟡:** el lookup **va a requerir** atribución y **va a descontar** cuota. Lo que
falta para que esto sea ✅ — la lista es el alcance del ticket, no está implementado:

1. Registrar autenticación en `src/routes/products/lookup.ts` (hoy no la registra).
2. Definir **qué pasa con el usuario anónimo**: es la sub-decisión que queda viva dentro de
   la decisión tomada (cuota por dispositivo · límite anónimo más bajo · login forzado al
   análisis N). Sin esto, el resto no se puede implementar.
3. Tabla de cuotas + RPC de descuento **atómico** (nunca read-modify-write desde Node).
4. RLS: escritura solo por service role; el cliente lee su propia fila, nunca la escribe.
5. Comportamiento al agotar la cuota: código de respuesta y payload de estado que el
   cliente pueda renderizar como paywall (§4.2).
6. Decidir si un hit servido 100% desde caché consume crédito — hoy declarado "a confirmar"
   en `03-agente-backend.md`.
7. Tests de QA que hoy no existen (ver `04-agente-qa.md`).

Esquema propuesto y detalle de implementación: `03-agente-backend.md` (§ Lógica de Cuotas),
que es el dueño del contrato. Ver §8 B-1.

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

⚠️ El roster es propuesta de `AUDITORIA_SETUP_AGENTICO.md`. **`architect` y `nutrition` no
existen todavía**: hoy la nutrición está repartida de hecho entre backend, data-ai y etl —
y repartido de hecho es sin dueño. Es el único rol cuyo error llega al usuario como un
consejo de salud equivocado, no como un bug.

**Regla de dominios exclusivos:** dos agentes nunca tocan el mismo archivo en paralelo, y
ningún agente edita un artefacto del que no es dueño — se lo pide al dueño.

---

## §8 — Bloqueantes activos

Ordenados por costo de seguir sin resolverlos.

| # | Bloqueante | Estado | Quién decide |
|---|---|---|---|
| **B-1** | 🟡 **C-02 — DECIDIDO (Jere, 28/8/2026): el lookup va CON CUOTA** (§4.3). La contradicción está cerrada; queda el gap de implementación | Endpoint público, cero cuotas ✅ | **Decidido.** Sub-decisión viva: qué pasa con el anónimo. Implementa backend, testea qa |
| **B-2** | 🔴 **C-11** — el motor **emite puntaje sin entender la etiqueta**: 1.453 productos con 0% de cobertura, casos "Excelente" entre ellos (§6.4 C) | Medido 28/8 ✅ · sin gate | nutrition define el umbral · architect dónde vive · backend implementa |
| **B-3** | 🔴 **C-10** — cola de curaduría de **8.991 términos** que se calcula y se tira (§6.5) | ✅ `audit-scores.ts` → `CURATION_QUEUE` | nutrition (clasifica) · backend (imprime) |
| **B-4** | 🔴 **C-08** — el criterio documentado (4 componentes ponderados) **no es el motor v2.1** (§2.2) | ✅ contra `constants.ts` | nutrition + orchestrator: qué se corrige, el doc o la expectativa |
| **B-4b** | 🔴 **C-09 — NOVA sigue vivo, pero no en el puntaje.** Se ingiere de OFF/OBF, se persiste en `products.nova_group`, lo mergea el ETL, `audit-scores.ts` lo usa como **señal de calidad** (NOVA 4 puntuando Excelente = flag), y el copy de la app se lo nombra al usuario — pero el motor v2.1 **no lo lee para el puntaje** ✅ (`steps.ts`/`pipeline.ts`/`rubric/`: cero referencias). **No se borra de la doc**: se documenta el hecho exacto. La limpieza de código, si se decide, es tarea aparte (§2.4) | ✅ mapeado 28/8 | Producto (Jere): si NOVA se le sigue diciendo al usuario, se sostiene; si no, sale del copy Y de la doc |
| ~~**B-5**~~ | ✅ **C-07 cerrado (28/8/2026).** La cascada externa ya no se documenta como camino de request en ningún archivo del set ni en el `README.md` del servidor (§5.3) | Verificado por grep en los 8 agentes + `CONTEXT.md` + READMEs | — |
| **B-6** | 🔴 Migraciones que **se corren a mano en el SQL Editor** de Supabase — `013_score_nullable.sql` y `014_product_search_trgm.sql` están marcadas NO APLICADAS en su propio archivo ✅. No hay forma automática de saber qué esquema está vivo | devops + architect |
| **B-7** | ⚠️ **Umbral del sello a 70** — decidido, ~40 productos afectados, ticket aparte; hoy sigue derivado de `TIERS` ✅. Cuando se aplique, se cambia **en `constants.ts` y en ningún otro lado** | orchestrator (prioriza) |
| **B-8** | ⚠️ Redis puede servir puntajes viejos: el prefijo de clave **no está versionado** por versión del motor ✅ (`redisService.ts`) | data-ai propone · backend aplica |
| **B-9** | ⚠️ Sin `Dockerfile`, sin config de despliegue, sin `engines.node` en `package.json` ✅. Rate limit en memoria: con N instancias el límite real es N veces el nominal | devops |
| **B-10** | ⚠️ Sin observabilidad conectada (Sentry/Datadog). El contrato de logging está escrito; no tiene a dónde reportar | devops + backend |
| **B-11** | ⚠️ Los octógonos se calculan con umbrales **nunca contrastados contra el texto del decreto** (§2.5), y el propio archivo lo advierte ✅ | nutrition |
| **B-12** | ⚠️ **Sin dueño de la nutrición** (§7). Es la causa raíz de B-2, B-3, B-4 y B-11, no un ítem más de la lista | Jere: crear el rol o asumirlo |
| **B-13** | 🔴 **C-14 — el copy in-app le miente al usuario** (§1.6): `HelpScreen.tsx` describe el motor v2 y la cascada retirada. Es deriva doc↔código que salió del repo y llegó a la pantalla. **Es cambio de código, no de documentación** — no se corrige desde el setup agéntico | ✅ `HelpScreen.tsx` → FAQs *"¿Por qué no encuentra mi producto?"* y *"¿Cómo se calcula el puntaje?"* | ux redacta el copy nuevo · mobile lo implementa. Bloqueado por B-4/B-4b: no se puede describir el motor hasta cerrar qué se dice de NOVA |
| **B-14** | 🟡 **La Fase 2 del plan está a medias y nadie lo anotó.** Las 8 dependencias sin usar **ya se eliminaron** ✅ (no están en `package.json`, cero usos). Siguen pendientes: `expo-image` instalada con cero imports ✅, y React Query ausente ✅ | Verificado 28/8 | mobile |

---

## §9 — Changelog

> **Único escritor: el Orquestador.** Un cambio de este documento se registra acá con
> fecha, qué sección cambió y contra qué se verificó. Una decisión de arquitectura además
> se registra como ADR en `BITACORA_DECISIONES.md`; acá va la línea de que se registró.

| Fecha | Cambio | Verificado contra |
|---|---|---|
| 2026-08-28 | Creación. §1–§8 armados desde `AUDITORIA_SETUP_AGENTICO.md`, `DICCIONARIO_DOMINIO.md` (ya corregido) y `tareas/FTG-001`. Números de §6 tomados de FTG-001 sin recalcular | `~/fitogenix-server` `main` `a0428bd` · `~/fitogenix-native` `main` |
| 2026-08-28 | Contradicciones nuevas encontradas en la verificación de esta sesión: **C-07** (cascada retirada, docs desactualizados), **C-08** (composición del score describe v2), **C-09** (rol de NOVA), **C-10** (cola de curaduría descartada), **C-11** (puntaje sin cobertura). Todas en §8 | `productLookupService.ts` · `scoring/constants.ts` · `scripts/audit-scores.ts` |
| 2026-08-28 | **Decisión de Jere aplicada:** C-02 pasa de 🔴 abierto a 🟡 decidido — el lookup va con cuota. §4.3 reescrito con el estado de hoy y la lista de 7 ítems que faltan para que sea ✅; §8 B-1 actualizado. La sub-decisión del usuario anónimo queda viva dentro de la decisión | `src/routes/products/lookup.ts` (sigue público) |
| 2026-08-28 | **Convención de marcas ampliada a cuatro:** se suma 🟡 (decidido, no implementado) a ✅/⚠️/🔴. ⚠️ = no verificado; 🟡 = verificado como ausente y ya decidido | — |
| 2026-08-28 | **Tres huecos del SSOT cerrados** (autorizados por Jere): §1.6 estado real de pantallas y features · §5.7 selección de modelo de IA · §5.8 stack del cliente. **Ninguna sección existente se renumeró** — los punteros `§X` de los 8 agentes siguen válidos | `fitogenix-native` `b7715b8` · `claudeService.ts` |
| 2026-08-28 | **C-09 mapeado, no cerrado:** NOVA se ingiere, se persiste, lo usa `audit-scores.ts` como señal de calidad y se le nombra al usuario, pero el motor no lo lee. B-4 se desdobla en B-4 (C-08) y B-4b (C-09) | `steps.ts`/`pipeline.ts` · `audit-scores.ts` (chequeos `nova_group === 4` / `=== 1`) · `HelpScreen.tsx` |
| 2026-08-28 | **C-07 cerrado.** Corregido en `00-orquestador.md` (reescrito), `02-agente-frontend.md` (reescrito), `03`, `06` y el `README.md` de `fitogenix-server` — que documentaba la cascada como *la* arquitectura y decía "Unit tests (119)" cuando hay 27 archivos y ~345 casos | grep en los 9 documentos + `productLookupService.test.ts` |
| 2026-08-28 | **C-14 nuevo (B-13):** el copy de `HelpScreen.tsx` describe el motor v2 y la cascada retirada. Primer caso de deriva que llegó al usuario final. **C-15 nuevo (B-14):** la poda de dependencias de la Fase 2 ya se hizo sin registrarse | `HelpScreen.tsx` · `fitogenix-native/package.json` |
| 2026-08-31 | **Convención de citas al código:** archivo + símbolo o cita textual, nunca número de línea. Se convirtieron los 10 punteros con línea del set vivo. Encontrado al aplicarla: `ENGINE_VERSION` se citaba como `ftgEngine.ts:24` y vive en `scoring/constants.ts:24` — archivo equivocado, número correcto, error invisible durante tres días. Los rangos de línea quedan permitidos solo en reportes fechados | `HelpScreen.tsx` · `ProfileScreen.tsx` · `ingredientData.ts` · `audit-scores.ts` · `scoring/constants.ts` |

### Pendiente inmediato (fuera de este documento)

**Poda de los 8 agentes a punteros §X.** Este documento tenía que existir primero. Cada
agente pierde su `## El producto: Fitogenix`, su copia del stack y su copia de las bandas,
y en su lugar cita `CONTEXT.md §1`, `§5`, `§3`. Es la cura de C-06 — la duplicación en
ocho lugares que causó C-01 y C-03.
