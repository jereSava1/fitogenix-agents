"""P0-1: salida estructurada, el `Cierre` y el reintento con el error de validación.

Ninguno llama a la API: un cliente falso devuelve bloques `tool_use` armados a mano. Lo que
se prueba es lo que hace `llama_estructurado` con ellos, que es lo que va a hacer con los
de verdad.
"""
import json
from types import SimpleNamespace

import pytest

from fitogenix import llm
from fitogenix.schemas import Cierre, ContratoAprobado, RevisionManual, Validacion
from fitogenix.stubs import STUB_CIERRE, STUB_CONTRATO


@pytest.fixture(autouse=True)
def real(tmp_path, monkeypatch):
    monkeypatch.delenv("FITOGENIX_DRY_RUN", raising=False)
    import dataclasses
    monkeypatch.setattr(llm, "SETTINGS", dataclasses.replace(llm.SETTINGS, state_dir=tmp_path))
    return tmp_path


def _cierre(**kw):
    base = {
        "resumen": "Escribí el contrato de FTG-002 con tres puntas y cuatro briefs.",
        "validaciones": [{"metodo": "cita-al-ssot", "referencia": "CONTEXT.md §3.1", "resultado": "pasa"}],
        "revision_manual": {"requerida": False},
        "proximo_paso": {"accion": "implementar los cuatro briefs", "responsable": "pipeline"},
    }
    base.update(kw)
    return base


def _bloque(entrada, stop="tool_use"):
    b = SimpleNamespace(type="tool_use", id="tu_1", name="entregar", input=entrada)
    b.model_dump = lambda **_: {"type": "tool_use", "id": "tu_1", "name": "entregar", "input": entrada}
    return SimpleNamespace(content=[b], stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=100, output_tokens=50))


class Cliente:
    def __init__(self, *respuestas):
        self.respuestas, self.pedidos = list(respuestas), []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.pedidos.append(json.loads(json.dumps(kw, default=str)))
        return self.respuestas.pop(0)


def _llama(cliente):
    return llm.llama_estructurado("architect", ContratoAprobado, sistema="s", usuario="u",
                                  stub=STUB_CONTRATO, cliente=cliente, traza="FTG-002")


VALIDO = {"resultado": json.loads(STUB_CONTRATO.model_dump_json()), "cierre": _cierre()}


# --- el schema viaja en la llamada ---------------------------------------------------

def test_la_llamada_fuerza_la_tool_con_el_schema_del_nodo():
    c = Cliente(_bloque(VALIDO))
    _llama(c)
    pedido = c.pedidos[0]
    assert pedido["tool_choice"] == {"type": "tool", "name": "entregar"}
    esquema = pedido["tools"][0]["input_schema"]
    assert set(esquema["required"]) == {"resultado", "cierre"}
    assert "reglas_de_validacion" in esquema["properties"]["resultado"]["properties"]
    assert "Cómo entregás" in pedido["system"]


def test_el_schema_no_tiene_refs_ni_deja_declarar_origen():
    texto = json.dumps(llm.esquema_para_tool(ContratoAprobado))
    assert "$ref" not in texto
    val = llm.esquema_para_tool(ContratoAprobado)["properties"]["cierre"]["properties"]["validaciones"]["items"]
    assert "origen" not in val["properties"]


def test_una_entrega_valida_vuelve_con_su_cierre_y_la_validacion_de_python():
    contrato, r = _llama(Cliente(_bloque(VALIDO)))
    assert isinstance(contrato, ContratoAprobado)
    assert r.cierre.resumen.startswith("Escribí")
    assert r.cierre.validaciones[-1].origen == "python"
    assert r.traza and json.loads(open(r.traza).read())["entrega_cruda"]["cierre"]


# --- reintento con el error ----------------------------------------------------------

def test_una_entrega_invalida_se_reintenta_con_el_error_y_se_corrige():
    malo = {"resultado": {**VALIDO["resultado"], "reglas_de_validacion": []}, "cierre": _cierre()}
    c = Cliente(_bloque(malo), _bloque(VALIDO))
    contrato, _ = _llama(c)
    assert isinstance(contrato, ContratoAprobado)
    segundo = c.pedidos[1]["messages"]
    assert segundo[-1]["content"][0]["type"] == "tool_result"
    assert segundo[-1]["content"][0]["is_error"] is True
    assert "reglas_de_validacion" in segundo[-1]["content"][0]["content"]


def test_dos_entregas_invalidas_cortan_y_dejan_la_traza(real):
    malo = {"resultado": {"objetivo": "x"}, "cierre": _cierre()}
    with pytest.raises(llm.EntregaInvalida, match="Traza"):
        _llama(Cliente(_bloque(malo), _bloque(malo)))
    trazas = list((real / "llamadas" / "FTG-002").glob("*.json"))
    assert len(trazas) == 2, "lo que se pagó se puede leer"


def test_una_salida_cortada_por_max_tokens_no_se_valida():
    """Un JSON cortado nunca se valida. Desde el debut (2026-09-20) primero se repite con el
    techo duplicado; si ni con `TOPE_DE_SALIDA` entra, corta."""
    c = Cliente(*[_bloque(VALIDO, stop="max_tokens")] * 4)
    with pytest.raises(llm.SalidaTruncada):
        _llama(c)
    assert [p["max_tokens"] for p in c.pedidos] == [16_000, 32_000]


def test_el_modelo_no_puede_declararse_una_validacion_de_python():
    trampa = {**VALIDO, "cierre": _cierre(validaciones=[
        {"metodo": "test", "referencia": "todo.test.ts", "resultado": "pasa", "origen": "python"}])}
    c = Cliente(_bloque(trampa), _bloque(VALIDO))
    _llama(c)
    assert "origen='python'" in c.pedidos[1]["messages"][-1]["content"][0]["content"]


def test_en_dry_run_vuelve_el_stub_y_su_cierre(monkeypatch):
    monkeypatch.setenv("FITOGENIX_DRY_RUN", "1")
    contrato, r = llm.llama_estructurado("architect", ContratoAprobado, sistema="s", usuario="u",
                                         stub=STUB_CONTRATO, stub_cierre=STUB_CIERRE)
    assert contrato is STUB_CONTRATO and r.cierre is STUB_CIERRE and r.dry_run


# --- el Cierre: lo que no se validó lo revisa un humano -------------------------------

def test_lo_que_no_corrio_exige_revision_manual():
    with pytest.raises(ValueError, match="lo revisa un humano"):
        Cierre.model_validate(_cierre(validaciones=[
            {"metodo": "ninguna", "referencia": "nada", "resultado": "no-corrido"}]))


def test_una_revision_manual_sin_objeto_no_vale():
    with pytest.raises(ValueError, match="sin decir qué revisar"):
        RevisionManual(requerida=True)
    RevisionManual(requerida=True, que_revisar=["la regla 3"], quien="jere",
                   por_que="cita el SSOT y no el código")


def test_el_modelo_solo_no_se_gana_un_verificado():
    with pytest.raises(ValueError, match="sin ninguna validación hecha por Python"):
        Cierre.model_validate(_cierre(marca="✅"))
    c = Cierre.model_validate(_cierre())
    c.validaciones.append(Validacion(metodo="schema", referencia="schema Pydantic", resultado="pasa", origen="python"))
    Cierre.model_validate({**c.model_dump(), "marca": "✅"})


# --- H25 ----------------------------------------------------------------------------

def test_los_errores_de_conexion_del_sdk_son_transitorios():
    import anthropic
    import httpx
    req = httpx.Request("POST", "https://api.anthropic.com")
    assert llm._es_transitorio(anthropic.APIConnectionError(request=req))
    assert llm._es_transitorio(anthropic.APITimeoutError(request=req))


# --- P0-8 ---------------------------------------------------------------------------

def test_el_humo_reporta_cada_id_que_la_api_no_conoce():
    from fitogenix.humo import modelos_del_ruteo, verifica_modelos

    class Modelos:
        def retrieve(self, m):
            if m == "claude-sonnet-5":
                raise RuntimeError("404 not_found_error")
    fallas = verifica_modelos(SimpleNamespace(models=Modelos()))
    assert len(fallas) == 1 and fallas[0].startswith("claude-sonnet-5")
    assert "claude-opus-5" in modelos_del_ruteo()
