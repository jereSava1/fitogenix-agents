# FTG-001 — Recuperar la corrección del scoring y el catálogo perdido

> **Estado:** especificada, NO iniciada.
> **Se ejecuta con el setup agéntico ya reorganizado.** Es el primer ticket real
> y funciona como prueba de que el setup sirve: toca cuatro agentes distintos y
> obliga a que el handoff funcione.
> **Fuente de los números:** `npm run audit:scores` + `npx tsx scripts/score-histogram.ts`
> corridos el 28/8/2026 contra el catálogo real (13.737 productos). Todos ✅ medidos.

---

## Por qué existe

El motor hoy **da información incorrecta**, no incompleta. Un producto con jarabe
de maíz de alta fructosa sale "Bueno" porque el motor no lo ve. Eso es peor que
un "Sin datos suficientes": el usuario recibe un aval que no corresponde.

Tres defectos independientes, medidos:

| # | Defecto | Magnitud | Naturaleza |
|---|---|---|---|
| A | Ingredientes reales sin alias en la tabla | `jmaf` **322** · `cloruro de sodio` 132 · `maíz` 82 · `goma xántica` 112 · `oleomargarina` 129 · `polidextrosa` 57 | Puntajes **mal calculados** hoy |
| B | Fragmentos de rotulado tratados como ingredientes | `3 mg/kg` 137 · `2 mg/kg` 124 · `30 mg/kg` 87 · `13 mg/kg` 73 · `CONTIENE` 109 · `rai ins 500ii` 98 · `rai ins 503ii` 55 · `RAI` 57 ≈ **740 apariciones de nada** | Cobertura artificialmente baja → catálogo perdido |
| C | Se emite puntaje sin haber entendido la etiqueta | 6 casos flagueados con `tier=Excelente`; **1.453 productos con 0% de cobertura**; ejemplo real: `89 Excelente cob=0% Té común` | **El más grave.** Aval de marca sobre datos no entendidos |

Contexto del catálogo: 13.737 productos con lista de ingredientes · **9.800 puntuados** ·
**3.937 sin puntaje**, de los cuales `sin-identificar` **2.484 (18,1%)** es el bucket
defectuoso — `fuera-de-alcance` (1.287) es comportamiento correcto, no un bug.

**Términos distintos sin identificar: 8.991. Apariciones totales: 20.290.
El top 40 cubre solo el 18,6%** — es una cola larga, y por eso el orden importa.

---

## El caso testigo: JMAF

`src/domain/product/ingredientData.ts:82`

```ts
{ aliases: ["jarabe de maíz", "corn syrup"],
  b: 'red',
  desc: "Jarabe de maíz de alta fructosa (JMAF). Altamente procesado.
         Vinculado a obesidad y hígado graso." }
```

**"JMAF" figura en la descripción, no en los alias.** Como buena parte del rotulado
argentino usa la sigla, el motor no matchea y 322 productos se puntúan como si no
tuvieran el endulzante que la propia rúbrica marca `red` / *"Hepatotóxico en exceso.
Evitar"*.

El arreglo es una palabra en un array. La lección no: **nadie es dueño de esa tabla**,
y por eso el error vivió sin que ningún test lo detectara. Un test de regresión congela
lo que el motor hace hoy — si hoy está mal, lo congela mal.

---

## Alcance

### Entra
1. **Alias faltantes** de ingredientes reales, empezando por el top de la cola de curaduría.
2. **Limpieza de rotulado** en `scoring/cleaning.ts`: dosis (`N mg/kg`), palabras de
   etiqueta (`CONTIENE`), y separación de código INS de su nombre (`RAI INS 500ii`).
3. **Gate de cobertura mínima** para emitir puntaje: definir el umbral, aplicarlo, y
   decidir qué se le muestra al usuario por debajo de él.
4. **Una regla nueva en `audit-scores.ts`** que detecte baja cobertura en TODAS las
   bandas, no solo en `Excelente`.
5. **Imprimir `CURATION_QUEUE`** en `audit-scores.ts` — hoy se calcula y se descarta.

### No entra
- Mover el umbral del sello a 70 (decidido, 40 productos, ticket aparte).
- Recalcular o migrar filas de `products` (el motor recompone al leer; no hace falta).
- Scrapers, ingesta nueva, ni tocar `products_staging`.
- Renombrar `ingredientData.ts` ni reorganizar la rúbrica.

---

## Criterios de aceptación

```
Given un producto cuyo rotulado dice "JMAF"
When el motor lo analiza
Then el término se identifica como jarabe de maíz de alta fructosa (impacto alto)
 And el puntaje refleja esa penalización

Given un rotulado que contiene "3 mg/kg" o "CONTIENE"
When el motor limpia el texto
Then esos fragmentos no se cuentan como ingredientes no identificados
 And la cobertura del producto sube sin que se agregue ningún alias

Given un producto con cobertura por debajo del umbral definido
When el motor calcula
Then NO emite puntaje, cualquiera sea la banda que habría dado
 And el usuario recibe un estado explícito, no un número

Given `npm run audit:scores`
When termina
Then imprime la cola de curaduría con frecuencias
 And marca baja cobertura en todas las bandas, no solo en Excelente
```

**Medición de cierre obligatoria:** volver a correr `score-histogram.ts` y reportar
el delta en `sin-identificar` (hoy 2.484), en cobertura promedio de los sin puntaje
(hoy 44,3%) y en la cantidad con 0% de cobertura (hoy 1.453).

---

## Reparto de responsabilidades

Esta es la razón por la que FTG-001 es buen primer ticket: **ningún agente puede
resolverlo solo.**

| Agente | Qué le toca | Qué NO le toca |
|---|---|---|
| **nutrition** | Clasificar cada término de la cola: qué sustancia es, qué impacto le corresponde y con qué fundamento. Definir qué cobertura es suficiente para afirmar un puntaje | Escribir código |
| **architect** | Decidir dónde vive el gate de cobertura y si es del motor o del pipeline. ADR | Clasificar sustancias |
| **backend** | Implementar el limpiador, los alias aprobados y el gate. Tests | Decidir qué impacto lleva un ingrediente |
| **qa** | Verificar que ningún puntaje cambió por accidente. Gate de "Listo" | Arreglar |
| **etl** | Volver a medir el catálogo y reportar el delta | Tocar el motor |

**Regla dura de este ticket:** ningún alias entra sin que `nutrition` declare la
sustancia y su fundamento. Un término se agrega porque se sabe qué es, no porque
aparezca mucho. Frecuencia es prioridad, no evidencia.

---

## Riesgos

- **Cambian puntajes en producción.** Es el objetivo, pero exige bumpear
  `ENGINE_VERSION` (Redis cachea el `FitogenixProduct` serializado hasta 7 días) y
  revalidar los goldens de `scoring/regression.test.ts`.
- **Los tests de regresión congelan el error.** Si un golden hoy refleja un puntaje
  calculado sin ver el JMAF, actualizarlo sin mirar es tapar el bug. Cada golden que
  cambie se justifica uno por uno.
- **Subir la cobertura mínima reduce el catálogo puntuado en el corto plazo.** Es
  correcto —mejor no decir nada que decir algo falso— pero es una decisión de producto
  y sale del setup, no de un agente.
- **La cola es larga:** 8.991 términos, top 40 = 18,6%. No hay victoria total; hay que
  fijar un criterio de "hasta acá" y volver periódicamente.
