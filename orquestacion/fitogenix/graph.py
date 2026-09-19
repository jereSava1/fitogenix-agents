"""
El grafo. Nueve nodos, dos `interrupt()`, tres techos, **una sola salida**.

Es la transcripción del diagrama de `PROPUESTA_grafo_fase2.md` sección 1. Lo que hay que
saber para leerlo:

**`n6_resumen` es la única salida, también cuando la corrida no cierra.** Si escalar
terminara en `END`, la corrida que más necesita dejar algo escrito —la que alguien va a
levantar sin haber estado— sería justamente la que no deja nada.

**Los dos `interrupt()` no son simétricos.** El primero es incondicional: el análisis
siempre vuelve al humano. El segundo dispara **por incertidumbre, no por tema**, y su
condición es la unión de dos fuentes: lo que el modelo declara (`supuestos`,
`decisiones_abiertas`) más lo que verifica Python (`det.todos`). La segunda existe porque
la primera sola no alcanza: *declarar menos incertidumbre es el camino más corto a no ser
interrumpido*.

**Los techos se consultan en el borde, no se declaran y ya.** Un techo escrito en un dict
que ningún borde condicional lee es un techo que no existe.
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from . import det
from .config import SETTINGS
from .context_loader import load_pointers
from .llm import Contador, llama_estructurado
from .schemas import (
    TECHOS,
    AnalisisDeRequerimiento,
    ContratoAprobado,
    EstadoDelPipeline,
    EventoDeLog,
    RespuestaHumana,
    aprobacion_valida,
    ReporteDeRevision,
    Marca,
    ResumenDeCorrida,
    hay_que_preguntar,
    rutea_revision,
)
from .stubs import (
    STUB_ANALISIS,
    STUB_ANALISIS_RESUELTO,
    STUB_CONTRATO,
    STUB_ENTREGA,
    STUB_REPORTE,
    STUB_REVISION,
    stub_paquete,
)


def _log(nodo: str, detalle: str) -> list[EventoDeLog]:
    return [EventoDeLog(nodo=nodo, detalle=detalle)]


def _sistema(agente: str) -> str:
    """El prompt del agente, de su `.md`. No se arma acá ni se resume: se lee entero.

    Es el único contexto que el agente recibe completo; todo lo demás entra por punteros,
    que es de dónde sale el ahorro.
    """
    return SETTINGS.prompt_de(agente).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# n1a · analizar — el único nodo que lee CONTEXT.md entero                     #
# --------------------------------------------------------------------------- #

def n1a_analizar(estado: EstadoDelPipeline, *, contador: Contador | None = None) -> dict[str, Any]:
    respuestas = "\n".join(
        f"- {q} → {a}" for r in estado.respuestas_humanas for q, a in r.respuestas.items()
    )
    analisis, _ = llama_estructurado(
        "orchestrator", AnalisisDeRequerimiento,
        sistema=_sistema("orchestrator"),
        usuario=(
            f"Ticket: {estado.ticket}\n\nPedido:\n{estado.entrada}\n"
            + (f"\nRespuestas del humano en rondas anteriores:\n{respuestas}\n" if respuestas else "")
        ),
        # El stub cambia según la ronda a propósito: en la segunda vuelta ya no tiene
        # preguntas abiertas, que es lo que un modelo real haría después de que el humano
        # las contestó. Con un stub fijo, `aprobacion_valida` no dejaría aprobar nunca y
        # el dry-run recorrería solo el camino del techo.
        stub=STUB_ANALISIS_RESUELTO if estado.respuestas_humanas else STUB_ANALISIS,
        contador=contador,
    )
    return {
        "analisis": analisis,
        "ronda_aclaracion": estado.ronda_aclaracion + 1,
        "log": _log("n1a_analizar", f"ronda {estado.ronda_aclaracion + 1}"),
    }


# --------------------------------------------------------------------------- #
# n1b · aclarar — HitL 1, SIEMPRE                                              #
# --------------------------------------------------------------------------- #

def n1b_aclarar(estado: EstadoDelPipeline) -> dict[str, Any]:
    """El primer `interrupt()`, incondicional.

    Lo que se le manda al humano no es "¿está bien?": son las preguntas concretas que el
    análisis dejó abiertas, más los requisitos trazados. Preguntar "¿apruebo?" invita a un
    sí automático; preguntar cinco cosas puntuales, no.
    """
    a = estado.analisis
    respuesta = interrupt({
        "nodo": "n1b_aclarar",
        "ticket": estado.ticket,
        "ronda": estado.ronda_aclaracion,
        "techo": TECHOS["aclaracion"],
        "preguntas": [p.model_dump() for p in (a.preguntas_abiertas if a else [])],
        "requisitos": [r.model_dump() for r in (a.requisitos if a else [])],
        "contradicciones": [c.model_dump() for c in (a.contradicciones if a else [])],
    })
    return _absorbe_respuesta(estado, respuesta, ronda=estado.ronda_aclaracion)


_OK = ("contratar", "continuar", "ok", "si", "sí", "aprobar")


def _absorbe_respuesta(
    estado: EstadoDelPipeline, respuesta: Any, *, ronda: int
) -> dict[str, Any]:
    """Lo que devuelve un `interrupt()` viene del humano y puede tener cualquier forma.

    Se normaliza en un solo lugar: si cada nodo lo interpretara a su manera, la diferencia
    entre "abortar" y "abortar." decidiría el destino de una corrida.

    **El OK del humano no alcanza por sí solo.** `aprobacion_valida` lo cruza contra el
    análisis: un `aprobado=True` no cuenta mientras queden preguntas abiertas o
    contradicciones sin resolver. Sin ese cruce, apretar "contratar" saltearía el análisis
    entero — y apretar el botón que sigue es lo más fácil que hay.
    """
    if isinstance(respuesta, dict):
        accion = str(respuesta.get("accion", "continuar")).strip().lower()
        dichos = respuesta.get("respuestas", []) or []
        comentario = str(respuesta.get("comentario", ""))
    else:
        accion = str(respuesta).strip().lower()
        dichos, comentario = [], ""

    pares = {
        str(d["pregunta"]): str(d.get("respuesta", ""))
        for d in dichos if isinstance(d, dict) and d.get("pregunta")
    }
    dicho = RespuestaHumana(
        ronda=max(1, ronda), aprobado=accion in _OK,
        respuestas=pares, comentario_libre=comentario,
    )
    aprobado = dicho.aprobado and (
        estado.analisis is None or aprobacion_valida(estado.analisis, dicho)
    )
    nota = "aprobado" if aprobado else (
        "OK sin efecto: el análisis todavía tiene preguntas abiertas" if dicho.aprobado
        else f"respondió: {accion}"
    )
    return {
        "respuestas_humanas": [dicho],
        "aprobacion_humana": aprobado,
        "estado_final": "abortada-por-techo" if accion == "abortar" else "en-curso",
        "log": _log("hitl", nota),
    }


def rutea_aclaracion(estado: EstadoDelPipeline) -> Literal["contratar", "reanalizar", "abortar"]:
    if estado.estado_final == "abortada-por-techo":
        return "abortar"
    if estado.aprobacion_humana:
        return "contratar"
    # El techo se consulta acá, no en el nodo: es el borde el que decide seguir o no.
    if estado.ronda_aclaracion >= TECHOS["aclaracion"]:
        return "abortar"
    return "reanalizar"


# --------------------------------------------------------------------------- #
# n2 · contrato — el arquitecto                                                #
# --------------------------------------------------------------------------- #

def n2_contrato(estado: EstadoDelPipeline, *, contador: Contador | None = None) -> dict[str, Any]:
    a = estado.analisis
    # Los punteros que el análisis trazó. El arquitecto recibe ESO, no `CONTEXT.md`
    # entero: el único nodo que lo lee completo es `n1a_analizar` (sección 1).
    punteros = [r.puntero for r in a.requisitos] if a else []
    contrato, _ = llama_estructurado(
        "architect", ContratoAprobado,
        sistema=_sistema("architect"),
        usuario=(
            f"Ticket: {estado.ticket}\n\nAnálisis:\n"
            f"{a.model_dump_json(indent=2) if a else '{}'}\n\n"
            f"Contexto citado:\n{load_pointers(punteros) if punteros else '(sin punteros)'}"
        ),
        stub=STUB_CONTRATO,
        escalado=bool(a and a.toca_scoring) if hasattr(a, "toca_scoring") else False,
        contador=contador,
    )
    return {
        "contrato": contrato,
        "ronda_contrato": estado.ronda_contrato + 1,
        "log": _log("n2_contrato", f"ronda {estado.ronda_contrato + 1}"),
    }


# --------------------------------------------------------------------------- #
# n2b · aclarar contrato — HitL 2, SOLO por incertidumbre                      #
# --------------------------------------------------------------------------- #

def n2b_aclarar_contrato(estado: EstadoDelPipeline) -> dict[str, Any]:
    """El segundo `interrupt()`. **No siempre corre: el borde decide.**

    Este nodo solo se alcanza cuando `_hay_dudas` dio verdadero, y esa condición mezcla lo
    que el modelo declaró con lo que Python verificó. El nodo en sí no vuelve a decidir:
    si llegó acá, pregunta.
    """
    c = estado.contrato
    respuesta = interrupt({
        "nodo": "n2b_aclarar_contrato",
        "ticket": estado.ticket,
        "supuestos": list(c.supuestos) if c else [],
        "decisiones_abiertas": list(c.decisiones_abiertas) if c else [],
        "chequeos_deterministas": [i.model_dump() for i in estado.incertidumbres],
    })
    return _absorbe_respuesta(estado, respuesta, ronda=max(1, estado.ronda_contrato))


def _dudas(estado: EstadoDelPipeline) -> list[Any]:
    """Los chequeos deterministas sobre el contrato. Corren **después** del modelo, así
    que su resultado es un hecho del estado y el modelo no lo puede declinar ni suavizar."""
    if estado.contrato is None:
        return []
    return det.todos(estado.contrato)


def marca_incertidumbres(estado: EstadoDelPipeline) -> dict[str, Any]:
    """Nodo determinista entre `n2_contrato` y el borde: deja los chequeos EN EL ESTADO.

    Podrían calcularse dentro del borde condicional y no quedar en ningún lado. Quedan
    porque el handoff que lee el humano tiene que poder mostrar qué levantó Python, no
    solo qué dudó el modelo.
    """
    d = _dudas(estado)
    return {"incertidumbres": d, "log": _log("chequeos", f"{len(d)} incertidumbre(s) deterministas")}


def rutea_contrato(estado: EstadoDelPipeline) -> Literal["preguntar", "implementar"]:
    c = estado.contrato
    if c is not None and hay_que_preguntar(c, list(estado.incertidumbres)):
        return "preguntar"
    return "implementar"


def rutea_post_contrato(estado: EstadoDelPipeline) -> Literal["implementar", "recontratar", "abortar"]:
    if estado.estado_final == "abortada-por-techo":
        return "abortar"
    if estado.ronda_contrato >= TECHOS["contrato"]:
        # Techo 1: sin aprobación humana de rutina, un segundo ciclo silencioso sería el
        # pipeline discutiendo consigo mismo.
        return "implementar" if estado.aprobacion_humana else "abortar"
    return "recontratar" if not estado.aprobacion_humana else "implementar"


# --------------------------------------------------------------------------- #
# n3 · implementar — una entrega por disciplina con Brief                      #
# --------------------------------------------------------------------------- #

def n3_implementar(estado: EstadoDelPipeline, *, contador: Contador | None = None) -> dict[str, Any]:
    c = estado.contrato
    entregas, reportes = [], []
    for brief in (c.briefs if c else []):
        agente = brief.destinatario.value
        contexto = load_pointers([p.ref for p in brief.contexto_relevante])
        _, _r = llama_estructurado(
            agente, type(STUB_REPORTE),
            sistema=_sistema(agente),
            usuario=f"Brief:\n{brief.model_dump_json(indent=2)}\n\nContexto:\n{contexto}",
            stub=STUB_REPORTE,
            contador=contador,
        )
        reportes.append(STUB_REPORTE if SETTINGS.dry_run else _r)
        entregas.append(STUB_ENTREGA)
    return {
        "entregas": entregas,
        "reportes": [r for r in reportes if hasattr(r, "estado")],
        "log": _log("n3_implementar", f"{len(entregas)} entrega(s)"),
    }


# --------------------------------------------------------------------------- #
# n4 · empaquetar PR — herramienta, no agente                                  #
# --------------------------------------------------------------------------- #

def n4_empaquetar_pr(estado: EstadoDelPipeline) -> dict[str, Any]:
    """Mecánica de git, no juicio. No pasa por modelo a propósito: meter un agente acá
    sería pagarle a Opus para que componga un nombre de rama."""
    return {
        "paquete_pr": stub_paquete(estado.ticket),
        "log": _log("n4_empaquetar_pr", "paquete armado"),
    }


# --------------------------------------------------------------------------- #
# n5 · revisar — QA, y NUNCA se abarata (sección 5)                            #
# --------------------------------------------------------------------------- #

def n5_revisar(estado: EstadoDelPipeline, *, contador: Contador | None = None) -> dict[str, Any]:
    ronda = estado.ronda_revision + 1
    revision, _ = llama_estructurado(
        "revisor", ReporteDeRevision,
        sistema=_sistema("qa"),
        usuario=(
            f"Paquete:\n{estado.paquete_pr.model_dump_json(indent=2) if estado.paquete_pr else '{}'}\n\n"
            f"Contrato:\n{estado.contrato.model_dump_json(indent=2) if estado.contrato else '{}'}"
        ),
        stub=STUB_REVISION.model_copy(update={"ronda": ronda}),
        contador=contador,
    )
    return {
        "revisiones": [revision],
        "ronda_revision": ronda,
        "log": _log("n5_revisar", f"ronda {ronda} · {revision.veredicto.value}"),
    }


def rutea_revision_nodo(
    estado: EstadoDelPipeline,
) -> Literal["continuar", "reimplementar", "recontratar", "escalar"]:
    """El ruteo vive en `schemas.rutea_revision` — veredicto primero, severidad después.

    Acá solo se traduce a nombres de borde. Que la regla viva en el schema y no en el
    grafo es lo que permite testearla sin levantar langgraph, y es donde está escrito el
    agujero que PampaGrow tapó: una revisión rechazada con hallazgos todos `menor`
    devolvía "continuar" y la corrida cerraba en verde.
    """
    rev = estado.ultima_revision
    return "escalar" if rev is None else rutea_revision(rev)  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# n_escalar · el handoff — y sigue hacia n6, no hacia END                      #
# --------------------------------------------------------------------------- #

def n_escalar(estado: EstadoDelPipeline) -> dict[str, Any]:
    motivo = estado.techo_alcanzado or "revisión no aprobada"
    return {
        "estado_final": "escalada",
        "log": _log("n_escalar", f"escalada por {motivo}"),
    }


# --------------------------------------------------------------------------- #
# n6 · resumen — la ÚNICA salida                                               #
# --------------------------------------------------------------------------- #

def n6_resumen(estado: EstadoDelPipeline, *, contador: Contador | None = None) -> dict[str, Any]:
    """La única salida, también cuando la corrida no cierra.

    El costo va **medido**, no estimado: `Contador` lleva tokens y llamadas reales, y por
    eso el resumen puede decir cuánto salió una corrida en vez de dar una sensación. Es la
    diferencia entre poder decidir si el pipeline conviene y tener que suponerlo.
    """
    c = contador or Contador()
    final = estado.estado_final if estado.estado_final != "en-curso" else "cerrada"
    rev = estado.ultima_revision
    resumen = ResumenDeCorrida(
        ticket=estado.ticket,
        thread_id=estado.ticket,
        estado_final=final,
        que_se_pidio=estado.entrada[:500],
        decisiones_humanas=[
            f"ronda {r.ronda}: {'aprobó' if r.aprobado else 'no aprobó'}"
            + (f" · {'; '.join(f'{q} → {a}' for q, a in r.respuestas.items())}" if r.respuestas else "")
            for r in estado.respuestas_humanas
        ],
        archivos=[a.ruta for e in estado.entregas for a in e.archivos],
        evidencia=[ev for r in estado.reportes for ev in r.evidencia],
        supuestos=list(estado.contrato.supuestos) if estado.contrato else [],
        errores=list(estado.errores),
        veredicto=rev.veredicto if rev else None,
        proximos_pasos=(
            list(estado.contrato.decisiones_abiertas) if estado.contrato else []
        ) + [f"incertidumbre determinista: {i.chequeo}" for i in estado.incertidumbres],
        marca=Marca.SIN_CONTRASTAR,
    )
    return {"resumen": resumen, "estado_final": final,
            "log": _log("n6_resumen", f"corrida {final} · {c.llamadas} llamada(s) · "
                                      f"{c.tokens_salida} tokens de salida")}


# --------------------------------------------------------------------------- #
# El armado                                                                    #
# --------------------------------------------------------------------------- #

def construye(contador: Contador | None = None) -> StateGraph:
    """El grafo sin compilar. `run.py` le pone el checkpointer y lo compila."""
    g = StateGraph(EstadoDelPipeline)

    g.add_node("n1a_analizar", lambda e: n1a_analizar(e, contador=contador))
    g.add_node("n1b_aclarar", n1b_aclarar)
    g.add_node("n2_contrato", lambda e: n2_contrato(e, contador=contador))
    g.add_node("chequeos", marca_incertidumbres)
    g.add_node("n2b_aclarar_contrato", n2b_aclarar_contrato)
    g.add_node("n3_implementar", lambda e: n3_implementar(e, contador=contador))
    g.add_node("n4_empaquetar_pr", n4_empaquetar_pr)
    g.add_node("n5_revisar", lambda e: n5_revisar(e, contador=contador))
    g.add_node("n_escalar", n_escalar)
    g.add_node("n6_resumen", lambda e: n6_resumen(e, contador=contador))

    g.add_edge(START, "n1a_analizar")
    g.add_edge("n1a_analizar", "n1b_aclarar")
    g.add_conditional_edges("n1b_aclarar", rutea_aclaracion, {
        "contratar": "n2_contrato",
        "reanalizar": "n1a_analizar",
        "abortar": "n_escalar",
    })
    g.add_edge("n2_contrato", "chequeos")
    g.add_conditional_edges("chequeos", rutea_contrato, {
        "preguntar": "n2b_aclarar_contrato",
        "implementar": "n3_implementar",
    })
    g.add_conditional_edges("n2b_aclarar_contrato", rutea_post_contrato, {
        "implementar": "n3_implementar",
        "recontratar": "n2_contrato",
        "abortar": "n_escalar",
    })
    g.add_edge("n3_implementar", "n4_empaquetar_pr")
    g.add_edge("n4_empaquetar_pr", "n5_revisar")
    g.add_conditional_edges("n5_revisar", rutea_revision_nodo, {
        "continuar": "n6_resumen",
        "reimplementar": "n3_implementar",
        "recontratar": "n2_contrato",
        "escalar": "n_escalar",
    })
    # `n_escalar` NO va a END: la corrida que escala es la que más necesita dejar algo
    # escrito, porque alguien la va a levantar sin haber estado.
    g.add_edge("n_escalar", "n6_resumen")
    g.add_edge("n6_resumen", END)
    return g
