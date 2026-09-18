"""
Los chequeos deterministas de incertidumbre. **La mitad del HitL 2 que no pasa por el
modelo.**

`PROPUESTA_grafo_fase2.md` sección 2 lo dice sin vueltas: confiar en que el modelo
declare su propia incertidumbre falla, porque *"declarar menos incertidumbre es el
camino más corto a no ser interrumpido"*. Por eso la condición de interrupción es la
unión de dos fuentes, y la segunda son estos chequeos: corren en Python **después** de
que el modelo respondió, así que su resultado es un hecho del estado y el modelo no lo
puede declinar ni suavizar.

Hasta el 2026-09-18 `Incertidumbre` declaraba seis `chequeo` posibles y **ninguno
estaba implementado**: `hay_que_preguntar()` dependía solo de que el modelo dijera que
tenía dudas, que es exactamente el agujero que el diseño dice tapar. Este módulo es esa
mitad faltante.

Cada función devuelve `list[Incertidumbre]`. Vacía = nada que preguntar por esa vía.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import SETTINGS
from .context_loader import SeccionNoEncontrada, load_section, secciones_disponibles
from .guards import corre_los_guards
from .schemas import ContratoAprobado, Incertidumbre, Marca, PUNTOS_DEL_CONTRATO

#: Tope de contexto que un solo Brief tiene derecho a arrastrar. El objetivo número uno
#: del pipeline es que un agente de disciplina no cargue el SSOT entero; sin un tope,
#: nada impide que un Brief lo reconstruya citando secciones gruesas.
PRESUPUESTO_BRIEF_BYTES = 12_000

_P_CODIGO = re.compile(r"^fitogenix-(server|native)/([\w\-./]+\.\w+)")
_P_CONTEXT = re.compile(r"^CONTEXT\.md\s+§(\d+(?:\.\d+)?)$", re.IGNORECASE)


def _punteros_del_contrato(c: ContratoAprobado) -> list[tuple[str, str]]:
    """(de dónde salió, puntero). Recorre reglas, briefs y sus contextos."""
    out = [("regla", r.puntero) for r in c.reglas_de_validacion]
    for b in c.briefs:
        out += [(f"brief:{b.destinatario.value}", p.ref) for p in b.contexto_relevante]
    return out


# --- 1 · sección inexistente ------------------------------------------------

def seccion_inexistente(c: ContratoAprobado) -> list[Incertidumbre]:
    """Un `§X` citado que no existe: el Brief se armó mal o el agente inventó el puntero."""
    out = []
    for origen, p in _punteros_del_contrato(c):
        if not _P_CONTEXT.match(p) and "NUTRICION" not in p.upper():
            continue
        try:
            load_section(p)
        except SeccionNoEncontrada:
            out.append(Incertidumbre(
                chequeo="seccion-inexistente",
                detalle=f"{origen} cita {p!r}, que no existe. "
                        f"Disponibles: {', '.join(secciones_disponibles(p)[:12])}…",
                puntero=p))
    return out


# --- 2 · puntero a archivo que no resuelve ----------------------------------

def puntero_sin_archivo(c: ContratoAprobado) -> list[Incertidumbre]:
    """Un puntero a código que no resuelve en ninguno de los dos repos: el contrato
    está describiendo código que no existe."""
    raices = {"server": SETTINGS.server_path, "native": SETTINGS.native_path}
    out = []
    for origen, p in _punteros_del_contrato(c):
        m = _P_CODIGO.match(p.split("→")[0].strip())
        if not m:
            continue
        raiz = raices[m.group(1)]
        if not raiz.exists():
            continue  # repo no clonado: no es un hallazgo del contrato
        if not (raiz / m.group(2)).exists():
            out.append(Incertidumbre(
                chequeo="puntero-sin-archivo",
                detalle=f"{origen} cita {m.group(0)!r}, que no existe en el repo",
                puntero=p))
    return out


# --- 3 · el plan toca un bloqueante 🔴 abierto --------------------------------

def bloqueante_abierto(c: ContratoAprobado) -> list[Incertidumbre]:
    """Hay una decisión de producto sin tomar en el camino.

    Se detecta por la marca de la propia sección `§8.<n>`: si el contrato la cita y esa
    subsección lleva 🔴, el bloqueante está abierto. Se lee del SSOT en vez de mantener
    una lista acá — una lista sería una segunda copia que deriva.
    """
    out = []
    for origen, p in _punteros_del_contrato(c):
        m = _P_CONTEXT.match(p)
        if not m or not m.group(1).startswith("8."):
            continue
        try:
            texto = load_section(p)
        except SeccionNoEncontrada:
            continue  # lo levanta el chequeo 1
        if "🔴" in texto:
            titulo = texto.splitlines()[0].lstrip("# ").strip()
            out.append(Incertidumbre(
                chequeo="bloqueante-abierto",
                detalle=f"{origen} toca un bloqueante 🔴 abierto: {titulo}",
                puntero=p))
    return out


# --- 4 · contrato sin campos donde debería tenerlos --------------------------

def campo_sin_criterio(c: ContratoAprobado) -> list[Incertidumbre]:
    """Un contrato que mueve el contrato de producto y no declara un solo campo.

    El schema ya obliga a que **cada campo declarado** tenga su criterio en
    Given/When/Then, así que ese caso no puede llegar hasta acá. Lo que el schema no
    puede exigir es que haya campos: un `ContratoAprobado` con `campos=[]` que igual
    toca las tres puntas pasa la validación y no dice qué cambia.
    """
    if c.puntas_tocadas and any(p.cambia for p in c.puntas_tocadas) and not c.campos:
        return [Incertidumbre(
            chequeo="campo-sin-criterio",
            detalle="el contrato mueve el contrato de producto y no declara ningún campo: "
                    "no hay forma de saber qué cambia ni cómo verificarlo")]
    return []


# --- 5 · afirmación ✅ sin ruta de archivo -----------------------------------

def verificado_sin_ruta(c: ContratoAprobado) -> list[Incertidumbre]:
    """Una regla marcada ✅ cuyo puntero no es una ruta de código.

    El propio SSOT dice que eso es 🔴, no ✅: verificado significa *verificado contra
    algo que se puede abrir*.
    """
    return [
        Incertidumbre(
            chequeo="verificado-sin-ruta",
            detalle=f"regla marcada ✅ apuntando a {r.puntero!r}, que no es una ruta de "
                    f"código. Sin archivo que abrir, es ⚠️ y no ✅",
            puntero=r.puntero)
        for r in c.reglas_de_validacion
        if r.marca == Marca.VERIFICADO and not _P_CODIGO.match(r.puntero.split("→")[0].strip())
    ]


# --- 6 · frontera violada ----------------------------------------------------

def frontera_violada(archivos: list[tuple[str, str]],
                     *, rutas_nuevas: list[str] | None = None) -> list[Incertidumbre]:
    """Los guards de `guards.py`, expresados como incertidumbre del contrato."""
    return [Incertidumbre(chequeo="frontera-violada", detalle=f)
            for f in corre_los_guards(archivos, rutas_nuevas=rutas_nuevas or [])]


# --- 7 · presupuesto de contexto (agregado el 2026-09-18) --------------------

def _tiene_subsecciones(seccion: str) -> bool:
    return any(s.startswith(f"{seccion}.") for s in secciones_disponibles())


def presupuesto_excedido(c: ContratoAprobado) -> list[Incertidumbre]:
    """Un Brief que cita una sección entera pudiendo citar la subsección, o que se pasa
    del presupuesto.

    No estaba en los cinco chequeos de la sección 2, y se suma porque **el objetivo
    número uno del pipeline es que un agente no cargue el SSOT entero** — y sin un tope
    nada impedía que un Brief lo reconstruyera citando `§1`, `§2` y `§5` completas. Que
    el ahorro dependa de la prolijidad del que escribe el Brief es el mismo error que
    confiar en la incertidumbre autodeclarada.
    """
    from .context_loader import load_pointers

    out = []
    for b in c.briefs:
        refs = [p.ref for p in b.contexto_relevante]
        for ref in refs:
            m = _P_CONTEXT.match(ref)
            if m and "." not in m.group(1) and _tiene_subsecciones(m.group(1)):
                hijas = [s for s in secciones_disponibles() if s.startswith(f"{m.group(1)}.")]
                out.append(Incertidumbre(
                    chequeo="presupuesto-excedido",
                    detalle=f"brief:{b.destinatario.value} cita §{m.group(1)} entera, "
                            f"pudiendo citar la subsección ({', '.join('§'+h for h in hijas[:6])}…). "
                            f"Cargar de más es el costo que este pipeline existe para evitar",
                    puntero=ref))
        if refs:
            peso = len(load_pointers(refs).encode())
            if peso > PRESUPUESTO_BRIEF_BYTES:
                out.append(Incertidumbre(
                    chequeo="presupuesto-excedido",
                    detalle=f"brief:{b.destinatario.value} arrastra {peso:,} B de contexto, "
                            f"por encima del presupuesto de {PRESUPUESTO_BRIEF_BYTES:,} B"))
    return out


# --- el conjunto -------------------------------------------------------------

def todos(c: ContratoAprobado,
          *, archivos: list[tuple[str, str]] | None = None,
          rutas_nuevas: list[str] | None = None) -> list[Incertidumbre]:
    """Los siete chequeos. Es lo que `n2b_aclarar_contrato` le pasa a `hay_que_preguntar`."""
    out: list[Incertidumbre] = []
    out += seccion_inexistente(c)
    out += puntero_sin_archivo(c)
    out += bloqueante_abierto(c)
    out += campo_sin_criterio(c)
    out += verificado_sin_ruta(c)
    out += presupuesto_excedido(c)
    if archivos:
        out += frontera_violada(archivos, rutas_nuevas=rutas_nuevas)
    return out
