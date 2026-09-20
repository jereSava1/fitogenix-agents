"""El cargador por sección ES el ahorro. Si carga de más, el pipeline no sirve."""

import pytest

from fitogenix.context_loader import (
    SeccionNoEncontrada,
    contexto_completo,
    costo,
    load_pointers,
    load_section,
    secciones_disponibles,
)


def test_carga_una_subseccion_y_no_el_documento():
    s = load_section("CONTEXT.md §5.2")
    assert s.startswith("### §5.2")
    assert "Regla absoluta de frontera" in s
    assert "§6" not in s.split("\n")[0]
    assert len(s.encode()) < 2000  # la sección, no las 50 KB


def test_acepta_las_tres_formas_de_escribir_el_puntero():
    a, b, c = load_section("CONTEXT.md §5.2"), load_section("§5.2"), load_section("5.2")
    assert a == b == c


def test_un_puntero_con_el_bloqueante_pegado_resuelve():
    """Los agentes escriben `CONTEXT.md §8.6` pero también `§8` B-6 en prosa."""
    assert load_section("CONTEXT.md §8.6").startswith("### §8.6")


def test_una_seccion_inventada_no_se_rellena():
    with pytest.raises(SeccionNoEncontrada) as e:
        load_section("CONTEXT.md §9.4")
    assert "no existe" in str(e.value) and "Disponibles" in str(e.value)


def test_nutricion_se_resuelve_contra_su_propio_SSOT():
    s = load_section("NUTRICION.md §N0")
    assert s.startswith("## §N0") or s.startswith("### §N0")


def test_una_seccion_que_no_resuelve_no_rompe_la_carga_pero_se_marca():
    b = load_pointers(["CONTEXT.md §3.1", "CONTEXT.md §99"])
    assert "Regla dura" in b and "[BLOQUEADO]" in b


def test_seccion_ocho_a_secas_ya_casi_no_trae_nada():
    """Desde el 2026-09-08 los bloqueantes son §8.<n>. `§8` devuelve su intro, que
    dice justamente que hay que apuntar más fino. Es lo buscado."""
    s = load_section("CONTEXT.md §8")
    assert len(s.encode()) < 1200
    assert "§8.<n>" in s or "8." in s


def test_el_ahorro_es_real_y_medible():
    cargado, entero = costo(["CONTEXT.md §1.1", "CONTEXT.md §5.2", "CONTEXT.md §3.1"])
    assert cargado < entero / 10       # tres subsecciones son menos del 10% del SSOT
    assert entero > 40_000             # el SSOT sigue siendo grande: no se achicó, se carga mejor


def test_el_indice_ve_subsecciones_y_secciones():
    d = secciones_disponibles()
    assert {"1.1", "5.2", "8.6", "8.0"} <= set(d)
    assert "8.19" in d


def test_contexto_completo_sigue_disponible_para_el_orquestador():
    assert len(contexto_completo().encode()) > 40_000
