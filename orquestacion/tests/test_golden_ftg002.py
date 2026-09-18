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
5. y el hallazgo incómodo: `det.verificado_sin_ruta` levanta 5, de los cuales 4 son
   artefacto de que `ReglaDeValidacion.puntero` sea un solo `str`. El test lo fija en 5
   a propósito: si mañana `puntero` pasa a ser una lista, este número tiene que bajar, y
   el test que se ponga en rojo es el recordatorio de por qué se cambió.
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


def test_las_tres_puntas_enumeradas_incluidas_las_que_no_cambian():
    nombradas = {p.archivo for p in CONTRATO_FTG_002.puntas_tocadas}
    assert nombradas == set(PUNTOS_DEL_CONTRATO)
    assert sum(1 for p in CONTRATO_FTG_002.puntas_tocadas if not p.cambia) == 2


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


def test_verificado_sin_ruta_mide_la_deuda_del_puntero_singular():
    """5 hallazgos. 1 es del arquitecto (marcó ✅ una regla que solo apunta a §5.2/§3.4);
    los otros 4 son porque el arquitecto dio dos punteros y el schema admite uno."""
    hallazgos = det.verificado_sin_ruta(CONTRATO_FTG_002)
    assert len(hallazgos) == 5
    assert all(h.chequeo == "verificado-sin-ruta" for h in hallazgos)


@pytest.mark.parametrize("archivo", [
    "fitogenix-server/src/routes/scoring/bands.ts",
    "fitogenix-server/src/routes/scoring/bandsSchema.ts",
    "fitogenix-native/src/lib/contracts/scoreBands.ts",
])
def test_las_puntas_nuevas_no_se_pueden_declarar(archivo):
    """**Deuda conocida, fijada a propósito.** El arquitecto declaró que este contrato
    agranda el conjunto de puntas de 3 a 5. `PUNTOS_DEL_CONTRATO` es una constante del
    módulo, así que no hay forma de registrarlo: el contrato queda afirmando la verdad
    vieja. Cuando se resuelva, este test cambia de sentido — y entonces hay que mirar
    `guards.verifica_ruta_con_contrato`, que lee la misma constante.
    """
    from fitogenix.schemas import PuntaDelContrato
    with pytest.raises(ValueError, match="no es una punta del contrato"):
        PuntaDelContrato(archivo=archivo, cambia=True, detalle="archivo nuevo del contrato")


def test_las_decisiones_abiertas_llevan_dueno_solo_como_prosa():
    """Otra deuda fijada: el arquitecto le puso dueño a cada decisión, pero
    `decisiones_abiertas` es `list[str]`, así que rutearlas exige parsear texto."""
    assert all(" · " in d for d in CONTRATO_FTG_002.decisiones_abiertas)
    assert all(not isinstance(d, tuple) for d in CONTRATO_FTG_002.decisiones_abiertas)
