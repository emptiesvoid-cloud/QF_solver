"""Validated inertia and first-root brackets for captured G08 binary64 pencils.

The certificate treats every stored float64 coefficient and endpoint as the
exact real number represented by that binary64 value. It does not bound FEM
assembly or modeling error.
"""

from __future__ import annotations

from contextlib import contextmanager
import importlib.metadata
import hashlib
import json
import math
import platform
from pathlib import Path
import time
from typing import Any, Iterator

import numpy as np
from scipy.linalg import eigh


class VerifiedInertiaInputError(ValueError):
    """Input is malformed or differs from the archived matrix contract."""


class VerifiedInertiaBackendUnavailable(RuntimeError):
    """The optional interval arithmetic backend is missing."""


MAX_DIMENSION = 400
DEFAULT_PRECISION_BITS = 128
MAX_CERTIFICATE_SECONDS = 120.0
MAX_PRECISION_BITS = 512
MAX_ROOT_REFINEMENT_STEPS = 16


def _validate_precision(precision_bits: int) -> None:
    if isinstance(precision_bits, bool) or not isinstance(precision_bits, int):
        raise VerifiedInertiaInputError("precision_bits must be an integer")
    if not 64 <= precision_bits <= MAX_PRECISION_BITS:
        raise VerifiedInertiaInputError(f"precision_bits must be between 64 and {MAX_PRECISION_BITS}")


@contextmanager
def _flint_precision(precision_bits: int) -> Iterator[tuple[Any, Any, Any]]:
    try:
        from flint import arb, arb_mat, ctx
    except ImportError as exc:
        raise VerifiedInertiaBackendUnavailable(
            "python-flint is unavailable; no verified interval result can be produced"
        ) from exc
    old_precision = int(ctx.prec)
    ctx.prec = int(precision_bits)
    try:
        yield arb, arb_mat, ctx
    finally:
        ctx.prec = old_precision


def _validated_symmetric(matrix: Any, name: str) -> np.ndarray:
    value = np.asarray(matrix, dtype=np.float64)
    if (
        value.ndim != 2
        or value.shape[0] == 0
        or value.shape[0] != value.shape[1]
        or value.shape[0] > MAX_DIMENSION
        or not np.isfinite(value).all()
    ):
        raise VerifiedInertiaInputError(f"{name} must be a finite, nonempty square matrix of size <= {MAX_DIMENSION}")
    if not np.array_equal(value, value.T):
        raise VerifiedInertiaInputError(f"{name} is not exactly symmetric in its stored binary64 representation")
    return value


def _arb_matrix(arb_mat: Any, matrix: np.ndarray) -> Any:
    return arb_mat(matrix.tolist())


def _row_sum_abs_bounds(matrix: Any, arb: Any) -> list[Any]:
    bounds = []
    for row_index in range(matrix.nrows()):
        row_sum = arb(0)
        for column_index in range(matrix.ncols()):
            row_sum += matrix[row_index, column_index].abs_upper()
        bounds.append(row_sum)
    return bounds


def _strictly_below_one(bounds: list[Any]) -> bool:
    return bool(bounds) and all(bool(bound < 1) for bound in bounds)


def _largest_upper_bound(bounds: list[Any]) -> str | None:
    upper_bounds = [bound.abs_upper() for bound in bounds]
    if not upper_bounds:
        return None
    largest = upper_bounds[0]
    for candidate in upper_bounds[1:]:
        if bool(candidate > largest):
            largest = candidate
    return str(largest)


def _certify_ball_inertia(ball_matrix: Any, approximate: np.ndarray, precision_bits: int) -> dict[str, Any]:
    started = time.perf_counter()
    with _flint_precision(precision_bits) as (arb, arb_mat, _ctx):
        value = np.asarray(approximate, dtype=np.float64)
        if (
            value.ndim != 2
            or value.shape[0] == 0
            or value.shape[0] != value.shape[1]
            or not np.isfinite(value).all()
            or not np.array_equal(value, value.T)
        ):
            return {"status": "INDETERMINATE_APPROXIMATION_INVALID", "precision_bits": precision_bits}
        n = value.shape[0]
        if ball_matrix.nrows() != n or ball_matrix.ncols() != n:
            return {"status": "INDETERMINATE_INTERVAL_DIMENSION_MISMATCH", "precision_bits": precision_bits}
        try:
            approximate_eigenvalues, vectors = eigh(value, check_finite=True, driver="evd")
        except np.linalg.LinAlgError:
            return {"status": "INDETERMINATE_FLOATING_EIGENSOLVE_FAILED", "precision_bits": precision_bits}
        if not np.isfinite(approximate_eigenvalues).all() or np.any(approximate_eigenvalues == 0.0):
            return {"status": "INDETERMINATE_APPROXIMATE_DIAGONAL_HAS_ZERO", "precision_bits": precision_bits}

        basis = _arb_matrix(arb_mat, vectors)
        basis_t = basis.transpose()
        identity_rows = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
        identity = arb_mat(identity_rows)

        gram_error = basis_t * basis - identity
        orthogonality_bounds = _row_sum_abs_bounds(gram_error, arb)
        if not _strictly_below_one(orthogonality_bounds):
            return {
                "status": "INDETERMINATE_BASIS_INVERTIBILITY_BOUND",
                "precision_bits": precision_bits,
                "orthogonality_rows_below_one": sum(bool(bound < 1) for bound in orthogonality_bounds),
                "orthogonality_max_row_sum_upper_bound": _largest_upper_bound(orthogonality_bounds),
                "dimension": n,
                "elapsed_seconds": time.perf_counter() - started,
            }

        diagonal = arb_mat(
            [[float(approximate_eigenvalues[i]) if i == j else 0.0 for j in range(n)] for i in range(n)]
        )
        transformed = basis_t * ball_matrix * basis
        error = transformed - diagonal
        inverse_sqrt_diagonal = [1 / arb(abs(float(item))).sqrt() for item in approximate_eigenvalues]

        scaled_row_bounds = []
        for i in range(n):
            row_sum = arb(0)
            for j in range(n):
                entry = error[i, j] * inverse_sqrt_diagonal[i] * inverse_sqrt_diagonal[j]
                row_sum += entry.abs_upper()
            scaled_row_bounds.append(row_sum)
        elapsed = time.perf_counter() - started
        all_scaled_rows_below_one = _strictly_below_one(scaled_row_bounds)
        if elapsed > MAX_CERTIFICATE_SECONDS:
            return {
                "status": "INDETERMINATE_BUDGET_EXCEEDED",
                "precision_bits": precision_bits,
                "dimension": n,
                "elapsed_seconds": elapsed,
                "budget_seconds": MAX_CERTIFICATE_SECONDS,
            }
        if not all_scaled_rows_below_one:
            return {
                "status": "INDETERMINATE_SCALED_RESIDUAL_BOUND",
                "precision_bits": precision_bits,
                "dimension": n,
                "orthogonality_rows_below_one": n,
                "scaled_residual_rows_below_one": sum(bool(bound < 1) for bound in scaled_row_bounds),
                "orthogonality_max_row_sum_upper_bound": _largest_upper_bound(orthogonality_bounds),
                "scaled_residual_max_row_sum_upper_bound": _largest_upper_bound(scaled_row_bounds),
                "elapsed_seconds": elapsed,
            }

        negative = int(np.count_nonzero(approximate_eigenvalues < 0.0))
        positive = int(np.count_nonzero(approximate_eigenvalues > 0.0))
        return {
            "status": "CERTIFIED",
            "dimension": n,
            "inertia": {"negative": negative, "zero": 0, "positive": positive},
            "precision_bits": precision_bits,
            "basis_invertibility": "CERTIFIED_BY ||I - V.T V||_infinity < 1",
            "inertia_stability": "CERTIFIED_BY ||D^-1/2 (V.T A V - D) D^-1/2||_infinity < 1",
            "orthogonality_rows_below_one": n,
            "scaled_residual_rows_below_one": n,
            "orthogonality_max_row_sum_upper_bound": _largest_upper_bound(orthogonality_bounds),
            "scaled_residual_max_row_sum_upper_bound": _largest_upper_bound(scaled_row_bounds),
            "elapsed_seconds": elapsed,
            "flint_version": importlib.metadata.version("python-flint"),
        }


def certify_symmetric_inertia(matrix: Any, *, precision_bits: int = DEFAULT_PRECISION_BITS) -> dict[str, Any]:
    """Certify inertia using an approximate eigenbasis and Arb norm bounds.

    The approximate binary64 eigenvectors are treated as exact basis entries.
    Arb encloses V.T @ A @ V. If V is certified nonsingular and the scaled
    residual has infinity norm below one, a symmetric homotopy proves that
    V.T @ A @ V has the inertia of the approximate diagonal D.
    """
    value = _validated_symmetric(matrix, "matrix")
    _validate_precision(precision_bits)
    try:
        with _flint_precision(precision_bits) as (arb, arb_mat, _ctx):
            return _certify_ball_inertia(_arb_matrix(arb_mat, value), value, precision_bits)
    except VerifiedInertiaBackendUnavailable as exc:
        return {"status": "INDETERMINATE_BACKEND_UNAVAILABLE", "reason": str(exc), "precision_bits": precision_bits}


def certify_pencil_inertia(
    k0: Any,
    kg: Any,
    load_factor: float,
    *,
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> dict[str, Any]:
    """Certify inertia of the exact binary64-input expression K0 + lambda Kg."""
    initial = _validated_symmetric(k0, "K0")
    geometric = _validated_symmetric(kg, "Kg")
    factor = float(load_factor)
    if initial.shape != geometric.shape:
        raise VerifiedInertiaInputError("K0 and Kg dimensions differ")
    if not math.isfinite(factor) or factor < 0.0:
        raise VerifiedInertiaInputError("load_factor must be finite and nonnegative")
    _validate_precision(precision_bits)
    approximate = initial + factor * geometric
    if not np.isfinite(approximate).all() or not np.array_equal(approximate, approximate.T):
        return {"status": "INDETERMINATE_FLOATING_PENCIL_ASSEMBLY", "precision_bits": precision_bits}
    try:
        with _flint_precision(precision_bits) as (arb, arb_mat, _ctx):
            k0_ball = _arb_matrix(arb_mat, initial)
            kg_ball = _arb_matrix(arb_mat, geometric)
            factor_ball = arb(factor)
            ball_pencil = k0_ball + kg_ball * factor_ball
            if not factor_ball.rad().is_zero():
                return {"status": "INDETERMINATE_FACTOR_NOT_EXACTLY_ENCLOSED", "precision_bits": precision_bits}
            result = _certify_ball_inertia(ball_pencil, approximate, precision_bits)
    except VerifiedInertiaBackendUnavailable as exc:
        return {"status": "INDETERMINATE_BACKEND_UNAVAILABLE", "reason": str(exc), "precision_bits": precision_bits}
    result["load_factor_binary64"] = factor
    result["pencil_convention"] = "Q(lambda) = K0 + lambda * Kg"
    return result


def refine_certified_root_bracket(
    k0: Any,
    kg: Any,
    lower: float,
    upper: float,
    *,
    precision_bits: int = DEFAULT_PRECISION_BITS,
    max_steps: int = MAX_ROOT_REFINEMENT_STEPS,
    started_at: float | None = None,
) -> dict[str, Any]:
    """Bisect a certified 0-to-1 inertia bracket without trusting a candidate value."""
    initial = _validated_symmetric(k0, "K0")
    geometric = _validated_symmetric(kg, "Kg")
    if initial.shape != geometric.shape:
        raise VerifiedInertiaInputError("K0 and Kg dimensions differ")
    _validate_precision(precision_bits)
    if not 0 <= max_steps <= MAX_ROOT_REFINEMENT_STEPS:
        raise VerifiedInertiaInputError(f"max_steps must be between 0 and {MAX_ROOT_REFINEMENT_STEPS}")
    lo, hi = float(lower), float(upper)
    if not math.isfinite(lo) or not math.isfinite(hi) or not 0.0 < lo < hi:
        raise VerifiedInertiaInputError("root bracket endpoints must be finite and satisfy 0 < lower < upper")
    k0_result = certify_symmetric_inertia(initial, precision_bits=precision_bits)
    if (
        k0_result.get("status") != "CERTIFIED"
        or k0_result.get("inertia") != {"negative": 0, "zero": 0, "positive": initial.shape[0]}
    ):
        return {
            "status": "K0_NOT_CERTIFIED_POSITIVE_DEFINITE",
            "lower": lo,
            "upper": hi,
            "K0_inertia": k0_result,
            "steps": [],
        }
    lo_result = certify_pencil_inertia(initial, geometric, lo, precision_bits=precision_bits)
    hi_result = certify_pencil_inertia(initial, geometric, hi, precision_bits=precision_bits)
    expected_lo = {"negative": 0, "zero": 0, "positive": initial.shape[0]}
    expected_hi = {"negative": 1, "zero": 0, "positive": initial.shape[0] - 1}
    if (
        lo_result.get("status") != "CERTIFIED"
        or lo_result.get("inertia") != expected_lo
        or hi_result.get("status") != "CERTIFIED"
        or hi_result.get("inertia") != expected_hi
    ):
        return {
            "status": "INITIAL_BRACKET_NOT_CERTIFIED",
            "lower": lo,
            "upper": hi,
            "lower_inertia": lo_result,
            "upper_inertia": hi_result,
            "K0_inertia": k0_result,
            "steps": [],
        }

    steps = []
    stop_status = "REFINEMENT_LIMIT_REACHED"
    for index in range(max_steps):
        if started_at is not None and time.perf_counter() - started_at >= MAX_CERTIFICATE_SECONDS:
            stop_status = "TOTAL_TIME_BUDGET_REACHED"
            break
        midpoint = lo + (hi - lo) / 2.0
        if midpoint == lo or midpoint == hi:
            stop_status = "FLOAT64_BRACKET_RESOLUTION_REACHED"
            break
        midpoint_result = certify_pencil_inertia(
            initial, geometric, midpoint, precision_bits=precision_bits
        )
        step = {
            "iteration": index + 1,
            "lambda": midpoint,
            "status": midpoint_result.get("status"),
            "inertia": midpoint_result.get("inertia"),
            "elapsed_seconds": midpoint_result.get("elapsed_seconds"),
        }
        steps.append(step)
        if midpoint_result.get("status") != "CERTIFIED":
            stop_status = "MIDPOINT_INERTIA_INDETERMINATE"
            break
        if midpoint_result["inertia"] == expected_lo:
            lo, lo_result = midpoint, midpoint_result
        elif midpoint_result["inertia"] == expected_hi:
            hi, hi_result = midpoint, midpoint_result
        else:
            stop_status = "MIDPOINT_INERTIA_OUTSIDE_BRACKET_COUNTS"
            break
    return {
        "status": stop_status,
        "lower": lo,
        "upper": hi,
        "lower_inertia": lo_result,
        "upper_inertia": hi_result,
        "K0_inertia": k0_result,
        "steps": steps,
        "max_steps": max_steps,
        "precision_bits": precision_bits,
    }


def certify_indefinite_witnesses(matrix: Any, *, precision_bits: int = DEFAULT_PRECISION_BITS) -> dict[str, Any]:
    """Prove indefiniteness from certified positive and negative Rayleigh witnesses."""
    value = _validated_symmetric(matrix, "matrix")
    _validate_precision(precision_bits)
    try:
        with _flint_precision(precision_bits) as (arb, arb_mat, _ctx):
            eigenvalues, vectors = eigh(value, check_finite=True, driver="evd")
            matrix_ball = _arb_matrix(arb_mat, value)
            witnesses = {}
            for name, column, expected_sign in (
                ("minimum_quotient", 0, "negative"),
                ("maximum_quotient", value.shape[0] - 1, "positive"),
            ):
                vector = vectors[:, column]
                vector_ball = arb_mat([[float(component)] for component in vector])
                quotient = (vector_ball.transpose() * matrix_ball * vector_ball)[0, 0]
                proven = bool(quotient < 0) if expected_sign == "negative" else bool(quotient > 0)
                witnesses[name] = {
                    "sign": expected_sign if proven else "UNRESOLVED",
                    "rayleigh_quotient_ball": str(quotient),
                    "approximate_eigenvalue": float(eigenvalues[column]),
                }
            indefinite = all(item["sign"] in {"negative", "positive"} for item in witnesses.values())
            return {
                "status": "CERTIFIED_INDEFINITE" if indefinite else "INDEFINITENESS_NOT_ESTABLISHED",
                "dimension": value.shape[0],
                "witnesses": witnesses,
                "precision_bits": precision_bits,
                "flint_version": importlib.metadata.version("python-flint"),
            }
    except VerifiedInertiaBackendUnavailable as exc:
        return {"status": "INDETERMINATE_BACKEND_UNAVAILABLE", "reason": str(exc), "precision_bits": precision_bits}


def residual_enclosure(
    k0: Any,
    kg: Any,
    load_factor: float,
    mode_full: Any,
    free_dof_indices: Any,
    *,
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> dict[str, Any]:
    """Recompute the candidate residual for the exact stored pencil and vector."""
    initial = _validated_symmetric(k0, "K0")
    geometric = _validated_symmetric(kg, "Kg")
    mode = np.asarray(mode_full, dtype=np.float64)
    free_raw = np.asarray(free_dof_indices)
    if free_raw.ndim != 1 or not np.issubdtype(free_raw.dtype, np.integer):
        raise VerifiedInertiaInputError("free-DOF indices must be a one-dimensional integer array")
    free = free_raw.astype(np.int64, copy=False)
    factor = float(load_factor)
    if (
        initial.shape != geometric.shape
        or mode.ndim != 1
        or free.shape != (initial.shape[0],)
        or np.unique(free).size != free.size
        or np.any(free < 0)
        or np.any(free >= mode.size)
        or not np.isfinite(mode).all()
        or not math.isfinite(factor)
    ):
        raise VerifiedInertiaInputError("candidate mode, free-DOF map, or pencil dimensions are invalid")
    _validate_precision(precision_bits)
    reduced_mode = mode[free]
    k0v_float = initial @ reduced_mode
    kgv_float = geometric @ reduced_mode
    residual_float = k0v_float + factor * kgv_float
    numerator = float(np.linalg.norm(residual_float))
    solver_style = numerator / max(float(np.linalg.norm(k0v_float)), 1.0)
    generalized = numerator / max(
        float(np.linalg.norm(k0v_float)) + abs(factor) * float(np.linalg.norm(kgv_float)), np.finfo(float).tiny
    )

    try:
        with _flint_precision(precision_bits) as (arb, arb_mat, _ctx):
            k0_ball = _arb_matrix(arb_mat, initial)
            kg_ball = _arb_matrix(arb_mat, geometric)
            mode_ball = arb_mat([[float(component)] for component in reduced_mode])
            factor_ball = arb(factor)
            k0v_ball = k0_ball * mode_ball
            kgv_ball = kg_ball * mode_ball
            residual_ball = k0v_ball + kgv_ball * factor_ball
            norm_upper_sq = arb(0)
            for index in range(residual_ball.nrows()):
                component_upper = residual_ball[index, 0].abs_upper()
                norm_upper_sq += component_upper * component_upper
            norm_upper = norm_upper_sq.sqrt()

            norm_k0v_lower_sq = arb(0)
            for index in range(k0v_ball.nrows()):
                component_lower = k0v_ball[index, 0].abs_lower()
                norm_k0v_lower_sq += component_lower * component_lower
            denominator_lower = norm_k0v_lower_sq.sqrt()
            if not bool(denominator_lower > 1):
                denominator_lower = arb(1)
            solver_style_upper = norm_upper / denominator_lower
    except VerifiedInertiaBackendUnavailable as exc:
        return {"status": "INDETERMINATE_BACKEND_UNAVAILABLE", "reason": str(exc), "precision_bits": precision_bits}
    return {
        "status": "RESIDUAL_ENCLOSED",
        "precision_bits": precision_bits,
        "candidate_factor": factor,
        "candidate_mode_norm": float(np.linalg.norm(reduced_mode)),
        "float64_generalized_residual": generalized,
        "float64_solver_style_residual": solver_style,
        "float64_residual_norm": numerator,
        "arb_residual_norm_upper_enclosure": str(norm_upper),
        "arb_solver_style_residual_upper_enclosure": str(solver_style_upper),
        "arb_residual_norm_upper_bound": str(norm_upper.abs_upper()),
        "arb_solver_style_residual_upper_bound": str(solver_style_upper.abs_upper()),
        "denominator_norm_lower_bound": str(denominator_lower),
        "flint_version": importlib.metadata.version("python-flint"),
    }


def _as_dense(matrix: Any) -> np.ndarray:
    return np.asarray(matrix.toarray() if hasattr(matrix, "toarray") else matrix, dtype=np.float64)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze_capture_inertia(
    archive: Path,
    case_name: str,
    *,
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> dict[str, Any]:
    """Verify one controlled archive and certify its first positive root.

    Once K0 is positive definite, Q(lambda) is congruent to I + lambda B
    for symmetric B. Its negative inertia is therefore monotone on lambda>=0,
    even when Kg is indefinite. A 0-to-1 inertia change brackets the first
    positive root and excludes earlier roots for the represented matrices.
    """
    _validate_precision(precision_bits)
    if case_name not in {"before", "after"}:
        raise VerifiedInertiaInputError("case_name must be 'before' or 'after'")

    from research.g08_compare.capture import read_matrix_archive, sha256_file
    from research.g08_compare.spectral_diagnostic import SpectralInputError, analyze_capture

    archive = Path(archive).resolve(strict=True)
    verified = analyze_capture(archive, case_name)
    metadata = json.loads((archive / "capture.json").read_text(encoding="utf-8"))
    result_data = json.loads((archive / "result.json").read_text(encoding="utf-8"))
    arrays = read_matrix_archive(archive / "matrices.npz")
    k0 = _as_dense(arrays["K0"])
    kg = _as_dense(arrays["Kg"])
    u_pre = np.asarray(arrays["u_pre"], dtype=np.float64)
    mode = np.asarray(np.load(archive / "mode.npy", allow_pickle=False), dtype=np.float64)
    free = np.asarray(arrays["free_dof_indices"], dtype=np.int64)

    expected_dimension = {"before": 276, "after": 300}[case_name]
    if k0.shape != (expected_dimension, expected_dimension) or kg.shape != k0.shape:
        raise SpectralInputError("captured matrix dimensions differ from the registered G08 case")
    if mode.shape != (int(metadata["full_dof_count"]),) or u_pre.shape != mode.shape:
        raise SpectralInputError("captured preload or candidate vector shape differs from the full DOF map")
    if not np.isfinite(u_pre).all() or not np.isfinite(mode).all():
        raise SpectralInputError("captured preload or candidate vector has non-finite values")
    if not np.array_equal(k0, k0.T) or not np.array_equal(kg, kg.T):
        raise SpectralInputError("stored binary64 matrices are not exactly symmetric; no symmetrization was applied")

    factor = float(result_data["factor"])
    signed_load = float(result_data["signed_load"])
    bracket = result_data["diagnostics"]["critical_bracket"]
    lower = float(bracket["lower"])
    upper = float(bracket["upper"])
    if signed_load != -factor or not (0.0 < lower < factor < upper):
        raise SpectralInputError("signed-load convention or candidate bracket does not match the archive")
    expected_convention = (
        "Q(lambda) = K0 + lambda * Kg; lambda is the positive dimensionless load multiplier"
    )
    if metadata["sign_convention"] != expected_convention:
        raise SpectralInputError("captured matrix sign convention differs from the study contract")
    if metadata["preload"]["u_pre_sha256"] != hashlib.sha256(np.ascontiguousarray(u_pre).tobytes()).hexdigest():
        raise SpectralInputError("u_pre fingerprint differs from the capture metadata")
    if metadata["candidate"]["mode_sha256"] != sha256_file(archive / "mode.npy"):
        raise SpectralInputError("candidate vector fingerprint differs from the capture metadata")

    # Neighbor root screens from the earlier double-precision study selected
    # dyadic endpoints; the interval proof below, not that screen, is decisive.
    second_brackets = {
        "before": (873.0, 873.03125),
        "after": (872.96875, 873.03125),
    }
    second_lower, second_upper = second_brackets[case_name]
    initial_lower, initial_upper = lower, upper
    measured_started = time.perf_counter()
    k0_inertia = certify_symmetric_inertia(k0, precision_bits=precision_bits)
    kg_signs = certify_indefinite_witnesses(kg, precision_bits=precision_bits)
    refinement = refine_certified_root_bracket(
        k0,
        kg,
        initial_lower,
        initial_upper,
        precision_bits=precision_bits,
        started_at=measured_started,
    )
    lower, upper = refinement["lower"], refinement["upper"]
    lower_inertia = refinement["lower_inertia"]
    upper_inertia = refinement["upper_inertia"]
    second_lower_inertia = certify_pencil_inertia(k0, kg, second_lower, precision_bits=precision_bits)
    second_upper_inertia = certify_pencil_inertia(k0, kg, second_upper, precision_bits=precision_bits)
    candidate_residual = residual_enclosure(
        k0, kg, factor, mode, free, precision_bits=precision_bits
    )
    elapsed_seconds = time.perf_counter() - measured_started

    first_certified = (
        elapsed_seconds <= MAX_CERTIFICATE_SECONDS
        and k0_inertia.get("status") == "CERTIFIED"
        and k0_inertia["inertia"] == {"negative": 0, "zero": 0, "positive": expected_dimension}
        and lower_inertia.get("status") == "CERTIFIED"
        and lower_inertia["inertia"] == {"negative": 0, "zero": 0, "positive": expected_dimension}
        and upper_inertia.get("status") == "CERTIFIED"
        and upper_inertia["inertia"] == {"negative": 1, "zero": 0, "positive": expected_dimension - 1}
    )
    second_certified = (
        elapsed_seconds <= MAX_CERTIFICATE_SECONDS
        and second_lower_inertia.get("status") == "CERTIFIED"
        and second_lower_inertia["inertia"] == {"negative": 1, "zero": 0, "positive": expected_dimension - 1}
        and second_upper_inertia.get("status") == "CERTIFIED"
        and second_upper_inertia["inertia"] == {"negative": 2, "zero": 0, "positive": expected_dimension - 2}
    )
    return {
        "case": case_name,
        "classification": "CERTIFICATE_FOR_STORED_BINARY64_MATRICES_ONLY",
        "historical_first_mode_status": "FIRST_MODE_NOT_ESTABLISHED",
        "stored_matrix_first_positive_root_status": (
            "CERTIFIED_FOR_STORED_BINARY64_MATRIX" if first_certified else "INDETERMINATE"
        ),
        "second_root_bracket_status": "CERTIFIED" if second_certified else "INDETERMINATE",
        "certificate_scope": (
            "Exact real values represented by stored binary64 K0, Kg, and dyadic bracket endpoints. "
            "No FEM assembly, discretization, or model error is bounded. The candidate vector itself is not interval-certified."
        ),
        "source_commit": verified["source_commit"],
        "source_tree": verified["source_tree"],
        "inputs_sha256": verified["inputs_sha256"],
        "mesh_sha256": verified["mesh_sha256"],
        "scope_id": verified["scope_id"],
        "capture_contract_sha256": verified["capture_contract_sha256"],
        "runner_evidence": verified["runner_evidence"],
        "preload_status": verified["preload_status"],
        "preload_final_relative_residual": verified["preload_final_relative_residual"],
        "archive_validation": verified["archive_validation"],
        "capture_validation": verified["capture_validation"],
        "capture_json_sha256": verified["capture_json_sha256"],
        "matrices_npz_sha256": verified["matrices_npz_sha256"],
        "result_json_sha256": verified["result_json_sha256"],
        "candidate_mode_sha256": verified["candidate_mode_sha256"],
        "K0_sha256_canonical_csr": verified["matrix_fingerprints"]["K0"]["sha256_canonical_csr"],
        "Kg_sha256_canonical_csr": verified["matrix_fingerprints"]["Kg"]["sha256_canonical_csr"],
        "u_pre_sha256": verified["u_pre_sha256"],
        "dof_map_sha256": verified["dof_map_sha256"],
        "K0_shape": list(k0.shape),
        "Kg_shape": list(kg.shape),
        "free_dofs": int(free.size),
        "exact_binary64_symmetry": {"K0": True, "Kg": True},
        "units": verified["units"],
        "pencil_convention": verified["pencil_sign_convention"],
        "candidate_factor": factor,
        "signed_load": signed_load,
        "archived_solver_candidate_residual_relative": verified["solver_candidate_residual_relative"],
        "candidate_factor_bracket": {"lower": lower, "upper": upper},
        "initial_solver_bracket": {"lower": initial_lower, "upper": initial_upper},
        "root_bracket_refinement": refinement,
        "archived_candidate_inside_certified_bracket": lower <= factor <= upper,
        "candidate_mode_residual_enclosure": candidate_residual,
        "K0_inertia": k0_inertia,
        "Kg_indefiniteness_witnesses": kg_signs,
        "inertia_at_bracket": {"lower": lower_inertia, "upper": upper_inertia},
        "second_positive_root_bracket": {
            "lower": second_lower,
            "upper": second_upper,
            "inertia": {"lower": second_lower_inertia, "upper": second_upper_inertia},
        },
        "root_count_reasoning": (
            "K0 is certified positive definite. By congruence, Q(lambda) is I + lambda B for a symmetric B. "
            "Each eigenvalue is affine in lambda and crosses zero at most once for lambda>=0. "
            "Thus inertia 0 at the first bracket's lower endpoint and inertia 1 at its upper endpoint "
            "certify exactly one first positive root there and exclude any earlier positive root."
        ),
        "precision_bits": precision_bits,
        "precision_schedule": [precision_bits],
        "maximum_single_certificate_seconds": MAX_CERTIFICATE_SECONDS,
        "budget_enforcement": "Elapsed-time check after each certificate; not a preemptive process timeout.",
        "observed_total_seconds": elapsed_seconds,
        "observed_total_seconds_scope": "Inertia and residual calculations after archive validation and data loading.",
        "memory_observation": "NOT_MEASURED",
        "flint_version": importlib.metadata.version("python-flint"),
        "runtime_versions": verified["runtime_versions"],
        "analysis_runtime_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": importlib.metadata.version("scipy"),
            "python_flint": importlib.metadata.version("python-flint"),
        },
        "historical_ab_result_match": verified["historical_ab_result_match"],
        "mode_comparison": "NOT_DONE; no common physical interpolation or projection is defined and tested.",
    }


def analyze_pair(
    before_archive: Path,
    after_archive: Path,
    *,
    precision_bits: int = DEFAULT_PRECISION_BITS,
) -> dict[str, Any]:
    """Analyze the two validated captures without changing historical reports."""
    before = analyze_capture_inertia(before_archive, "before", precision_bits=precision_bits)
    after = analyze_capture_inertia(after_archive, "after", precision_bits=precision_bits)
    repository_root = Path(__file__).resolve().parents[2]
    implementation = {
        "analysis_script_sha256": _file_sha256(Path(__file__).resolve()),
        "synthetic_tests_sha256": _file_sha256(repository_root / "tests" / "research" / "test_g08_verified_inertia.py"),
        "optional_dependency_spec_sha256": _file_sha256(
            Path(__file__).resolve().parent / "requirements-inertia.txt"
        ),
    }
    interval_lower = before["candidate_factor_bracket"]["upper"]
    interval_upper = after["candidate_factor_bracket"]["lower"]
    comparison = {
        "first_positive_root_brackets": {
            "before": before["candidate_factor_bracket"],
            "after": after["candidate_factor_bracket"],
        },
        "after_minus_before_root_difference_bracket": {
            "lower": after["candidate_factor_bracket"]["lower"] - before["candidate_factor_bracket"]["upper"],
            "upper": after["candidate_factor_bracket"]["upper"] - before["candidate_factor_bracket"]["lower"],
        },
        "candidate_factor_difference_after_minus_before": after["candidate_factor"] - before["candidate_factor"],
        "free_dofs_before_after": [before["free_dofs"], after["free_dofs"]],
        "interpretation_limit": (
            "The A/B change combines connectivity and discretization; it is not a physical validation or an isolated connectivity effect."
        ),
    }
    if interval_lower >= interval_upper:
        comparison["after_minus_before_root_difference_bracket"] = {"status": "INTERVALS_OVERLAP_OR_ORDER_UNRESOLVED"}
    return {
        "schema": "qf-g08-verified-inertia-v1",
        "classification": "DEVELOPMENT_ONLY_STORED_MATRIX_CERTIFICATE",
        "method": "Arb interval enclosure plus approximate eigenbasis and norm perturbation bounds",
        "implementation_fingerprints": implementation,
        "cases": {"before": before, "after": after},
        "comparison": comparison,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-archive", type=Path, required=True)
    parser.add_argument("--after-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--precision-bits", type=int, default=DEFAULT_PRECISION_BITS)
    args = parser.parse_args()
    report = analyze_pair(args.before_archive, args.after_archive, precision_bits=args.precision_bits)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    args.output.write_bytes(rendered.encode("utf-8"))
    print(
        json.dumps(
            {
                "output": str(args.output),
                "cases": {
                    key: {
                        "first_root_status": value["stored_matrix_first_positive_root_status"],
                        "K0_inertia": value["K0_inertia"].get("inertia"),
                        "elapsed_seconds": value["observed_total_seconds"],
                    }
                    for key, value in report["cases"].items()
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
