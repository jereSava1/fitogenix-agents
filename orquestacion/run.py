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
    # Sin default desde el 2026-09-19: con `contratar` por default, `--resume <ticket>` pelado
    # —lo que sugería el propio handoff— aprobaba el HitL 2 sin contestar nada.
    p.add_argument("--accion", choices=["contratar", "implementar", "reanalizar", "abortar"],
                   help="obligatoria con --resume")
    p.add_argument("--hasta", choices=["contrato", "completo"], default="contrato",
                   help="contrato (default): corta después del HitL 2. completo: solo en dry-run "
                        "hasta que n3/n4 generen código real (dictamen P1-1)")
    p.add_argument("--humo", action="store_true",
                   help="verifica que existan los IDs de modelo de RUTEO y sale")
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
    if not ticket and not args.humo:
        p.error("hace falta --ticket, --resume, --list o --humo")
    if args.resume and not args.accion:
        p.error("--resume exige --accion (contratar | implementar | reanalizar | abortar). "
                "Nada se aprueba por default.")
    if args.hasta == "completo" and not args.dry_run:
        p.error("--hasta completo solo corre en dry-run: n3/n4 todavía no generan código real "
                "(dictamen P1-1).")

    if args.humo or not args.dry_run:
        # P0-8: los IDs se verifican antes de gastar un token. Un 404 no se reintenta.
        from fitogenix.humo import modelos_del_ruteo, verifica_modelos
        from fitogenix.llm import SinCredencial

        try:
            fallas = verifica_modelos()
        except SinCredencial as e:
            print(f"❌ {e}")
            return FALLO
        for f in fallas:
            print(f"❌ modelo inexistente o inaccesible · {f}")
        if args.humo:
            if not fallas:
                print(f"✅ {len(modelos_del_ruteo())} modelos verificados: {', '.join(modelos_del_ruteo())}")
            return FALLO if fallas else CERRADA
        if fallas:
            print("No se gasta un token con un ruteo roto. Arreglá RUTEO en config.py.")
            return FALLO

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
        else:
            texto = args.entrada
            if args.entrada_archivo:
                texto = Path(args.entrada_archivo).read_text(encoding="utf-8")
            if not texto.strip():
                p.error("--entrada o --entrada-archivo: el pipeline no adivina el pedido")
            entrada = EstadoDelPipeline(entrada=texto, ticket=ticket, hasta=args.hasta)

        try:
            salida = app.invoke(entrada, config=cfg)
        except Exception as e:  # noqa: BLE001 - una corrida que falla deja rastro, no un traceback
            # El handoff se reescribe ANTES de salir (dictamen H2/H18): una corrida que falla
            # tiene que aparecer en `--list`, y el checkpoint permite retomarla desde el nodo.
            ruta = sessions.guarda_handoff(Handoff(
                thread_id=sessions.thread_id(ticket), ticket=ticket, nodo="fallo",
                pregunta=(f"La corrida falló: `{type(e).__name__}: {str(e)[:800]}`\n\n"
                          "El checkpoint quedó en el último nodo completo. Arreglá la causa y "
                          "retomá: reejecuta solo el nodo que falló."),
            ))
            print(f"❌ {type(e).__name__}: {str(e)[:800]}\n→ {ruta}")
            return FALLO

        # Recién ahora: si el invoke fallaba, el handoff ya estaba borrado y `--list` mentía.
        sessions.cierra_handoff(ticket)
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
                a_responder=_a_responder(carga),
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
        return CERRADA if final in ("cerrada", "contrato-listo") else FALLO


def _a_responder(carga: dict) -> tuple[str, ...]:
    if carga.get("a_responder"):
        return tuple(f"{k} — {v}" for k, v in carga["a_responder"].items())
    return tuple(f"{q.get('id', '?')} — {q.get('pregunta', '')}" for q in carga.get("preguntas") or [])


def _pregunta_legible(carga: dict) -> str:
    preguntas = carga.get("preguntas") or []
    extra = ""
    if carga.get("resumen"):
        extra += f"\n\n**Resumen del análisis:** {carga['resumen']}"
    if carga.get("contradicciones"):
        extra += "\n\n**Contradicciones (se resuelven antes de contratar):**\n" + "\n".join(
            f"- {c.get('tema')}: {c.get('fuente_a')} vs {c.get('fuente_b')}" for c in carga["contradicciones"])
    if carga.get("bloqueantes_tocados"):
        extra += f"\n\n**Bloqueantes tocados:** {', '.join(carga['bloqueantes_tocados'])}"
    if preguntas:
        return "\n".join(
            f"{i}. **{q.get('id', '')} · {q.get('pregunta','?')}** — {q.get('por_que_bloquea','')}"
            for i, q in enumerate(preguntas, 1)
        ) + extra
    if extra and carga.get("nodo") == "n1b_aclarar":
        return "El análisis no dejó preguntas. Revisá y confirmá." + extra
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
    cierres = estado.get("cierres", [])
    if cierres:
        lineas += ["", "## Cierre por nodo", ""]
        for rc in cierres:
            c = rc.cierre
            rm = c.revision_manual
            lineas += [
                f"### `{rc.nodo}` · {rc.agente} · {rc.modelo} · {c.marca.value}",
                "",
                f"**Qué se hizo:** {c.resumen}",
                "",
                "**Cambios:**" if c.cambios else "**Cambios:** ninguno declarado",
                *[f"- {x.que}" + (f" — `{x.donde}`" if x.donde else "") for x in c.cambios],
                "",
                "**Cómo se validó:**",
                *[f"- {v.metodo} · {v.resultado} · {v.referencia} ({v.origen})" for v in c.validaciones],
                "",
                (f"**Revisión manual: SÍ** — {rm.quien} · {rm.por_que}" if rm.requerida
                 else "**Revisión manual:** no hace falta"),
                *[f"- [ ] {q}" for q in rm.que_revisar],
                "",
                f"**Próximo paso:** {c.proximo_paso.accion} — {c.proximo_paso.responsable}"
                + (f" · bloqueado por: {c.proximo_paso.bloqueado_por}" if c.proximo_paso.bloqueado_por else ""),
                "",
            ]
    log = estado.get("log", [])
    if log:
        lineas += ["", "## Recorrido", ""]
        lineas += [f"- `{e.nodo}` — {e.detalle}" for e in log]
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
