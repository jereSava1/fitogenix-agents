"""
Carga `CONTEXT.md` **por sección**.

El motivo, y es el objetivo número uno de todo este pipeline: ningún agente lee el
documento entero por reflejo. El `Brief` apunta a `§X.Y` y este cargador entrega
exactamente eso. Si un agente necesita una sección que su Brief no le apuntó, lo pide
en `blockers` en vez de leer de más — que un agente lea de su cuenta es señal de que
el Brief se armó mal, y eso hay que ver, no tapar.

Cuánto vale, medido el 2026-09-08 sobre los diez agentes:

    sin cargador (SSOT entero en cada invocación)   800.323 B
    con cargador y punteros finos                   320.069 B    −61 %

Dos diferencias con el cargador de PampaGrow, las dos deliberadas:

  1. **Sin `DOCS_ROOT`.** `CONTEXT.md` vive en este mismo repo; la indirección no
     compraba nada y era una variable más que podía apuntar mal.
  2. **El regex lleva `§`.** PampaGrow numera `## 4.2`; acá es `## §4.2`, y
     `NUTRICION.md` usa `## §N5`. Copiar el regex tal cual no habría matcheado nada.

Y una consecuencia del 2026-09-08 que conviene saber: **`§8` a secas ya casi no trae
nada.** Los bloqueantes pasaron a ser `§8.2`…`§8.20`, así que `§8` devuelve solo su
introducción —467 B— que dice justamente que hay que apuntar más fino. Es el
comportamiento buscado, no un bug.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .config import SETTINGS

#: `## §4.2`, `### §8.19`, `## §N5`. El `§` es parte del formato, no decoración.
_H = re.compile(r"^(#{2,3})\s*§(N?\d+(?:\.\d+)?)\s*(?:—|-|\s)?\s*(.*)$", re.MULTILINE)


class SeccionNoEncontrada(KeyError):
    """El Brief apuntó a una sección que no existe. El hueco no se rellena: se devuelve.

    Es una de las cinco fuentes de incertidumbre determinista de
    `PROPUESTA_grafo_fase2.md` sección 2 — un `§X` inventado significa que el Brief se
    armó mal o que el agente inventó el puntero, y las dos cosas frenan el pipeline.
    """

    def __str__(self) -> str:
        return self.args[0]


@lru_cache(maxsize=8)
def _texto(ruta: str) -> str:
    p = Path(ruta)
    if not p.exists():
        raise FileNotFoundError(f"No encuentro {p}. Sin SSOT no se opera.")
    return p.read_text(encoding="utf-8")


@lru_cache(maxsize=4)
def _indice(ruta: str) -> dict[str, tuple[int, int, str]]:
    txt = _texto(ruta)
    hs = list(_H.finditer(txt))
    idx: dict[str, tuple[int, int, str]] = {}
    for i, m in enumerate(hs):
        fin = hs[i + 1].start() if i + 1 < len(hs) else len(txt)
        idx[m.group(2).lower()] = (m.start(), fin, m.group(3).strip())
    return idx


def _archivo_de(puntero: str) -> str:
    """Qué documento nombra el puntero. Por default, `CONTEXT.md`."""
    if "NUTRICION" in puntero.upper() or re.search(r"§\s*N\d", puntero, re.I):
        return str(SETTINGS.nutricion_md)
    return str(SETTINGS.context_md)


def secciones_disponibles(puntero_o_archivo: str = "CONTEXT.md") -> list[str]:
    idx = _indice(_archivo_de(puntero_o_archivo))
    return sorted(idx, key=lambda s: [int(p) for p in re.findall(r"\d+", s)] or [99])


def load_section(puntero: str) -> str:
    """`load_section("CONTEXT.md §5.2")`, `load_section("§5.2")` o `load_section("5.2")`."""
    archivo = _archivo_de(puntero)
    clave = puntero.split("§")[-1].strip().replace(" ", "").rstrip(".").lower()
    # Un puntero como `CONTEXT.md §8` B-6 puede llegar con el bloqueante pegado.
    clave = re.split(r"[^\w.]", clave)[0]
    idx = _indice(archivo)
    if clave not in idx:
        raise SeccionNoEncontrada(
            f"{Path(archivo).name} §{clave} no existe. "
            f"Disponibles: {', '.join(secciones_disponibles(puntero))}"
        )
    ini, fin, _ = idx[clave]
    return _texto(archivo)[ini:fin].strip()


#: Dónde buscar un documento citado por nombre. La raíz se ordenó el 2026-09-19 en `docs/`
#: y `agents/`, y los tickets viven en `tareas/`: el puntero nombra el archivo, no la carpeta.
_CARPETAS = ("", "docs", "agents", "tareas", "nutricion")


def _archivo_del_documento(ref: str) -> Optional[Path]:
    """El `.md` que nombra el puntero, si existe en alguna de las carpetas del set."""
    m = re.match(r"^([\w.\-/]+\.md)", ref.strip(), re.IGNORECASE)
    if not m:
        return None
    nombre = m.group(1)
    for carpeta in _CARPETAS:
        p = SETTINGS.agentes_root / carpeta / nombre
        if p.exists():
            return p
    # `tareas/FTG-002-…md` ya trae su carpeta, y también un glob por prefijo de ticket.
    p = SETTINGS.agentes_root / nombre
    if p.exists():
        return p
    tronco = Path(nombre).stem
    for carpeta in _CARPETAS:
        base = SETTINGS.agentes_root / carpeta
        if base.is_dir():
            for cand in sorted(base.glob(f"{tronco}*.md")):
                return cand
    return None


def load_documento(ref: str) -> str:
    """Un documento del set citado por nombre, entero o por sección CON NOMBRE.

    `CONTEXT.md` y `NUTRICION.md` no pasan por acá: esos van por `§` y por `load_section`.
    Existe desde el 2026-09-20 porque el orquestador cita el ticket que está analizando
    (`FTG-002.md sección Criterio de aceptación`) y el prompt del dueño (`01-agente-ux.md`),
    y sin esto el agente recibía `[BLOQUEADO]` sobre su propia fuente.
    """
    archivo = _archivo_del_documento(ref)
    if archivo is None:
        raise SeccionNoEncontrada(f"no encuentro el documento de {ref!r} en el set")
    texto = archivo.read_text(encoding="utf-8")
    m = re.search(r"secci[oó]n\s+(.+)$", ref, re.IGNORECASE)
    if not m:
        return texto
    buscado = m.group(1).strip().strip("`\"'").lower()
    encabezados = list(re.finditer(r"^(#{1,6})\s*(.+)$", texto, re.MULTILINE))
    for i, h in enumerate(encabezados):
        if buscado in h.group(2).strip().lower():
            nivel = len(h.group(1))
            fin = next((x.start() for x in encabezados[i + 1:] if len(x.group(1)) <= nivel), len(texto))
            return texto[h.start():fin].strip()
    # La sección con nombre no aparece: se devuelve el documento y se dice por qué. El hueco
    # no se rellena en silencio, pero tampoco se pierde la fuente entera.
    return f"[SECCIÓN NO ENCONTRADA: {m.group(1).strip()!r} — va el documento completo]\n\n{texto}"


#: Tope por archivo de código inyectado. Un archivo de pantalla entero puede ser 20 KB, y el
#: presupuesto de un Brief son 12 KB: sin tope, un solo puntero lo agota. Se trunca DICIENDO
#: que se truncó — un recorte silencioso es peor que no cargar.
TOPE_DE_CODIGO_BYTES = 6_000

_P_CODIGO_REF = re.compile(r"^(fitogenix-(?:server|native))/([\w\-./]+\.\w+)(?:\s*→\s*(.+))?$")


def load_codigo(ref: str) -> str:
    """El archivo de código que cita el puntero, recortado alrededor del símbolo.

    Existe desde el 2026-09-20: los punteros a código llegaban al agente como `[BLOQUEADO]`,
    así que el arquitecto escribía contratos sobre archivos que no había visto. Sus ✅ sobre
    código eran, por construcción, "lo cité", nunca "lo abrí" (dictamen H17).

    Si el repo no está, se dice — no se rellena. Es el mismo criterio que `det.puntero_sin_archivo`.
    """
    m = _P_CODIGO_REF.match(ref.strip())
    if not m:
        raise SeccionNoEncontrada(f"{ref!r} no es un puntero a código")
    repo, relativo, simbolo = m.group(1), m.group(2), m.group(3)
    raiz = SETTINGS.server_path if repo.endswith("server") else SETTINGS.native_path
    archivo = raiz / relativo
    if not raiz.exists():
        raise SeccionNoEncontrada(f"{repo} no está en {raiz}: no se puede cargar {relativo}")
    if not archivo.exists():
        raise SeccionNoEncontrada(f"{relativo} no existe en {repo}")
    texto = archivo.read_text(encoding="utf-8", errors="ignore")
    cabecera = f"// {repo}/{relativo}" + (f" → {simbolo}" if simbolo else "")

    if simbolo:
        lineas = texto.splitlines()
        primero = next((s.strip() for s in re.split(r"[,\s]+", simbolo) if s.strip()), "")
        for i, l in enumerate(lineas):
            if re.search(rf"\b{re.escape(primero)}\b", l) and re.match(
                    r"\s*(export\s+)?(const|let|var|function|class|type|interface|enum|async)\b", l):
                trozo = "\n".join(lineas[max(0, i - 3): i + 60])
                return _recorta(f"{cabecera}\n{trozo}")
    return _recorta(f"{cabecera}\n{texto}")


def _recorta(t: str) -> str:
    b = t.encode()
    if len(b) <= TOPE_DE_CODIGO_BYTES:
        return t
    return (b[:TOPE_DE_CODIGO_BYTES].decode(errors="ignore")
            + f"\n\n[TRUNCADO a {TOPE_DE_CODIGO_BYTES} B de {len(b)} B: pedí el archivo por "
              f"puntero más fino o declaralo como supuesto]")


def load_pointers(punteros: list[str], tope: int | None = None) -> str:
    """El bloque de contexto que se le inyecta a un agente. **Solo lo apuntado.**

    Una sección que no resuelve no rompe la carga: entra marcada `[BLOQUEADO]`, para que
    el agente la vea y la reporte en vez de seguir como si nada. El chequeo determinista
    de `n2b` la levanta de ahí.
    """
    partes: list[str] = []
    afuera: list[str] = []
    peso = 0
    for p in punteros:
        # Tope de contexto (2026-09-21). Antes el presupuesto se medía DESPUÉS de haber
        # pagado: en el debut el brief de ux arrastró 38.553 B contra un tope de 12.000, y el
        # chequeo determinista lo reportó igual de tarde. Acá se corta antes de la llamada y
        # se dice qué quedó afuera, para que el que armó el Brief lo vea y apunte más fino.
        if tope is not None and peso >= tope:
            afuera.append(p)
            continue
        try:
            if "§" in p:
                partes.append(load_section(p))
            elif _P_CODIGO_REF.match(p.strip()):
                partes.append(load_codigo(p))
            else:
                partes.append(load_documento(p))
        except SeccionNoEncontrada as e:
            partes.append(f"[BLOQUEADO] {e}")
        peso = sum(len(x.encode()) for x in partes)
    if afuera:
        partes.append(
            f"[PRESUPUESTO EXCEDIDO: {len(afuera)} puntero(s) NO se cargaron, tope {tope:,} B. "
            f"Quedaron afuera: {', '.join(afuera)}. Si alguno te hace falta, pedilo en "
            f"`blockers` o en un supuesto; no supongas su contenido.]")
    return "\n\n---\n\n".join(partes)


#: Cuánto texto de cada sección entra en el índice: alcanza para saber de qué habla y
#: decidir si hace falta. El texto completo lo carga quien la cite por puntero.
ASOMO_DE_SECCION = 220


def indice_del_ssot(asomo: int = ASOMO_DE_SECCION) -> str:
    """El SSOT como índice: cada sección con su título y sus primeras líneas.

    `n1a_analizar` mandaba `contexto_completo()` —59 KB, ~15k tokens— en CADA ronda de
    aclaración, y su trabajo es trazar requisitos a punteros, no leer el documento entero.
    Con el índice sabe qué secciones existen y de qué hablan, que es lo que necesita para
    citar bien; el texto completo de lo citado lo recibe después el arquitecto.
    """
    ruta = str(SETTINGS.context_md)
    txt = _texto(ruta)
    idx = _indice(ruta)
    partes = [f"# Índice de CONTEXT.md — {len(idx)} secciones. Citá `CONTEXT.md §X`: el "
              f"texto completo de lo que cites se carga después, solo."]
    for sec in secciones_disponibles():
        ini, fin, titulo = idx[sec]
        bloque = txt[ini:fin]
        cuerpo = bloque.split("\n", 1)[1] if "\n" in bloque else ""
        cuerpo = re.sub(r"\s+", " ", cuerpo).strip()[:asomo]
        partes.append(f"## §{sec} — {titulo}\n{cuerpo}…")
    return "\n\n".join(partes)


def contexto_completo() -> str:
    """Solo el Orquestador. Ningún agente de disciplina llama a esto."""
    return _texto(str(SETTINGS.context_md))


def costo(punteros: list[str]) -> tuple[int, int]:
    """(bytes que cargan esos punteros, bytes del SSOT entero).

    Existe para que el ahorro sea **verificable en cada corrida** en vez de una cifra en
    un reporte: la Fase 6 pide medir, no estimar.
    """
    return len(load_pointers(punteros).encode()), len(contexto_completo().encode())
