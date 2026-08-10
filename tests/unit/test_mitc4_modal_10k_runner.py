from __future__ import annotations

from pathlib import Path

from scripts.build_mitc4_modal_10k_owner_review import _make_figures
from scripts.run_code_aster_mitc4_modal_10k_vnv import _parse_code_aster_frequencies


def test_code_aster_modal_frequency_fallback_parser(tmp_path: Path) -> None:
    log = tmp_path / "stdout.log"
    log.write_text(
        "frequence (HZ)\n"
        "1       5.74958E+00        5.7E-08\n"
        "2       3.59201E+01        5.4E-08\n"
        "3       9.37085E+01        1.0E-07\n"
        "4       1.02829E+02        3.9E-08\n",
        encoding="utf-8",
    )

    assert _parse_code_aster_frequencies(log) == [5.74958, 35.9201, 93.7085, 102.829]


def test_owner_review_figures_are_generated() -> None:
    figures = _make_figures()

    assert all(path.is_file() and path.stat().st_size > 0 for path in figures.values())
