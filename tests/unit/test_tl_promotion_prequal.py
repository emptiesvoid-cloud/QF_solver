"""Contract checks for the independent TL promotion-prequalification corpus."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from run_tl_promotion_prequal import (  # noqa: E402
    FAMILIES,
    HOLDOUT_CASES,
    INCREMENT_CASES,
    INCREMENT_LEVELS,
    MESH_LEVELS,
    PRIMARY_CASES,
)


def test_independent_corpus_has_required_dimensions() -> None:
    definitions = PRIMARY_CASES + INCREMENT_CASES + HOLDOUT_CASES
    assert {item["family"] for item in definitions} == set(FAMILIES)
    assert {item["cells"] for item in PRIMARY_CASES} == set(MESH_LEVELS)
    assert {item["increments"] for item in INCREMENT_CASES} == set(INCREMENT_LEVELS)
    assert all(item["group"] == "holdout" for item in HOLDOUT_CASES)


def test_corpus_ids_are_unique_and_explicitly_new() -> None:
    definitions = PRIMARY_CASES + INCREMENT_CASES + HOLDOUT_CASES
    ids = [item["id"] for item in definitions]
    assert len(ids) == len(set(ids))
    assert all(item.startswith("TL-PQ-") for item in ids)
    assert all("rescue" not in item.lower() for item in ids)


def test_campaign_does_not_enable_rescue_controls() -> None:
    definitions = PRIMARY_CASES + INCREMENT_CASES + HOLDOUT_CASES
    assert all(item["increments"] >= 8 for item in definitions)
    assert all("bounded_growth" not in item for item in definitions)
