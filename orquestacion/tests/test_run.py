"""El CLI: nada se aprueba por default, y una corrida que falla deja rastro (P0-3, H18)."""
import os
import subprocess
import sys
from pathlib import Path

RUN = Path(__file__).parent.parent / "run.py"


def _run(tmp_path, *args, env_extra=None):
    env = {**os.environ, "FITOGENIX_STATE_DIR": str(tmp_path / "st"),
           "FITOGENIX_CHECKPOINT_DB": str(tmp_path / "st" / "cp.sqlite"),
           "FITOGENIX_CHECKPOINTER": "sqlite", **(env_extra or {})}
    env.pop("ANTHROPIC_API_KEY", None)
    return subprocess.run([sys.executable, str(RUN), *args], capture_output=True, text=True, env=env)


def test_resume_sin_accion_es_un_error(tmp_path):
    r = _run(tmp_path, "--resume", "FTG-002", "--dry-run")
    assert r.returncode == 2 and "exige --accion" in r.stderr


def test_hasta_completo_fuera_de_dry_run_es_un_error(tmp_path):
    r = _run(tmp_path, "--ticket", "FTG-002", "--entrada", "x", "--hasta", "completo")
    assert r.returncode == 2 and "solo corre en dry-run" in r.stderr


def test_una_corrida_real_sin_credencial_no_arranca(tmp_path):
    """P0-8: el humo corre antes de gastar; sin credencial, corta con un mensaje, no un traceback."""
    r = _run(tmp_path, "--ticket", "FTG-002", "--entrada", "x")
    assert r.returncode == 1 and "ANTHROPIC_API_KEY" in r.stdout and "Traceback" not in r.stderr
    r = _run(tmp_path, "--humo")
    assert r.returncode == 1 and "ANTHROPIC_API_KEY" in r.stdout


def test_el_handoff_pide_accion_explicita_e_ids(tmp_path):
    r = _run(tmp_path, "--ticket", "FTG-002", "--entrada", "[test] pedido", "--dry-run")
    assert r.returncode == 2
    md = (tmp_path / "st" / "sessions" / "FTG-002.md").read_text()
    assert "--accion contratar" in md and '--respuesta "P1=' in md
    assert "python run.py --resume FTG-002\n" not in md


def test_una_corrida_que_falla_queda_en_la_lista(tmp_path):
    """Sin repos hermanos, el dry-run llega al HitL 2 por `repo-no-encontrado` (P0-6). Un
    resume con un ticket cuyo checkpoint no existe no puede fallar en silencio."""
    _run(tmp_path, "--ticket", "FTG-002", "--entrada", "[test]", "--dry-run")
    r = _run(tmp_path, "--resume", "FTG-002", "--accion", "contratar", "--dry-run",
             "--respuesta", "P1=alcance acotado")
    assert r.returncode == 2
    r = _run(tmp_path, "--resume", "FTG-002", "--accion", "contratar", "--dry-run")
    lista = _run(tmp_path, "--list").stdout
    assert "FTG-002" in lista, "mientras espera o falla, aparece en --list"
