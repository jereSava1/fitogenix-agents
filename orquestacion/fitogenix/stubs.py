"""
Las salidas mínimas válidas de cada nodo. **Lo que hace que el grafo corra sin modelo.**

`llm.llama_estructurado` exige el stub a quien llama en vez de inventarlo por reflexión
sobre el schema, y esto es la consecuencia: cada nodo tiene que poder decir, escrito y a
la vista, cómo es su salida más chica válida. Un nodo que no lo sabe tiene el contrato mal
puesto, y es mucho mejor descubrirlo acá que en la primera corrida paga.

**Estos objetos son deliberadamente pobres.** No son ejemplos de buenas salidas: son el
piso que los validadores aceptan. Si alguno se empieza a parecer a una salida real, es
señal de que el schema dejó de exigir algo.

Nada de acá puede cerrar una corrida: `Respuesta.dry_run` viaja con el resultado y
`exigir_real()` lo frena.
"""

from __future__ import annotations

from .schemas import (
    AnalisisDeRequerimiento,
    ArchivoGenerado,
    CodigoGenerado,
    Disciplina,
    Evidencia,
    Marca,
    PaquetePR,
    PreguntaAbierta,
    Reporte,
    ReporteDeRevision,
    RequisitoTrazado,
    Veredicto,
)

#: Un puntero real, para que el stub pase los chequeos de puntero igual que una salida
#: de verdad. Uno falso haría que el dry-run probara un camino que la corrida real no usa.
_PUNTERO = "CONTEXT.md §3.1"

STUB_ANALISIS = AnalisisDeRequerimiento(
    resumen="[dry-run] análisis mínimo: un requisito trazado y una pregunta abierta",
    requisitos=[RequisitoTrazado(
        enunciado="[dry-run] el cliente no recalcula el puntaje",
        puntero=_PUNTERO, marca=Marca.SIN_CONTRASTAR)],
    preguntas_abiertas=[PreguntaAbierta(
        id="P1", pregunta="[dry-run] ¿alcance?",
        por_que_bloquea="[dry-run] sin esto no se puede escribir el contrato")],
)

#: El contrato mínimo se arma en `_contrato_minimo` y no como literal: `ContratoAprobado`
#: valida relaciones entre campos —las tres puntas, el ADR, la migración—, así que un
#: literal suelto se rompería en silencio con el próximo validador que se agregue.
def _contrato_minimo():
    from .schemas import Brief, ContratoAprobado, Entregable, PunteroDeContexto, ReglaDeValidacion

    return ContratoAprobado(
        objetivo="[dry-run] contrato mínimo para verificar el grafo sin llamar a un modelo",
        reglas_de_validacion=[ReglaDeValidacion(
            enunciado="[dry-run] los umbrales se citan, no se transcriben",
            punteros=[_PUNTERO])],
        briefs=[Brief(
            objetivo="[dry-run] brief mínimo",
            fuente=Marca.SIN_CONTRASTAR,
            contexto_relevante=[PunteroDeContexto(ref=_PUNTERO)],
            criterio_de_aceptacion=(
                "Dado el pipeline en dry-run Cuando corre este brief "
                "Entonces no se llama a ningún modelo"),
            entregable=Entregable.PR,
            destinatario=Disciplina.BACKEND,
        )],
    )


STUB_CONTRATO = _contrato_minimo()

STUB_REPORTE = Reporte(
    agente=Disciplina.BACKEND,
    estado="done",
    que_hice=["[dry-run] nada: el grafo corrió sin modelo"],
    evidencia=[Evidencia(tipo="test", referencia="[dry-run] sin evidencia real")],
)

STUB_ENTREGA = CodigoGenerado(
    agente=Disciplina.BACKEND,
    archivos=[ArchivoGenerado(
        ruta="fitogenix-server/src/routes/scoring/bands.ts",
        lenguaje="typescript",
        contenido="// [dry-run] sin contenido\n")],
)

#: Aprobado a propósito: el camino que el dry-run tiene que recorrer entero es el feliz.
#: Los caminos de rechazo se prueban en los tests del ruteo, con revisiones armadas a
#: mano — ahí sí conviene el control fino, y no depender de lo que devuelva un stub.
STUB_REVISION = ReporteDeRevision(
    veredicto=Veredicto.APROBADO,
    resumen="[dry-run] revisión mínima aprobada, sin hallazgos",
    ronda=1,
)


def stub_paquete(ticket: str) -> PaquetePR:
    """El paquete de PR es determinista, así que su 'stub' es la cosa real con contenido
    de relleno. Nunca sobre `main`: el validador de `PaquetePR` lo rechaza, y el dry-run
    tiene que respetar la misma regla que la corrida de verdad."""
    slug = ticket.lower().replace("_", "-")
    return PaquetePR(
        rama=f"feat/{slug}",
        titulo=f"[dry-run] {ticket}",
        # La plantilla completa, no un placeholder: `PaquetePR` exige las seis secciones
        # (`CONVENCIONES_EQUIPO.md` sección 2) y el dry-run tiene que respetar la misma
        # regla que la corrida de verdad. Un stub que se saltea un validador prueba un
        # grafo que no existe.
        cuerpo_md=(
            f"# [dry-run] {ticket}\n\n"
            "## Qué\n\n[dry-run] nada: corrida sin modelo.\n\n"
            "## Por qué\n\n[dry-run] verificar el grafo sin gastar.\n\n"
            "## Cómo\n\n[dry-run] stubs declarados por cada nodo.\n\n"
            "## Tests\n\n[dry-run] sin tests reales.\n\n"
            "## Riesgos residuales\n\n[dry-run] este paquete no se mergea nunca.\n\n"
            "## Checklist\n\n- [ ] [dry-run]\n"
        ),
        commits=[f"feat({slug}): [dry-run] sin cambios reales"],
        comandos_git=[f"git checkout -b feat/{slug}"],
    )


#: El análisis de la segunda vuelta: sin preguntas abiertas, porque el humano ya
#: contestó. Existe porque `aprobacion_valida` no deja aprobar mientras queden preguntas
#: —y tiene razón—, así que con un solo stub fijo el dry-run nunca podría pasar del
#: primer interrupt y recorrería únicamente el camino del techo de aclaración.
STUB_ANALISIS_RESUELTO = AnalisisDeRequerimiento(
    resumen="[dry-run] análisis de la segunda vuelta: sin preguntas abiertas",
    requisitos=[RequisitoTrazado(
        enunciado="[dry-run] el cliente no recalcula el puntaje",
        puntero=_PUNTERO, marca=Marca.SIN_CONTRASTAR)],
)
