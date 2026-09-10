---
doc_id: DOC-028-WP04-001
revision: 0.3
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP04 — MITC3 and MITC4 V&V

This record freezes the WP04 contract from baseline
`2a6a02859e3f19ddf26903167de1db6fdd3f3c7c`. The machine-readable contract is
[`wp04_mitc_vnv.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp04_mitc_vnv.json).

## Historical evidence audit

WP01 classified MITC3 static as `NEEDS_MINOR_VNV`, MITC3 modal/Newmark/harmonic
as `NEEDS_MAJOR_VNV`, and all four MITC4 routes as `NEEDS_MINOR_VNV`. The
historical Owner review documents remain useful provenance, but their cited
`qualification/vnv`, `qualification/evidence`, `results` and PDF artifacts are
not all present in this clone. They are therefore not treated as current
executable correlations and are not recreated or rewritten.

## Frozen scope and decision rule

The campaign promotes only bounded, reproducible scopes. MITC3 static uses
affine membrane/bending/shear patches, rigid-body and energy/reaction
invariants, locking and reference-shell trends. MITC3 modal, Newmark and
harmonic remain experimental because their current independent same-mesh
oracles are missing.

MITC4 static uses element mechanics, patch, orientation/objectivity, drilling,
locking and declared structural convergence. MITC4 modal uses a slender
cantilever analytical reference, but its final relative-residual observation
(`2.6317020430528298e-08`) does not meet the stricter frozen WP04 limit
(`1e-08`), so it remains `EXPERIMENTAL`. MITC4 Newmark uses an exact
first-mode time history with temporal refinement and energy checks. MITC4
harmonic uses a closed-form first-mode FRF across several frequencies,
including zero-frequency and resonance checks.

All limits are predeclared in the JSON record before the WP04 campaign. A
technical `PASS` is not a universal claim: each accepted route remains bounded
by the exact geometry, material, mesh, loading, damping and observable scope
listed in the record.

## Local orientation, permutations and thickness

The executable shell checks include local-frame/objectivity and orientation
contracts, consistent node ordering, rigid-body invariance and finite positive
thickness cases. Reversed or inconsistent shell orientation remains rejected
by the mesh contract; it is not silently repaired into a qualification pass.

## External correlation policy

No absent historical Code_Aster, CalculiX or PDF artifact is counted as a live
correlation. The approved MITC4 dynamic scopes use independent analytical
time/frequency references because their claims are explicitly limited to a
single verified mode. The MITC3 dynamic routes do not receive that promotion:
same-assembled-model internal references alone do not close their route-level
oracle requirement.

## Executed decision snapshot

| Combination | WP04 decision | Evidence status |
| --- | --- | --- |
| MITC3 linear static | `QUALIFIED_BOUNDED` candidate | Two deterministic replays; patch, equilibrium, energy, orientation, permutation and locking gates pass. Reference-shell trends remain bounded warnings. |
| MITC3 modal / Newmark / harmonic | `EXPERIMENTAL` | No executable independent shell oracle is present in the clone. |
| MITC4 linear static | `QUALIFIED_BOUNDED` candidate | Two deterministic replays; mechanics, patches, drilling sensitivity and structural convergence gates pass. Cook is retained as a bounded trend warning. |
| MITC4 modal | `EXPERIMENTAL` | Two deterministic replays pass the study's internal checks, but the predeclared WP04 residual gate fails; no tolerance was relaxed. |
| MITC4 Newmark | `QUALIFIED_BOUNDED` candidate | Two deterministic replays pass the declared time-step, phase/period, energy and residual gates. |
| MITC4 harmonic | `QUALIFIED_BOUNDED` candidate | Two deterministic replays pass the declared multi-frequency amplitude, phase, resonance, static-limit and residual gates. |

The machine-readable replay digests, observed values and test references are
recorded in [`wp04_mitc_vnv.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp04_mitc_vnv.json).
The eight-route decision delta is summarized in the
[`WP04 maturity matrix`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp04_maturity_matrix.json).
The final Owner decisions are recorded in
[`wp04_owner_gate_final.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp04_owner_gate_final.json).
The four approved bounded routes are now `QUALIFIED_BOUNDED` within the scopes
below; no claim is broadened beyond the evidence.

Across the 46-record technical matrix after the WP03 and WP04 deltas, the
state is 31 `QUALIFIED_BOUNDED`, 14 `EXPERIMENTAL`, and 1
`NOT_QUALIFIED`, for a total of 46. The sole not-qualified combination is
`COMB-HEX8-linear_buckling`. `COMB-WEDGE6-linear_static` remains a distinct
`EXPERIMENTAL` combination and is not confused with that status.

## Final Owner gate

| Combination | Owner decision | Resulting state | Limitation or rejected gate |
| --- | --- | --- | --- |
| MITC3 linear static | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` | Executed patch, equilibrium, energy, orientation, permutation and locking scope only. |
| MITC3 modal | `REJECT` | `EXPERIMENTAL` | No executable independent shell modal oracle. |
| MITC3 Newmark | `REJECT` | `EXPERIMENTAL` | No executable independent same-mesh transient shell oracle. |
| MITC3 harmonic | `REJECT` | `EXPERIMENTAL` | No executable independent same-mesh shell FRF oracle. |
| MITC4 linear static | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` | Executed mechanics, patch, equilibrium, drilling and reference-mesh scope only. |
| MITC4 modal | `REJECT` | `EXPERIMENTAL` | Relative residual `2.6317020430528298e-08` exceeds frozen `1e-08` gate. |
| MITC4 Newmark | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` | Verified first-mode, undamped Newmark temporal scope only. |
| MITC4 harmonic | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` | Verified first-mode, seven-frequency, mass-proportional damping scope only. |

The Owner gate found no numerical-core change, no opportunistic tolerance
change and no alteration of 0.2.7 evidence. The machine-readable gate also
reconciles all 46 source combination records directly.
