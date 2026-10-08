# WP08-R2 — Objectivity and plastic-state verification

## Question and contract

The R1 model uses the right polar split `F=R U` and material-frame Biot stretch strain `E_B=U-I`. The constitutive point state is attached to the fixed material/reference frame, not transported by the current polar rotation. R2 retains the existing associative J2 linear-isotropic-hardening return; it changes the kinematic input and state contract, not the material law family.

For a superposed proper spatial rotation `Q`, `F*=QF` gives the same `U` and a rotated `R`. Therefore `E_B`, accepted material state, and local Biot-conjugate stress must be invariant; `P` transforms as `Q P`, PK2 remains invariant, and Cauchy transforms as `Q sigma Q^T`. R2 compares the raw values; it does not rotate constitutive history or symmetrize stresses to improve a metric.

## Material state and transaction behavior

Corrected states use `corotational_j2_state/v2`, explicitly carry `corrected_corotational_biot_j2/v1`, and bind to a hash of material type and constitutive parameters. The tensor state contains the existing six-component engineering-Voigt plastic strain, strain, and stress. Plastic strain is checked symmetric/deviatoric in tensor interpretation. The scalar `equivalent_plastic_strain` is nonnegative and monotone; `plastic_dissipation=sigma_y alpha` and `hardening_energy=H alpha^2/2` are checked against the same accepted history.

The local update delegates to the repository's `evaluate_constitutive` radial return. Each trial validates and copies the accepted corrected state, and emits a separate trial mapping. A superposed rigid spin that leaves `U` fixed therefore causes no local strain increment, plastic increment, or artificial material-state rotation. Tests compare state before and after rotation on virgin and plastically preloaded paths, and compare an independently coded tensor radial-return oracle for elastic, active-plastic, unload/reload, reverse, and noncoaxial increments.

`StateTransaction` tests verify rollback leaves the accepted state unchanged and commit applies only the selected trial. Material mismatch, legacy/unknown formulation, malformed arrays, nonfinite values, nondeviatoric plastic strain, and inconsistent dissipation/hardening scalars are rejected. This verifies the local transaction seam; it does not implement a corrected global checkpoint format.

## Bounded results

The preregistered R1 rigid-spin and objectivity tests pass for the tested tensors and histories. Corrected Cauchy and PK2 are reconstructed from the nominal stress and remain symmetric within the frozen `1e-10` relative-skew limit without post-hoc averaging. A bounded two-step noncoaxial TET4 history reduced Cauchy relative skew from `1.9436e-2` on the legacy path to `1.3091e-16` on the corrected path; corrected PK2 skew was `1.3163e-16`. The corrected normalized element resultant moment was `7.9840e-18`.

These are implementation-level checks on selected solid fixtures. The independent material point oracle and incremental-potential gradient support the implemented local history and force mapping. They do not prove universal constitutive validity beyond the frozen small-local-strain domain, and they are not a global nonlinear qualification.

The corrected and legacy force results differ by about `0.5477%` on the cited noncoaxial fixture, while the compared equivalent plastic strain is the same. This is recorded as an expected consequence of the changed nominal stress mapping, not treated as an error to tune away. Other histories may differ differently; no general equivalence claim is made.

## Limits

- The local constitutive update is existing small-strain associative J2 with linear isotropic hardening applied to bounded `E_B`; no multiplicative plastic deformation gradient is introduced.
- The R1 stretch-strain norm cap is `0.05`; determinant floor is `1e-10`.
- The corrected material hash is not a complete model, units, geometry, integration-rule, or checkpoint identity.
- Result aggregation and corrected checkpoint resume are unavailable pending R3.
- The global corrected Newton route is explicitly rejected because no compatible production tangent has been validated.
- The tests exercise TET4, TET10, HEX8, and HEX20 fixtures separately; evidence for one family is not substituted for another.

## Test evidence

The focused current-tree campaign passed 196 tests, including corrected objectivity/plasticity, legacy J2, TL J2, material transactions, checkpoint guards, and WP02–WP07 regression surfaces. The broader unit run recorded 3,303 passed and 93 skipped with no failures, but preceded the final small fail-closed guard/test edits. Exact final state is therefore supported by the rerun focused campaign, not by a claim that the entire unit suite was rerun after every last edit.
