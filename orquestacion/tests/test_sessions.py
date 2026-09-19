"""Reanudar. Si esto no anda, el HitL es una promesa.

El test que importa es `test_otro_proceso_ve_el_checkpoint`: el diseño asume que el humano
contesta la interrupción más tarde y desde otra terminal. Un checkpoint que solo existe
dentro del proceso que lo escribió no sirve para eso, y desde adentro se ve idéntico.
"""
import pytest

from fitogenix import sessions
from fitogenix.sessions import Handoff, TicketInvalido


@pytest.fixture(autouse=True)
def estado_aparte(tmp_path, monkeypatch):
    """Cada test con su propio `.fitogenix/`, para no tocar el del repo."""
    monkeypatch.setenv("FITOGENIX_STATE_DIR", str(tmp_path / ".fitogenix"))
    monkeypatch.setenv("FITOGENIX_CHECKPOINT_DB", str(tmp_path / ".fitogenix" / "cp.sqlite"))
    from fitogenix import config
    monkeypatch.setattr(config, "SETTINGS", config.Settings())
    monkeypatch.setattr(sessions, "SETTINGS", config.SETTINGS)
    yield


# --- el thread_id ------------------------------------------------------------------

def test_el_thread_id_sale_del_ticket_y_es_estable():
    """Quien vuelve al día siguiente se acuerda del ticket, no de un uuid."""
    assert sessions.thread_id("ftg-002") == "FTG-002" == sessions.thread_id(" FTG-002 ")


@pytest.mark.parametrize("malo", ["../../etc/passwd", "FTG-002/x", "", "no-es-un-ticket", "F-99999"])
def test_lo_que_no_sirve_como_nombre_de_archivo_se_rechaza(malo):
    """Esto arma un nombre de archivo. No se sanea, se rechaza."""
    with pytest.raises(TicketInvalido):
        sessions.thread_id(malo)


def test_el_config_de_langgraph_lo_arma_este_modulo():
    cfg = sessions.config_de("FTG-002")["configurable"]
    assert cfg["thread_id"] == "FTG-002"
    # `checkpoint_ns` lo exige el saver de SQLite: sin él, `put` tira KeyError.
    assert cfg["checkpoint_ns"] == ""


# --- el checkpointer ---------------------------------------------------------------

def test_otro_proceso_ve_el_checkpoint(monkeypatch):
    """**El test del módulo.** Se escribe con un saver y se lee con otro, recién
    construido, como haría una terminal distinta al día siguiente."""
    monkeypatch.setenv("FITOGENIX_CHECKPOINTER", "sqlite")
    from fitogenix import config
    monkeypatch.setattr(sessions, "SETTINGS", config.Settings())

    cfg = sessions.config_de("FTG-002")
    from langgraph.checkpoint.base import empty_checkpoint
    punto = {**empty_checkpoint(), "channel_values": {"paso": "n2_contrato"}}

    with sessions.checkpointer() as saver:
        saver.put(cfg, punto, {"source": "update", "step": 1}, {})

    with sessions.checkpointer() as otro:          # otro proceso, otra terminal
        leido = otro.get(cfg)

    assert leido is not None
    assert leido["channel_values"]["paso"] == "n2_contrato"


def test_memory_es_solo_para_tests(monkeypatch):
    """Existe, pero una corrida real guardada ahí no se puede reanudar."""
    monkeypatch.setenv("FITOGENIX_CHECKPOINTER", "memory")
    from fitogenix import config
    monkeypatch.setattr(sessions, "SETTINGS", config.Settings())
    with sessions.checkpointer() as saver:
        assert "InMemory" in saver.__class__.__name__ or "Memory" in saver.__class__.__name__


# --- el handoff --------------------------------------------------------------------

def _handoff() -> Handoff:
    return Handoff(
        thread_id="FTG-002", ticket="FTG-002", nodo="n2_contrato",
        pregunta="¿El umbral del sello se mueve con TIERS o es un corte aparte?",
        supuestos=("no corrí npm test",),
        decisiones_abiertas=("D-2 · orchestrator: ¿entran HomeScreen y ScanResultScreen?",),
        chequeos=("presupuesto-excedido: el Brief de backend cita §8 entero",),
    )


def test_el_handoff_se_lee_sin_abrir_el_sqlite():
    """La otra mitad de reanudar: el humano tiene que entender qué le preguntan."""
    p = sessions.guarda_handoff(_handoff())
    md = p.read_text(encoding="utf-8")
    assert "¿El umbral del sello" in md
    assert "n2_contrato" in md
    assert "python run.py --resume FTG-002" in md
    assert "D-2" in md and "presupuesto-excedido" in md


def test_un_handoff_sin_supuestos_no_deja_secciones_vacias():
    md = Handoff(thread_id="FTG-9", ticket="FTG-9", nodo="n1", pregunta="¿?").a_markdown()
    assert "Supuestos" not in md and "Decisiones abiertas" not in md


def test_el_handoff_se_borra_al_retomar():
    """Un handoff que sobrevive al retomado le miente a quien lista los threads abiertos,
    y esa lista es lo primero que mira alguien que vuelve después de dos días."""
    sessions.guarda_handoff(_handoff())
    assert sessions.hay_handoff("FTG-002") and sessions.abiertos() == ["FTG-002"]
    sessions.cierra_handoff("FTG-002")
    assert not sessions.hay_handoff("FTG-002") and sessions.abiertos() == []


def test_cerrar_dos_veces_no_rompe():
    sessions.cierra_handoff("FTG-002")
    sessions.cierra_handoff("FTG-002")


def test_leer_un_handoff_que_no_existe_lo_dice():
    with pytest.raises(FileNotFoundError, match="ya se retomó"):
        sessions.lee_handoff("FTG-404")


def test_los_abiertos_vienen_ordenados():
    for t in ("FTG-9", "FTG-2", "FTG-5"):
        sessions.guarda_handoff(Handoff(thread_id=t, ticket=t, nodo="n1", pregunta="¿?"))
    assert sessions.abiertos() == ["FTG-2", "FTG-5", "FTG-9"]


# --- el resumen --------------------------------------------------------------------

def test_se_guarda_el_resumen_de_las_que_cierran_solas_tambien():
    """Si solo se registraran las que salieron mal, no habría con qué comparar."""
    p = sessions.guarda_resumen("FTG-002", "# cerró sola\n")
    assert p.exists() and p.name.startswith("FTG-002-")
    otro = sessions.guarda_resumen("FTG-002", "# otra corrida\n")
    assert otro != p or otro.read_text(encoding="utf-8") == "# otra corrida\n"


def test_los_schemas_quedan_declarados_para_el_checkpoint():
    """langgraph avisa hoy y **bloquea mañana** al deserializar tipos que nadie registró.
    El día que bloquee, el estado se guardaría bien y no se podría volver a leer — la
    forma más silenciosa de perder una corrida. La lista se arma enumerando el módulo,
    así que un schema nuevo entra solo."""
    serde = sessions._serde()
    permitidos = getattr(serde, "_allowed_msgpack_modules", None) or []
    nombres = {n for m, n in permitidos if m == "fitogenix.schemas"}
    assert {"EventoDeLog", "ContratoAprobado", "Marca", "EstadoDelPipeline"} <= nombres
