# WP13 P0 installed-package FEM smoke decision dossier

**Status:** `PREPARED_NOT_AUTHORIZED`
**Purpose:** Request one bounded Owner decision for installed wheel/sdist solve
smokes. No FEM has run under this dossier.

## Frozen candidate and artifacts

| Identity | Value |
|---|---|
| PR | #114, `codex/wp13-release-engineering-20261031` |
| P0 workflow execution HEAD | `3e2d5f07585b270bb1ac0157a911e94d59991735` |
| Release base | `ab137051d920d7fa9aae9a3012a48b2b26e2198b` |
| Package source SHA | `60c202a75d20c6dea1df35aab591bd3832d12c58` |
| Contract | `QF-0212-WP13-SELECTED-CANDIDATE-20261031-04` |
| Contract file SHA-256 | `f8c43bd1bad5987acb589c7735ac7a1e39e0f7119e50a49dd2061cd135954833` |
| Wheel | `qf_solver-0.2.12-py3-none-any.whl`, SHA-256 `8d3e571ce7d4ced533d7b97ed0bc0f7a91e29a3d530e3a1b406716fecf721b0e` |
| Raw sdist | `qf_solver-0.2.12.tar.gz`, SHA-256 `4d9e571583b3bd345abdbf4bca5f6b86e17d776c6d2a386019da32c8c0b8a44b` |
| Normalized sdist | SHA-256 `4fba0a1f1e700aaa6bf58c4cdd1a0edd5adea1145db886d5bf1903d30f460da1` |

The wheel and raw sdist were separately installed into clean Windows Python
3.13.1 environments with dependency resolution. Their install reports and
probes are SHA-bound in
[`WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v4.md`](WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v4.md).
Both prior v4 installed-artifact probes passed import-origin, CLI version/help,
and six check-mesh checks. Those checks did not assemble or solve a model.
The wheel/sdist and model inputs below remain bound to the same package source:
no `src/`, `tests/`, examples, `pyproject.toml`, or `MANIFEST.in` changes were
made after source `60c202a75d20c6dea1df35aab591bd3832d12c58`.

## Exact proposed cases

Each row is one exact case per installed artifact. Run serially, once each,
for six total solve attempts. Use the existing fresh wheel and sdist
environments, verify `solveur.__file__` resolves under the selected
environment's `site-packages`, and place input copies, outputs, logs, and
manifests under a new external run directory on E:. Do not use a source-tree
launcher or `PYTHONPATH` pointing at the checkout. The exact command shape is
the installed CLI `qf-solver solve --input <frozen-input> --output <fresh-output>`;
no override options are needed because analysis and method are in the JSON.

| Case ID / campaign reference | Input SHA-256 | Model and requested checks |
|---|---|---|
| `WP13-P0-STATIC-01` / `SOV-TET4-STATIC-001` | `5296102b955ae4ac83b341178a8a555feb87faa0e9a30abe9f77c29df21988b8` (`examples/tet4_static.json` as installed) | One TET4, four nodes, three free DOFs; isotropic linear elastic `E=210 GPa`, `nu=0.3`; direct linear static; `1000 N` at node 1 UX. Check `UX=2.1224489795918369e-08 m` and von Mises `3428.5714285714284 Pa` against the closed-form constrained TET4 oracle at relative tolerance `1e-12`; free relative residual `<=1e-9`; reaction resultant X `-1000 N` within absolute `1e-10 N`; relative force-balance error `<=1e-12`; linear-energy-identity error `<=1e-9`. |
| `WP13-P0-MODAL-01` / `SOV-MODAL-TET4-001` | `0d40df125888b467017d053795336cb8960f643c95a209c3c96379a50c689750` (`examples/tet4_modal_unit.json` as installed) | Same unit TET4 mesh and material, three free DOFs; `eigh`, three modes. Check first shear frequency `1619.5553821068941 Hz` against `sqrt(10*G/rho)/(2*pi)` at relative tolerance `1e-12`; maximum relative eigen residual, mass orthogonality, and stiffness-diagonal errors each `<=1e-10`. |
| `WP13-P0-DYNAMIC-01` / `SOV-DYN-SDOF-001` | `b40d7188143e4bcc73ee63407f426633490921075990bcad47bd25c9a188480b` (`examples/tet4_dynamic_sdof_free_vibration.json` as installed) | One TET4, four nodes, one free DOF; `E=1000`, `nu=0.25`, `rho=10`; undamped Newmark average acceleration, `dt=0.001 s`, 40 steps, initial UX `0.001`. Check initial and step-39 total energy against closed-form `0.0001 J` at relative tolerance `1e-10`; step-39 relative energy drift in `[-1e-10,1e-10]`; dynamic residual and free equilibrium residual each `<=1e-10`. |

Installed input paths are under `E:\QFSolverAgents\wp13_deps_wheel_20261031_v4\examples\`
and `E:\QFSolverAgents\wp13_deps_sdist_20261031_v4\examples\`. For all
three files, the installed wheel and sdist copies are byte-identical. Their
parsed JSON values equal the corresponding frozen source examples; source and
installed file hashes differ because their serialized bytes differ.

The frozen oracle sources are `src/solveur/verification/analytical_references.py`
(SHA-256 `cdda2add8ea2341bae0249746cd080e50a56c89b11793d2d412815c65171edfc`),
`src/solveur/verification/campaign.py` (SHA-256
`580f736efbf5a21caf95e5c563ead74dec369f6816294236f79c7bfe793eae72`), and
`qualification/campaign.json` (SHA-256
`8750d29a9d52498ec5051f4850c600232b0e7a4515905a8354f4a34771fd92cf`). The
static oracle is explicitly scalar closed form and has no element, assembly,
solver, NumPy, or SciPy dependency. The modal and dynamic oracle formulas are
the existing closed-form campaign equations, separate from element assembly.
The oracle source is pinned to the frozen source SHA, not imported from the
installed solver during the smoke comparison. The final runner/manifest must
record all three source hashes and the scalar expected values before execution.

The campaign's `qualification.maturity.overall` expectations are not smoke
acceptance criteria. A smoke may establish only `EXECUTION_PASS` and
`NUMERICAL_ORACLE_PASS`; it cannot produce `QUALIFICATION_PASS` or alter WP12
or capability maturity.

## Proposed execution limits and stop rules

- Exactly six attempts: three cases against the wheel install and the same
  three against the sdist install; serial execution; no retry.
- One four-node TET4 and at most three free DOFs; the dynamic case has one free
  DOF and 40 time steps.
- Per case: hard wall timeout 30 seconds, stdout/stderr cap 1 MiB each, fresh
  result output only. Record sampled process RSS with a 512 MiB soft ceiling;
  it is an observation unless the approved runner provides an enforceable OS
  limit.
- Stop the entire batch on any source/import mismatch, unexpected case
  selection, contract/manifest/preflight mismatch, timeout, output cap,
  convergence failure, or failed oracle. Preserve all original outputs; no
  automatic rerun.
- Run the cases only after a no-FEM synthetic preflight proves the authorized
  route `CLI -> preflight -> manifest -> reservation` using the exact approved
  runner. No reservation has been made.

## Controller compatibility and authorization gate

The repository's current `scripts/run_local_vv.py` accepts one exact pytest
nodeid per run and expects `solveur` to import from the scientific source
checkout. It rejects/does not represent an installed wheel or sdist import.
The registered development scopes are not WP13 package-smoke scopes. No
compatible WP13 controller, exact pytest nodes, manifest, preflight, or
reservation currently exists. The current candidate's CLI supports the
installed `qf-solver solve --input ... --output ...` route, but that alone is
not a policy-compliant execution controller.

**Decision requested:** authorize preparation of a minimal shell-free WP13
package-smoke runner/scope for only the six case/artifact pairs above, followed
by a synthetic no-FEM CLI-to-reservation preflight. The controller source,
exact manifest, independent-oracle constants, resource enforcement, and all
SHA-256 values must be frozen and reviewed in the PR before any reservation.
After those artifacts are reviewable, Owner approval must explicitly bind the
final manifest SHA and permit the six one-attempt solves. If this runner cannot
be made compatible without weakening existing gates, close the solve-smoke
gate as `BLOCKED` and do not substitute an unbounded command.
