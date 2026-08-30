# TL blocker resolution

Status: `DIAGNOSTIC_ONLY`; G07 remains open and no promotion decision is made here.

Source SHA: `bb44c121c1c6c676f808ff4498aa7e8c980dff0e`; dirty at capture: `False`.

## Small-strain asymptotic study

Metric: `||u_TL-u_linear|| / ||u_linear||`, with a common two-cell, aspect-6.5 traction model and load factors 1, 1/2, 1/4, 1/8 and 1/16.

| Family | factor 1 | 1/2 | 1/4 | 1/8 | 1/16 |
| --- | ---: | ---: | ---: | ---: | ---: |
| TET4 | 1.422e-03 | 7.118e-04 | 3.561e-04 | 1.753e-04 | 8.768e-05 |
| HEX8 | 1.416e-03 | 7.088e-04 | 3.546e-04 | 1.746e-04 | 8.732e-05 |

Policy proposal: `PROPOSED_OWNER_REVIEW`. Require a documented asymptotic trend toward zero over the declared small-strain domain; no scalar acceptance band is auto-approved because the controlled tolerance policy is case-defined.

## Tangent FD study

180 observations cover six states, three deterministic directions and five FD steps for each family. Observed maximum relative error: `4.643e-08`.

Policy proposal: `PROPOSED_OWNER_REVIEW`. Retain the full error envelope, state coverage and FD-step stability; a numerical band and near-zero denominator treatment require Owner approval.

## Flexion/shear mesh sensitivity

16 solves cover TET4/HEX8, bending/shear and four mesh levels. Adjacent changes are reported in `tl_blocker_resolution.json`; no monotonicity or universal aspect-ratio rule is imposed.

Interpretation: `OBSERVED_TREND_ONLY`. Flexion and shear sensitivity is retained as a bounded-domain limitation pending Owner review; it is not silently classified as a solver defect or as convergence.

## External correlation

New Code_Aster/CalculiX execution: `SKIPPED_NOT_COMPARABLE`. The current environment has no compatible external executable, and no exact apples-to-apples deck was run. Existing bounded external evidence is not relabeled as this new campaign.

## Artifacts and limitations

- Raw measurements: `tl_blocker_resolution.json`.
- Reproducibility manifest: `tl_blocker_resolution_manifest.json`.
- Figures: `small_strain_asymptotic.png`, `tangent_fd_policy.png`, `mesh_flexion_shear.png`.
- This pack does not modify G07, G04, Agent B, TL formulation, tangent, Newton controls or default adaptive behavior.
