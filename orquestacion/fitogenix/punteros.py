"""
Verifica que los punteros al SSOT que el código cita **resuelvan de verdad**.

Es la otra mitad de `guards.py`. Los guards impiden que el código copie el SSOT;
esto impide que lo cite mal. Las dos fallas tienen la misma consecuencia —alguien
lee el código, sigue la referencia y llega a otra cosa o a nada— y las dos ya
pasaron en este proyecto:

  · `ENGINE_VERSION` se citaba como `ftgEngine.ts:24` y vive en `constants.ts:24`.
    Archivo equivocado, número correcto, invisible durante tres días.
  · `scripts/etl/jobs/fixDataQuality.ts` mandaba a aplicar
    `migrations/010_manufacturer_info.sql`, un archivo que no existe desde el
    renumerado `a0560ca`. El job citaba por un nombre inexistente justamente la
    migración que necesita para funcionar.

── La ambigüedad que obliga a exigir calificación ──

**`§X` significa dos cosas distintas en este proyecto**, y el código usa la segunda
mucho más que la primera. En `fitogenix-server` hay 46 apariciones de `§2`, 13 de
`§4.7` y 9 de `§4.5` que **no son de `CONTEXT.md`**: son secciones de la rúbrica del
motor, numeradas en el encabezado de `scoring/steps.ts` (*"FITOGENIX — §2: los pasos
del cálculo"*). `CONTEXT.md §4` ni siquiera llega a `§4.5`.

Por eso este verificador **solo valida punteros calificados** — los que nombran el
documento: `CONTEXT.md §5.2`, `NUTRICION.md §N5`, `ADR-006`. Un `§X` pelado se
ignora, porque no se puede saber a cuál de las dos numeraciones pertenece.

Que existan dos numeraciones con la misma notación es deuda real y está reportada;
resolverla es de **backend** (dueño del motor) y del **orquestador** (dueño de la
convención), no de este archivo.
"""

from __future__ import annotations

import re
from pathlib import Path

#: Punteros calificados: nombran el documento, así que no hay ambigüedad posible.
_P_CONTEXT = re.compile(r"CONTEXT\.md\s*[`'\"]?\s*§(\d+(?:\.\d+)?)")
_P_NUTRICION = re.compile(r"NUTRICION\.md\s*[`'\"]?\s*§(N\d+)")
_P_ADR = re.compile(r"\bADR-(\d{3})\b")
#: Rutas de archivo citadas entre backticks, para verificar que existan.
_P_ARCHIVO = re.compile(r"`((?:migrations|src|scripts)/[\w\-./]+\.\w{2,4})`")
#: Número de línea: prohibido por la convención del 2026-08-31.
_P_LINEA = re.compile(r"`?([\w\-./]+\.\w{2,4}):(\d+)`?")

_EXT_CODIGO = {".ts", ".tsx", ".sql", ".js"}


def indice_de_secciones(context_md: Path) -> set[str]:
    """Las secciones `§X` que `CONTEXT.md` define hoy, de sus encabezados."""
    return set(re.findall(r"^#{2,3}\s*§([\d.]+)", context_md.read_text(encoding="utf-8"), re.M))


def indice_de_nutricion(nutricion_md: Path) -> set[str]:
    return set(re.findall(r"^#{2,3}\s*§(N\d+)", nutricion_md.read_text(encoding="utf-8"), re.M))


def indice_de_adrs(bitacora_md: Path) -> set[str]:
    return set(re.findall(r"^##\s*ADR-(\d{3})", bitacora_md.read_text(encoding="utf-8"), re.M))


def verifica_texto(
    ruta: str,
    texto: str,
    *,
    secciones: set[str],
    secciones_nutricion: set[str],
    adrs: set[str],
    raiz_repo: Path | None = None,
) -> list[str]:
    """Punteros calificados que no resuelven. Lista vacía = limpio."""
    fallas: list[str] = []

    for m in _P_CONTEXT.finditer(texto):
        if m.group(1) not in secciones:
            fallas.append(f"{ruta}: cita `CONTEXT.md §{m.group(1)}`, que no existe")
    for m in _P_NUTRICION.finditer(texto):
        if m.group(1) not in secciones_nutricion:
            fallas.append(f"{ruta}: cita `NUTRICION.md §{m.group(1)}`, que no existe")
    for m in _P_ADR.finditer(texto):
        if m.group(1) not in adrs:
            fallas.append(f"{ruta}: cita `ADR-{m.group(1)}`, que no está en BITACORA_DECISIONES.md")

    if raiz_repo is not None:
        for m in _P_ARCHIVO.finditer(texto):
            if not (raiz_repo / m.group(1)).exists():
                fallas.append(f"{ruta}: cita el archivo `{m.group(1)}`, que no existe en el repo")

    for m in _P_LINEA.finditer(texto):
        fallas.append(
            f"{ruta}: cita por número de línea (`{m.group(1)}:{m.group(2)}`). "
            f"Archivo + símbolo, nunca línea — la línea se mueve y la cita sigue pareciendo sana."
        )
    return fallas


def verifica_repo(raiz_repo: Path, raiz_agentes: Path) -> list[str]:
    """Recorre el código de un repo y devuelve los punteros rotos.

    `raiz_agentes` es la raíz del repo de agentes, no la carpeta `docs/`: desde el
    reordenamiento del 2026-09-19 el SSOT vive en `docs/` pero `nutricion/` quedó
    colgando de la raíz, así que cada documento se compone con su prefijo propio.
    """
    secciones = indice_de_secciones(raiz_agentes / "docs" / "CONTEXT.md")
    nutricion = indice_de_nutricion(raiz_agentes / "nutricion" / "NUTRICION.md")
    adrs = indice_de_adrs(raiz_agentes / "docs" / "BITACORA_DECISIONES.md")

    fallas: list[str] = []
    for carpeta in ("src", "scripts", "migrations"):
        base = raiz_repo / carpeta
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.suffix not in _EXT_CODIGO or not p.is_file() or "node_modules" in p.parts:
                continue
            fallas += verifica_texto(
                str(p.relative_to(raiz_repo)),
                p.read_text(encoding="utf-8", errors="ignore"),
                secciones=secciones,
                secciones_nutricion=nutricion,
                adrs=adrs,
                raiz_repo=raiz_repo,
            )
    return fallas


#: Archivos donde una decisión de negocio DEBERÍA venir con su puntero. No falla si
#: no lo tiene: se reporta como cobertura, porque poner 47 punteros de golpe sería
#: inventar trazabilidad en vez de registrarla.
_CON_DECISION = ("src/domain/", "src/routes/")


def cobertura(raiz_repo: Path) -> tuple[int, int]:
    """(archivos con puntero calificado, archivos de dominio y rutas)."""
    con = tot = 0
    for prefijo in _CON_DECISION:
        base = raiz_repo / prefijo
        if not base.exists():
            continue
        for p in base.rglob("*.ts"):
            if ".test." in p.name or "node_modules" in p.parts:
                continue
            tot += 1
            t = p.read_text(encoding="utf-8", errors="ignore")
            if _P_CONTEXT.search(t) or _P_NUTRICION.search(t) or _P_ADR.search(t):
                con += 1
    return con, tot
