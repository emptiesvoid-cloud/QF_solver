# 0.2.6 G05 Qualification Contract

`026-G05` covers modal, transient dynamic and harmonic response evidence. The
registry targets are **14 modal**, **16 dynamic** and **12 harmonic** cases.
Executable status is deliberately separate from qualification status: `READY`
means that the controlled runner can execute a case; it does not close G05.

| Requirement | Target | Evidence required | Policy |
| --- | ---: | --- | --- |
| G05-MOD-001 | 14 | Frequencies, generalized residuals, mass orthogonality, normalization and expected rigid modes | Residual uses the existing `<= 1e-7` contract; other limits are case-specific |
| G05-MOD-002 | 14 | Compatible coarse/medium/fine modal refinement and mode tracking | `OWNER_APPROVED_BOUNDED`: final adjacent tracked-mode frequency change `<= 1%`, at least three compatible levels; residual and MAC remain recorded when available |
| G05-DYN-001 | 16 | Newmark histories, residuals, stability and energy drift | Existing residual and benchmark energy policies are retained |
| G05-DYN-002 | 16 | At least three time steps over a common physical interval | `OWNER_APPROVED_BOUNDED`: final adjacent history error `<= 1%`; identical physical interval and comparison times, with residual and energy criteria retained separately |
| G05-HAR-001 | 12 | Complex amplitude/phase, residual and zero-frequency behavior | Existing harmonic residual and zero-frequency criteria are retained |
| G05-HAR-002 | 12 | Frequency-grid refinement, peak/phase tracking and resonance handling | `OWNER_APPROVED_BOUNDED`: final amplitude change `<= 1%`; phase, peak displacement and complex residual remain recorded; exact singular resonance is excluded |

The Owner approved these bounded policies on 2026-08-29. They do not promote a
family by case count alone, relax the pre-existing residual/energy criteria, or
close G05. Each application still requires compatible meshes or grids, a
documented observable and controlled provenance.
