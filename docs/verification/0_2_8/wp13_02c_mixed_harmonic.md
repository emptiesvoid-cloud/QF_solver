---
doc_id: DOC-028-WP13-02C-MIXED-HARMONIC-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP13-02C connected mixed harmonic campaign

This record covers the separate WP13-02C harmonic workflow for the connected
TET4/WEDGE6/HEX8 compact elbow.  The machine-readable contract was committed
before the numerical campaign in commit
`4f6e4490d4069b417e9830b8b6a7dc595bd23bb6` and is
[`wp13_02c_harmonic_contract.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02c_harmonic_contract.json).

The evidence is archived in
[`manifest.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02c_harmonic_v1/manifest.json)
and [`wp13_02c_harmonic_arrays.npz`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02c_harmonic_v1/wp13_02c_harmonic_arrays.npz).

## Scope and result

The run uses one connected component with 3 TET4, 2 WEDGE6 and 1 HEX8,
consistent translational mass, 2% mass-proportional Rayleigh damping, the
frozen frequency ratios `0, 0.25, 0.5, 0.75, 0.9, 0.98, 1.0, 1.02, 1.1,
1.25, 1.5, 2.0`, and a direct complex SciPy solve.  The load is applied on
the TET4 end face and the support is only on HEX8, so the declared mechanical
path is `LOAD -> TET4 -> WEDGE6 -> HEX8 -> SUPPORT`.

The dense independent K/M/C reference, static limit, complex residuals,
interface displacement/force/work checks, family energies, replays and all
nine runtime failure cases passed their predeclared checks.  This is a
technical candidate only; the Owner Gate remains mandatory.

## Explicit limitation

The dense oracle is the acceptance oracle.  The analytical first-mode SDOF
calculation is retained as supporting diagnostic evidence only.  The frozen
TET4 end-face load has a very small first-mode participation in this discrete
model, so the evidence does not support a first-mode-dominance claim and does
not generalize to arbitrary FRF, damping, loading or geometry.

No 0.2.7 evidence, Newmark evidence, formulation, gate or maturity record was
changed by this campaign.
