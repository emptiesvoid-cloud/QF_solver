# STAT-BEAM-001 — BEAM2 Timoshenko cantilever preparation

**Status:** `EXECUTION_RECORDED`<br>
**Numerical execution:** `PERFORMED_FOR_TWO_ONE_ELEMENT_CASES`<br>
**WP12:** `OPEN`

The two prepared cases are `STAT-BEAM-UY-001` and `STAT-BEAM-UZ-001`, selected through fixed non-parameterized wrappers. They reuse `beam_model` and constants from `tests/unit/test_beam2_element.py`; that historical source test is not modified. The original pytest IDs are parameterized. Their anticipated suffixes were derived from source and pytest's primitive parameter ID rule, but collection was not run. The new wrappers avoid relying on those bracketed IDs.

## Model and oracle

- Straight BEAM2 from `(0,0,0)` to `(2,0,0)`, fixed-free, all six root DOFs fixed.
- `E=210e9`, `nu=0.3`, `G=E/[2(1+nu)]`, `A=0.01`, `Iy=2e-6`, `Iz=3e-6`, `J=5e-6`, force `1000` on the selected tip translation.
- Reference direction is global/local y for this x-axis beam. `UY` uses `Iz`, `RZ`, and positive rotation; `UZ` uses `Iy`, `RY`, and negative rotation.
- `kappa=5/6`.

The reference is the existing Timoshenko tip expression:

```text
delta = F L^3/(3 E I) + F L/(kappa G A)
theta = sign * F L^2/(2 E I)
```

The existing test compares displacement and rotation at relative tolerance `1e-12`. The wrapper records both values, absolute/relative differences, model parameters, and sign convention before applying the same assertions. No new tolerance is introduced. The model values are SI-valued as written in the source test; QF Solver's input schema does not itself impose a universal unit system.

## Theoretical references (not solver results)

Formula substitution yields the following analytical reference values. The measured QF Solver values and discrepancies from the authorized execution are recorded in the [execution report](WP12_S_EXECUTION_REPORT.md); the checks agreed to the existing `rel=1e-12` criteria. These cases each use one straight element and do not establish mesh convergence or 3-D validation:

| Plane | Reference tip displacement | Reference tip rotation |
|---|---:|---:|
| UY / Iz / RZ positive | approximately `0.00423577566138 m` | approximately `+0.00317460317460 rad` |
| UZ / Iy / RY negative | approximately `0.00635217777778 m` | approximately `-0.00476190476190 rad` |

## Limits

This is a one-element, uniform, straight, fixed-free beam comparison in two principal planes. It checks the chosen bending inertias and sign convention against a one-dimensional closed form. It is not a mesh-refinement study, orientation-general test, shell/solid correlation, 3-D continuum validation, or general qualification of BEAM2. Reactions and strain energy are not emitted by this wrapper; they are not required for these two existing assertions.
