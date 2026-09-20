"""P0-2 a P0-4 y P0-7, con el grafo real y `llama_estructurado` reemplazado por un doble
que simula MODO REAL (sin dry-run) y registra cada prompt. Es el harness del dictamen,
convertido en tests: estos caminos no se pueden probar con los stubs del dry-run."""
import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from fitogenix import graph, stubs
from fitogenix.config import MODELO_COMPLEJO
from fitogenix.llm import EsUnStub, Respuesta, choose_model
from fitogenix.schemas import AnalisisDeRequerimiento, ContratoAprobado, EstadoDelPipeline


@pytest.fixture
def pedidos(monkeypatch, repos_falsos):
    monkeypatch.delenv("FITOGENIX_DRY_RUN", raising=False)
    registro = []

    def doble(agente, modelo, *, usuario, stub, escalado=False, mecanico=False, **_):
        registro.append({"agente": agente, "usuario": usuario, "escalado": escalado})
        r = Respuesta(texto="", modelo=choose_model(agente, escalado=escalado), agente=agente,
                      cierre=stubs.STUB_CIERRE)
        if modelo is AnalisisDeRequerimiento:
            return stubs.STUB_ANALISIS_RESUELTO, r
        if modelo is ContratoAprobado:
            n = sum(1 for x in registro if x["agente"] == "architect")
            sup = ["asumo que el umbral del sello es 70"] if n == 1 else []
            return stubs.STUB_CONTRATO.model_copy(update={"supuestos": sup}), r
        return stub, r

    monkeypatch.setattr(graph, "llama_estructurado", doble)
    return registro


def _app():
    return graph.construye().compile(checkpointer=MemorySaver()), {"configurable": {"thread_id": "T"}}


def _hasta_el_hitl2(app, cfg):
    app.invoke(EstadoDelPipeline(entrada="[test] FTG-002", ticket="FTG-002"), cfg)
    return app.invoke(Command(resume={"accion": "contratar"}), cfg)


def test_n1a_recibe_el_ssot_entero(pedidos):
    app, cfg = _app()
    app.invoke(EstadoDelPipeline(entrada="[test]", ticket="FTG-002"), cfg)
    assert "## §8 — Bloqueantes activos" in pedidos[0]["usuario"]


def test_el_arquitecto_escala_cuando_el_analisis_toca_el_motor(pedidos):
    app, cfg = _app()
    _hasta_el_hitl2(app, cfg)
    arq = [p for p in pedidos if p["agente"] == "architect"]
    assert arq and arq[0]["escalado"] is True  # el stub cita CONTEXT.md §3.1
    assert app.get_state(cfg).values["modelo_contrato"] == MODELO_COMPLEJO


def test_el_hitl2_da_ids_y_un_ok_sin_respuestas_no_avanza(pedidos):
    app, cfg = _app()
    out = _hasta_el_hitl2(app, cfg)
    carga = out["__interrupt__"][0].value
    assert carga["nodo"] == "n2b_aclarar_contrato" and "S1" in carga["a_responder"]
    out = app.invoke(Command(resume={"accion": "contratar"}), cfg)
    assert out["__interrupt__"][0].value["nodo"] == "n2b_aclarar_contrato", "vuelve a preguntar"
    assert sum(1 for p in pedidos if p["agente"] == "architect") == 1


def test_una_respuesta_sin_accion_no_aprueba(pedidos):
    app, cfg = _app()
    _hasta_el_hitl2(app, cfg)
    out = app.invoke(Command(resume={"respuestas": [{"pregunta": "S1", "respuesta": "75"}]}), cfg)
    assert out["__interrupt__"]


def test_las_respuestas_vuelven_al_arquitecto_y_el_contrato_se_rehace(pedidos):
    app, cfg = _app()
    _hasta_el_hitl2(app, cfg)
    out = app.invoke(Command(resume={"accion": "contratar", "respuestas": [
        {"pregunta": "S1", "respuesta": "XYZZY: el umbral lo fija constants.ts, no se asume"}]}), cfg)
    arq = [p for p in pedidos if p["agente"] == "architect"]
    assert len(arq) == 2 and "XYZZY" in arq[1]["usuario"]
    assert out["estado_final"] == "contrato-listo"
    assert out["contrato"].supuestos == [] and out["ronda_contrato"] == 2


def test_implementar_acepta_el_contrato_explicitamente_y_con_hasta_contrato_corta(pedidos):
    app, cfg = _app()
    _hasta_el_hitl2(app, cfg)
    out = app.invoke(Command(resume={"accion": "implementar"}), cfg)
    assert out["estado_final"] == "contrato-listo"
    assert not any(p["agente"] in ("backend", "revisor") for p in pedidos)


def test_abortar_en_el_hitl2_escala_con_resumen(pedidos):
    app, cfg = _app()
    _hasta_el_hitl2(app, cfg)
    out = app.invoke(Command(resume={"accion": "abortar"}), cfg)
    assert out["estado_final"] == "abortada" and out["resumen"] is not None


def test_cada_entrega_deja_su_cierre_en_el_estado(pedidos):
    app, cfg = _app()
    _hasta_el_hitl2(app, cfg)
    nodos = [c.nodo for c in app.get_state(cfg).values["cierres"]]
    assert nodos == ["n1a_analizar", "n2_contrato"]


def test_n3_fuera_de_dry_run_no_finge_codigo(pedidos):
    with pytest.raises(EsUnStub, match="P1-1"):
        graph.n3_implementar(EstadoDelPipeline(entrada="x", contrato=stubs.STUB_CONTRATO))
