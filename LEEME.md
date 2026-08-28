# Agentes de Migración — Fitogenix

## Cómo usar estos archivos

Cada archivo `.md` es el prompt inicial de un agente de Claude Code. Para activar un agente, abrís una sesión de Claude Code y pegás el contenido del archivo como primer mensaje, o lo usás como CLAUDE.md en el directorio correspondiente.

## Los 8 agentes

| Archivo | Agente | Cuándo usarlo |
|---------|--------|---------------|
| `00-orquestador.md` | Orquestador | Siempre que empieces una sesión de trabajo. Coordinador central. |
| `01-agente-ux.md` | UX/UI Expert | Cuando necesitás diseñar o mejorar un flujo de usuario antes de implementarlo. |
| `02-agente-frontend.md` | Frontend (React Native) | Cuando implementás cambios en la app Expo: pantallas, componentes, hooks, navegación. |
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

Fase 0 (fixes críticos: UNIQUE en `barcode`, JWT auth, rate limit) y la migración de identidad de producto (`id`/`barcode`/`name_key`/`engine_version`) ya están resueltas — ver el checklist de estado en `00-orquestador.md`. El foco actual es:

1. **Agente ETL** → poblar el catálogo (dump de OFF filtrado a Argentina/LATAM + scrapers + pre-población sintética)
2. **Agente DevOps** → Dockerfile y despliegue formal de `fitogenix-server` (hoy no existe ninguno)
3. **Frontend/UX** → Fase 2 del plan (expo-image, React Query, poda de dependencias)

## Notas importantes

- Los agentes están diseñados para trabajar en el proyecto Fitogenix específicamente.
  Tienen el contexto del producto, la arquitectura actual y la arquitectura objetivo.
- Cada agente tiene su propio protocolo de validación antes de ejecutar cambios.
- El Orquestador tiene la autoridad final sobre el orden de los cambios.
- Nunca dos agentes deben tocar el mismo archivo en paralelo.
