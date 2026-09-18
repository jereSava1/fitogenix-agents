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
TECHOS: dict[str, int] = {"aclaracion": 3, "contrato": 1, "revision": 2}

FRASE_DE_INCERTIDUMBRE = (
    "No tengo información verificable suficiente para esto. Lo marco en vez de suponerlo."
)

# --------------------------------------------------------------------------- #
# Punteros — el SSOT se cita, no se copia                                      #
# --------------------------------------------------------------------------- #

_P_CONTEXT = re.compile(r"^CONTEXT\.md\s+§\d+(\.\d+)?$", re.IGNORECASE)
_P_NUTRICION = re.compile(r"^(?:nutricion/)?NUTRICION\.md\s+§N\d+$", re.IGNORECASE)
_P_BITACORA = re.compile(r"^BITACORA_DECISIONES\.md\s+ADR-\d{3}$", re.IGNORECASE)
_P_DOCUMENTO = re.compile(r"^[\w.\-/]+\.md\s+secci[oó]n\s+\d+(\.\d+)?$", re.IGNORECASE)
# Código: repo/ruta.ext, opcionalmente ` → simbolo`. Sin número de línea.
_P_CODIGO = re.compile(
    r"^fitogenix-(server|native)/[\w\-./]+\.\w+(\s*→\s*[\w.]+)?$"
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


class PunteroInvalido(ValueError):
    """El puntero no resuelve. El hueco no se rellena: se devuelve."""


def valida_puntero(p: str) -> str:
    """Un puntero es `CONTEXT.md §X`, `NUTRICION.md §Nx`, un ADR, una sección en prosa
    de otro documento, o una ruta de código con símbolo. Nada más.

    Rechaza el número de línea por la convención del 31/8/2026 (`CONTEXT.md §9`): se
    encontró `ENGINE_VERSION` citado como `ftgEngine.ts:24` cuando vive en
    `scoring/constants.ts:24` — archivo equivocado, número correcto, error invisible
    durante tres días. Un número de línea hace que una cita rota siga pareciendo sana.
    """
    if len(p) > LARGO_MAXIMO_DE_PUNTERO:
        raise PunteroInvalido(f"puntero demasiado largo, parece texto copiado: {p[:60]!r}...")
    if _NUMERO_DE_LINEA.search(p):
        raise PunteroInvalido(
            f"cita por número de línea: {p!r}. CONTEXT.md §9 (convención del 31/8/2026): "
            f"archivo + símbolo o cita textual, nunca número de línea."
        )
    if not any(rx.match(p) for rx in (_P_CONTEXT, _P_NUTRICION, _P_BITACORA, _P_DOCUMENTO, _P_CODIGO)):
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
        return valida_puntero(v)

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
        return valida_puntero(v) if v else v


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
        return valida_puntero(v) if v else v


class Contradiccion(Base):
    """Se reporta, nunca se elige en silencio. Es como se cerraron C-07 y C-14."""

    tema: str
    fuente_a: str
    fuente_b: str
    resuelve: Literal["jere", "orchestrator", "architect", "nutrition"] = "jere"


class RequisitoTrazado(Base):
    enunciado: str
    puntero: str
    marca: Marca

    @field_validator("puntero")
    @classmethod
    def _p(cls, v: str) -> str:
        return valida_puntero(v)


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

    @model_validator(mode="after")
    def _reglas(self) -> "AnalisisDeRequerimiento":
        if (self.preguntas_abiertas or self.contradicciones) and self.listo_para_contratar:
            raise ValueError(
                "listo_para_contratar=True con preguntas o contradicciones pendientes. "
                "Se escala, no se supone."
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
    return respuesta.aprobado and not analisis.preguntas_abiertas and not analisis.contradicciones


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
    """Cada regla del contrato cita su puntero. Sin puntero no es una regla: es una opinión."""

    enunciado: str = Field(min_length=10)
    puntero: str
    marca: Marca = Marca.SIN_CONTRASTAR

    @field_validator("puntero")
    @classmethod
    def _p(cls, v: str) -> str:
        return valida_puntero(v)


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
    """Qué pasa con una de las tres puntas. `cambia=False` también es una afirmación."""

    archivo: str
    cambia: bool
    detalle: str = Field(min_length=5)

    @field_validator("archivo")
    @classmethod
    def _es_punta(cls, v: str) -> str:
        if v not in PUNTOS_DEL_CONTRATO:
            raise ValueError(f"{v!r} no es una punta del contrato. Son: {PUNTOS_DEL_CONTRATO}")
        return v


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
        if self.puntas_tocadas:
            nombradas = {p.archivo for p in self.puntas_tocadas}
            faltan = set(PUNTOS_DEL_CONTRATO) - nombradas
            if faltan:
                raise ValueError(
                    f"el contrato toca el contrato de producto y no nombra {sorted(faltan)}. "
                    f"Las tres puntas se enumeran siempre, aunque en dos la respuesta sea "
                    f"'no cambia': 'no cambia' es verificable, el silencio no."
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
    ]
    detalle: str
    puntero: Optional[str] = None


def hay_que_preguntar(c: ContratoAprobado, det: list[Incertidumbre]) -> bool:
    """La condición de interrupción de `n2b_aclarar_contrato`: la UNIÓN de dos fuentes.

    Confiar en que el modelo declare su propia incertidumbre tiene una falla obvia:
    declarar menos incertidumbre es el camino más corto a no ser interrumpido. `det` no
    pasa por el modelo, y por eso el agujero queda tapado.
    """
    return bool(c.decisiones_abiertas) or bool(c.supuestos) or bool(det)


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
    incertidumbres: Annotated[list[Incertidumbre], _concat] = Field(default_factory=list)
    ronda_contrato: int = 0

    entregas: Annotated[list[CodigoGenerado], _concat] = Field(default_factory=list)
    reportes: Annotated[list[Reporte], _concat] = Field(default_factory=list)

    paquete_pr: Optional[PaquetePR] = None

    revisiones: Annotated[list[ReporteDeRevision], _concat] = Field(default_factory=list)
    ronda_revision: int = 0

    resumen: Optional[ResumenDeCorrida] = None
    log: Annotated[list[EventoDeLog], _concat] = Field(default_factory=list)
    errores: Annotated[list[str], _concat] = Field(default_factory=list)
    estado_final: Literal[
        "en-curso", "cerrada", "escalada", "bloqueada", "abortada-por-techo"
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
