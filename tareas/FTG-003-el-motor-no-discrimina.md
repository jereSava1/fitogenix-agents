# FTG-003 — El motor no discrimina, y no sabemos contra qué estábamos calibrando

**Tipo:** investigación (entregable: dictamen, **no** PR)
**Abre:** `CONTEXT.md §8.21` (B-21)
**Toca:** `§8.2` (B-2) · `§8.12` (B-12) · `§6.3`
**Dueños:** nutrition (criterio) · data-ai (método) · Jere (decide)
**Estado:** 🔴 abierto

---

## El hecho

Medido el 19/9/2026 sobre la base (`§6.3`): **46.232 de 61.359 productos puntuados caen en
la misma banda** ✅, la más angosta de las cuatro. El usuario escanea cinco productos y
cuatro le dicen lo mismo.

Mover el borde de las bandas (ADR-007) mejoró del 82 % al 75 %. Es evidencia de que **los
cortes no son el problema**: el problema es dónde el motor deposita los puntajes.

## Por qué esto es lo más importante abierto

La app promete una cosa: **decirte si un producto es bueno para vos.** Un puntaje que le
pone la misma etiqueta a tres de cada cuatro productos no cumple esa promesa, por bien
escrita que esté la pantalla que lo muestra.

Y hay algo peor que la falta de discriminación: **no tenemos con qué verificar que los
números sean correctos.** B-12 lleva abierto desde el principio — el criterio propio no
tiene fundamento científico escrito. Los coeficientes del motor (`§2` de la rúbrica) se
eligieron por juicio, se calibraron contra una docena de productos armados a mano, y nunca
se contrastaron contra nada externo. **Calibrar contra la intuición se siente igual que
calibrar bien, hasta que alguien pregunta por qué.**

Por eso esto es investigación y no una tarea de código. Tocar un coeficiente antes de tener
una referencia externa sería mover el problema, no resolverlo.

## Alcance

### 1 · Dónde deposita los puntajes el motor, y por qué

- Histograma fino del catálogo, no por banda sino por tramos chicos: dónde exactamente se
  apila la masa. `scripts/score-histogram.ts` ya existe y hace parte de esto.
- Descomponer esa masa por **paso del cálculo**: cuánto de la concentración viene de la
  base, cuánto de las restas por impacto, cuánto del modificador de procesamiento, cuánto
  de los techos. El desglose ya viaja en `breakdown.steps` ✅.
- Cuántos productos llegan a su puntaje por el **mismo camino** — si la mayoría recibe las
  mismas dos o tres deducciones, el motor tiene menos resolución de la que aparenta.
- Efecto de la cobertura: cuánto del puntaje lo explica **no haber entendido la etiqueta**
  en vez de la etiqueta en sí. Es B-2 medido.

### 2 · Contraste contra fuentes externas

Sobre una **muestra representativa y trazable** (no productos elegidos a dedo), comparar
nuestro puntaje contra:

- **Fuentes de datos reconocidas** — Nutri-Score y NOVA ya viajan en el dato de Open Food
  Facts para buena parte del catálogo ✅, así que el contraste no requiere ingesta nueva.
- **Otras apps del rubro**, sobre los mismos productos concretos.

**El objetivo no es coincidir.** Fitogenix declara una postura —alimentación integral y
mínimamente procesada— y el `DISCLAIMER` (`§7`) dice explícitamente que *no* es una medición
médica ni nutricional. Coincidir con Nutri-Score sería, de hecho, una mala señal: estaríamos
reimplementando algo que ya existe.

Lo que hace falta saber es otra cosa: **dónde diferimos, cuánto, y si podemos explicar cada
diferencia con nuestro propio criterio.** Una diferencia explicable es posicionamiento. Una
diferencia que no sabemos explicar es un error que todavía no encontramos.

### 3 · Qué se le muestra al usuario

Jere, 19/9: *"necesitamos certezas, mediciones precisas y sección de información nutricional
e ingredientes clara, medible y 100 % real y comprobada"*.

- Qué afirma hoy la app sobre cómo se calcula el puntaje, y si es cierto. Ya hay una
  contradicción conocida y abierta: `§8.4` (B-4) y `§8.13` (B-13) — el copy in-app describe
  cuatro componentes ponderados que el motor v2.1 **no tiene**.
- Qué parte del panel nutricional y de la lista de ingredientes que mostramos es dato
  verificado de la fuente, qué parte es derivado nuestro, y qué parte es enriquecimiento de
  IA. Hoy eso viaja en `dataSource` y `aiEnriched` ✅ pero no se le dice al usuario.
- Qué habría que poder afirmar, y con qué respaldo, para que la sección sea defendible.

## Criterios de aceptación

```
Dada la distribución del puntaje sobre el catálogo completo
Cuando se descompone por paso del cálculo
Entonces queda escrito qué paso concentra la masa y con qué peso relativo,
        con el número medido y el comando que lo reproduce
```

```
Dada una muestra representativa y trazable del catálogo
Cuando se compara el puntaje de Fitogenix contra las fuentes externas elegidas
Entonces hay una tabla de acuerdo y desacuerdo, y cada familia de desacuerdo
        está explicada por una regla propia del criterio o marcada como 🔴 no explicada
```

```
Dado el dictamen terminado
Cuando se lee la sección de recomendaciones
Entonces propone cambios concretos al motor con su justificación y su costo,
        sin haber cambiado ningún coeficiente todavía
```

```
Dado lo que la app afirma hoy sobre el puntaje y sobre los datos que muestra
Cuando se contrasta contra lo que el motor y el pipeline realmente hacen
Entonces cada afirmación queda marcada ✅ cierta, 🔴 falsa o ⚠️ sin verificar,
        citada por archivo y símbolo
```

## Fuera de alcance

- **Cambiar coeficientes, cortes o el modificador de procesamiento.** Este ticket produce un
  dictamen. El cambio, si va, sale de acá con su propio ADR.
- Reescribir el copy de la app — es B-4 y B-13, y dependen de este resultado.
- El recompute del catálogo (B-19) y la ingesta.
- Cualquier consulta de escritura contra producción.

## Restricciones

- **Los umbrales no se transcriben** en el dictamen (`§3.1`): se citan por puntero.
- **Cualquier query contra la base de producción se pide antes**, aunque sea de solo lectura.
- **Citas al código: archivo + símbolo, nunca número de línea** (`§3.1`, convención del 31/8).
- Las afirmaciones van marcadas ✅ / ⚠️ / 🟡 / 🔴. Una comparación contra otra app que no se
  pudo reproducir es ⚠️, no ✅.
