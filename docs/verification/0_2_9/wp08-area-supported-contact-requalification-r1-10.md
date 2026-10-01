---
doc_id: "DOC-MARKDOWN-16532487F5DF938E"
revision: "0.1"
status: "controlled_evidence"
applicable_version: "0.2.9"
reviewer: ""
approver: ""
---
# WP08 area-supported contact — prospective R1.10 diagnostic

## Purpose and authorization

R1.10 prospectively reruns the bounded area-supported friction benchmark after
the contact-root correction described below. The Owner authorized freezing
the R1.10 runner and one serial M1/M2/M3 campaign. This authorizes diagnostic
execution only: it does not qualify WP08, award points, authorize a merge or
push, or authorize a retry. The historical R1.9 results and its M3/slip
failure remain immutable.

## R1.9 failure and R1.10 change

R1.9 passed M1 and M2 for both targets and M3 for `stick_target`; M3
`slip_target` failed closed at load step 8. The direct active set reached its
existing 25-iteration cap; the active-slip candidate stopped on `xtol` above
the frozen per-contact `1e-9` scaled-residual gate. After the normal active
set changed from 15 to 20 contacts, the coupled candidate also stopped on
`xtol` above that gate, and the existing enumeration guard prevented a wider
search.

R1.10 changes only the numerical contact-root path in
`src/solveur/contact/slip_root.py`:

1. Build the piecewise coupled-projection Jacobian from exact linear
   displacement and pressure sensitivities, including the derivative of the
   pressure-dependent local residual normalization.
2. Continue active-slip recovery from the best finite root/semismooth
   candidate instead of restarting from the original seed.
3. If the trust-region optimizer stops on `xtol` above the physical gate,
   apply safeguarded semismooth polishing from its best candidate, consuming
   only the unused portion of the pre-existing 30-iteration budget.

The frozen per-contact `1e-9` acceptance gate, 25-iteration active-set limit,
enumeration guard, physical residual, fallback policy and all benchmark inputs
remain unchanged. A nonconverged case remains a failure; no threshold is
relaxed and no retry is allowed.

## Frozen benchmark

- Straight TET4 prism: `Lx=2.0 m`, `Ly=1.0 m`, `Lz=0.5 m`.
- Isotropic 3-D linear elasticity: `E=1.0e6 Pa`, `nu=0.30`.
- Fix all translations on the body face at `x=0`; fix four rigid-master
  metadata nodes in all translations. No body slave node at `x=2` is fixed.
- Fixed-initial-search node-to-triangle contact, initial gap `5.0e-4 m`,
  master plane `x=2.0005 m`, normal `[-1,0,0]`, friction `mu=0.30`.
- Tangential support uses reference T3 tributary areas with
  `K_i=kappa*A_i`, no redistribution, and fixed `kappa=2,666,700 N/m^3`.
  This is a benchmark calibration, not a measured material property.
- Normal resultant: `1000 N` in `+x`. `stick_target` applies `150 N` in
  `+y`; `slip_target` applies `450 N` in `+y`.
- Eight load steps: four normal ramp steps (0.25, 0.50, 0.75, 1.00), then
  four tangential ramp steps (0.25, 0.50, 0.75, 1.00) at full normal load.
- Meshes are TET4 subdivisions M1 `2x1x1`, M2 `4x2x2`, and M3 `8x4x4`.
- Serial execution order: M1 stick, M1 slip, M2 stick, M2 slip, M3 stick,
  M3 slip. M2 starts only if both M1 cases pass; M3 starts only if both M2
  cases pass. Stop after the first failed process or diagnostic gate.

## Diagnostic gates and interpretation

Each case must report a converged solve and all eight load steps. Its terminal
active contact state must match its declared target (`stick` or `slip`) and
the active support must span a two-dimensional affine patch. M1 additionally
requires all four slave nodes active and active area fraction 1.0. Serialized
M2/M3 observables must be finite. The runner records force/moment equilibrium,
residuals, contact state, timings, raw arrays and refinement comparisons; it
does not invent a missing fallback count or an equilibrium threshold.

M1/M2/M3 displacement, reaction, energy, stress and contact-field differences
are descriptive only. No mesh-convergence threshold is frozen by this
diagnostic; a small or large difference is not automatically a formal
convergence PASS/FAIL.

## Evidence and limitations

Every executed case has a child-process manifest, stdout/stderr logs,
telemetry, `result.json`, `progress.json` and raw arrays, bound to the frozen
contract and source inventory. Prior R1.9 evidence is referenced by absolute
external evidence root and verified SHA-256 values; R1.9 bytes are neither
copied over nor rewritten.

This is experimental bounded evidence only. It does not include an
independent global FEM/Newton reference, formal replay, external solver
correlation, a formal mesh-convergence claim, or WP08 point attribution. No
full repository test suite is run. Production contact mechanics are changed
in this candidate, so later Owner review must inspect the exact source diff and
all campaign evidence before deciding whether the correction is acceptable.
