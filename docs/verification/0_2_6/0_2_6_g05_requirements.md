# 0.2.6 G05 Qualification Contract

`026-G05` covers modal, transient dynamic and harmonic response evidence. The
registry targets are **14 modal**, **16 dynamic** and **12 harmonic** cases.
Executable status is deliberately separate from qualification status: `READY`
means that the controlled runner can execute a case; it does not close G05.

| Requirement | Target | Evidence required | Policy |
| --- | ---: | --- | --- |
| G05-MOD-001 | 14 | Frequencies, generalized residuals, mass orthogonality, normalization and expected rigid modes | Residual uses the existing `<= 1e-7` contract; other limits are case-specific |
| G05-MOD-002 | 14 | Compatible coarse/medium/fine modal refinement and mode tracking | `UNDEFINED_POLICY`: Owner approval required for a general band |
| G05-DYN-001 | 16 | Newmark histories, residuals, stability and energy drift | Existing residual and benchmark energy policies are retained |
| G05-DYN-002 | 16 | At least three time steps over a common physical interval | `UNDEFINED_POLICY`: Owner approval required for a general band |
| G05-HAR-001 | 12 | Complex amplitude/phase, residual and zero-frequency behavior | Existing harmonic residual and zero-frequency criteria are retained |
| G05-HAR-002 | 12 | Frequency-grid refinement, peak/phase tracking and resonance handling | `UNDEFINED_POLICY`: Owner approval required for a general band |

The current contract therefore supports execution and evidence collection, but
does not silently invent universal frequency, time-step or phase tolerances.
Those policies must be approved before an eventual G05 closeout.
