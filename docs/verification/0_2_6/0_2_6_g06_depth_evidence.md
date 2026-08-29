# 026-G06 Deep J2 Evidence

## Status

`026-G06` remains **NOT_STARTED**. This pack is a controlled evidence package
for Owner closeout; it does not close the official gate automatically.

- Start SHA: `b952520f5db8095e1fa214e451999aaedc672341`
- Execution source SHA: `8bd0f2d8fdce7bf27ffc4c28e6aa26e69288fa63`
- Source dirty state: `false`
- Proposed decision: `PASS_WITH_LIMITATIONS`
- Finite-kinematic J2: `RESEARCH_NOT_QUALIFIED`

## Internal evidence

| Evidence | Result |
| --- | --- |
| Dedicated TET10 cyclic J2 | `PASS_INTERNAL`, 341 nodes, 140 elements, 4 integration points/element |
| Inverted TET10 rejection | `EXPECTED_FAILURE / INVALID_ELEMENT`, rejected before solve |
| J2 mesh series | `PASS_INTERNAL_MESH_REFINEMENT`, levels 1/2/4/8, TET4/TET10/HEX8/HEX20 |
| Load-increment sensitivity | `PASS_INTERNAL`, subdivisions 4/8/16, maximum state sensitivity `3.444e-09` |
| Multi-element invariant matrix | All four families `PASS` |
| Energy and plastic dissipation | All four families `PASS_INTERNAL_ENERGY` |
| Cyclic paths | All four families `PASS_INTERNAL_CYCLIC` |
| Adversarial rollback | `PASS_INTERNAL_ROLLBACK` for TET4/TET10/HEX8/HEX20, deterministic rejected increment and clean retry |
| Consistent tangent checks | Targeted tests `PASS` |

The mesh study is deliberately reported as bounded evidence. Its regular
unit-block topology and the non-monotone field trends do not justify a universal
mesh-convergence claim.

Cross-family proof coverage is explicit: homogeneous constitutive response,
yield threshold, shared tangent FD, equilibrium/residuals and rollback are
covered in bounded form. Tangent symmetry is not separately assessed, and
increment-independence beyond the existing TET4 study is not claimed.

## Code_Aster correlation

The pinned Code_Aster 18.1.0 image was executed after the evidence runner was
committed. The regular two-cell shared benchmark produced `64/64` PASS checks:

| Family | Maximum relative error | Result |
| --- | ---: | --- |
| TET4 | `1.613e-03` | PASS |
| TET10 | `6.230e-04` | PASS |
| HEX8 | `2.734e-07` | PASS |
| HEX20 | `6.339e-04` | PASS |

The TET10 comparison uses `code_aster_5` as an explicit external convention;
QF's historical default remains `hammer4`. This is bounded numerical
correlation, not physical validation.

## Targeted verification

Command:

```text
python -m pytest tests/unit/test_robustness_tangent_fd.py tests/unit/test_nonlinear_multielement.py tests/unit/test_nonlinear_cyclic.py tests/unit/test_j2_multielement_external.py tests/verification/test_tet10_j2_structural_vnv.py -q
```

Result: **38 passed, 0 failed** in approximately 160.77 seconds.

Registry, anti-forgetting, Ruff, compileall and `git diff --check` also passed.
Full regression was not rerun because no solver or functional FEM code changed.

## Limitations and remaining Owner decision

- G06 remains officially `NOT_STARTED` until the Owner reviews this pack.
- The mesh series is bounded and does not qualify arbitrary distortion,
  localization or industrial geometries.
- Increment refinement is inherited from the TET4 cyclic structural path and is
  not a universal path-independence statement for all families.
- Rollback evidence covers deterministic rejection before the first accepted
  increment for all four families; broader material-update and sparse-backend
  failure matrices remain separate work.
- Finite-kinematic J2 and coupled nonlinear workflows remain research/experimental.

The generated aggregate artifacts are under the ignored `results/g06_depth`
directory. Their digests are recorded in
`qualification/0_2_6/g06_depth_evidence.json`, together with the exact source
and external-image provenance.
