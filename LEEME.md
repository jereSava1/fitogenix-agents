# Agentes de Fitogenix

> **La migración terminó.** Este set se llamaba "agentes de migración" y arrancaba con un
> plan de fases; la separación del backend está hecha desde la Fase 1. Lo que sigue abierto
> vive en `CONTEXT.md §8`, no en un plan.

## Cómo usar estos archivos

Cada archivo `.md` es el prompt inicial de un agente de Claude Code. Para activar un agente, abrís una sesión de Claude Code y pegás el contenido del archivo como primer mensaje, o lo usás como CLAUDE.md en el directorio correspondiente.

## Los 8 agentes

| Archivo | Agente | Cuándo usarlo |
|---------|--------|---------------|
| **`CONTEXT.md`** | **SSOT de negocio** | **Primero, siempre.** Los 8 agentes lo citan por puntero (`CONTEXT.md §X`). Escritura exclusiva del Orquestador |
| `00-orquestador.md` | Orquestador | Siempre que empieces una sesión de trabajo. Coordinador central. |
| `01-agente-ux.md` | UX/UI Expert | Cuando necesitás diseñar o mejorar un flujo de usuario antes de implementarlo. |
| `02-agente-frontend.md` | Mobile (React Native) | Cuando implementás cambios en la app Expo: pantallas, componentes, hooks, navegación. |
| `03-agente-backend.md` | Backend (Node.js) | Cuando trabajás en el servidor Fastify, Supabase, Redis, o las integraciones con IA. |
| `04-agente-qa.md` | QA y Accesibilidad | Cuando necesitás auditar calidad, tests o accesibilidad antes de dar algo por terminado. |
| `05-agente-datos.md` | Datos e IA | Cuando tocás prompts de Claude, parámetros de inferencia, o la estrategia de invalidación de cache. |
| `06-agente-etl-data.md` | ETL / Data Engineering | Cuando necesitás poblar el catálogo masivamente: dump de Open Food Facts, scrapers, pre-población sintética. |
| `07-agente-devops.md` | DevOps & Infraestructura | Cuando trabajás en Dockerfile, despliegue, rate limiting de infraestructura, o auditoría de secretos. |

## Flujo de trabajo recomendado

```
1. Abrís sesión con el Orquestador
2. Le decís qué fase del plan querés avanzar
3. El Orquestador te dice qué tarea hacer primero y con qué agente
4. Abrís una nueva sesión con ese agente especializado
5. El agente implementa, valida, y te da el resultado
6. Volvés al Orquestador con el resultado
7. El Orquestador decide qué sigue
```

## Orden de prioridad actual

**No se mantiene acá.** La lista de bloqueantes activos, con su dueño, su marca de estado y
qué falta para cerrar cada uno, vive en **`CONTEXT.md §8`** — un solo lugar, con changelog.
El Orquestador la prioriza (`00-orquestador.md`, sección "Qué está abierto"); este archivo
solo dice cómo se usa el set.

## Notas importantes

- Los agentes están diseñados para trabajar en el proyecto Fitogenix específicamente.
  Tienen el contexto del producto, la arquitectura actual y la arquitectura objetivo.
- Cada agente tiene su propio protocolo de validación antes de ejecutar cambios.
- El Orquestador tiene la autoridad final sobre el orden de los cambios.
- Nunca dos agentes deben tocar el mismo archivo en paralelo.
