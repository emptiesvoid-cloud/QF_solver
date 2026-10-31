# WP13 P0 installed-package FEM smoke decision dossier

**Status:** `PREPARED_NOT_AUTHORIZED`
**Purpose:** Request one bounded Owner decision for installed wheel/sdist solve
smokes. No FEM has run under this dossier.

## Frozen candidate and artifacts

| Identity | Value |
|---|---|
| PR | #114, `codex/wp13-release-engineering-20261031` |
| PR #114 HEAD during v6 artifact verification | `d6a49a279b4d8ce548e4d6ed1f48e8cad6f20e23` |
| P0 workflow execution commit | `2865587a44f9e461a0b4e4286c912c17e4f04be5` |
| Release base | `ab137051d920d7fa9aae9a3012a48b2b26e2198b` |
| Package source SHA | `2865587a44f9e461a0b4e4286c912c17e4f04be5` |
| Contract | `QF-0212-WP13-SELECTED-CANDIDATE-20261031-06` |
| Contract file SHA-256 | `f33a72b182439774828f8e604d6ab234bbf206c697c0f1082d7bc0ef81003db9` |
| Bounded smoke controller | [`scripts/wp13_package_smoke.py`](../../scripts/wp13_package_smoke.py), SHA-256 `83dbd60bbc481ee7dbae90dd5052454508ec3da65e42039888d9b92a9a386571` |
| Exact smoke manifest | [`wp13_p0_package_smoke_manifest_20261031_v1.json`](wp13_p0_package_smoke_manifest_20261031_v1.json), SHA-256 `2dc2badf59c1a35aff44fcb5763eaac4e0e55b73857be878b660c3bd0430addb` |
| Wheel (run 1 and run 2) | `qf_solver-0.2.12-py3-none-any.whl`, 1,689,662 bytes, SHA-256 `ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a` |
| Raw sdist (run 1) | `qf_solver-0.2.12.tar.gz`, 1,320,001 bytes, SHA-256 `f4aaafffc184c662808f061e2b234fe4d6623ae07f2a3c18f2d74721185f71e3` |
| Raw sdist (run 2; selected for the smoke dossier) | `qf_solver-0.2.12.tar.gz`, 1,320,067 bytes, SHA-256 `15c838af12c8401b61c561f5f079debc702e072241e9ee8c17cd5861cbf082e5` |
| Normalized sdist (both runs) | 1,294,049 bytes, SHA-256 `183bc4448d4a83c5e24d9c8b0d7f15e9e2cca37b63b25646d9ec030220611fde` |

The exact run-2 wheel and raw sdist were separately installed into clean
Windows Python 3.13.1 environments with dependency resolution. Their pip
reports, installed-source probes, and check-mesh logs are SHA-bound in
[`WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md`](WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md).
Each install verified 501 installed source files, CLI version/help, and three
check-mesh cases. Those checks did not assemble or solve a model. The v4
oracle sources, inputs, and solver files below were compared with the v6
source commit; the relevant solver code and examples are unchanged.

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
| `WP13-P0-DYNAMIC-01` / `SOV-DYN-SDOF-001` | `b40d7188143e4bcc73ee63407f426633490921075990bcad47bd25c9a188480b` (`examples/tet4_dynamic_sdof_free_vibration.json` as installed) | One TET4, four nodes, one free DOF; `E=1000`, `nu=0.25`, `rho=10`; undamped Newmark average acceleration, `dt=0.001 s`, 40 steps, initial UX `0.001`, initial velocity zero. The history is indexed 0–39 for steps 1–40: index 39 is step 40 at `0.040 s`. Check analytic initial energy, first recorded energy at `0.001 s`, final state energy, history energy and relative drift against `0.0001 J` at the frozen tolerances; dynamic and free-equilibrium residuals each `<=1e-10`. |

Installed input paths are under `E:\QFSolverAgents\wp13_deps_wheel_20261031_v6\examples\`
and `E:\QFSolverAgents\wp13_deps_sdist_20261031_v6\examples\`. For all
three files, the installed wheel and sdist copies are byte-identical. Their
parsed JSON values equal the corresponding frozen source examples; source and
installed file hashes differ because their serialized bytes differ.

The frozen oracle source files are
`src/solveur/verification/analytical_references.py` and
`src/solveur/verification/campaign.py`, with v6 Git-blob byte SHA-256 values
`38ae37e1ff40844eedf7c2ca5b95d9d03f3fe660670036b05895c5043c96fb6c` and
`ea06968dc65927791549d698d19eeae33b6a3ad3e466ed2da0b87ae45e8952f1`.
The earlier values `cdda2add…` and `580f736e…` are Windows working-tree
hashes after CRLF conversion; they are not Git-blob hashes. The immutable
`qualification/campaign.json` SHA-256 remains
`8750d29a9d52498ec5051f4850c600232b0e7a4515905a8354f4a34771fd92cf`. The
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
checkout. It does not represent imports from an installed wheel or sdist. The
registered development scopes are not WP13 package-smoke scopes. A dedicated
WP13 controller and exact manifest are now prepared, with their hashes above.
The controller allows only the six fixed artifact/case pairs, constructs
shell-free installed CLI arguments, rechecks the installed archives,
environments, inputs and frozen oracle-source hashes, and records execution
and numerical-oracle verdicts separately. It cannot claim
`QUALIFICATION_PASS`.

At this report revision, the no-FEM preflight route has not yet been executed
and no reservation exists. The controller requires an append-only synthetic
preflight plus an Owner decision bound to the controller, manifest, persisted
preflight report, synthetic no-FEM report and exact six-pair list. If any
bound identity changes, execution is refused.

**Decision requested after the synthetic preflight is recorded:** approve only
the six one-attempt solves above, in the fixed wheel-then-sdist order, with the
30-second per-attempt timeout, output caps, 512 MiB sampled RSS stop, exact
input hashes and analytical oracles, serial execution and stop-on-first-fail
rule. If the runner or preflight cannot meet the existing policy, the
solve-smoke gate will remain `BLOCKED`; no unbounded substitute is permitted.
