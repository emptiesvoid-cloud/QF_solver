"""Contract tests for the G04 Code_Aster continuation deck."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_code_aster_arc_length_025.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("g04_code_aster_runner", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deck_uses_the_qf_physical_load_direction_and_apex_control() -> None:
    runner = _load_runner()

    deck = runner.command_text(reference_load_sign=-1.0, arc_length_end=0.96, arc_length_steps=160)

    assert 'FZ=-0.33333333333333331' in deck
    assert 'GROUP_NO="APEX"' in deck
    assert 'NOM_CMP=("DZ",)' in deck
    assert 'JUSQU_A=0.95999999999999996, NOMBRE=160' in deck


@pytest.mark.parametrize(
    "kwargs",
    [{"reference_load_sign": 0.0}, {"arc_length_end": 0.0}, {"arc_length_steps": 0}],
)
def test_deck_rejects_invalid_continuation_parameters(kwargs: dict[str, float | int]) -> None:
    runner = _load_runner()

    with pytest.raises(ValueError):
        runner.command_text(**kwargs)
