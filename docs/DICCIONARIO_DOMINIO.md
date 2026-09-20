# Diccionario de Dominio — Fitogenix

Glosario canónico del ecosistema Fitogenix. Las definiciones acá son **estrictas y sin ambigüedad**: son la fuente de verdad terminológica para todos los agentes, el código, el copy de la app y la comunicación con negocio. Si un término se usa distinto en algún lado, ese lugar está mal, no este documento.

Regla: ante cualquier duda sobre qué significa un término del dominio, se consulta este archivo antes de asumir. Todo término nuevo del dominio se agrega acá con su definición estricta.

---

## Score Fitogenix

**Definición:** número entero de **0 a 100** que resume la evaluación de salud de un producto según el criterio Fitogénico. Es el resultado final del motor de scoring (`ftgEngine.ts`), calculado a partir de cuatro componentes ponderados y ajustado por gates.

**Cómo se compone:** combinación ponderada de cuatro sub-scores:
- Toxicidad (35%) — evidencia regulatoria/toxicológica (Capa A).
- Nutrición (25%) — perfil nutricional, consciente de NOVA.
- Procesamiento (25%) — grado de procesamiento industrial (NOVA).
- Alineación (15%) — afinidad con la filosofía Fitogenix (Capa B).

Sobre el resultado ponderado se aplican **gates** (anulaciones o techos) por ingredientes críticos (grasas trans industriales, nitritos, aspartamo, carragenina).

**Tiers (bandas de clasificación):**

> ⚠️ **Fuente única de verdad:** `fitogenix-server/src/domain/product/scoring/constants.ts` (`TIERS`, `EXCELLENT_FROM`, `BAD_BELOW`). Los umbrales se citan acá por puntero a ese archivo, nunca se transcriben de memoria en ningún otro documento. Esta tabla ya estuvo mal una vez —85/70/50/25 en vez de 75/50/25/0— y el propio `constants.ts` documenta el incidente en el comentario de `TIERS`: *"Antes había tres criterios distintos para la misma decisión (...) y un producto de 72 salía 'Bueno' con sello 'Fitogénico'"*.

| Score | Tier | Significado |
|-------|------|-------------|
| ≥ 75 | Excelente | Lo recomendamos |
| 50–74 | Bueno | Buena opción |
| 25–49 | Moderado | Consumilo con consciencia |
| 0–24 | Malo | No lo recomendamos |
| `null` (sin score) | Sin datos suficientes | No tenemos datos confiables de este producto |

**No confundir con:** el sello Fitogénico (ver abajo), que es una etiqueta binaria, no el número.

---

## Criterio Fitogénico

**Definición:** el marco de evaluación **propietario de la marca** que determina qué tan alineado está un producto con una alimentación real, mínimamente procesada y de raíz ancestral. Es la filosofía que da identidad a Fitogenix y lo diferencia de un simple lector de etiquetas.

**Estructura de dos capas:**
- **Capa A — Regulatoria/Toxicológica:** evaluación basada en evidencia científica y organismos reguladores (IARC, EFSA, JECFA). Responde "¿hay evidencia de daño?".
- **Capa B — Filosofía Fitogenix:** evaluación según el ideal de alimento integral y ancestral. Responde "¿esto se parece a comida real?". Acá un aceite de semilla industrial puede ser "cuestionable" aunque la Capa A no muestre riesgo regulatorio directo.

**Sello Fitogénico:** etiqueta binaria derivada del Score (`EXCELLENT_FROM` / `BAD_BELOW` en `constants.ts`, ver nota de fuente única arriba):
- **FITOGÉNICO** — Score ≥ 75.
- **NO FITOGÉNICO** — Score < 25.
- Sin sello entre 25 y 74 (bandas Moderado y Bueno).

**Regla de comunicación:** cuando una evaluación de Capa B difiere del consenso regulatorio (Capa A), debe comunicarse explícitamente como "la mirada Fitogenix", no como hecho regulatorio. La honestidad sobre qué capa habla es innegociable.

---

## Severidad de Ingredientes

**Definición:** clasificación de cada ingrediente individual en una de cinco categorías de color, que expresa qué tan problemático es desde la mirada Fitogenix (Capa B, la que se muestra en la UI). Un ingrediente también tiene una severidad de Capa A (regulatoria) usada internamente por el score de toxicidad.

**Escala (Capa B — display):**
| Severidad | Color | Significado |
|-----------|-------|-------------|
| `green` | Verde | Beneficioso / alimento real |
| `yellow` | Amarillo | Neutro o precaución leve / sin clasificar |
| `orange` | Naranja | Cuestionable |
| `red` | Rojo | Problemático / evitar |
| `gray` | Gris | Sin datos |

**Reglas estrictas:**
- La severidad **nunca se comunica solo por color** en la UI: siempre acompañada de texto o ícono (requisito de accesibilidad).
- Un ingrediente tiene dos severidades: `sev` (Capa B, display) y `sevA` (Capa A, regulatoria). Pueden diferir (ej. un aceite de semilla: `red` en Capa B, `green` en Capa A). El código las lleva juntas en un solo registro.
- La clasificación sale de la base de datos de ingredientes (`ingredientData.ts`), por longest-match de alias (español + inglés).
- Un ingrediente no encontrado en la base se marca `yellow` con la nota "Sin clasificación en nuestra base de datos", nunca se inventa una severidad.

**No confundir con:** el Score total (0-100) ni con los sub-scores. La severidad es por ingrediente; el score es del producto.

---

## Clasificación NOVA

**Definición:** sistema de clasificación de alimentos según su **grado de procesamiento industrial**, desarrollado por la Universidad de São Paulo y adoptado por la OMS/OPS. Fitogenix lo usa como uno de sus componentes de score (Procesamiento, 25%) y lo consume desde el campo `nova_group` de Open Food Facts.

**Los cuatro grupos:**
| Grupo | Nombre | Descripción | Aporte al sub-score de procesamiento |
|-------|--------|-------------|--------------------------------------|
| NOVA 1 | Sin procesar / mínimamente procesados | Frutas, verduras, huevos, carne fresca | 95 |
| NOVA 2 | Ingredientes culinarios procesados | Aceites, mantequilla, sal, azúcar (uso culinario) | 75 |
| NOVA 3 | Alimentos procesados | Panes, quesos, conservas — pocos ingredientes añadidos | 45 |
| NOVA 4 | Ultraprocesados | Formulaciones industriales con múltiples aditivos | 10 |

**Reglas estrictas:**
- NOVA mide **procesamiento, no toxicidad ni nutrición**: son ejes distintos. Un NOVA 1 puede ser alto en azúcar natural; un NOVA 4 puede tener bajo sodio. Por eso son componentes separados del score.
- El motor es **NOVA-aware** en nutrición: azúcares y grasas saturadas **naturales** en un NOVA 1 (alimento entero) no se penalizan; en un NOVA 4 sí.
- Cuando OFF no provee `nova_group`, se usa un fallback basado en la cantidad de aditivos declarados, y se comunica como "NOVA no disponible" en el desglose, nunca se inventa un número.

**No confundir con:** el Score Fitogenix (NOVA es solo un insumo de uno de sus cuatro componentes).
