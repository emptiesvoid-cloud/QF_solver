# G05 Final Qualification Evidence

## Decision Boundary

This pack records the Owner closeout for `026-G05` as
`PASS_WITH_LIMITATIONS`. It does not promote a capability merely because its
runner is executable.

| Item | Result |
| --- | --- |
| Qualified numerical source | `6cd971756af0f1b8a114fd98b188714da39ff081` |
| Final evidence replay SHA | `77f147ee261d97fd5e6b88281daafb4deba9ce53` |
| Internal family campaign | `PASS_INTERNAL_PREQUAL`, `dirty=false` |
| Modal cases | `14 / 14` |
| Newmark cases | `32 / 16` |
| Harmonic cases | `12 / 12` |
| Covered family rows | TET4, TET10, HEX8, HEX20, BEAM2, MITC3/MITC3+, MITC4, discrete |
| Unexpected failures | `0` |
| Official gate | `PASS_WITH_LIMITATIONS`; Owner decision recorded |

## Owner-Approved Bounded Policies

The Owner approved the following policies on 2026-08-29. They retain the
existing residual, energy and response-quality requirements; no tolerance was
weakened.

| Route | Promotion metric | Bounded policy |
| --- | --- | --- |
| Modal | final adjacent tracked-mode frequency change | `<= 1%`, at least three compatible levels; preserve residual and MAC when available |
| Newmark | final adjacent displacement-history error | `<= 1%`, same physical interval and comparison times; residual and energy remain separate criteria |
| Harmonic | final-grid amplitude change | `<= 1%`; preserve phase, peak location and complex residual; exact singular resonance is excluded |

## Internal Oracles And Refinement

The campaign records generalized modal residuals, mass/stiffness orthogonality,
zero-frequency harmonic behavior, complex residuals, energy drift and an
assembled first-eigenmode oscillator reference. The maintained SDOF Newmark
and harmonic closed-form tests also pass.

Newmark was executed at 30, 60, 120 and 240 steps per period for each baseline
family. The worst final adjacent error recorded by the campaign is
`4.720960909695235e-3`, below the approved one-percent band. Modal mesh
refinement remains explicitly family-specific bounded evidence. Harmonic
baseline and refined grids were executed; peak and phase remain review data,
not an amplitude-only claim.

## External Correlations

| Family | Route | Oracle | Result | Maximum recorded error / limit |
| --- | --- | --- | --- | --- |
| Discrete | Modal, Newmark, harmonic | Code_Aster `DIS_T` | PASS | `3.05e-11 / 1e-7` |
| BEAM2 | Modal | Code_Aster `POU_D_E` | PASS | `2.65e-4 / 1e-2` |
| BEAM2 | Newmark, harmonic | Code_Aster `POU_D_E` | PASS | `4.75e-13 / 1e-7` |
| TET4 | Modal, Newmark, harmonic | Code_Aster `TETRA4` | PASS | `4.64e-2 / 1e-1` |

The pinned Code_Aster image is
`simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`.
The raw results and their digests are listed in
`qualification/0_2_6/g05_final_evidence.json`.

These four correlations were replayed successfully on the final evidence replay
SHA with `dirty=false`. TET10, HEX8, HEX20, MITC3 and MITC4 have no same-SHA,
formulation-compatible external deck in this run and are not claimed as
externally correlated.

## Bounded Limitation

TET10, HEX8, HEX20, MITC3 and MITC4 rely on internal quantitative V&V and
analytical evidence pending comparable independent external decks. This
limitation is part of the approved G05 scope and is not an unresolved gate
blocker.

No numerical formulation, solver API, physics model or gate requirement was
modified by this pack.
