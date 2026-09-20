# WP09 HEX8-only formal requalification — R1

## Contract and provenance

This campaign formally isolates HEX8 from the historical TET4 route. TET4 is
excluded from this contract and its previous `FAIL_CLOSED` evidence remains
unchanged and preserved.

```text
BRANCH = codex/wp09-hex8-only-formal
EXECUTION_SHA = 2b6350c8b6bb45d16ca13ee716af97b5aa247db5
CONTRACT_SHA256 = 42b33386ca4da1e199a13517255007eaf2fa74ea5af52ea694062ca0d54592b6
FAMILY_SCOPE = HEX8 only
LOAD_SCALE = 0.25
LOAD_PATH = [0.25, 0.5, 0.75, 1.0]
```

The campaign uses the legacy WP09 hierarchy: `cells = 1, 2, 4` along the
existing refinement direction. Thresholds, material, tolerances, solver
backend, fallback policy, and local-strain bound were not relaxed.

## Stage results

| Stage | Mesh | Nodes | Elements | DOFs | Structural | Reference | Replay |
|---|---:|---:|---:|---:|---|---|---|
| M1 | HEX8 cells=1 | 8 | 1 | 24 | PASS | PASS | PASS |
| M2 | HEX8 cells=2 | 12 | 2 | 36 | PASS | dependency PASS | PASS |
| M3 | HEX8 cells=4 | 20 | 4 | 60 | PASS | dependency PASS | PASS |

The independent reference is the existing material-point/affine-element
recomputation. It is independent of production contact/element routines, but
it is not an independent global FEM/Newton solve.

## Structural observables

| Stage | max displacement | reaction norm | energy | max von Mises | max local strain | force balance | moment balance |
|---|---:|---:|---:|---:|---:|---:|---:|
| M1 | 1.065944e-03 | 2.500000e-01 | 1.412232e-04 | 2.909757e-02 | 1.401096e-03 | 6.273e-11 | 4.451e-11 |
| M2 | 3.627957e-03 | 2.500000e-01 | 4.829699e-04 | 6.811637e-02 | 6.134e-03 | 1.586e-11 | 1.127e-11 |
| M3 | 9.193498e-03 | 2.500000e-01 | 1.225722e-03 | 1.490561e-01 | 1.605e-02 | 3.161e-09 | 2.235e-09 |

All structural envelope and equilibrium gates pass for the three stages. The
replay comparisons are exactly zero for the recorded observables.

## Closure gate

The frozen M2→M3 mesh gate is `5%` for displacement/energy and `10%` for
von Mises stress. It fails as follows:

```text
DISPLACEMENT_DELTA = 60.537800%
REACTION_DELTA = 1.258e-08
ENERGY_DELTA = 60.597109%
VON_MISES_DELTA = 54.301532%
```

Therefore:

```text
M1_STATUS = PASS
M2_STATUS = PASS
M3_STATUS = PASS
REFERENCE_STATUS = PASS
REPLAY_STATUS = PASS
MESH_CLOSURE = FAIL_CLOSED
WP09_HEX8_ONLY_FORMAL_STATUS = FAIL_CLOSED
WP09_FORMAL_POINTS = 0/8
```

The H4 isotropic HEX8 diagnostic campaign remains useful evidence, but it does
not repair this legacy H2→H3 closure failure: its H3→H4 deltas also remained
well above the frozen limits.

## Interpretation and next step

The HEX8-only split is technically coherent: the element solves, independent
reference, replay, local-strain envelope, and equilibrium are all clean at
M1–M3. The remaining blocker is mesh sensitivity, not TET4 contamination.

No threshold or result was altered to obtain this conclusion. The next
decision is either to retain HEX8 as `EXPERIMENTAL_BOUNDED`, or to define a
new HEX8-only mesh/closure contract with a physically justified refinement
strategy (preferably the isotropic hierarchy) before another formal campaign.

No official WP09 points are awarded by this report.
