"""
Contratos de transición del pipeline de Fitogenix — Fase 3 (SDD).

Estos modelos NO son documentación: son el mecanismo anti-alucinación. Cada regla del
SSOT que se puede verificar sin un LLM está acá como validador.

**Por qué pesan tanto acá y no en PampaGrow.** Jere decidió el 31/8/2026 que el pipeline
**no pide OK antes de implementar**: se interrumpe solo si hay duda
(`PROPUESTA_grafo_fase2.md` sección 10, decisión 1). Si nadie firma de rutina, el contrato
lo tiene que sostener Pydantic. Un `Brief` con texto copiado en vez de puntero **tiene que
fallar**, y un `ContratoAprobado` con una regla sin puntero **tiene que fallar**, porque no
hay un humano río abajo que lo note.

Reglas del SSOT implementadas como código, no como prompt:

  §3.1   los umbrales no se transcriben — viven en `scoring/constants.ts`   → guards.py
  §3.4   el cliente renderiza, nunca recalcula                              → guards.py
  §5.2   regla absoluta de frontera: todo pasa por el backend propio        → guards.py
  §5.6   endpoint nuevo ⇒ contrato de API en el MISMO commit                → guards.py
  §7     dominios exclusivos: nadie edita un artefacto del que no es dueño
  §8     un plan que toca un bloqueante 🔴 abierto no está listo
  §9     citas al código: archivo + símbolo, NUNCA número de línea
  —      un Brief cita §X; texto copiado es rechazo
  —      `done` sin evidencia es rechazo; con supuestos abiertos, es `partial`
  —      una afirmación ✅ sin ruta de archivo es 🔴, no ✅
  —      un 📄 (fuente secundaria) nunca alcanza para proponer cambio de código

**Lo que deliberadamente NO se copió de PampaGrow:** la `DENY_LIST` (prohíbe `supabase`,
que es nuestra base de datos), las reglas R1–R14 (son de su dominio), `TOOLS_BY_AGENT` (ya
no existe allá: era código muerto) y los nombres de nodo y de agente.

**Una convención documentada que este archivo NO valida, a propósito.** `CONVENCIONES_EQUIPO.md`
sección 3 pide asunto de commit en inglés y ≤72 caracteres. Medido sobre los últimos 40
commits de cada repo (2026-09-01): 22 de 115 pasan de 72 caracteres y la mayoría están en
español, incluidos los tres HEAD actuales. Un validador que rechaza la historia del propio
proyecto no es un control: es ruido, y un guard que da ruido termina apagado. Se reporta la
divergencia y se deja que la resuelva quien es dueño del documento, en vez de elegirla en
silencio (`CONTEXT.md §9`, convención de contradicciones).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .guards import corre_los_guards

# --------------------------------------------------------------------------- #
# Vocabulario cerrado                                                          #
# --------------------------------------------------------------------------- #


class Marca(str, Enum):
    """Las cuatro marcas de `CONTEXT.md` (convención ampliada el 28/8/2026), más 📄.

    ⚠️ **nunca** se trata como ✅: ⚠️ es "no verificado", 🟡 es "verificado como ausente
    y ya decidido". Son estados distintos y la diferencia es la que hace auditable al SSOT.
    """

    VERIFICADO = "✅"
    SIN_CONTRASTAR = "⚠️"
    DECIDIDO_NO_IMPLEMENTADO = "🟡"
    ABIERTO = "🔴"
    FUENTE_SECUNDARIA = "📄"


class Disciplina(str, Enum):
    """Los dueños de `CONTEXT.md §7`. No se traducen: son identificadores de dominio."""

    ORCHESTRATOR = "orchestrator"
    ARCHITECT = "architect"
    NUTRITION = "nutrition"
    BACKEND = "backend"
    MOBILE = "mobile"
    DATA_AI = "data-ai"
    ETL = "etl"
    QA = "qa"
    UX = "ux"
    DEVOPS = "devops"
    NINGUNA = "ninguna"


class Entregable(str, Enum):
    PR = "PR"
    ADR = "ADR"
    DICTAMEN = "dictamen"
    CONTRATO = "contrato"
    REPORTE = "reporte"
    MOCKUP = "mockup"


class EstadoReporte(str, Enum):
    DONE = "done"
    BLOCKED = "blocked"
    PARTIAL = "partial"


class Severidad(str, Enum):
    BLOQUEANTE = "bloqueante"  # vuelve a n2_contrato: el contrato está mal
    MAYOR = "mayor"            # vuelve a n3_implementar: la implementación está mal
    MENOR = "menor"            # se anota, no bloquea


class Veredicto(str, Enum):
    APROBADO = "aprobado"
    APROBADO_CON_CONDICIONES = "aprobado-con-condiciones"
    RECHAZADO = "rechazado"


#: Veredictos que avanzan. `aprobado-con-condiciones` avanza a propósito: las condiciones
#: viajan en el cuerpo del PR, para el humano que revisa.
VEREDICTOS_QUE_AVANZAN = (Veredicto.APROBADO, Veredicto.APROBADO_CON_CONDICIONES)

#: Techos de loop (`PROPUESTA_grafo_fase2.md` sección 3). *"Un pipeline de agentes sin
#: techo de iteración no es autónomo: es una factura."*
#: El de contrato pasó de 1 a 2 el 2026-09-19 (decisión de Jere al ejecutar el P0-4 del
#: dictamen pre-debut): la segunda ronda existe SOLO para rehacer el contrato con las
#: respuestas del HitL 2. Con techo 1 esas respuestas se guardaban y no llegaban a ningún
#: prompt. Una ronda con respuesta humana no es "el pipeline discutiendo consigo mismo".
TECHOS: dict[str, int] = {"aclaracion": 3, "contrato": 2, "revision": 2}

FRASE_DE_INCERTIDUMBRE = (
    "No tengo información verificable suficiente para esto. Lo marco en vez de suponerlo."
)

# --------------------------------------------------------------------------- #
# Punteros — el SSOT se cita, no se copia                                      #
# --------------------------------------------------------------------------- #

_P_CONTEXT = re.compile(r"^CONTEXT\.md\s+§\d+(\.\d+)?$", re.IGNORECASE)
_P_NUTRICION = re.compile(r"^(?:nutricion/)?NUTRICION\.md\s+§N\d+$", re.IGNORECASE)
# `BITACORA_DECISIONES.md ADR-007` o `BITACORA_DECISIONES.md → ADR-007`: la flecha es la
# misma separación que ya se usa para código, y el modelo la escribió sola (2026-09-20).
_P_BITACORA = re.compile(r"^BITACORA_DECISIONES\.md\s*(?:→\s*)?\s*ADR-\d{3}$", re.IGNORECASE)
#: Cualquier documento del set: entero, por sección numerada, o por sección CON NOMBRE.
#:
#: Las secciones con nombre entraron el 2026-09-20, en la segunda corrida real: los tickets
#: de `tareas/` no numeran sus secciones —se llaman "Criterio de aceptación", "Riesgo"— y el
#: orquestador no tenía forma válida de citar el criterio que estaba analizando. Los prompts
#: de agente (`01-agente-ux.md`) tampoco: citarlos enteros es correcto, son el documento del
#: dueño. Cada forma rechazada de más cuesta un reintento de ~45k tokens en Opus.
#:
#: `CONTEXT.md` y `NUTRICION.md` quedan afuera a propósito: esos SIEMPRE llevan `§`, porque
#: son los grandes y citarlos enteros es justo el costo que este pipeline existe para evitar.
_P_DOCUMENTO = re.compile(
    r"^(?!CONTEXT\.md$|(?:nutricion/)?NUTRICION\.md$)[\w.\-/]+\.md"
    r"(?:\s+secci[oó]n\s+[^\n]{1,60}|\s*→\s*[^\n]{1,60})?$",
    re.IGNORECASE)
# Código: repo/ruta.ext, opcionalmente ` → simbolo` (o varios, separados por coma), o un
# directorio terminado en `/`. Sin número de línea.
# Los dos agregados son del 2026-09-18, medidos contra el golden FTG-002: el arquitecto
# citó `constants.ts → TIERS, NO_DATA_TIER, EXCELLENT_FROM, BAD_BELOW` —cuatro símbolos
# del mismo archivo, que es exactamente cómo se cita una tabla— y `fitogenix-server/
# migrations/` como directorio. Los dos se rechazaban, y la única salida era truncar la
# cita. Un validador que obliga a citar de menos no protege nada.
_P_CODIGO = re.compile(
    r"^fitogenix-(server|native)/[\w\-./]+(?:\.\w+(\s*→\s*[\w.]+(?:\s*,\s*[\w.]+)*)?|/)$"
)
_NUMERO_DE_LINEA = re.compile(r"\.\w+:\d+")
_TICKET = re.compile(r"^(FTG-\d{1,4}|B-\d{1,3}|C-\d{1,3}|N-\d{1,3}|sin-ticket)$")
# Given/When/Then, en español: la documentación del proyecto va en español.
# El español concuerda en género y número, y hasta el 2026-09-18 este validador no: pedía
# `dado` literal, así que "Dada una banda cualquiera / Cuando / Entonces" —castellano
# correcto— se rechazaba como "sin criterio de aceptación". Lo encontró el primer contrato
# real (golden FTG-002): caían 3 de 9 campos, los 3 por la concordancia y ninguno por el
# criterio. Un validador que castiga la gramática correcta le enseña al modelo a escribir mal.
_DCE = re.compile(r"\bdad[oa]s?\b.*\bcuando\b.*\bentonces\b", re.IGNORECASE | re.DOTALL)

#: Largo por encima del cual un "puntero" es, casi con certeza, texto copiado.
LARGO_MAXIMO_DE_PUNTERO = 120


#: Separadores con los que un modelo pega varios punteros en una sola cadena. Se parten en
#: vez de rechazarse: en la primera corrida real esto costó tres reintentos de Opus (~45k
#: tokens de entrada cada uno) y ninguno era un error de criterio — era formato.
_SEPARADORES = re.compile(r"\s+[·•|]\s+|\s+\+\s+|\s*;\s*")
#: Un paréntesis al final (`CONTEXT.md §3.1 (ADR-007)`) es una glosa, no parte del puntero.
_GLOSA = re.compile(r"\s*\([^)]*\)\s*$")


def normaliza_puntero(p: str) -> str:
    """Limpieza mecánica de UN puntero. No cambia a qué apunta; solo cómo está escrito.

    Lo que arregla: backticks y comillas alrededor, espacios de más, `§ 3.1` → `§3.1`, la
    glosa entre paréntesis al final, y la flecha con espaciado raro. Lo que NO arregla:
    nada de sustancia — un puntero que apunta a otra cosa sigue siendo un error del modelo.
    """
    t = p.strip().strip("`\"'").strip()
    t = _GLOSA.sub("", t)
    t = re.sub(r"§\s+", "§", t)
    t = re.sub(r"\s*→\s*", " → ", t)
    return re.sub(r"\s{2,}", " ", t).strip()


def normaliza_punteros(v: object) -> object:
    """Igual, pero para un campo de lista: además PARTE lo que venga pegado.

    No parte por coma cuando hay `→`: `constants.ts → TIERS, NO_DATA_TIER` son cuatro
    símbolos del mismo archivo, que es exactamente cómo se cita una tabla.
    """
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        return v
    out: list[str] = []
    for x in v:
        if not isinstance(x, str):
            out.append(x)
            continue
        partes = _SEPARADORES.split(x)
        if len(partes) == 1 and "→" not in x and "," in x:
            partes = x.split(",")
        documento = ""
        for p in partes:
            if not p or not p.strip():
                continue
            limpio = normaliza_puntero(p)
            # `CONTEXT.md §3.1 · §3.2 · §3.3`: del segundo en adelante el documento queda
            # implícito. Es como cita una persona, y rechazarlo no enseña nada.
            m = re.match(r"^([\w.\-/]+\.md)\b", limpio)
            if m:
                documento = m.group(1)
            elif limpio.startswith("§") and documento:
                limpio = f"{documento} {limpio}"
            out.append(limpio)
    return out


class PunteroInvalido(ValueError):
    """El puntero no resuelve. El hueco no se rellena: se devuelve."""


def valida_puntero(p: str) -> str:
    """Un puntero es `CONTEXT.md §X`, `NUTRICION.md §Nx`, un ADR, una sección en prosa
    de otro documento, o una ruta de código con símbolo. Nada más.

    Un documento del set se puede citar entero (`01-agente-ux.md`), por sección numerada
    (`CONVENCIONES_EQUIPO.md sección 2`) o por sección con nombre
    (`FTG-002.md sección Criterio de aceptación`). `CONTEXT.md` y `NUTRICION.md` no: esos
    llevan `§` siempre.

    Rechaza el número de línea por la convención del 31/8/2026 (`CONTEXT.md §9`): se
    encontró `ENGINE_VERSION` citado como `ftgEngine.ts:24` cuando vive en
    `scoring/constants.ts:24` — archivo equivocado, número correcto, error invisible
    durante tres días. Un número de línea hace que una cita rota siga pareciendo sana.
    """
    if _NUMERO_DE_LINEA.search(p):
        raise PunteroInvalido(
            f"cita por número de línea: {p!r}. CONTEXT.md §9 (convención del 31/8/2026): "
            f"archivo + símbolo o cita textual, nunca número de línea."
        )
    if not any(rx.match(p) for rx in (_P_CONTEXT, _P_NUTRICION, _P_BITACORA, _P_DOCUMENTO, _P_CODIGO)):
        # El largo se chequea acá abajo y no arriba (2026-09-18): es una heurística contra
        # prosa copiada, y las formas de arriba están ancladas con `^...$`, así que lo que
        # las matchea ya es un puntero por estructura, por largo que sea. Citar cuatro
        # símbolos del mismo archivo —`constants.ts → TIERS, NO_DATA_TIER, EXCELLENT_FROM,
        # BAD_BELOW`, 125 caracteres— se rechazaba por largo siendo la cita más precisa
        # posible. El largo solo decide sobre lo que ya no matcheó nada.
        if len(p) > LARGO_MAXIMO_DE_PUNTERO:
            raise PunteroInvalido(
                f"puntero demasiado largo, parece texto copiado: {p[:60]!r}..."
            )
        raise PunteroInvalido(
            f"puntero inválido: {p!r}. Se espera 'CONTEXT.md §X', 'NUTRICION.md §Nx', "
            f"'BITACORA_DECISIONES.md ADR-00X', '<doc>.md sección N' o "
            f"'fitogenix-server/ruta.ts → simbolo'."
        )
    return p


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False, str_strip_whitespace=True)


class PunteroDeContexto(Base):
    """Un puntero al SSOT. Existe como modelo para que no se pueda pasar prosa donde va
    una cita: el `Brief` de un agente de disciplina se arma con esto, y el cargador por
    sección entrega exactamente lo que dice `ref`.
    """

    ref: str
    motivo: str = Field(default="", max_length=200, description="Por qué hace falta esta sección.")

    @field_validator("ref")
    @classmethod
    def _valida(cls, v: str) -> str:
        return valida_puntero(normaliza_puntero(v))

    @property
    def es_seccion_de_context(self) -> bool:
        return bool(_P_CONTEXT.match(self.ref))

    def __str__(self) -> str:  # pragma: no cover - conveniencia de logging
        return self.ref


# --------------------------------------------------------------------------- #
# Protocolo de handoff                                                         #
# --------------------------------------------------------------------------- #


class Brief(Base):
    """Arquitecto → agente de disciplina. Un Brief, un entregable.

    **Este objeto es el ahorro de tokens entero.** Hoy un agente de disciplina se traga el
    SSOT completo para usar dos secciones; con esto carga su archivo más las secciones que
    su Brief apunta. Un Brief que apunta de más es la diferencia entre un agente barato y
    uno caro, y uno que copia texto en vez de apuntar anula el mecanismo.
    """

    ticket: str = Field(default="sin-ticket")
    objetivo: str = Field(min_length=8, max_length=200)
    fuente: Marca
    contexto_relevante: list[PunteroDeContexto] = Field(default_factory=list)
    criterio_de_aceptacion: str
    fuera_de_alcance: list[str] = Field(default_factory=list)
    entregable: Entregable
    destinatario: Disciplina

    @field_validator("ticket")
    @classmethod
    def _ticket(cls, v: str) -> str:
        if not _TICKET.match(v):
            raise ValueError(f"ticket inválido: {v!r} (FTG-###, B-##, C-##, N-## o 'sin-ticket')")
        return v

    @field_validator("criterio_de_aceptacion")
    @classmethod
    def _dce(cls, v: str) -> str:
        if not _DCE.search(v):
            raise ValueError(
                "criterio_de_aceptacion tiene que estar en formato Dado/Cuando/Entonces"
            )
        return v

    @model_validator(mode="after")
    def _reglas(self) -> "Brief":
        if self.destinatario == Disciplina.NINGUNA:
            raise ValueError("un Brief sin destinatario no se puede delegar.")
        # `CONTEXT.md §7`: el arquitecto no implementa. Si lo hiciera, dejaría de ser el
        # que puede decir que las tres puntas del contrato coinciden.
        if self.destinatario == Disciplina.ARCHITECT and self.entregable == Entregable.PR:
            raise ValueError(
                "el arquitecto no implementa (CONTEXT.md §7): produce contrato y Briefs, no PRs."
            )
        # `09-agente-nutricion.md`: no escribe código.
        if self.destinatario == Disciplina.NUTRITION and self.entregable == Entregable.PR:
            raise ValueError("nutrition no escribe código (CONTEXT.md §7): produce dictámenes.")
        return self


class Evidencia(Base):
    tipo: Literal["test", "archivo", "comando", "grep", "captura"]
    referencia: str = Field(min_length=3, description="p. ej. seals.test.ts → 'sodio en bebidas'")
    verificada_en_sesion: bool = Field(
        default=False, description="Si es False, el agente dice 'sin verificar'."
    )

    @property
    def tiene_ruta_de_archivo(self) -> bool:
        """`PROPUESTA_grafo_fase2.md` sección 2: una afirmación ✅ sin ruta de archivo es 🔴."""
        return bool(re.search(r"[\w\-/]+\.\w{2,4}\b", self.referencia))


class Bloqueo(Base):
    descripcion: str = Field(min_length=10)
    desbloquea: Disciplina | Literal["jere"]
    puntero: Optional[str] = None

    @field_validator("puntero")
    @classmethod
    def _p(cls, v: Optional[str]) -> Optional[str]:
        return valida_puntero(normaliza_puntero(v)) if v else v


class Reporte(Base):
    """Agente de disciplina → orquestador."""

    ticket: str = "sin-ticket"
    agente: Disciplina
    estado: EstadoReporte
    que_hice: list[str] = Field(max_length=3)
    evidencia: list[Evidencia] = Field(default_factory=list)
    supuestos: list[str] = Field(default_factory=list)
    bloqueos: list[Bloqueo] = Field(default_factory=list)
    marca: Marca = Marca.SIN_CONTRASTAR
    cambio_de_codigo_propuesto: list[str] = Field(default_factory=list)
    handoff_a: Disciplina = Disciplina.NINGUNA

    @model_validator(mode="after")
    def _reglas_de_cierre(self) -> "Reporte":
        if self.estado == EstadoReporte.DONE and not self.evidencia:
            raise ValueError("estado=done exige evidencia. Sin evidencia no se cierra.")
        if self.estado == EstadoReporte.DONE and self.supuestos:
            raise ValueError(
                "supuestos abiertos ⇒ el ticket no pasa a 'done'. Usá estado=partial y que "
                "el supuesto viaje visible."
            )
        if self.estado == EstadoReporte.BLOCKED and not self.bloqueos:
            raise ValueError("estado=blocked exige al menos un bloqueo con dueño.")
        # Una afirmación ✅ sin ruta de archivo es 🔴, no ✅.
        if self.marca == Marca.VERIFICADO and not any(e.tiene_ruta_de_archivo for e in self.evidencia):
            raise ValueError(
                "marca ✅ sin evidencia con ruta de archivo. El propio SSOT dice que eso es 🔴."
            )
        # `09-agente-nutricion.md`: un 📄 nunca alcanza para cambiar código.
        if self.marca == Marca.FUENTE_SECUNDARIA and self.cambio_de_codigo_propuesto:
            raise ValueError(
                "un 📄 (fuente secundaria) nunca alcanza para proponer cambio de código: "
                "sirve para abrir un ticket y decir qué fuente primaria hace falta."
            )
        return self

    @property
    def puede_cerrar(self) -> bool:
        return self.estado == EstadoReporte.DONE and not self.supuestos


# --------------------------------------------------------------------------- #
# n1a_analizar — análisis del requerimiento                                    #
# --------------------------------------------------------------------------- #


class PreguntaAbierta(Base):
    """Pregunta directa para Jere. Sin preámbulo."""

    id: str = Field(pattern=r"^P\d{1,2}$")
    pregunta: str = Field(min_length=10, max_length=280)
    por_que_bloquea: str = Field(min_length=10)
    puntero: Optional[str] = None
    opciones: list[str] = Field(default_factory=list)

    @field_validator("puntero")
    @classmethod
    def _p(cls, v: Optional[str]) -> Optional[str]:
        return valida_puntero(normaliza_puntero(v)) if v else v


class Contradiccion(Base):
    """Se reporta, nunca se elige en silencio. Es como se cerraron C-07 y C-14.

    **`resolucion` existe desde el 2026-09-20**, por la primera corrida real: el humano
    contestó las cuatro preguntas del HitL 1, el análisis quedó listo, y el objeto no tenía
    dónde decir *cómo* se resolvió cada contradicción. Reportada y pendiente eran el mismo
    estado, así que `listo_para_contratar=True` no podía convivir con una contradicción ya
    zanjada: el modelo entregó tres veces lo mismo y la corrida murió con la decisión ya
    tomada. Lo que la regla protege es que nadie elija en silencio — y una resolución
    escrita es lo contrario del silencio.
    """

    tema: str
    fuente_a: str
    fuente_b: str
    resuelve: Literal["jere", "orchestrator", "architect", "nutrition"] = "jere"
    resolucion: Optional[str] = Field(
        default=None, min_length=10,
        description="Cómo se resolvió, en una frase. Vacío = sigue pendiente y frena el contrato.")

    @property
    def pendiente(self) -> bool:
        return not self.resolucion


class RequisitoTrazado(Base):
    """Un requisito con su trazabilidad. **Los punteros son varios** (2026-09-20).

    Es la misma lección que `ReglaDeValidacion` aprendió el 18/9 y que este campo no había
    aprendido: en la primera corrida real el orquestador quiso trazar un requisito a la
    sección que manda **y** al archivo donde se ve —`CONTEXT.md §3.1 · fitogenix-native/
    src/screens/GuideScreen.tsx → TIERS`—, el campo era un `str`, y la única salida era
    concatenarlos con un `·`, que no valida. Costó 13 y 18 errores de validación en dos
    corridas, o sea dos reintentos de Opus de ~40k tokens cada uno, y ninguno era un error
    del modelo: era el schema pidiendo citar de menos.
    """

    enunciado: str
    punteros: list[str] = Field(min_length=1)
    marca: Marca

    @model_validator(mode="before")
    @classmethod
    def _singular(cls, data: object) -> object:
        if isinstance(data, dict) and "puntero" in data and "punteros" not in data:
            data = {**data, "punteros": [data["puntero"]]}
            data.pop("puntero")
        return data

    @field_validator("punteros", mode="before")
    @classmethod
    def _p(cls, v: object) -> object:
        return normaliza_punteros(v)

    @field_validator("punteros")
    @classmethod
    def _valida(cls, v: list[str]) -> list[str]:
        return [valida_puntero(x) for x in v]

    @property
    def puntero(self) -> str:
        """El primero. La autoridad va primero por convención; la evidencia después."""
        return self.punteros[0]


class AnalisisDeRequerimiento(Base):
    """Salida de `n1a_analizar`. Se recomputa en cada vuelta del loop de aclaración.

    El nodo está partido del `interrupt()` a propósito: `interrupt()` re-ejecuta el nodo
    entero al reanudar, así que si la llamada al LLM viviera en el mismo nodo, cada
    respuesta de Jere pagaría un análisis extra.
    """

    ronda: int = Field(default=1, ge=1, le=TECHOS["aclaracion"])
    ticket: str = "sin-ticket"
    resumen: str = Field(min_length=20, max_length=1200)
    disciplinas_afectadas: list[Disciplina] = Field(default_factory=list)
    requisitos: list[RequisitoTrazado] = Field(default_factory=list)
    preguntas_abiertas: list[PreguntaAbierta] = Field(default_factory=list)
    contradicciones: list[Contradiccion] = Field(default_factory=list)
    bloqueantes_tocados: list[str] = Field(
        default_factory=list, description="IDs de `CONTEXT.md §8`, p. ej. ['B-6']."
    )
    fuera_de_alcance: list[str] = Field(default_factory=list)
    marca_general: Marca = Marca.SIN_CONTRASTAR
    listo_para_contratar: bool = False
    nota_de_incertidumbre: Optional[str] = None
    # De acá sale el escalado del arquitecto (`PROPUESTA_grafo_fase2.md` sección 5). Hasta
    # el 2026-09-19 `n2_contrato` buscaba `toca_scoring` en este objeto con `hasattr`, el
    # campo no existía y el arquitecto iba siempre a Sonnet. Lo declarado se une con lo que
    # `det.escalado_del_analisis` deriva de los punteros: el modelo no puede bajarlo.
    toca_scoring: bool = False
    toca_auth: bool = False
    toca_migracion: bool = False

    @model_validator(mode="after")
    def _reglas(self) -> "AnalisisDeRequerimiento":
        pendientes = [c for c in self.contradicciones if c.pendiente]
        if (self.preguntas_abiertas or pendientes) and self.listo_para_contratar:
            raise ValueError(
                f"listo_para_contratar=True con {len(self.preguntas_abiertas)} pregunta(s) "
                f"abierta(s) y {len(pendientes)} contradicción(es) sin `resolucion`. Se escala, "
                f"no se supone. Una contradicción ya zanjada lleva su `resolucion` escrita y "
                f"viaja como registro; una sin resolver frena el contrato."
            )
        # `CONTEXT.md §8`: un plan que toca un bloqueante 🔴 abierto tiene una decisión de
        # producto sin tomar en el camino. B-12 no tiene dueño, así que B-2/B-3/B-4 no se
        # rutean a ningún nodo: vuelven `blocked → unblocks: jere`.
        if self.bloqueantes_tocados and self.listo_para_contratar:
            raise ValueError(
                f"listo_para_contratar=True tocando bloqueantes abiertos "
                f"{sorted(self.bloqueantes_tocados)}. CONTEXT.md §8: se resuelven antes."
            )
        marcas = {r.marca for r in self.requisitos} | {self.marca_general}
        if (Marca.SIN_CONTRASTAR in marcas or Marca.ABIERTO in marcas) and not self.nota_de_incertidumbre:
            object.__setattr__(self, "nota_de_incertidumbre", FRASE_DE_INCERTIDUMBRE)
        return self


class RespuestaHumana(Base):
    """Lo que Jere contesta en el interrupt. Se persiste: es una decisión de producto."""

    ronda: int = Field(ge=1)
    aprobado: bool = Field(description="True solo con un OK explícito.")
    respuestas: dict[str, str] = Field(default_factory=dict, description="{'P1': '...'}")
    comentario_libre: str = ""
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def aprobacion_valida(analisis: AnalisisDeRequerimiento, respuesta: RespuestaHumana) -> bool:
    """Un `aprobado=True` no cuenta si el análisis todavía tiene preguntas abiertas.

    Impide el OK vacío: no se puede aprobar un requisito sin resolver.
    """
    return (respuesta.aprobado and not analisis.preguntas_abiertas
            and not any(c.pendiente for c in analisis.contradicciones))


# --------------------------------------------------------------------------- #
# n2_contrato — el arquitecto                                                  #
# --------------------------------------------------------------------------- #

#: Las tres puntas del contrato de producto (`PROPUESTA_grafo_fase2.md` sección 7).
#: Se mueven juntas o no se mueven: cada archivo tenía dueño, la relación entre ellos no,
#: y es exactamente así como C-04 y C-08 se quedaron abiertos.
PUNTOS_DEL_CONTRATO: tuple[str, ...] = (
    "fitogenix-server/src/types/fitogenix.ts",
    "fitogenix-server/src/routes/products/lookupSchema.ts",
    "fitogenix-native/src/lib/contracts/product.ts",
)


class ReglaDeValidacion(Base):
    """Cada regla del contrato cita sus punteros. Sin puntero no es una regla: es una opinión.

    **Son varios, no uno** (2026-09-18). El campo era un `str` y el primer contrato real
    dio dos punteros por regla —la sección de `CONTEXT.md` que manda y el archivo donde se
    verificó— porque son dos cosas distintas: una es la autoridad, la otra la evidencia.
    Forzar a elegir uno hacía que `det.verificado_sin_ruta` levantara 5 hallazgos sobre el
    golden FTG-002, y **4 eran del schema, no del arquitecto**: la regla sí tenía su ruta,
    pero no había dónde ponerla. Un validador que inventa hallazgos se desactiva solo.

    Se sigue aceptando `puntero=` en singular: es la forma corta de una lista de uno.
    """

    enunciado: str = Field(min_length=10)
    punteros: list[str] = Field(min_length=1)
    marca: Marca = Marca.SIN_CONTRASTAR

    @model_validator(mode="before")
    @classmethod
    def _singular(cls, data: object) -> object:
        if isinstance(data, dict) and "puntero" in data and "punteros" not in data:
            data = {**data, "punteros": [data["puntero"]]}
            data.pop("puntero")
        return data

    @field_validator("punteros", mode="before")
    @classmethod
    def _p(cls, v: object) -> object:
        return normaliza_punteros(v)

    @field_validator("punteros")
    @classmethod
    def _valida(cls, v: list[str]) -> list[str]:
        return [valida_puntero(x) for x in v]

    @property
    def puntero(self) -> str:
        """El primero. La autoridad va primero por convención; la evidencia después."""
        return self.punteros[0]

    @property
    def rutas_de_codigo(self) -> list[str]:
        """Los punteros que son un archivo que se puede abrir. Vacío = nada verificable."""
        return [x for x in self.punteros if _P_CODIGO.match(x.split("→")[0].strip())]


class CampoDelContrato(Base):
    nombre: str = Field(min_length=1)
    tipo: str = Field(min_length=1)
    obligatorio: bool = True
    criterio_de_aceptacion: str

    @field_validator("criterio_de_aceptacion")
    @classmethod
    def _dce(cls, v: str) -> str:
        if not _DCE.search(v):
            raise ValueError(
                "sin criterio de aceptación en Dado/Cuando/Entonces no hay forma de saber "
                "si el campo se cumplió."
            )
        return v


class PuntaDelContrato(Base):
    """Qué pasa con una punta del contrato. `cambia=False` también es una afirmación.

    **Las puntas ya no son solo tres** (2026-09-18). `PUNTOS_DEL_CONTRATO` pasó a ser la
    base —el contrato de *producto*— y no el universo. El primer contrato real declaró
    que agrandaba el conjunto a cinco, con un endpoint nuevo y su espejo, y no había
    forma de registrarlo: el objeto quedaba afirmando la verdad vieja, que es justo el
    silencio que la regla de las tres puntas existe para impedir.

    Lo que se conserva es el principio, no la lista: un tipo que cruza el cable se
    declara **en los dos repos**. Eso lo verifica `ContratoAprobado`.
    """

    archivo: str
    cambia: bool
    detalle: str = Field(min_length=5)

    @field_validator("archivo")
    @classmethod
    def _es_ruta_de_repo(cls, v: str) -> str:
        if not _P_CODIGO.match(v):
            raise ValueError(
                f"{v!r} no es una ruta de repo. Una punta del contrato es un archivo de "
                f"`fitogenix-server/` o `fitogenix-native/`."
            )
        return v

    @property
    def es_del_producto(self) -> bool:
        """Si es una de las tres puntas del contrato de producto."""
        return self.archivo in PUNTOS_DEL_CONTRATO

    @property
    def repo(self) -> str:
        return self.archivo.split("/", 1)[0]


class CambioDeEsquema(Base):
    """`CONTEXT.md §8` B-6: hoy las migraciones se corren a mano y nadie sabe qué esquema
    está vivo. Un cambio de esquema sin ADR repite exactamente eso.
    """

    tabla: str
    tipo: Literal["nueva-tabla", "nueva-columna", "indice", "constraint", "ninguno"]
    archivo_de_migracion: str = Field(pattern=r"^migrations/\d{3}_[a-z0-9_]+\.sql$")
    reversible: bool = True
    justificacion: str = Field(min_length=10)

    @model_validator(mode="after")
    def _reglas(self) -> "CambioDeEsquema":
        if self.tipo != "ninguno" and not self.reversible:
            raise ValueError(
                "una migración irreversible sin declararlo repite B-6: nadie sabría cómo volver."
            )
        return self


class ContratoAprobado(Base):
    """Salida de `n2_contrato`. **No se aprueba: se declara.**

    El pipeline no pide OK antes de implementar. Lo que decide si se interrumpe es
    `hay_que_preguntar()`, y sus dos fuentes son `supuestos`/`decisiones_abiertas` —que
    declara el modelo— más los chequeos deterministas, que corren en Python después y el
    modelo no puede declinar ni suavizar.
    """

    ticket: str = "sin-ticket"
    ronda: int = Field(default=1, ge=1, le=TECHOS["contrato"])
    objetivo: str = Field(min_length=20)
    reglas_de_validacion: list[ReglaDeValidacion] = Field(min_length=1)
    campos: list[CampoDelContrato] = Field(default_factory=list)
    puntas_tocadas: list[PuntaDelContrato] = Field(default_factory=list)
    cambios_de_esquema: list[CambioDeEsquema] = Field(default_factory=list)
    requiere_adr: bool = False
    adr_ref: Optional[str] = Field(default=None, pattern=r"^ADR-\d{3}$")
    briefs: list[Brief] = Field(min_length=1)
    supuestos: list[str] = Field(default_factory=list)
    decisiones_abiertas: list[str] = Field(default_factory=list)
    toca_scoring: bool = False
    toca_auth: bool = False
    toca_migracion: bool = False
    marca: Marca = Marca.SIN_CONTRASTAR

    @model_validator(mode="after")
    def _reglas(self) -> "ContratoAprobado":
        # La regla que define al arquitecto: las tres puntas se mueven juntas o no se mueve
        # ninguna. Un contrato que nombra una y calla las otras dos es el que rompe en el
        # dispositivo de un usuario semanas después, sin stack trace.
        nombradas = {p.archivo for p in self.puntas_tocadas}
        if nombradas & set(PUNTOS_DEL_CONTRATO):
            faltan = set(PUNTOS_DEL_CONTRATO) - nombradas
            if faltan:
                raise ValueError(
                    f"el contrato toca el contrato de producto y no nombra {sorted(faltan)}. "
                    f"Las tres puntas se enumeran siempre, aunque en dos la respuesta sea "
                    f"'no cambia': 'no cambia' es verificable, el silencio no."
                )
        # Una punta fuera de la base es un contrato NUEVO. La regla de las tres puntas no
        # se escribió por esos tres archivos: se escribió porque un tipo que cruza el cable
        # sin su espejo rompe en el dispositivo de un usuario semanas después y sin stack
        # trace. Así que un contrato nuevo también se declara en los dos repos.
        nuevas = [p for p in self.puntas_tocadas if not p.es_del_producto]
        if nuevas:
            repos = {p.repo for p in nuevas}
            if len(repos) < 2:
                solo = repos.pop()
                falta = "fitogenix-native" if solo == "fitogenix-server" else "fitogenix-server"
                raise ValueError(
                    f"el contrato declara puntas nuevas solo en {solo} y ninguna en {falta}. "
                    f"Un tipo que cruza el cable se declara en los dos repos, o el espejo "
                    f"queda sin dueño — que es cómo C-04 y C-08 se quedaron abiertos."
                )
        # Un cambio de esquema es una decisión de arquitectura: se registra como ADR.
        if any(c.tipo != "ninguno" for c in self.cambios_de_esquema) and not self.requiere_adr:
            raise ValueError("cambio de esquema sin requiere_adr=True (CONTEXT.md §8 B-6).")
        if self.requiere_adr and not self.adr_ref:
            raise ValueError("requiere_adr=True exige adr_ref (p. ej. ADR-006).")
        if self.toca_migracion and not self.cambios_de_esquema:
            raise ValueError("toca_migracion=True sin declarar el cambio de esquema.")
        return self

    @property
    def escala_a_opus(self) -> bool:
        """`PROPUESTA_grafo_fase2.md` sección 5: el arquitecto escala a Opus cuando el
        contrato toca el motor de scoring, auth/RLS o migraciones."""
        return self.toca_scoring or self.toca_auth or self.toca_migracion


class Incertidumbre(Base):
    """Un hecho del estado, calculado en Python después de que el modelo respondió."""

    chequeo: Literal[
        "seccion-inexistente",
        "puntero-sin-archivo",
        "bloqueante-abierto",
        "campo-sin-criterio",
        "verificado-sin-ruta",
        "frontera-violada",
        # Agregado el 2026-09-18: no estaba en los cinco de la sección 2. Existe porque
        # el objetivo número uno del pipeline es que un agente no cargue el SSOT entero,
        # y sin un tope nada impedía que un Brief lo reconstruyera citando §1, §2 y §5.
        "presupuesto-excedido",
        # Agregados el 2026-09-19 (dictamen pre-debut, P0-5 a P0-7):
        "regla-sin-verificar",   # una regla ⚠️ o 🔴 es una duda que el modelo ya confesó
        "repo-no-encontrado",    # sin el repo, el chequeo de punteros no puede correr: falla cerrado
        "escalado-omitido",      # el contrato toca motor/auth/migración y no corrió en Opus
    ]
    detalle: str
    puntero: Optional[str] = None


def ids_a_responder(c: ContratoAprobado, det: list[Incertidumbre]) -> dict[str, str]:
    """Lo que el HitL 2 le pregunta al humano, con un id estable por ítem.

    `S<n>` supuesto · `D<n>` decisión abierta · `C<n>` chequeo determinista. Los ids
    existen para que una respuesta se pueda atar a lo que responde, y para que un OK sin
    respuestas no cuente (`aprobacion_contrato_valida`).
    """
    out: dict[str, str] = {}
    out.update({f"S{i}": s for i, s in enumerate(c.supuestos, 1)})
    out.update({f"D{i}": d for i, d in enumerate(c.decisiones_abiertas, 1)})
    out.update({f"C{i}": f"{x.chequeo}: {x.detalle}" for i, x in enumerate(det, 1)})
    return out


def aprobacion_contrato_valida(
    c: ContratoAprobado, det: list[Incertidumbre], respuesta: "RespuestaHumana"
) -> bool:
    """El OK del HitL 2 cuenta solo si cada ítem preguntado tiene una respuesta no vacía.

    Hasta el 2026-09-19 este cruce se hacía contra el **análisis**, que a esa altura ya
    estaba limpio, así que cualquier OK aprobaba un contrato con supuestos sin contestar.
    """
    faltan = set(ids_a_responder(c, det)) - {
        k.strip().upper() for k, v in respuesta.respuestas.items() if str(v).strip()
    }
    return respuesta.aprobado and not faltan


def hay_que_preguntar(c: ContratoAprobado, det: list[Incertidumbre]) -> bool:
    """La condición de interrupción de `n2b_aclarar_contrato`: la UNIÓN de dos fuentes.

    Confiar en que el modelo declare su propia incertidumbre tiene una falla obvia:
    declarar menos incertidumbre es el camino más corto a no ser interrumpido. `det` no
    pasa por el modelo, y por eso el agujero queda tapado.
    """
    return bool(c.decisiones_abiertas) or bool(c.supuestos) or bool(det)


# --------------------------------------------------------------------------- #
# Cierre — lo que TODA entrega de un modelo deja escrito (2026-09-19)          #
# --------------------------------------------------------------------------- #


class CambioHecho(Base):
    """Un cambio concreto. `donde` es un puntero (se valida), no prosa."""

    que: str = Field(min_length=10, max_length=240)
    donde: Optional[str] = Field(
        default=None, description="Puntero: 'CONTEXT.md §X', 'fitogenix-server/ruta.ts → simbolo', …"
    )

    @field_validator("donde")
    @classmethod
    def _p(cls, v: Optional[str]) -> Optional[str]:
        return valida_puntero(normaliza_puntero(v)) if v else v


class Validacion(Base):
    """Cómo se validó algo. `origen` distingue lo que el modelo DICE de lo que Python HIZO.

    Un modelo llamado por API no tiene tools: no puede correr un test ni abrir un archivo.
    Por eso `origen="python"` solo lo escribe el pipeline (`llm.llama_estructurado`
    rechaza una entrega que lo traiga) y es la única validación que es un hecho.
    """

    metodo: Literal[
        "schema", "chequeo-determinista", "test", "comando", "lectura-de-codigo",
        "cita-al-ssot", "ninguna",
    ]
    referencia: str = Field(min_length=3, max_length=240)
    resultado: Literal["pasa", "falla", "no-corrido"]
    origen: Literal["modelo", "python"] = "modelo"


class RevisionManual(Base):
    requerida: bool
    que_revisar: list[str] = Field(default_factory=list, max_length=8)
    quien: Optional[Disciplina | Literal["jere"]] = None
    por_que: str = ""

    @model_validator(mode="after")
    def _reglas(self) -> "RevisionManual":
        if self.requerida and not (self.que_revisar and self.quien and len(self.por_que) >= 10):
            raise ValueError(
                "revisión manual requerida sin decir qué revisar, quién y por qué: "
                "una revisión sin objeto no se hace."
            )
        if not self.requerida and self.que_revisar:
            raise ValueError("que_revisar con requerida=False: o hace falta revisar, o no.")
        return self


class ProximoPaso(Base):
    # 600, no 280 (2026-09-20): en la primera corrida real el próximo paso era "contratar a
    # architect con tal alcance, que además arrastra el contrato de API en el mismo commit"
    # y no entraba. Un validador que obliga a resumir de más tira información que el humano
    # necesita para decidir.
    accion: str = Field(min_length=10, max_length=600)
    responsable: Disciplina | Literal["jere", "pipeline"]
    bloqueado_por: Optional[str] = None


class Cierre(Base):
    """El cierre de una entrega: qué cambió, cómo se validó, qué revisa un humano, qué sigue.

    Va en TODA salida de un modelo (`llm.Entrega`), no dentro de cada schema: así el
    formato es uno solo para los diez agentes, y los contratos de cada nodo no cambian.

    La regla que Python impone y el modelo no puede suavizar: **lo que no se validó de
    verdad pide revisión manual.** Si una validación falla, no corrió, o es `ninguna`, la
    revisión manual es obligatoria. Y ✅ exige al menos una validación de `origen=python`
    —el modelo sin tools no puede ganarse un ✅ solo—.
    """

    resumen: str = Field(min_length=20, max_length=600)
    cambios: list[CambioHecho] = Field(default_factory=list, max_length=12)
    validaciones: list[Validacion] = Field(min_length=1)
    revision_manual: RevisionManual
    proximo_paso: ProximoPaso
    marca: Marca = Marca.SIN_CONTRASTAR

    @model_validator(mode="after")
    def _reglas(self) -> "Cierre":
        flojas = [v for v in self.validaciones
                  if v.resultado != "pasa" or v.metodo == "ninguna"]
        if flojas and not self.revision_manual.requerida:
            raise ValueError(
                f"{len(flojas)} validación(es) sin pasar o sin correr y revision_manual."
                f"requerida=False. Lo que no se validó, lo revisa un humano."
            )
        if self.marca == Marca.VERIFICADO and not any(v.origen == "python" for v in self.validaciones):
            raise ValueError("cierre ✅ sin ninguna validación hecha por Python: es ⚠️.")
        return self


class RegistroDeCierre(Base):
    """Un `Cierre` en el estado, con quién y dónde lo escribió."""

    nodo: str
    agente: str
    modelo: str
    cierre: Cierre


# --------------------------------------------------------------------------- #
# n3_implementar                                                               #
# --------------------------------------------------------------------------- #


class ArchivoGenerado(Base):
    ruta: str = Field(min_length=3)
    lenguaje: Literal["typescript", "tsx", "sql", "json", "yaml", "md", "python"]
    contenido: str
    es_test: bool = False
    es_nuevo: bool = False


class CodigoGenerado(Base):
    """Salida de un agente de disciplina en `n3_implementar`."""

    ticket: str = "sin-ticket"
    agente: Disciplina
    ronda: int = Field(default=1, ge=1)
    archivos: list[ArchivoGenerado] = Field(min_length=1)
    notas: list[str] = Field(default_factory=list, max_length=5)
    supuestos: list[str] = Field(default_factory=list)
    toca_dominio: bool = Field(
        default=False,
        description="True si toca `domain/` o `services/`: CONVENCIONES_EQUIPO.md sección 2 "
        "no permite mergear sin tests.",
    )
    marca: Marca = Marca.SIN_CONTRASTAR

    @model_validator(mode="after")
    def _reglas(self) -> "CodigoGenerado":
        fallas = corre_los_guards(
            [(a.ruta, a.contenido) for a in self.archivos],
            rutas_nuevas=[a.ruta for a in self.archivos if a.es_nuevo],
        )
        if fallas:
            raise ValueError("frontera violada:\n  - " + "\n  - ".join(fallas))
        # `CONVENCIONES_EQUIPO.md` sección 2: no se mergea sin tests si toca domain/ o services/.
        if self.toca_dominio and not any(a.es_test for a in self.archivos):
            raise ValueError(
                "toca domain/ o services/ sin un test nuevo. CONVENCIONES_EQUIPO.md sección 2."
            )
        # `CONTEXT.md §7`: dominios exclusivos. Nadie edita un artefacto del que no es dueño.
        if self.agente in (Disciplina.ARCHITECT, Disciplina.NUTRITION, Disciplina.QA):
            raise ValueError(
                f"{self.agente.value} no implementa (CONTEXT.md §7): produce dictamen o veredicto."
            )
        return self

    @property
    def puede_mergear(self) -> bool:
        """Un ⚠️ o un supuesto abierto no llega a `main`."""
        return not self.supuestos and self.marca == Marca.VERIFICADO


# --------------------------------------------------------------------------- #
# n4_empaquetar_pr — determinista, no es un agente                             #
# --------------------------------------------------------------------------- #

#: Secciones obligatorias de la plantilla de PR (`CONVENCIONES_EQUIPO.md` sección 2).
SECCIONES_DE_PR: tuple[str, ...] = (
    "## Qué",
    "## Por qué",
    "## Cómo",
    "## Tests",
    "## Riesgos residuales",
    "## Checklist",
)

_COMANDOS_PROHIBIDOS = ("push --force", "push -f", "reset --hard origin", "checkout main")


class PaquetePR(Base):
    """`n4` es mecánica de git, no juicio de un agente.

    La rama sigue `tipo/descripcion-corta` (`CONVENCIONES_EQUIPO.md` sección 3) y la base es
    `main`: verificado el 2026-09-01, los tres repos están en `main` y no existe `develop`.
    """

    rama: str = Field(pattern=r"^[a-z]+/[a-z0-9][a-z0-9\-]*$")
    base: Literal["main"] = "main"
    titulo: str = Field(min_length=8, max_length=100)
    cuerpo_md: str
    commits: list[str] = Field(min_length=1)
    comandos_git: list[str] = Field(min_length=1)
    evidencia_adjunta: list[Evidencia] = Field(default_factory=list)
    condiciones: list[str] = Field(
        default_factory=list, description="De un veredicto aprobado-con-condiciones."
    )

    @model_validator(mode="after")
    def _reglas(self) -> "PaquetePR":
        if self.rama == "main" or self.rama.startswith("main/"):
            raise ValueError("nunca se trabaja directo sobre main (CONVENCIONES_EQUIPO.md § 3).")
        for c in self.comandos_git:
            bajo = c.lower()
            for prohibido in _COMANDOS_PROHIBIDOS:
                if prohibido in bajo:
                    raise ValueError(f"comando destructivo en el paquete de PR: {c!r}")
        faltan = [s for s in SECCIONES_DE_PR if s not in self.cuerpo_md]
        if faltan:
            raise ValueError(
                f"al cuerpo del PR le faltan secciones obligatorias: {faltan}. "
                f"CONVENCIONES_EQUIPO.md sección 2 la llama plantilla obligatoria."
            )
        for c in self.commits:
            if c.endswith("."):
                raise ValueError(f"asunto de commit con punto final: {c!r}")
        return self


# --------------------------------------------------------------------------- #
# n5_revisar — 04 qa, siempre en Opus                                          #
# --------------------------------------------------------------------------- #


class Hallazgo(Base):
    id: str = Field(pattern=r"^H-\d{2}$")
    categoria: Literal[
        "frontera", "umbral-transcripto", "contrato-cross-repo", "seguridad",
        "deuda-tecnica", "cobertura", "claridad", "error-silencioso",
    ]
    severidad: Severidad
    archivo: str
    descripcion: str = Field(min_length=15)
    correccion_sugerida: str = Field(min_length=10)
    vuelve_a: Disciplina = Disciplina.BACKEND

    @field_validator("archivo")
    @classmethod
    def _sin_linea(cls, v: str) -> str:
        if _NUMERO_DE_LINEA.search(v):
            raise ValueError(f"cita por número de línea: {v!r} (CONTEXT.md §9).")
        return v


class ReporteDeRevision(Base):
    """Salida de `n5_revisar`. Su veredicto rutea el grafo."""

    ticket: str = "sin-ticket"
    ronda: int = Field(default=1, ge=1)
    veredicto: Veredicto
    hallazgos: list[Hallazgo] = Field(default_factory=list)
    resumen: str = Field(min_length=20)

    @model_validator(mode="after")
    def _reglas(self) -> "ReporteDeRevision":
        bloqueantes = [h for h in self.hallazgos if h.severidad == Severidad.BLOQUEANTE]
        if self.veredicto in VEREDICTOS_QUE_AVANZAN and bloqueantes:
            raise ValueError(
                f"no se puede avanzar con {len(bloqueantes)} hallazgo(s) bloqueante(s). "
                f"QA es el único gate y no negocia."
            )
        if self.veredicto == Veredicto.RECHAZADO and not self.hallazgos:
            raise ValueError("rechazo sin hallazgos: no es accionable.")
        return self

    @property
    def severidad_max(self) -> Optional[Severidad]:
        orden = {Severidad.BLOQUEANTE: 3, Severidad.MAYOR: 2, Severidad.MENOR: 1}
        if not self.hallazgos:
            return None
        return max((h.severidad for h in self.hallazgos), key=lambda s: orden[s])


def rutea_revision(rev: ReporteDeRevision) -> str:
    """`PROPUESTA_grafo_fase2.md` sección 4: **veredicto primero, severidad después.**

    La cuarta condición es un agujero que PampaGrow tapó después de tenerlo: ruteando solo
    por severidad, una revisión **rechazada** cuyos hallazgos eran todos `menor` devolvía
    "continuar", la corrida cerraba en verde y el CLI salía 0. El gate de calidad se podía
    saltar sin que nadie lo notara.
    """
    if rev.veredicto in VEREDICTOS_QUE_AVANZAN:
        return "continuar"
    if rev.ronda >= TECHOS["revision"]:
        return "escalar"
    if rev.severidad_max == Severidad.BLOQUEANTE:
        return "recontratar"      # el contrato está mal → n2_contrato
    if rev.severidad_max == Severidad.MAYOR:
        return "reimplementar"    # la implementación está mal → n3_implementar
    return "reimplementar"        # rechazado sin bloqueantes ni mayores: igual no avanza


# --------------------------------------------------------------------------- #
# n6_resumen — la ÚNICA salida, también cuando la corrida no cierra            #
# --------------------------------------------------------------------------- #


class ResumenDeCorrida(Base):
    """Lo que una corrida dejó escrito, en un solo objeto.

    Existe porque "siempre" tiene que incluir el camino que no cierra: la corrida que
    escala es justamente la que MÁS necesita dejar algo escrito, porque alguien la va a
    levantar sin haber estado. Si escalar terminara en END, no dejaría nada.
    """

    ticket: str = "sin-ticket"
    thread_id: str = ""
    estado_final: str = "en-curso"
    que_se_pidio: str = ""
    decisiones_humanas: list[str] = Field(default_factory=list)
    archivos: list[str] = Field(default_factory=list)
    evidencia: list[Evidencia] = Field(default_factory=list)
    supuestos: list[str] = Field(default_factory=list)
    bloqueos: list[Bloqueo] = Field(default_factory=list)
    errores: list[str] = Field(default_factory=list)
    veredicto: Optional[Veredicto] = None
    proximos_pasos: list[str] = Field(default_factory=list)
    marca: Marca = Marca.SIN_CONTRASTAR

    @property
    def cerro_sola(self) -> bool:
        return self.estado_final == "cerrada" and not self.bloqueos and not self.supuestos

    @property
    def queda_algo_abierto(self) -> bool:
        return bool(self.supuestos or self.bloqueos or self.errores)


# --------------------------------------------------------------------------- #
# Estado del grafo                                                             #
# --------------------------------------------------------------------------- #


class EventoDeLog(Base):
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    nodo: str
    detalle: str
    marca: Marca = Marca.VERIFICADO


def _concat(a: list, b: list) -> list:
    return (a or []) + (b or [])


class EstadoDelPipeline(BaseModel):
    """Estado del grafo. Pydantic, no un dict suelto: el borde valida en cada transición."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    entrada: str
    ticket: str = "sin-ticket"

    analisis: Optional[AnalisisDeRequerimiento] = None
    respuestas_humanas: Annotated[list[RespuestaHumana], _concat] = Field(default_factory=list)
    aprobacion_humana: bool = False
    ronda_aclaracion: int = 0

    contrato: Optional[ContratoAprobado] = None
    # SIN reducer desde el 2026-09-19: son los chequeos del contrato VIGENTE. Con `_concat`
    # los de un contrato ya reemplazado seguían forzando el HitL 2 sobre el nuevo.
    incertidumbres: list[Incertidumbre] = Field(default_factory=list)
    ronda_contrato: int = 0
    respuestas_contrato: Annotated[list[RespuestaHumana], _concat] = Field(default_factory=list)
    modelo_contrato: str = ""
    decision_contrato: str = ""
    #: Hasta dónde corre. `contrato` corta después de `n2b` (el debut recomendado): `n3`/`n4`
    #: todavía no generan código real (dictamen H3/H4), así que seguir solo gastaría Opus
    #: revisando un stub.
    hasta: Literal["contrato", "completo"] = "contrato"
    cierres: Annotated[list[RegistroDeCierre], _concat] = Field(default_factory=list)

    entregas: Annotated[list[CodigoGenerado], _concat] = Field(default_factory=list)
    reportes: Annotated[list[Reporte], _concat] = Field(default_factory=list)

    paquete_pr: Optional[PaquetePR] = None

    revisiones: Annotated[list[ReporteDeRevision], _concat] = Field(default_factory=list)
    ronda_revision: int = 0

    resumen: Optional[ResumenDeCorrida] = None
    log: Annotated[list[EventoDeLog], _concat] = Field(default_factory=list)
    errores: Annotated[list[str], _concat] = Field(default_factory=list)
    estado_final: Literal[
        "en-curso", "cerrada", "escalada", "bloqueada", "abortada-por-techo",
        "abortada", "contrato-listo",
    ] = "en-curso"

    @property
    def ultima_revision(self) -> Optional[ReporteDeRevision]:
        return self.revisiones[-1] if self.revisiones else None

    @property
    def techo_alcanzado(self) -> Optional[str]:
        for loop, valor in (
            ("aclaracion", self.ronda_aclaracion),
            ("contrato", self.ronda_contrato),
            ("revision", self.ronda_revision),
        ):
            if valor >= TECHOS[loop]:
                return loop
        return None
