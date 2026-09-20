# `orquestacion/` — el pipeline agéntico de Fitogenix

Estado al **2026-09-19**: **el pipeline corre de punta a punta en dry-run**, sin llamar a
ningún modelo y sin API key. El orden lo fijó `PROPUESTA_grafo_fase2.md` secciones 9 y 11
—nada de `graph.py` hasta que los schemas y sus tests estuvieran en verde— y se respetó.

Lo que **todavía no pasó**: la primera corrida real. Antes va la auditoría de
`PROMPT_auditoria_entorno_agentico.md`, y después el debut lo autoriza Jere: es el primer
momento en que esto gasta tokens.

```
orquestacion/
├── fitogenix/
│   ├── schemas.py         los contratos — Pydantic es el mecanismo anti-alucinación
│   ├── guards.py          las fronteras del SSOT, verificadas sin modelo
│   ├── punteros.py        que las citas al SSOT resuelvan de verdad
│   ├── det.py             los 7 chequeos deterministas de incertidumbre
│   ├── config.py          rutas, ruteo de modelo, dry-run
│   ├── context_loader.py  carga por sección: de dónde sale el ahorro
│   ├── llm.py             la llamada al modelo — lo único que gasta plata
│   ├── stubs.py           la salida mínima válida de cada nodo (dry-run)
│   ├── sessions.py        checkpointer SQLite + el handoff en .md
│   └── graph.py           9 nodos, 2 interrupt(), 3 techos, UNA salida
├── run.py                 el CLI
├── verificar.py           guards + punteros + cobertura, un solo comando
└── tests/                 181 tests, ninguno necesita API key
```

## Correrlo

```bash
# el grafo entero, sin llamar a ningún modelo y sin credencial
python run.py --ticket FTG-002 --dry-run --entrada-archivo ../tareas/FTG-002-*.md

# qué quedó esperando respuesta
python run.py --list

# retomar — desde otra terminal, otro día. `--accion` es OBLIGATORIA: nada se aprueba por default
python run.py --resume FTG-002 --accion contratar --respuesta "P1=el alcance es X"

# antes de la primera corrida real: ¿existen los IDs de modelo de RUTEO? (no gasta tokens)
python run.py --humo
```

`--hasta contrato` es el default: la corrida corta después del HitL 2 y termina
`contrato-listo`. `--hasta completo` solo corre en dry-run hasta que `n3`/`n4` generen
código real (`DICTAMEN_auditoria_pre_debut.md`, P1-1). Cada entrega de un modelo trae un
`Cierre` —qué cambió, cómo se validó, qué revisión manual hace falta y cuál es el próximo
paso— y el resumen de la corrida lo muestra nodo por nodo. Las llamadas crudas quedan en
`.fitogenix/llamadas/<ticket>/`.

Códigos de salida: **0** cerrada o `contrato-listo` · **2** esperando respuesta humana · **1** escalada o
abortada. El 2 es su propio código a propósito: una corrida interrumpida no es un
fracaso, pero tampoco es un éxito, y en CI se tratan distinto.

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
