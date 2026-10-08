# WP08-R2 — Corrected corotational J2 state and internal force kernel

**Status of this bounded implementation:** PASS for the force/state kernel only. This is not WP08 closure, nonlinear qualification, or authorization to use the corrected route in a global Newton solve.

## Scope and frozen traceability

R2 was implemented on `codex/v0.2.12-wp08-r2-constitutive-forces`, based on R1 commit `8fc7eb90b5e0063a58acb3f7e788edd517e223ca`. Before mechanical source edits, the equation-to-function-to-independent-test mapping was committed as `f0bc55e91f795c1ea736a181b71636c180dce5e9` in `wp08_r2_equation_implementation_test_map.json`. The mapping was frozen before implementation; its preregistered test-name entry for the global Newton guard is a shorter name than the final test name, whose suffix additionally verifies the legacy default. No R1 acceptance threshold was changed.

The implementation is bounded to the existing small-local-strain corotational solid J2 kernel, using `F=R U`, `E_B=U-I`, the existing isotropic small-strain J2 radial return, and the exact polar-adjoint force map. It does not introduce multiplicative plasticity, alter the global Newton algorithm, or complete R3 result/checkpoint migration.

## Implemented path

For each integration point, the explicitly selected corrected element now performs:

1. Form and validate `F`; compute its right polar decomposition `F=R U` by SVD.
2. Reject nonfinite tensors, `det(F) <= 1e-10`, invalid polar factors, failed reconstruction/orthogonality checks, and `||U-I||_F > 0.05`.
3. Set material-frame Biot stretch strain `E_B=U-I`. The accepted material state is not rotated with `R`.
4. Validate a detached corrected state (`corotational_j2_state/v2`) and call the existing `evaluate_constitutive` J2 return. No second return-map implementation was added.
5. Construct the conjugate nominal stress using the R1 polar adjoint. In an eigenbasis of `U`, `Pbar_ii=T_B,ii`, `Pbar_ij=2 lambda_i T_B,ij/(lambda_i+lambda_j)`, and `P=R Pbar`.
6. Integrate `f_int[a,i] = sum_q w_q P[i,J] N[a,J]` from reference gradients and return a detached trial state.

The polar directional derivative is implemented from the skew Sylvester equation `Omega U + U Omega = A-A^T`, where `A=R^T deltaF`, followed by `deltaU=sym(A-Omega U)`. The eigenvalue denominators are sums of positive stretches, not differences, so repeated stretches do not require arbitrary eigenvector derivatives. The production force uses the exact adjoint formula, not finite differences.

Raw reconstructed measures are computed without symmetrization: `S=solve(F,P)` and `sigma=P F^T/J`, with a determinant consistency check. Symmetry and the angular identity are checked on the unsymmetrized tensors. `P` may be nonsymmetric; this is expected. Any loss of the expected PK2/Cauchy symmetry is an error, not something repaired by averaging.

## State and transaction boundary

The corrected material state is explicitly identified by:

- formulation: `corrected_corotational_biot_j2/v1`;
- state schema: `corotational_j2_state/v2`;
- stress semantics identifier: `corotational_stress/v2`.

Plastic strain is stored as a deviatoric material/reference-frame tensor in the repository's engineering-strain Voigt convention; equivalent plastic strain is a nonnegative scalar. The corrected state records intrinsic rate-independent dissipation `sigma_y alpha` and hardening energy `H alpha^2/2`, and does not relabel the legacy trapezoidal plastic-work field. State validation rejects legacy/unknown schemas, material-identity mismatch, malformed or nonfinite fields, nondeviatoric plastic strain, and inconsistent scalar history. Each trial begins from the accepted state. The existing `StateTransaction` is used to verify rollback and commit behavior; the element itself returns detached trial state and does not mutate its accepted input.

The material identity hashes the exact constitutive material type and the material parameters consumed by this local law. It is not a full physical/model/operator identity: geometry, units, integration configuration, and model provenance remain the responsibility of future checkpoint/result identity work. R2 does not add checkpoint migration or claim restart compatibility.

## Scope safety and legacy behavior

Legacy remains the default `legacy_corotational_j2/v1` path. Its historical force, state transport, output behavior, and finite-difference tangent were not replaced. The corrected element can be instantiated explicitly for bounded kernel verification, but its production tangent and generic integration-point results raise a clear not-ready error. The nonlinear assembly and solver validation boundaries reject an explicitly selected corrected formulation before global Newton assembly, and reject unknown formulation identifiers. Thus the corrected force is not silently paired with the legacy tangent.

R2 has not implemented public serialization, corrected checkpoint resume, aggregate result semantics, or a migration from legacy state. Those outputs/restarts must remain unavailable for the corrected route until R3. Direct force/state tests are not a production analysis route.

## Verification summary

The independent checks and measured values are itemized in `wp08_r2_constitutive_forces_evidence.json`, with narrative in the companion reports.

- Current targeted impacted campaign: **196 passed** in 22.90 s, covering corrected and legacy corotational J2, material state transactions, TL J2, checkpoints/assembly plans, WP02–WP07 integrations.
- Full `tests/unit` campaign: **3,303 passed, 93 skipped, 0 failed**, 1,321.29 s. This run preceded the final small fail-closed guard/test edits; it is recorded as a completed broad regression run, not exact-final-tree evidence. The focused 196-test run was rerun after those edits.
- Ruff on modified Python files: pass.
- Targeted mypy on three modified source files: pass, no issues.
- Ruff format check on the new test file: pass. The three touched production files have pre-existing format drift at the R1 baseline; unrelated whole-file formatting changes were deliberately avoided.
- `git diff --check`: pass.

For a bounded two-step noncoaxial TET4 plastic history, legacy relative Cauchy skew was `1.9435682829880684e-2`; corrected Cauchy skew was `1.309077983855475e-16`, corrected PK2 skew `1.316278678438816e-16`, and normalized resultant moment `7.983988316015165e-18`. The corrected/legacy internal-force relative difference was `5.476930316979128e-3`; this is an expected semantic change, not calibrated away. The plastic multiplier/history scalar was unchanged in this comparison (`alpha=0.01485788113695092`). Independent nodal finite differences of a separately coded local incremental potential gave force-gradient scaled errors from `9.98e-11` to `1.82e-7` across elastic, active-plastic, and noncoaxial smooth-branch cases, below the preregistered `2e-6` criterion.

These are implementation verifications on bounded fixtures, not qualification, a global equilibrium convergence campaign, or general finite-strain validation.

## Performance characterization

On the same local environment, median bounded element-kernel timings were:

| Fixture | Integration points | Legacy force/state | Corrected force/state | Ratio | Corrected traced peak |
|---|---:|---:|---:|---:|---:|
| TET4 | 1 | 338.994 μs | 616.220 μs | 1.818 | 10,661 bytes |
| HEX20 | 27 | 9,361.342 μs | 17,219.867 μs | 1.839 | 217,197 bytes |

The corrected microkernel medians were 90.613 μs for polar kinematics, 50.201 μs for the polar stretch derivative, and 260.627 μs for the material return. Serialized state sizes were 864 bytes (TET4) and 23,317 bytes (HEX20); internal diagnostic state sizes were 3,236 and 90,141 bytes respectively. `tracemalloc` observes Python-traced allocations and may omit native NumPy allocations. These fixtures do not establish scaling or industrial performance. No optimization was attempted.

## R3 boundary and disposition

The historical tangent is not demonstrated to be the derivative of the corrected force. Corrected global Newton is therefore **NOT_READY**. The production consistent tangent, active-set/generalized derivative treatment, final output aggregation/serialization, checkpoint identities/migration, and integrated nonlinear equilibrium verification remain R3 work. R2's force-gradient oracle is not a replacement tangent and must not be used to claim Newton readiness.

`WP08_STATUS`, `QF0212_G03_NL`, and `QF0212_G04_NL` remain **BLOCKED**. Historical G03 remains `FAIL_PRESERVED`; historical WP14 remains `HOLD_NOT_PROMOTED`; `WHOLE_REPOSITORY_ARCHIVE_CLEARED` remains `NO`. No maturity or qualification is promoted.

## Files in the R2 implementation commit

- `src/solveur/elements/solid/corotational_j2.py`
- `src/solveur/core/assembly/nonlinear.py`
- `src/solveur/core/nonlinear/solver.py`
- `tests/unit/test_corotational_j2_corrected.py`
- the six WP08-R2 report/evidence files in this directory

The equation/test map is a separate, earlier preimplementation commit. No R1, audit, historical qualification, or WP00/WP01 contract file was modified.
