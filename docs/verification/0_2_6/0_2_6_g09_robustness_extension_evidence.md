# 026-G09 Robustness Extension Evidence

Status: **PASS_WITH_LIMITATIONS**; official G09 closeout remains **PASS_WITH_LIMITATIONS**.
Source SHA: `b09d8ddc98f8f54d9204d3d45cd9a8e07e7edbd6`; dirty: `False`.

This extension adds controlled evidence only. It does not add contact physics or alter the numerical solver.

## Campaign summary

| Category | Cases | Result |
|---|---:|---|
| penalty_mesh | 15 | PASS |
| activation | 8 | PASS |
| geometry | 13 | PASS |
| cycles | 4 | PASS |
| rollback | 4 | PASS |
| phase_rollback | 5 | PASS |
| adversarial | 6 | PASS |
| Total extension cases | 55 | PASS_WITH_LIMITATIONS |

## Requirement reassessment

The 18 historical requirements are preserved as `SUPPORTING_EVIDENCE_ONLY`.
Counts: `{'FULL_CANDIDATE': 4, 'BOUNDED': 11, 'DEFERRED': 3, 'FAIL': 0}`. Deferred requirements remain deferred; no acceptance criterion was weakened.

## Penalty and mesh matrix

The five penalty values are observational probes. The normalized value uses the benchmark `E=10`, `L=1` only as a reporting coordinate; it is not a universal scaling law.

| Mesh | Penalty | Penetration | Reaction | Displacement | Residual | Iterations | Penalty energy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1e+02 | 1.56561093e-01 | 1.93035879e+01 | 1.85245335e+00 | 1.784e-15 | 2 | 1.22556879e+00 |
| 1 | 1e+03 | 1.61833496e-02 | 1.93445870e+01 | 1.62761159e+00 | 6.753e-15 | 2 | 1.30950402e-01 |
| 1 | 1e+04 | 1.62380333e-03 | 1.93495444e+01 | 1.60429170e+00 | 2.201e-13 | 2 | 1.31836863e-02 |
| 1 | 1e+05 | 1.62435220e-04 | 1.93500493e+01 | 1.60195104e+00 | 8.288e-13 | 2 | 1.31926004e-03 |
| 1 | 1e+06 | 1.62440711e-05 | 1.93500999e+01 | 1.60171689e+00 | 2.173e-11 | 2 | 1.31934923e-04 |
| 2 | 1e+02 | 1.65584007e-01 | 1.90752548e+01 | 1.81506553e+00 | 1.651e-15 | 2 | 1.37090317e+00 |
| 2 | 1e+03 | 1.69971306e-02 | 1.91747535e+01 | 1.58368374e+00 | 2.807e-14 | 2 | 1.44451224e-01 |
| 2 | 1e+04 | 1.70422856e-03 | 1.91853109e+01 | 1.55986939e+00 | 3.713e-13 | 2 | 1.45219750e-02 |
| 2 | 1e+05 | 1.70468143e-04 | 1.91863730e+01 | 1.55748100e+00 | 1.396e-12 | 2 | 1.45296940e-03 |
| 2 | 1e+06 | 1.70472673e-05 | 1.91864793e+01 | 1.55724209e+00 | 1.891e-11 | 2 | 1.45304662e-04 |
| 4 | 1e+02 | 1.67139355e-01 | 1.89646812e+01 | 2.12546339e+00 | 6.182e-15 | 2 | 1.39677820e+00 |
| 4 | 1e+03 | 1.71362671e-02 | 1.90824214e+01 | 1.85229458e+00 | 2.115e-14 | 2 | 1.46825825e-01 |
| 4 | 1e+04 | 1.71796771e-03 | 1.90947909e+01 | 1.82421650e+00 | 1.460e-14 | 2 | 1.47570653e-02 |
| 4 | 1e+05 | 1.71840302e-04 | 1.90960341e+01 | 1.82140087e+00 | 5.493e-13 | 2 | 1.47645447e-03 |
| 4 | 1e+06 | 1.71844656e-05 | 1.90961584e+01 | 1.82111923e+00 | 6.619e-11 | 2 | 1.47652930e-04 |

Force/moment equilibrium check: `PASS`; moment evidence: `True`; deterministic mesh replay: `True`.
Mesh changes at `1e5`: `[{'from': 1, 'to': 2, 'reaction_relative_change': 0.008458702778432019, 'displacement_relative_change': 0.027759927745920464}, {'from': 2, 'to': 4, 'reaction_relative_change': 0.0047084946616538555, 'displacement_relative_change': 0.16945302777321938}]`.

## Activation and geometry

| Case | Status | Active | Observed gap | Residual/force diagnostic |
|---|---|---:|---:|---:|
| `positive_epsilon` | `PASS` | False | 1.00000000e-08 | 0.000e+00 |
| `zero_gap` | `PASS` | False | 0.00000000e+00 | 0.000e+00 |
| `negative_epsilon` | `PASS` | True | -1.00000000e-08 | 1.173e-03 |
| `small_positive_gap` | `PASS` | False | 1.00000000e-05 | 0.000e+00 |
| `small_negative_gap` | `PASS` | True | -1.00000000e-05 | 1.173e+00 |
| `deep_negative_gap` | `PASS` | True | -1.00000000e-02 | 1.173e+03 |
| `global_open_close` | `PASS` | True | -1.62435220e-04 | 0.000e+00 |
| `global_close_open_recontact` | `PASS` | True | -1.62435220e-04 | 0.000e+00 |

Activation boundary: `gap >= 0` is inactive and negative gap is active in the existing operator. No attraction was observed: `True`.
Geometry orientation cases: `13`; all PASS: `True`.

## Cycles and transactions

| Case | Cycles | Steps | Final reference difference | Energy trace | Status |
|---|---:|---:|---:|---:|---|
| `10_cycles_amp_1` | 10 | 21 | 1.530e-15 | True | `PASS_INTERNAL_RESEARCH` |
| `20_cycles_amp_1` | 20 | 41 | 1.305e-15 | True | `PASS_INTERNAL_RESEARCH` |
| `50_cycles_amp_1` | 50 | 101 | 1.305e-15 | True | `PASS_INTERNAL_RESEARCH` |
| `10_cycles_amp_0.5` | 10 | 21 | 1.410e-15 | True | `PASS_INTERNAL_RESEARCH` |

| Rollback case | Rejected increments | Attempts | Retry digest clean | Reference error | Status |
|---|---:|---:|---:|---:|---|
| `RB-01` | 1 | 3 | True | 4.514e-09 | `PASS_INTERNAL_ROLLBACK` |
| `RB-02` | 1 | 3 | True | 6.743e-09 | `PASS_INTERNAL_ROLLBACK` |
| `RB-03` | 1 | 4 | True | 4.534e-09 | `PASS_INTERNAL_ROLLBACK` |
| `RB-04` | 1 | 7 | True | 4.903e-12 | `PASS_INTERNAL_ROLLBACK` |

### Phase-specific rollback

| Phase | Rejected increments | Attempted contact | Failed-trial contact | State preserved | Energy trace | Reference error | Status |
|---|---:|---|---|---:|---:|---:|---|
| `before_activation` | 1 | False | False | True | True | 0.000e+00 | `PASS_INTERNAL_ROLLBACK` |
| `during_activation` | 1 | False | True | True | True | 0.000e+00 | `PASS_INTERNAL_ROLLBACK` |
| `just_after_activation` | 1 | True | True | True | True | 0.000e+00 | `PASS_INTERNAL_ROLLBACK` |
| `during_separation` | 1 | True | False | True | True | 0.000e+00 | `PASS_INTERNAL_ROLLBACK` |
| `during_recontact` | 1 | False | True | True | True | 0.000e+00 | `PASS_INTERNAL_ROLLBACK` |

State integrity: `True`. Contact state remains stateless and is recomputed from trial geometry.

## Failure contract

| Case | Status | Deterministic | Fail closed | No silent pass |
|---|---|---:|---:|---:|
| `invalid_penalty` | `EXPECTED_FAILURE` | True | True | True |
| `invalid_target` | `EXPECTED_FAILURE` | True | True | True |
| `invalid_master_geometry` | `EXPECTED_FAILURE` | True | True | True |
| `unsupported_contact_route` | `EXPECTED_FAILURE` | True | True | True |
| `excessive_penetration` | `EXPECTED_FAILURE` | True | True | True |
| `newton_max_iterations` | `EXPECTED_FAILURE` | True | True | True |

## External evidence basis

Status: `PASS_WITH_LIMITATIONS`; execution mode: `REUSED_CONTROLLED_ARCHIVE`; new external run: `False`.
Archive: `qualification/0_2_6/g09_lot3_evidence.json` at source SHA `c76d4af39dc270a05596a53ef2d93baa9171c29b`; source dirty: `False`.
External mesh levels: `['mesh8', 'mesh6']`; load points: `10`.
Active branch errors: `{'displacement': 4.024558464266181e-15, 'gap': 4.0245584642661925e-16}`; transition warnings: `[0.04339979885207582, 0.052565319500610296]`.
The two levels support a bounded mesh-sensitivity observation only. They do not establish a universal external curve tolerance for the exact-unilateral versus penalty transition.

## Limitations and decision

- The extension remains bounded to the existing TET4 node-to-triangle penalty route.
- No friction, general surface-to-surface, self-contact or new contact physics is qualified.
- Penalty candidate values are observational and remain Owner-reviewable; no universal range is approved.
- External evidence is reused from the controlled Lot 3 Code_Aster/CalculiX archive; no new external claim is created.
- The active set is stateless in the exercised frictionless route; generic and phase-specific rollback cover common-driver mutable state before activation, during activation, after activation, separation and recontact.

No bug was found. The official G09 status remains `PASS_WITH_LIMITATIONS`; this extension does not create an Owner-approved production penalty range.
