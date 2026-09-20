"""Un puntero al SSOT que no resuelve es peor que no citar: aparenta trazabilidad."""

from pathlib import Path

from fitogenix.punteros import cobertura, verifica_texto

CTX = {"1.1", "3.1", "5.2", "8.6"}
NUT = {"N0", "N5"}
ADR = {"002", "006"}


def _v(texto, ruta="src/x.ts", raiz=None):
    return verifica_texto(ruta, texto, secciones=CTX, secciones_nutricion=NUT, adrs=ADR, raiz_repo=raiz)


# --- Lo que tiene que fallar ---------------------------------------------


def test_una_seccion_de_context_que_no_existe_falla():
    f = _v("// la frontera está en CONTEXT.md §9.4")
    assert len(f) == 1 and "§9.4" in f[0]


def test_una_seccion_de_nutricion_que_no_existe_falla():
    assert any("§N9" in x for x in _v("/* ver NUTRICION.md §N9 */"))


def test_un_ADR_inexistente_falla():
    """El caso real: se citaba ADR-006 antes de que existiera."""
    assert any("ADR-004" in x for x in _v("// decidido en ADR-004"))


def test_citar_por_numero_de_linea_falla():
    """`ENGINE_VERSION` se citaba como `ftgEngine.ts:24` y vive en `constants.ts:24`:
    archivo equivocado, número correcto, invisible tres días."""
    assert any("número de línea" in x for x in _v("// ver `ftgEngine.ts:24`"))


def test_un_archivo_citado_que_no_existe_falla(tmp_path):
    """El caso real: fixDataQuality.ts mandaba a aplicar migrations/010_manufacturer_info.sql,
    que no existe desde el renumerado a0560ca."""
    f = _v("// requiere `migrations/010_manufacturer_info.sql` aplicada", raiz=tmp_path)
    assert any("no existe en el repo" in x for x in f)


# --- Lo que NO tiene que fallar -------------------------------------------


def test_un_puntero_valido_pasa():
    assert _v("// el cliente no recalcula: CONTEXT.md §3.1 y §5.2") == []


def test_un_ADR_que_existe_pasa():
    assert _v("// decisión de producto, ADR-002") == []


def test_el_parrafo_pelado_de_la_rubrica_NO_se_valida():
    """`§X` significa dos cosas en este proyecto. En el server, `§4.7` y `§2` son
    secciones de la rúbrica del motor, no de CONTEXT.md — 46 apariciones de `§2`.
    Validar un `§` pelado serían 46 falsos positivos el primer día."""
    assert _v("/* FITOGENIX — §2: los pasos del cálculo */\n// §4.7 — no identificado") == []


def test_un_archivo_citado_que_si_existe_pasa(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.ts").write_text("x")
    assert _v("// ver `src/a.ts`", raiz=tmp_path) == []


def test_una_version_con_punto_no_se_confunde_con_numero_de_linea():
    """`ftg-rubric-v2.3` no es `archivo.ts:24`."""
    assert _v("// ENGINE_VERSION pasó a ftg-rubric-v2.3") == []


# --- Cobertura -------------------------------------------------------------


def test_cobertura_cuenta_dominio_y_rutas(tmp_path):
    for d in ("src/domain", "src/routes"):
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "src/domain/con.ts").write_text("// CONTEXT.md §3.1\n")
    (tmp_path / "src/domain/sin.ts").write_text("export const x = 1;\n")
    (tmp_path / "src/routes/t.test.ts").write_text("// no cuenta: es test\n")
    con, tot = cobertura(tmp_path)
    assert (con, tot) == (1, 2)
