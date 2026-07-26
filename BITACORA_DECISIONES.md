# Bitácora de Decisiones — Fitogenix

Registro de decisiones de arquitectura del proyecto, en formato **ADR** (Architecture Decision Record). Cada decisión relevante —de arquitectura, de stack, de modelo de negocio con impacto técnico, o de reversión tras un fallo— se registra acá.

Un ADR es inmutable una vez aceptado: no se edita, se **supersede** con uno nuevo que lo referencie. Así queda el rastro de por qué el sistema es como es.

**Cuándo registrar un ADR:** al elegir entre alternativas técnicas con consecuencias a largo plazo (framework, base de datos, límite de un servicio), al cambiar una decisión previa, o al revertir una tarea fallida tras 2 iteraciones (Protocolo de Reversión del Orquestador).

---

## Plantilla ADR

Copiar este bloque para cada decisión nueva. Numeración incremental (`ADR-002`, `ADR-003`, ...).

```markdown
## ADR-NNN: [Título corto y descriptivo de la decisión]

- **Fecha:** AAAA-MM-DD
- **Estado:** Propuesto | Aceptado | Rechazado | Supersedido por ADR-XXX
- **Decididores:** [agentes / roles involucrados]

### Contexto
Cuál es el problema o la fuerza que motiva esta decisión. Las restricciones
relevantes (técnicas, de negocio, de tiempo). Qué es verdad hoy que obliga a decidir.

### Decisión
Qué se decidió hacer, en una afirmación clara y directa. "Vamos a X."

### Alternativas consideradas
- **Opción A:** descripción · por qué se descartó.
- **Opción B:** descripción · por qué se descartó.

### Consecuencias
- **Positivas:** qué mejora, qué habilita.
- **Negativas / costos:** qué se paga, qué se vuelve más difícil, qué deuda se asume.
- **Neutras / seguimiento:** qué hay que vigilar, qué queda pendiente de revisar.
```

---

## ADR-001: Separar el Backend de Expo a un servidor Node.js + Fastify

- **Fecha:** 2026-07-01
- **Estado:** Aceptado
- **Decididores:** Orquestador (Tech Lead), Agente Backend

### Contexto
La primera versión de Fitogenix corría toda la lógica dentro de la app Expo, usando las rutas API de Expo Router (`+api.ts`) como "backend". Ese modelo tenía problemas estructurales serios:

- Las rutas `+api.ts` corren en el runtime de Expo Router, una caja negra sin control de infraestructura: no se puede agregar Redis, ni rate limiting real, ni observabilidad propia, ni escalar el backend independientemente del cliente.
- Endpoints sensibles quedaban expuestos sin autenticación (`/api/analyze` proxy a Anthropic, `/api/cache-product` con service role de Supabase), permitiendo quemar API keys o envenenar el caché.
- La lógica de negocio (motor de scoring, orquestación de OFF/Claude) vivía duplicada o mezclada con la UI, con riesgo de divergencia entre lo que calcula el cliente y lo que debería ser autoritativo.
- El proyecto apunta a decenas de miles de usuarios mensuales y a un modelo Freemium con cuotas server-side: nada de eso es viable sin un backend propio y controlable.

### Decisión
Separar el backend a un proyecto independiente **`fitogenix-server`**, construido con **Node.js + Fastify + TypeScript**, desplegable por su cuenta. La app Expo queda como cliente puro (UI + llamadas al backend propio con JWT). Toda la lógica de negocio, las integraciones con servicios externos (Open Food Facts, Anthropic, SerpAPI, remove.bg) y el acceso a Supabase con service role viven exclusivamente en el servidor.

### Alternativas consideradas
- **Seguir con las rutas `+api.ts` de Expo Router, agregándoles auth:** descartada. Resuelve la autenticación pero no el problema de fondo — seguís sin control de infraestructura, sin Redis, sin poder escalar el backend aparte, y sin observabilidad. Es maquillaje sobre una arquitectura que no da para el objetivo de escala.
- **Backend serverless (funciones lambda):** descartada para esta etapa. La orquestación del pipeline (caché → OFF → Claude → imágenes) con estado de caché caliente (Redis) y deduplicación in-flight se modela mejor en un servicio persistente. Serverless agregaría complejidad de cold starts y de estado compartido sin beneficio claro a esta escala.
- **Framework Express en vez de Fastify:** descartada. Fastify ofrece mejor rendimiento, validación de esquemas nativa y un sistema de plugins más limpio, sin costo de adopción relevante para el equipo.

### Consecuencias
- **Positivas:**
  - Control total de la infraestructura: se habilitan Redis (caché caliente), rate limiting, JWT en todos los endpoints, y observabilidad propia.
  - Las API keys y el service role de Supabase quedan estrictamente server-side; el cliente nunca los ve.
  - Una única fuente de verdad para el scoring y las reglas de negocio (el servidor), eliminando la divergencia cliente/servidor.
  - Se habilita el modelo Freemium: la lógica de cuotas y el descuento de créditos pueden vivir transaccionalmente en el backend.
  - Backend y cliente escalan y se despliegan por separado.
- **Negativas / costos:**
  - Dos repos que mantener y coordinar, con un contrato de API entre ellos.
  - El motor de scoring (`ftgEngine.ts`) y sus tipos se comparten conceptualmente entre repos; hay que mantenerlos en sync (por ahora, copia + tipos en el cliente; a futuro, evaluar paquete compartido).
  - Costo de infraestructura y de deploy del nuevo servicio (Railway/Render + Upstash).
- **Neutras / seguimiento:**
  - Migración por fases para no romper lo que funciona: crear el backend, migrar el cliente, agregar Redis/auth/rate-limit, y features de negocio.
  - Revisar a futuro si conviene extraer el dominio compartido (`ftgEngine`) a un paquete npm privado para eliminar la duplicación de código entre repos.
