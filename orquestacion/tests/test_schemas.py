"""Los validadores SON las reglas del SSOT. Si estos tests pasan, la regla existe.

Cada test nombra el puntero de la regla que verifica. Un test acá que no se pueda atar a
una sección de `CONTEXT.md`, a `CONVENCIONES_EQUIPO.md` o a una decisión registrada en
`PROPUESTA_grafo_fase2.md` es una regla inventada, y hay que borrarla o escalarla.
"""

import pytest
from pydantic import ValidationError

from fitogenix.schemas import (
    TECHOS,
    AnalisisDeRequerimiento,
    ArchivoGenerado,
    Bloqueo,
    Brief,
    CambioDeEsquema,
    CampoDelContrato,
    CodigoGenerado,
    ContratoAprobado,
    Disciplina,
    Entregable,
    EstadoReporte,
    Evidencia,
    Hallazgo,
    Incertidumbre,
    Marca,
    PaquetePR,
    PreguntaAbierta,
    PuntaDelContrato,
    PunteroDeContexto,
    ReglaDeValidacion,
    Reporte,
    ReporteDeRevision,
    RequisitoTrazado,
    RespuestaHumana,
    Severidad,
    Veredicto,
    aprobacion_valida,
    hay_que_preguntar,
    rutea_revision,
)

DCE = "Dado un producto sin datos Cuando se pide el lookup Entonces devuelve null"

CUERPO_PR = "\n".join(
    ["## Qué", "x", "## Por qué", "x", "## Cómo", "x", "## Tests", "x",
     "## Riesgos residuales", "x", "## Checklist", "- [ ] tsc"]
)


def _brief(**kw):
    base = dict(
        objetivo="agregar el gate de cobertura al motor",
        fuente=Marca.VERIFICADO,
        contexto_relevante=[PunteroDeContexto(ref="CONTEXT.md §3.1")],
        criterio_de_aceptacion=DCE,
        entregable=Entregable.PR,
        destinatario=Disciplina.BACKEND,
    )
    base.update(kw)
    return Brief(**base)


def _regla(**kw):
    base = dict(enunciado="el cliente no recalcula el puntaje", puntero="CONTEXT.md §3.4")
    base.update(kw)
    return ReglaDeValidacion(**base)


def _contrato(**kw):
    base = dict(
        objetivo="declarar el gate de cobertura y sus tres puntas",
        reglas_de_validacion=[_regla()],
        briefs=[_brief()],
    )
    base.update(kw)
    return ContratoAprobado(**base)


# --- Punteros: el SSOT se cita, no se copia ---------------------------------


def test_el_brief_rechaza_texto_copiado_en_vez_de_puntero():
    """El mecanismo entero del ahorro de tokens. Texto copiado lo anula."""
    with pytest.raises(ValidationError, match="puntero"):
        _brief(contexto_relevante=[PunteroDeContexto(ref="Las bandas salen del mismo lugar")])


def test_un_puntero_con_numero_de_linea_se_rechaza():
    """`CONTEXT.md §9`, convención del 31/8: `ENGINE_VERSION` se citaba como
    `ftgEngine.ts:24` y vive en `constants.ts:24` — archivo equivocado, número correcto,
    error invisible durante tres días."""
    with pytest.raises(ValidationError, match="número de línea"):
        PunteroDeContexto(ref="fitogenix-server/src/domain/product/scoring/constants.ts:24")


def test_el_puntero_a_codigo_con_simbolo_es_valido():
    p = PunteroDeContexto(ref="fitogenix-server/src/domain/product/scoring/steps.ts → applyNutrition")
    assert not p.es_seccion_de_context


def test_el_puntero_a_nutricion_es_valido():
    assert PunteroDeContexto(ref="nutricion/NUTRICION.md §N7").ref.endswith("§N7")


def test_un_puntero_larguisimo_es_texto_copiado():
    with pytest.raises(ValidationError, match="texto copiado"):
        PunteroDeContexto(ref="CONTEXT.md §3.1 " + "x" * 130)


# --- Brief -------------------------------------------------------------------


def test_el_brief_exige_dado_cuando_entonces():
    with pytest.raises(ValidationError, match="Dado/Cuando/Entonces"):
        _brief(criterio_de_aceptacion="que funcione bien")


def test_el_arquitecto_no_recibe_un_brief_de_PR():
    """`CONTEXT.md §7`: si escribe código deja de ser el que puede firmar las tres puntas."""
    with pytest.raises(ValidationError, match="no implementa"):
        _brief(destinatario=Disciplina.ARCHITECT, entregable=Entregable.PR)


def test_nutricion_no_recibe_un_brief_de_PR():
    with pytest.raises(ValidationError, match="no escribe código"):
        _brief(destinatario=Disciplina.NUTRITION, entregable=Entregable.PR)


def test_un_brief_sin_destinatario_no_se_delega():
    with pytest.raises(ValidationError, match="destinatario"):
        _brief(destinatario=Disciplina.NINGUNA)


# --- Reporte -----------------------------------------------------------------


def test_done_sin_evidencia_se_rechaza():
    with pytest.raises(ValidationError, match="evidencia"):
        Reporte(agente=Disciplina.BACKEND, estado=EstadoReporte.DONE, que_hice=["algo"])


def test_supuestos_abiertos_impiden_cerrar():
    with pytest.raises(ValidationError, match="supuestos"):
        Reporte(
            agente=Disciplina.BACKEND,
            estado=EstadoReporte.DONE,
            que_hice=["algo"],
            evidencia=[Evidencia(tipo="test", referencia="seals.test.ts")],
            supuestos=["el umbral de cobertura es 30%"],
        )


def test_blocked_sin_bloqueo_no_tiene_dueno():
    with pytest.raises(ValidationError, match="bloqueo"):
        Reporte(agente=Disciplina.NUTRITION, estado=EstadoReporte.BLOCKED, que_hice=["nada"])


def test_una_afirmacion_verificada_sin_ruta_de_archivo_es_roja():
    """`PROPUESTA_grafo_fase2.md` sección 2: el propio SSOT dice que eso es 🔴, no ✅."""
    with pytest.raises(ValidationError, match="ruta de archivo"):
        Reporte(
            agente=Disciplina.BACKEND,
            estado=EstadoReporte.PARTIAL,
            que_hice=["revisé el motor"],
            evidencia=[Evidencia(tipo="comando", referencia="lo miré y está bien")],
            marca=Marca.VERIFICADO,
        )


def test_una_fuente_secundaria_no_alcanza_para_cambiar_codigo():
    """`09-agente-nutricion.md`: un 📄 sirve para abrir un ticket, no para tocar el motor."""
    with pytest.raises(ValidationError, match="fuente secundaria"):
        Reporte(
            agente=Disciplina.NUTRITION,
            estado=EstadoReporte.PARTIAL,
            que_hice=["leí una nota de prensa"],
            marca=Marca.FUENTE_SECUNDARIA,
            cambio_de_codigo_propuesto=["bajar el corte de sodio en seals.ts"],
        )


# --- n1a_analizar ------------------------------------------------------------


def test_no_se_avanza_con_preguntas_abiertas():
    with pytest.raises(ValidationError, match="listo_para_contratar"):
        AnalisisDeRequerimiento(
            resumen="x" * 30,
            preguntas_abiertas=[
                PreguntaAbierta(id="P1", pregunta="¿Desde qué cobertura se puntúa?",
                                por_que_bloquea="Define el gate del motor.")
            ],
            listo_para_contratar=True,
        )


def test_no_se_avanza_tocando_un_bloqueante_abierto():
    """`CONTEXT.md §8`: hay una decisión de producto sin tomar en el camino."""
    with pytest.raises(ValidationError, match="bloqueantes abiertos"):
        AnalisisDeRequerimiento(
            resumen="x" * 30, bloqueantes_tocados=["B-2"], listo_para_contratar=True
        )


def test_una_marca_sin_contrastar_inyecta_la_frase_de_incertidumbre():
    a = AnalisisDeRequerimiento(
        resumen="x" * 30,
        requisitos=[RequisitoTrazado(enunciado="e", puntero="CONTEXT.md §2.2",
                                     marca=Marca.SIN_CONTRASTAR)],
        listo_para_contratar=True,
    )
    assert "verificable" in (a.nota_de_incertidumbre or "")


def test_el_techo_de_aclaracion_es_tres():
    with pytest.raises(ValidationError):
        AnalisisDeRequerimiento(resumen="x" * 30, ronda=TECHOS["aclaracion"] + 1)


def test_un_ok_vacio_no_aprueba_un_requisito_sin_resolver():
    a = AnalisisDeRequerimiento(
        resumen="x" * 30,
        preguntas_abiertas=[PreguntaAbierta(id="P1", pregunta="¿Cuál es el umbral?",
                                            por_que_bloquea="Define el gate.")],
    )
    assert aprobacion_valida(a, RespuestaHumana(ronda=1, aprobado=True)) is False


# --- n2_contrato -------------------------------------------------------------


def test_una_regla_sin_puntero_se_rechaza():
    """Si nadie firma de rutina, el contrato lo sostiene Pydantic."""
    with pytest.raises(ValidationError):
        _regla(puntero="según lo que veníamos hablando")


def test_un_contrato_que_toca_una_punta_tiene_que_nombrar_las_tres():
    """La regla que define al arquitecto. C-04 y C-08 se quedaron abiertos justo así:
    cada archivo tenía dueño, la relación entre ellos no."""
    with pytest.raises(ValidationError, match="tres puntas"):
        _contrato(
            puntas_tocadas=[
                PuntaDelContrato(
                    archivo="fitogenix-server/src/types/fitogenix.ts",
                    cambia=True, detalle="suma el campo coverage",
                )
            ]
        )


def test_nombrar_las_tres_puntas_alcanza_aunque_dos_no_cambien():
    """'No cambia' es una afirmación verificable; el silencio no."""
    c = _contrato(
        puntas_tocadas=[
            PuntaDelContrato(archivo=p, cambia=(i == 0), detalle="suma coverage" if i == 0 else "no cambia")
            for i, p in enumerate(
                ["fitogenix-server/src/types/fitogenix.ts",
                 "fitogenix-server/src/routes/products/lookupSchema.ts",
                 "fitogenix-native/src/lib/contracts/product.ts"]
            )
        ]
    )
    assert len(c.puntas_tocadas) == 3


def test_un_campo_sin_criterio_de_aceptacion_se_rechaza():
    with pytest.raises(ValidationError, match="Dado/Cuando/Entonces"):
        CampoDelContrato(nombre="coverage", tipo="number", criterio_de_aceptacion="que venga")


def test_un_cambio_de_esquema_exige_ADR():
    with pytest.raises(ValidationError, match="requiere_adr"):
        _contrato(
            cambios_de_esquema=[
                CambioDeEsquema(
                    tabla="products", tipo="nueva-columna",
                    archivo_de_migracion="migrations/015_coverage.sql",
                    justificacion="el gate necesita persistir la cobertura",
                )
            ]
        )


def test_una_migracion_irreversible_repite_B6():
    with pytest.raises(ValidationError, match="B-6"):
        CambioDeEsquema(
            tabla="products", tipo="nueva-columna", reversible=False,
            archivo_de_migracion="migrations/015_coverage.sql",
            justificacion="el gate necesita persistir la cobertura",
        )


def test_el_techo_de_contrato_es_uno():
    """Sin aprobación humana de rutina, un segundo ciclo silencioso sería el pipeline
    discutiendo consigo mismo."""
    with pytest.raises(ValidationError):
        _contrato(ronda=TECHOS["contrato"] + 1)


def test_el_contrato_escala_a_opus_cuando_toca_scoring():
    assert _contrato(toca_scoring=True).escala_a_opus is True
    assert _contrato().escala_a_opus is False


# --- La condición de interrupción -------------------------------------------


def test_sin_supuestos_ni_deterministas_el_pipeline_no_pregunta():
    assert hay_que_preguntar(_contrato(), []) is False


def test_un_supuesto_declarado_interrumpe():
    assert hay_que_preguntar(_contrato(supuestos=["asumo que el gate va en steps.ts"]), []) is True


def test_un_chequeo_determinista_interrumpe_aunque_el_modelo_diga_que_esta_todo_claro():
    """El agujero de confiar en la incertidumbre autodeclarada: declarar menos es el camino
    más corto a no ser interrumpido. `det` no pasa por el modelo."""
    limpio = _contrato()
    assert not limpio.supuestos and not limpio.decisiones_abiertas
    assert hay_que_preguntar(
        limpio, [Incertidumbre(chequeo="seccion-inexistente", detalle="CONTEXT.md §12 no existe")]
    ) is True


# --- n3_implementar ----------------------------------------------------------


def _codigo(**kw):
    base = dict(
        agente=Disciplina.BACKEND,
        archivos=[ArchivoGenerado(ruta="fitogenix-server/src/services/x.ts",
                                  lenguaje="typescript", contenido="export const x = 1;")],
    )
    base.update(kw)
    return CodigoGenerado(**base)


def test_tocar_dominio_sin_test_no_mergea():
    """`CONVENCIONES_EQUIPO.md` sección 2."""
    with pytest.raises(ValidationError, match="sin un test"):
        _codigo(toca_dominio=True)


def test_qa_no_implementa_lo_que_audita():
    with pytest.raises(ValidationError, match="no implementa"):
        _codigo(agente=Disciplina.QA)


def test_puede_mergear_es_falso_con_marca_sin_contrastar():
    assert _codigo(marca=Marca.SIN_CONTRASTAR).puede_mergear is False
    assert _codigo(marca=Marca.VERIFICADO).puede_mergear is True


# --- n4_empaquetar_pr --------------------------------------------------------


def _pr(**kw):
    base = dict(rama="feat/gate-de-cobertura", titulo="Add coverage gate",
                cuerpo_md=CUERPO_PR, commits=["feat: add coverage gate"],
                comandos_git=["git status"])
    base.update(kw)
    return PaquetePR(**base)


def test_el_paquete_de_pr_rechaza_force_push():
    with pytest.raises(ValidationError, match="destructivo"):
        _pr(comandos_git=["git push --force origin feat/gate-de-cobertura"])


def test_nunca_se_trabaja_directo_sobre_main():
    with pytest.raises(ValidationError):
        _pr(rama="main")


def test_el_cuerpo_del_pr_exige_la_plantilla_obligatoria():
    with pytest.raises(ValidationError, match="plantilla obligatoria"):
        _pr(cuerpo_md="## Qué\narreglé el gate")


def test_asunto_de_commit_con_punto_final_se_rechaza():
    with pytest.raises(ValidationError, match="punto final"):
        _pr(commits=["feat: add coverage gate."])


# --- n5_revisar --------------------------------------------------------------


def _hallazgo(sev=Severidad.BLOQUEANTE, **kw):
    base = dict(id="H-01", categoria="frontera", severidad=sev,
                archivo="fitogenix-native/src/screens/GuideScreen.tsx",
                descripcion="transcribe los cortes de banda fuera de constants.ts",
                correccion_sugerida="derivar de TIERS por contrato")
    base.update(kw)
    return Hallazgo(**base)


def test_no_se_aprueba_con_hallazgos_bloqueantes():
    with pytest.raises(ValidationError, match="bloqueante"):
        ReporteDeRevision(veredicto=Veredicto.APROBADO, hallazgos=[_hallazgo()], resumen="x" * 25)


def test_aprobado_con_condiciones_tampoco_pasa_por_encima_de_un_bloqueante():
    with pytest.raises(ValidationError, match="bloqueante"):
        ReporteDeRevision(veredicto=Veredicto.APROBADO_CON_CONDICIONES,
                          hallazgos=[_hallazgo()], resumen="x" * 25)


def test_un_rechazo_sin_hallazgos_no_es_accionable():
    with pytest.raises(ValidationError, match="accionable"):
        ReporteDeRevision(veredicto=Veredicto.RECHAZADO, resumen="x" * 25)


def test_un_hallazgo_no_cita_por_numero_de_linea():
    with pytest.raises(ValidationError, match="número de línea"):
        _hallazgo(archivo="fitogenix-native/src/screens/GuideScreen.tsx:27")


def test_un_rechazo_con_hallazgos_solo_menores_NO_continua():
    """El agujero que PampaGrow tapó después de tenerlo: ruteando solo por severidad, un
    rechazo con hallazgos `menor` devolvía 'continuar', la corrida cerraba en verde y el
    CLI salía 0. El gate se podía saltar sin que nadie lo notara."""
    rev = ReporteDeRevision(
        veredicto=Veredicto.RECHAZADO,
        hallazgos=[_hallazgo(sev=Severidad.MENOR)],
        resumen="x" * 25,
    )
    assert rutea_revision(rev) == "reimplementar"


def test_un_bloqueante_vuelve_al_contrato_no_a_la_implementacion():
    rev = ReporteDeRevision(veredicto=Veredicto.RECHAZADO, hallazgos=[_hallazgo()],
                            resumen="x" * 25)
    assert rutea_revision(rev) == "recontratar"


def test_aprobado_con_condiciones_avanza():
    """Las condiciones viajan en el cuerpo del PR, para el humano que revisa."""
    rev = ReporteDeRevision(veredicto=Veredicto.APROBADO_CON_CONDICIONES,
                            hallazgos=[_hallazgo(sev=Severidad.MAYOR)], resumen="x" * 25)
    assert rutea_revision(rev) == "continuar"


def test_alcanzado_el_techo_de_revision_se_escala():
    rev = ReporteDeRevision(veredicto=Veredicto.RECHAZADO, ronda=TECHOS["revision"],
                            hallazgos=[_hallazgo()], resumen="x" * 25)
    assert rutea_revision(rev) == "escalar"


def test_un_bloqueo_apunta_a_jere_cuando_nadie_es_dueno():
    """B-12 no tiene dueño: B-2, B-3 y B-4 no se rutean a ningún nodo del grafo."""
    b = Bloqueo(descripcion="falta la publicación de OPS para fijar el umbral",
                desbloquea="jere", puntero="CONTEXT.md §8")
    assert b.desbloquea == "jere"
