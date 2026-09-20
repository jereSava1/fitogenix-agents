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
from .schemas import AnalisisDeRequerimiento, ContratoAprobado, Incertidumbre, Marca

#: Tope de contexto que un solo Brief tiene derecho a arrastrar. El objetivo número uno
#: del pipeline es que un agente de disciplina no cargue el SSOT entero; sin un tope,
#: nada impide que un Brief lo reconstruya citando secciones gruesas.
PRESUPUESTO_BRIEF_BYTES = 12_000

_P_CODIGO = re.compile(r"^fitogenix-(server|native)/([\w\-./]+\.\w+)")
_P_CONTEXT = re.compile(r"^CONTEXT\.md\s+§(\d+(?:\.\d+)?)$", re.IGNORECASE)


def _punteros_del_contrato(c: ContratoAprobado) -> list[tuple[str, str]]:
    """(de dónde salió, puntero). Recorre reglas, briefs y sus contextos."""
    out = [("regla", x) for r in c.reglas_de_validacion for x in r.punteros]
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
    faltantes: set[str] = set()
    for origen, p in _punteros_del_contrato(c):
        m = _P_CODIGO.match(p.split("→")[0].strip())
        if not m:
            continue
        raiz = raices[m.group(1)]
        if not raiz.exists():
            # Falla CERRADO desde el 2026-09-19. Antes era `continue`: sin el repo el
            # chequeo se apagaba en silencio y el contrato pasaba como si todo resolviera.
            if m.group(1) not in faltantes:
                faltantes.add(m.group(1))
                out.append(Incertidumbre(
                    chequeo="repo-no-encontrado",
                    detalle=f"el contrato cita código de fitogenix-{m.group(1)} y el repo no "
                            f"está en {raiz}. Sin él no se puede verificar ningún puntero a "
                            f"código. Seteá FITOGENIX_{m.group(1).upper()}_PATH.",
                    puntero=p))
            continue
        if not (raiz / m.group(2)).exists():
            out.append(Incertidumbre(
                chequeo="puntero-sin-archivo",
                detalle=f"{origen} cita {m.group(0)!r}, que no existe en el repo",
                puntero=p))
    return out


# --- 3 · el plan toca un bloqueante abierto de §8 ---------------------------------

_B_ID = re.compile(r"\bB-(\d{1,3})\b")


def bloqueantes_de_context() -> dict[str, tuple[str, str]]:
    """`{'B-6': ('8.6', 'título'), …}` — los bloqueantes ABIERTOS, leídos del SSOT.

    **Estar en `§8.<n>` con n≠0 es estar abierto** (intro de `§8`: "los cerrados viven
    juntos en `§8.0`"). Hasta el 2026-09-19 se decidía por un 🔴 en el cuerpo, y solo 5 de
    13 abiertos lo tenían: B-6 (⚠️) y B-12 (🟡) no disparaban. La marca del cuerpo describe
    el avance del bloqueante, no si está abierto.
    """
    out: dict[str, tuple[str, str]] = {}
    for sec in secciones_disponibles():
        if not sec.startswith("8.") or sec == "8.0":
            continue
        titulo = load_section(f"§{sec}").splitlines()[0].lstrip("# ").strip()
        titulo = re.sub(r"^§[\d.]+\s*—\s*", "", titulo)
        for b in _B_ID.findall(titulo.split("·")[0] + " " + titulo):
            out.setdefault(f"B-{b}", (sec, titulo))
    return out


def bloqueante_abierto(c: ContratoAprobado) -> list[Incertidumbre]:
    """Hay una decisión de producto sin tomar en el camino.

    Dispara por dos vías: el contrato **cita** `§8.<n>` abierto, o **nombra** un `B-<n>`
    abierto en cualquier campo (objetivo, reglas, supuestos, briefs). La segunda existe
    porque tocar un bloqueante sin citarlo es justo lo que un modelo apurado haría.
    """
    abiertos = bloqueantes_de_context()
    por_seccion = {sec: (b, t) for b, (sec, t) in abiertos.items()}
    vistos: set[str] = set()
    out = []
    for origen, p in _punteros_del_contrato(c):
        m = _P_CONTEXT.match(p)
        if m and m.group(1) in por_seccion and m.group(1) not in vistos:
            vistos.add(m.group(1))
            out.append(Incertidumbre(
                chequeo="bloqueante-abierto",
                detalle=f"{origen} cita un bloqueante abierto: §{m.group(1)} — {por_seccion[m.group(1)][1]}",
                puntero=p))
    texto = c.model_dump_json()
    for b in sorted(set(f"B-{n}" for n in _B_ID.findall(texto))):
        if b in abiertos and abiertos[b][0] not in vistos:
            vistos.add(abiertos[b][0])
            out.append(Incertidumbre(
                chequeo="bloqueante-abierto",
                detalle=f"el contrato nombra {b}, abierto en §{abiertos[b][0]} — {abiertos[b][1]}",
                puntero=f"CONTEXT.md §{abiertos[b][0]}"))
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
            detalle=f"regla marcada ✅ y ninguno de sus punteros {r.punteros!r} es una ruta "
                    f"de código. Sin archivo que abrir, es ⚠️ y no ✅",
            puntero=r.puntero)
        for r in c.reglas_de_validacion
        if r.marca == Marca.VERIFICADO and not r.rutas_de_codigo
    ]


# --- 5b · regla ⚠️ o 🔴 (agregado el 2026-09-19) ------------------------------------

def regla_sin_verificar(c: ContratoAprobado) -> list[Incertidumbre]:
    """Una regla que el propio modelo marcó ⚠️ (no verificada) o 🔴 (abierta).

    Era la duda que se escapaba **a las dos fuentes a la vez**: `verificado_sin_ruta`
    solo mira ✅, y un contrato con todas las reglas en ⚠️ y `supuestos=[]` avanzaba
    sin interrupción. 🟡 no dispara: es "verificado como ausente y ya decidido".
    """
    return [
        Incertidumbre(
            chequeo="regla-sin-verificar",
            detalle=f"regla marcada {r.marca.value}: {r.enunciado[:140]}",
            puntero=r.puntero)
        for r in c.reglas_de_validacion
        if r.marca in (Marca.SIN_CONTRASTAR, Marca.ABIERTO)
    ]


# --- escalado a Opus (agregado el 2026-09-19) ---------------------------------

_SCORING = re.compile(r"scoring/|ftgEngine|constants\.ts|CONTEXT\.md\s+§[23](?:\.\d+)?$", re.I)
_MIGRACION = re.compile(r"migrations/|CONTEXT\.md\s+§8\.6$", re.I)
_AUTH = re.compile(r"\bauth|\brls\b|polic(y|ies)|supabase/.*polic", re.I)


def escalado_del_analisis(a: AnalisisDeRequerimiento | None) -> tuple[bool, bool, bool]:
    """(toca_scoring, toca_auth, toca_migracion): lo que declara el modelo **o** lo que
    derivan los punteros de sus requisitos. La unión, por la misma razón que en el HitL 2:
    declarar menos es el camino más corto a correr en el modelo barato."""
    if a is None:
        return (False, False, False)
    ps = [p for r in a.requisitos for p in r.punteros]
    textos = ps + [r.enunciado for r in a.requisitos]
    return (
        a.toca_scoring or any(_SCORING.search(p) for p in ps),
        a.toca_auth or any(_AUTH.search(t) for t in textos),
        a.toca_migracion or any(_MIGRACION.search(p) for p in ps),
    )


def escalado_omitido(c: ContratoAprobado, modelo_usado: str) -> list[Incertidumbre]:
    """El contrato se declara de motor/auth/migración y no lo escribió Opus.

    Pasa cuando el análisis no lo anticipó. No se re-llama solo (costaría una ronda sin
    que nadie lo decida): se pregunta.
    """
    from .config import MODELO_COMPLEJO

    if c.escala_a_opus and modelo_usado and modelo_usado != MODELO_COMPLEJO:
        return [Incertidumbre(
            chequeo="escalado-omitido",
            detalle=f"el contrato toca scoring/auth/migración y lo escribió {modelo_usado}, "
                    f"no {MODELO_COMPLEJO} (PROPUESTA_grafo_fase2.md sección 5)")]
    return []


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
          rutas_nuevas: list[str] | None = None,
          modelo_contrato: str = "") -> list[Incertidumbre]:
    """Los chequeos. Es lo que `n2b_aclarar_contrato` le pasa a `hay_que_preguntar`."""
    out: list[Incertidumbre] = []
    out += seccion_inexistente(c)
    out += puntero_sin_archivo(c)
    out += bloqueante_abierto(c)
    out += campo_sin_criterio(c)
    out += verificado_sin_ruta(c)
    out += regla_sin_verificar(c)
    out += presupuesto_excedido(c)
    out += escalado_omitido(c, modelo_contrato)
    if archivos:
        out += frontera_violada(archivos, rutas_nuevas=rutas_nuevas)
    return out
