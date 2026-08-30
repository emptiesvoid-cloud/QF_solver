# TL blocker resolution

Status: `OWNER_REVIEW_PACKAGE`; G07 remains open and this document records a bounded recommendation, not an automatic gate closure.

`TL_WORK_STATUS = PARKED_PENDING_EXTERNAL_EVIDENCE`

Execution source SHA: `bb44c121c1c6c676f808ff4498aa7e8c980dff0e`; initial evidence-pack parent SHA: `a503a63c7f0669804e3c225425e6dc15d2ca6a8d`; dirty at capture: `False`. The final Owner-decision commit is reported externally to avoid a self-referential SHA.

## Small-strain asymptotic study

Metric: `||u_TL-u_linear|| / ||u_linear||`, with a common two-cell, aspect-6.5 traction model and load factors 1, 1/2, 1/4, 1/8 and 1/16.

| Family | factor 1 | 1/2 | 1/4 | 1/8 | 1/16 |
| --- | ---: | ---: | ---: | ---: | ---: |
| TET4 | 1.422e-03 | 7.118e-04 | 3.561e-04 | 1.753e-04 | 8.768e-05 |
| HEX8 | 1.416e-03 | 7.088e-04 | 3.546e-04 | 1.746e-04 | 8.732e-05 |

Recommended policy: `OWNER_APPROVED_BOUNDED`, subject to Owner confirmation. Require a documented asymptotic trend toward zero over the declared small-strain domain; no universal scalar error law is claimed. The observed endpoint reduction is approximately 16x for both families when the load is reduced by 16x.

## Tangent FD study

180 observations cover six states, three deterministic directions and five FD steps for each family. Observed maximum relative error: `4.643e-08`.

Recommended policy: `OWNER_APPROVED_BOUNDED`, subject to Owner confirmation. Use the existing relative metric and an acceptance band of `<= 1e-6` for the declared FD study, with the reported error envelope retained. The band is separated from the observed maximum (`4.643e-8`) and the `1e-8` result is retained as a round-off observation. Near-zero denominators must be reported with the existing floor and not converted into a relative PASS without an absolute residual record.

## Flexion/shear mesh sensitivity

16 solves cover TET4/HEX8, bending/shear and four mesh levels. Adjacent changes are reported in `tl_blocker_resolution.json`; no monotonicity or universal aspect-ratio rule is imposed.

Interpretation: `BOUNDED_WITH_LIMITATIONS`. Flexion and shear sensitivity is retained as a domain limitation; it is not silently classified as a solver defect or as convergence. No universal mesh/aspect-ratio threshold is claimed.

## External correlation

New Code_Aster/CalculiX execution: `SKIPPED_NOT_COMPARABLE`. The current environment has no compatible external executable, and no exact apples-to-apples deck was run. Existing bounded external evidence is not relabeled as this new campaign.

External policy: `MORE_EVIDENCE_REQUIRED` before TL promotion. G07-TL-008 remains an independent-correlation requirement; historical evidence may be used only after formulation, observable and domain compatibility are demonstrated.

## Owner decision summary

The recommended family decisions are `MORE_EVIDENCE_REQUIRED` for both TET4 and HEX8, because the new comparable external correlation is unavailable. The internal evidence supports an `INTERNAL_BOUNDED_WITH_LIMITATIONS` scope only; it does not close G07 or promote TL.

- Bounded domain: existing TL elasticity observations for TET4/HEX8, the declared small-strain series, six-state tangent FD study, and the four-level flexion/shear study.
- Excluded claim: universal mesh convergence, unrestricted large deformation, and external validation.
- Required follow-up: run a genuinely comparable Code_Aster or CalculiX case, then reopen Owner review with the complete curve and provenance.

## Artifacts and limitations

- Raw measurements: `tl_blocker_resolution.json`.
- Reproducibility manifest: `tl_blocker_resolution_manifest.json`.
- Figures: `small_strain_asymptotic.png`, `tangent_fd_policy.png`, `mesh_flexion_shear.png`.
- Decision record: `tl_owner_review_decision.json`.
- This pack does not modify G07, G04, Agent B, TL formulation, tangent, Newton controls or default adaptive behavior.
