"""Tests for the compact multi-route 026-G12 measurement runner."""

from __future__ import annotations

from scripts.benchmark_g12_route_matrix import _finite, _route_specs, _timings


def test_g12_final_campaign_declares_required_route_scope() -> None:
    specs = _route_specs()
    pairs = {(spec["route"], spec["family"]) for spec in specs}
    assert {("linear_static", family) for family in ("TET4", "TET10", "HEX8", "HEX20")} <= pairs
    assert {("modal", "TET4"), ("linear_buckling", "TET4")} <= pairs
    assert {("nonlinear_static", "TET4"), ("geometric_nonlinear_static", "TET4")} <= pairs
    assert ("nonlinear_static/contact_g09_bounded", "TET4") in pairs


def test_g12_final_campaign_finite_guard_rejects_nonfinite_values() -> None:
    assert _finite({"finite": [1.0, 2, True, None]})
    assert not _finite({"bad": float("nan")})
    assert not _finite({"bad": float("inf")})


def test_g12_final_campaign_extracts_route_timing_scopes() -> None:
    modal = {
        "assembly": {
            "stiffness": {
                "assembly_phase_seconds": {"assembly_plan": 1.0, "element_kernel": 2.0},
                "final_nnz": 12,
            }
        }
    }
    assembly, solve, nnz, scope = _timings("modal", modal)
    assert assembly == 3.0
    assert solve is None
    assert nnz == 12
    assert scope == "global_stiffness"
