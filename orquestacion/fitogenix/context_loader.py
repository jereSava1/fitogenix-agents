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


def load_pointers(punteros: list[str]) -> str:
    """El bloque de contexto que se le inyecta a un agente. **Solo lo apuntado.**

    Una sección que no resuelve no rompe la carga: entra marcada `[BLOQUEADO]`, para que
    el agente la vea y la reporte en vez de seguir como si nada. El chequeo determinista
    de `n2b` la levanta de ahí.
    """
    partes = []
    for p in punteros:
        try:
            partes.append(load_section(p))
        except SeccionNoEncontrada as e:
            partes.append(f"[BLOQUEADO] {e}")
    return "\n\n---\n\n".join(partes)


def contexto_completo() -> str:
    """Solo el Orquestador. Ningún agente de disciplina llama a esto."""
    return _texto(str(SETTINGS.context_md))


def costo(punteros: list[str]) -> tuple[int, int]:
    """(bytes que cargan esos punteros, bytes del SSOT entero).

    Existe para que el ahorro sea **verificable en cada corrida** en vez de una cifra en
    un reporte: la Fase 6 pide medir, no estimar.
    """
    return len(load_pointers(punteros).encode()), len(contexto_completo().encode())
