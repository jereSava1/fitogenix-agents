"""
Guards de frontera de Fitogenix — el reemplazo de la `DENY_LIST` de PampaGrow.

La `DENY_LIST` de PampaGrow protege un stack cerrado. Acá no serviría: prohíbe
`supabase`, `prisma`, `flutter` y `react-query`, y Fitogenix corre sobre Supabase
(`CONTEXT.md §5.4`). Copiarla rompería el proyecto en la primera validación.

El problema que Fitogenix sí tiene es otro y ya está escrito en el SSOT:

  · `CONTEXT.md §5.2` — regla absoluta de frontera: el cliente nunca habla directo
    con Supabase, Anthropic, OFF, SerpAPI ni remove.bg. Todo pasa por el backend.
  · `CONTEXT.md §3.4` — solo el backend puede recalcular; el cliente renderiza.
  · `CONTEXT.md §3.1` — los umbrales no se transcriben en NINGÚN documento, prompt,
    copy ni test. Viven en `scoring/constants.ts` y se citan por puntero.
  · `CONTEXT.md §5.6` — un endpoint nuevo se agrega al contrato de API en el mismo
    commit que lo implementa.

Los cuatro son verificables con un grep determinista. Y —el punto entero— **corren
en Python DESPUÉS de que el modelo respondió**, que es el patrón que PampaGrow
adoptó cuando eliminó `TOOLS_BY_AGENT`: un validador atado a una tool el modelo lo
puede llamar y después describir como quiera; corrido después, su resultado es un
hecho del estado y no algo que el modelo pueda declinar ni suavizar.

Calibración (2026-09-01): los tres guards se corrieron contra el árbol real antes de
escribirse. `verifica_frontera_cliente` sale limpio — no queda un solo import de
`ftgEngine` en `fitogenix-native/src/` fuera del propio shim. `verifica_umbrales`
NO sale limpio: ver el test `test_el_caso_real_de_GuideScreen_dispara`.
"""

from __future__ import annotations

import re

# El único archivo donde los umbrales tienen derecho a existir (`CONTEXT.md §3.1`).
FUENTE_DE_UMBRALES = "src/domain/product/scoring/constants.ts"

# El shim deprecado tiene permiso de existir: es `export * from '@/lib/contracts/product'`
# y su propio encabezado dice que se borra cuando no queden imports (`CONTEXT.md §3.4`).
SHIM_DEPRECADO = "src/domain/product/ftgEngine.ts"

# Nombres que `CONTEXT.md §3.1` y `§3.3` declaran propiedad de `constants.ts`.
NOMBRES_DE_UMBRAL: tuple[str, ...] = ("TIERS", "EXCELLENT_FROM", "BAD_BELOW", "NO_DATA_TIER")

# Símbolos del motor. Que el cliente los USE por contrato es correcto; que los DEFINA
# es reimplementar el motor, y es lo que `§3.4` prohíbe.
SIMBOLOS_DEL_MOTOR: tuple[str, ...] = (
    "applyNutrition",
    "computeScore",
    "resolveProductStatus",
    "getSello",
    "getScoreLabel",
    "getScoreTagline",
    "classifyIngredient",
)

# Servicios que el cliente no puede tocar directo (`CONTEXT.md §5.2`). Auth de Supabase
# es la única excepción que la propia regla declara.
SERVICIOS_PROHIBIDOS_EN_CLIENTE: tuple[str, ...] = (
    "@anthropic-ai/sdk",
    "openfoodfacts",
    "serpapi",
    "remove.bg",
)

_LINEA_DE_COMENTARIO = re.compile(r"^\s*(//|#|/\*|\*(?!/)|\*/)")
_DECLARACION = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var|function|class|type|interface|enum)\s+({nombres})\b".format(
        nombres="|".join(NOMBRES_DE_UMBRAL + SIMBOLOS_DEL_MOTOR)
    ),
    re.MULTILINE,
)
# Un corte de banda va de 0 a 100 y no lleva cero a la izquierda. `08–18` es una fecha
# (`2026-08-18`), y hacerlo fallar por eso es el falso positivo que apaga un guard: se
# encontró exactamente así, escaneando `lib/contracts/product.ts` el 2026-09-01.
_RANGO = re.compile(r"(?<![\d.])([1-9]?\d|100)\s*[–—-]\s*([1-9]?\d|100)(?![\d.])")
# Sin `IGNORECASE` hasta el 2026-09-18, y el motor escribe las etiquetas en mayúsculas
# pero el cliente las escribe en capitalizado: `scoreLabel` en `HomeScreen.tsx` devuelve
# "Excelente"/"Bueno"/"Moderado"/"Malo" con los cortes 75/50/25 al lado, y el barrido daba
# **cero hallazgos** sobre ese archivo. El criterio de aceptación A-2 de FTG-002 es
# literalmente "el barrido completo da 0 hallazgos": habría dado verde con el defecto vivo.
# Lo señaló el arquitecto sin poder verificarlo (no tenía permitido leer `orquestacion/`):
# lo dejó como supuesto ⚠️, y el supuesto era cierto.
_ETIQUETA_DE_BANDA = re.compile(r"\b(EXCELENTE|BUENO|MODERADO|MALO|FITOG[EÉ]NICO)\b", re.IGNORECASE)
#: Un corte suelto es un número, y un número solo no significa nada: `NOVA 4`, `omega-6`
#: y `§5` conviven con la palabra "Moderado" en prosa española y no transcriben nada. Se
#: midió el 2026-09-18: buscar "número cerca de etiqueta" a secas daba **4 falsos
#: positivos sobre 113 archivos** del server, todos en descripciones de ingredientes y
#: comentarios. Un guard con 4 falsos positivos es un guard apagado.
#: Por eso el número tiene que estar en una de las dos formas en que un corte SE USA:
_CORTE_COMPARADO = re.compile(r"(?:>=|<=|>|<|===|==|!==|!=)\s*(100|[1-9]?\d)(?![\w.%])")
_CORTE_ARGUMENTO = re.compile(r"\(\s*(100|[1-9]?\d)\s*[,)]")
#: Un rango y una etiqueta de banda son una tabla de cortes solo si están JUNTOS: en el
#: mismo objeto literal, la misma línea, el mismo `it(...)`. A distancia de archivo no
#: significan nada — `product.ts` nombra 'EXCELENTE' en un union de tipos y lleva una
#: fecha en un comentario, y no transcribe ningún umbral.
VENTANA_DE_PROXIMIDAD = 100
#: Un corte suelto —`getScoreLabel(75)` junto a `'EXCELENTE'`— también es una
#: transcripción: `§3.1` habla de umbrales, no de rangos. Pero un número solo es mucho más
#: ambiguo que un rango, así que la ventana es la mitad: tienen que estar pegados.
VENTANA_DE_CORTE_SUELTO = 40

# El cliente puede NOMBRAR a Open Food Facts —el crédito de la fuente de datos es correcto
# y probablemente obligatorio—; lo que no puede es HABLARLE. Solo dispara la forma que es
# una llamada: un import, un require o una URL dentro de un fetch.
_LLAMADA_EXTERNA = re.compile(
    r"""(?:from\s+['"][^'"]*{s}[^'"]*['"]|require\(\s*['"][^'"]*{s}|(?:fetch|axios|get|post)\s*\(\s*[`'"][^`'"]*{s})""",
    re.IGNORECASE,
)
_IMPORT_FTGENGINE = re.compile(r"""from\s+['"][^'"]*ftgEngine['"]|require\(\s*['"][^'"]*ftgEngine""")

#: Excepción explícita y acotada: la suite del propio motor, co-locada con `constants.ts`,
#: fija sus valores a propósito — es su red de regresión, y es donde un cambio no querido
#: TIENE que romper algo. Fuera de ese directorio, un test que fija un corte es una copia
#: más, exactamente lo que `§3.1` prohíbe.
#: 🟡 Esta excepción la escribió el pipeline, no el dueño de `§3.1`. Está pendiente de
#: ratificación por architect/backend: si se rechaza, se borra esta constante y
#: `presentation.test.ts` pasa a ser un hallazgo.
SUITE_DEL_MOTOR = "src/domain/product/scoring/"


class FronteraViolada(ValueError):
    """El cambio cruza una frontera que el SSOT declara absoluta. No es estilo."""


def _sin_comentarios(texto: str) -> str:
    """Saca las líneas que son solo comentario antes de escanear.

    Un escaneo crudo no distingue `import { TIERS }` de `// los TIERS viven en
    constants.ts`. La segunda es una frase SOBRE la regla, y hacer fallar el nodo por
    ella le enseña al equipo que el guard es ruido — que es como termina apagado.
    Los comentarios al final de una línea con código se dejan: esa línea también
    lleva código, y tirar media línea para adivinar intención es peor.
    """
    return "\n".join(l for l in texto.splitlines() if not _LINEA_DE_COMENTARIO.match(l))


def _es_cliente(ruta: str) -> bool:
    return "fitogenix-native/" in ruta or ruta.startswith("src/") and "/screens/" in ruta


def verifica_umbrales_no_transcriptos(ruta: str, contenido: str) -> list[str]:
    """`CONTEXT.md §3.1`: los umbrales viven en un solo archivo y se citan por puntero.

    Devuelve la lista de violaciones. Vacía = limpio.

    La regla existe porque ya pasó: *"Antes había tres criterios distintos para la misma
    decisión —75/50/25 acá, 70/50 en `resolveProductStatus`, 75/25 en el sello— y un
    producto de 72 salía 'Bueno' con sello 'Fitogénico'"* (`constants.ts`, comentario de
    `TIERS`). Una cuarta copia no rompe hoy: rompe el día que B-7 mueva el sello a 70.
    """
    if ruta.endswith(FUENTE_DE_UMBRALES):
        return []
    limpio = _sin_comentarios(contenido)
    fallas: list[str] = []

    for m in _DECLARACION.finditer(limpio):
        nombre = m.group(1)
        if nombre in NOMBRES_DE_UMBRAL:
            fallas.append(
                f"{ruta}: declara `{nombre}` fuera de {FUENTE_DE_UMBRALES}. "
                f"CONTEXT.md §3.1: se cita por puntero, no se transcribe."
            )

    if SUITE_DEL_MOTOR in ruta and ".test." in ruta:
        return fallas

    # Una tabla de bandas: rangos numéricos JUNTO a las etiquetas del producto.
    rangos = set()
    for m in _RANGO.finditer(limpio):
        a, b = int(m.group(1)), int(m.group(2))
        if b <= a:
            continue
        desde = max(0, m.start() - VENTANA_DE_PROXIMIDAD)
        if _ETIQUETA_DE_BANDA.search(limpio[desde : m.end() + VENTANA_DE_PROXIMIDAD]):
            rangos.add(f"{a}–{b}")
    if not rangos:
        # Comparar contra un número y devolver una etiqueta de banda es exactamente la
        # tabla de cortes, escrita como cadena de `if`. Se exigen DOS: un solo `>= N`
        # cerca de una etiqueta es demasiado ambiguo (`bd.nova === 4` al lado de
        # `'Excelente'` no transcribe ningún umbral).
        comparados = set()
        for m in _CORTE_COMPARADO.finditer(limpio):
            desde = max(0, m.start() - VENTANA_DE_CORTE_SUELTO)
            if _ETIQUETA_DE_BANDA.search(limpio[desde : m.end() + VENTANA_DE_CORTE_SUELTO]):
                comparados.add(m.group(1))
        if len(comparados) >= 2:
            rangos |= comparados
        # Pasar el corte como argumento y afirmar la etiqueta —`label(75)` → `'EXCELENTE'`—
        # es la otra forma, y con una alcanza: ahí el número no puede ser otra cosa.
        for m in _CORTE_ARGUMENTO.finditer(limpio):
            desde = max(0, m.start() - VENTANA_DE_CORTE_SUELTO)
            if _ETIQUETA_DE_BANDA.search(limpio[desde : m.end() + VENTANA_DE_CORTE_SUELTO]):
                rangos.add(m.group(1))
    if rangos:
        fallas.append(
            f"{ruta}: transcribe cortes de banda ({', '.join(sorted(rangos))}) "
            f"junto a las etiquetas del producto. CONTEXT.md §3.1: derivar de TIERS."
        )
    return fallas


def verifica_frontera_cliente(ruta: str, contenido: str) -> list[str]:
    """`CONTEXT.md §5.2` + `§3.4`: el cliente es UI. No recalcula y no habla afuera."""
    if not _es_cliente(ruta):
        return []
    limpio = _sin_comentarios(contenido)
    fallas: list[str] = []

    if _IMPORT_FTGENGINE.search(limpio) and not ruta.endswith(SHIM_DEPRECADO):
        fallas.append(
            f"{ruta}: importa `ftgEngine`. Es un shim DEPRECATED que reexporta el contrato; "
            f"importá de `@/lib/contracts/product`. CONTEXT.md §3.4."
        )
    for m in _DECLARACION.finditer(limpio):
        if m.group(1) in SIMBOLOS_DEL_MOTOR:
            fallas.append(
                f"{ruta}: define `{m.group(1)}`, que es motor. El cliente renderiza los "
                f"campos derivados que le llegan, nunca los recalcula. CONTEXT.md §3.4."
            )
    for servicio in SERVICIOS_PROHIBIDOS_EN_CLIENTE:
        patron = re.compile(
            _LLAMADA_EXTERNA.pattern.format(s=re.escape(servicio)), re.IGNORECASE | re.VERBOSE
        )
        if patron.search(limpio):
            fallas.append(
                f"{ruta}: llama a `{servicio}` desde el cliente. Todo pasa por el backend "
                f"propio. CONTEXT.md §5.2 (regla absoluta de frontera)."
            )
    return fallas


_ES_RUTA = re.compile(r"fitogenix-server/src/routes/[^/]+/(?!.*\.test\.)([a-zA-Z]+)\.ts$")
_ES_SCHEMA = re.compile(r"fitogenix-server/src/routes/.*Schema\.ts$")


def verifica_ruta_con_contrato(rutas_tocadas: list[str], *, rutas_nuevas: list[str]) -> list[str]:
    """`CONTEXT.md §5.6`: un endpoint nuevo entra al contrato en el MISMO commit.

    `rutas_nuevas` son los archivos que el cambio crea; `rutas_tocadas`, todos los que
    modifica. Una ruta nueva sin un `*Schema.ts` en el mismo paquete de cambios es un
    endpoint que existe y que el contrato no conoce.
    """
    nuevas = [r for r in rutas_nuevas if _ES_RUTA.search(r)]
    if not nuevas:
        return []
    if any(_ES_SCHEMA.search(r) for r in rutas_tocadas):
        return []
    return [
        f"rutas nuevas sin cambio de contrato en el mismo commit: {', '.join(sorted(nuevas))}. "
        f"CONTEXT.md §5.6."
    ]


def corre_los_guards(archivos: list[tuple[str, str]], *, rutas_nuevas: list[str] | None = None) -> list[str]:
    """Los tres guards sobre un paquete de archivos `(ruta, contenido)`."""
    fallas: list[str] = []
    for ruta, contenido in archivos:
        fallas += verifica_umbrales_no_transcriptos(ruta, contenido)
        fallas += verifica_frontera_cliente(ruta, contenido)
    fallas += verifica_ruta_con_contrato(
        [r for r, _ in archivos], rutas_nuevas=rutas_nuevas or []
    )
    return fallas
