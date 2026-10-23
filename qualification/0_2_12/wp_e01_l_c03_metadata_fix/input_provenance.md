# C03 archived input provenance

## Source and archive identity

`archive_inputs.py` is an offline verifier and extractor. It reads the archived case JSON and frozen source only; it imports no solver, constitutive kernel, assembly, FEM, NumPy, SciPy, or pytest module. It verifies each archive manifest's complete file set, sizes, and SHA-256 values before extraction. It checks the historical checkout is clean at commit `87e54913077c7d9fce6f259fb4a4a11f5295e6a5`, tree `c42e3c2241af1862d66cab51a38fda74a1167361`, checks all 29 archived production pins, and checks the serializer capture source commits and file hashes recorded by each campaign. The resulting identities are recorded in `archive_inventory.json`.

The probe campaign itself is globally `INCOMPLETE`: it completed the four TET4 cases, timed out after starting one HEX8 case, and did not start the remaining three HEX8 cases. The separate HEX8 archive completed all four HEX8 cases. Together the two verified archives contain all eight complete case records. The timeout and archive-level campaign statuses are retained; no missing action record was recreated.

## Exact frozen values

The archived `observed_data` for each complete action contains the full input fields needed for the mathematical model:

- `nodes`, `elements`, and `base_state_displacement_m`;
- all integration-point values in `accepted_history`, including the full plastic-strain vector and equivalent plastic strain;
- `centered_difference_observations[*].full_projected_direction`;
- `production_trial_state_by_integration_point` and its archived `elastic` branch bit.

These are JSON arrays/numbers emitted by the archived capture path. The hashed `support.py` implementation passes finite Python floats through as floats and converts arrays using `tolist()`; its JSON writer uses Python's standard `json.dumps` with `allow_nan=False`. JSON float spellings therefore round-trip to the exact original binary64 value. The extractor maps each float to its exact `as_integer_ratio()` value. It does not interpret decimal report strings as exact inputs.

For each case, the extractor restores integer element keys and independently recomputes the frozen `state_digest` canonical payload using each float's `float.hex()` representation. Both archived `accepted_history_digest_before` and `accepted_history_digest_after` must match. The resulting eight verified digests are in `archive_inventory.json`; directions within a base state share its digest, giving four distinct accepted histories.

Each per-action proof input carries exact rational point intervals for source material constants, mesh coordinates, base displacement, and the full archived direction. Each per-point record carries exact point intervals for incoming plastic strain and equivalent plastic strain, in addition to the complete history digest and derived trial deviator tensors. The perturbation domain is exactly the Owner's rational `[-1/10000, +1/10000] m`; it is not formed by converting a binary64 `1e-4` value.

The historical test's `_d` helper uses `Decimal.from_float(float(value))`. Thus the exact rational inputs here correspond to the frozen binary64 material constants, hardening values, and archived state. The constants are `E=210.0e9`, `nu=0.30`, and `sigma_y0=250.0e6` as source binary64 literals; `H` comes from the frozen case parameter (`0` or `1.5e9`). `R = sigma_y0 + H*alpha_n` is formed exactly from those rational inputs. Segment endpoints are exactly `-1/10000 m` and `+1/10000 m`.

## Independent kinematic reconstruction

The extractor derives the small-strain base and direction tensors from nodal displacement inputs and reference shape gradients. TET4 gradients are solved over exact rational coordinates. HEX8 connectivity is checked against the frozen standard local-node ordering and the archived 0.5 m axis-aligned cells. The historical integration-point order is `product((-1, 1), repeat=3)` with the last axis varying fastest. The exact-real reference quadrature coordinate `±1/sqrt(3)` is enclosed by a 192-bit dyadic rational interval whose endpoints are verified by exact integer-square comparisons.

The target for A/B/C is the source-level small-strain J2 mathematical path with exact-real arithmetic on the frozen binary64 inputs and exact-real `±1/sqrt(3)` quadrature. This enclosure also contains the historical Decimal-80 quadrature approximation; it does not claim to reproduce the rounded binary64 quadrature values or arithmetic executed by production. For each point, trial deviator base/direction tensors are stored as rational intervals; their Frobenius products generate outward rational intervals for `A (Pa²)`, `B (Pa²/m)`, and `C (Pa²/m²)`. `R` is stored in Pa. No observed margin, sampled branch result, force, or report value is used to select coefficients or interval widths.

## Production-branch linkage

The branch actually archived at the base state is preserved point-by-point from `production_trial_state_by_integration_point[*].elastic`. The production code classifies from `yield_value = q_trial - current_yield` and branches on `yield_value <= 0`. For plastic points, the archived trial-state object carries corrected stress and a post-return `yield_function` of zero; it does not directly preserve pre-return `q_trial` or `yield_value`. It does preserve the production `plastic_multiplier`, `yield_stress`, and `elastic` fields. For elastic points, the archived `yield_function` is the pre-return trial value.

The separate `production_branch_budget.py` performs this inverse-division enclosure using exact rational outward intervals around each frozen binary64 operation in the denominator and the two neighboring binary64 quotient values around the archived plastic multiplier. It reports that the plastic production yield value itself is unavailable; the interval is a rigorous enclosure, not an exact recovery. Elastic points use the exact archived binary64 pre-return `yield_function`. The helper compares each production enclosure to the exact-real base margin, derives the a-posteriori discrepancy `B=max|Yprod-G0|`, and requires the exact-real base clearance to exceed `B`. It separately checks the decisive extremum over the whole exact-real segment. This `B` is an a-posteriori base-state discrepancy only; it is not represented as an a-priori error bound for reevaluating the perturbed path in floating point.

## Candidate interval evaluation

`integrate_proofs.py` revalidates the archive and source hashes, regenerates the exact proof inputs, checks the exact eight action IDs and expected per-action point counts, and evaluates all 304 point records (12 TET4 points per action, 64 HEX8 points per action). Every point has a strict exact-real candidate sign matching the archived expected branch and a passing production base linkage / segment-sign check. The technical aggregate is `PASS`, with eight action proofs and 304 points. The owner-facing status is `C03_PROOF_READY_FOR_OWNER_REVIEW`, with certificate status `PROPOSED_NOT_PROMOTED`; this worker result does not promote a qualification certificate. Nonpassing technical aggregates map separately to owner-facing `C03_PROOF_PARTIAL`, `C03_PROOF_INCONCLUSIVE`, or `C03_PROOF_INVALID`, while preserving the underlying technical verdict. Exact point bounds, G0 values, production enclosures, discrepancy bounds, and source references are in the per-action `*.proof_result.json` files; hashes and point counts are in `proof_action_summary.json` and `archive_inventory.json`.
