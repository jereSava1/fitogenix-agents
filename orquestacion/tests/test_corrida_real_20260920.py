"""Las dos formas en que la PRIMERA CORRIDA REAL (2026-09-20, FTG-002) se murió.

Ninguna fue culpa del modelo: las dos fueron validadores pidiendo menos información de la
que el trabajo necesitaba. Salieron caras —cuatro llamadas a Opus de ~40k tokens de entrada,
dos por cada forma— así que quedan fijadas acá con los datos reales de `.fitogenix/llamadas/`.

  1. `RequisitoTrazado.puntero` era un `str`. El orquestador quiso trazar el requisito a la
     sección que manda Y al archivo donde se ve, y lo único que podía hacer era concatenar
     con `·`. 13 errores en la primera corrida, 18 en la segunda, todos del mismo tipo.
  2. `AnalisisDeRequerimiento` prohibía `listo_para_contratar=True` con contradicciones, sin
     mirar si seguían pendientes. Jere contestó las cuatro preguntas, el modelo resolvió las
     contradicciones y las dejó como registro, y el schema lo leyó como "sin resolver".
"""
import pytest

from fitogenix import det
from fitogenix.schemas import (
    AnalisisDeRequerimiento,
    Contradiccion,
    Marca,
    ProximoPaso,
    RequisitoTrazado,
    RespuestaHumana,
    aprobacion_valida,
)

PEGADOS = "CONTEXT.md §3.1 · fitogenix-native/src/screens/GuideScreen.tsx → TIERS"


# --- 1 · un requisito puede necesitar más de un puntero ------------------------------

def test_un_requisito_traza_a_la_autoridad_y_a_la_evidencia():
    r = RequisitoTrazado(
        enunciado="la guía no transcribe los cortes",
        punteros=["CONTEXT.md §3.1", "fitogenix-native/src/screens/GuideScreen.tsx → TIERS"],
        marca=Marca.SIN_CONTRASTAR)
    assert r.puntero == "CONTEXT.md §3.1", "la autoridad va primero"
    assert len(r.punteros) == 2


def test_el_singular_sigue_valiendo_como_lista_de_uno():
    r = RequisitoTrazado(enunciado="x", puntero="CONTEXT.md §3.1", marca=Marca.VERIFICADO)
    assert r.punteros == ["CONTEXT.md §3.1"]


def test_dos_punteros_pegados_en_una_cadena_siguen_sin_entrar():
    """Lo que se arregla es el campo, no el formato: un puntero sigue siendo uno."""
    with pytest.raises(ValueError, match="puntero inválido"):
        RequisitoTrazado(enunciado="x", puntero=PEGADOS, marca=Marca.SIN_CONTRASTAR)


def test_el_escalado_mira_todos_los_punteros_no_solo_el_primero():
    a = AnalisisDeRequerimiento(
        resumen="[test] el motor aparece recién en el segundo puntero del requisito",
        requisitos=[RequisitoTrazado(
            enunciado="x", marca=Marca.SIN_CONTRASTAR,
            punteros=["CONTEXT.md §1.6",
                      "fitogenix-server/src/domain/product/scoring/constants.ts → TIERS"])])
    assert det.escalado_del_analisis(a)[0] is True


# --- 2 · una contradicción resuelta es registro, no pendiente -------------------------

def _analisis(contradicciones, listo=True):
    return AnalisisDeRequerimiento(
        resumen="[test] análisis de la segunda ronda, con el humano ya contestado",
        listo_para_contratar=listo, contradicciones=contradicciones)


RESUELTA = Contradiccion(
    tema="Alcance de FTG-002 vs. criterio A-2",
    fuente_a="Handoff paso 4: mobile borra el TIERS local",
    fuente_b="Criterio A-2: el barrido completo da 0 hallazgos",
    resuelve="orchestrator",
    resolucion="Jere acotó el alcance a GuideScreen.tsx y A-2 se reescribe sobre los "
               "archivos del alcance; las otras dos copias salen en ticket propio.")
PENDIENTE = RESUELTA.model_copy(update={"resolucion": None})


def test_una_contradiccion_con_resolucion_no_frena_el_contrato():
    a = _analisis([RESUELTA])
    assert a.listo_para_contratar and not RESUELTA.pendiente
    assert aprobacion_valida(a, RespuestaHumana(ronda=2, aprobado=True)) is True


def test_una_contradiccion_sin_resolucion_sigue_frenando():
    with pytest.raises(ValueError, match="sin `resolucion`"):
        _analisis([PENDIENTE])
    a = _analisis([PENDIENTE], listo=False)
    assert aprobacion_valida(a, RespuestaHumana(ronda=2, aprobado=True)) is False


def test_la_resolucion_no_puede_ser_un_ok_pelado():
    with pytest.raises(ValueError):
        RESUELTA.model_copy(update={"resolucion": "ok"}).model_validate(
            {**RESUELTA.model_dump(), "resolucion": "ok"})


# --- 3 · el próximo paso del cierre no entra en un tuit -------------------------------

def test_un_proximo_paso_real_entra():
    real = ("Contratar a architect (escalado a Opus) para que fije cómo llega la tabla de "
            "bandas al cliente sin que el cliente importe TIERS, con el alcance acotado a "
            "GuideScreen.tsx; el contrato arrastra el contrato de API en el mismo commit "
            "(CONTEXT.md §5.6) y enumera las tres puntas aunque dos no cambien.")
    assert len(real) > 280
    assert ProximoPaso(accion=real, responsable="architect").accion == real


# --- 4 · lo que la SEGUNDA corrida real chocó: citar el ticket y el prompt del dueño ---

from fitogenix.schemas import PunteroInvalido, valida_puntero  # noqa: E402


@pytest.mark.parametrize("p", [
    "FTG-002.md sección Criterio de aceptación",      # los tickets no numeran sus secciones
    "tareas/FTG-002-guia-contradice-al-motor.md sección Riesgo",
    "01-agente-ux.md",                                 # el documento del dueño, entero
    "agents/03-agente-backend.md",
    "BITACORA_DECISIONES.md → ADR-007",                # la flecha, que el modelo escribió sola
    "BITACORA_DECISIONES.md ADR-007",
    "CONVENCIONES_EQUIPO.md sección 2",                # la forma numerada de siempre
])
def test_las_formas_que_el_orquestador_necesitaba(p):
    assert valida_puntero(p) == p


@pytest.mark.parametrize("p", [
    "CONTEXT.md",                    # entero es justo lo que el cargador existe para evitar
    "NUTRICION.md",
    "nutricion/NUTRICION.md",
])
def test_los_dos_grandes_siguen_exigiendo_seccion(p):
    with pytest.raises(PunteroInvalido):
        valida_puntero(p)


def test_el_numero_de_linea_sigue_prohibido_en_cualquier_forma():
    with pytest.raises(PunteroInvalido, match="número de línea"):
        valida_puntero("FTG-002.md sección Riesgo linea ftgEngine.ts:24")


# --- 5 · y que esos punteros CARGUEN, no den [BLOQUEADO] -----------------------------

from fitogenix.context_loader import load_documento, load_pointers  # noqa: E402


def test_el_prompt_del_dueno_se_carga_entero():
    t = load_documento("01-agente-ux.md")
    assert "agente **ux**" in t or "ux" in t.lower()
    assert len(t) > 1000


def test_una_seccion_con_nombre_trae_solo_esa_seccion():
    entero = load_documento("CONVENCIONES_EQUIPO.md")
    parte = load_documento("CONVENCIONES_EQUIPO.md sección 2")
    assert len(parte) < len(entero)


def test_un_documento_que_no_existe_no_se_rellena():
    assert "[BLOQUEADO]" in load_pointers(["INVENTADO-QUE-NO-ESTA.md"])


def test_el_ticket_que_el_orquestador_esta_analizando_resuelve():
    t = load_pointers(["FTG-002.md sección Criterio de aceptación"])
    assert "[BLOQUEADO]" not in t and len(t) > 200


# --- 6 · el código citado llega al agente, o se dice por qué no ----------------------

from fitogenix.context_loader import TOPE_DE_CODIGO_BYTES, load_codigo  # noqa: E402


def test_el_archivo_citado_llega_recortado_alrededor_del_simbolo(repos_falsos, monkeypatch):
    server, _ = repos_falsos
    from fitogenix import context_loader
    import dataclasses
    monkeypatch.setattr(context_loader, "SETTINGS", dataclasses.replace(
        context_loader.SETTINGS, server_path=server))
    f = server / "src/domain/product/scoring/constants.ts"
    f.write_text("// arriba\n" * 50 + "export const TIERS = [1,2,3]\n" + "// abajo\n" * 50)
    t = load_codigo("fitogenix-server/src/domain/product/scoring/constants.ts → TIERS")
    assert "export const TIERS" in t and "constants.ts → TIERS" in t
    assert len(t.encode()) <= TOPE_DE_CODIGO_BYTES


def test_sin_el_repo_se_dice_en_vez_de_rellenar(monkeypatch, tmp_path):
    from fitogenix import context_loader
    import dataclasses
    monkeypatch.setattr(context_loader, "SETTINGS", dataclasses.replace(
        context_loader.SETTINGS, native_path=tmp_path / "no-esta"))
    t = load_pointers(["fitogenix-native/src/screens/GuideScreen.tsx → TIERS"])
    assert "[BLOQUEADO]" in t and "no está" in t


# --- 7 · el contrato no entraba en 8.000 tokens de salida (debut, 23:23) --------------

import json  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from fitogenix import llm  # noqa: E402
from fitogenix.schemas import ContratoAprobado  # noqa: E402
from fitogenix.stubs import STUB_CONTRATO  # noqa: E402


class _Cliente:
    """Devuelve las respuestas en orden y guarda con qué max_tokens se pidió cada una."""

    def __init__(self, *respuestas):
        self.respuestas, self.max_tokens = list(respuestas), []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.max_tokens.append(kw["max_tokens"])
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def _msg(stop, entrada=None):
    b = SimpleNamespace(type="tool_use", id="tu_1", name="entregar", input=entrada or {})
    b.model_dump = lambda **_: {"type": "tool_use", "id": "tu_1", "name": "entregar", "input": entrada or {}}
    return SimpleNamespace(content=[b], stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=50_000, output_tokens=8_000))


_CIERRE_OK = {
    "resumen": "Escribí el contrato de FTG-002 con sus briefs, reglas y puntas.",
    "validaciones": [{"metodo": "cita-al-ssot", "referencia": "CONTEXT.md §3.1", "resultado": "pasa"}],
    "revision_manual": {"requerida": False},
    "proximo_paso": {"accion": "delegar los briefs a cada disciplina", "responsable": "pipeline"},
}


@pytest.fixture
def real(tmp_path, monkeypatch):
    monkeypatch.delenv("FITOGENIX_DRY_RUN", raising=False)
    import dataclasses
    monkeypatch.setattr(llm, "SETTINGS", dataclasses.replace(llm.SETTINGS, state_dir=tmp_path))


def _llama(cliente, **kw):
    return llm.llama_estructurado("architect", ContratoAprobado, sistema="s", usuario="u",
                                  stub=STUB_CONTRATO, cliente=cliente, traza="FTG-002", **kw)


def test_una_entrega_cortada_se_repite_con_mas_aire(real):
    valido = {"resultado": json.loads(STUB_CONTRATO.model_dump_json()), "cierre": _CIERRE_OK}
    c = _Cliente(_msg("max_tokens"), _msg("tool_use", valido))
    contrato, _ = _llama(c, max_tokens=8_000)
    assert isinstance(contrato, ContratoAprobado)
    assert c.max_tokens == [8_000, 16_000], "duplica el techo en vez de morir"


def test_el_reintento_por_truncado_tiene_techo(real):
    c = _Cliente(*[_msg("max_tokens")] * 4)
    with pytest.raises(llm.SalidaTruncada, match="demasiado de una sola vez"):
        _llama(c, max_tokens=llm.TOPE_DE_SALIDA)
    assert c.max_tokens == [llm.TOPE_DE_SALIDA], "no reintenta una vez llegado al techo"


def test_truncado_y_validacion_no_comparten_presupuesto_de_reintentos(real):
    """Un truncado no gasta el reintento que existe para corregir un error de validación."""
    invalido = {"resultado": {"objetivo": "corto"}, "cierre": _CIERRE_OK}
    valido = {"resultado": json.loads(STUB_CONTRATO.model_dump_json()), "cierre": _CIERRE_OK}
    c = _Cliente(_msg("max_tokens"), _msg("tool_use", invalido), _msg("tool_use", valido))
    contrato, _ = _llama(c, max_tokens=8_000)
    assert isinstance(contrato, ContratoAprobado)


def test_si_la_api_rechaza_el_techo_se_baja_una_vez(real):
    valido = {"resultado": json.loads(STUB_CONTRATO.model_dump_json()), "cierre": _CIERRE_OK}
    c = _Cliente(ValueError("max_tokens: 32000 > 16000, the maximum for this model"),
                 _msg("tool_use", valido))
    contrato, _ = _llama(c, max_tokens=llm.TOPE_DE_SALIDA)
    assert isinstance(contrato, ContratoAprobado) and c.max_tokens[1] < c.max_tokens[0]


def test_el_default_dejo_de_ser_ocho_mil():
    assert llm.MAX_TOKENS == 16_000
