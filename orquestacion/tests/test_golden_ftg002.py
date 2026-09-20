"""El golden set. **La única prueba de que los schemas sirven.**

Los 106 tests anteriores verifican que los validadores rechazan lo que tienen que
rechazar — pero con objetos que escribí yo, sabiendo qué valida cada campo. Eso prueba
que el código hace lo que dije, no que el contrato sea escribible por un agente que
nunca vio el validador.

`tests/golden/ftg_002.py` es la salida real del arquitecto contra FTG-002, del
2026-09-18, transcrita a los schemas. Lo que estos tests fijan:

1. el objeto **valida** (si deja de validar, un schema se endureció de más);
2. `hay_que_preguntar()` da True por la vía del modelo (6 supuestos, 5 decisiones) —
   o sea el pipeline se habría interrumpido, que es lo que el diseño promete;
3. `escala_a_opus` da True, porque el contrato toca el motor;
4. las tres puntas están enumeradas, incluidas las dos que **no cambian**;
5. y que `det.verificado_sin_ruta` levanta **1** hallazgo y no 5. Los otros 4 eran del
   schema: `ReglaDeValidacion.puntero` era un `str` y el arquitecto había dado dos por
   regla. Se corrigió con esta evidencia el 2026-09-18 y el campo pasó a `punteros`.

Este archivo cambió dos veces por lo que el contrato real destapó, y las dos veces ganó
el contrato. Es el punto: el golden no está acá para que los schemas pasen.
"""
import pytest

from fitogenix import det
from fitogenix.schemas import (
    PUNTOS_DEL_CONTRATO, ContratoAprobado, Disciplina, Marca, hay_que_preguntar,
)
from tests.golden.ftg_002 import CONTRATO_FTG_002


def test_el_contrato_real_valida():
    assert isinstance(CONTRATO_FTG_002, ContratoAprobado)
    assert CONTRATO_FTG_002.ticket == "FTG-002"


def test_el_pipeline_se_habria_interrumpido():
    """La promesa del diseño: no se pide OK de rutina, pero sí si hay duda declarada."""
    assert CONTRATO_FTG_002.supuestos, "sin supuestos el golden no prueba la interrupción"
    assert CONTRATO_FTG_002.decisiones_abiertas
    assert hay_que_preguntar(CONTRATO_FTG_002, []) is True


def test_escala_a_opus_porque_toca_el_motor():
    assert CONTRATO_FTG_002.toca_scoring is True
    assert CONTRATO_FTG_002.escala_a_opus is True


def test_las_tres_puntas_del_producto_enumeradas_incluidas_las_que_no_cambian():
    delproducto = [p for p in CONTRATO_FTG_002.puntas_tocadas if p.es_del_producto]
    assert {p.archivo for p in delproducto} == set(PUNTOS_DEL_CONTRATO)
    assert sum(1 for p in delproducto if not p.cambia) == 2


def test_el_contrato_nuevo_se_declara_en_los_dos_repos():
    """El arquitecto dijo que este contrato agranda el conjunto de 3 a 5 archivos.
    Hasta el 2026-09-18 no se podía registrar y el objeto afirmaba la verdad vieja."""
    nuevas = [p for p in CONTRATO_FTG_002.puntas_tocadas if not p.es_del_producto]
    assert len(nuevas) == 3
    assert {p.repo for p in nuevas} == {"fitogenix-server", "fitogenix-native"}


def test_cero_migraciones_declaradas():
    assert CONTRATO_FTG_002.cambios_de_esquema == []
    assert CONTRATO_FTG_002.toca_migracion is False
    assert CONTRATO_FTG_002.requiere_adr is False


def test_hay_brief_por_disciplina_y_ninguno_para_nutrition():
    """El arquitecto dejó por escrito a quién NO le escribe brief y por qué."""
    destinos = {b.destinatario for b in CONTRATO_FTG_002.briefs}
    assert destinos == {Disciplina.BACKEND, Disciplina.UX, Disciplina.MOBILE, Disciplina.QA}
    assert Disciplina.NUTRITION not in destinos
    assert Disciplina.DEVOPS not in destinos


def test_cada_campo_tiene_criterio_en_dado_cuando_entonces():
    """9 campos, 3 de ellos en femenino ('Dada la respuesta…'). Hasta el 2026-09-18 el
    validador pedía `dado` literal y los rechazaba por gramática, no por contenido."""
    assert len(CONTRATO_FTG_002.campos) == 9
    femeninos = [c for c in CONTRATO_FTG_002.campos
                 if c.criterio_de_aceptacion.lower().startswith(("dada", "dados", "dadas"))]
    assert len(femeninos) >= 3


def test_los_chequeos_puros_sobre_una_salida_real():
    assert det.campo_sin_criterio(CONTRATO_FTG_002) == []


def test_verificado_sin_ruta_deja_de_inventar_hallazgos():
    """Con `punteros` en plural queda **1**, y es el único real: el arquitecto marcó ✅
    "el cliente no ordena ni deduce filas" apuntando solo a `§5.2` y `§3.4`. Son secciones,
    no hay archivo que abrir, así que es ⚠️ y no ✅. Los otros 4 eran del schema: la regla
    sí tenía su ruta y no había dónde ponerla."""
    hallazgos = det.verificado_sin_ruta(CONTRATO_FTG_002)
    assert len(hallazgos) == 1
    assert "no ordena" in hallazgos[0].detalle or "CONTEXT.md §5.2" in str(hallazgos[0].puntero)


@pytest.mark.parametrize("archivo", [
    "fitogenix-server/src/routes/scoring/bands.ts",
    "fitogenix-server/src/routes/scoring/bandsSchema.ts",
    "fitogenix-native/src/lib/contracts/scoreBands.ts",
])
def test_una_punta_nueva_se_puede_declarar(archivo):
    from fitogenix.schemas import PuntaDelContrato
    punta = PuntaDelContrato(archivo=archivo, cambia=True, detalle="archivo nuevo del contrato")
    assert punta.es_del_producto is False


def test_una_punta_que_no_es_ruta_de_repo_sigue_sin_entrar():
    from fitogenix.schemas import PuntaDelContrato
    with pytest.raises(ValueError, match="no es una ruta de repo"):
        PuntaDelContrato(archivo="CONTEXT.md §3.1", cambia=True, detalle="no es un archivo")


def test_un_contrato_nuevo_declarado_en_un_solo_repo_no_valida():
    """Lo que se conserva de la regla de las tres puntas no es la lista: es que un tipo
    que cruza el cable se declare en los dos lados."""
    from fitogenix.schemas import PuntaDelContrato
    solo_server = [
        PuntaDelContrato(archivo="fitogenix-server/src/routes/scoring/bands.ts",
                         cambia=True, detalle="ruta nueva sin su espejo"),
    ]
    datos = {**CONTRATO_FTG_002.model_dump(),
             "puntas_tocadas": [p.model_dump() for p in solo_server]}
    with pytest.raises(ValueError, match="se declara en los dos repos"):
        ContratoAprobado.model_validate(datos)


def test_las_decisiones_abiertas_llevan_dueno_solo_como_prosa():
    """Otra deuda fijada: el arquitecto le puso dueño a cada decisión, pero
    `decisiones_abiertas` es `list[str]`, así que rutearlas exige parsear texto."""
    assert all(" · " in d for d in CONTRATO_FTG_002.decisiones_abiertas)
    assert all(not isinstance(d, tuple) for d in CONTRATO_FTG_002.decisiones_abiertas)
