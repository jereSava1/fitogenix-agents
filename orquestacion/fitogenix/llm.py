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

import copy
import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from pydantic import ValidationError, create_model

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

#: Salidas por llamada. **16.000 desde el 2026-09-20**, y con techo propio: en el debut, el
#: primer contrato real del arquitecto —4 briefs, 9 reglas, 7 campos, 6 puntas— se cortó
#: exactamente en 8.000, con todo escrito menos el cierre. "Entran holgados" era una
#: suposición mía, no una medición: un contrato de FTG-002 pesa más que eso.
MAX_TOKENS = 16_000
#: Tope duro al que puede llegar el reintento por truncado. Más que esto no es una salida
#: larga: es un nodo que está pidiendo demasiado de una sola vez.
TOPE_DE_SALIDA = 32_000


class SinCredencial(RuntimeError):
    """No hay API key y no estamos en `dry_run`. Se levanta al llamar, no al importar:
    importar este módulo tiene que seguir siendo gratis y sin efectos."""


class EsUnStub(RuntimeError):
    """Alguien intentó usar como real una respuesta de `dry_run`."""


class PresupuestoAgotado(RuntimeError):
    """La corrida pasó el techo de tokens. Corta acá, no en la factura."""


class EntregaInvalida(RuntimeError):
    """El modelo no produjo una entrega válida ni después del reintento con el error.

    Lleva la ruta de la traza cruda: lo que se pagó no se pierde, se puede leer.
    """


class SalidaTruncada(RuntimeError):
    """El modelo cortó por `max_tokens`. Un JSON a medias no se valida: se reporta."""


#: Reintentos cuando la entrega no valida, devolviéndole al modelo el `ValidationError`.
#: Uno alcanza para un campo mal escrito; si falla dos veces, el problema es el prompt o el
#: schema, y reintentar más solo lo esconde detrás de la factura.
REINTENTOS_DE_VALIDACION = 1

NOMBRE_DE_LA_TOOL = "entregar"

INSTRUCCION_DE_ENTREGA = f"""

---

## Cómo entregás (lo agrega el pipeline, vale para todos los agentes)

Entregás llamando **una sola vez** a la tool `{NOMBRE_DE_LA_TOOL}`. No escribas prosa fuera de
la tool. El objeto tiene dos partes:

- Un puntero por entrada de la lista: `["CONTEXT.md §3.1", "fitogenix-native/src/x.tsx → TIERS"]`.
  Nunca dos punteros pegados en una sola cadena con `·`, `+` o coma: no validan.
  Las cinco formas válidas, y no hay otras:
  `CONTEXT.md §3.1` · `NUTRICION.md §N5` · `BITACORA_DECISIONES.md ADR-007` ·
  `FTG-002.md sección Criterio de aceptación` (o el documento entero: `01-agente-ux.md`) ·
  `fitogenix-server/src/ruta.ts → simbolo` (nunca `archivo.ts:24`).
  `CONTEXT.md` y `NUTRICION.md` van SIEMPRE con su `§`: enteros no se citan.
- Una contradicción que el humano ya te resolvió viaja con su `resolucion` escrita, y deja
  de estar pendiente. Sin `resolucion` frena el contrato.
- `resultado`: tu salida, con exactamente los campos del schema. Si algo no lo sabés, va en
  `supuestos`, `decisiones_abiertas` o `preguntas_abiertas`, según el schema — nunca inventado.
- `cierre`: el resumen de tu entrega para el humano.
  - `resumen`: qué hiciste, en 1–3 frases concretas.
  - `cambios`: cada cambio o decisión, con `donde` como puntero (`CONTEXT.md §X` o
    `fitogenix-server/ruta.ts → simbolo`), nunca número de línea.
  - `validaciones`: cómo lo validaste. **No tenés tools para abrir archivos ni correr
    tests**: si solo citaste el SSOT, el método es `cita-al-ssot`; si no validaste, es
    `ninguna` con resultado `no-corrido`. No declares `origen`: lo pone el pipeline.
  - `revision_manual`: si alguna validación no pasó o no corrió, es `requerida=true`, con
    qué revisar, quién (`jere` o una disciplina) y por qué.
  - `proximo_paso`: la acción siguiente, su responsable y qué la bloquea.
  - `marca`: ⚠️ salvo que tengas algo mejor que decir. ✅ no te lo podés dar solo.
"""


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
    #: El `Cierre` de la entrega (solo en `llama_estructurado`). `Any` para no importar
    #: `schemas` acá: este módulo tiene que poder importarse sin efectos.
    cierre: Any = None
    traza: str = ""

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
    if isinstance(e, (TimeoutError, ConnectionError)):
        return True
    # `anthropic.APIConnectionError` / `APITimeoutError` no heredan de `ConnectionError` ni
    # traen `status_code`: sin esto, un timeout de red mataba la corrida al primer intento.
    try:
        from anthropic import APIConnectionError
    except Exception:  # pragma: no cover
        return False
    return isinstance(e, APIConnectionError)


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


@lru_cache(maxsize=32)
def entrega_de(modelo_pydantic: type["BaseModel"]) -> type["BaseModel"]:
    """El sobre de toda salida estructurada: `{resultado: <schema del nodo>, cierre: Cierre}`.

    Se arma por tipo y se cachea. El `Cierre` es uno solo para los diez agentes; por eso va
    en el sobre y no dentro de cada schema.
    """
    from .schemas import Base, Cierre

    return create_model(
        f"Entrega{modelo_pydantic.__name__}",
        __base__=Base,
        resultado=(modelo_pydantic, ...),
        cierre=(Cierre, ...),
    )


def esquema_para_tool(modelo_pydantic: type["BaseModel"]) -> dict[str, Any]:
    """El JSON Schema del sobre, con los `$ref` resueltos en línea.

    Se inlinea para no depender de cómo la API resuelve referencias, y se saca `origen` de
    `Validacion`: es un campo que solo escribe Python, y mostrárselo al modelo es invitarlo
    a declararlo.
    """
    raiz = entrega_de(modelo_pydantic).model_json_schema()
    defs = raiz.pop("$defs", {})
    for nombre, d in defs.items():
        if nombre == "Validacion":
            d.get("properties", {}).pop("origen", None)

    def resuelve(n: Any, pila: tuple[str, ...] = ()) -> Any:
        if isinstance(n, dict):
            if "$ref" in n:
                nombre = n["$ref"].rsplit("/", 1)[-1]
                if nombre in pila:  # pragma: no cover - hoy no hay schemas recursivos
                    raise ValueError(f"schema recursivo: {nombre}")
                base = copy.deepcopy(defs[nombre])
                extra = {k: v for k, v in n.items() if k != "$ref"}
                return resuelve({**base, **extra}, pila + (nombre,))
            return {k: resuelve(v, pila) for k, v in n.items()}
        if isinstance(n, list):
            return [resuelve(x, pila) for x in n]
        return n

    return resuelve(raiz)


def _escribe_traza(etiqueta: str, agente: str, intento: int, datos: dict[str, Any]) -> str:
    """Guarda la llamada cruda en `.fitogenix/llamadas/<ticket>/`. Best-effort.

    Lo que se pagó tiene que poder leerse: sin esto, una entrega que no valida se pierde
    con su texto y no hay cómo depurar el prompt.
    """
    try:
        carpeta = SETTINGS.state_dir / "llamadas" / (etiqueta or "sin-ticket")
        carpeta.mkdir(parents=True, exist_ok=True)
        sello = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        p = carpeta / f"{sello}-{agente}-{intento}.json"
        p.write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return str(p)
    except OSError:  # pragma: no cover - la traza nunca rompe una corrida
        return ""


def llama_estructurado(
    agente: str,
    modelo_pydantic: type["BaseModel"],
    *,
    sistema: str,
    usuario: str,
    stub: "BaseModel",
    stub_cierre: Any = None,
    escalado: bool = False,
    mecanico: bool = False,
    contador: Contador | None = None,
    max_tokens: int = MAX_TOKENS,
    traza: str = "",
    cliente: Any = None,
) -> tuple[Any, Respuesta]:
    """Una llamada cuya salida se valida contra un schema. **Salida estructurada, no texto.**

    El modelo entrega llamando a la tool `entregar`, forzada con `tool_choice`, cuyo
    `input_schema` es el sobre `{resultado, cierre}` generado desde Pydantic. Hasta el
    2026-09-19 el schema no viajaba en la llamada: el modelo tenía que adivinar los campos.

    Si la entrega no valida, se le devuelve el `ValidationError` como `tool_result` con
    `is_error` y se reintenta **una** vez (`REINTENTOS_DE_VALIDACION`). Si vuelve a fallar,
    `EntregaInvalida`, con la traza cruda en disco. Nunca se rellenan huecos con defaults.

    **El `stub` es obligatorio y es del que llama**: es lo que hace que el grafo entero
    corra en `dry_run`.
    """
    modelo_id = choose_model(agente, escalado=escalado, mecanico=mecanico)
    if SETTINGS.dry_run:
        if not isinstance(stub, modelo_pydantic):
            raise TypeError(
                f"el stub de {agente} es {type(stub).__name__} y el nodo declara "
                f"{modelo_pydantic.__name__}: el dry-run estaría probando otra cosa."
            )
        return stub, Respuesta(texto="", modelo=modelo_id, agente=agente, dry_run=True,
                               cierre=stub_cierre)

    from .schemas import Validacion

    cliente = cliente or _cliente()
    sobre = entrega_de(modelo_pydantic)
    tool = {
        "name": NOMBRE_DE_LA_TOOL,
        "description": f"Entrega la salida del nodo: `resultado` ({modelo_pydantic.__name__}) y `cierre`.",
        "input_schema": esquema_para_tool(modelo_pydantic),
    }
    sistema_completo = sistema + INSTRUCCION_DE_ENTREGA
    mensajes: list[dict[str, Any]] = [{"role": "user", "content": usuario}]
    huella = hashlib.sha256(sistema_completo.encode()).hexdigest()[:12]

    intento = 0
    reintentos_de_validacion = 0
    while True:
        intento += 1
        truncada = False

        def _pedir() -> Any:
            return cliente.messages.create(
                model=modelo_id, max_tokens=max_tokens, system=sistema_completo,
                messages=mensajes, tools=[tool],
                tool_choice={"type": "tool", "name": NOMBRE_DE_LA_TOOL},
            )

        try:
            msg, reintentos_red = _con_reintentos(_pedir)
        except Exception as e:  # noqa: BLE001
            # Si la API rechaza el techo de salida (cada modelo tiene el suyo), se baja una
            # vez y se sigue. Es la única forma de 400 que no es un bug nuestro.
            if "max_tokens" in str(e).lower() and max_tokens > MAX_TOKENS // 2:
                max_tokens = max(MAX_TOKENS // 2, max_tokens // 2)
                continue
            raise
        r = Respuesta(
            texto="", modelo=modelo_id, agente=agente,
            tokens_entrada=getattr(msg.usage, "input_tokens", 0),
            tokens_salida=getattr(msg.usage, "output_tokens", 0),
            intentos=reintentos_red,
        )
        bloque = next((b for b in msg.content if getattr(b, "type", "") == "tool_use"), None)
        crudo = getattr(bloque, "input", None)
        error = ""
        entrega = None
        if getattr(msg, "stop_reason", "") == "max_tokens":
            error = f"stop_reason=max_tokens con max_tokens={max_tokens}: la entrega llegó cortada"
            truncada = True
        elif bloque is None:
            error = "no llamó a la tool `entregar`"
        else:
            try:
                entrega = sobre.model_validate(crudo)
                if any(v.origen == "python" for v in entrega.cierre.validaciones):
                    entrega = None
                    error = "cierre.validaciones trae origen='python': ese campo lo escribe el pipeline"
            except ValidationError as e:
                error = str(e)

        r.traza = _escribe_traza(traza, agente, intento, {
            "agente": agente, "modelo": modelo_id, "intento": intento, "huella_sistema": huella,
            "usuario": usuario, "stop_reason": getattr(msg, "stop_reason", None),
            "tokens": [r.tokens_entrada, r.tokens_salida], "entrega_cruda": crudo, "error": error,
        })
        if contador is not None:
            contador.anota(r)
            contador.verifica_techo()

        if entrega is not None:
            # La única validación que es un hecho: la puso Python, después del modelo.
            entrega.cierre.validaciones.append(Validacion(
                metodo="schema", referencia=f"{modelo_pydantic.__name__} + Cierre (Pydantic)",
                resultado="pasa", origen="python"))
            r.cierre = entrega.cierre
            return entrega.resultado, r
        if truncada:
            # Un JSON cortado no se puede validar ni arreglar: se repite con más aire. Una
            # sola vez, y con techo — si 32k no alcanzan, el problema es el nodo, no el tope.
            if max_tokens < TOPE_DE_SALIDA:
                max_tokens = min(max_tokens * 2, TOPE_DE_SALIDA)
                continue
            raise SalidaTruncada(
                f"{agente}: {error} y el reintento con {TOPE_DE_SALIDA} tampoco entró. "
                f"El nodo está pidiendo demasiado de una sola vez. Traza: {r.traza}")
        reintentos_de_validacion += 1
        if reintentos_de_validacion > REINTENTOS_DE_VALIDACION:
            raise EntregaInvalida(f"{agente}: la entrega no valida tras {intento} intentos. "
                                  f"Último error: {error[:600]}. Traza: {r.traza}")
        mensajes.append({"role": "assistant",
                         "content": [b.model_dump(exclude_none=True) if hasattr(b, "model_dump") else b
                                     for b in msg.content]})
        if bloque is not None:
            mensajes.append({"role": "user", "content": [{
                "type": "tool_result", "tool_use_id": bloque.id, "is_error": True,
                "content": f"La entrega no valida:\n{error}\n\nCorregí y volvé a llamar a `{NOMBRE_DE_LA_TOOL}`.",
            }]})
        else:
            mensajes.append({"role": "user", "content": f"Tenés que entregar llamando a `{NOMBRE_DE_LA_TOOL}`."})


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
