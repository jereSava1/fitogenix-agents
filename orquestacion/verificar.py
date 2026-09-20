#!/usr/bin/env python3
"""
Uso:  python verificar.py [--repos ~/fitogenix-server ~/fitogenix-native] [--sin-repos]

`--sin-repos` es para CI, donde los repos hermanos no están clonados: saltea 2–4 **y lo
dice**. Sin esa bandera, un repo que no se encuentra es un fallo (exit 1), no un ⚠️.

Corre, de una, todo lo que se puede verificar sin un humano:

  1. Punteros `§X` del set de documentos → resuelven contra `CONTEXT.md`.
  2. Punteros al SSOT citados **desde el código** → resuelven (`punteros.py`).
  3. Guards de frontera sobre el código (`guards.py`): umbrales no transcritos,
     el cliente no recalcula ni habla afuera, ruta nueva con su contrato.
  4. Cobertura: cuántos archivos de `domain/` y `routes/` citan la decisión en
     la que se basan. **Se informa, no falla** — poner 30 punteros de golpe sería
     inventar trazabilidad en vez de registrarla.

Sale con código 1 si algo de 1–3 falla. Solo lectura: no toca la base ni escribe.

Por qué existe: los guards y el verificador de punteros encontraron cosas reales
—un umbral transcrito en un archivo recién escrito, una migración citada por un
nombre inexistente— pero **dependían de que alguien se acordara de correrlos**.
Un comando es más fácil de recordar que tres.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fitogenix.config import SETTINGS  # noqa: E402
from fitogenix.guards import corre_los_guards  # noqa: E402
from fitogenix.punteros import (  # noqa: E402
    cobertura,
    indice_de_secciones,
    indice_de_nutricion,
    verifica_repo,
)

#: Raíz del repo de agentes. Desde el reordenamiento del 2026-09-19 los documentos
#: cuelgan de `docs/` y los prompts de agente de `agents/`; `nutricion/` y `tareas/`
#: siguen en la raíz. El barrido de abajo recorre las cuatro.
RAIZ = Path(__file__).parent.parent
DOCS = RAIZ / "docs"
EXT = {".ts", ".tsx", ".sql"}


def punteros_de_documentos() -> list[str]:
    sec = indice_de_secciones(DOCS / "CONTEXT.md")
    nut = indice_de_nutricion(RAIZ / "nutricion" / "NUTRICION.md")
    import re

    # `§X` significa dos cosas en este proyecto: una sección de `CONTEXT.md` y una sección
    # de la rúbrica del motor (`scoring/steps.ts` → "FITOGENIX — §2: los pasos del
    # cálculo"). En el código eso obliga a exigir puntero calificado (`punteros.py`); acá,
    # en el set de documentos, el `§` pelado SÍ es de `CONTEXT.md` — salvo cuando el texto
    # está hablando **de la otra numeración**, y entonces la nombra justo antes.
    # Se encontró el 2026-09-18: el propio `CHANGELOG.md`, explicando la ambigüedad, citaba
    # `§4.7` y `§4.5` de la rúbrica y el verificador los reportaba como punteros rotos. Un
    # verificador que falla sobre el documento que documenta el problema entrena a ignorarlo.
    ajeno = re.compile(r"(?:\.(?:ts|tsx|sql|js)`?|r[uú]brica|motor)\s*(?:→\s*)?[`'\"]?\s*$",
                       re.IGNORECASE)
    VENTANA = 40

    fallas = []
    for d in sorted(
        list(RAIZ.glob("*.md")) + list(DOCS.glob("*.md"))
        + list(RAIZ.glob("agents/*.md")) + list(RAIZ.glob("nutricion/*.md"))
        + list(RAIZ.glob("tareas/*.md")) + list(RAIZ.glob(".claude/agents/*.md"))
    ):
        t = d.read_text(encoding="utf-8")
        vistos: set[str] = set()
        for m in re.finditer(r"§(\d+(?:\.\d+)?)\b", t):
            if m.group(1) in sec or m.group(1) in vistos:
                continue
            if ajeno.search(t[max(0, m.start() - VENTANA):m.start()]):
                continue  # es un § de la rúbrica del motor, no de CONTEXT.md
            vistos.add(m.group(1))
            fallas.append(f"{d.name}: §{m.group(1)} no existe en CONTEXT.md")
        for m in set(re.findall(r"§(N\d+)\b", t)):
            if m not in nut:
                fallas.append(f"{d.name}: §{m} no existe en NUTRICION.md")
    return fallas


def main() -> int:
    args = sys.argv[1:]
    sin_repos = "--sin-repos" in args
    args = [a for a in args if a != "--sin-repos"]
    # Los defaults salen de `config.SETTINGS`, que **busca** los repos en vez de fijar
    # `~/<nombre>`. Hasta el 2026-09-18 estaban fijos y no existían en esta máquina: este
    # comando salteaba en silencio 3 de sus 4 verificaciones y salía 0 igual.
    repos = [Path(p).expanduser() for p in args[args.index("--repos") + 1:]] if "--repos" in args else [
        SETTINGS.server_path, SETTINGS.native_path
    ]
    fallas: list[str] = []

    print("1 · punteros §X del set de documentos")
    f = punteros_de_documentos()
    print(f"   {'✅ todos resuelven' if not f else f'❌ {len(f)}'}")
    fallas += f
    for x in f:
        print("     ", x)

    for raiz in repos:
        if not raiz.exists():
            # Falla CERRADO desde el 2026-09-19 (dictamen H16/P0-6). Antes esto era un ⚠️ con
            # exit 0: salteaba 3 de 4 verificaciones y decía "todo en verde".
            if sin_repos:
                print(f"\n   ⏭  {raiz} no está — salteado a pedido (--sin-repos): 2–4 NO corrieron")
                continue
            print(f"\n   ❌ {raiz} no está. Seteá FITOGENIX_SERVER_PATH / FITOGENIX_NATIVE_PATH, "
                  f"pasá --repos, o --sin-repos si es a propósito.")
            fallas.append(f"repo no encontrado: {raiz}")
            continue
        print(f"\n══ {raiz.name} ══")

        print("2 · punteros al SSOT citados desde el código")
        f = verifica_repo(raiz, RAIZ)
        print(f"   {'✅ todos resuelven' if not f else f'❌ {len(f)}'}")
        fallas += f
        for x in f:
            print("     ", x)

        print("3 · guards de frontera")
        archivos, nuevas = [], []
        for carpeta in ("src", "scripts", "migrations"):
            base = raiz / carpeta
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if p.suffix in EXT and p.is_file() and "node_modules" not in p.parts:
                    archivos.append((f"{raiz.name}/{p.relative_to(raiz)}",
                                     p.read_text(encoding="utf-8", errors="ignore")))
        f = corre_los_guards(archivos, rutas_nuevas=nuevas)
        print(f"   {'✅ limpio' if not f else f'❌ {len(f)}'}  ({len(archivos)} archivos)")
        fallas += f
        for x in f:
            print("     ", x)

        con, tot = cobertura(raiz)
        pct = f"{100 * con // tot}%" if tot else "n/a"
        print(f"4 · cobertura de punteros en domain/ y routes/: {con}/{tot} ({pct}) — informativo")

    print(f"\n{'✅ todo en verde' if not fallas else f'❌ {len(fallas)} hallazgo(s)'}")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
