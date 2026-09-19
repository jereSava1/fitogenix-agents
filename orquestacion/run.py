#!/usr/bin/env python3
"""
El CLI del pipeline.

    python run.py --ticket FTG-002 --entrada-archivo ../tareas/FTG-002-*.md
    python run.py --ticket FTG-002 --dry-run        # corre el grafo entero sin modelo
    python run.py --list                            # qué quedó esperando respuesta
    python run.py --resume FTG-002 --accion contratar

**La corrida no termina cuando el proceso termina.** El diseño asume que el humano
contesta la interrupción más tarde y desde otra terminal, así que este CLI se apaga
dejando dos cosas en disco: el checkpoint, para que el grafo se pueda rearmar, y el
handoff en `.md`, para que la persona entienda qué le están preguntando sin abrir el
SQLite. Falta cualquiera de las dos y el HitL no existe.

**Códigos de salida:** 0 cerrada · 2 esperando respuesta humana · 1 escalada o abortada.
El 2 es su propio código a propósito: una corrida interrumpida no es un fracaso, pero
tampoco es un éxito, y en CI las dos cosas se tratan distinto.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

CERRADA, FALLO, ESPERANDO = 0, 1, 2


def main() -> int:
    p = argparse.ArgumentParser(description="Pipeline agéntico de Fitogenix")
    p.add_argument("--ticket", help="FTG-002, B-7, …")
    p.add_argument("--entrada", default="", help="el pedido, en texto")
    p.add_argument("--entrada-archivo", help="un .md con el ticket")
    p.add_argument("--resume", metavar="TICKET", help="retomar una corrida interrumpida")
    p.add_argument("--accion", default="contratar",
                   help="respuesta al interrupt: contratar | reanalizar | abortar")
    p.add_argument("--respuesta", action="append", default=[], metavar="PREGUNTA=TEXTO")
    p.add_argument("--list", action="store_true", help="threads esperando respuesta")
    p.add_argument("--dry-run", action="store_true", help="sin llamar a ningún modelo")
    args = p.parse_args()

    # Se setea ANTES de importar el paquete: `Settings.dry_run` lee el entorno en cada
    # llamada justamente para que esto funcione sin depender del orden de los imports.
    if args.dry_run:
        os.environ["FITOGENIX_DRY_RUN"] = "1"

    from fitogenix import sessions
    from fitogenix.graph import construye
    from fitogenix.llm import Contador
    from fitogenix.schemas import EstadoDelPipeline
    from fitogenix.sessions import Handoff, config_de

    if args.list:
        abiertos = sessions.abiertos()
        print("\n".join(abiertos) if abiertos else "(no hay corridas esperando respuesta)")
        return CERRADA

    ticket = args.resume or args.ticket
    if not ticket:
        p.error("hace falta --ticket, --resume o --list")

    contador = Contador()
    with sessions.checkpointer() as saver:
        app = construye(contador).compile(checkpointer=saver)
        cfg = config_de(ticket)

        if args.resume:
            from langgraph.types import Command

            respuestas = [
                {"pregunta": r.split("=", 1)[0], "respuesta": r.split("=", 1)[1]}
                for r in args.respuesta if "=" in r
            ]
            entrada = Command(resume={"accion": args.accion, "respuestas": respuestas})
            sessions.cierra_handoff(ticket)
        else:
            texto = args.entrada
            if args.entrada_archivo:
                texto = Path(args.entrada_archivo).read_text(encoding="utf-8")
            if not texto.strip():
                p.error("--entrada o --entrada-archivo: el pipeline no adivina el pedido")
            entrada = EstadoDelPipeline(entrada=texto, ticket=ticket)

        salida = app.invoke(entrada, config=cfg)

        pendiente = salida.get("__interrupt__") if isinstance(salida, dict) else None
        if pendiente:
            carga = getattr(pendiente[0], "value", {}) or {}
            ruta = sessions.guarda_handoff(Handoff(
                thread_id=sessions.thread_id(ticket),
                ticket=ticket,
                nodo=str(carga.get("nodo", "?")),
                pregunta=_pregunta_legible(carga),
                supuestos=tuple(carga.get("supuestos", ())),
                decisiones_abiertas=tuple(carga.get("decisiones_abiertas", ())),
                chequeos=tuple(f"{i.get('chequeo')}: {i.get('detalle')}"
                               for i in carga.get("chequeos_deterministas", ())),
            ))
            print(f"⏸  esperando respuesta · {ruta}")
            return ESPERANDO

        estado = salida if isinstance(salida, dict) else {}
        final = estado.get("estado_final", "en-curso")
        resumen = estado.get("resumen")
        md = _resumen_md(ticket, final, resumen, contador, estado)
        ruta = sessions.guarda_resumen(ticket, md)
        print(md)
        print(f"\n→ {ruta}")
        return CERRADA if final == "cerrada" else FALLO


def _pregunta_legible(carga: dict) -> str:
    preguntas = carga.get("preguntas") or []
    if preguntas:
        return "\n".join(
            f"{i}. **{q.get('pregunta','?')}** — {q.get('por_que_bloquea','')}"
            for i, q in enumerate(preguntas, 1)
        )
    if carga.get("supuestos") or carga.get("decisiones_abiertas"):
        return ("El contrato quedó con supuestos o decisiones abiertas. "
                "Están listados abajo: contestá los que puedas y retomá.")
    return "El pipeline se interrumpió y no dejó preguntas: revisá el nodo."


def _resumen_md(ticket, final, resumen, contador, estado) -> str:
    rondas = {"aclaracion": estado.get("ronda_aclaracion", 0),
              "contrato": estado.get("ronda_contrato", 0),
              "revision": estado.get("ronda_revision", 0)}
    lineas = [
        f"# {ticket} — corrida {final}",
        "",
        f"- **Llamadas al modelo:** {contador.llamadas}",
        f"- **Tokens:** {contador.tokens_entrada} entrada · {contador.tokens_salida} salida",
        f"- **Rondas:** " + " · ".join(f"{k} {v}" for k, v in rondas.items()),
        f"- **Veredicto:** {getattr(getattr(resumen, 'veredicto', None), 'value', '—')}",
        f"- **Incertidumbres deterministas:** {len(estado.get('incertidumbres', []))}",
    ]
    if contador.por_agente:
        lineas += ["", "## Tokens de salida por agente", ""]
        lineas += [f"- `{a}`: {t}" for a, t in sorted(contador.por_agente.items())]
    log = estado.get("log", [])
    if log:
        lineas += ["", "## Recorrido", ""]
        lineas += [f"- `{e.nodo}` — {e.detalle}" for e in log]
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
