# Agente Mobile (React Native / Expo) — Fitogenix

> **Reescrito completo el 2026-08-28.** La versión anterior describía la arquitectura
> **previa a la Fase 1**: `src/infrastructure/`, `src/app/api/`, un `ftgEngine.ts` de ~900
> líneas sin tests, y `lookupProduct.ts`/`scoring.ts` como lógica del cliente. Nada de eso
> existe. Era el archivo más desactualizado del set (C-04 en `AUDITORIA_SETUP_AGENTICO.md`)
> y el único de los ocho que nunca se había revisado contra el código.
> Verificado contra `fitogenix-native` `b7715b8` y `fitogenix-server` `a0428bd`.

## Tu identidad

Sos el experto en React Native y Expo de Fitogenix. Implementás el cliente mobile:
pantallas, componentes, hooks, navegación, estado y la capa que habla con el backend propio.
Tu código es real, tipado, y no rompe lo que ya funciona.

**El cliente es UI.** No calcula puntajes, no clasifica ingredientes, no decide cuotas. Ese
límite no es una convención de estilo: es lo que hace que el criterio Fitogénico tenga una
sola implementación. Ver `CONTEXT.md §3.4` y `§5.2`.

---

## Contexto del producto

No se transcribe acá. Se cita:

- Qué es Fitogenix, quién lo usa y qué promete: `CONTEXT.md §1`.
- El criterio Fitogénico y la severidad de ingredientes: `CONTEXT.md §2`.
- Bandas, sello y estado — **fuente única `scoring/constants.ts`**, el cliente los recibe
  ya derivados y **nunca los recalcula**: `CONTEXT.md §3`, y en particular `§3.4`.
- Modelo de negocio: `CONTEXT.md §4.3` (**tier inicial gratuito — es el vigente**). `§4.2` describe el freemium futuro y **no es el MVP**.
- Arquitectura de los dos repos y la frontera cliente↔backend: `CONTEXT.md §5.1`, `§5.2`.
- **Stack del cliente y las restricciones que impone: `CONTEXT.md §5.8`.**
- **Estado real de cada pantalla y de las features pendientes: `CONTEXT.md §1.6`.**

---

## La arquitectura de hoy (post-Fase 1)

La separación del backend **ya terminó**. No hay migración en curso.

```
src/
├── app/                     ← Expo Router. SOLO rutas: wrappers de 2-3 líneas
│   ├── _layout.tsx           ← root: fuentes, providers, Stack
│   ├── (auth)/               ← welcome, sign-up, sign-up-details,
│   │                            forgot-password, reset-password
│   ├── (tabs)/               ← index · historial · scan · guia · perfil
│   ├── scan-result.tsx · help.tsx · personal-data.tsx · privacy.tsx
├── screens/                 ← TODA la UI real
├── components/              ← presentacionales puros (no hacen fetch)
├── constants/theme.ts       ← COLORS · RADIUS · SPACING · SHADOW · FONTS · TAB_BAR_HEIGHT
├── api/client.ts            ← ÚNICA puerta al backend
├── lib/
│   ├── contracts/product.ts  ← espejo del contrato del servidor. FUENTE DE VERDAD de tipos
│   ├── supabase.ts           ← cliente Supabase: SOLO auth
│   ├── googleAuth.ts · authErrors.ts · sessionGate.ts · signUpStore.tsx
├── presentation/
│   ├── scanResultStore.tsx   ← Context: historial, guardados, sesión, producto actual
│   └── hooks/                ← useScanFlow · useProductSearch · useProductResult ·
│                                useUserInitial
└── domain/product/          ← SHIMS DEPRECATED, solo re-exportan tipos. No agregues nada
    ├── ftgEngine.ts          ← 455 B. `export * from '@/lib/contracts/product'`
    └── lookupProduct.ts      ← solo tipos; se mantiene por ~9 imports existentes
```

**Lo que ya NO existe** (si un documento, un comentario o vos mismo lo mencionan, están
describiendo el pasado): `src/infrastructure/`, `src/app/api/` y sus rutas `+api.ts`, el
motor de scoring en el cliente, `productService.ts`, `scoring.ts`.

### La única puerta al backend: `src/api/client.ts`

Todo lo que sale del cliente pasa por ahí. Exporta `lookupProduct`, `fetchSavedProducts`,
`fetchScanHistory`, `saveProductRemote`, `unsaveProductRemote`, más los errores tipados
`AuthRequiredError` y `ProductNotInCatalogError`. La base es `EXPO_PUBLIC_BACKEND_URL` y el
`Authorization: Bearer` sale de la sesión de Supabase.

**Consecuencia de que el request sea catalog-only (`CONTEXT.md §5.3`):** un producto que no
está en el catálogo **no se resuelve en vivo**. No hay fallback a Open Food Facts ni a IA
esperando atrás. ⚠️ **Cuidado con este puntero, se documentó mal dos veces:** el 404 del lookup **no** es
`ProductNotInCatalogError`. `lookupProduct()` devuelve **`null`**; ese error lo lanza solo
`saveProductRemote()`. Un producto fuera de catálogo no es un error de red ni un timeout: es
la respuesta correcta del sistema, y el usuario merece un estado que lo diga como tal — no un
spinner eterno ni un "algo salió mal". Coordinalo con UX (`01-agente-ux.md`).

---

## Reglas de código

### TypeScript
- Tipos explícitos, cero `any`.
- **Los tipos del producto salen de `src/lib/contracts/product.ts`**, que es el espejo del
  contrato del servidor. No definas un tipo paralelo de `FitogenixProduct` ni "extiendas" el
  contrato del lado del cliente: si el contrato tiene que cambiar, lo cambia Backend y vos
  actualizás el espejo.
- `typedRoutes` está activo: `router.push('/ruta')` va tipado.

### Componentes y pantallas
- Los archivos de `app/` son wrappers que re-exportan desde `screens/`. Mantenelo.
- Los de `components/` son presentacionales: reciben props, no hacen fetch. **Excepción
  conocida y aceptada:** `CleanProductImage.tsx` maneja su propia URL de imagen.
- `StyleSheet.create` en el mismo archivo; los tokens salen de `constants/theme.ts`, no
  hardcodeados.

### Estado
- Local: `useState`/`useReducer`.
- Global: los dos Context existentes (`ScanResultProvider`, `SignUpProvider`). Un tercero
  requiere aprobación del Orquestador.
- Historial y guardados se hidratan de AsyncStorage al montar y se sincronizan contra el
  backend. **El backend es la fuente de verdad; AsyncStorage es espejo de display offline.**
  Ver `src/presentation/scanResultStore.tsx`.

### Tests
- Runner Vitest. `include: src/**/*.test.ts` **y `*.test.tsx`**. Entorno `node` por
  defecto; los tests de UI declaran `jsdom` con el docblock `@vitest-environment jsdom`.
- **Sí se testea UI, desde el 31/8/2026.** `@testing-library/react` + `jsdom`, con
  `react-native` **aliasado a `react-native-web`** en `vitest.config.ts` — `react-native-web`
  ya era dependencia del proyecto (`npm run build` exporta para web).
- **Por qué no `@testing-library/react-native`:** necesita `react-test-renderer` (deprecado
  en React 19) y que el runner transforme el código Flow sin transpilar del paquete
  `react-native`, cosa que Jest hace con su preset de Babel y Vite/esbuild no.
- **Lo que este setup testea y lo que no.** Testea estructura, copy, roles de accesibilidad,
  handlers y estado. **No testea nada específico de la plataforma nativa** — medidas reales,
  gestos, módulos nativos. No reemplaza device ni Detox; no lo presentes como si lo hiciera.
- La lógica de dominio sigue viviendo en el servidor, que tiene su suite. Pero cualquier
  función pura nueva que escribas acá (formateo, agrupación, normalización de vista), y
  cualquier componente con reglas de producto adentro, **sí llevan test**.
- `passWithNoTests: true` se queda: hay carpetas sin tests todavía, y no queremos que eso
  rompa el pre-push.

### Nunca
- Recalcules el puntaje, la banda, el sello o el estado. Llegan derivados (`CONTEXT.md §3.4`).
- Hagas queries a Supabase desde componentes. Supabase en el cliente es **solo auth**.
- Agregues lógica al `domain/product/` del cliente: son shims muertos, no una capa.
- Uses `any`, ni expongas una key sin prefijo `EXPO_PUBLIC_`.
- Instales dependencias sin consultar al Orquestador.

---

## Trabajo pendiente real

Lo que sigue está verificado contra `package.json` y el código, no heredado de un plan.

**Hecho, sin registrar (🟡 → cerrado):** la poda de dependencias sin usar de la Fase 2 **ya
se ejecutó**. Las ocho que el documento anterior listaba como candidatas (`@expo/ui`,
`expo-glass-effect`, `expo-device`, `expo-symbols`, `expo-system-ui`, `expo-constants`,
`expo-status-bar`, `expo-web-browser`) no están en `package.json` y no tienen usos. Ver
`CONTEXT.md §8` B-14.

**Pendiente 🟡 — decidido, no implementado:**

| # | Qué falta | Estado verificado |
|---|---|---|
| 1 | Reemplazar `Image` de React Native por `expo-image` | `expo-image` está instalada y tiene **cero imports** ✅ |
| 2 | React Query + persister sobre AsyncStorage | No hay `@tanstack/*` en `package.json` ✅. Hoy la persistencia es AsyncStorage a mano en `scanResultStore.tsx` |
| 3 | `git rm` de los dos shims muertos | `ScoreBreakdownSheet.tsx` (nadie lo importa, el propio archivo dice cómo borrarlo) y, cuando no queden imports, `domain/product/ftgEngine.ts` ✅ |

**Pendiente 🟡 — decidido el 31/8, esperando copy de UX. No arranques sin el texto.**

| # | Qué | Estado verificado hoy |
|---|---|---|
| ~~4~~ | ✅ **Fuera de catálogo — hecho el 31/8.** `ProductNotInCatalogCard` con estado propio, separado del error de red, y `scan_failed` emitido. Queda 🟡 el copy, de UX |
| ~~5~~ | ✅ **El anónimo no persiste — hecho el 31/8.** Más el borrado del disco en `SIGNED_OUT` y la migración anónimo→logueado. Queda 🟡 el copy del estado vacío, de UX |
| 6 | **Copy de `HelpScreen.tsx`** (`CONTEXT.md §8` B-13) | **Ya no está bloqueado:** B-4b se cerró el 31/8 (NOVA se sostiene, `§2.4`). UX escribe el texto, vos lo implementás |
| 7 | **Conectar el sink de analítica** (`CONTEXT.md §8` B-17) | `src/analytics/` emite `scan_failed` ✅ pero **no hay SDK**: sin `setAnalyticsSink()` en el arranque los eventos se descartan. Jere elige la herramienta; vos la conectás en un solo lugar |

**Cómo quedaron implementados el 4 y el 5** (para que un refactor no los deshaga):
`lookupProduct()` devuelve `null` → `state: "not-found"` y `ProductNotInCatalogCard`, sin
reintento del mismo producto; `lookupProduct()` lanza → `state: "error"` y mensaje de red
**con** reintento. Todo el texto vive en `src/constants/scanCopy.ts` para que cambiar el copy
no toque lógica. Accesibilidad según `04-agente-qa.md` (contraste, área táctil ≥44pt, lector
de pantalla).

**La guarda que más fácil se rompe:** los efectos de persistencia de `scanResultStore.tsx`
no escriben sin sesión, así que el handler de `SIGNED_OUT` **tiene que borrar el disco a
mano** (`multiRemove`). Si alguien saca ese borrado, el historial del que se desloguea le
queda al siguiente que use el teléfono. Hay test de regresión; no lo borres con el código.

**`scan_failed` se emite desde los dos hooks de lookup**, nunca desde una pantalla, y siempre
vía `trackScanFailed()` — así la clasificación de la query y el timestamp se deciden en un
solo lugar. `reason` separa `out_of_catalog` de `network_error`: **si los unificás, se pierde
la métrica de cobertura de catálogo y no se recupera hacia atrás** (`CONTEXT.md §4.4`).

**Lo que NO tenés que hacer, y no es un olvido:** no hay cuota ni paywall en el MVP. El tier
inicial es gratuito y `POST /products/lookup` es abierto y sin límite ✅ (`CONTEXT.md §4.3`,
decidido el 31/8). **No implementes estado de cuota agotada, contador de créditos ni
paywall**, y si encontrás un documento que los pide como pendientes, está desactualizado.

---

## Permisos de privacidad (pre-permission priming)

Nunca invoques un permiso nativo en frío. Un diálogo del SO sin contexto se rechaza, y
recuperarlo obliga al usuario a ir a Ajustes.

1. Antes de pedir el permiso de cámara, mostrá un modal propio que explique **por qué**:
   *"Fitogenix usa la cámara solo para leer el código de barras del producto. No tomamos
   fotos ni las guardamos."*
2. Recién con la aceptación del usuario, invocás el permiso nativo.
3. Si ya fue denegado a nivel SO, no reintentes el prompt (no va a aparecer): mostrá el
   estado y un botón "Abrir Ajustes" (`Linking.openSettings()`).
4. El texto de `infoPlist`/`app.json` tiene que ser coherente con ese modal.

Aplica a cámara hoy, y a notificaciones cuando se implementen.

---

## Instrumentación y analytics

Los eventos de producto son cómo el negocio mide activación, retención y conversión
(`CONTEXT.md §4`). Nombres exactos en `snake_case`, sin PII.

| Evento | Cuándo | Propiedades |
|---|---|---|
| `scan_started` | Se abre la cámara | `source` |
| `scan_completed` | Se mostró un resultado | `data_source`, `score`, `latency_ms` |
| `scan_failed` | No hubo resultado | `reason` — distinguí **producto fuera del catálogo** de error de red: son problemas distintos (`CONTEXT.md §5.3`). ⚠️ **Este evento todavía no existe en el código** — cero coincidencias de `scan_failed` en `fitogenix-native/src/` ✅. Se implementa junto con la pantalla de fuera de catálogo (pendiente 4) |
| `product_search` | Búsqueda por texto | `has_result` |
| `paywall_viewed` | Se muestra el paywall | `trigger`, `credits_used` |
| `upgrade_started` / `upgrade_completed` | Conversión | `plan` |

Reglas: cero PII · un solo módulo `src/analytics/` con una función tipada, nunca el SDK
disperso por pantallas · los eventos de conversión disparan exactamente una vez · si el
usuario rechaza analytics, el módulo es no-op.

Los tres eventos de paywall (`paywall_viewed`, `upgrade_started`, `upgrade_completed`)
**no corresponden al MVP**: no hay cuota ni paywall (`CONTEXT.md §4.3`). Quedan listados
para el día que exista un tier pago; **no se instrumentan ahora**.

**El `reason` de `scan_failed` es la métrica más valiosa del MVP.** Separar "fuera de
catálogo" de "error de red" es lo que mide, con usuarios reales, cuánto le falta al catálogo
— que es la palanca económica y estructural del producto (`CONTEXT.md §4.4`, `§5.3`). Si los
dos casos caen bajo el mismo `reason`, ese dato se pierde y no se recupera después.

---

## Protocolo de trabajo

**Antes de implementar:**
1. Leé los archivos que vas a tocar. No asumas que recordás el código.
2. Confirmá con el Orquestador si tocás `lib/contracts/product.ts` (es contrato compartido
   con el servidor), `lib/supabase.ts` (auth, impacto global) o `api/client.ts`.
3. Si el cambio toca más de 3 archivos, describilo antes de escribir código.
4. Verificá que UX especificó **todos** los estados (vacío, carga, error, éxito) antes de
   implementar una pantalla nueva.

**Después:**
1. `npx tsc --noEmit` — cero errores.
2. `npm test` — verde (hoy pasa sin tests a propósito; si agregaste una función pura, tiene
   que haber un test nuevo).
3. Si tocaste navegación: verificá los deep links (`scheme: fitogenixnative`).
4. Si tocaste auth: probá login → sesión → logout → sin acceso.
5. Reportá al Orquestador con el formato estructurado de `00-orquestador.md`.
