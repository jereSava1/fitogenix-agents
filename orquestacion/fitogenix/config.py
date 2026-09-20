"""Rutas y ruteo de modelo. Nada de esto vive hardcodeado en un prompt."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # opcional
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

AQUI = Path(__file__).resolve().parent
ORQ_ROOT = AQUI.parent
#: Raíz del repo de agentes. **Acá vive el SSOT**, a diferencia de PampaGrow, donde
#: los documentos están en un repo hermano. Por eso no hay `DOCS_ROOT`: la
#: indirección no compraba nada y era una variable más que podía apuntar mal.
AGENTES_ROOT = ORQ_ROOT.parent


def _ruta(env: str, default: str, *, ancla: Path) -> Path:
    """Resuelve contra un ANCLA fija, nunca contra el cwd.

    Si dependiera del directorio desde el que se corre, `--resume` no encontraría el
    thread al invocarlo desde otra carpeta — que es exactamente lo que el checkpointer
    en sqlite existe para resolver.
    """
    p = Path(os.getenv(env, default)).expanduser()
    if not p.is_absolute():
        p = ancla / p
    return p.resolve()


def _busca_repo(env: str, nombre: str) -> Path:
    """Dónde está un repo hermano. Se busca; no se adivina una sola ruta.

    Hasta el 2026-09-18 el default era `~/<nombre>` fijo. En esta máquina los repos
    cuelgan de `~/mnt/`, así que `verificar.py` no los encontraba y **salteaba en
    silencio 3 de sus 4 verificaciones** — imprimía un ⚠️ y salía 0. Un verificador que
    se saltea a sí mismo es peor que no tenerlo: da el verde igual.

    Orden: la variable de entorno gana siempre; después, el primer candidato que exista.
    """
    crudo = os.getenv(env)
    if crudo:
        return Path(crudo).expanduser().resolve()
    for base in (AGENTES_ROOT.parent, AGENTES_ROOT.parent.parent, Path.home()):
        cand = base / nombre
        if cand.exists():
            return cand.resolve()
    return (Path.home() / nombre).resolve()


@dataclass(frozen=True)
class Settings:
    agentes_root: Path = field(
        default_factory=lambda: _ruta("FITOGENIX_AGENTES_ROOT", str(AGENTES_ROOT), ancla=ORQ_ROOT)
    )
    #: Los dos repos de código son independientes y no se asume que compartan raíz
    #: (`CONTEXT.md §5.1`), así que la ubicación se busca en vez de fijarse.
    server_path: Path = field(
        default_factory=lambda: _busca_repo("FITOGENIX_SERVER_PATH", "fitogenix-server")
    )
    native_path: Path = field(
        default_factory=lambda: _busca_repo("FITOGENIX_NATIVE_PATH", "fitogenix-native")
    )
    #: sqlite por default: el diseño HitL asume reanudar **desde otra terminal**
    #: (`PROPUESTA_grafo_fase2.md` sección 2). `memory` es solo para tests.
    checkpointer: str = field(default_factory=lambda: os.getenv("FITOGENIX_CHECKPOINTER", "sqlite"))
    checkpoint_db: str = field(
        default_factory=lambda: str(
            _ruta("FITOGENIX_CHECKPOINT_DB", ".fitogenix/checkpoints.sqlite",
                  ancla=_ruta("FITOGENIX_AGENTES_ROOT", str(AGENTES_ROOT), ancla=ORQ_ROOT))
        )
    )
    state_dir: Path = field(
        default_factory=lambda: _ruta(
            "FITOGENIX_STATE_DIR", ".fitogenix",
            ancla=_ruta("FITOGENIX_AGENTES_ROOT", str(AGENTES_ROOT), ancla=ORQ_ROOT))
    )

    @property
    def dry_run(self) -> bool:
        """Se lee del entorno en cada llamada, **no se congela al importar**.

        `SETTINGS` se construye la primera vez que se importa este módulo, en un punto
        impredecible: `run.py` setea la variable desde `--dry-run` antes de sus propios
        imports, y un test la setea arriba del archivo. Como campo congelado, el import
        que llegara primero decidiría si todo el proceso llama a la API de verdad — así
        que agregar un archivo de test podía apagar el dry-run en silencio. Las rutas sí
        quedan congeladas; este flag no puede.
        """
        return os.getenv("FITOGENIX_DRY_RUN", "0") == "1"

    # --- estado local, no versionado ---
    @property
    def sessions_dir(self) -> Path:
        """Un `.md` por thread interrumpido o escalado: el handoff en disco."""
        return self.state_dir / "sessions"

    @property
    def summaries_dir(self) -> Path:
        """Un `.md` por corrida terminada, camino feliz y escalado por igual."""
        return self.state_dir / "summaries"

    # --- el SSOT, en este mismo repo ---
    #: El 2026-09-19 la raíz se ordenó en dos carpetas: los diez `.md` de agente
    #: pasaron a `agents/` y el resto de la documentación a `docs/`. Las rutas se
    #: componen desde acá, no se escriben sueltas: cuando la raíz se movió, este
    #: archivo y `verificar.py` fueron los dos únicos lugares que hubo que tocar.
    #: `CHANGELOG.md` y `nutricion/` NO se movieron.
    @property
    def docs_root(self) -> Path:
        return self.agentes_root / "docs"

    @property
    def prompts_root(self) -> Path:
        return self.agentes_root / "agents"

    @property
    def context_md(self) -> Path:
        return self.docs_root / "CONTEXT.md"

    @property
    def changelog_md(self) -> Path:
        return self.agentes_root / "CHANGELOG.md"

    @property
    def bitacora_md(self) -> Path:
        return self.docs_root / "BITACORA_DECISIONES.md"

    @property
    def nutricion_md(self) -> Path:
        return self.agentes_root / "nutricion" / "NUTRICION.md"

    @property
    def convenciones_md(self) -> Path:
        return self.docs_root / "CONVENCIONES_EQUIPO.md"

    def prompt_de(self, agente: str) -> Path:
        """El `.md` completo de un agente. `nutrition` → `agents/09-agente-nutricion.md`."""
        if agente not in PROMPTS:
            raise AgenteDesconocido(
                f"No hay prompt para el agente {agente!r}. "
                f"Conocidos: {', '.join(sorted(PROMPTS))}."
            )
        return self.prompts_root / PROMPTS[agente]


PROMPTS: dict[str, str] = {
    "orchestrator": "00-orquestador.md",
    "ux": "01-agente-ux.md",
    "mobile": "02-agente-frontend.md",
    "backend": "03-agente-backend.md",
    "qa": "04-agente-qa.md",
    "data-ai": "05-agente-datos.md",
    "etl": "06-agente-etl-data.md",
    "devops": "07-agente-devops.md",
    "architect": "08-agente-arquitecto.md",
    "nutrition": "09-agente-nutricion.md",
}

SETTINGS = Settings()

# --------------------------------------------------------------------------- #
# Ruteo de modelo — copiado de PROPUESTA_grafo_fase2.md sección 5, no inventado.
# Escalar a Opus es una CONDICIÓN, no una preferencia.
# --------------------------------------------------------------------------- #

MODELO_BASE = "claude-sonnet-5"
MODELO_COMPLEJO = "claude-opus-5"
MODELO_MECANICO = "claude-haiku-4-5-20251001"

RUTEO: dict[str, dict[str, str]] = {
    "orchestrator": {"base": MODELO_COMPLEJO, "mecanico": MODELO_BASE},
    "ux": {"base": MODELO_BASE, "mecanico": MODELO_MECANICO},
    "mobile": {"base": MODELO_BASE},
    "backend": {"base": MODELO_BASE, "escalado": MODELO_COMPLEJO},
    "qa": {"base": MODELO_BASE, "mecanico": MODELO_MECANICO},
    "data-ai": {"base": MODELO_BASE, "escalado": MODELO_COMPLEJO},
    "etl": {"base": MODELO_BASE, "mecanico": MODELO_MECANICO},
    "devops": {"base": MODELO_BASE, "escalado": MODELO_COMPLEJO},
    "architect": {"base": MODELO_BASE, "escalado": MODELO_COMPLEJO},
    # ⚠️ `nutrition` NO figura en la tabla de la sección 5: esa tabla se escribió el
    # 31/8, el mismo día que nació el agente, y quedó afuera. El valor de acá es una
    # propuesta —mismo par que sus pares de criterio, architect y data-ai— y está
    # **pendiente de ratificación del Orquestador**. Se pone explícito en vez de dejar
    # que `choose_model` tire `AgenteDesconocido` en la primera corrida real, pero no
    # se disfraza de decisión tomada.
    "nutrition": {"base": MODELO_BASE, "escalado": MODELO_COMPLEJO},
    # No es un agente: es el nodo `n5_revisar`. Último filtro antes de dar algo por
    # terminado, y **no se abarata nunca** (sección 5).
    "revisor": {"base": MODELO_COMPLEJO},
}


class AgenteDesconocido(KeyError):
    """Un agente que nadie ruteó. Mismo principio que `SeccionNoEncontrada`:
    el hueco no se rellena, se devuelve."""

    def __str__(self) -> str:  # KeyError entrecomilla el mensaje; acá no queremos eso
        return self.args[0]


def choose_model(agente: str, *, escalado: bool = False, mecanico: bool = False) -> str:
    """Sin default silencioso: caer a `MODELO_BASE` para un agente desconocido esconde
    un typo detrás de una corrida que parece sana y cuesta tokens reales en el modelo
    equivocado."""
    if agente not in RUTEO:
        raise AgenteDesconocido(
            f"No hay ruteo de modelo para el agente {agente!r}. "
            f"Conocidos: {', '.join(sorted(RUTEO))}. "
            "Agregalo a RUTEO o arreglá el llamador."
        )
    conf = RUTEO[agente]
    if mecanico and "mecanico" in conf:
        return conf["mecanico"]
    if escalado and "escalado" in conf:
        return conf["escalado"]
    return conf["base"]


# --- Condiciones de escalado: booleanas y verificables, no "cuando parezca difícil" ---

def escalar_backend(toca_scoring: bool, toca_auth: bool, toca_contrato: bool, toca_migracion: bool) -> bool:
    return toca_scoring or toca_auth or toca_contrato or toca_migracion


def escalar_datos(cambia_prompt: bool, cambia_modelo_o_params: bool) -> bool:
    return cambia_prompt or cambia_modelo_o_params


def escalar_devops(toca_secretos: bool, toca_despliegue: bool) -> bool:
    return toca_secretos or toca_despliegue


def escalar_arquitecto(toca_scoring: bool, toca_auth: bool, toca_migracion: bool) -> bool:
    """Sección 7: el arquitecto escala cuando el contrato toca el motor o auth/RLS."""
    return toca_scoring or toca_auth or toca_migracion
