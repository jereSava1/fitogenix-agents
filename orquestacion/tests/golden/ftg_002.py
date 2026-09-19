# -*- coding: utf-8 -*-
"""Golden #1 — el primer contrato **real** que produjo el arquitecto, contra FTG-002.

No es un fixture inventado para que los schemas pasen. Es la transcripción de la salida
de un subagente que trabajó sobre el árbol real el 2026-09-18 y al que se le prohibió
explícitamente leer `orquestacion/`: mirar el validador antes de escribir el contrato
habría sido escribir *para* el validador, y el test no habría probado nada.

Lo que este archivo fija es el contrato **tal como se pudo expresar**. Lo que NO entró
está anotado abajo con `# NO ENTRA:` y es la lista de trabajo de los schemas, no del
arquitecto.

Arrancó con seis. El 2026-09-18 se cerraron las dos que más dolían —`punteros` pasó a
plural y las puntas del contrato dejaron de ser una lista fija de tres— y quedan cuatro.
"""
from fitogenix.schemas import (
    Brief, CampoDelContrato, ContratoAprobado, Disciplina, Entregable, Marca,
    PuntaDelContrato, PunteroDeContexto, ReglaDeValidacion,
)

P = PunteroDeContexto
CONST = "fitogenix-server/src/domain/product/scoring/constants.ts"
PRES = "fitogenix-server/src/domain/product/scoring/presentation.ts"

# Los punteros van en plural desde el 2026-09-18, y esta es la razón: el arquitecto dio
# DOS por regla —la sección de `CONTEXT.md` que manda y el archivo donde lo verificó—
# porque son dos cosas distintas. Con el campo en singular había que tirar uno, y
# `det.verificado_sin_ruta` levantaba 5 hallazgos de los que 4 eran del schema.
REGLAS = [
    ReglaDeValidacion(enunciado="ningún umbral, color ni mensaje de banda se escribe a mano en la ruta, el schema ni el cliente: todo sale de TIERS / NO_DATA_TIER", punteros=["CONTEXT.md §3.1", f"{CONST} → TIERS, NO_DATA_TIER, EXCELLENT_FROM, BAD_BELOW"], marca=Marca.VERIFICADO),
    ReglaDeValidacion(enunciado="label, color, tagline y fito se derivan con las mismas funciones que derivan la presentación de un producto", punteros=[f"{PRES} → getScoreLabel, getScoreTagline, getSello, resolveProductStatus"], marca=Marca.VERIFICADO),
    ReglaDeValidacion(enunciado="el mapeo estado→fito deja de estar duplicado: se extrae al motor y el servicio de lookup pasa a llamarlo", punteros=["fitogenix-server/src/services/productLookupService.ts → scorePresentation"], marca=Marca.VERIFICADO),
    ReglaDeValidacion(enunciado="max se deriva del tope de la escala y del min de la banda siguiente; no se escribe 100 en la ruta", punteros=["fitogenix-server/src/domain/product/scoring/ledger.ts → MIN_SCORE, MAX_SCORE"], marca=Marca.VERIFICADO),
    ReglaDeValidacion(enunciado="el schema de respuesta queda atado a los tipos en compilación, con el mismo mecanismo satisfies del contrato existente", punteros=["fitogenix-server/src/routes/products/lookupSchema.ts → productProperties"], marca=Marca.VERIFICADO),
    ReglaDeValidacion(enunciado="endpoint nuevo entra al contrato de API en el mismo commit: el *Schema.ts hermano y la entrada del documento", punteros=["CONTEXT.md §5.6"], marca=Marca.SIN_CONTRASTAR),
    ReglaDeValidacion(enunciado="invariante del sello por banda: el sello de min y el de max coinciden para toda banda con puntaje, o el build rompe", punteros=["fitogenix-server/src/domain/product/scoring/invariants.test.ts", "CONTEXT.md §8.7"], marca=Marca.DECIDIDO_NO_IMPLEMENTADO),
    ReglaDeValidacion(enunciado="ningún test del contrato afirma un umbral literal: se afirma derivación, nunca el número", punteros=["CONTEXT.md §3.1", "fitogenix-server/src/domain/product/scoring/presentation.test.ts"], marca=Marca.VERIFICADO),
    # La única regla del contrato real que `det.verificado_sin_ruta` levanta con razón:
    # el arquitecto la marcó ✅ y sus dos punteros son secciones. No hay archivo que abrir.
    ReglaDeValidacion(enunciado="el cliente no ordena, no completa ni deduce filas: renderiza el array en el orden que llega", punteros=["CONTEXT.md §5.2", "CONTEXT.md §3.4"], marca=Marca.VERIFICADO),
    ReglaDeValidacion(enunciado="el cliente cachea la tabla por engineVersion y trata como MISS toda entrada de otra versión", punteros=["CONTEXT.md §5.4", "fitogenix-server/src/services/redisService.ts → setInRedis, unwrapCachedProduct"], marca=Marca.VERIFICADO),
    ReglaDeValidacion(enunciado="el contrato no toca la columna denormalizada de puntaje ni ningún camino de lectura que la sirva", punteros=["fitogenix-server/src/services/cacheService.ts", "CONTEXT.md §5.4", "CONTEXT.md §8.19"], marca=Marca.VERIFICADO),
    ReglaDeValidacion(enunciado="cero migraciones: no hay cambio de esquema y la numeración de migrations/ no se toca", punteros=["fitogenix-server/migrations/", "CONTEXT.md §8.6"], marca=Marca.VERIFICADO),
]

# NO ENTRA (1/4): el arquitecto dio DOS criterios Dado/Cuando/Entonces para `min`/`max` y
# para `tagline` (el caso normal y el de la banda sin datos). `CampoDelContrato` admite
# uno, así que van concatenados y el segundo deja de ser verificable por separado.
CAMPOS = [
    CampoDelContrato(nombre="engineVersion", tipo="string", criterio_de_aceptacion="Dado un cliente que ya tiene la tabla cacheada de una versión anterior del motor Cuando pide GET /scoring/bands y el engineVersion que llega no coincide con el guardado Entonces descarta la copia local y usa la nueva, sin mezclar filas de las dos"),
    CampoDelContrato(nombre="bands", tipo="ScoreBand[]", criterio_de_aceptacion="Dado GET /scoring/bands con el motor vigente Cuando se compara la cantidad de filas contra TIERS Entonces hay una fila por cada banda con puntaje más una por la banda sin datos, ordenadas de mayor a menor, con la de sin datos al final, y el cliente las renderiza en ese orden sin reordenarlas"),
    CampoDelContrato(nombre="bands[].key", tipo="string", criterio_de_aceptacion="Dada una banda cualquiera Cuando el cliente busca su párrafo explicativo propio por esa clave Entonces lo encuentra; y si la clave no existe en su copy, renderiza la banda sin ese párrafo en vez de omitir la banda o romper"),
    CampoDelContrato(nombre="bands[].min", tipo="number | null", criterio_de_aceptacion="Dada la respuesta del endpoint Cuando se comparan min y max contra TIERS y contra las cotas de escala del motor Entonces cada min es el min de su banda y ningún literal numérico aparece en la ruta, en el schema ni en el test; y Dada la banda sin datos Cuando se leen min y max Entonces los dos son null, nunca 0, porque 0 se leería como el peor producto posible"),
    CampoDelContrato(nombre="bands[].max", tipo="number | null", criterio_de_aceptacion="Dada la respuesta del endpoint Cuando se compara max contra el min de la banda siguiente Entonces cada max es ese min menos uno y el max de la banda más alta es el tope de la escala del motor"),
    CampoDelContrato(nombre="bands[].label", tipo="string", criterio_de_aceptacion="Dado un puntaje cualquiera dentro de una banda Cuando se compara el label de esa banda con el scoreLabel que /products/lookup devuelve para un producto con ese puntaje Entonces son idénticos, carácter por carácter, incluida la caja"),
    CampoDelContrato(nombre="bands[].color", tipo="string", criterio_de_aceptacion="Dado un puntaje cualquiera dentro de una banda Cuando se compara el color de esa banda con el scoreColor del mismo producto Entonces son idénticos, y ningún color de banda está escrito en fitogenix-native/src/"),
    CampoDelContrato(nombre="bands[].tagline", tipo="string", criterio_de_aceptacion="Dado un puntaje cualquiera dentro de una banda Cuando se compara el tagline de esa banda con el tagline del mismo producto Entonces son idénticos; y Dada la banda sin datos Cuando se lee su tagline Entonces es el mensaje que el motor da para un producto sin puntaje, no un texto escrito en la Guía"),
    CampoDelContrato(nombre="bands[].fito", tipo="'fito' | 'nofito' | 'none'", criterio_de_aceptacion="Dado cualquier puntaje dentro de una banda Cuando se compara el fito de la banda con el fito que el contrato de producto devuelve para ese puntaje Entonces coinciden para TODO puntaje de la banda, no solo para su extremo"),
]

# Las tres puntas del contrato de producto, más las tres del contrato NUEVO. El
# arquitecto declaró que este contrato agranda el conjunto de 3 a 5 archivos; hasta el
# 2026-09-18 eso no se podía registrar y el objeto quedaba afirmando la verdad vieja.
PUNTAS = [
    PuntaDelContrato(archivo="fitogenix-server/src/types/fitogenix.ts", cambia=True,
                     detalle="agrega ScoreBand y ScoreBandsResponse; FitogenixProduct no se toca"),
    PuntaDelContrato(archivo="fitogenix-server/src/routes/products/lookupSchema.ts", cambia=False,
                     detalle="lookupResponseSchema y productProperties quedan idénticos; el satisfies sigue compilando"),
    PuntaDelContrato(archivo="fitogenix-native/src/lib/contracts/product.ts", cambia=False,
                     detalle="el espejo nuevo entra como archivo hermano en la misma carpeta declarada espejo"),
    PuntaDelContrato(archivo="fitogenix-server/src/routes/scoring/bands.ts", cambia=True,
                     detalle="ruta nueva scoreBandsRoute, sin auth, registrada en main.ts"),
    PuntaDelContrato(archivo="fitogenix-server/src/routes/scoring/bandsSchema.ts", cambia=True,
                     detalle="bandsResponseSchema atado a ScoreBand con satisfies"),
    PuntaDelContrato(archivo="fitogenix-native/src/lib/contracts/scoreBands.ts", cambia=True,
                     detalle="el espejo del cliente para la tabla de bandas"),
]

BRIEFS = [
    Brief(ticket="FTG-002", destinatario=Disciplina.BACKEND, entregable=Entregable.PR, fuente=Marca.VERIFICADO,
          objetivo="exponer GET /scoring/bands derivado de TIERS y NO_DATA_TIER, sin un segundo literal en ningún lado, y dejar el mapeo estado→fito en un solo lugar",
          contexto_relevante=[P(ref="CONTEXT.md §3.1"), P(ref="CONTEXT.md §3.2"), P(ref="CONTEXT.md §3.3"), P(ref="CONTEXT.md §3.4"), P(ref="CONTEXT.md §5.6"), P(ref="CONTEXT.md §8.7")],
          criterio_de_aceptacion="Dado el endpoint implementado Cuando se corre el grep de literales de umbral y de color en src/routes/scoring/ Entonces da cero y ningún test nuevo afirma un número: afirma derivación",
          fuera_de_alcance=["tocar FitogenixProduct o lookupResponseSchema", "cambiar umbrales (CONTEXT.md §8.7)", "cualquier migración", "la columna denormalizada de CONTEXT.md §8.19"]),
    Brief(ticket="FTG-002", destinatario=Disciplina.UX, entregable=Entregable.MOCKUP, fuente=Marca.VERIFICADO,
          objetivo="el copy de las cinco bandas de la Guía, incluida la de sin datos, y todos los estados de una pantalla que deja de ser estática",
          contexto_relevante=[P(ref="CONTEXT.md §3.1"), P(ref="CONTEXT.md §3.3"), P(ref="CONTEXT.md §1.6"), P(ref="CONTEXT.md §5.8")],
          criterio_de_aceptacion="Dados los cinco estados de red y las cinco bandas Cuando se revisa el copy entregado Entonces cada estado tiene copy escrito, ningún texto contiene un corte ni un color, y la banda sin datos está explicada",
          fuera_de_alcance=["los STEPS de GuideScreen (CONTEXT.md §8.4, §8.13)", "elegir umbrales o nombres de banda"]),
    Brief(ticket="FTG-002", destinatario=Disciplina.MOBILE, entregable=Entregable.PR, fuente=Marca.VERIFICADO,
          objetivo="borrar el TIERS local de la Guía, consumir el endpoint nuevo y renderizar exactamente lo que llega",
          contexto_relevante=[P(ref="CONTEXT.md §5.2"), P(ref="CONTEXT.md §3.4"), P(ref="CONTEXT.md §3.1"), P(ref="CONTEXT.md §5.8"), P(ref="CONTEXT.md §1.6")],
          criterio_de_aceptacion="Dado el cliente sin TIERS local Cuando se barre fitogenix-native/src/ buscando cortes, rangos y colores de banda Entonces da cero fuera de src/constants/theme.ts y no hay ninguna comparación numérica nueva sobre score",
          fuera_de_alcance=["borrar src/domain/product/ftgEngine.ts", "reescribir los STEPS", "recalcular cualquier cosa del puntaje"]),
    Brief(ticket="FTG-002", destinatario=Disciplina.QA, entregable=Entregable.REPORTE, fuente=Marca.VERIFICADO,
          objetivo="verificar que la Guía y la pantalla de producto dicen lo mismo, banda por banda, y que el barrido del guard queda limpio",
          contexto_relevante=[P(ref="CONTEXT.md §3.1"), P(ref="CONTEXT.md §3.2"), P(ref="CONTEXT.md §3.3"), P(ref="CONTEXT.md §5.2"), P(ref="CONTEXT.md §5.6")],
          criterio_de_aceptacion="Dado un puntaje por banda Cuando se abre la Guía y después la pantalla de ese producto Entonces label, color, tagline y sello coinciden, y en la franja del medio ninguna de las dos pantallas afirma el sello",
          fuera_de_alcance=["auditar el copy de los STEPS", "implementar cualquier fix"]),
]

# NO ENTRA (2/4): el arquitecto devolvió `status: partial`. `ContratoAprobado` no tiene
# campo de estado — `EstadoReporte` existe, pero para `Reporte`.
# NO ENTRA (3/4): cada supuesto venía marcado ⚠️. `supuestos` es `list[str]`: la marca se pierde.
# NO ENTRA (4/4): cada decisión abierta venía con **dueño** (orchestrator / ux).
# `decisiones_abiertas` es `list[str]`, así que el dueño viaja como prosa y ruteársela a
# alguien exige parsearla. Es el mismo defecto que B-6: una decisión sin dueño explícito.
CONTRATO_FTG_002 = ContratoAprobado(
    ticket="FTG-002",
    objetivo="que la pantalla de Guía muestre las bandas, sus colores, sus mensajes y su sello derivados en el servidor desde TIERS/NO_DATA_TIER y servidos como datos por un endpoint nuevo",
    reglas_de_validacion=REGLAS,
    campos=CAMPOS,
    puntas_tocadas=PUNTAS,
    briefs=BRIEFS,
    toca_scoring=True,
    supuestos=[
        "no leí orquestacion/: lo que afirmo sobre qué detecta cada guard sale de 08-agente-arquitecto.md y del ticket, no del código",
        "'ningún endpoint devuelve la tabla' lo verifiqué por enumeración de declaraciones de ruta, no contra la API viva",
        "asumo que mover el umbral del sello (CONTEXT.md §8.7) se hará moviendo un corte de TIERS; si es un corte independiente, el payload cambia",
        "no corrí npm test ni tsc --noEmit en ninguno de los dos repos",
        "asumo que la tabla de bandas puede cachearse sin sesión porque no es dato de usuario; no está escrito en ningún lado",
        "GuideScreen pasa de estática a dependiente de red: los estados de carga/error/offline no existen hoy y hay que especificarlos",
    ],
    decisiones_abiertas=[
        "D-1 · orchestrator: ¿el umbral del sello se mueve cambiando TIERS[0].min o se vuelve un corte independiente de las bandas? La forma del contrato depende de la respuesta",
        "D-2 · orchestrator: ¿HomeScreen.tsx y ScanResultScreen.tsx entran a FTG-002 o van a ticket aparte? El criterio A-2 del ticket no se puede cumplir sin ellos",
        "D-3 · ux: cómo se llama en la Guía la franja sin sello",
        "D-4 · orchestrator: CONTEXT.md §5.6 no verifica que el contrato documentado se actualice; cerrar la brecha es ampliar el guard o reescribir la sección",
        "D-5 · orchestrator: que esto entre a CONTEXT.md §8 como bloqueante nuevo",
    ],
    marca=Marca.DECIDIDO_NO_IMPLEMENTADO,
)
