import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


import dataclasses

import pytest


@pytest.fixture
def repos_falsos(tmp_path, monkeypatch):
    """Los dos repos hermanos, mínimos, en un tmp. Desde el 2026-09-19 `det.puntero_sin_archivo`
    falla cerrado sin ellos, así que un test que quiera un contrato "limpio" los necesita —
    en vez de depender de que el repo real esté clonado (el test viejo pasaba vacuo en CI)."""
    from fitogenix import det

    server, native = tmp_path / "fitogenix-server", tmp_path / "fitogenix-native"
    (server / "src/domain/product/scoring").mkdir(parents=True)
    (server / "src/domain/product/scoring/constants.ts").write_text("export const TIERS = []\n")
    (native / "src/lib/contracts").mkdir(parents=True)
    (native / "src/lib/contracts/product.ts").write_text("export type X = 1\n")
    monkeypatch.setattr(det, "SETTINGS", dataclasses.replace(
        det.SETTINGS, server_path=server, native_path=native))
    return server, native
