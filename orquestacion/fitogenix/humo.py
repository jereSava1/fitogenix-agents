"""
Humo de modelos: que cada ID de `RUTEO` exista **antes** de gastar un token (dictamen P0-8).

Un 404 por un ID mal escrito no es transitorio (`llm._es_transitorio`), así que no se
reintenta: rompe en el nodo que lo use, a mitad de corrida y después de haber pagado los
anteriores. `models.retrieve` no consume tokens, así que se corre antes de cada corrida real.
"""

from __future__ import annotations

from typing import Any, Iterable

from .config import RUTEO


def modelos_del_ruteo() -> list[str]:
    """Los IDs distintos que el ruteo puede pedir, en cualquier palanca."""
    return sorted({m for conf in RUTEO.values() for m in conf.values()})


def verifica_modelos(cliente: Any = None, modelos: Iterable[str] | None = None) -> list[str]:
    """Una falla por ID que la API no reconoce. Lista vacía = todos existen."""
    if cliente is None:
        from .llm import _cliente

        cliente = _cliente()
    fallas: list[str] = []
    for m in modelos or modelos_del_ruteo():
        try:
            cliente.models.retrieve(m)
        except Exception as e:  # noqa: BLE001 - se reporta, no se decide acá
            fallas.append(f"{m}: {type(e).__name__}: {str(e)[:160]}")
    return fallas
