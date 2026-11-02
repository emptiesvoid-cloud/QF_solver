# QF Solver 0.2.12 P1/P2 Remediation Report — Second Review

## Final numerical follow-up (Owner directive)

This addendum resolves the DA-003 and DA-005 counterexamples found during the second independent review. It supersedes that review's interim `DEFECT_FOUND` disposition for those two items, subject to the limits below.

- **DA-003:** HEX20 still applies the existing signed, dimensionless determinant threshold. It now also rejects any sampled raw Jacobian determinant below the smallest normal IEEE-754 float. A positive subnormal determinant has fixed absolute spacing, so its relative error can dominate the integration weight. The `1e-107` regression now fails explicitly; regular stiffness tests at `1e-100` and `1e100` pass. No scientific quality threshold changed.
- **DA-005:** final residual validation computes a row-wise conservative floating-point error bound from absolute sparse products, with `math.fsum` for their magnitude sum. It combines that bound with the computed residual and uses an upper bound for the relative residual. If that upper bound exceeds the existing tolerance, or cannot be represented finitely, the solve raises `NumericalConvergenceError` with roundoff diagnostics. This catches the dot-product cancellation example although the ordinary sparse product reports zero. The exact zero-RHS/zero-solution case remains converged.
- The gate addresses whether the computed equation residual is within tolerance after accounting for arithmetic uncertainty. It does not equate residual with backward error, and neither quantity proves small forward or solution error for an ill-conditioned matrix. The solver makes no such precision guarantee.
- Regression tests were run red against the prior code: the HEX20 `1e-107` case was accepted and the direct cancellation case did not raise. Both pass after the guards. The former small-CG false convergence remains rejected with relative residual 1. The well-conditioned direct and standard CG tests pass.
- Validation after this follow-up: 28 exact test-function nodeids, 51 case outcomes PASS; Ruff PASS; in-memory compilation of the four changed Python files PASS; `git diff --check` PASS. No controlled FEM, WP12, v7 smoke, benchmark, or full CI was run.
- The bound is deliberately conservative and can reject valid results for large rows or extreme scales. It establishes a residual upper bound under the floating-point operation model, not a forward-error guarantee. Matrix conditioning and solution error remain distinct. HEX20 elements with subnormal determinant are now rejected, including mathematically scaled coordinates; this is the declared supported-precision boundary, not a change to the geometric distortion criterion.

## Scope and identity

- Repository: `emptiesvoid-cloud/QF_solver`.
- Corrective PR: #119, branch `codex/qfsolver-0.2.12-p1-p2-remediation-20261102`.
- Audited PR head at start: `062b04f562bd52a5ac4340e255f09658d8c42112`.
- Target branch baseline: `emptiesvoids-cloud/0.2.12` at `d31614f59341d175d8e2daade92daf7d8149d199`.
- This report covers the additional corrections requested after independent review. No target-branch change, merge, tag, package build, controlled FEM campaign, or WP13 v7 smoke was performed.

## Findings and disposition

| Finding | Status | Cause and correction | Evidence and limits |
| --- | --- | --- | --- |
| DA-001 — Springs omitted by unsupported nonlinear routes | FIXED | The nonlinear static route uses its own nonlinear assembly path, which does not assemble the model's discrete spring terms. It now raises `InputValidationError` as soon as a valid nonlinear method is selected and before mesh validation or load assembly. The earlier geometric nonlinear and buckling guards remain. | Regression tests replace validation/assembly with fail-fast sentinels and verify spring cases stop at the guard. Spring-free models remain in the existing supported scopes. No nonlinear solve was run. |
| DA-002 — Unmeasured contact residual hidden in Markdown | FIXED | Contact metadata correctly has no measured residual and stores `null` with `residual_status=NOT_COMPUTABLE`; the Markdown writer omitted the status. It now prints that status and leaves the residual value unavailable. | JSON and Markdown tests pass. No residual was invented and no contact solve was repeated. |
| DA-003 — HEX20 raw determinant underflow | FIXED | The dimensionless determinant check can remain positive after the raw Jacobian determinant underflows to zero, while stiffness integration consumes the raw determinant. Geometry validation now also requires every sampled raw determinant to be finite and strictly positive. The existing scaled signed-determinant threshold remains in force. | Tests cover regular geometry, inverted and degenerate geometry, a positive geometry whose raw determinant underflows, extreme distortion, and stiffness at scales (10^{-100}) and (10^{100}). This does not establish mesh quality between integration points or general conditioning. |
| DA-004 — Nodal-load coercion and validation crash | FIXED | `from_raw` previously converted booleans and numeric strings with `float()`. It now accepts finite built-in or NumPy integer/float scalars and rejects booleans, strings, and non-finite values before conversion. The JSON numeric predicate now catches conversion overflow and reports an ordinary schema error for integers outside the finite float range. Directly constructed invalid models still return a validation failure; mechanical-rank and component checks are marked unrun when input validation has already failed, avoiding a crash during rank fingerprinting. | Tests cover JSON and Python input, oversized integers, NumPy booleans, non-finite values, accepted finite NumPy scalars, and strict JSON reaction serialization. The Python API admits NumPy scalar types that JSON itself cannot encode. Other `from_raw` coercions are outside this finding. |
| DA-005 — CG false convergence and unsafe residual norms | FIXED | Squaring very small residual entries in the previous Euclidean norm underflowed to zero. A zero norm ratio could then pass the residual gate even when the computed solution was inaccurate. Residual and reference norms now use scaled sum-of-squares evaluation; non-finite or unrepresentable norms cause a numerical failure. The zero-reference convention remains exact: (0/0=0), nonzero/0 is infinite. Residual failure limits accept only finite positive built-in/NumPy integer or floating scalars; booleans and strings are rejected. No tolerance default or threshold was changed. | Algebraic regressions reproduce the tiny CG false-convergence case, test very small and large norms including true norm overflow, complex vectors, zero references, ordinary CG, singular direct solve, and route-level tolerance rejection. No full harmonic or transient solve was run. |

## Before/after regression evidence

The new regressions were first exercised against the pre-correction code. They reproduced the silent spring-route continuation, the HEX20 underflow acceptance, the missing Markdown status, the CG underflow false convergence, and unsafe nodal-load input handling. During this pass, an added oversized-JSON-integer counterexample also reproduced an uncaught `OverflowError`; after the shared schema fix it is rejected through `InputValidationError`.

| Finding and counterexample | Regression nodeid | Before correction | After correction |
| --- | --- | --- | --- |
| DA-001 — `nonlinear_static` with a spring | `test_nonlinear_static_rejects_springs_before_mesh_or_load_assembly` | Reached validation/assembly sentinel | `InputValidationError` before either sentinel |
| DA-002 — unavailable contact residual | `test_contact_residual_status_is_visible_in_markdown_without_fabricating_a_value` | Markdown omitted `NOT_COMPUTABLE` | Status is visible; residual remains `None` |
| DA-003 — HEX20 scaled to (10^{-108}) | `test_hex20_rejects_underflowed_positive_geometry_before_stiffness` | Raw determinant could underflow while normalized geometry stayed positive | Rejected before stiffness integration |
| DA-004 — boolean/string/non-finite/oversized load | `test_from_raw_rejects_nonfinite_or_implicitly_coerced_nodal_load_values`; `test_json_schema_rejects_unrepresentable_integer_nodal_load_cleanly` | Implicit coercion, late failure, or uncaught `OverflowError` | Rejected at input/schema validation |
| DA-005 — CG system (A=[10^{-200}], b=[10^{-200}]), inaccurate zero iterate | `test_cg_rejects_underflowed_residual_instead_of_accepting_bad_solution` | Squared norms could become zero and satisfy the gate | Relative residual is 1; solver raises `NumericalConvergenceError` |
| DA-005 — Euclidean norm outside float range | `test_unrepresentable_norm_fails_the_residual_gate_conservatively` | Raw norm arithmetic could overflow or underflow | Non-finite norm is detected and the solver rejects it |

## Regression risks by correction

| Finding | Residual regression risk |
| --- | --- |
| DA-001 | Nonlinear callers that previously supplied springs and relied on their omission now receive an explicit error. No spring-free route behavior or nonlinear spring support was added. |
| DA-002 | Markdown now exposes the unavailable status. Consumers that assumed every residual cell is numeric must honor `residual_status`; JSON metadata already used `null`. |
| DA-003 | Geometries with an unrepresentable raw determinant now fail explicitly, including some mathematically scaled geometries. Tested finite stiffness remains available at (10^{-100}) and (10^{100}); no general conditioning guarantee is claimed. |
| DA-004 | Callers relying on strings, booleans, or non-finite nodal-load coercion now receive `InputValidationError`. Finite built-in and NumPy numeric scalars remain supported. |
| DA-005 | If a true norm exceeds floating-point range, the solver rejects the result even if a separately scaled ratio might be representable. This conservative false-failure risk prevents overflow from becoming false convergence. |

## Targeted tests executed

Each pytest invocation selected one exact test-function nodeid. Parameterized outcomes are counted individually. All 35 selected functions passed after the final source changes (64 case outcomes):

- DA-005: `tests/unit/test_da005_residual_contracts.py` — tolerance type/range validation, numeric-string rejection, accepted finite Python/NumPy tolerances, default CG, tiny-system false-convergence regression, underflow/overflow norms, complex norms, zero-reference behavior, singular direct solve, and static/harmonic/dynamic route validation.
- DA-003: `tests/unit/test_hex20_element.py` — unit-scale invariance, underflow rejection, small/large-scale stiffness, determinant overflow, severe positive distortion, inverted/degenerate geometry, and the existing stiffness/mass/rigid-mode test.
- DA-001: `tests/unit/test_p1_route_spring_rejections.py` — geometric nonlinear, buckling, and nonlinear static rejection before validation/assembly, plus spring-free scope checks.
- DA-004: `tests/unit/test_da004_nodal_load_validation.py` — invalid direct-model values, invalid `from_raw` values, accepted finite Python/NumPy values, oversized JSON integer rejection, and fixed-DOF reaction JSON serialization.
- JSON compatibility: `tests/unit/test_json_io.py::test_json_reader_rejects_invalid_boundary_and_load_fields` and `::test_json_reader_loads_tet4_model`.
- DA-002: `tests/unit/test_da002_contact_residual_metadata.py` — null JSON metadata and visible Markdown status.
- Mesh-validation compatibility: `tests/unit/test_mesh_validation.py::test_mesh_validation_accepts_valid_tet4` and `::test_mesh_validation_rejects_incompatible_dof`.

Static checks passed:

- Ruff on all changed Python source and test files.
- Python compilation of all changed Python source and test files.
- `git diff --check`.

No full test suite, complete CI matrix, controlled FEM qualification, WP12 campaign, package rebuild, or v7 smoke rerun was performed.

## Compatibility, package, and proof impact

- The existing finite default residual tolerances are unchanged. Numeric strings and booleans that were previously coerced are now invalid input.
- Finite Python integers/floats and NumPy integer/floating scalars remain supported for nodal loads. JSON continues to accept finite JSON numbers and reject booleans/strings.
- Spring support was not added to any nonlinear route.
- HEX20 geometry is now rejected where the raw determinant is zero/non-finite, even if its normalized determinant alone appears valid. Extremely scaled geometries whose raw stiffness measure cannot be represented therefore fail explicitly.
- Distributed solver source changed. The v7 wheel and sdist hashes and six smoke results remain historical evidence for their exact earlier artifacts; they do not verify a package rebuilt from this source. A new artifact contract and installed-package checks are required for a later candidate.
- No WP12 oracle, threshold, result, or ledger was changed.

## Remaining risks and limitations

- The HEX20 test samples the existing integration points. It does not prove positive Jacobian everywhere between samples or certify general mesh quality.
- A mathematically finite relative residual may be impossible to represent when its norm exceeds the floating-point range. The implementation fails conservatively in this case; this can produce a false failure for extreme magnitudes, but not a false convergence.
- The dynamic equilibrium summary retains its pre-existing unit floor for its reporting-only load reference. The Newmark convergence gate uses the scale-aware relative residual and no unit floor.
- Harmonic and transient convergence paths received stable norm integration and route-input tests, but no actual FEM response was executed under this mandate.
- The existing proof limitations DA-006/DA-007 and hypotheses DA-H01/DA-H02 remain open; this remediation does not reclassify them.

## Verdict

**`REMEDIATION_READY_FOR_FINAL_REVIEW`** — the five requested P1/P2 corrections, including the DA-003 and DA-005 follow-up guards, have targeted regression evidence; Ruff, compilation, and diff checks pass. This verdict does not authorize merge, qualification, package release, tagging, or publication.
