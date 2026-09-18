# FTG-002 — La pantalla de Guía contradice al motor, y transcribe sus umbrales

> **Estado:** especificada, NO iniciada.
> **Origen:** hallazgo del guard de frontera (`orquestacion/fitogenix/guards.py`) al barrer
> los 136 archivos `.ts/.tsx` de los dos repos, 2026-09-01. Verificado contra el call site
> el 2026-09-03.
> **Por qué es el primer ticket del pipeline:** toca las tres puntas del contrato, obliga a
> que el arquitecto decida antes de que alguien implemente, y necesita copy de UX. Es la
> prueba de que el handoff funciona, sobre un defecto real y no un ejercicio.

---

## Por qué existe

`fitogenix-native/src/screens/GuideScreen.tsx` declara su propia constante `TIERS` con los
cuatro cortes, los colores, los CTA y el sello por banda. Es una copia hecha a mano de
`fitogenix-server/src/domain/product/scoring/constants.ts` → `TIERS`.

Son **dos defectos**, y el segundo no es de higiene.

### A · La copia (`CONTEXT.md §3.1`)

`§3.1` dice que los umbrales **no se transcriben en ningún documento, prompt, copy ni test**.
Los colores (`#16a34a`, `#84cc16`, `#f97316`, `#dc2626`) y los CTA (*"Lo recomendamos"*,
*"Buena opción"*, *"Consumilo con consciencia"*, *"No lo recomendamos"*) coinciden **literal**
con `TIERS`. Es una cuarta copia de la misma tabla.

`§3.1` existe porque esto ya pasó, y el propio código lo cuenta: *"Antes había tres criterios
distintos para la misma decisión —75/50/25 acá, 70/50 en `resolveProductStatus`, 75/25 en el
sello— y un producto de 72 salía 'Bueno' con sello 'Fitogénico'"* ✅ comentario de `TIERS`.

### B · La contradicción, que es lo grave

El defecto que `§3.1` describe **no se arregló del todo: sobrevivió en el cliente.**

| Banda | `GuideScreen` le dice al usuario | Lo que el motor hace ✅ |
|---|---|---|
| 75–100 EXCELENTE | `badge: 'FITOGÉNICO'` | `FITOGÉNICO` — coincide |
| **50–74 BUENO** | **`badge: 'FITOGÉNICO'`** | **`null` — sin sello** |
| 25–49 MODERADO | `badge: null` | `null` — coincide |
| 0–24 MALO | `badge: 'NO FITOGÉNICO'` | `NO FITOGÉNICO` — coincide |

✅ `scoring/presentation.ts` → `getSello`: `>= EXCELLENT_FROM` da `FITOGÉNICO`,
`< BAD_BELOW` da `NO FITOGÉNICO`, **y todo el medio da `null`**. `resolveProductStatus`
coincide por construcción y llama *"Consumo consciente"* a esa franja.

O sea: **la pantalla cuya única función es explicarle al usuario cómo funciona el puntaje le
dice que un producto de 60 lleva el sello Fitogénico, y la pantalla de producto no se lo
muestra.** El usuario escanea, lee 60 / BUENO, y no encuentra el sello que la guía le
prometió. Es exactamente el bug que `constants.ts` dice haber arreglado, un repo más allá.

### C · La omisión (`CONTEXT.md §3.3`)

`NO_DATA_TIER` no está en `GuideScreen`. La guía enumera cuatro bandas; la app tiene **cinco**
— *"Sin datos suficientes"* existe, se muestra ✅ (`getScoreLabel(null)`) y `§3.3` es explícita
en que es una banda propia, no un cero. La pantalla que explica el sistema omite el caso que
más explicación necesita.

---

## Por qué no es un fix de una línea

El cliente **no puede** importar `TIERS`: `CONTEXT.md §5.2` (regla absoluta de frontera) y
`§3.4` (solo el backend recalcula) lo prohíben, y el guard lo rechaza.

Lo que el contrato ya le da al cliente es la presentación **de un producto**:
`scoreLabel`, `scoreColor`, `tagline` ✅ `fitogenix-native/src/lib/contracts/product.ts`.
La guía necesita la **tabla entera**, y hoy ningún endpoint la devuelve.

Eso convierte esto en una **decisión de contrato cross-repo**, no en una tarea de UI. Es de
`08-agente-arquitecto.md`.

---

## Handoff

| # | Agente | Qué decide o hace |
|---|---|---|
| 1 | **architect** | Cómo llega la tabla de bandas al cliente sin romper `§5.2`. Enumera las **tres puntas** del contrato y qué pasa con cada una, aunque en dos sea "no cambia". Si hay endpoint nuevo, entra al contrato de API en el mismo commit (`§5.6`) |
| 2 | **backend** | Expone lo que el contrato declare, derivado de `TIERS` y `NO_DATA_TIER` — **sin un segundo literal en ningún lado** |
| 3 | **ux** | El copy de las cinco bandas, incluida la de sin datos. Y el de la franja 25–74, que hoy no tiene nombre en la guía: el motor la llama *"Consumo consciente"* |
| 4 | **mobile** | Borra el `TIERS` local y renderiza lo que llega |
| 5 | **qa** | Que el guard salga limpio y que la guía y la pantalla de producto digan lo mismo para un puntaje de cada banda |

**Escalado a Opus:** sí para `architect` — toca el contrato de producto (`PROPUESTA_grafo_fase2.md` sección 5).

---

## Criterio de aceptación

```
Dado un producto con puntaje en la franja 25–74
Cuando el usuario abre la pantalla de Guía y después la de ese producto
Entonces las dos dicen lo mismo sobre el sello, y ninguna afirma "FITOGÉNICO"
```

```
Dado el barrido del guard sobre fitogenix-native/src/
Cuando corre verifica_umbrales_no_transcriptos
Entonces GuideScreen.tsx no aparece, y el barrido completo da 0 hallazgos
```

```
Dado un producto sin datos suficientes
Cuando el usuario abre la pantalla de Guía
Entonces la banda "Sin datos suficientes" está explicada, con su color y su mensaje
```

> **2026-09-18 — el criterio A-2 no se puede cumplir arreglando solo `GuideScreen`.**
> El arquitecto, produciendo el contrato de este ticket, encontró dos copias más en el
> cliente, y las dos además **recalculan** (violan `CONTEXT.md §3.4`, no solo `§3.1`):
>
> - ✅ `fitogenix-native/src/screens/HomeScreen.tsx` → `scoreLabel` / `scoreColor`
>   reimplementan los cortes con literales y devuelven `"Sin score"` donde el motor da la
>   banda de sin datos. **Alcanzable:** `HistoryCard` las usa como fallback de
>   `product.scoreLabel ‖ product.scoreColor`.
> - ✅ `fitogenix-native/src/screens/ScanResultScreen.tsx` → `isBad` parte el puntaje por
>   un corte propio para elegir qué grupo de ingredientes destaca.
>
> Lo dejó como **supuesto ⚠️** que el barrido pudiera no verlas, porque no tenía permitido
> leer `orquestacion/`. **Verificado: el supuesto era cierto.** `_ETIQUETA_DE_BANDA` no
> llevaba `IGNORECASE`, así que `HomeScreen.tsx` daba **0 hallazgos** y A-2 habría dado
> verde con el defecto vivo. El guard ya está corregido y hoy lo reporta.
> `ScanResultScreen.tsx` **sigue sin ser detectable** por el barrido (una comparación
> sola, sin etiqueta de banda al lado): se encuentra leyendo, no barriendo.
>
> 🔴 **Decisión abierta (D-2, del orchestrator):** o esos dos archivos entran al alcance
> de FTG-002, o A-2 se reescribe acotándolo a `GuideScreen.tsx`. Como está, es imposible.

---

## Riesgo si no se hace

Es la única afirmación del producto que el usuario puede contrastar **dentro de la misma
app**, en dos toques. Y empeora sola: `§8` **B-7** decidió mover el umbral del sello a 70.
Cuando se aplique en `constants.ts` —que es donde `§3.1` dice que se cambia, "y en ningún
otro lado"— la guía va a seguir diciendo 75, y nadie se va a enterar.

---

## Marcas

| Afirmación | Marca | Fuente |
|---|---|---|
| `GuideScreen` declara `TIERS` propio con los cuatro cortes | ✅ | `fitogenix-native/src/screens/GuideScreen.tsx` |
| La pantalla está viva y es un tab | ✅ | `fitogenix-native/src/app/(tabs)/guia.tsx` → `export default GuideScreen` |
| El motor no da sello entre 25 y 74 | ✅ | `fitogenix-server/src/domain/product/scoring/presentation.ts` → `getSello` |
| El cliente ya recibe `scoreLabel`/`scoreColor`/`tagline` por producto | ✅ | `fitogenix-native/src/lib/contracts/product.ts` |
| Ningún endpoint devuelve la tabla de bandas | ⚠️ | verificado por ausencia en `fitogenix-server/src/routes/`; no se probó contra la API viva |
| Se propone que esto entre a `CONTEXT.md §8` como bloqueante nuevo | 🟡 | lo escribe el **orchestrator**, único escritor de `CONTEXT.md` |
