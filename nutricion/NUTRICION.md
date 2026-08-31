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

**Los umbrales viven en el Artículo 6 del Decreto 151/2022** ✅, que remite a la **Tabla 1**
de su Anexo I. **Las dos etapas tienen valores distintos**, no solo plazos distintos:

| Nutriente crítico | Primera etapa | **Segunda etapa (vigente)** |
|---|---|---|
| Azúcares añadidos | ≥ 20 % de la energía | **≥ 10 % de la energía** |
| Grasas totales | ≥ 35 % de la energía | **≥ 30 % de la energía** |
| Grasas saturadas | ≥ 12 % de la energía | **≥ 10 % de la energía** |
| Sodio | ≥ 5 mg/kcal **o** ≥ 600 mg/100 g | **≥ 1 mg/kcal *o* ≥ 300 mg/100 g** |
| Calorías — alimentos | ≥ 300 kcal/100 g | **≥ 275 kcal/100 g** |
| Calorías — bebidas | ≥ 50 kcal/100 ml | **≥ 25 kcal/100 ml** |

> ⚠️ **Nivel de confianza de esta tabla, y por qué importa.** Está transcripta de un PDF del
> Anexo I publicado por una editorial jurídica (F6), no del PDF oficial del BORA. **Cuatro
> de las seis filas de la segunda etapa coinciden exactamente con el modelo de OPS** (§N4),
> que es fuente primaria independiente — eso les da respaldo doble. **Las dos filas de
> calorías no lo tienen**, porque OPS no define criterio de energía, y la condición
> alternativa de sodio tampoco. Ver §N6.

**La segunda etapa es la vigente:** primera etapa a los 9 meses de la vigencia (15 para
PyMEs), segunda a los 18 (24 para PyMEs), sobre un decreto de marzo de 2022 ✅.

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

## §N5 — Las disposiciones de diciembre de 2024

> **Corrección del 31/8/2026.** La primera versión de esta sección atribuía el cambio de
> base de cálculo a **las dos** disposiciones. Es falso, y salió de leer prensa en vez del
> texto. Cada una hace algo distinto:

**Disposición ANMAT 11362/2024** ✅ — es la que importa para el criterio. Aprueba el
**Manual de Aplicación** de la Ley 27.642 y el Decreto 151/2022 (Anexo
`IF-2024-135393117-APN-DLEIAER#ANMAT`), sustituye el art. 1 de la Disposición 2673/22 y
deroga sus arts. 2–8 y 10.

- **No cambia los valores de corte** ✅. Remite al artículo 6 del Decreto 151/2022 como
  fuente, sin modificarlo. ANMAT lo dice explícitamente: *"Los valores no se modificaron
  sino que siguen siendo los mismos"* 📄.
- **Sí precisa la distinción intrínseco vs. añadido.** El Manual aclara, por ejemplo, que
  *"no se considera azúcar añadido a los provenientes de frutas y hortalizas (enteras o en
  trozos) frescas, congeladas, desecadas…"* ✅.

**Disposición ANMAT 11378/2024** ✅ — **no toca el criterio nutricional.** Regula
**publicidad, promoción y patrocinio** de productos con al menos un sello, y deroga la
Disposición 6924/22. Es relevante para el negocio, no para el motor.

> 🔴 **N-3 — El efecto real de la precisión intrínseco/añadido está sin medir.** Que el
> Manual "precise" en vez de "sustituir" suena menor, pero las fuentes 📄 lo describen con
> ejemplos de peso: frutos secos que dejan de llevar sello por su grasa natural, manteca
> que no lo lleva si no se le agregó sodio. **No leímos el Manual.** Su Anexo
> (`IF-2024-135393117`) es la fuente que falta.

> 🔴 **N-4 — El cambio está judicializado y profesionalmente cuestionado.** 📄 Hay demandas
> contra ANMAT por "flexibilizar los criterios" y la Fundación Interamericana del Corazón
> advierte que los productos van a llevar **menos sellos de los que deberían**. **Esto
> convierte a §N2 en una decisión de producto, no técnica:** si la norma vigente y el
> criterio de OPS divergen, Fitogenix elige cuál sigue cada capa. La recomendación del
> agente es la de §N2 — el octógono sigue a la norma porque el usuario lo contrasta con el
> envase; el puntaje puede seguir a la ciencia porque es criterio declarado — pero **quien
> elige es producto (Jere), no el agente.**

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

### Contraste completo contra la Tabla 1 (segunda etapa, §N3)

| Umbral | La norma | El código | |
|---|---|---|---|
| Azúcares añadidos | ≥ 10 % E | ≥ 10 % E | ✅ |
| Grasas saturadas | ≥ 10 % E | ≥ 10 % E | ✅ |
| Grasas totales | ≥ 30 % E | ≥ 30 % E | ✅ |
| Sodio | ≥ 1 mg/kcal **o ≥ 300 mg/100 g** | ≥ 1 mg/kcal, **sin la alternativa** | 🟡 **N-5** |
| Calorías — alimentos | ≥ 275 kcal/100 g | 275 | ✅ |
| Calorías — bebidas | ≥ 25 kcal/100 ml | **70** | 🔴 **N-6** |

> 🟡 **N-5 — Al sodio le falta la condición alternativa.** La norma marca el sello con
> `≥1 mg/kcal` **o** `≥300 mg/100 g`; `seals.ts` implementa solo la primera. El efecto es
> **sub-marcar**: un producto salado y muy calórico diluye su ratio y escapa al sello que el
> envase sí lleva. Dos fuentes secundarias independientes coinciden en la condición (F5, F6)
> y **ninguna primaria la contradice** — pero OPS tampoco la incluye, así que **no se toca el
> código hasta tener el anexo del BORA.**

> 🔴 **N-6 — El umbral de calorías de bebidas no coincide, y el conflicto es interesante.**
> La Tabla 1 dice `≥25 kcal/100 ml`; el código usa `70`. Setenta **no es ninguna de las dos
> etapas** argentinas (50 y 25): es el valor final del modelo **chileno**. Parece un valor
> tomado del país equivocado.
>
> **Pero el código no está solo en su creencia.** `seals.test.ts` tiene un caso escrito por
> el equipo —una gaseosa cola de 42 kcal/100 ml que espera **solo** `EXCESO EN AZÚCARES`—
> que codifica una observación de góndola: una gaseosa real no lleva octógono de calorías.
> Con el umbral en 25, sí lo llevaría.
>
> **Entonces una de estas tres es falsa, y no sé cuál:** la transcripción de la Tabla 1, el
> umbral del código, o la observación del test. Resolverlo **no requiere leer nada más**:
> ANMAT publicó una **calculadora oficial** (F7). Cargar una gaseosa de 42 kcal/100 ml y ver
> si devuelve el sello de calorías lo cierra en dos minutos, empíricamente. **Ese es el
> siguiente paso, y es más barato que conseguir el anexo.**

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
| F1 | **Decreto 151/2022** (reglamenta la Ley 27.642) — InfoLEG `362577` · `servicios.infoleg.gob.ar/infolegInternet/anexos/360000-364999/362577/norma.htm` | 2026-08-31 | Nutrientes críticos · excepciones del art. 7 · etapas · el art. 6 como fuente de los umbrales |
| F2 | **OPS — "PAHO defines excess levels of sugar, salt and fat"** · `paho.org/en/news/19-2-2016-…` | 2026-08-31 | Los cinco criterios del perfil · ámbito de aplicación (procesados y ultraprocesados) |
| F3 | **Decreto 151/2022** — Boletín Oficial `259690/20220323` | 2026-08-31 | Identificadores de los anexos: `IF-2022-27565868-APN-MS` (I) e `IF-2022-24456831-APN-DNAIENT#MS` (II) |
| F4 | **Disposición ANMAT 11362/2024** — InfoLEG `407673` | 2026-08-31 | Aprueba el Manual de Aplicación · no cambia valores · precisa intrínseco vs. añadido |
| F5 | **Disposición ANMAT 11378/2024** — BORA `318799/20241226` | 2026-08-31 | **Publicidad, no criterio.** Deroga la Disp. 6924/22 |
| F6 | **Anexo I del Decreto 151/2022** (PDF de editorial jurídica) · `aldiaargentina.microjuris.com/wp-content/uploads/2022/03/ANX_-Anexo-1-Decreto-151-2022.pdf` | 2026-08-31 | **La Tabla 1 con los valores de las dos etapas.** No es el PDF del BORA — ver la advertencia de §N3 |
| F7 | **Calculadora oficial de ANMAT** — "Sistema de Sellos y Advertencias Nutricionales" (SIFEGA) | pendiente | **Oráculo empírico.** Resuelve N-6 sin leer normativa |
| F8 | Chequeado · Infobae · Infoalimentos · saludables.com.ar 📄 | 2026-08-31 | Contexto de las disposiciones de 2024 y su cuestionamiento |

### 🔴 Fuentes que faltan, en orden de costo/beneficio

1. **La calculadora de ANMAT (F7).** Lo más barato y lo que más desbloquea: cierra N-6
   empíricamente, sin leer una línea de normativa.
2. **Anexo I del Decreto 151/2022, PDF del BORA** — para confirmar la Tabla 1 contra la
   fuente oficial y cerrar N-5 y N-6. Los anexos se publican en la edición web del BORA;
   el aviso es `259690/20220323` y el documento es `IF-2022-27565868-APN-MS`.
3. **Anexo II del Decreto 151/2022** (`IF-2022-24456831-APN-DNAIENT#MS`) — especificaciones
   técnicas. Menos urgente ahora que sabemos que los umbrales están en el art. 6 y la
   Tabla 1 del Anexo I, no en el II.
4. **Manual de Aplicación** de la Disp. 11362/2024 (`IF-2024-135393117-APN-DLEIAER#ANMAT`)
   — cierra N-3, el alcance real de la precisión intrínseco/añadido.
5. **Modelo de Perfil de Nutrientes de OPS**, publicación completa (`iris.paho.org`) — el
   fundamento científico de cada umbral, no solo el número.

**Cómo se consiguen los del BORA:** el sitio bloquea la descarga automatizada (robots y
403), así que hay que abrir el aviso en un navegador y guardar el PDF de anexos a mano. Una
vez bajados van a `nutricion/fuentes/`, con el nombre del identificador `IF-…`.
