"""Non-FEM tests for declared source provenance through reduced public routes."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from solveur.core.analyses import reduced_harmonic
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.errors import InputValidationError
from solveur.core.router import AnalysisRouter


def test_resolve_source_sha_marks_explicit_value_as_caller_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QF_SOURCE_SHA", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(reduced_harmonic, "_clean_checkout_sha", lambda: None)

    value, origin = reduced_harmonic._resolve_source_sha_with_origin("A" * 40)

    assert value == "a" * 40
    assert origin == "CALLER_DECLARED"
    assert reduced_harmonic._source_sha_availability(origin) == "DECLARED_BY_CALLER_UNVERIFIED"


def test_resolve_source_sha_marks_environment_value_as_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QF_SOURCE_SHA", "B" * 40)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(reduced_harmonic, "_clean_checkout_sha", lambda: None)

    value, origin = reduced_harmonic._resolve_source_sha_with_origin(None)

    assert value == "b" * 40
    assert origin == "ENVIRONMENT_DECLARED"
    assert reduced_harmonic._source_sha_availability(origin) == "DECLARED_BY_ENVIRONMENT_UNVERIFIED"


def test_checkout_revision_is_reported_without_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QF_SOURCE_SHA", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(reduced_harmonic, "_clean_checkout_sha", lambda: "f" * 40)

    value, origin = reduced_harmonic._resolve_source_sha_with_origin(None)

    assert value == "f" * 40
    assert origin == "CHECKOUT_REPORTED_UNVERIFIED"
    assert (
        reduced_harmonic._source_sha_availability(origin)
        == "CHECKOUT_REVISION_REPORTED_UNVERIFIED"
    )


def test_prepared_system_without_origin_is_explicitly_unknown() -> None:
    assert reduced_harmonic._source_sha_availability("PREPARED_SYSTEM_ORIGIN_UNKNOWN") == "ORIGIN_UNKNOWN"


def test_clean_checkout_lookup_fails_closed_if_module_is_outside_git_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_file = Path(reduced_harmonic.__file__).resolve()
    unrelated_root = source_file.parent / "not-the-containing-repository"
    monkeypatch.setattr(
        reduced_harmonic.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=str(unrelated_root)),
    )

    assert reduced_harmonic._clean_checkout_sha() is None


@pytest.mark.parametrize(
    ("analysis_type", "method", "solver_module", "solver_name"),
    [
        (
            "harmonic_response",
            "modal_superposition",
            "solveur.core.analyses.reduced_harmonic",
            "ReducedHarmonicResponseSolver",
        ),
        (
            "transient_dynamic",
            "modal_newmark",
            "solveur.core.analyses.modal_newmark",
            "ModalNewmarkTransientSolver",
        ),
    ],
)
def test_router_forwards_source_sha_only_to_reduced_routes(
    monkeypatch: pytest.MonkeyPatch,
    analysis_type: str,
    method: str,
    solver_module: str,
    solver_name: str,
) -> None:
    import importlib

    calls: list[str | None] = []

    class FakeSolver:
        def solve(self, model: object, *, source_sha: str | None = None) -> str:
            calls.append(source_sha)
            return "routed"

    monkeypatch.setattr(
        "solveur.core.router.preflight_model",
        lambda _model: SimpleNamespace(raise_for_error=lambda: None),
    )
    monkeypatch.setattr(importlib.import_module(solver_module), solver_name, FakeSolver)
    model = SimpleNamespace(
        analysis=AnalysisSettings(type=analysis_type, method=method),
        concentrated_masses=[],
    )

    result = AnalysisRouter().solve(model, source_sha="c" * 40)  # type: ignore[arg-type]

    assert result == "routed"
    assert calls == ["c" * 40]


def test_public_solve_model_forwards_source_sha_without_running_solver(monkeypatch: pytest.MonkeyPatch) -> None:
    from solveur.api import public

    observed: dict[str, object] = {}

    class FakeRouter:
        def solve(self, model: object, *, telemetry: object = None, source_sha: str | None = None) -> object:
            observed.update(model=model, telemetry=telemetry, source_sha=source_sha)
            return "result"

    monkeypatch.setattr(public, "AnalysisRouter", FakeRouter)
    monkeypatch.setattr(public, "enforce_qualification_policy", lambda result, _model: result)
    model = object()

    result = public.solve_model(model, source_sha="d" * 40)  # type: ignore[arg-type]

    assert result == "result"
    assert observed == {"model": model, "telemetry": None, "source_sha": "d" * 40}


def test_router_rejects_source_sha_for_routes_without_provenance_support() -> None:
    model = SimpleNamespace(
        analysis=AnalysisSettings(type="linear_static", method="direct"),
        concentrated_masses=[],
    )

    with pytest.raises(InputValidationError, match="accepted only for"):
        AnalysisRouter()._solve(model, source_sha="e" * 40)  # type: ignore[arg-type]


def test_source_sha_validation_rejects_non_full_or_non_hex_values() -> None:
    with pytest.raises(InputValidationError, match="full 40- or 64-character hexadecimal"):
        reduced_harmonic._resolve_source_sha_with_origin("not-a-git-sha")
