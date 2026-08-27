---
doc_id: DOC-NL-025-027
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 J2 qualification report

## Scope and decision rule

This report covers `025-G01` only: J2 small-strain qualification on connected
TET4, TET10, HEX8 and HEX20 meshes, including constitutive paths, the
algorithmic tangent, material transactions, load-step sensitivity, mesh
trends, energy accounting, rollback/retry and the bounded Code_Aster
correlation. It does not qualify geometric nonlinearity, buckling,
arc-length, contact, friction or coupled gates.

The evidence is controlled by the `source_sha` and `dirty` fields in the
machine-readable manifests. Generated evidence is output produced after
checkout and is intentionally not committed into the source revision that it
describes.

## Controlled evidence

| Evidence | Artifact | Result |
|---|---|---|
| Internal J2 campaign | `results/vnv_0_2_5/g01_latest/summary.json` and `evidence_manifest.json` | `PASS_INTERNAL_J2` |
| Code_Aster correlation | `results/vnv_0_2_5/g01_code_aster_latest/summary.json` and `evidence_manifest.json` | `PASS_EXTERNAL_CORRELATION` |
| Targeted regression | J2 constitutive, state, cyclic, sensitivity, multi-element and evidence tests | `68 passed` |

The controlled replay regenerates both manifests on the final clean source SHA.
The recorded campaign used the pinned Code_Aster image
`simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`
and the command documented in the external manifest. TET10 uses the explicit
comparison convention `tet10_nonlinear_quadrature=code_aster_5`; the legacy
QF Hammer-4 rule remains the default for existing models.

## Measured results

### Constitutive and tangent

Elastic, near-yield, traction, compression, shear, reload, shear-cycle and
non-proportional states passed. The centered finite-difference tangent sweep
used steps `1e-5`, `1e-6`, `1e-7` and recorded a maximum relative error of
`2.1204721119376345e-10`, below the existing implementation limit `1e-6`.

### Four-family connected mesh

| Element | DOF | Newton iterations | Max relative residual | Final PEEQ | Plastic dissipation |
|---|---:|---:|---:|---:|---:|
| TET4 | 15 | 13 | `2.39e-08` | `5.305e-03` | `2.341e-04` |
| TET10 | 42 | 20 | `1.93e-08` | `9.991e-01` | `5.008e+00` |
| HEX8 | 36 | 21 | `3.39e-08` | `9.649e-02` | `4.824e-02` |
| HEX20 | 96 | 22 | `7.80e-08` | `1.149e+00` | `6.625e+00` |

All four rows reached positive plastic state, positive internal/external work
and passed the existing residual/work checks. The large differences in PEEQ
between families are recorded observations of this controlled two-element
benchmark; they are not interpreted as a defect without a formulation,
quadrature or mesh-convergence diagnosis.

### Energy balance

The ten-increment runs satisfied the existing test contract
`relative_balance_error < 1e-6` and `D_p >= 0` for every family. The maximum
relative balance errors were:

| Element | Relative balance error | Dissipation sign |
|---|---:|---|
| TET4 | `1.835e-12` | non-negative |
| TET10 | `5.490e-09` | non-negative |
| HEX8 | `8.645e-09` | non-negative |
| HEX20 | `1.800e-09` | non-negative |

This is an internal work-energy consistency check, not physical validation.

### Mesh and load-step studies

Mesh levels `1/2/4` and load paths `2/4/8` steps were executed for all four
families. The runs passed and provide trend evidence. No release threshold
for coarse-to-refined displacement, reaction, stress, PEEQ or energy change
was frozen before this campaign. Those acceptance bands therefore remain
`OWNER_DECISION_REQUIRED`; the observations cannot honestly be converted to
PASS by relabeling them.

For the reference-to-refined load-step comparison, displacement differences
were `2.46e-08` (TET4), `7.29e-06` (TET10), `5.03e-05` (HEX8) and `3.67e-05`
(HEX20). These are diagnostic values, not release limits.

### Rollback and retry

The adversarial run rejected one increment, preserved the committed state,
cut the retry increment to `0.5`, and converged on the retry path. The final
displacement relative difference against the small-step reference was
`1.25432459287778e-07`; the final PEEQ absolute difference was
`3.34527073576896e-09`. The exact committed-state transaction invariant
passed. A separate Owner decision is still required for any numerical band
placed on the reference-difference metrics.

### Code_Aster correlation

The common regular two-cell campaign produced `64/64 PASS` checks across
TET4, TET10, HEX8 and HEX20. Complete four-step histories were compared for
loaded displacement, reaction, stress and equivalent plastic strain, with
matched integration-point counts. The existing runner tolerance is `5e-3`
for each comparable scalar. This is bounded numerical correlation, not
physical validation and not an industrial qualification envelope.

## Acceptance bands and gate decision

The following table records the observed coarse-to-refined changes and the
only technically defensible proposal available without inventing a limit
after seeing the results: use a documented asymptotic/convergence criterion
for the selected observable and freeze its numerical band before promotion.
The numerical band and the reference observable still require Owner approval.

| Observable | Coarse-to-refined relative changes (TET4, TET10, HEX8, HEX20) | Proposed threshold | Margin |
|---|---|---|---|
| Displacement | `27.5%`, `31.7%`, `91.3%`, `52.5%` | `OWNER_DECISION_REQUIRED`: asymptotic trend criterion | not computable before approval |
| Reaction | `58.5%`, `26.3%`, `45.0%`, `72.9%` | `OWNER_DECISION_REQUIRED`: equilibrium/convergence criterion | not computable before approval |
| Stress / VM | `35.1%`, `25.3%`, `89.4%`, `39.5%` | `OWNER_DECISION_REQUIRED`: field-recovery criterion | not computable before approval |
| PEEQ | `35.9%`, `9.5%`, `91.4%`, `34.8%` | `OWNER_DECISION_REQUIRED`: localization/convergence criterion | not computable before approval |
| Energy | `31.3%`, `4.1%`, `88.5%`, `29.1%` | `OWNER_DECISION_REQUIRED`: energy asymptote criterion | not computable before approval |

These are not failures of the solver by themselves: they are the measured
response of the regular one-direction refinement study. They do demonstrate
that a universal scalar band cannot be inferred from this campaign alone.

| Requirement | Frozen criterion used | Result | Margin | Owner decision |
|---|---|---|---:|---|
| Constitutive paths | finite, physically signed/invariant path checks from existing tests | PASS | n/a | none |
| Algorithmic tangent | relative FD error `< 1e-6` | PASS (`2.12e-10`) | `9.998e-7` | none |
| Connected four-family solve | existing residual/work contracts, including residual `< 1e-6` | PASS | `9.220e-7` on max residual | none |
| Energy | relative balance `< 1e-6`; `D_p >= 0` | PASS | `9.914e-7` on max imbalance | none |
| State transaction | rollback leaves committed digest unchanged; commit changes trial state | PASS | exact invariant | none |
| Rollback reference difference | no release band frozen | evidence available | n/a | `OWNER_DECISION_REQUIRED` |
| Load-step sensitivity | no release band frozen | trend evidence available | n/a | `OWNER_DECISION_REQUIRED` |
| Mesh/PEEQ convergence | no release band frozen | trend evidence available | n/a | `OWNER_DECISION_REQUIRED` |
| Code_Aster four-family correlation | existing runner tolerance `5e-3` on 64 comparable checks | PASS (`64/64`) | `3.387e-3` on max error | none |

### G01 status

`025-G01 = OPEN`.

The technical evidence is green, but the gate cannot be closed until the
Owner explicitly approves the frozen acceptance treatment for rollback
reference differences and mesh/load-step trends. This is a governance
blocker, not a failed numerical test. No other functional gate is changed by
this report.

## Owner questions

1. Approve the inherited `1e-6` tangent and energy criteria and the existing
   `5e-3` Code_Aster correlation criterion for G01.
2. Approve a release treatment for mesh/load-step trends: either define
   numerical bands from an Owner-reviewed asymptotic basis, or accept these
   as bounded observations while keeping the corresponding claim limited.
3. Approve whether the rollback/reference differences remain diagnostic only
   or receive a frozen acceptance band.

Until these decisions are recorded, the claim remains `EXPERIMENTAL` at the
release level even though the controlled internal and external evidence
artifacts report PASS statuses.
