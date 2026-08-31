# NUTRICION.md — SSOT del criterio nutricional de Fitogenix

> **Qué es.** La fuente única de verdad **del criterio nutricional**: qué dice la ciencia,
> qué dice la norma, y con qué evidencia. Complementa a `CONTEXT.md`, no lo reemplaza.
>
> **Qué NO es.** No es un espejo del código. **Ningún umbral vigente se transcribe acá**:
> los números viven en `scoring/constants.ts` y `scoring/seals.ts` y se citan por puntero.
> Si un umbral vive en los dos lados ya perdimos — es la causa raíz de C-01, que puso las
> bandas mal en tres documentos a la vez.
>
> **Punteros:** las secciones son `§N1`, `§N2`… con `N` de nutrición, para que nunca se
> confundan con las `§X` de `CONTEXT.md`.
>
> **Dueño:** el Agente de Nutrición (`09-agente-nutricion.md`). Único escritor.
>
> **Cómo se lee cada afirmación** — misma convención que `CONTEXT.md`, más una marca nueva:
>
> | Marca | Significa |
> |---|---|
> | ✅ | Verificado contra fuente primaria **citada en `§N7`**. |
> | 📄 | Verificado contra fuente **secundaria** (prensa, divulgación). Vale menos que ✅ y se dice. |
> | ⚠️ | Declarado en el código o en un documento del setup, sin contrastar contra fuente. |
> | 🟡 | Decidido, no implementado. |
> | 🔴 | Abierto. No lo resuelve un agente por criterio propio. |
>
> **Sesión de verificación:** 2026-08-31, contra `~/fitogenix-server` `main` `415577c`.

---

## §N1 — Qué evalúa Fitogenix, y qué no

**Fitogenix evalúa productos, no personas.** ✅ `CONTEXT.md §1.4`.

El criterio se aplica a un envase con su lista de ingredientes y su panel nutricional. **No
hay consejo dietario, no hay condiciones de salud, no hay recomendación individual.** Un
puntaje alto no es "esto te hace bien"; es "este producto, según nuestro criterio
declarado, tiene una lista de ingredientes mejor que la mayoría".

Esta sección existe porque un agente que se llama "nutrición" invita a cruzar ese límite, y
cruzarlo convierte a Fitogenix en algo que no es y que además no está habilitado a ser.

---

## §N2 — Las dos capas, y por qué no se pueden mezclar

Fitogenix produce **dos cosas distintas** sobre el mismo producto, y confundirlas es el
error nutricional más caro que puede cometer:

| | Los octógonos (§N3) | El puntaje Fitogénico (`CONTEXT.md §2`) |
|---|---|---|
| Qué es | Una **advertencia legal** definida por el Estado | Un **criterio propio** de la marca |
| Quién lo define | Ley 27.642 / OPS | Fitogenix |
| Puede verificarlo el usuario | **Sí**, mirando el envase ✅ `CONTEXT.md §2.5` | No |
| Si nos equivocamos | El usuario ve un octógono que el paquete no tiene | Discrepamos, y es opinable |

**El octógono tiene que coincidir con el envase.** No con lo que a Fitogenix le parece
nutricionalmente correcto: con lo que la ley obliga a imprimir. Es el único dato del
producto que el usuario puede contrastar, y ahí no hay margen para tener razón por
nuestra cuenta.

El puntaje, en cambio, **sí puede ser más exigente que la ley.** Es una postura de marca,
está declarada, y es legítima mientras sea explícita.

> 🔴 **N-1 — Hoy las dos capas comparten un solo cálculo.** `computeWarningSeals()` produce
> los octógonos que se le muestran al usuario **y** alimenta `sealPenalty()`, que resta en
> el puntaje ✅ (`scoring/steps.ts` → `applyNutrition`). Mientras la ley y el criterio
> coincidan, no se nota. Desde las disposiciones de 2024 (§N5) **pueden divergir**, y ahí un
> solo cálculo no puede servir a los dos. Ver §N6.

---

## §N3 — Los octógonos: qué exige la norma argentina

**Nutrientes críticos de la Ley 27.642** ✅: azúcares **añadidos**, grasas saturadas,
grasas totales, sodio y calorías. Más **leyendas precautorias** para edulcorantes y cafeína.

**No existe octógono de grasas trans.** ✅ La ley no la incluye entre los nutrientes
críticos. Es una diferencia deliberada con el modelo de OPS, que sí la contempla (§N4).

**Excepciones — Artículo 7** ✅. La ley remite explícitamente al perfil de OPS y exceptúa:

- alimentos **in natura** e **ingredientes culinarios** sin procesos de adición de
  nutrientes críticos;
- alimentos para propósitos médicos específicos;
- suplementos dietarios;
- fórmulas para lactantes y niños de hasta 36 meses.

**Etapas de aplicación** ✅: primera etapa a los 9 meses de vigencia (15 para PyMEs),
segunda a los 18 (24 para PyMEs).

> 🔴 **N-2 — No está verificado si las dos etapas tenían umbrales distintos o solo plazos
> distintos.** En el modelo chileno, del que Argentina toma la forma, las etapas endurecían
> los valores. Acá no pudimos confirmarlo: el **Anexo II del Decreto 151/2022** no está
> disponible en ninguna de las fuentes accesibles — el manual oficial de `argentina.gob.ar`
> bloquea la descarga automática y el sitio de ANMAT devuelve 403. **Es la fuente que
> falta**, y de ella depende §N6/N-3.

---

## §N4 — El modelo de perfil de nutrientes de OPS

Es la base científica que la ley adopta ✅ (Ley 27.642, art. 7).

**Umbrales** ✅ — *no se transcriben como valores vigentes de Fitogenix; los vigentes están
en `scoring/seals.ts`. Acá figuran como la fuente contra la cual se contrastan:*

| Nutriente crítico | Criterio OPS |
|---|---|
| Azúcares libres | ≥ 10 % de la energía total |
| Grasas totales | ≥ 30 % de la energía total |
| Grasas saturadas | ≥ 10 % de la energía total |
| Grasas trans | ≥ 1 % de la energía total |
| Sodio | ≥ 1 mg por kcal |

**Ámbito de aplicación** ✅: el modelo se aplica a alimentos **procesados y
ultraprocesados**, y **no** a los no procesados o mínimamente procesados — verduras,
legumbres, granos, frutas, **frutos secos**, carne, pescado, **leche** y **huevos**.

Esto es lo mismo que dice el Artículo 7 (§N3), con otro vocabulario: **el criterio de
exención es el nivel de procesamiento**, no la composición.

> **Consecuencia para NOVA.** La clasificación NOVA es exactamente el eje que decide esa
> exención: NOVA 1 (in natura o mínimamente procesado) y NOVA 2 (ingrediente culinario)
> quedan fuera; NOVA 3 y 4, dentro. `products.nova_group` ya se ingiere y se persiste ✅
> (`CONTEXT.md §2.4`). **Este es un uso concreto y legalmente fundado del campo que el
> proyecto decidió sostener** (ADR-004), y hasta hoy no estaba identificado. Ver §N6/N-4.

---

## §N5 — Las disposiciones de 2024, y por qué no son un detalle técnico

📄 El **26/12/2024**, ANMAT publicó las **Disposiciones 11378/2024 y 11362/2024**, que
**no cambiaron los umbrales** sino la **base de cálculo**: los nutrientes críticos se
computan sobre los ingredientes **agregados deliberadamente** en la elaboración, excluyendo
los intrínsecos de la materia prima.

Ejemplos que dan las fuentes: la mermelada declara solo el azúcar incorporado, no el de la
fruta; los frutos secos dejan de llevar sello por su grasa natural; la manteca no lo lleva
si no se le agregó sodio.

> 🔴 **N-3 — Esto está marcado 📄, no ✅, y la distinción importa.** Está tomado de prensa
> que resume las disposiciones. **No leímos el texto de las disposiciones.** Antes de mover
> una línea de código por esto, hay que leerlas.

> 🔴 **N-4 — El cambio está judicializado y profesionalmente cuestionado.** 📄 Hay
> demandas contra ANMAT por "flexibilizar los criterios" y colegios de nutricionistas
> advirtiendo retrocesos. **Esto convierte a §N2 en una decisión de producto, no técnica:**
> si la norma vigente y el criterio de OPS divergen, Fitogenix tiene que elegir **cuál
> sigue cada capa**. La recomendación del agente es la de §N2 — el octógono sigue a la
> norma porque el usuario lo contrasta con el envase; el puntaje puede seguir a la ciencia
> porque es criterio declarado — pero **quien elige es producto (Jere), no el agente.**

---

## §N6 — Estado del código contra estas fuentes

Contrastado el 2026-08-31 contra `fitogenix-server` `415577c`.

### Lo que está bien, y conviene no tocar

| Qué | Veredicto |
|---|---|
| Umbrales de azúcares, grasas saturadas, grasas totales y sodio | ✅ **Coinciden exactamente con OPS** (§N4). `scoring/seals.ts` |
| Ausencia de octógono de grasas trans | ✅ **Correcto.** La ley no lo incluye (§N3). El propio archivo lo dice, y ahora está verificado |
| `hasAddedSugar` en el sello de azúcares | ✅ **Correcto y bien fundado.** La ley habla de azúcares **añadidos**; el panel declara totales. `scoring/steps.ts` |
| La excepción de alimentos sin nutrientes críticos añadidos | ✅ **Existe.** `scoring/steps.ts` → `applyNutrition` corta antes de calcular sellos. No es un hueco |

### Lo que queda abierto

> 🔴 **N-5 — El umbral de calorías no está verificado.** `scoring/seals.ts` usa 275 kcal/100
> (sólidos) y 70 kcal/100 (líquidos). **No figuran en el modelo de OPS**, que no define un
> criterio de energía: son un agregado de la norma argentina, y su valor está en el Anexo II
> que no pudimos abrir (§N3/N-2). **Es el único de los cinco umbrales sin respaldo citable.**

> 🟡 **N-6 — La excepción se implementa por proxy, no por el criterio legal.** El código
> exime cuando *"ningún ingrediente tiene impacto"*; la ley exime a *"in natura e
> ingredientes culinarios sin adición de nutrientes críticos"*. Se parecen y coinciden en
> los casos típicos, pero no son la misma regla: un ingrediente culinario cuyo impacto la
> tabla marca distinto de `none` **queda dentro** cuando la ley lo deja fuera.
> **`nova_group` permitiría chequearlo directamente** (§N4). La tarea es medir cuánto
> divergen las dos reglas sobre el catálogo real **antes** de cambiar nada: si divergen en
> pocos productos, el proxy se queda y se documenta; si divergen en muchos, se corrige.

---

## §N7 — Fuentes

Toda afirmación ✅ de este documento se apoya en una de estas. Las 📄 se apoyan en prensa y
están marcadas como tales en el lugar donde se usan.

| # | Fuente | Consultada | Para qué |
|---|---|---|---|
| F1 | **Ley 27.642** — texto oficial, InfoLEG · `servicios.infoleg.gob.ar/infolegInternet/anexos/360000-364999/362577/norma.htm` | 2026-08-31 | Nutrientes críticos · excepciones del art. 7 · etapas |
| F2 | **OPS — "PAHO defines excess levels of sugar, salt and fat"** · `paho.org/en/news/19-2-2016-paho-defines-excess-levels-sugar-salt-and-fat-processed-food-and-drink-products-0` | 2026-08-31 | Los cinco criterios del perfil · ámbito de aplicación |
| F3 | **Decreto 151/2022** — Boletín Oficial · `boletinoficial.gob.ar/detalleAviso/primera/259690/20220323` | 2026-08-31 | Remisión al perfil de OPS. **No contiene el Anexo II** |
| F4 | **Infobae, 26/12/2024** — cambios de ANMAT 📄 | 2026-08-31 | Base de cálculo agregado vs. intrínseco |
| F5 | **Infoalimentos** — etiquetado frontal 📄 | 2026-08-31 | Mención de un umbral alternativo de sodio (≥300 mg/100 g) **no implementado y no verificado** |

### 🔴 Fuentes que faltan, en orden de urgencia

1. **Anexo II del Decreto 151/2022** — los umbrales oficiales. Sin esto, N-5 y N-2 no se
   cierran. `argentina.gob.ar` bloquea la descarga automática: hay que bajarlo a mano y
   dejarlo en `nutricion/fuentes/`.
2. **Disposiciones ANMAT 11378/2024 y 11362/2024** — texto completo. Sin esto, N-3 no pasa
   de 📄.
3. **Modelo de Perfil de Nutrientes de OPS**, publicación completa (`iris.paho.org`) — para
   el fundamento científico de cada umbral, no solo el número.
