"""
La llamada al modelo. **Lo único de este paquete que gasta plata.**

Tres decisiones que valen más que el código:

1. **Se puede correr el pipeline entero sin llamar a ningún modelo.** `dry_run` no es un
   modo de test: es cómo se verifica el grafo —nodos, bordes, techos, interrupciones—
   sin factura y sin API key. Un pipeline agéntico que solo se puede probar gastando se
   prueba poco.

2. **En `dry_run` el stub lo declara quien llama, no este módulo.** Podría inventar un
   objeto mínimo por reflexión sobre el schema, y sería peor: cada nodo tiene que poder
   decir, explícito y a la vista, cómo es su salida más chica válida. Si esa salida no se
   puede escribir en tres líneas, el contrato del nodo está mal.

3. **Un stub nunca puede pasar por salida real.** `Respuesta.dry_run` viaja con el
   resultado y `EsUnStub` se levanta si alguien intenta cerrar una corrida con uno. La
   alternativa —confiar en que nadie se confunda— es exactamente el tipo de cosa que en
   este proyecto ya falló una vez.

Los reintentos son solo para fallas transitorias. Un 400 significa que la request está
mal armada, y reintentarla esconde el bug detrás de un delay.
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from .config import SETTINGS, choose_model

if TYPE_CHECKING:  # pragma: no cover - solo para tipar
    from pydantic import BaseModel

T = TypeVar("T")

#: Reintentos de una llamada. No es un techo de loop del grafo (eso es `TECHOS`): es
#: resiliencia de red. Tres alcanzan para un 429 o un 529 pasajero; más que eso ya no es
#: un pico, es un problema que hay que ver.
REINTENTOS = 3
#: Espera base en segundos. Crece exponencial y con jitter, para no sincronizar
#: reintentos si algún día hay más de un agente en paralelo.
ESPERA_BASE = 1.5

#: Techo de tokens de salida por corrida. Los techos de loop de `schemas.TECHOS` acotan
#: cuántas veces se repite un paso; esto acota el gasto total aunque ningún loop se pase.
#: Son dos fallas distintas: un prompt que devuelve de más no itera, y no lo frena ningún
#: techo de iteración.
TECHO_DE_TOKENS_POR_CORRIDA = int(os.getenv("FITOGENIX_TECHO_TOKENS", "400000"))

#: Salidas por llamada. Un contrato o un reporte largo entran holgados acá; si algo lo
#: necesita más alto, es señal de que el Brief está pidiendo demasiado de una sola vez.
MAX_TOKENS = 8_000


class SinCredencial(RuntimeError):
    """No hay API key y no estamos en `dry_run`. Se levanta al llamar, no al importar:
    importar este módulo tiene que seguir siendo gratis y sin efectos."""


class EsUnStub(RuntimeError):
    """Alguien intentó usar como real una respuesta de `dry_run`."""


class PresupuestoAgotado(RuntimeError):
    """La corrida pasó el techo de tokens. Corta acá, no en la factura."""


@dataclass
class Respuesta:
    """Lo que devuelve una llamada. `dry_run` viaja adentro a propósito."""

    texto: str
    modelo: str
    agente: str
    tokens_entrada: int = 0
    tokens_salida: int = 0
    intentos: int = 1
    dry_run: bool = False

    def exigir_real(self) -> "Respuesta":
        """Para los puntos donde una corrida se da por terminada."""
        if self.dry_run:
            raise EsUnStub(
                f"respuesta de {self.agente} generada en dry-run: no se cierra una corrida "
                f"con un stub. Sacá FITOGENIX_DRY_RUN o no llames a esto."
            )
        return self


@dataclass
class Contador:
    """El libro de la corrida. `n6_resumen` lo lee para informar el costo medido en vez
    de estimarlo — que es la diferencia entre un número y una sensación."""

    llamadas: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    por_agente: dict[str, int] = field(default_factory=dict)
    por_modelo: dict[str, int] = field(default_factory=dict)

    def anota(self, r: Respuesta) -> None:
        self.llamadas += 1
        self.tokens_entrada += r.tokens_entrada
        self.tokens_salida += r.tokens_salida
        self.por_agente[r.agente] = self.por_agente.get(r.agente, 0) + r.tokens_salida
        self.por_modelo[r.modelo] = self.por_modelo.get(r.modelo, 0) + r.tokens_salida

    @property
    def tokens(self) -> int:
        return self.tokens_entrada + self.tokens_salida

    def verifica_techo(self) -> None:
        if self.tokens_salida > TECHO_DE_TOKENS_POR_CORRIDA:
            raise PresupuestoAgotado(
                f"{self.tokens_salida} tokens de salida en {self.llamadas} llamadas, "
                f"techo {TECHO_DE_TOKENS_POR_CORRIDA}. Por agente: {self.por_agente}"
            )


def _cliente() -> Any:
    """Se construye al primer uso. Importar `llm` no puede exigir credencial."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SinCredencial(
            "falta ANTHROPIC_API_KEY. Para correr el grafo sin modelo: FITOGENIX_DRY_RUN=1"
        )
    from anthropic import Anthropic

    # `max_retries=0`: los reintentos los maneja `_con_reintentos`, que distingue lo
    # transitorio de lo que es un bug nuestro. Dos capas de retry esconden la segunda.
    return Anthropic(max_retries=0)


def _es_transitorio(e: Exception) -> bool:
    """Solo se reintenta lo que puede salir distinto la próxima vez."""
    codigo = getattr(e, "status_code", None)
    if codigo in (408, 409, 429, 500, 502, 503, 504, 529):
        return True
    if codigo is not None:  # un 4xx que no está arriba es una request mal armada
        return False
    return isinstance(e, (TimeoutError, ConnectionError))


def _con_reintentos(fn: Callable[[], T], *, dormir: Callable[[float], None] = time.sleep) -> tuple[T, int]:
    ultima: Exception | None = None
    for intento in range(1, REINTENTOS + 1):
        try:
            return fn(), intento
        except Exception as e:  # noqa: BLE001 - se reclasifica abajo
            if not _es_transitorio(e) or intento == REINTENTOS:
                raise
            ultima = e
            dormir(ESPERA_BASE * (2 ** (intento - 1)) * (0.5 + random.random()))
    raise ultima  # pragma: no cover - inalcanzable; el for sale por return o raise


def llama(
    agente: str,
    *,
    sistema: str,
    usuario: str,
    escalado: bool = False,
    mecanico: bool = False,
    stub: str = "",
    contador: Contador | None = None,
    max_tokens: int = MAX_TOKENS,
) -> Respuesta:
    """Una llamada. El modelo sale de `RUTEO`, no del que llama.

    `escalado` y `mecanico` son las dos palancas de `PROPUESTA_grafo_fase2.md` sección 5.
    Que el modelo lo elija `choose_model` y no el nodo es lo que hace auditable el ruteo:
    si un agente termina en un modelo caro, está escrito en un solo lugar por qué.
    """
    modelo = choose_model(agente, escalado=escalado, mecanico=mecanico)

    if SETTINGS.dry_run:
        return Respuesta(
            texto=stub or f"[dry-run · {agente} · {modelo}]",
            modelo=modelo, agente=agente, dry_run=True,
        )

    cliente = _cliente()

    def _pedir() -> Any:
        return cliente.messages.create(
            model=modelo,
            max_tokens=max_tokens,
            system=sistema,
            messages=[{"role": "user", "content": usuario}],
        )

    msg, intentos = _con_reintentos(_pedir)
    r = Respuesta(
        texto="".join(b.text for b in msg.content if getattr(b, "type", "") == "text"),
        modelo=modelo,
        agente=agente,
        tokens_entrada=getattr(msg.usage, "input_tokens", 0),
        tokens_salida=getattr(msg.usage, "output_tokens", 0),
        intentos=intentos,
    )
    if contador is not None:
        contador.anota(r)
        contador.verifica_techo()
    return r


def llama_estructurado(
    agente: str,
    modelo_pydantic: type["BaseModel"],
    *,
    sistema: str,
    usuario: str,
    stub: "BaseModel",
    escalado: bool = False,
    mecanico: bool = False,
    contador: Contador | None = None,
    max_tokens: int = MAX_TOKENS,
) -> tuple[Any, Respuesta]:
    """Igual que `llama`, pero el texto se valida contra un schema antes de volver.

    **El `stub` es obligatorio y es del que llama.** Es la salida mínima válida de ese
    nodo, escrita a mano, y es lo que hace que el grafo entero corra en `dry_run`.
    Pedirlo obliga a que cada nodo sepa decir cómo es su salida más chica — y un nodo que
    no lo sabe tiene el contrato mal puesto, que es mejor descubrirlo acá que en la
    primera corrida paga.
    """
    if SETTINGS.dry_run:
        if not isinstance(stub, modelo_pydantic):
            raise TypeError(
                f"el stub de {agente} es {type(stub).__name__} y el nodo declara "
                f"{modelo_pydantic.__name__}: el dry-run estaría probando otra cosa."
            )
        return stub, Respuesta(texto="", modelo=choose_model(agente, escalado=escalado,
                                                             mecanico=mecanico),
                               agente=agente, dry_run=True)

    r = llama(agente, sistema=sistema, usuario=usuario, escalado=escalado,
              mecanico=mecanico, contador=contador, max_tokens=max_tokens)
    # `model_validate_json` levanta `ValidationError`, y eso es lo correcto: el hueco no
    # se rellena con defaults, se devuelve. Quien llama decide si reintenta con el error
    # en el prompt o si corta — y esa decisión es del grafo, no de este módulo.
    return modelo_pydantic.model_validate_json(_solo_json(r.texto)), r


def _solo_json(texto: str) -> str:
    """Recorta el JSON de una respuesta que vino envuelta en prosa o en un bloque.

    No 'arregla' JSON roto: si adentro del bloque hay algo inválido, que falle la
    validación. Esto solo saca el envoltorio.
    """
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    i, j = t.find("{"), t.rfind("}")
    return t[i : j + 1] if 0 <= i < j else t
