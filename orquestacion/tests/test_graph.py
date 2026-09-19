"""El grafo, entero, **sin llamar a ningún modelo**.

Que esta suite exista y pase es la prueba de que `dry_run` sirve para lo que se diseñó:
verificar nodos, bordes, techos e interrupciones sin factura y sin API key. Si para
probar el grafo hiciera falta una credencial, el grafo se probaría una vez.
"""
import pytest

from fitogenix import graph
from fitogenix.schemas import (
    TECHOS,
    EstadoDelPipeline,
    Hallazgo,
    ReporteDeRevision,
    Severidad,
    Veredicto,
)


@pytest.fixture(autouse=True)
def seco(tmp_path, monkeypatch):
    monkeypatch.setenv("FITOGENIX_DRY_RUN", "1")
    monkeypatch.setenv("FITOGENIX_CHECKPOINTER", "memory")
    monkeypatch.setenv("FITOGENIX_STATE_DIR", str(tmp_path / ".fitogenix"))
    from fitogenix import config, sessions
    monkeypatch.setattr(config, "SETTINGS", config.Settings())
    monkeypatch.setattr(sessions, "SETTINGS", config.SETTINGS)


def _estado(**kw) -> EstadoDelPipeline:
    return EstadoDelPipeline(entrada="[test] un pedido", ticket="FTG-002", **kw)


# --- la forma del grafo -------------------------------------------------------------

def test_los_nueve_nodos_del_diagrama_estan():
    g = graph.construye()
    assert set(g.nodes) >= {
        "n1a_analizar", "n1b_aclarar", "n2_contrato", "n2b_aclarar_contrato",
        "n3_implementar", "n4_empaquetar_pr", "n5_revisar", "n_escalar", "n6_resumen",
    }


def test_escalar_no_termina_en_end_sino_en_el_resumen():
    """La corrida que escala es la que MÁS necesita dejar algo escrito: alguien la va a
    levantar sin haber estado. Si `n_escalar` fuera a END, no dejaría nada."""
    destinos = {(a, b) for a, b in graph.construye().edges}
    assert ("n_escalar", "n6_resumen") in destinos
    assert ("n_escalar", "__end__") not in destinos


# --- HitL 1: el OK no alcanza por sí solo -------------------------------------------

def test_un_ok_con_preguntas_abiertas_no_aprueba():
    """`aprobacion_valida`: apretar el botón que sigue es lo más fácil que hay."""
    from fitogenix.stubs import STUB_ANALISIS
    e = _estado(analisis=STUB_ANALISIS, ronda_aclaracion=1)
    r = graph._absorbe_respuesta(e, {"accion": "contratar"}, ronda=1)
    assert r["aprobacion_humana"] is False
    assert "sin efecto" in r["log"][0].detalle


def test_el_mismo_ok_aprueba_cuando_no_quedan_preguntas():
    from fitogenix.stubs import STUB_ANALISIS_RESUELTO
    e = _estado(analisis=STUB_ANALISIS_RESUELTO, ronda_aclaracion=2)
    r = graph._absorbe_respuesta(e, {"accion": "contratar"}, ronda=2)
    assert r["aprobacion_humana"] is True


def test_abortar_se_entiende_aunque_venga_suelto():
    r = graph._absorbe_respuesta(_estado(), "abortar", ronda=1)
    assert r["estado_final"] == "abortada-por-techo"


# --- los techos se consultan en el borde --------------------------------------------

def test_el_techo_de_aclaracion_aborta_en_vez_de_seguir_preguntando():
    """Más rondas que el techo no significa 'falta información': significa que el ticket
    está mal planteado, y escalarlo es más honesto que seguir preguntando."""
    e = _estado(ronda_aclaracion=TECHOS["aclaracion"])
    assert graph.rutea_aclaracion(e) == "abortar"
    assert graph.rutea_aclaracion(_estado(ronda_aclaracion=1)) == "reanalizar"


def test_con_aprobacion_se_contrata_aunque_falten_rondas():
    assert graph.rutea_aclaracion(_estado(aprobacion_humana=True)) == "contratar"


def test_el_techo_de_contrato_es_uno():
    """Sin aprobación de rutina, un segundo ciclo silencioso sería el pipeline discutiendo
    consigo mismo."""
    assert TECHOS["contrato"] == 1
    e = _estado(ronda_contrato=1, aprobacion_humana=False)
    assert graph.rutea_post_contrato(e) == "abortar"
    assert graph.rutea_post_contrato(_estado(ronda_contrato=1, aprobacion_humana=True)) == "implementar"


# --- HitL 2: por incertidumbre, no por tema -----------------------------------------

def test_sin_dudas_no_se_interrumpe():
    from fitogenix.stubs import STUB_CONTRATO
    assert graph.rutea_contrato(_estado(contrato=STUB_CONTRATO)) == "implementar"


def test_un_supuesto_declarado_alcanza_para_interrumpir():
    from fitogenix.stubs import STUB_CONTRATO
    c = STUB_CONTRATO.model_copy(update={"supuestos": ["no corrí los tests"]})
    assert graph.rutea_contrato(_estado(contrato=c)) == "preguntar"


def test_un_chequeo_determinista_interrumpe_aunque_el_modelo_no_declare_nada():
    """La mitad del HitL que el modelo no puede declinar ni suavizar."""
    from fitogenix.schemas import Incertidumbre
    from fitogenix.stubs import STUB_CONTRATO
    e = _estado(contrato=STUB_CONTRATO, incertidumbres=[
        Incertidumbre(chequeo="frontera-violada", detalle="el cliente importa TIERS")])
    assert graph.rutea_contrato(e) == "preguntar"


# --- el ruteo de la revisión --------------------------------------------------------

def _rev(veredicto, severidad=None, ronda=1):
    hallazgos = []
    if severidad is not None:
        hallazgos = [Hallazgo(id="H-01", categoria="contrato-cross-repo", severidad=severidad,
                              archivo="fitogenix-server/src/x.ts",
                              descripcion="[test] un hallazgo de prueba",
                              correccion_sugerida="[test] la corrección sugerida")]
    return ReporteDeRevision(veredicto=veredicto, resumen="[test] revisión de prueba para el ruteo",
                             hallazgos=hallazgos, ronda=ronda)


def test_aprobado_continua():
    e = _estado(revisiones=[_rev(Veredicto.APROBADO)])
    assert graph.rutea_revision_nodo(e) == "continuar"


def test_aprobado_con_condiciones_tambien_avanza():
    e = _estado(revisiones=[_rev(Veredicto.APROBADO_CON_CONDICIONES)])
    assert graph.rutea_revision_nodo(e) == "continuar"


def test_un_bloqueante_vuelve_al_contrato():
    e = _estado(revisiones=[_rev(Veredicto.RECHAZADO, Severidad.BLOQUEANTE)])
    assert graph.rutea_revision_nodo(e) == "recontratar"


def test_rechazado_con_hallazgos_solo_menores_no_pasa():
    """**El agujero que PampaGrow tapó.** Ruteando solo por severidad, esto devolvía
    'continuar', la corrida cerraba en verde y el CLI salía 0: el gate de calidad se podía
    saltar sin que nadie lo notara."""
    e = _estado(revisiones=[_rev(Veredicto.RECHAZADO, Severidad.MENOR)])
    assert graph.rutea_revision_nodo(e) == "reimplementar"


def test_en_el_techo_de_revision_escala():
    e = _estado(revisiones=[_rev(Veredicto.RECHAZADO, Severidad.BLOQUEANTE,
                                 ronda=TECHOS["revision"])])
    assert graph.rutea_revision_nodo(e) == "escalar"


def test_sin_revision_escala_en_vez_de_continuar():
    """Ante la falta de dato, el camino seguro no es seguir."""
    assert graph.rutea_revision_nodo(_estado()) == "escalar"


# --- la corrida entera, sin modelo ---------------------------------------------------

def test_el_grafo_entero_corre_en_dry_run_y_cierra():
    from langgraph.types import Command

    from fitogenix import sessions

    with sessions.checkpointer() as saver:
        app = graph.construye().compile(checkpointer=saver)
        cfg = sessions.config_de("FTG-002")

        salida = app.invoke(_estado(), config=cfg)
        assert salida["__interrupt__"], "el HitL 1 es incondicional: tiene que interrumpir"

        # El humano contesta la pregunta pero todavía no puede aprobar: el análisis la
        # tiene abierta. Vuelve a analizar y vuelve a preguntar.
        salida = app.invoke(Command(resume={"accion": "contratar", "respuestas": [
            {"pregunta": "P1", "respuesta": "solo GuideScreen"}]}), config=cfg)
        assert salida["__interrupt__"], "sin preguntas resueltas, el OK no cuenta"

        salida = app.invoke(Command(resume={"accion": "contratar"}), config=cfg)

    assert not salida.get("__interrupt__")
    assert salida["estado_final"] == "cerrada"
    assert salida["resumen"].veredicto == Veredicto.APROBADO
    assert salida["ronda_aclaracion"] == 2 and salida["ronda_revision"] == 1
    nodos = [e.nodo for e in salida["log"]]
    assert nodos[0] == "n1a_analizar" and nodos[-1] == "n6_resumen"
