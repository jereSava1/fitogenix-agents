# Fitogenix Agents

Este repositorio reúne el set de agentes de trabajo para Fitogenix, pensado para guiar a un equipo en la evolución del producto. (La migración del backend fuera de Expo ya está hecha; ver `CONTEXT.md §5`.)

## Qué incluye

- Prompt inicial del orquestador
- Agentes especializados de UX, frontend, backend, QA y datos/IA
- Documentos de contexto de negocio, convenciones y decisiones del equipo

## Estructura

- `CONTEXT.md` — **fuente única de verdad de negocio.** Los agentes la citan por puntero (`CONTEXT.md §X`) en vez de duplicar el contexto; escritura exclusiva del Orquestador
- `00-orquestador.md` — coordinación general del trabajo
- `01-agente-ux.md` — experiencia de usuario y accesibilidad
- `02-agente-frontend.md` — implementación en React Native + Expo (post-Fase 1: el cliente es solo UI)
- `03-agente-backend.md` — backend Node.js + Fastify, Supabase, Redis y APIs externas
- `04-agente-qa.md` — auditoría, tests y calidad
- `05-agente-datos.md` — prompts de IA, costos y estrategia de cache
- `06-agente-etl-data.md` — poblamiento masivo de datos: ingesta de Open Food Facts, scrapers, pre-población sintética
- `07-agente-devops.md` — Dockerfile, despliegue, rate limiting de infraestructura y auditoría de secretos
- `CONVENCIONES_EQUIPO.md` — reglas operativas del equipo
- `DICCIONARIO_DOMINIO.md` — vocabulario y conceptos clave
- `BITACORA_DECISIONES.md` — registro de decisiones relevantes

## Cómo usarlo

1. Cloná este repositorio.
2. Abrí el archivo del agente que quieras usar.
3. Copiá su contenido y pégalo como primer mensaje en una sesión de Claude Code.
4. Comenzá con `00-orquestador.md` para coordinar el trabajo.

## Instalación rápida

```bash
git clone https://github.com/jereSava1/fitogenix-agents.git
cd fitogenix-agents
```

## Recomendación de uso para el equipo

- Usá el orquestador como punto de entrada para cada iniciativa.
- Delegá tareas específicas a los agentes especializados.
- Registrá decisiones importantes en `BITACORA_DECISIONES.md`.

## Licencia

Este proyecto se publica con licencia MIT.
