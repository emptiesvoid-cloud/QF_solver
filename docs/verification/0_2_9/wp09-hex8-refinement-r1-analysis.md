# WP09 HEX8 refinement study — diagnostic analysis

## Scope and provenance

This is an HEX8-only diagnostic campaign at the accepted bounded load scale
of 25% of the formal reference load. It does not modify production mechanics,
does not overwrite the TET4 evidence, and does not award formal WP09 points.

Runner execution SHA: `7553d4c6b776db2296c6d6eb437e9dbb1dee9ea4`

The hierarchy is isotropic in all three spatial directions:

| Level | Subdivision | Nodes | HEX8 elements | DOFs |
|---|---:|---:|---:|---:|
| H1 | 1×1×1 | 8 | 1 | 24 |
| H2 | 2×2×2 | 27 | 8 | 81 |
| H3 | 4×4×4 | 125 | 64 | 375 |
| H4 | 8×8×8 | 729 | 512 | 2,187 |

All four meshes pass mesh-quality preflight with zero errors and zero
warnings. All four structural runs terminate with `PASS`, four accepted load
steps, and zero rejected increments.

## Observables

| Level | max displacement | reaction norm | energy | max von Mises | max PEEQ | max local strain | min detF |
|---|---:|---:|---:|---:|---:|---:|---:|
| H1 | 1.065944e-03 | 2.500000e-01 | 1.412232e-04 | 2.909757e-02 | 1.113890e-03 | 1.401096e-03 | 9.998201e-01 |
| H2 | 7.400543e-03 | 2.500000e-01 | 6.530805e-04 | 8.347733e-02 | 9.893822e-03 | 1.223946e-02 | 9.987323e-01 |
| H3 | 1.509184e-02 | 2.500000e-01 | 1.364766e-03 | 2.082318e-01 | 2.326010e-02 | 2.875461e-02 | 9.979918e-01 |
| H4 | 2.123035e-02 | 2.499999e-01 | 2.093816e-03 | 3.105745e-01 | 3.414347e-02 | 4.219400e-02 | 9.977076e-01 |

The H4 local-strain bound passes (`0.042194 < 0.05`) and the deformation
determinant remains positive.

## Formal-gate comparison

H4 does not satisfy the currently frozen formal gates:

- force balance: `1.490e-07`, above `1e-08`;
- moment balance: `1.053e-07`, above `1e-08`;
- free residual: `8.423e-08`, below `1e-07`, but close to the limit;
- H3→H4 displacement delta: `28.91%`;
- H3→H4 energy delta: `34.82%`;
- H3→H4 von Mises delta: `32.95%`;
- H3→H4 equivalent plastic strain delta: `31.88%`.

The reaction delta is small (`5.96e-07`), as expected for a fixed applied
resultant, but it cannot establish field or energy convergence.

## Conclusion

```text
HEX8_DIAGNOSTIC_RUN = PASS
HEX8_MESH_QUALITY = PASS
HEX8_LOCAL_STRAIN_ENVELOPE = PASS
HEX8_H4_EQUILIBRIUM_FORMAL_GATE = FAIL
HEX8_H3_H4_CONVERGENCE_FORMAL_GATE = FAIL
HEX8_FORMAL_REQUALIFICATION = NOT_READY
WP09_FORMAL_POINTS = UNCHANGED
```

HEX8 is the more viable family than TET4 for the bounded route, but it is not
formally validated by this campaign. The next technical step is to diagnose
the H4 equilibrium/tolerance loss and the still-large refinement deltas, then
freeze a HEX8-only contract before any formal M1/M2/M3 execution. No TET4 run
is required for that next diagnostic step.

## Evidence

- Raw results and summary:
  `qualification/0_2_9/wp09_hex8_refinement_r1/`
- SHA-256 manifest:
  `qualification/0_2_9/wp09_hex8_refinement_r1/manifest.json`
- No push, merge, threshold change, or production-mechanics change was made.
