import numpy as np
import pytest

from solveur.experimental.eas_residual.bounded_exact_supervisor import _verified_message, identity, supervise
from solveur.experimental.eas_residual.archive_api import supervise_npz_archives


def invoke(value, **kwargs):
    return supervise(np.array([1.0]), np.array([0]), np.array([0, 1]), (1, 1),
                     np.array([1.0]), np.array([value]), 1e-7, **kwargs)


@pytest.mark.parametrize("value,decision", [(1.0, "PASS"), (0.5, "FAIL"), (1.0-5e-8, "PASS")])
def test_decisions_leave_guard_unchanged(value, decision):
    result = invoke(value)
    assert result["supplemental"] == decision
    assert result["historical_decision"] in {"ACCEPTED", "REJECTED"}


def test_real_child_timeout_is_inconclusive():
    result = invoke(1.0, timeout=0.000001)
    assert result["supplemental"] == "INCONCLUSIVE"
    assert result["reason"] == "TIMEOUT"
    assert result["child_exitcode"] is not None


def test_invalid_data_and_input_budget_are_inconclusive():
    assert invoke(float("nan"))["supplemental"] == "INCONCLUSIVE"
    assert invoke(1.0, input_limit=1)["supplemental"] == "INCONCLUSIVE"
    result = supervise(np.array([1., 2.]), np.array([0, 0]), np.array([0, 2]), (1, 1),
                       np.ones(1), np.ones(1), 1e-7)
    assert result["supplemental"] == "INCONCLUSIVE"


def test_missing_psutil_is_inconclusive(monkeypatch):
    import solveur.experimental.eas_residual.bounded_exact_supervisor as module
    monkeypatch.setattr(module, "psutil", None)
    result = invoke(1.0)
    assert result["supplemental"] == "INCONCLUSIVE"
    assert result["reason"] == "PSUTIL_UNAVAILABLE"


def test_zero_denominator_and_cancellation():
    zero = supervise(np.array([1.0]), np.array([0]), np.array([0, 1]), (1, 1),
                     np.array([0.0]), np.array([0.0]), 1e-7)
    assert zero["supplemental"] == "INCONCLUSIVE"
    cancellation = supervise(np.array([1e200, -1e200]), np.array([0, 1]), np.array([0, 2, 2]), (2, 2),
                             np.array([0.0, 1.0]), np.array([1.0, 1.0]), 1e-7)
    assert cancellation["supplemental"] == "FAIL"


def test_identity_covers_values_shape_and_threshold():
    arrays = (np.array([1.0]), np.array([0]), np.array([0, 1]), np.ones(1), np.ones(1))
    baseline = identity(arrays, (1, 1), 0.5)
    assert baseline != identity(arrays, (1, 1), np.nextafter(0.5, 1.0))
    assert baseline != identity((*arrays[:-1], np.zeros(1)), (1, 1), 0.5)


def test_substituted_and_incomplete_responses_are_inconclusive():
    assert _verified_message({"identity": "other", "decision": "PASS"}, "expected") == "INCONCLUSIVE"
    assert _verified_message({"identity": "expected"}, "expected") == "INCONCLUSIVE"
    assert _verified_message(None, "expected") == "INCONCLUSIVE"
    assert _verified_message({"identity": "expected", "decision": ["PASS"]}, "expected") == "INCONCLUSIVE"


def test_late_reply_after_child_exit_cannot_pass(monkeypatch):
    import solveur.experimental.eas_residual.bounded_exact_supervisor as module

    real_context = module.mp.get_context("spawn")

    class CompletedChild:
        exitcode = 0

        def __init__(self, *, target, args):
            self.args = args

        def start(self):
            self.args[0].send({"identity": self.args[-1], "decision": "PASS"})

        def is_alive(self):
            return False

        def join(self, _timeout):
            pass

    context = type("Context", (), {"Pipe": staticmethod(real_context.Pipe), "Process": CompletedChild})
    clock = iter((0.0, 2.0, 2.0))
    monkeypatch.setattr(module.mp, "get_context", lambda _: context)
    monkeypatch.setattr(module.time, "monotonic", lambda: next(clock))
    result = invoke(1.0, timeout=1.0)
    assert result["historical_decision"] == "ACCEPTED"
    assert result["supplemental"] == "INCONCLUSIVE"
    assert result["reason"] == "TIMEOUT"


def test_nonfinite_resource_limits_are_refused():
    for limit in ("timeout", "rss_limit", "input_limit"):
        assert invoke(1.0, **{limit: float("nan")})["reason"] == "INVALID_LIMIT_OR_INPUT_SIZE"


def write_archive_pair(tmp_path):
    import hashlib

    matrix_path = tmp_path / "matrix.npz"
    candidate_path = tmp_path / "candidate.npz"
    np.savez(
        matrix_path,
        reduced_data=np.array([1.0]),
        reduced_indices=np.array([0], dtype=np.int32),
        reduced_indptr=np.array([0, 1], dtype=np.int32),
        reduced_shape=np.array([1, 1], dtype=np.int64),
        rhs=np.array([1.0]),
    )
    np.savez(candidate_path, candidate=np.array([1.0]))
    return (
        matrix_path,
        candidate_path,
        hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
        hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    )


def test_hash_bound_archive_interface_runs_spawned_diagnostic(tmp_path):
    matrix_path, candidate_path, matrix_sha, candidate_sha = write_archive_pair(tmp_path)
    result = supervise_npz_archives(
        matrix_path,
        candidate_path,
        matrix_sha256=matrix_sha,
        candidate_sha256=candidate_sha,
    )
    assert result["archive_validation"] == "PASS"
    assert result["supplemental"] == "PASS"
    assert result["historical_decision"] == "ACCEPTED"
    assert result["matrix_archive_sha256"] == matrix_sha
    assert result["candidate_archive_sha256"] == candidate_sha


def test_altered_archive_is_refused_before_guard(tmp_path, monkeypatch):
    matrix_path, candidate_path, matrix_sha, candidate_sha = write_archive_pair(tmp_path)
    matrix_path.write_bytes(matrix_path.read_bytes() + b"altered")
    monkeypatch.setattr(
        "solveur.experimental.eas_residual.archive_api.supervise",
        lambda *_a, **_k: pytest.fail("guard and child must not run for an altered archive"),
    )
    result = supervise_npz_archives(
        matrix_path,
        candidate_path,
        matrix_sha256=matrix_sha,
        candidate_sha256=candidate_sha,
    )
    assert result["archive_validation"] == "REJECTED"
    assert result["historical_decision"] == "NOT_RUN"
    assert result["supplemental"] == "INCONCLUSIVE"
    assert result["reason"] == "ARCHIVE_SHA256_MISMATCH"


def test_archive_api_refuses_substitution_and_incomplete_npz(tmp_path):
    import hashlib

    matrix_path, candidate_path, matrix_sha, candidate_sha = write_archive_pair(tmp_path)
    candidate_path.write_bytes(candidate_path.read_bytes() + b"substituted")
    altered = supervise_npz_archives(
        matrix_path,
        candidate_path,
        matrix_sha256=matrix_sha,
        candidate_sha256=candidate_sha,
    )
    assert altered["supplemental"] == "INCONCLUSIVE"
    assert altered["reason"] == "ARCHIVE_SHA256_MISMATCH"

    incomplete_path = tmp_path / "incomplete_matrix.npz"
    candidate_valid_path = tmp_path / "candidate_valid.npz"
    np.savez(incomplete_path, reduced_data=np.array([1.0]))
    np.savez(candidate_valid_path, candidate=np.array([1.0]))
    result = supervise_npz_archives(
        incomplete_path,
        candidate_valid_path,
        matrix_sha256=hashlib.sha256(incomplete_path.read_bytes()).hexdigest(),
        candidate_sha256=hashlib.sha256(candidate_valid_path.read_bytes()).hexdigest(),
    )
    assert result["supplemental"] == "INCONCLUSIVE"
    assert result["historical_decision"] == "NOT_RUN"
    assert result["reason"] == "ARCHIVE_MEMBERS_INVALID"


def test_archive_header_must_match_payload_before_loading(tmp_path, monkeypatch):
    import hashlib
    import io
    import zipfile

    matrix_path, candidate_path, matrix_sha, _ = write_archive_pair(tmp_path)
    header = io.BytesIO()
    np.lib.format.write_array_header_1_0(
        header, {"shape": (2,), "fortran_order": False, "descr": "<f8"}
    )
    with zipfile.ZipFile(candidate_path, "w") as archive:
        archive.writestr("candidate.npy", header.getvalue() + np.ones(1, dtype="<f8").tobytes())
    monkeypatch.setattr(
        "solveur.experimental.eas_residual.archive_api.supervise",
        lambda *_a, **_k: pytest.fail("invalid NPY layout reached the guard"),
    )
    result = supervise_npz_archives(
        matrix_path,
        candidate_path,
        matrix_sha256=matrix_sha,
        candidate_sha256=hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    )
    assert result["reason"] == "ARCHIVE_NPY_LAYOUT_INVALID"
    assert result["historical_decision"] == "NOT_RUN"
    assert result["supplemental"] == "INCONCLUSIVE"


def test_monitor_failure_is_inconclusive(monkeypatch):
    import psutil
    import solveur.experimental.eas_residual.bounded_exact_supervisor as module

    def fail(_pid):
        raise psutil.AccessDenied()

    monkeypatch.setattr(module.psutil, "Process", fail)
    result = invoke(1.0)
    assert result["supplemental"] == "INCONCLUSIVE"
    assert result["reason"] == "MONITOR_ERROR"


def test_real_child_interruption_is_inconclusive(monkeypatch):
    import multiprocessing as mp
    import solveur.experimental.eas_residual.bounded_exact_supervisor as module

    real_context = mp.get_context("spawn")

    class InterruptedContext:
        Pipe = staticmethod(real_context.Pipe)

        @staticmethod
        def Process(*args, **kwargs):
            process = real_context.Process(*args, **kwargs)

            class Proxy:
                def start(self):
                    process.start()
                    process.terminate()

                def __getattr__(self, name):
                    return getattr(process, name)

            return Proxy()

    monkeypatch.setattr(module.mp, "get_context", lambda _name: InterruptedContext())
    result = invoke(1.0)
    assert result["supplemental"] == "INCONCLUSIVE"
    assert result["child_exitcode"] not in (None, 0)


def test_parent_interrupt_is_inconclusive(monkeypatch):
    import solveur.experimental.eas_residual.bounded_exact_supervisor as module

    def interrupt(_delay):
        raise KeyboardInterrupt()

    monkeypatch.setattr(module.time, "sleep", interrupt)
    result = invoke(1.0)
    assert result["supplemental"] == "INCONCLUSIVE"
    assert result["reason"] == "SUPERVISOR_ERROR_OR_INTERRUPTED"
