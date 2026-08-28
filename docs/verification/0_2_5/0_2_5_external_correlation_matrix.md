---
doc_id: DOC-NL-025-010
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 external correlation matrix

`MUST` cells must close for the associated release claim. An unavailable or
non-comparable solver is `N/A WITH JUSTIFICATION`, never `PASS`.

| Capability | Analytical/published | Code_Aster | CalculiX | Abaqus if available | Required outputs | Gate |
|---|---|---|---|---|---|---|
| J2 multi-element | MUST | MUST | SHOULD | COULD | F-u, reactions, VM, PEEQ, yield onset, energy | G01/G10 |
| Large deformation | MUST | MUST | SHOULD | COULD | load-u, reactions, stress/strain measure, energy | G02/G10 |
| Linear buckling | MUST Euler | MUST | SHOULD | COULD | factors, modes, normalization/MAC | G03/G10 |
| Arc-length | MUST published branch | MUST | SHOULD if supported | COULD | complete load-factor/displacement branch | G04/G10 |
| Frictionless contact | simple analytical MUST | MUST | SHOULD | COULD | gap, pressure, reactions, active set/path | G05/G10 |
| J2 + geometry | published if available | MUST after formulation approval | SHOULD | COULD | F-u, VM, PEEQ, energy | G06/G10 |
| Geometry + contact | qualitative/analytical limits | MUST | SHOULD | COULD | load-gap-u, pressure, reactions | G06/G10 |
| Triple coupling SHOULD | none required | SHOULD | COULD | COULD | full histories and limits | G06/G10 |
| Friction COULD | simple block analytical | SHOULD if WP7 promoted | SHOULD | COULD | stick/slip, traction, dissipation | G07/G10 |

## Reproducibility contract

The existing 0.2.4 RQ-G08 Docker replay is a useful environment smoke check,
but it is not a 0.2.5 multi-element closure: it covers the affine one-element
TET4/TET10/HEX8/HEX20 patch only. The 0.2.5 G10 row remains open until a
multi-element history with matched reactions and state fields is generated,
executed and archived with its own provenance.

The reproducible 0.2.5 entry point is:

```text
python scripts/run_j2_multielement_external_025.py --output results/vnv_0_2_5/j2_multielement_code_aster
```

On the current working tree this campaign executes in the pinned Docker image
on a regular two-cell shared mesh. Displacements, reactions, `stress_xx` and
aggregate PEEQ agree for all four families within the current 0.5% limit. The
campaign currently reports `PASS_EXTERNAL_CORRELATION` with 64 checks; no
tolerance was widened.

The TET10 comparison uses the explicit QF analysis parameter
`tet10_nonlinear_quadrature=code_aster_5`. This symmetric five-point rule
matches the five `ELGA` values per `TETRA10` element exposed by the pinned
Code_Aster run. The legacy QF Hammer four-point rule remains the default for
existing models and for linear TET10 paths; this external evidence therefore
records a matched comparison configuration, not a silent global change of
historical behavior. The campaign is bounded numerical correlation, not
physical validation, and does not by itself close G01 or G10.

## Observed G04 Configuration-Matched Branch Diagnostic

The historical G04 Code_Aster replay was not comparable to the QF branch: QF
uses a positive reference load with negative load factor (physical downward
load), while the historical deck used upward `FZ=+1/3`; it also post-processed
mean crown displacement instead of QF apex `UZ`. The corrected deck uses
`FZ=-1/3`, controls `APEX/DZ`, and samples the same apex-displacement domain.

The corrected pinned Code_Aster 18.1 Docker run and the QF two-element TET4
path both show one limit point. Comparison by apex displacement gives maximum
and RMS load-factor differences of `4.8719e-07` and `2.0730e-07`, respectively.
This removes an external configuration mismatch, but remains bounded numerical
diagnostic evidence. It does not close the G04/G10 Arc-length row because the
custom two-element model has no linked published FEM branch reference and no
coarse/medium/fine/refined branch study. See `DOC-NL-025-030`.

## Observed bounded contact oracle

`VNV-CONTACT-CODEASTER-LIAISON-UNIL-001` was replayed with the pinned
Code_Aster 18.1.0 image
`simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`.
The QF Solver and Code_Aster results agree for compression/closure and
separation/opening, including the active-set branch and scalar gap, with five
checks passing. The controlled evidence is archived under
`results/vnv_0_2_5/contact_code_aster_liaison_unil/`.

This is an external correlation of the equivalent scalar unilateral normal
inequality only. It does not close the general frictionless-contact cell:
surface-to-surface finite sliding, updated normals, recontact, penetration
sensitivity, contact rollback and multi-element external histories remain
open requirements for the general `025-G10` correlation matrix. The scalar
oracle alone does not close G05; the bounded G05 closure additionally relies
on the controlled faceted/contact histories recorded below.

## Controlled bounded contact correlation for G05

The Code_Aster campaign `VNV-CONTACT-CODEASTER-ADDITIONAL-009` was replayed
on source SHA `a3ab8de707ffc88fc5e39e4f999eb872c9223b73` with a clean tree,
using the pinned `simvia/code_aster:18.1.0` image. It compares ten load
factors for a dual-stop corner, a three-facet ramp patch and a deformable
TET4 model with two slave nodes. The 768-TET4 replay passes with a maximum
QF/Code_Aster displacement-curve error of `4.33998 %`; its first-sample
activation difference is retained explicitly, while the active-branch gap
error is below `4.1e-16 m`. The 9,984-TET4 confirmation passes with
`3.30291e-12 %` and has no first-sample activation mismatch. These are bounded
normal-contact histories, not a claim of general surface-to-surface
equivalence.

The external evidence is archived in
`results/vnv_0_2_5/g05_latest/code_aster_768/` and
`results/vnv_0_2_5/g05_latest/code_aster_h10k/`, with the aggregate manifest
at `results/vnv_0_2_5/g05_latest/evidence_manifest.json`. CalculiX remains a
SHOULD/supporting pre-contact tie-breaker and is not required to close G05.

## Controlled Code_Aster TET4 buckling correlation

The bounded Code_Aster MUST cell for G03 is closed by the exact constrained
five-TET4 unit-block probe archived under
`results/vnv_0_2_5/g03_final/`. The pinned Code_Aster 18.1.0 execution uses
`RIGI_GEOM` and `CALC_MODES(TYPE_RESU="MODE_FLAMB")`. QF Solver uses the
sparse initial-stress geometric tangent and obtains a critical factor of
`221.54828247814925`; Code_Aster reports `221.774`, for a relative difference
of `1.018e-3`. The best modal MAC is `0.9999999989229131`, with QF critical
mode residual `1.72e-15`. This is a bounded numerical correlation and not
physical validation or a claim for all solid families.

The current container could not replay the deck because its Code_Aster
launcher lacks `mpi4py`; the prior execution is retained with its source deck,
mode output and pinned image digest. This environment limitation is recorded
in the final evidence manifest and does not alter the archived external result.

## Observed bounded TET4-TL buckling correlation

The existing CalculiX structural campaign was replayed under the dedicated
0.2.5 output directory as `VNV-TET4-TL-CALCULIX-STRUCTURAL-008`. Four
structured TET4/C3D4 levels passed the stress patch and linear-buckling
checks. On the finest level the QF/CalculiX critical-load difference was
`3.52e-4`, while the CalculiX/Euler relative error was `5.91 %`. The pinned
campaign uses the CalculiX 2.20 image
`qf-solver/calculix-nafems13h:2.20`; the machine-readable evidence is under
`results/vnv_0_2_5/calculix_tl_structural/` and the existing controlled
reference archive under
`qualification/vnv/external/calculix_tl_structural/reference/`.

This result is bounded to the TET4 Total-Lagrangian structural route and does
not qualify the general sparse buckling API, HEX8, post-buckling or contact.

## External solid-family buckling probe: blocked

The new reproducible entry point is:

```text
python scripts/run_calculix_buckling_025.py --output results/vnv_0_2_5/calculix_buckling_solid_families_mode1_recorded --families TET4 TET10 HEX8 HEX20 --cells 1 --modes 1
```

The generator now applies the fixed node set with `*BOUNDARY`, requests only
the first eigenfactor, and bounds the Lanczos subspace to the number of free
equations. The resulting archive is
`results/vnv_0_2_5/calculix_buckling_solid_families_mode1_recorded/summary.json`.
It is retained as negative evidence: TET4, TET10 and HEX8 remain outside the
10 % bounded band, with relative differences of approximately 24.6 %, 45.1 %
and 13.4 %, respectively, and the C3D20 buckling job stops natively after
selecting the buckling step. The Lanczos correction fixes the small-system
ARPACK setup error but does not turn the correlation into a PASS.
The same C3D20 ordering passes the existing linear-static replay, so the
failure is isolated to this buckling formulation/campaign rather than hidden
as an input success. The campaign status is `BLOCKED_EXTERNAL_TOOL`; it does
not close `025-G03` or `025-G10`.
An additional two-cell C3D20 probe is archived at
`results/vnv_0_2_5/calculix_buckling_hex20_cells2_probe/`; the pinned external
executable terminates with `double free or corruption (!prev)`. This is retained
as an external-tool diagnostic, not as a QF Solver result or a PASS.
The recorded provenance is SHA
`e368c0ce00874c16ff1e8fa9158ea0a8cd2dd745` with `worktree_dirty=true`, so this
archive is diagnostic working-tree evidence and cannot serve as final release
evidence.

Every external case must provide:

- solver name/version and execution environment;
- source deck and generated deck digest;
- identical geometry and mesh where possible;
- explicit element-formulation differences where not possible;
- material parameters, stress/strain measures and hardening convention;
- BC, loading history, increments and convergence options;
- matched result locations and post-processing definitions;
- full machine-readable curves plus summary plots;
- threshold source and limitations;
- QF Solver SHA and evidence digest.

## Correlation decision rule

Agreement of one final scalar cannot close a row. Mandatory rows compare complete
histories, reactions and at least one relevant field/state quantity. Differences
caused by incompatible integration, locking control, contact enforcement or
stress recovery must be quantified rather than hidden in a broad tolerance.
