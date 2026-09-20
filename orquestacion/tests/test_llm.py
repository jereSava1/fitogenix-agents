"""La llamada al modelo. Todo esto corre **sin red y sin API key**, que es el punto.

Si estos tests necesitaran una credencial, el dry-run no serviría para lo que existe:
verificar el grafo entero sin gastar.
"""
import os

import pytest
from pydantic import BaseModel

from fitogenix import llm
from fitogenix.llm import Contador, EsUnStub, PresupuestoAgotado, Respuesta, SinCredencial


class Salida(BaseModel):
    ok: bool


class Otra(BaseModel):
    ok: bool


@pytest.fixture
def seco(monkeypatch):
    monkeypatch.setenv("FITOGENIX_DRY_RUN", "1")


@pytest.fixture
def mojado(monkeypatch):
    monkeypatch.setenv("FITOGENIX_DRY_RUN", "0")


# --- dry-run: el grafo corre sin modelo ------------------------------------------

def test_en_dry_run_no_hace_falta_credencial(seco, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = llm.llama("backend", sistema="s", usuario="u")
    assert r.dry_run is True and r.modelo


def test_el_stub_del_que_llama_es_lo_que_vuelve(seco):
    r = llm.llama("backend", sistema="s", usuario="u", stub="contrato mínimo")
    assert r.texto == "contrato mínimo"


def test_estructurado_devuelve_el_stub_sin_tocar_la_red(seco):
    obj, r = llm.llama_estructurado("architect", Salida, sistema="s", usuario="u",
                                    stub=Salida(ok=True))
    assert obj.ok is True and r.dry_run is True


def test_un_stub_del_tipo_equivocado_no_pasa(seco):
    """Si el stub no es del schema que el nodo declara, el dry-run estaría probando otra
    cosa — y pasaría en verde igual."""
    with pytest.raises(TypeError, match="estaría probando otra cosa"):
        llm.llama_estructurado("architect", Salida, sistema="s", usuario="u", stub=Otra(ok=True))


def test_un_stub_no_puede_cerrar_una_corrida():
    with pytest.raises(EsUnStub):
        Respuesta(texto="x", modelo="m", agente="qa", dry_run=True).exigir_real()
    real = Respuesta(texto="x", modelo="m", agente="qa")
    assert real.exigir_real() is real


def test_el_dry_run_se_lee_en_cada_llamada(monkeypatch):
    """`SETTINGS` se construye al importar, en un punto impredecible. Si el flag quedara
    congelado ahí, agregar un archivo de test podía apagar el dry-run en silencio."""
    monkeypatch.setenv("FITOGENIX_DRY_RUN", "1")
    assert llm.llama("qa", sistema="s", usuario="u").dry_run is True
    monkeypatch.setenv("FITOGENIX_DRY_RUN", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SinCredencial):
        llm.llama("qa", sistema="s", usuario="u")


# --- reintentos: solo lo transitorio ----------------------------------------------

class _Http(Exception):
    def __init__(self, codigo):
        super().__init__(f"HTTP {codigo}")
        self.status_code = codigo


def test_reintenta_lo_transitorio_y_termina_bien():
    intentos = {"n": 0}

    def flaky():
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise _Http(529)
        return "listo"

    valor, n = llm._con_reintentos(flaky, dormir=lambda _: None)
    assert valor == "listo" and n == 3


def test_no_reintenta_una_request_mal_armada():
    """Un 400 no sale distinto la próxima vez: reintentarlo esconde el bug."""
    intentos = {"n": 0}

    def roto():
        intentos["n"] += 1
        raise _Http(400)

    with pytest.raises(_Http):
        llm._con_reintentos(roto, dormir=lambda _: None)
    assert intentos["n"] == 1


def test_se_rinde_despues_del_techo_de_reintentos():
    with pytest.raises(_Http):
        llm._con_reintentos(lambda: (_ for _ in ()).throw(_Http(503)), dormir=lambda _: None)


# --- el contador y el techo de gasto ----------------------------------------------

def test_el_contador_lleva_el_libro_por_agente_y_por_modelo():
    c = Contador()
    c.anota(Respuesta(texto="", modelo="m1", agente="backend", tokens_entrada=10, tokens_salida=5))
    c.anota(Respuesta(texto="", modelo="m1", agente="qa", tokens_entrada=3, tokens_salida=7))
    assert c.llamadas == 2 and c.tokens == 25
    assert c.por_agente == {"backend": 5, "qa": 7} and c.por_modelo == {"m1": 12}


def test_el_techo_de_gasto_corta_aunque_ningun_loop_se_haya_pasado(monkeypatch):
    """Un prompt que devuelve de más no itera, así que no lo frena ningún techo de
    iteración. Son dos fallas distintas y hacen falta los dos techos."""
    monkeypatch.setattr(llm, "TECHO_DE_TOKENS_POR_CORRIDA", 100)
    c = Contador()
    c.anota(Respuesta(texto="", modelo="m", agente="ux", tokens_salida=101))
    with pytest.raises(PresupuestoAgotado, match="ux"):
        c.verifica_techo()


# --- el recorte del JSON -----------------------------------------------------------

@pytest.mark.parametrize("crudo", [
    '{"ok": true}',
    'Acá va el contrato:\n{"ok": true}\nY eso es todo.',
    '```json\n{"ok": true}\n```',
    '```\n{"ok": true}\n```',
])
def test_saca_el_envoltorio_y_deja_el_json(crudo):
    assert Salida.model_validate_json(llm._solo_json(crudo)).ok is True


def test_no_arregla_json_roto():
    """Sacar el envoltorio sí; adivinar lo que el modelo quiso decir, no."""
    with pytest.raises(Exception):
        Salida.model_validate_json(llm._solo_json('```json\n{"ok": tru\n```'))
