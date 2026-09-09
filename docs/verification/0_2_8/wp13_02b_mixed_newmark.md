---
doc_id: DOC-028-WP13-02B-MIXED-NEWMARK-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP13-02B connected mixed Newmark campaign

WP13-02B executes the frozen Newmark contract
[`WP13-02A-NEWMARK-MIXED-CONTRACT-001`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02a_newmark_contract.json)
on the connected compact elbow. It does not change the Newmark formulation,
the contract gates, the historical maturity registry, or any 0.2.7 evidence.

The machine-readable evidence is
[`wp13_02b_mixed_newmark_evidence.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02b_mixed_newmark_evidence.json).

## Campaign scope

The model has 48 translational DOF, one connected component, 3 TET4, 2
WEDGE6 and 1 HEX8. The conforming interfaces are TET4/WEDGE6 on nodes
10/11/12 and WEDGE6/HEX8 on nodes 2/3/6/7. The declared mechanical path is

`initial modal state -> TET4 -> WEDGE6 -> HEX8 -> fixed HEX8 support`.

The primary case is undamped free vibration: external load is zero after the
declared first-mode initial displacement, initial velocity is zero, and
consistent mass is used. The monitored probe is node 13, `UZ`.

## Independent reference and results

The reference was assembled by an independent local-element K/M scatter and a
dense generalized eigensolve, followed by the closed-form first-mode
oscillator. It did not call the production Newmark loop, router, or time
integrator. The reference first frequency is 97.80394654204198 Hz; the
production modal cross-check is 97.80394654200138 Hz.

All four frozen time-step levels were executed. T1/20 and T1/40 are retained
as coarse convergence characterization; the frozen oracle amplitude, phase,
and RMS gates pass at T1/80 and T1/160. The T1/80-to-T1/160 relative probe
refinement is 5.585216889486116e-3 against the 1e-2 fine-refinement gate.
Maximum observed energy drift is 1.8201536793793772e-13. Capturing every
Newmark step gives a maximum interface force-transfer metric of
3.66742111211155e-12 relative and a maximum interface energy decomposition
error of 3.948190782042867e-14.

The two complete T1/160 replays pass numerical determinism with identical
iterations and zero relative differences in the recorded displacement,
velocity, acceleration, reaction, residual and energy records.

## Failure contract and limits

Invalid time step, incompatible damping, invalid initial condition, invalid
interface connectivity, unsupported time load, and unsupported dynamic family
inputs fail explicitly. No silent family substitution or fallback was
observed.

This is a bounded workflow result, not a maturity promotion. It does not
claim arbitrary temporal loads, nonlinear dynamics, nonconforming interfaces,
distributed performance, external correlation, or general mixed transient
support. A separate WP13-02D Owner gate is required before any public claim.

`WP13-02B = PASS_WITH_LIMITATIONS`; the technical record is 8/8 points and
WP13-02C may be considered separately. The full regression suite remains
deferred to the WP13 final gate.
