# `orquestacion/` — el pipeline agéntico de Fitogenix

Estado al **2026-09-01**: **Fase 3 (contratos) cerrada.** No hay grafo todavía, y es a
propósito: `PROPUESTA_grafo_fase2.md` secciones 9 y 11 dicen que nada de `graph.py` se
escribe hasta que los schemas y sus tests estén en verde.

```
orquestacion/
├── fitogenix/
│   ├── schemas.py   contratos de transición — Pydantic es el control de calidad
│   └── guards.py    los guards de frontera — reemplazan a la DENY_LIST de PampaGrow
└── tests/           68 tests · `pytest tests/ -q`
```

## Cómo se corre

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r orquestacion/requirements.txt
cd orquestacion && pytest tests/ -q
```

## Las dos ideas que hay que entender antes de tocar esto

**1 · Si nadie firma de rutina, el contrato lo sostiene Pydantic.** Jere decidió el 31/8
que el pipeline **no pide OK antes de implementar**: se interrumpe solo si hay duda. Eso
convierte a la Fase 3 de preparación en el control de calidad principal. Un `Brief` con
texto copiado en vez de puntero **falla**; un `ContratoAprobado` con una regla sin puntero
**falla**. No hay un humano río abajo que lo note.

**2 · Los validadores corren DESPUÉS del modelo.** Es el patrón que PampaGrow adoptó
cuando eliminó `TOOLS_BY_AGENT`: un validador atado a una tool el modelo lo puede llamar y
después describir como quiera; corrido después, su resultado es un hecho del estado. Por eso
`hay_que_preguntar()` une dos fuentes y la segunda no pasa por el modelo — declarar menos
incertidumbre es el camino más corto a no ser interrumpido.

## Lo que sigue (Fase 4)

`context_loader.py`, `llm.py`, `graph.py`, `run.py` y el checkpointer en SQLite. Se copian
de `pampagrow-ai/orchestration` con la tabla de `PROPUESTA_grafo_fase2.md` sección 8 al
lado. Dos adaptaciones ya identificadas: el regex de headings del cargador (PampaGrow usa
`## 4.2`, nosotros `## §4.2`) y sacar la indirección `DOCS_ROOT` — `CONTEXT.md` vive en
este mismo repo.

## Lo que quedó abierto y no es de la Fase 3

| Qué | Dónde |
|---|---|
| 🔴 `GuideScreen.tsx` transcribe los cuatro cortes de banda y el sello | violación real de `CONTEXT.md §3.1`, encontrada por el guard |
| 🟡 La excepción de `SUITE_DEL_MOTOR` en `guards.py` | la escribió el pipeline, no el dueño de `§3.1`. Pendiente de ratificación |
| 🟡 `CONVENCIONES_EQUIPO.md` sección 3 vs. la práctica | asunto de commit en inglés y ≤72 caracteres: 22 de 115 commits recientes pasan de 72 y la mayoría están en español. No se valida a propósito |
| 🟡 `CONTEXT.md §7` sigue diciendo que `architect` no existe | ya existe: `08-agente-arquitecto.md`. Lo actualiza el Orquestador, único escritor |
