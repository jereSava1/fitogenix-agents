# Dictamen — auditoría del entorno agéntico antes del debut

**Fecha:** 2026-09-19 · **Repo:** `fitogenix-agents` @ `7386d69` (`feat/fase3-contratos`, árbol limpio)
**Alcance real:** este repo completo. `fitogenix-server` y `fitogenix-native` **no están en la carpeta conectada** → todo lo que depende de ellos va ⚠️.
**Método:** lectura de cada archivo citado + ejecución. Suite: `181 passed` (local y en sandbox). Además corrí el grafo con un doble de `llama_estructurado` que simula **modo real** (`dry_run=False`), el CLI en dry-run contra un SQLite temporal, y payloads tramposos contra los guards. Nada tocó la base.

> **Veredicto en una línea:** el pipeline **no está listo para una corrida real completa**. El dry-run cierra en verde porque los stubs tapan exactamente los caminos que están rotos: en modo real, `n1a` no recibe el schema ni el SSOT, `n3`/`n4` siguen siendo stubs, el techo de revisión no se aplica y las respuestas del HitL 2 no llegan a ningún lado.

Marcas: ✅ verificado abriendo/corriendo · ⚠️ no lo pude verificar · 🟡 ausente y ya decidido · 🔴 ausente y sin decidir.

---

## 1 · Hallazgos, ordenados por costo de no arreglarlos

| # | Qué | Marca | Puntero | Evidencia | A quién |
|---|---|---|---|---|---|
| **H1** | **El modelo nunca recibe el schema de salida.** No hay `model_json_schema`, ni tool use, ni structured output; `00-orquestador.md` y `04-agente-qa.md` no nombran `AnalisisDeRequerimiento` / `ReporteDeRevision`. La primera llamada real (Opus, `n1a`) va a fallar la validación casi seguro. | 🔴 | `llm.py → llama_estructurado` · `graph.py → _sistema` | grep sin resultados sobre `orquestacion/` y los prompts | orq/ |
| **H2** | **Un `ValidationError` mata la corrida.** El docstring dice "esa decisión es del grafo"; el grafo no la toma: no hay reintento con el error ni try/except. Sin `n6`, sin handoff, y **no aparece en `--list`**. | 🔴 (escrito, no implementado) | `llm.py → llama_estructurado` · `run.py → main` | sin `except` alrededor de `app.invoke` | orq/ |
| **H3** | **`n3_implementar` es un stub también en modo real.** Le pide un `Reporte` (no `CodigoGenerado`), descarta lo que devuelve (`_, _r`), mete un `Respuesta` que el filtro `hasattr(r,"estado")` después tira, y **siempre** agrega `STUB_ENTREGA`. | 🔴 | `graph.py → n3_implementar` | harness en modo real: `entregas = ['// [dry-run] sin contenido']`, `reportes = []` | orq/ |
| **H4** | **`n4` siempre arma `stub_paquete`** (título `[dry-run] FTG-…` en modo real) y **`n5` revisa contrato + paquete, nunca código.** QA aprueba algo que no vio. | 🔴 | `graph.py → n4_empaquetar_pr`, `n5_revisar` | harness: el prompt del revisor no contiene ningún `contenido` | orq/ |
| **H5** | **Un stub puede cerrar una corrida real.** `Respuesta.exigir_real()` / `EsUnStub` no tienen call site. Juntando H3+H4: una corrida real termina `cerrada · aprobado` con cero código. | 🔴 (escrito, no implementado) | `llm.py → Respuesta.exigir_real` | grep: solo aparece en `test_llm.py` | orq/ |
| **H6** | **El techo de revisión no existe en el camino real.** `rutea_revision` compara `rev.ronda` —que declara el modelo, y que el prompt no le informa— y `n5_revisar` solo la pisa en el stub. | 🔴 | `schemas.py → rutea_revision` · `graph.py → n5_revisar` | harness: QA rechaza con `mayor` → **8 llamadas a Opus** y `GraphRecursionError`, techo declarado 2, sin `n6` | orq/ |
| **H7** | **El camino `n5 → recontratar` saltea el techo de contrato.** `rutea_contrato` no mira `ronda_contrato`; solo `rutea_post_contrato` lo hace, y solo si hubo interrupt. | 🔴 | `graph.py → rutea_contrato` | harness: `ronda_contrato = 6` con techo 1 | orq/ |
| **H8** | **Las respuestas del HitL 2 se tiran.** Se guardan como `RespuestaHumana` pero el contrato no se regenera (con techo 1, `recontratar` es inalcanzable desde `n2b`) y `n3` no las recibe. | 🔴 | `graph.py → n2b_aclarar_contrato`, `rutea_post_contrato`, `n3_implementar` | harness: la respuesta `XYZZY-umbral-75` no aparece en ningún prompt posterior; el contrato sigue con `supuestos=['asumo que el umbral es 70']` | orq/ + Jere (decisión) |
| **H9** | **El HitL 2 se aprueba solo.** `--accion` tiene default `contratar`, el handoff sugiere literalmente `python run.py --resume FTG-XXX`, y `aprobacion_valida` en `n2b` cruza contra el **análisis** (ya limpio), no contra el contrato. Retomar sin argumentos = aprobar supuestos sin contestarlos. | 🔴 | `run.py → main` (`--accion`) · `sessions.py → Handoff.a_markdown` · `graph.py → _absorbe_respuesta` | CLI dry-run: dos `--resume FTG-900` pelados → `corrida cerrada` | orq/ |
| **H10** | **`n1a` no recibe `CONTEXT.md`.** `PROPUESTA_grafo_fase2.md` sección 1 dice que es "el único que lee CONTEXT.md entero"; el prompt de usuario es solo ticket + respuestas. `contexto_completo()` no tiene call site en el grafo. Todos los punteros aguas abajo salen de la memoria del modelo. | 🔴 (escrito, no implementado) | `graph.py → n1a_analizar` · `context_loader.py → contexto_completo` | harness: ningún prompt del orquestador contiene `## §` | orq/ |
| **H11** | **El escalado a Opus nunca se activa.** `n2_contrato` usa `hasattr(a, "toca_scoring")` sobre un `AnalisisDeRequerimiento`, que no tiene ese campo → siempre `False`. `escala_a_opus` y los cuatro `escalar_*` no tienen call site. FTG-002 toca el motor e iría a Sonnet, contra §5. | 🔴 | `graph.py → n2_contrato` · `config.py → escalar_*` · `schemas.py → ContratoAprobado.escala_a_opus` | harness: contrato con `toca_scoring=True` → architect llamado con `escalado=False` | orq/ |
| **H12** | **El chequeo 6 (`frontera_violada`) no corre nunca en el grafo.** `_dudas` llama `det.todos(contrato)` sin `archivos`. Los guards solo corren dentro de `CodigoGenerado`, que solo ve stubs (H3). | 🔴 | `graph.py → _dudas` · `det.py → todos` | lectura | orq/ |
| **H13** | **`bloqueante_abierto` depende de que haya un 🔴 en el cuerpo.** Solo 5 de los 13 bloqueantes abiertos de `§8` lo tienen. **B-6 (migraciones, del propio arquitecto) va ⚠️ y B-12 va 🟡 → no disparan.** El intro de `§8` ya define la regla correcta: todo lo que no es `§8.0` está abierto. | 🔴 | `det.py → bloqueante_abierto` · `CONTEXT.md §8` | escaneo de `§8.2`…`§8.21` | orq/ |
| **H14** | **Una regla ⚠️ no cuenta como duda.** `verificado_sin_ruta` solo mira ✅. Un contrato con todas las reglas en ⚠️ y `supuestos=[]` avanza sin interrupción: es la duda que se les escapa **a las dos fuentes a la vez**. | 🔴 | `det.py → verificado_sin_ruta` · `schemas.py → hay_que_preguntar` | lectura | orq/ + Jere |
| **H15** | **"El arquitecto dijo `partial`" no se puede expresar.** Golden `# NO ENTRA (2/4)`. Un contrato que el propio autor declara incompleto sigue de largo si no llenó `supuestos`. | 🔴 | `schemas.py → ContratoAprobado` · `tests/golden/ftg_002.py` | comentario del golden | orq/ |
| **H16** | **`puntero_sin_archivo` falla abierto.** Si el repo hermano no está, `continue` en silencio. `verificar.py` hace lo mismo: imprime ⚠️ y sale **`✅ todo en verde`, exit 0** — el "arreglo" del 18/9 solo corrige dónde se busca, no qué pasa si no se encuentra. En tu máquina: ⚠️ no sé si `_busca_repo` los encuentra (no están en la carpeta conectada). | 🔴 | `det.py → puntero_sin_archivo` · `verificar.py → main` · `config.py → _busca_repo` | `verificar.py` corrido acá: exit 0 con 3 de 4 chequeos salteados | orq/ |
| **H17** | **✅ sin evidencia real pasa.** `Reporte` acepta ✅ con `verificada_en_sesion=False`, y `tiene_ruta_de_archivo` matchea `"versión 2.10"`. Además, **en el pipeline por API ningún agente tiene tools**: todo ✅ que emita un modelo es, por construcción, "lo cité", nunca "lo abrí". | 🔴 | `schemas.py → Reporte._reglas_de_cierre`, `Evidencia.tiene_ruta_de_archivo` | probado: ambos aceptan | orq/ |
| **H18** | **Un fallo o un cambio de schema deja la corrida huérfana.** `cierra_handoff` se llama **antes** de `app.invoke`. Si el resume falla (p. ej. porque cambiaste un schema — que va a pasar después del debut, ver `# NO ENTRA`), el `.md` ya se borró y `--list` dice que no hay nada esperando. | 🔴 | `run.py → main` · `sessions.py → cierra_handoff` | probado: saco un campo del schema → `AttributeError` al reanudar, `--list` vacío | orq/ |
| **H19** | **Mismo ticket = mismo thread, para siempre.** Correr FTG-002 dos veces reusa el estado; los reducers `_concat` arrastran `respuestas_humanas` viejas al prompt nuevo y acumulan `incertidumbres` (una vieja fuerza HitL 2 en la corrida nueva). | 🔴 | `sessions.py → thread_id` · `schemas.py → EstadoDelPipeline` (`_concat`) | CLI: re-correr FTG-900 mostró el log de la corrida anterior | orq/ |
| **H20** | **Guards: 13 de 13 payloads tramposos pasaron.** Supabase directo desde el cliente (`SERVICIOS_PROHIBIDOS_EN_CLIENTE` no lo incluye), Anthropic por `fetch` a la URL, OFF por constante, cortes con etiquetas en inglés / con colores / en array, copia de `constants.ts` **en el cliente** (la excepción es por `endswith`), ruta sin prefijo de repo, endpoint nuevo **en un archivo de rutas existente** (el caso normal), endpoint anidado o con guion. | 🔴 | `guards.py → verifica_frontera_cliente`, `verifica_umbrales_no_transcriptos`, `verifica_ruta_con_contrato`, `_es_cliente` | script de payloads | orq/ + backend (dueño de §3.1) |
| **H21** | **Guards: falsos positivos triviales.** `'Bueno para 18-25 años'` y `if (items.length > 3 && page < 2) setMsg('Malo…')` disparan: "bueno"/"malo" son palabras comunes y el regex es case-insensitive. Sobre los repos reales: ⚠️ no medible desde acá. | ⚠️ | `guards.py → _ETIQUETA_DE_BANDA` | script | orq/ |
| **H22** | **`PaquetePR` deja pasar comandos destructivos**: `git push origin HEAD --force`, `git reset --hard HEAD~3`, `git clean -fdx`, `git branch -D main`. Es substring sobre 4 frases. | 🔴 | `schemas.py → _COMANDOS_PROHIBIDOS` | probado | orq/ |
| **H23** | **Dominios exclusivos (§7) solo por prompt.** `CodigoGenerado` frena a 3 agentes y nada más: `mobile` puede escribir `fitogenix-server/…`; `ArchivoGenerado.ruta` no se valida (`../`, `.github/workflows/`); `toca_dominio` es autodeclarado. | 🔴 | `schemas.py → CodigoGenerado._reglas`, `ArchivoGenerado` | lectura | orq/ + architect |
| **H24** | **Techo de gasto mal medido.** Cuenta solo tokens de **salida**; la entrada (lo caro, lo que el cargador existe para ahorrar) no tiene tope. El `Contador` no se persiste: cada `--resume` arranca en cero. `MAX_TOKENS=8000` no alcanza para un `CodigoGenerado` con archivos enteros, y `stop_reason` no se chequea (JSON truncado → H2). | 🔴 | `llm.py → Contador`, `TECHO_DE_TOKENS_POR_CORRIDA`, `MAX_TOKENS` | lectura | orq/ |
| **H25** | **Timeouts y caídas de red no se reintentan.** `anthropic.APIConnectionError` / `APITimeoutError` no heredan de `ConnectionError` ni traen `status_code`. | 🔴 | `llm.py → _es_transitorio` | probado con anthropic 1.7.0: `False` / `False` | orq/ |
| **H26** | **El HitL 1 esconde cosas al humano.** El payload no lleva `bloqueantes_tocados`, `resumen` ni `nota_de_incertidumbre`; el handoff `.md` no muestra `contradicciones`, así que un OK queda "sin efecto" y el loop gira hasta el techo sin que sepas por qué. `listo_para_contratar` y `bloqueantes_tocados` no tienen call site. | 🔴 | `graph.py → n1b_aclarar` · `sessions.py → Handoff` · `schemas.py → AnalisisDeRequerimiento` | lectura | orq/ |
| **H27** | **CI: el paso "Punteros §X sin colgar" está en rojo** sobre este árbol (`CHANGELOG.md` cita las secciones 4.5 y 4.7 de la rúbrica del motor). `verificar.py` los exceptúa (regex `ajeno`), el script inline no: dos chequeos del mismo invariante no coinciden. Nadie lo vio porque la rama **no tiene upstream**: el CI nunca corrió sobre estos 28 commits. | 🔴 | `.github/workflows/tests.yml` · `verificar.py → punteros_de_documentos` | corrí el script inline tal cual | orq/ |
| **H28** | **Rama con diff muy ancho.** `feat/fase3-contratos`: 28 commits, 62 archivos, +7.195 líneas sobre `main`, sin push. | ⚠️ riesgo | git | `git diff --stat main...HEAD` | Jere |
| **H29** | **Tests verdes que no pueden fallar:** `test_un_puntero_a_codigo_real_no_dispara` (vacuo sin el repo, que es el caso de CI), `test_un_stub_no_puede_cerrar_una_corrida` (guard sin call site), `test_escala_a_opus_porque_toca_el_motor` (property muerta), `test_contexto_completo_sigue_disponible_para_el_orquestador` (el orquestador no lo recibe), `test_en_el_techo_de_revision_escala` (le pasa la `ronda` a mano; en el grafo la pone el modelo). | 🔴 | `tests/test_det.py`, `test_llm.py`, `test_golden_ftg002.py`, `test_context_loader.py`, `test_graph.py` | lectura + corrida | orq/ |
| **H30** | **El golden derivó y ningún test lo nota**: cita la sección 8.7 de `CONTEXT.md`, que ya no existe → `seccion_inexistente` da 2 hallazgos hoy. Ningún test afirma los 7 chequeos sobre el golden. | 🔴 | `tests/golden/ftg_002.py` · `test_golden_ftg002.py` | corrí `det.*` sobre el golden | orq/ |
| **H31** | **Permisos:** el pipeline por API **no pasa por `.claude/settings.json`** —ese archivo gobierna sesiones de Claude Code—. Cuando `n3`/`n4` escriban de verdad, el único control es H22. Dentro de Claude Code: `allow: Bash(git branch:*)` habilita `git branch -D` sin preguntar; `architect`, `qa` y `nutrition` tienen `Bash` (pueden escribir con shell aunque "no escriben código"); `ux` tiene `Write`/`Edit` aunque "no implementa"; `orchestrator` no tiene `Write`. `ask: Bash(git push:*)` se va a pedir en cada PR: se aprueba sin leer. | 🔴 | `.claude/settings.json` · `.claude/agents/*.md` (`tools`) | lectura | Jere + devops |
| **H32** | **`CONTEXT.md §7` afirma ✅ que el arquitecto está "sin permisos de escritura de código"**; su frontmatter le da `Bash`. Es un ✅ que depende del modo de permisos, no del archivo. | 🔴 | `CONTEXT.md §7` · `.claude/agents/architect.md` | lectura | orchestrator (propuesta abajo) |
| **H33** | **`claude-sonnet-5` no está verificado como ID.** Un 404 no es transitorio: la primera llamada a un agente Sonnet muere. | ⚠️ | `config.py → MODELO_BASE` | no se puede sin llamar a la API | Jere |
| **H34** | **`orquestacion/` no tiene dueño en `§7`**, y `PROPUESTA_grafo_fase2.md` —el diseño que el código cita en cada docstring— vive **fuera del repo** (carpeta padre): no está versionado y el CI no lo ve. | 🔴 | `CONTEXT.md §7` · `config.py`, `graph.py` (docstrings) | ubicación del archivo | Jere |
| **H35** | `pyproject.toml` declara solo `pydantic`; `requirements.txt` trae `langgraph` y `anthropic`. `pip install .` da un paquete roto. | 🔴 menor | `orquestacion/pyproject.toml` | lectura | orq/ |

**Más estricto de lo necesario (entrena al modelo a escribir mal):** `ContratoAprobado.ronda le=1` y `AnalisisDeRequerimiento.ronda le=3` convierten un número de más en crash en vez de ruteo; `ArchivoGenerado.lenguaje` rechaza `.js` (p. ej. `babel.config.js` de native); `_P_CODIGO` no deja citar `orquestacion/…` (por eso el arquitecto no pudo verificar `guards.py`); `Reporte.que_hice max 3` y `CodigoGenerado.notas max 5` recortan información en vez de ordenarla.

---

## 2 · Separación pedida

### (a) Implementado y funciona — ✅ verificado

| Qué | Puntero |
|---|---|
| Validadores de contrato: Brief con Dado/Cuando/Entonces (con concordancia), ticket, arquitecto/nutrition sin PR; `done` exige evidencia; tres puntas + espejo en dos repos; ADR ante cambio de esquema | `schemas.py → Brief`, `Reporte`, `ContratoAprobado._reglas` |
| Ruteo de revisión veredicto-primero (rechazado con solo `menor` no avanza) | `schemas.py → rutea_revision` |
| HitL 1 incondicional; un OK con preguntas abiertas queda "sin efecto" | `graph.py → n1b_aclarar`, `_absorbe_respuesta` · CLI dry-run |
| Techo de aclaración consultado en el borde | `graph.py → rutea_aclaracion` |
| 6 de los 7 chequeos deterministas se llaman desde el grafo (nodo `chequeos`) | `graph.py → marca_incertidumbres` |
| Dry-run de punta a punta sin API key | `run.py --dry-run` → `corrida cerrada` |
| Checkpoint por superstep: si la API falla en `n5`, `--resume` reejecuta solo `n5` | harness con `SqliteSaver` |
| Serializador con los schemas declarados (0 avisos con SQLite) | `sessions.py → _serde` |
| `RUTEO` coincide fila por fila con `PROPUESTA_grafo_fase2.md` sección 5; `choose_model` sin default silencioso | `config.py → RUTEO`, `choose_model` |
| Cargador por sección: 55 secciones, sin duplicados, sin headings sin `§`; la más grande (`§1.6`, 7,9 KB) es el 13 % del SSOT | `context_loader.py → _indice` |
| Los 10 prompts no copian frases de `CONTEXT.md` (0 frases ≥70 caracteres en común; paráfrasis ⚠️ no medida) | `0*-agente-*.md` |
| Guards: los casos base de los tres (ternario con etiquetas en español, import del SDK, ruta nueva sin Schema) disparan | `guards.py` |

### (b) Escrito y no implementado

H2 (reintento por validación), H5 (`exigir_real`), H10 (`n1a` lee el SSOT), H11 (escalado), H12 (chequeo 6 en el grafo), H6/H7 (techos en el camino real), H8 (HitL 2 "te muestra las preguntas" → y las usa), `§7` dominios exclusivos (H23), `listo_para_contratar` / `bloqueantes_tocados` (H26), `CONTEXT.md §7` sobre permisos del arquitecto (H32).

### (c) En ningún lado

| Práctica | Por qué importa acá |
|---|---|
| **Salida estructurada** (tool use / JSON schema en la llamada) + **reintento con el error de validación** | Es H1+H2: sin esto no hay debut |
| **Log crudo de cada llamada** (prompt, respuesta, modelo, hash del prompt, tokens) | Si la validación falla, hoy se pierde el texto que ya pagaste y no hay cómo depurar |
| **Versión de prompt y de schema en el estado** | Sin eso no sabés qué prompt produjo qué contrato, ni si un checkpoint es compatible (H18) |
| **Ejecutar lo generado antes de QA** (worktree, `tsc`, tests) | Hoy "evidencia" es texto; ningún agente corre nada |
| **Evals más allá de un golden**: goldens para `AnalisisDeRequerimiento`, `Reporte` y `ReporteDeRevision`, y replay de salidas reales | Hay uno solo, del contrato, y ya derivó (H30) |
| **Prompt caching** (`cache_control`) | Los system prompts pesan 9–26 KB y se reenvían enteros en cada llamada |
| **Run ID separado del ticket** y **lock** contra dos `--resume` simultáneos | H19 |
| **Defensa contra prompt injection** desde el ticket o desde contenido del repo, y escaneo de secretos en lo generado | El ticket entra crudo a Opus |
| **Tope en plata**, no en tokens de salida | H24 |

---

## 3 · Qué hay que arreglar SÍ O SÍ antes de la primera corrida real

**Mi recomendación como CTO: que el debut sea solo de contrato** (`n1a → n1b → n2 → chequeos → n2b` y cortar ahí, con un `--hasta contrato`). Es el tramo que está casi listo, prueba lo que más importa (si el modelo escribe contratos que validan y si el HitL 2 dispara cuando debe), y `n3`/`n4`/`n5` no están implementados de verdad: correrlos solo gasta Opus para revisar un stub.

### Bloquean el debut de contrato

| P | Qué | Por qué bloquea |
|---|---|---|
| **P0-1** | Pasar el schema en la llamada (tool use con `input_schema = Model.model_json_schema()`) + un reintento con el `ValidationError` en el prompt + guardar la respuesta cruda — H1, H2 | Sin esto la primera llamada (Opus) falla, la corrida muere sin `n6` y el texto pagado se pierde |
| **P0-2** | `n1a` recibe `contexto_completo()` — H10 | Todos los punteros del contrato salen de acá; sin SSOT son inventados y el debut mide alucinación, no el pipeline |
| **P0-3** | Sacar el default `--accion contratar`; `--resume` sin `--accion` explícita tiene que fallar. En `n2b`, un OK no cuenta mientras el contrato tenga supuestos o decisiones sin respuesta — H9 | Hoy el HitL 2 se aprueba solo siguiendo la instrucción del propio handoff |
| **P0-4** | Las respuestas del HitL 2 vuelven a `n2_contrato` (una ronda extra *con* respuesta humana no es "el pipeline discutiendo consigo mismo") — H8. **Es decisión tuya**: cambia el techo de contrato de `PROPUESTA_grafo_fase2.md` sección 3 | Si no, preguntarte no cambia nada: contestás y se implementa el supuesto viejo |
| **P0-5** | `bloqueante_abierto`: todo `§8.n` con n≠0 está abierto — H13. Y que una regla ⚠️ cuente como duda — H14 | FTG-002 roza B-6 y B-12, justo los dos que hoy no disparan; es la clase de duda que ninguna de las dos fuentes ve |
| **P0-6** | `puntero_sin_archivo` y `verificar.py` fallan **cerrado** si no encuentran los repos (o exigen `FITOGENIX_*_PATH`) — H16 | Si en tu máquina no los encuentra, el chequeo 2 está apagado y nadie se entera |
| **P0-7** | Arreglar `hasattr(a, "toca_scoring")` → que el escalado salga del análisis — H11 | FTG-002 toca el motor; por la sección 5 el arquitecto va a Opus. Sin esto el debut mide a Sonnet |
| **P0-8** | Una llamada de humo por cada ID de `RUTEO` — H33 | Un 404 no se reintenta: rompe en el nodo que toque |

### Bloquean además una corrida completa (no hacen falta si el debut es de contrato)

| P | Qué | Por qué bloquea |
|---|---|---|
| **P1-1** | `n3` real (`CodigoGenerado`), `n4` con los archivos reales, `n5` recibiendo el código, `exigir_real()` en `n6` — H3, H4, H5 | Hoy una corrida real cierra "aprobada" sin código |
| **P1-2** | `n5` pisa `revision.ronda` con `estado.ronda_revision`; `rutea_contrato` consulta `ronda_contrato` — H6, H7 | Sin esto el único techo es el `recursion_limit` de LangGraph: 8 llamadas a Opus y crash sin resumen |
| **P1-3** | `det.frontera_violada` sobre las entregas después de `n3` — H12 | Es el guard que justifica todo `guards.py` |
| **P1-4** | `ArchivoGenerado.ruta` validada contra el dueño del Brief y contra `../` / `.github/`; `_COMANDOS_PROHIBIDOS` por parseo y no por substring — H22, H23 | Es lo único entre el modelo y tu disco/git: `settings.json` no aplica al pipeline (H31) |
| **P1-5** | `stop_reason == "max_tokens"` → error explícito; techo sobre tokens de entrada; `Contador` en el estado — H24 | JSON truncado en `n3` y gasto sin tope real |

### Mayores, que no bloquean el debut

`cierra_handoff` después del invoke exitoso (H18) · run ID por corrida (H19) · reintentar `APIConnectionError`/`APITimeoutError` (H25) · mostrar contradicciones y bloqueantes en el handoff (H26) · alinear los dos chequeos de punteros y **pushear la rama para que el CI corra** (H27, H28) · reescribir los 5 tests vacuos (H29) · afirmar los 7 chequeos sobre el golden y actualizar la cita a la 8.7 (H30) · `Supabase` en `SERVICIOS_PROHIBIDOS_EN_CLIENTE` y endpoint nuevo por diff de `router.<verbo>(` (H20) · `git branch` fuera de `allow` (H31) · mover `PROPUESTA_grafo_fase2.md` al repo y darle dueño a `orquestacion/` en `§7` (H34).

---

## 4 · Propuestas sobre `CONTEXT.md` (no escritas — piden permiso)

| Sección | Hoy dice | Diría | Por qué |
|---|---|---|---|
| `§7`, párrafo del arquitecto | "…registrado como subagente… **sin permisos de escritura de código**" con ✅ | "…con `tools: Read, Grep, Glob, Bash`. No escribe código **por contrato de prompt**; `Bash` le permite escribir, así que el control real es el modo de permisos ⚠️" | Es un ✅ que no resiste abrir `.claude/agents/architect.md` (H32) |
| `§7`, tabla de dueños | `orquestacion/` no figura | Agregar dueño de `orquestacion/` (propongo orchestrator para el diseño, devops para CI) | H34: hoy nadie es dueño del pipeline que decide quién es dueño de qué |
| `§8`, intro | "Cada bloqueante abierto es su propia subsección" | Agregar: "**Estar en `§8.n` con n≠0 es estar abierto**, sin importar la marca del cuerpo; la marca describe el avance, no el estado" | Hace explícita la regla que `det.bloqueante_abierto` necesita (H13) |

---

**Nota operativa:** mi primer `git status` dejó un `.git/index.lock` huérfano (esta sesión no tenía permiso de borrado). Ya lo borré con tu permiso; el árbol quedó limpio en `feat/fase3-contratos`. No toqué `CONTEXT.md`, `PODA_REPORTE.md` ni `REALINEACION_REPORTE.md`, no corrí nada contra la base, y los checkpoints de prueba fueron a `/tmp`, no a `.fitogenix/`.
