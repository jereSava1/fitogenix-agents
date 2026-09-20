"""Los guards de frontera, calibrados contra el árbol real del 2026-09-01.

Un guard que da falsos positivos termina apagado, así que cada regla tiene su test de que
**dispara** y su test de que **no dispara** sobre lo que se le parece.
"""

import pytest
from pydantic import ValidationError

from fitogenix.guards import (
    corre_los_guards,
    verifica_frontera_cliente,
    verifica_ruta_con_contrato,
    verifica_umbrales_no_transcriptos,
)
from fitogenix.schemas import ArchivoGenerado, CodigoGenerado, Disciplina

# Extracto textual de `fitogenix-native/src/screens/GuideScreen.tsx`, tal como estaba el
# 2026-09-01. Es una pantalla viva: `src/app/(tabs)/guia.tsx` la exporta como tab.
GUIDESCREEN_REAL = """
const TIERS = [
  { range: '75–100', label: 'EXCELENTE', badge: 'FITOGÉNICO', color: '#16a34a' },
  { range: '50–74', label: 'BUENO', badge: 'FITOGÉNICO', color: '#84cc16' },
  { range: '25–49', label: 'MODERADO', badge: null, color: '#f97316' },
  { range: '0–24', label: 'MALO', badge: 'NO FITOGÉNICO', color: '#dc2626' },
];
"""

CONSTANTS_TS = "fitogenix-server/src/domain/product/scoring/constants.ts"


# --- §3.1 los umbrales no se transcriben -------------------------------------


def test_el_caso_real_de_GuideScreen_dispara():
    """El guard no es hipotético: cuando se escribió, el árbol ya tenía una cuarta copia
    de los cortes. `constants.ts` explica por qué importa: *"antes había tres criterios
    distintos para la misma decisión y un producto de 72 salía 'Bueno' con sello
    'Fitogénico'"*. Esta copia no rompe hoy: rompe el día que B-7 mueva el sello a 70."""
    fallas = verifica_umbrales_no_transcriptos(
        "fitogenix-native/src/screens/GuideScreen.tsx", GUIDESCREEN_REAL
    )
    assert len(fallas) == 2
    assert any("declara `TIERS`" in f for f in fallas)
    assert any("cortes de banda" in f for f in fallas)


def test_constants_ts_es_el_unico_archivo_que_puede_declararlos():
    assert verifica_umbrales_no_transcriptos(CONSTANTS_TS, GUIDESCREEN_REAL) == []


def test_un_comentario_que_solo_nombra_la_regla_no_dispara():
    """La regla es sobre transcribir el umbral, no sobre la palabra. Un comentario es una
    frase, y hacer fallar el nodo por ella enseña que el guard es ruido."""
    codigo = (
        "// Los TIERS viven en scoring/constants.ts y se citan por puntero (CONTEXT.md §3.1).\n"
        "import { getScoreLabel } from '@/lib/contracts/product';\n"
    )
    assert verifica_umbrales_no_transcriptos("fitogenix-native/src/screens/HomeScreen.tsx", codigo) == []


def test_importar_el_umbral_por_contrato_no_dispara():
    """Consumir el campo derivado que llega del backend es exactamente lo que §3.4 pide."""
    codigo = "import type { FitogenixProduct } from '@/lib/contracts/product';\nconst t = p.tier;\n"
    assert verifica_umbrales_no_transcriptos("fitogenix-native/src/screens/HomeScreen.tsx", codigo) == []


def test_una_prosa_con_numeros_pero_sin_etiquetas_de_banda_no_dispara():
    codigo = "const RETRIES = 3;\nconst TIMEOUT_MS = 25000;\n"
    assert verifica_umbrales_no_transcriptos("fitogenix-server/src/services/x.ts", codigo) == []


# --- §5.2 / §3.4 la frontera del cliente -------------------------------------


def test_importar_ftgEngine_desde_el_cliente_dispara():
    codigo = "import { computeScore } from '@/domain/product/ftgEngine';\n"
    fallas = verifica_frontera_cliente("fitogenix-native/src/screens/ScanScreen.tsx", codigo)
    assert any("ftgEngine" in f for f in fallas)


def test_el_shim_deprecado_tiene_permiso_de_existir():
    """`ftgEngine.ts` es `export * from '@/lib/contracts/product'` y su encabezado dice que
    se borra cuando no queden imports. Hacerlo fallar sería pedir que se borre solo."""
    codigo = "export * from '@/lib/contracts/product';\n"
    assert verifica_frontera_cliente(
        "fitogenix-native/src/domain/product/ftgEngine.ts", codigo
    ) == []


def test_el_cliente_no_puede_definir_un_simbolo_del_motor():
    codigo = "function resolveProductStatus(score: number) { return score > 50; }\n"
    fallas = verifica_frontera_cliente("fitogenix-native/src/screens/ScanScreen.tsx", codigo)
    assert any("nunca los recalcula" in f for f in fallas)


def test_el_cliente_no_habla_directo_con_anthropic():
    codigo = "import Anthropic from '@anthropic-ai/sdk';\n"
    fallas = verifica_frontera_cliente("fitogenix-native/src/api/client.ts", codigo)
    assert any("frontera" in f for f in fallas)


def test_el_backend_si_puede_definir_simbolos_del_motor():
    """El guard es de frontera, no de estilo: en el servidor esto es exactamente correcto."""
    codigo = "export function resolveProductStatus(score: number) { return score; }\n"
    assert verifica_frontera_cliente(
        "fitogenix-server/src/domain/product/scoring/presentation.ts", codigo
    ) == []


def test_el_cliente_puede_usar_el_campo_derivado_que_le_llega():
    codigo = "const label = product.scoreLabel;\nconst sello = product.sello;\n"
    assert verifica_frontera_cliente("fitogenix-native/src/screens/ScanScreen.tsx", codigo) == []


# --- §5.6 un endpoint nuevo entra al contrato en el mismo commit -------------


def test_una_ruta_nueva_sin_contrato_dispara():
    nueva = "fitogenix-server/src/routes/products/similar.ts"
    fallas = verifica_ruta_con_contrato([nueva], rutas_nuevas=[nueva])
    assert any("§5.6" in f for f in fallas)


def test_una_ruta_nueva_con_su_schema_en_el_mismo_commit_pasa():
    nueva = "fitogenix-server/src/routes/products/similar.ts"
    schema = "fitogenix-server/src/routes/products/lookupSchema.ts"
    assert verifica_ruta_con_contrato([nueva, schema], rutas_nuevas=[nueva]) == []


def test_modificar_una_ruta_existente_no_exige_contrato_nuevo():
    """La regla es sobre endpoints nuevos. Un fix dentro de una ruta que ya está en el
    contrato no lo cambia."""
    existente = "fitogenix-server/src/routes/products/lookup.ts"
    assert verifica_ruta_con_contrato([existente], rutas_nuevas=[]) == []


def test_un_test_de_ruta_no_cuenta_como_ruta_nueva():
    nueva = "fitogenix-server/src/routes/products/lookup.test.ts"
    assert verifica_ruta_con_contrato([nueva], rutas_nuevas=[nueva]) == []


# --- Integración: el guard corre DESPUÉS de que el modelo respondió ----------


def test_el_schema_rechaza_el_codigo_que_viola_la_frontera():
    """El patrón que PampaGrow adoptó al eliminar `TOOLS_BY_AGENT`: el validador corre en
    Python después del modelo, así su resultado es un hecho del estado y no algo que el
    modelo pueda describir como quiera."""
    with pytest.raises(ValidationError, match="frontera violada"):
        CodigoGenerado(
            agente=Disciplina.MOBILE,
            archivos=[
                ArchivoGenerado(
                    ruta="fitogenix-native/src/screens/GuideScreen.tsx",
                    lenguaje="tsx",
                    contenido=GUIDESCREEN_REAL,
                )
            ],
        )


def test_corre_los_guards_junta_todas_las_fallas():
    fallas = corre_los_guards(
        [
            ("fitogenix-native/src/screens/GuideScreen.tsx", GUIDESCREEN_REAL),
            ("fitogenix-native/src/screens/ScanScreen.tsx",
             "import { computeScore } from '@/domain/product/ftgEngine';"),
        ]
    )
    assert len(fallas) == 3


# --- Los falsos positivos que el barrido del 2026-09-01 encontró --------------
# Los tres se detectaron corriendo los guards sobre los 136 archivos .ts/.tsx reales de
# los dos repos. Quedan como test para que no vuelvan: un guard que da ruido se apaga.


def test_una_fecha_no_es_un_rango_de_banda():
    """Línea real de `fitogenix-native/src/lib/contracts/product.ts`. El archivo nombra
    'EXCELENTE' en un union de tipos y lleva `2026-08-18` en un comentario; ni de lejos
    transcribe un umbral. Sin proximidad ni el filtro de cero a la izquierda, disparaba."""
    codigo = (
        "export type ScoreLabel = 'EXCELENTE' | 'BUENO' | 'MODERADO' | 'MALO';\n"
        "/**\n"
        "   NO incluye `breakdown` (decisión de producto, 2026-08-18): el servidor\n"
        "   manda el puntaje ya compuesto.\n"
        " */\n"
    )
    assert verifica_umbrales_no_transcriptos("fitogenix-native/src/lib/contracts/product.ts", codigo) == []


def test_creditar_a_open_food_facts_no_es_hablarle():
    """Línea real de `fitogenix-native/src/screens/ScanResultScreen.tsx`. `§5.2` prohíbe
    que el cliente HABLE con OFF, no que lo nombre — el crédito de la fuente es correcto."""
    codigo = "const credito = ' · Datos: Open Food Facts (openfoodfacts.org)';\n"
    assert verifica_frontera_cliente("fitogenix-native/src/screens/ScanResultScreen.tsx", codigo) == []


def test_llamar_a_open_food_facts_desde_el_cliente_si_dispara():
    codigo = "const r = await fetch('https://world.openfoodfacts.org/api/v2/product/' + code);\n"
    fallas = verifica_frontera_cliente("fitogenix-native/src/api/client.ts", codigo)
    assert any("§5.2" in f for f in fallas)


def test_la_suite_del_motor_puede_fijar_sus_propios_cortes():
    """Excepción acotada y pendiente de ratificación por el dueño de `§3.1`: los tests
    co-locados con `constants.ts` son la red de regresión del motor, y es ahí donde un
    cambio no querido tiene que romper algo."""
    codigo = "it('75+ es EXCELENTE', () => expect(getScoreLabel(75).label).toBe('EXCELENTE'));\n"
    ruta = "fitogenix-server/src/domain/product/scoring/presentation.test.ts"
    assert verifica_umbrales_no_transcriptos(ruta, codigo) == []


def test_un_test_fuera_de_la_suite_del_motor_no_puede_fijar_los_cortes():
    codigo = "it('75 es EXCELENTE', () => expect(label(75)).toBe('EXCELENTE'));\n"
    fallas = verifica_umbrales_no_transcriptos("fitogenix-native/src/screens/Home.test.tsx", codigo)
    assert any("cortes de banda" in f for f in fallas)


# --- Lo que el golden FTG-002 destapó el 2026-09-18 -------------------------------
# El arquitecto declaró como supuesto ⚠️ que el barrido podía no ver `HomeScreen.tsx`.
# Tenía razón: `_ETIQUETA_DE_BANDA` no llevaba IGNORECASE, el motor escribe las etiquetas
# en mayúsculas y el cliente en capitalizado. El criterio A-2 del ticket ("el barrido
# completo da 0 hallazgos") habría dado verde con el defecto vivo.

_HOMESCREEN = """
function scoreLabel(score: number | null): string {
  if (score == null) return "Sin score";
  if (score >= 75) return "Excelente";
  if (score >= 50) return "Bueno";
  if (score >= 25) return "Moderado";
  return "Malo";
}
"""


def test_la_etiqueta_capitalizada_tambien_es_una_etiqueta_de_banda():
    fallas = verifica_umbrales_no_transcriptos("fitogenix-native/src/screens/HomeScreen.tsx", _HOMESCREEN)
    assert any("cortes de banda" in f for f in fallas), (
        "el cliente escribe 'Excelente', el motor 'EXCELENTE': sin IGNORECASE el barrido "
        "da 0 hallazgos sobre una tabla de cortes completa."
    )


def test_una_sola_comparacion_cerca_de_una_etiqueta_no_alcanza():
    """Los 4 falsos positivos medidos sobre `fitogenix-server` el 2026-09-18. Ninguno
    transcribe un umbral: son prosa en español, una categoría NOVA y una cita `§5`."""
    casos = [
        ("fitogenix-server/src/domain/product/ingredientData.ts",
         '{ aliases: ["sorbitol"], b: "yellow", desc: "Poliol. Produce malestar. Moderado." },\n'),
        ("fitogenix-server/scripts/audit-scores.ts",
         "if (bd.nova === 4 && bd.tier === 'Excelente') out.push(base);\n"),
        ("fitogenix-server/scripts/audit-scores.ts",
         "why: `Excelente con solo ${Math.round(bd.coverage * 100)}% reconocidos.`\n"),
    ]
    for ruta, codigo in casos:
        assert verifica_umbrales_no_transcriptos(ruta, codigo) == [], ruta


def test_el_corte_como_argumento_alcanza_solo_porque_ahi_no_puede_ser_otra_cosa():
    codigo = "it('75 es EXCELENTE', () => expect(label(75)).toBe('EXCELENTE'));\n"
    fallas = verifica_umbrales_no_transcriptos("fitogenix-native/src/screens/Home.test.tsx", codigo)
    assert any("cortes de banda" in f for f in fallas)


def test_lo_que_este_guard_sigue_sin_ver():
    """**Deuda declarada, no disimulada.** `ScanResultScreen.tsx` parte el puntaje por un
    corte propio para elegir qué grupo de ingredientes destaca. Es una comparación sola y
    lo que tiene al lado no es una etiqueta de banda, así que el barrido no la ve. Lo
    encontró el arquitecto leyendo, no el guard. Si algún día se detecta, este test cambia.
    """
    codigo = 'const isBad = result.score != null && result.score < 50;\n' \
             'const featuredLabel = isBad ? "INGREDIENTES CUESTIONABLES" : "INGREDIENTES BENEFICIOSOS";\n'
    assert verifica_umbrales_no_transcriptos("fitogenix-native/src/screens/ScanResultScreen.tsx", codigo) == []


def test_un_comentario_de_sql_no_es_codigo():
    """`--` abre comentario de línea en SQL. Encontrado el 19/9/2026 escribiendo la
    migración que saca los umbrales del COMMENT de `products.sello`: su bloque de
    rollback, todo comentado, daba hallazgo."""
    codigo = "-- COMMENT ON COLUMN products.sello IS 'FITOGÉNICO (>=75), NO FITOGÉNICO (<25)';\n"
    assert verifica_umbrales_no_transcriptos("fitogenix-server/migrations/099_x.sql", codigo) == []


def test_un_umbral_dentro_de_un_comment_on_si_es_hallazgo():
    """No es un comentario de SQL: es una cadena que termina en la metadata de Postgres,
    donde ningún barrido la alcanza una vez aplicada."""
    codigo = "COMMENT ON COLUMN products.sello IS 'FITOGÉNICO (>=75), NO FITOGÉNICO (<25)';\n"
    fallas = verifica_umbrales_no_transcriptos("fitogenix-server/migrations/099_x.sql", codigo)
    assert any("cortes de banda" in f for f in fallas)
