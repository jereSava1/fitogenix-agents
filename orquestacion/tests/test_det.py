"""Los chequeos deterministas son la mitad del HitL que no pasa por el modelo.

Si estos tests pasan, `hay_que_preguntar()` deja de depender de que el modelo declare
sus propias dudas — que es el agujero que `PROPUESTA_grafo_fase2.md` sección 2 nombra
explícitamente.
"""

from fitogenix import det
from fitogenix.schemas import (
    Brief,
    CampoDelContrato,
    ContratoAprobado,
    Disciplina,
    Entregable,
    Marca,
    PuntaDelContrato,
    PunteroDeContexto,
    ReglaDeValidacion,
    hay_que_preguntar,
)

DCE = "Dado un producto sin datos Cuando se pide el lookup Entonces devuelve null"
CODIGO = "fitogenix-server/src/domain/product/scoring/constants.ts"


def _brief(refs=("CONTEXT.md §3.1",), destinatario=Disciplina.BACKEND):
    return Brief(
        objetivo="agregar el gate de cobertura",
        fuente=Marca.VERIFICADO,
        contexto_relevante=[PunteroDeContexto(ref=r) for r in refs],
        criterio_de_aceptacion=DCE,
        entregable=Entregable.PR,
        destinatario=destinatario,
    )


def _contrato(**kw):
    base = dict(
        objetivo="declarar el gate de cobertura y sus tres puntas",
        reglas_de_validacion=[ReglaDeValidacion(
            enunciado="el cliente no recalcula el puntaje", puntero="CONTEXT.md §3.4")],
        briefs=[_brief()],
    )
    base.update(kw)
    return ContratoAprobado(**base)


# --- 1 · sección inexistente -------------------------------------------------

def test_una_seccion_citada_que_no_existe_dispara():
    c = _contrato(reglas_de_validacion=[ReglaDeValidacion(
        enunciado="algo que no se puede verificar", puntero="CONTEXT.md §9.4")])
    d = det.seccion_inexistente(c)
    assert len(d) == 1 and d[0].chequeo == "seccion-inexistente" and "§9.4" in d[0].detalle


def test_una_seccion_que_existe_no_dispara():
    assert det.seccion_inexistente(_contrato()) == []


# --- 2 · puntero a archivo -----------------------------------------------------

def test_un_puntero_a_codigo_inexistente_dispara(monkeypatch, tmp_path):
    import dataclasses
    monkeypatch.setattr(det, "SETTINGS", dataclasses.replace(det.SETTINGS, server_path=tmp_path))
    c = _contrato(reglas_de_validacion=[ReglaDeValidacion(
        enunciado="el motor vive acá", puntero="fitogenix-server/src/no/existe.ts")])
    d = det.puntero_sin_archivo(c)
    assert len(d) == 1 and d[0].chequeo == "puntero-sin-archivo"


def test_un_puntero_a_codigo_real_no_dispara():
    c = _contrato(reglas_de_validacion=[ReglaDeValidacion(
        enunciado="los umbrales viven acá", puntero=CODIGO)])
    assert det.puntero_sin_archivo(c) == []


# --- 3 · bloqueante 🔴 abierto --------------------------------------------------

def test_tocar_un_bloqueante_rojo_abierto_dispara():
    """§8.2 (B-2) está 🔴 en el SSOT: hay una decisión de producto sin tomar."""
    c = _contrato(reglas_de_validacion=[ReglaDeValidacion(
        enunciado="el gate de cobertura", puntero="CONTEXT.md §8.2")])
    d = det.bloqueante_abierto(c)
    assert len(d) == 1 and d[0].chequeo == "bloqueante-abierto"


def test_citar_los_cerrados_no_dispara():
    """§8.0 son los cerrados: citarlos es recordar, no tropezar."""
    c = _contrato(reglas_de_validacion=[ReglaDeValidacion(
        enunciado="no lo reabras", puntero="CONTEXT.md §8.0")])
    assert det.bloqueante_abierto(c) == []


# --- 4 · contrato sin campos ---------------------------------------------------

def test_mover_el_contrato_sin_declarar_campos_dispara():
    from fitogenix.schemas import PUNTOS_DEL_CONTRATO
    c = _contrato(puntas_tocadas=[
        PuntaDelContrato(archivo=p, cambia=(i == 0),
                         detalle="suma coverage" if i == 0 else "no cambia")
        for i, p in enumerate(PUNTOS_DEL_CONTRATO)])
    d = det.campo_sin_criterio(c)
    assert len(d) == 1 and d[0].chequeo == "campo-sin-criterio"


def test_con_campos_declarados_no_dispara():
    from fitogenix.schemas import PUNTOS_DEL_CONTRATO
    c = _contrato(
        campos=[CampoDelContrato(nombre="coverage", tipo="number", criterio_de_aceptacion=DCE)],
        puntas_tocadas=[
            PuntaDelContrato(archivo=p, cambia=(i == 0),
                             detalle="suma coverage" if i == 0 else "no cambia")
            for i, p in enumerate(PUNTOS_DEL_CONTRATO)])
    assert det.campo_sin_criterio(c) == []


# --- 5 · ✅ sin ruta -------------------------------------------------------------

def test_una_regla_verificada_sin_ruta_de_archivo_dispara():
    c = _contrato(reglas_de_validacion=[ReglaDeValidacion(
        enunciado="esto está verificado", puntero="CONTEXT.md §3.4", marca=Marca.VERIFICADO)])
    d = det.verificado_sin_ruta(c)
    assert len(d) == 1 and "no es una ruta de código" in d[0].detalle


def test_una_regla_verificada_con_ruta_no_dispara():
    c = _contrato(reglas_de_validacion=[ReglaDeValidacion(
        enunciado="los umbrales viven acá", puntero=CODIGO, marca=Marca.VERIFICADO)])
    assert det.verificado_sin_ruta(c) == []


# --- 6 · frontera ----------------------------------------------------------------

def test_la_frontera_violada_entra_como_incertidumbre():
    d = det.frontera_violada([("fitogenix-native/src/screens/G.tsx",
                               "const TIERS = [{ range: '75–100', label: 'EXCELENTE' }];")])
    assert d and d[0].chequeo == "frontera-violada"


# --- 7 · presupuesto de contexto --------------------------------------------------

def test_citar_una_seccion_entera_pudiendo_citar_la_subseccion_dispara():
    """§5 entera son ~7 KB; §5.2 sola son 397 B. Es el costo que este pipeline
    existe para evitar."""
    c = _contrato(briefs=[_brief(refs=("CONTEXT.md §5",))])
    d = det.presupuesto_excedido(c)
    assert any(x.chequeo == "presupuesto-excedido" and "§5 entera" in x.detalle for x in d)


def test_citar_la_subseccion_no_dispara():
    assert det.presupuesto_excedido(_contrato(briefs=[_brief(refs=("CONTEXT.md §5.2",))])) == []


def test_una_seccion_sin_subsecciones_no_dispara():
    """§7 no tiene hijas: citarla entera es lo más fino que se puede."""
    assert det.presupuesto_excedido(_contrato(briefs=[_brief(refs=("CONTEXT.md §7",))])) == []


def test_pasarse_del_presupuesto_dispara():
    c = _contrato(briefs=[_brief(refs=("CONTEXT.md §1.6", "CONTEXT.md §8.0", "CONTEXT.md §2.5"))])
    d = det.presupuesto_excedido(c)
    assert any("presupuesto" in x.detalle for x in d)


# --- la unión, que es el punto ------------------------------------------------------

def test_un_contrato_limpio_no_interrumpe():
    c = _contrato()
    assert det.todos(c) == []
    assert hay_que_preguntar(c, det.todos(c)) is False


def test_el_determinista_interrumpe_aunque_el_modelo_diga_que_esta_todo_claro():
    """El agujero que este módulo tapa: el modelo no declaró ni un supuesto, y el
    contrato cita una sección que no existe."""
    c = _contrato(reglas_de_validacion=[ReglaDeValidacion(
        enunciado="una regla cualquiera", puntero="CONTEXT.md §9.4")])
    assert not c.supuestos and not c.decisiones_abiertas
    d = det.todos(c)
    assert d and hay_que_preguntar(c, d) is True
