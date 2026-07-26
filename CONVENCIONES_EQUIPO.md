# Convenciones de Equipo — Fitogenix

Documento estático de reglas de desarrollo. Aplica a los dos repos del proyecto: **`fitogenix-server`** (Node.js + Fastify + TypeScript) y **`fitogenix-native`** (React Native + Expo + TypeScript). El objetivo es consistencia: que el código de cualquier agente sea indistinguible del de otro y que un cambio de contexto entre backend y frontend no exija reaprender convenciones.

Estas reglas no se negocian por tarea. Si algo acá queda obsoleto, se actualiza este documento con una entrada en `BITACORA_DECISIONES.md`, no se ignora en silencio.

---

## 1. Nomenclatura

**General (ambos repos):**
- **TypeScript estricto siempre.** Cero `any`. Si un tipo de terceros obliga a `any`, se aísla y se comenta por qué.
- Nombres en **inglés** para código (variables, funciones, tipos, archivos de código). El **dominio de negocio** y el copy de usuario van en **español** (ej. `score`, `tier`, pero labels "EXCELENTE", "Fitogénico").
- Nada de abreviaturas crípticas. `product`, no `prod`. `ingredient`, no `ing` (salvo variables de loop locales y efímeras).

**Variables y funciones:** `camelCase`. Funciones son verbos (`lookupProduct`, `fetchByBarcode`). Booleanos con prefijo `is/has/should` (`isBarcode`, `hasImage`).

**Tipos e interfaces:** `PascalCase` (`FitogenixProduct`, `AnalyzedIngredient`). Sin prefijo `I`.

**Constantes de módulo:** `UPPER_SNAKE_CASE` (`ENGINE_VERSION`, `REDIS_KEY_PREFIX`).

**Archivos:**
- Backend: `camelCase.ts` para servicios/módulos (`productLookupService.ts`), agrupados por responsabilidad (`services/`, `routes/`, `domain/`).
- Frontend: `PascalCase.tsx` para componentes y pantallas (`ScoreDial.tsx`, `HomeScreen.tsx`); `camelCase.ts` para hooks (`useProductSearch.ts`) y utilidades.

**Componentes React:** `PascalCase`. Hooks: prefijo `use` (`useScanFlow`). Un componente presentacional no hace fetch (los datos entran por props).

**Eventos de analytics:** `snake_case` (`scan_completed`, `paywall_viewed`).

**Claves de caché:** con prefijo namespaced (`ftg:product:{barcode}`, `ftg:search:{query}`).

---

## 2. Estructura de Pull Requests

Un PR resuelve **una** cosa. PRs chicos, enfocados y revisables (idealmente < 400 líneas de diff efectivo).

**Título:** imperativo y claro, en inglés, sin punto final.
`Add product cache with raw-data persistence`

**Descripción — plantilla obligatoria:**
```markdown
## Qué
Una o dos frases: qué hace este PR.

## Por qué
El problema o la necesidad que resuelve.

## Cómo
Decisiones técnicas relevantes y trade-offs.

## Tests
- `npx tsc --noEmit`: OK
- `npm test`: X passed (Y total)
- Tests nuevos: ...

## Riesgos residuales
Qué podría romperse, qué quedó fuera de alcance.

## Checklist
- [ ] TypeScript sin errores
- [ ] Tests pasando (nuevos donde corresponde)
- [ ] Sin `.catch` silenciosos ni errores tragados
- [ ] a11y verificada (si toca UI)
- [ ] Sin secretos ni PII en el código ni en los logs
```

**Reglas:**
- No se mergea con CI en rojo.
- No se mergea sin tests si el cambio toca `domain/` o `services/`.
- Cambios en `ftgEngine.ts` requieren tests nuevos que cubran el cambio, sí o sí.
- El autor no aprueba su propio PR; pasa por el Agente de QA cuando corresponde.

---

## 3. Git Flow — Micro-commits

**Rama:** nunca se trabaja directo sobre `main`. Rama por tarea, nombrada `tipo/descripcion-corta` (`feat/product-cache`, `fix/tier-thresholds`, `chore/remove-unused-deps`).

**Micro-commits:** commits chicos, atómicos y coherentes. Cada commit deja el repo compilando y con tests en verde — no commits "WIP roto". Un commit = un paso lógico completo.

**Mensajes de commit:**
- Primera línea imperativa, en inglés, ≤ 72 caracteres, sin punto final.
- Cuerpo (cuando aporta) explica el **porqué**, no el qué (el diff ya dice el qué).
- Prefijos convencionales: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`.
```
feat: add text→barcode search cache in Redis

Repeat text searches skipped the product cache because query resolution
always hit OFF first. Cache query→barcode so the second search is instant.
```

**Reglas:**
- No reescribir historia ya compartida (`push --force` sobre ramas compartidas está prohibido).
- No commitear secretos, `.env`, ni artefactos de build. Verificar `.gitignore`.
- No pushear a la nube sin autorización explícita del responsable del repo.
- Ante fallo de una tarea tras 2 iteraciones: rollback según el Protocolo de Reversión del Orquestador.

---

## 4. Documentación

**Comentarios en código:** explican el **porqué**, no el qué. Un comentario que repite lo que el código ya dice es ruido. Los comentarios valiosos documentan decisiones no obvias, invariantes, y trampas ("esto se llama así porque OFF no manda CORS").

**Densidad y estilo:** matchear el archivo circundante. No introducir un estilo de comentario nuevo en un archivo que ya tiene el suyo.

**Docstrings:** funciones públicas de `domain/` y `services/` con un bloque que explique contrato (qué recibe, qué devuelve, qué errores lanza) cuando no es trivial.

**Documentos vivos del proyecto:**
- `DICCIONARIO_DOMINIO.md` — terminología canónica. Todo término nuevo del dominio se agrega acá.
- `BITACORA_DECISIONES.md` — toda decisión de arquitectura relevante se registra como ADR.
- `CONVENCIONES_EQUIPO.md` (este archivo) — reglas de desarrollo.
- Migraciones SQL versionadas en `migrations/NNN_descripcion.sql`, documentando el contexto.

**Idioma de la documentación:** español para docs de proyecto y de negocio; inglés aceptable para docstrings técnicos de código. Consistencia dentro de cada archivo.

---

## 5. Reglas transversales (aplican a todo el código)

- **Sin errores silenciosos.** Prohibido `.catch(() => {})`. Todo error se loguea con contexto y, en backend, se reporta a la observabilidad.
- **Secretos server-only.** Ninguna API key sensible en el cliente. En Expo, solo variables `EXPO_PUBLIC_*` llegan al bundle; el resto es server-side.
- **Fuente de verdad única.** La lógica de negocio (scoring, cuotas, umbrales) vive en el backend. El cliente renderiza, no recalcula.
- **Tests donde hay lógica.** Funciones puras de dominio y servicios se testean. La UI se prueba con el Agente de QA (a11y + flujos).
