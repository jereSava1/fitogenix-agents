# Auditoría del setup agéntico — Fitogenix

> Fecha: 28/8/2026 · Alcance: los 8 agentes de `fitogenix-agents/` + `DICCIONARIO_DOMINIO.md`,
> `CONVENCIONES_EQUIPO.md`, `BITACORA_DECISIONES.md`, cruzados contra el código real de
> `fitogenix-server` y `fitogenix-native`.
> Todo lo marcado ✅ se verificó contra el código en esta sesión. Lo ⚠️ no.

## ⚠️ Estado de esta auditoría al 28/8/2026 — leer antes de usar cualquier hallazgo

Este documento es del **28/8/2026 a la mañana** y fue el punto de partida de dos tandas de
trabajo posteriores (`PODA_REPORTE.md` y la realineación del mismo día). **Varios de sus
hallazgos ya están cerrados, y al menos uno era incorrecto en su origen.** No lo cites como
estado vigente: el estado vigente está en `CONTEXT.md §8`.

| Hallazgo | Estado hoy |
|---|---|
| **C-01** — bandas mal en toda la documentación | **Cerrado**, con una corrección al propio hallazgo: la tabla acusaba a `03-agente-backend.md` de tener 85/70/50/25/0, pero esa copia **ya tenía los números correctos** (75/50/25/0, sin banda "Peligroso"). El diccionario sí estaba mal y se corrigió; `00-orquestador.md` los transcribía y hoy apunta a `CONTEXT.md §3` |
| **C-02** — lookup público vs cuotas | **Decidido el 28/8/2026 (Jere): el lookup va con cuota.** Pasó de 🔴 a 🟡 — falta implementarlo. Ver `CONTEXT.md §4.3` y `§8` B-1 |
| **C-03** — agentes citando archivos y tests que no existen | **Cerrado y verificado:** cero citas remanentes a `scoring.ts`, `ftgEngine.test.ts`, `scoring.test.ts` o `ftgEngine.regression.test.ts` en los 8 archivos |
| **C-04** — `02-agente-frontend.md` describe la arquitectura pre-migración | **Cerrado:** el archivo se reescribió completo el 28/8/2026 contra `fitogenix-native` `b7715b8` |
| **C-05** — estado mutable dentro de un system prompt | **Cerrado:** el plan de migración y el checklist fechado salieron de `00-orquestador.md`. Lo abierto vive en `CONTEXT.md §8`, la historia en `BITACORA_DECISIONES.md` |
| **C-06** — contexto de negocio duplicado en los 8 | **Cerrado:** los 8 citan `CONTEXT.md §X` en vez de transcribir |
| §3 — hechos de dominio verificados | **Siguen válidos**, salvo *"416 tests en verde"*, que sigue **sin reproducir**. Conteo estático del 28/8: 27 archivos de test, ~345 casos `it()`. La suite no se pudo correr |
| §4 — el problema de datos sucios | **Sigue válido y sin avanzar.** Nadie corrió la auditoría sobre lo que ya está en la base; la cola de curaduría se sigue calculando y descartando (`CONTEXT.md §8` B-3) |
| §5 — falta un dueño de la nutrición | **Sigue válido.** Es `CONTEXT.md §8` B-12, y la causa raíz de otros cuatro bloqueantes |
| §6 — roster propuesto | **Sin ejecutar:** `architect` y `nutrition` siguen sin existir |
| §7 — plan de acción | Pasos 1, 3, 4 y 5 **hechos**. Paso 2 **decidido**, sin implementar. Pasos 6 (harness LangGraph) y 7 (auditoría de `products`) **sin empezar** |

**Dos hallazgos que esta auditoría no vio**, encontrados al verificar contra el código el
mismo día y hoy en `CONTEXT.md §8`: **C-07** (la cascada `OFF→OBF→Edamam→Claude` seguía
documentada como camino de request diez días después de retirarse) y **C-14** (el copy
in-app le describe al usuario el motor v2 y esa misma cascada — la única deriva que llegó al
usuario final).

**Sobre sus mediciones de tamaño:** la estimación de que los archivos pesan "entre 5,6 KB y
25,5 KB" quedó ~22% por debajo de lo medido después. No se investigó de dónde salió la
diferencia; se reporta.

---

## Resumen ejecutivo

1. **El setup es bueno.** Mejor de lo que suele encontrarse: identidad, responsabilidades
   exclusivas, protocolos y reglas inamovibles por agente, más un formato de reporte
   estructurado que el Orquestador está mandatado a rechazar si no se cumple.
2. **El defecto dominante es la deriva doc↔código.** Los agentes citan archivos y tests que
   ya no existen, y el número central del producto —las bandas del score— está mal en los
   tres documentos que lo declaran.
3. **`DICCIONARIO_DOMINIO.md` contradice al código en el dato más importante del negocio.**
   Es el hallazgo más grave: es el documento que todos los agentes tienen orden de consultar
   antes de asumir.
4. **El problema de datos sucios ya está 80% construido.** Existen heurísticas, validación de
   plausibilidad y jobs de auditoría/fix. Lo que falta no es tooling, es haberlo corrido y
   convertido los hallazgos en constraints.
5. **Falta un dueño de la nutrición.** Ninguno de los 8 agentes es responsable de la
   corrección de valores, claims regulatorios ni de la rúbrica de scoring.

---

## 1. Contradicciones encontradas

### 🔴 C-01 — Las bandas del score están mal en TODA la documentación

Tres fuentes, tres respuestas distintas, y la que manda es la que nadie actualizó.

| Fuente | Excelente | Bueno | Moderado | Malo | Peligroso |
|---|---|---|---|---|---|
| **CÓDIGO** — `scoring/constants.ts` `TIERS` ✅ | **≥ 75** | **50–74** | **25–49** | **0–24** | — |
| `DICCIONARIO_DOMINIO.md` | ≥ 85 | 70–84 | 50–69 | 0–49 | — |
| `00-orquestador.md` y `03-agente-backend.md` | ≥ 85 | 70–84 | 50–69 | 25–49 | 0–24 |

El sello también: el diccionario dice FITOGÉNICO ≥ 70 / NO FITOGÉNICO < 50. El código dice
`EXCELLENT_FROM = 75` y `BAD_BELOW = 25`.

**Por qué importa más que un typo:** el `DICCIONARIO_DOMINIO.md` se autodeclara fuente de verdad
terminológica y dice literalmente *"Si un término se usa distinto en algún lado, ese lugar está
mal, no este documento"*. Un agente que siga esa instrucción va a "corregir" el código correcto
contra un documento equivocado.

Encima, el propio `constants.ts` documenta que este problema YA pasó una vez:

> *"Antes había tres criterios distintos para la misma decisión —75/50/25 acá, 70/50 en
> `resolveProductStatus`, 75/25 en el sello— y un producto de 72 salía 'Bueno' con sello
> 'Fitogénico'."*

Se arregló en el código con el motor v2.1 y se dejó la documentación atrás.

**Acción:** el código gana. Actualizar el diccionario y los dos agentes, y agregar la regla de
que las bandas se citan por puntero a `constants.ts`, nunca se transcriben.

---

### 🔴 C-02 — El endpoint de lookup es público, pero el modelo freemium exige atribución

- `00-orquestador.md`, sección de negocio: *"Cada análisis consumido debe poder atribuirse a un
  usuario para el descuento de crédito — esto condiciona el diseño de auth y de los endpoints."*
- `03-agente-backend.md`: *"`POST /products/lookup` NO tiene `requireAuth` … **Excepción
  deliberada, no bug** … No agregues auth obligatoria a este endpoint sin que sea una decisión
  de producto explícita del Orquestador — rompería el flujo anónimo."*

Las dos afirmaciones no pueden ser ciertas a la vez cuando se implemente el plan Free de 10
análisis/mes. Nadie la flagueó porque las cuotas todavía no existen (✅ verificado: no hay
`user_quotas` ni ninguna referencia a créditos en `src/` ni en `migrations/`).

**Acción:** es una decisión de producto tuya, no técnica. Las opciones son cuota por dispositivo
para anónimos, límite anónimo más bajo sin cuenta, o forzar login al análisis N. Hasta que se
decida, queda marcada 🔴 en el contexto, no resuelta por criterio de un agente.

---

### ⚠️ C-03 — Los agentes citan archivos y tests que no existen

| El doc dice | La realidad ✅ |
|---|---|
| `src/domain/product/scoring.ts` (orquestador, backend) | No existe. Es el **directorio** `scoring/` con 24 archivos |
| `ftgEngine.test.ts` (orquestador, backend) | **No existe** |
| `ftgEngine.regression.test.ts` (orquestador, backend) | **No existe** |
| `scoring.test.ts` (orquestador, backend) | **No existe** |
| — | Los tests reales del motor son `scoring/*.test.ts`: `rules`, `calibration`, `robustness`, `ledger`, `presentation`, `regression`, `cleaning`, `invariants`, `seals` (9) + `nutrientPlausibility.test.ts` |

El motor se refactorizó a v2.1 (ver `MOTOR_V21_INFORME.md`) y la documentación de agentes no
siguió. Es la misma clase de error que el PR de PampaGrow encontró en sus `CLAUDE.md`: ejemplos
que no matchean el código.

---

### ⚠️ C-04 — `02-agente-frontend.md` describe la arquitectura PRE-migración como si fuera el presente

Ese documento afirma que en `fitogenix-native` existen:

- `src/domain/product/ftgEngine.ts` — *"~900 líneas, CERO tests — NO TOCAR"*
- `src/domain/product/lookupProduct.ts`, `scoring.ts`
- `src/infrastructure/` llamando directo a OFF, Claude y Supabase
- `src/app/api/` con rutas `+api.ts`

Todo eso migró al servidor en la Fase 1. El propio `00-orquestador.md` lo confirma y agrega que
los stubs vacíos de `ScoreBreakdownSheet.tsx` y `ftgEngine.ts` quedaron pendientes de `git rm`.
El agente Frontend está operando con un mapa viejo.

---

### ⚠️ C-05 — Estado mutable dentro de un system prompt

`00-orquestador.md` contiene el checklist "Estado actual de la migración" con notas fechadas
(18/8), SHAs de commits y pendientes menores, más la instrucción *"actualizá esta sección"*.

Un changelog viviendo dentro de un prompt se desactualiza el primer día y nadie se entera. Ese
contenido pertenece a un documento de estado con dueño único y registro de cambios, no al prompt
que define quién es el agente.

---

### ⚠️ C-06 — El contexto de negocio está duplicado en los 8 agentes

Cada archivo abre con su propia sección `## El producto: Fitogenix` y su propia versión del
stack y las bandas del score. Ocho copias del mismo hecho es la causa raíz de C-01 y C-03: el día
que algo cambia, hay que acordarse de ocho lugares.

Es también la razón de que los archivos pesen entre 5,6 KB y 25,5 KB: el agente de Backend carga
la escala de severidad de ingredientes que no usa, y el de UX carga el TTL de Redis.

---

## 2. Veredicto por documento

| Documento | Veredicto | Motivo |
|---|---|---|
| `00-orquestador.md` | **Adaptar — partir en tres** | El rol es sólido. El plan de migración, el estado y el contexto de negocio salen a documentos propios |
| `01-agente-ux.md` | **Conservar** | El bloque de a11y (WCAG AA, no-solo-color, 44pt, Dynamic Type) y las pautas TEA son de lo mejor del set. Portables tal cual |
| `02-agente-frontend.md` | **Reescribir** | Describe la arquitectura anterior a la Fase 1. Es el más desactualizado de los ocho |
| `03-agente-backend.md` | **Adaptar** | Excelente contenido técnico. Corregir punteros muertos y bandas. Candidato a partirse: 25,5 KB mezcla contrato de API, schema, cascada, cuotas y observabilidad |
| `04-agente-qa.md` | **Conservar** | El más chico (5,6 KB) y de los más efectivos. *"No escribís features: las rompés"* y el veredicto estructurado se portan sin cambios |
| `05-agente-datos.md` | **Conservar** | Dueño único de prompts, presupuesto de tokens, y el razonamiento sobre invalidación por `ENGINE_VERSION` es correcto y está verificado contra el código |
| `06-agente-etl-data.md` | **Conservar — es el mejor del set** | El pipeline `products_staging` → merge campo a campo → gate de completitud → enriquecimiento, con `run_id`/`merged_into` para trazabilidad, ya resuelve el problema de datos por diseño |
| `07-agente-devops.md` | **Conservar** | Verificado contra el repo, y el hallazgo del rate limit en memoria con N instancias es real y no trivial |
| `DICCIONARIO_DOMINIO.md` | **Conservar la forma, corregir los números** | La estructura (definición estricta + "no confundir con" + reglas) es ideal para un SSOT. Las bandas y el sello están mal (C-01) |
| `CONVENCIONES_EQUIPO.md` | **Conservar** | Sin objeciones. Prohibición de `.catch(() => {})`, micro-commits, secretos server-only, plantilla de PR |
| `BITACORA_DECISIONES.md` | **Conservar** | Formato ADR ya en uso, referenciado desde las migraciones |

---

## 3. Hechos de dominio verificados contra el código

| Hecho | Marca |
|---|---|
| `ENGINE_VERSION = 'ftg-rubric-v2.1'` (`ftgEngine.ts:24`) | ✅ |
| Bandas reales: 75 / 50 / 25 / 0 (`scoring/constants.ts` `TIERS`) | ✅ |
| `EXCELLENT_FROM = 75`, `BAD_BELOW = 25` — sello y estado salen de ahí | ✅ |
| `null` es una banda legítima: "Sin datos suficientes", no se coerciona a 0 | ✅ |
| 27 archivos de test en `src/` + `scripts/etl/` | ✅ |
| Stack server: Fastify 5, `@anthropic-ai/sdk` 0.55, `@supabase/supabase-js` 2.108, `@upstash/redis` 1.38, TypeScript ~6.0.3, Vitest 4.1.9 | ✅ |
| Sin `engines.node` en `package.json` (riesgo señalado por DevOps) | ✅ |
| 13 migraciones; varias documentadas como **NO APLICADAS**, se corren a mano en el SQL Editor de Supabase | ✅ |
| Cuotas freemium: **cero implementación** — no hay `user_quotas`, ni créditos, ni RPC | ✅ |
| `nutrientPlausibility.ts` vive en `domain/` y lo comparten el ETL y `enrichWithAI` | ✅ |
| 18 scripts npm, de los cuales 10 son de ETL/calidad | ✅ |
| "416 tests en verde" (nota del 18/8 en el orquestador) | ⚠️ no reproducido en esta sesión |

---

## 4. El problema de datos sucios: lo que ya existe

Descripción del problema: *datos de locaciones en lugar de nutrientes, filas vacías*.

Eso **ya está detectado y nombrado en el código** ✅. `scripts/etl/lib/qualityHeuristics.ts`
tiene `BOILERPLATE_PATTERNS` que capturan exactamente ese síntoma:

```
elaborado por/en · establecimiento · industria argentina · RNE/RNPA
parque industrial · ruta N · Cno. · código postal argentino (CPA) · URLs
```

Es decir: la dirección de la fábrica aterrizando en `ingredients_text`, un error típico de carga
comunitaria en Open Food Facts. La heurística además exige **dos señales** antes de marcar, para
no dar falsos positivos con listas cortas legítimas ("Agua, sal").

Y `src/domain/product/nutrientPlausibility.ts` valida rangos fisiológicos por 100 g/ml, con el
razonamiento correcto escrito en el propio archivo:

> *"un valor que Claude inventa fuera de rango es el MISMO tipo de error que uno que llegó
> corrupto de una fuente externa, así que usan la misma validación, una sola vez, acá"*

**Inventario de lo que ya existe:**

| Pieza | Estado |
|---|---|
| `qualityHeuristics.ts` + tests — boilerplate, brand en el nombre | ✅ existe |
| `nutrientPlausibility.ts` + tests — rangos físicos | ✅ existe |
| `completeness.ts` + tests — gate de datos vs gate de scoring | ✅ existe |
| `merge.ts` + tests — merge campo a campo, prioridad por fuente | ✅ existe |
| `staging.ts` + tests — `products_staging`, `run_id`, `merged_into` | ✅ existe |
| `jobs/auditDataQuality.ts` (`npm run etl:audit-quality`) | ✅ existe |
| `jobs/fixDataQuality.ts` (`npm run etl:fix-quality`) | ✅ existe |
| `qualityAI.ts` + tests — verificación asistida por IA | ✅ existe |
| **Un reporte de haberlo corrido, con números** | 🔴 **no existe** |
| **Constraints en la base que impidan que vuelva a entrar** | 🔴 **no existe** |
| **Criterio versionado de "qué es un dato sucio"** | 🔴 **no existe** |

**Conclusión:** el ETL guarda bien la puerta de entrada. Nadie auditó lo que ya está adentro.
La primera tarea del arquitecto no es diseñar nada nuevo — es **correr `etl:audit-quality` sobre
`products`, triar la salida, y convertir el resultado en constraints y en una definición
versionada de dato sucio**.

---

## 5. Lo que falta: dueño de la nutrición

Ninguno de los 8 agentes es responsable de:

- que un valor nutricional sea **correcto** (no solo plausible)
- la rúbrica del criterio Fitogénico: qué penaliza, cuánto, y con qué fundamento
- los claims regulatorios (CAA/ANMAT en Argentina; IARC/EFSA/JECFA como referencia, ya citados
  en el diccionario pero sin dueño)
- la clasificación de `ingredientData.ts` y sus alias
- qué constituye un dato sucio, en términos de dominio y no de patrón de texto

Hoy eso está repartido de hecho entre Backend (que implementa), Datos (que ajusta prompts) y ETL
(que detecta patrones). **Repartido de hecho = sin dueño.** Y es el único agente cuyo error
llega al usuario como un consejo de salud equivocado, no como un bug.

---

## 6. Roster propuesto

| Agente | Origen | Cambio |
|---|---|---|
| **orchestrator** | `00` | Partir: rol → prompt · plan y estado → documento con dueño |
| **architect** | 🆕 | No existe hoy. Dueño del esquema, las constraints y los ADRs. Primera tarea: la auditoría de datos |
| **backend** | `03` | Corregir punteros, sacar el contexto duplicado |
| **mobile** | `02` | Reescribir contra la arquitectura post-Fase 1 |
| **nutrition** | 🆕 | Dueño de valores, rúbrica, claims y definición de dato sucio |
| **data-ai** | `05` | Sin cambios de fondo |
| **etl** | `06` | Sin cambios de fondo. Sumar el gate de calidad medible |
| **qa** | `04` | Sin cambios de fondo |
| ux · devops | `01` · `07` | Conservar, invocar bajo demanda |

Son 9 con dos bajo demanda. Es mucho para tu equipo, pero el recorte no lo decido yo sin saber
quién trabaja hoy en el proyecto además de vos.

---

## 7. Plan de acción propuesto

| # | Paso | Por qué en ese orden |
|---|---|---|
| 1 | **Corregir C-01** en diccionario, orquestador y backend | Es el número central del producto y hoy está mal en todos lados |
| 2 | **Decidir C-02** (lookup público vs cuotas) | Es decisión de producto y condiciona el diseño de auth |
| 3 | Crear el SSOT único con punteros `§X` y marcas ✅/⚠️/🔴 | Elimina la causa raíz de C-01, C-03 y C-06 |
| 4 | Reescribir `02-agente-frontend.md` | Es el que más miente hoy |
| 5 | Sacar plan y estado del prompt del orquestador | C-05 |
| 6 | Portar el harness de LangGraph con el roster nuevo | Automatiza el handoff que hoy es copiar y pegar |
| 7 | **Primer ticket real: auditoría de `products`** | Valida el setup con trabajo de verdad |

---

## Anexo — qué NO se verificó en esta sesión

- El contenido de `BITACORA_DECISIONES.md` (16,5 KB) — solo se confirmó su existencia y que las
  migraciones la referencian (ADR-002).
- Los dos `.docx` de negocio.
- La suite de tests corriendo (`npm test`) — no se ejecutó.
- El estado real de la base de Supabase: qué migraciones están aplicadas, cuántas filas de
  `products` hay, y cuántas están sucias. **Requiere credenciales y es el primer ticket.**
