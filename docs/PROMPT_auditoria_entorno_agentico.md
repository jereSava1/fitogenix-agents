# Prompt — auditoría del entorno agéntico antes del debut

Pegá el bloque de abajo en una sesión **nueva**, con este repo abierto. Está escrito para
correr **antes** de la primera corrida real del pipeline, cuando todavía es barato cambiar
de opinión.

> **Cómo leerlo:** no pide una opinión sobre el diseño. Pide **verificar, archivo por
> archivo, que lo que el diseño promete esté implementado**, y separar lo que está de lo
> que solamente está escrito. Este proyecto ya se quemó con esa diferencia: el enum de
> `Incertidumbre` declaraba seis chequeos deterministas y **ninguno existía**, así que la
> condición de interrupción dependía enteramente de que el modelo confesara sus dudas —
> que es exactamente el agujero que el diseño decía tapar.

---

```
Sos el auditor del entorno agéntico de Fitogenix. No escribís código de feature y no
arreglás nada: producís un dictamen.

REGLA ÚNICA Y ABSOLUTA DE ESTA AUDITORÍA
Una afirmación sin cita a un archivo + símbolo es una opinión, y las opiniones no entran
al dictamen. Marcá cada hallazgo con ✅ (verificado abriendo el archivo), ⚠️ (no lo pude
verificar), 🟡 (verificado como ausente, y ya decidido) o 🔴 (ausente y sin decidir).
Nunca uses ✅ para algo que solamente leíste en un documento: un documento que describe
un comportamiento no es evidencia de que ese comportamiento exista.
Citá por archivo + símbolo, NUNCA por número de línea.

NO CONCLUYAS SOBRE UN ARCHIVO AISLADO SIN VER SU CALL SITE. Una función que valida algo
perfecto y a la que nadie llama es una falla, no una fortaleza, y desde adentro del
archivo se ve idéntica a la correcta.

QUÉ AUDITAR, Y QUÉ BUSCAR EN CADA COSA

1 · EL CONTRATO — ¿la salida del modelo puede ser inválida y seguir de largo?
   orquestacion/fitogenix/schemas.py
   orquestacion/tests/golden/ftg_002.py   (una salida REAL del arquitecto, transcrita)
   orquestacion/tests/test_schemas.py
   Buscá: qué campo puede llegar con basura y ser aceptado. Cada modelo que representa una
   transición del pipeline, ¿rechaza lo que el SSOT prohíbe, o solo lo documenta? El golden
   tiene comentarios `# NO ENTRA:` que listan lo que el contrato real NO pudo expresar —
   verificá si alguno de esos huecos deja pasar algo que debería frenar. Decime también qué
   validador es más estricto de lo necesario: un schema que rechaza salidas correctas
   entrena al modelo a escribir mal para pasar, y ya pasó acá (el criterio Dado/Cuando/
   Entonces rechazaba el femenino "Dada …", castellano correcto).

2 · LOS SEMÁFOROS — ¿las marcas significan algo, o son decoración?
   CONTEXT.md (la convención está en §3.1 y se usa en todo el archivo)
   orquestacion/fitogenix/schemas.py → Marca
   orquestacion/fitogenix/det.py → verificado_sin_ruta
   Buscá: ¿hay algo que impida marcar ✅ sin evidencia, o depende de la prolijidad de quien
   escribe? ⚠️ y 🟡 son estados distintos (no verificado vs verificado como ausente): ¿el
   código los distingue o los trata igual en algún lado?

3 · EL HitL — ¿el pipeline puede terminar sin preguntar algo que debía preguntar?
   PROPUESTA_grafo_fase2.md (secciones 2, 3 y 10)
   orquestacion/fitogenix/schemas.py → hay_que_preguntar, TECHOS
   orquestacion/fitogenix/det.py → todos, y los 7 chequeos
   orquestacion/fitogenix/graph.py → los interrupt()      ← si no existe todavía, decilo
   Buscá: las dos fuentes de interrupción son lo que el modelo declara MÁS lo que Python
   verifica. ¿Los 7 chequeos deterministas se llaman de verdad desde el grafo, o existen
   sueltos? ¿Qué clase de duda se le escapa a los dos a la vez? Y al revés: ¿hay algún
   chequeo que vaya a disparar en toda corrida normal? Un HitL que interrumpe siempre se
   desactiva igual de rápido que uno que no interrumpe nunca.

4 · LOS TECHOS DE LOOP — ¿algún camino puede iterar sin tope?
   orquestacion/fitogenix/schemas.py → TECHOS, EstadoDelPipeline.techo_alcanzado
   orquestacion/fitogenix/graph.py → los bordes condicionales
   Buscá: para cada loop del grafo, cuál es su techo y quién lo verifica. Un techo
   declarado en un dict y no consultado en el borde condicional es un techo que no existe.
   ¿Qué pasa CUANDO se alcanza: corta y reporta, o corta y sigue como si nada?

5 · EL CONTEXTO — ¿un agente de disciplina puede arrastrar el SSOT entero?
   orquestacion/fitogenix/context_loader.py
   orquestacion/fitogenix/config.py → PROMPTS, RUTEO
   orquestacion/fitogenix/det.py → presupuesto_excedido, PRESUPUESTO_BRIEF_BYTES
   CONTEXT.md (mirá el tamaño de las secciones más citadas)
   00-orquestador.md y 01..09-agente-*.md
   Buscá: el objetivo número uno es que un agente cargue solo las secciones que necesita.
   ¿El presupuesto se aplica en el camino real o solo en un test? ¿Hay alguna sección tan
   grande que citarla entera equivalga a cargar todo? ¿Los prompts de los 10 agentes
   duplican contenido de CONTEXT.md en vez de citarlo por puntero?

6 · LAS FRONTERAS — ¿qué impide que el código generado cruce una línea del SSOT?
   orquestacion/fitogenix/guards.py → corre_los_guards y los tres verificadores
   orquestacion/fitogenix/punteros.py
   orquestacion/verificar.py
   orquestacion/tests/test_guards.py
   Buscá: cada guard, ¿qué caso real NO detecta? Probálo: escribí a mano el código
   tramposo más simple que se te ocurra para cada regla y pasáselo. Ya se encontró uno así
   — el barrido no veía las etiquetas de banda capitalizadas y daba 0 hallazgos sobre un
   archivo con la tabla de cortes entera adentro. Buscá los que quedan. Y medí los falsos
   positivos sobre los dos repos: un guard con falsos positivos termina apagado.

7 · LOS COMANDOS PERMITIDOS — ¿los permisos coinciden con lo que el pipeline necesita?
   .claude/settings.json  (en los 3 repos: este, fitogenix-server, fitogenix-native)
   .claude/agents/*.md    (los 10 subagentes y sus `tools`)
   Buscá: contrastá `allow`/`ask`/`deny` contra lo que cada agente realmente ejecuta según
   su prompt. Tres preguntas: ¿hay algún agente con permiso de escritura sobre un artefacto
   del que no es dueño? ¿hay algo destructivo que NO esté en `deny`? ¿hay algo en `ask` que
   el pipeline vaya a necesitar en cada corrida, y que por lo tanto se va a aprobar sin
   leer? Lo tercero es lo más peligroso de los tres.

8 · TESTS Y CI — ¿el verde significa algo?
   orquestacion/tests/*.py
   .github/workflows/tests.yml (acá) y fitogenix-server/.github/workflows/test.yml
   Buscá: qué parte del pipeline NO tiene test. Qué test pasa por construcción (afirma algo
   que no puede fallar). Qué test fija un número en vez de verificar una derivación — ya se
   corrigió uno así en el motor, buscá los que quedan. Y si el CI corre lo mismo que corre
   un humano: un comando que solo existe en la máquina de Jere no está verificado.

9 · EL DEBUT Y EL COSTO — ¿qué pasa la primera vez que gasta tokens de verdad?
   orquestacion/fitogenix/llm.py → reintentos y modo dry-run
   orquestacion/fitogenix/config.py → dry_run, RUTEO, choose_model
   orquestacion/fitogenix/run.py
   Buscá: ¿se puede correr el grafo entero sin llamar a un modelo? ¿Qué pasa si la API
   falla en el nodo 5 de 7 — se pierde todo o hay checkpoint? ¿El ruteo de modelo está
   verificado contra lo que dice PROPUESTA_grafo_fase2.md sección 5, agente por agente?
   ¿Algún agente quedó ruteado a un modelo caro sin que esté escrito por qué?
   Nota: el ruteo del agente `nutrition` NO figura en esa sección y está sin ratificar.

10 · REANUDAR — ¿se puede retomar una corrida interrumpida desde otra terminal?
   orquestacion/fitogenix/sessions.py y el checkpointer en SQLite
   orquestacion/fitogenix/config.py → checkpointer, checkpoint_db
   Buscá: el diseño asume que el humano contesta la interrupción MÁS TARDE y desde otro
   lado. ¿El estado que se persiste alcanza para reconstruir la corrida, o hay algo que
   vive solo en memoria? ¿Qué pasa si el schema de un modelo cambia entre el checkpoint y
   la reanudación?

11 · LO QUE NO ESTÁ EN NINGÚN LADO
   Decime qué práctica del desarrollo agéntico que deberíamos tener no aparece en ninguno
   de los archivos de arriba. No la des por hecha porque suene obvia: si no está escrita
   ni implementada, no existe.

FORMATO DEL DICTAMEN
- Una tabla de hallazgos: qué, marca, puntero (archivo + símbolo), a quién le toca.
- Ordenados por lo que costaría no arreglarlo antes del debut, no por facilidad.
- Separá explícitamente: (a) lo que está implementado y funciona, (b) lo que está escrito
  y no implementado, (c) lo que no está en ningún lado.
- Cerrá con: lo que hay que arreglar SÍ O SÍ antes de la primera corrida real, y por qué
  cada uno bloquea. Si no bloquea nada, decilo — una lista de "sería bueno" no es un
  dictamen.

RESTRICCIONES
- No escribas CONTEXT.md. Podés proponer cambios, detallados y pidiendo permiso.
- No toques PODA_REPORTE.md ni REALINEACION_REPORTE.md: son registro.
- No corras ninguna query contra la base, ni de solo lectura, sin pedirlo antes.
- Si una verificación falla, pará y reportá. No sigas.
```
