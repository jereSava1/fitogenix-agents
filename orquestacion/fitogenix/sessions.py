"""
Reanudar. **Lo que hace que el HitL no sea una promesa.**

`PROPUESTA_grafo_fase2.md` sección 2 asume que el humano contesta la interrupción *más
tarde* y *desde otra terminal*. Eso tiene dos consecuencias que este módulo resuelve, y
que son distintas entre sí:

1. **El grafo tiene que poder volver a armarse.** Eso lo da el checkpointer en SQLite:
   estado serializado por `thread_id`, en un archivo, no en el proceso.
2. **El humano tiene que poder entender qué le están preguntando sin leer el SQLite.**
   Eso lo da el handoff: un `.md` por thread interrumpido, escrito para una persona.

Falta cualquiera de las dos y el HitL no existe. Con solo (1), el que reanuda tiene que
adivinar qué se estaba preguntando. Con solo (2), no hay nada que reanudar.

**El `thread_id` es determinista y sale del ticket.** No es un uuid: quien vuelve al día
siguiente sabe el ticket, no el uuid. Que sea derivable es lo que permite `--resume FTG-002`
en vez de `--resume 3f2a…`.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import SETTINGS

#: Los tickets válidos, mismo vocabulario que `schemas._TICKET`. Se re-declara acotado
#: acá porque esto arma un NOMBRE DE ARCHIVO: lo que entre tiene que ser seguro en disco,
#: y esa es una preocupación distinta de la del schema.
_TICKET_SEGURO = re.compile(r"^[A-Za-z]{1,6}-\d{1,4}$")


class TicketInvalido(ValueError):
    """El ticket va a un nombre de archivo. No se sanea: se rechaza."""


@dataclass(frozen=True)
class Handoff:
    """Lo que se le deja escrito al humano cuando el grafo se interrumpe."""

    thread_id: str
    ticket: str
    nodo: str
    pregunta: str
    supuestos: tuple[str, ...] = ()
    decisiones_abiertas: tuple[str, ...] = ()
    chequeos: tuple[str, ...] = ()
    #: `ID — texto` de cada ítem que hay que contestar (P1…, S1/D1/C1…). Sin esto el humano
    #: no puede atar su respuesta a lo que responde, y el OK no cuenta.
    a_responder: tuple[str, ...] = ()
    cuando: str = ""

    def a_markdown(self) -> str:
        def lista(titulo: str, xs: tuple[str, ...]) -> str:
            if not xs:
                return ""
            cuerpo = "\n".join(f"- {x}" for x in xs)
            return f"\n## {titulo}\n\n{cuerpo}\n"

        return (
            f"# {self.thread_id} — esperando respuesta\n\n"
            f"- **Ticket:** {self.ticket}\n"
            f"- **Nodo:** `{self.nodo}`\n"
            f"- **Interrumpido:** {self.cuando or ahora()}\n\n"
            f"## La pregunta\n\n{self.pregunta}\n"
            + lista("Supuestos que declaró el modelo", self.supuestos)
            + lista("Decisiones abiertas", self.decisiones_abiertas)
            + lista("Lo que verificó Python, y el modelo no puede declinar", self.chequeos)
            + lista("A contestar (cada ID necesita respuesta para que el OK cuente)", self.a_responder)
            + self._como_retomar()
        )

    def _como_retomar(self) -> str:
        """`--accion` es obligatoria (2026-09-19). Antes el handoff sugería
        `--resume <ticket>` pelado, y eso aprobaba por default."""
        ids = [x.split(" — ", 1)[0] for x in self.a_responder]
        resp = " ".join(f'--respuesta "{i}=…"' for i in ids) or '--respuesta "P1=…"'
        return (
            "\n---\n\nPara retomar — `--accion` es obligatoria:\n\n```\n"
            f"# contestar y seguir\npython run.py --resume {self.ticket} --accion contratar {resp}\n"
            + (f"# aceptar el contrato tal cual, con sus supuestos (decisión explícita)\n"
               f"python run.py --resume {self.ticket} --accion implementar\n"
               if self.nodo == "n2b_aclarar_contrato" else "")
            + f"# cortar acá\npython run.py --resume {self.ticket} --accion abortar\n```\n"
        )


def ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def thread_id(ticket: str) -> str:
    """Determinista y legible. Quien vuelve mañana se acuerda del ticket, no de un uuid."""
    t = ticket.strip().upper()
    if not _TICKET_SEGURO.match(t):
        raise TicketInvalido(
            f"ticket {ticket!r} no sirve como nombre de archivo. Se espera algo como FTG-002."
        )
    return t


@contextmanager
def checkpointer() -> Iterator[Any]:
    """El checkpointer de la corrida, como context manager.

    `memory` existe **solo para tests**: un `MemorySaver` muere con el proceso, así que
    una corrida real guardada ahí no se puede reanudar — que es justamente lo único que
    este módulo tiene que garantizar. Por eso el default de `config` es `sqlite` y esto no
    lo adivina: lo lee.
    """
    if SETTINGS.checkpointer == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        yield MemorySaver()
        return

    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    db = Path(SETTINGS.checkpoint_db)
    db.parent.mkdir(parents=True, exist_ok=True)
    # `check_same_thread=False` porque langgraph puede tocar la conexión desde otro hilo;
    # el acceso concurrente real lo serializa SQLite con su propio lock.
    conn = sqlite3.connect(str(db), check_same_thread=False)
    try:
        yield SqliteSaver(conn, serde=_serde())
    finally:
        conn.close()


def config_de(ticket: str) -> dict[str, Any]:
    """El `config` que come langgraph. Se arma acá para que ningún nodo invente la clave.

    `checkpoint_ns` va vacío y **va sí o sí**: el saver de SQLite lo indexa y revienta con
    `KeyError` si falta. Lo encontró `test_otro_proceso_ve_el_checkpoint` —el único test
    que escribe con un saver y lee con otro—, no la suite en memoria, que nunca lo toca.
    Sin ese test, el primer intento de reanudar en serio habría sido el que lo descubría.
    """
    return {"configurable": {"thread_id": thread_id(ticket), "checkpoint_ns": ""}}


# --- el handoff en disco ----------------------------------------------------------

def _ruta_handoff(tid: str) -> Path:
    return SETTINGS.sessions_dir / f"{tid}.md"


def guarda_handoff(h: Handoff) -> Path:
    """Escribe el `.md` del thread interrumpido y devuelve dónde quedó."""
    SETTINGS.sessions_dir.mkdir(parents=True, exist_ok=True)
    p = _ruta_handoff(h.thread_id)
    p.write_text(h.a_markdown(), encoding="utf-8")
    return p


def hay_handoff(ticket: str) -> bool:
    return _ruta_handoff(thread_id(ticket)).exists()


def lee_handoff(ticket: str) -> str:
    p = _ruta_handoff(thread_id(ticket))
    if not p.exists():
        raise FileNotFoundError(
            f"no hay handoff para {ticket}: o nunca se interrumpió, o ya se retomó."
        )
    return p.read_text(encoding="utf-8")


def cierra_handoff(ticket: str) -> None:
    """Se llama al reanudar. Un handoff que sigue en disco después de retomado le miente
    a quien liste los threads abiertos — y esa lista es lo primero que mira alguien que
    vuelve después de dos días."""
    p = _ruta_handoff(thread_id(ticket))
    if p.exists():
        p.unlink()


def abiertos() -> list[str]:
    """Los threads esperando respuesta, ordenados. Lo que `run.py --list` imprime."""
    if not SETTINGS.sessions_dir.exists():
        return []
    return sorted(p.stem for p in SETTINGS.sessions_dir.glob("*.md"))


# --- el resumen de una corrida terminada ------------------------------------------

def guarda_resumen(ticket: str, markdown: str) -> Path:
    """Un `.md` por corrida terminada — camino feliz y escalado por igual.

    Las dos se guardan a propósito: si solo se registraran las que salieron mal, no habría
    con qué comparar, y la pregunta que importa después de un mes es qué cambió entre las
    que cerraron solas y las que no.
    """
    SETTINGS.summaries_dir.mkdir(parents=True, exist_ok=True)
    tid = thread_id(ticket)
    sello = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    p = SETTINGS.summaries_dir / f"{tid}-{sello}.md"
    p.write_text(markdown, encoding="utf-8")
    return p


def _serde():
    """El serializador del checkpoint, con nuestros schemas declarados.

    Sin declararlos, langgraph **avisa hoy y bloquea mañana** al deserializar tipos que
    nadie registró. El día que bloquee, reanudar deja de funcionar: el estado se guardaría
    bien y no se podría volver a leer, que es la forma más silenciosa de perder una
    corrida. Se declara `fitogenix.schemas` y nada más — lo que entra al checkpoint son
    los modelos del pipeline.

    Best-effort a propósito: si la versión instalada no acepta el parámetro, reanudar
    tiene que seguir andando igual, solo que con el aviso.
    """
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    # La lista se arma por enumeración del módulo, no a mano: un schema nuevo entra solo.
    # Escrita a mano, el día que alguien agregue un modelo al estado, reanudar se rompería
    # y el error aparecería recién en la corrida que hubiera que retomar.
    from enum import Enum

    from pydantic import BaseModel

    from . import schemas

    permitidos = [
        ("fitogenix.schemas", n)
        for n, o in vars(schemas).items()
        if isinstance(o, type) and issubclass(o, (BaseModel, Enum)) and o.__module__ == schemas.__name__
    ]
    try:
        return JsonPlusSerializer(allowed_msgpack_modules=permitidos)
    except TypeError:  # pragma: no cover - versiones sin el parámetro
        return None
