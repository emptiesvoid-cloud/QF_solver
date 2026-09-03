import numpy as np
import pytest
import sys
import types
from scipy.sparse import csr_matrix

from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core import solver_backend
from solveur.core.solver_backend import optional_backend_status, select_backend


def test_auto_backend_is_scipy_by_default_for_small_systems() -> None:
    selection = select_backend("auto", problem_size=10, parameters={})

    assert selection.selected == "scipy"
    assert selection.fallback_used is False
    assert selection.to_dict()["requested"] == "auto"


def test_auto_backend_records_scipy_fallback_for_large_system_without_petsc() -> None:
    if optional_backend_status()["petsc"]:
        pytest.skip("PETSc is installed in this environment")

    selection = select_backend("auto", problem_size=250_000, parameters={})

    assert selection.selected == "scipy"
    assert selection.fallback_used is True
    assert "fallback" in selection.reason.lower()


def test_explicit_petsc_request_is_clear_when_optional_dependency_is_missing() -> None:
    if optional_backend_status()["petsc"]:
        pytest.skip("PETSc is installed in this environment")
    with pytest.raises(InputValidationError, match="petsc4py"):
        select_backend("petsc", problem_size=10, parameters={})


def test_backend_rejects_unknown_name() -> None:
    with pytest.raises(InputValidationError, match="backend must be"):
        select_backend("cuda", problem_size=10, parameters={})


def test_explicit_scipy_never_falls_back() -> None:
    selection = select_backend("scipy", problem_size=500_000, parameters={})

    assert selection.selected == "scipy"
    assert selection.fallback_used is False
    assert selection.reason == "explicit SciPy backend"


def test_auto_backend_can_select_optional_petsc_when_policy_requests_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(solver_backend, "_petsc_module", lambda: object())
    monkeypatch.setattr(solver_backend, "_slepc_module", lambda: None)

    selection = select_backend("auto", problem_size=10, parameters={"prefer_petsc": True})

    assert selection.selected == "petsc"
    assert selection.fallback_used is False
    assert selection.petsc_available is True
    assert selection.slepc_available is False


def test_explicit_petsc_selection_is_auditable_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(solver_backend, "_petsc_module", lambda: object())
    monkeypatch.setattr(solver_backend, "_slepc_module", lambda: object())

    selection = select_backend("petsc", problem_size=10, parameters={})

    assert selection.selected == "petsc"
    assert selection.fallback_used is False
    assert selection.to_dict() == {
        "requested": "petsc",
        "selected": "petsc",
        "fallback_used": False,
        "petsc_available": True,
        "slepc_available": True,
        "reason": "explicit PETSc backend",
    }


def test_petsc_linear_adapter_uses_optional_module_without_eager_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeVec:
        def __init__(self, size: int) -> None:
            self.values = np.zeros(size, dtype=float)

        def setArray(self, values: np.ndarray) -> None:
            self.values = np.asarray(values, dtype=float).copy()

        def getArray(self) -> np.ndarray:
            return self.values

        def destroy(self) -> None:
            return None

    class FakeMat:
        def __init__(self) -> None:
            self.csr = None

        def createAIJ(self, *, size, csr):
            self.shape = tuple(size)
            self.csr = csr_matrix((csr[2], csr[1], csr[0]), shape=self.shape)
            return self

        def assemble(self) -> None:
            return None

        def createVecs(self):
            return FakeVec(self.shape[0]), FakeVec(self.shape[0])

        def destroy(self) -> None:
            return None

    class FakePC:
        def setType(self, value: str) -> None:
            self.type = value

    class FakeKSP:
        def __init__(self) -> None:
            self.pc = FakePC()
            self.matrix = None
            self.rhs = None

        def create(self):
            return self

        def setType(self, value: str) -> None:
            self.method = value

        def getPC(self):
            return self.pc

        def setOperators(self, matrix) -> None:
            self.matrix = matrix

        def setTolerances(self, **kwargs) -> None:
            self.tolerances = kwargs

        def setFromOptions(self) -> None:
            return None

        def solve(self, rhs, solution) -> None:
            solution.values = np.linalg.solve(self.matrix.csr.toarray(), rhs.values)

        def getConvergedReason(self) -> int:
            return 1

        def getIterationNumber(self) -> int:
            return 1

        def getResidualNorm(self) -> float:
            return 0.0

        def destroy(self) -> None:
            return None

    fake_module = types.ModuleType("petsc4py")
    fake_module.PETSc = types.SimpleNamespace(Mat=FakeMat, KSP=FakeKSP)
    monkeypatch.setitem(sys.modules, "petsc4py", fake_module)
    monkeypatch.setattr(solver_backend, "_petsc_module", lambda: fake_module)

    matrix = csr_matrix([[4.0, 1.0], [1.0, 3.0]])
    solution, iterations, residual = solver_backend.solve_with_petsc(
        matrix, np.array([1.0, 2.0]), "direct", {"rtol": 1.0e-12}
    )

    assert np.allclose(matrix @ solution, [1.0, 2.0])
    assert iterations == 1
    assert residual == 0.0


@pytest.mark.parametrize(
    ("preconditioner", "expected_pc"),
    (("jacobi", "jacobi"), ("gamg", "gamg"), ("hypre", "hypre"), ("ilu", "ilu"), ("none", "none")),
)
def test_petsc_iterative_adapter_configures_preconditioner(
    monkeypatch: pytest.MonkeyPatch, preconditioner: str, expected_pc: str
) -> None:
    class FakeVec:
        def __init__(self, size: int) -> None:
            self.values = np.zeros(size, dtype=float)

        def setArray(self, values: np.ndarray) -> None:
            self.values = np.asarray(values, dtype=float).copy()

        def getArray(self) -> np.ndarray:
            return self.values

        def destroy(self) -> None:
            return None

    class FakeMat:
        def createAIJ(self, *, size, csr):
            self.shape = tuple(size)
            self.csr = csr_matrix((csr[2], csr[1], csr[0]), shape=self.shape)
            return self

        def assemble(self) -> None:
            return None

        def createVecs(self):
            return FakeVec(self.shape[0]), FakeVec(self.shape[0])

        def destroy(self) -> None:
            return None

    class FakePC:
        def __init__(self) -> None:
            self.type = None

        def setType(self, value: str) -> None:
            self.type = value

    class FakeKSP:
        instances = []

        def __init__(self) -> None:
            self.pc = FakePC()
            self.matrix = None
            self.method = None
            FakeKSP.instances.append(self)

        def create(self):
            return self

        def setType(self, value: str) -> None:
            self.method = value

        def getPC(self):
            return self.pc

        def setOperators(self, matrix) -> None:
            self.matrix = matrix

        def setTolerances(self, **kwargs) -> None:
            self.tolerances = kwargs

        def setFromOptions(self) -> None:
            return None

        def solve(self, rhs, solution) -> None:
            solution.values = np.linalg.solve(self.matrix.csr.toarray(), rhs.values)

        def getConvergedReason(self) -> int:
            return 1

        def getIterationNumber(self) -> int:
            return 3

        def getResidualNorm(self) -> float:
            return 1.0e-12

        def destroy(self) -> None:
            return None

    fake_module = types.ModuleType("petsc4py")
    fake_module.PETSc = types.SimpleNamespace(Mat=FakeMat, KSP=FakeKSP)
    monkeypatch.setitem(sys.modules, "petsc4py", fake_module)
    monkeypatch.setattr(solver_backend, "_petsc_module", lambda: fake_module)

    matrix = csr_matrix([[4.0, 1.0], [1.0, 3.0]])
    solution, iterations, residual = solver_backend.solve_with_petsc(
        matrix,
        np.array([1.0, 2.0]),
        "cg",
        {"preconditioner": preconditioner, "maxiter": 7, "rtol": 1.0e-9},
    )

    assert np.allclose(matrix @ solution, [1.0, 2.0])
    assert iterations == 3
    assert residual == pytest.approx(1.0e-12)
    assert FakeKSP.instances[0].method == "cg"
    assert FakeKSP.instances[0].pc.type == expected_pc
    assert FakeKSP.instances[0].tolerances["max_it"] == 7


def test_petsc_adapter_rejects_unknown_preconditioner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(solver_backend, "_petsc_module", lambda: object())
    with pytest.raises(InputValidationError, match="Unsupported PETSc preconditioner"):
        solver_backend._petsc_preconditioner_type("made_up")


def test_petsc_adapter_reports_nonconvergence(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeVec:
        def __init__(self, size: int) -> None:
            self.values = np.zeros(size, dtype=float)

        def setArray(self, values: np.ndarray) -> None:
            self.values = np.asarray(values, dtype=float)

        def getArray(self) -> np.ndarray:
            return self.values

        def destroy(self) -> None:
            return None

    class FakeMat:
        def createAIJ(self, *, size, csr):
            self.shape = tuple(size)
            return self

        def assemble(self) -> None:
            return None

        def createVecs(self):
            return FakeVec(self.shape[0]), FakeVec(self.shape[0])

        def destroy(self) -> None:
            return None

    class FakePC:
        def setType(self, value: str) -> None:
            return None

    class FakeKSP:
        def create(self):
            self.pc = FakePC()
            return self

        def setType(self, value: str) -> None:
            return None

        def getPC(self):
            return self.pc

        def setOperators(self, matrix) -> None:
            return None

        def setTolerances(self, **kwargs) -> None:
            return None

        def setFromOptions(self) -> None:
            return None

        def solve(self, rhs, solution) -> None:
            return None

        def getConvergedReason(self) -> int:
            return -3

        def destroy(self) -> None:
            return None

    fake_module = types.ModuleType("petsc4py")
    fake_module.PETSc = types.SimpleNamespace(Mat=FakeMat, KSP=FakeKSP)
    monkeypatch.setitem(sys.modules, "petsc4py", fake_module)
    monkeypatch.setattr(solver_backend, "_petsc_module", lambda: fake_module)

    with pytest.raises(NumericalConvergenceError, match="did not converge"):
        solver_backend.solve_with_petsc(csr_matrix(np.eye(2)), np.ones(2), "gmres", {})


def test_slepc_modal_adapter_returns_requested_eigenpairs(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeVec:
        def __init__(self, size: int) -> None:
            self.values = np.zeros(size, dtype=float)

        def getArray(self) -> np.ndarray:
            return self.values

        def destroy(self) -> None:
            return None

    class FakeMat:
        def __init__(self) -> None:
            self.shape = None

        def createAIJ(self, *, size, csr):
            self.shape = tuple(size)
            return self

        def assemble(self) -> None:
            return None

        def createVecs(self):
            return FakeVec(self.shape[0]), FakeVec(self.shape[0])

        def destroy(self) -> None:
            return None

    class FakeEPS:
        class ProblemType:
            GHEP = "ghep"

        class Which:
            SMALLEST_REAL = "smallest_real"

        def create(self):
            return self

        def setOperators(self, stiffness, mass) -> None:
            return None

        def setProblemType(self, value) -> None:
            return None

        def setDimensions(self, nev) -> None:
            self.mode_count = nev

        def setWhichEigenpairs(self, value) -> None:
            return None

        def setTolerances(self, **kwargs) -> None:
            return None

        def setFromOptions(self) -> None:
            return None

        def solve(self) -> None:
            return None

        def getConverged(self) -> int:
            return self.mode_count

        def getEigenpair(self, index, real, imaginary):
            real.values[:] = 2.0 + index
            imaginary.values[:] = 0.0
            return (2.0 + index, 0.0)

        def destroy(self) -> None:
            return None

    fake_petsc = types.ModuleType("petsc4py")
    fake_petsc.PETSc = types.SimpleNamespace(Mat=FakeMat)
    fake_slepc = types.ModuleType("slepc4py")
    fake_slepc.SLEPc = types.SimpleNamespace(EPS=FakeEPS)
    monkeypatch.setitem(sys.modules, "petsc4py", fake_petsc)
    monkeypatch.setitem(sys.modules, "slepc4py", fake_slepc)
    monkeypatch.setattr(solver_backend, "_petsc_module", lambda: fake_petsc)
    monkeypatch.setattr(solver_backend, "_slepc_module", lambda: fake_slepc)

    values, vectors = solver_backend.solve_with_slepc(
        csr_matrix(np.eye(2)), csr_matrix(np.eye(2)), 2, {}
    )

    assert np.array_equal(values, [2.0, 3.0])
    assert vectors.shape == (2, 2)
    assert np.all(vectors == np.asarray([[2.0, 3.0], [2.0, 3.0]]))


def test_optional_solver_adapters_fail_explicitly_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(solver_backend, "_petsc_module", lambda: None)
    monkeypatch.setattr(solver_backend, "_slepc_module", lambda: None)
    matrix = csr_matrix(np.eye(2))

    with pytest.raises(InputValidationError, match="petsc4py"):
        solver_backend.solve_with_petsc(matrix, np.ones(2), "direct", {})
    with pytest.raises(InputValidationError, match="slepc4py"):
        solver_backend.solve_with_slepc(matrix, matrix, 1, {})


def test_linear_solver_resource_estimate_keeps_dense_cost_visible() -> None:
    from solveur.core.linear_policy import LinearSolverPolicy

    matrix = csr_matrix(np.diag(np.ones(12)))
    selection = LinearSolverPolicy.assess(matrix, "direct", {})

    assert selection.dense_memory_estimate_bytes == 12 * 12 * np.dtype(float).itemsize
    assert selection.to_dict(used_method="direct")["resource_estimate"]["dense_memory_estimate_bytes"] > 0
