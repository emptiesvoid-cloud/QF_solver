# WP08-D M2 reference/replay and conditional M3 report

## Scope

This report records the Owner-authorized M2 independent-reference attempt. The
accepted corrected production M2 evidence was read-only and remains unchanged.
No production solve, replay, or M3 solve was run by this task after the
frozen-contract reference failed.

Start SHA: `0510e6fbc70e61454304b88b2b64662e2f87d5bb`  
Branch: `0.2.9-wp08d-m1-phase1`  
Contract digest: `d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a`  
Policy digest: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`  
Independent-reference harness commit: `163b879`

## M2 production evidence

The accepted production result remains `PASS`: M2 (49 nodes, 96 TET4, 147
DOFs), 7/7 accepted increments, active contacts `[3, 7, 11]`, zero fallback,
force equilibrium `2.359249378146216e-14`, and moment equilibrium
`4.591631339243615e-14`. Its raw result, checkpoints, telemetry and manifest
were not modified.

## Blocking provenance finding

The frozen contract declares the load path

`[(1, 0), (1, 0.25), (1, 0.75), (1, 1), (1, 1.25), (1, 0.25), (1, -0.5)]`.

The accepted production route is constructed by
`scripts/wp08d_phase1_common.py::_load_vector_from_contract`; its first
increment is actually `(normal_factor=1, tangential_factor=1)`, followed by
the same remaining six factors. This is a contract/runner provenance drift,
not a threshold adjustment and not a production mechanics change made here.

## Independent M2 reference

The independent reference uses its own dense TET4 assembly, normal KKT solve
and Coulomb return-map implementation. Static inspection confirms it imports
no production contact routine. With the frozen contract path it accepted four
increments, retained normal active set `[3, 7, 11]`, and failed closed at
increment 5 with:

`Independent active-slip root failed: residual=3.290e+00.`

The complete failure evidence is under
`qualification/0_2_9/wp08d_phase1_mixed_open_active_slip_requalification/independent_reference/M2_frozen_contract_fail_closed_final/`.

The corresponding diagnostic run using the accepted production path is under
`qualification/0_2_9/wp08d_phase1_mixed_open_active_slip_requalification/independent_reference/M2_actual_production_route_final/`.

As a separate diagnostic, the reference was run with the load path actually
used by the accepted production evidence. That run passed 7/7 increments and
matched production observables: displacement `1.87e-15`, reaction
`6.92e-14`, moment `1.09e-13`, normal-contact resultant `2.79e-13`,
tangential-contact resultant `2.35e-13`, and dissipation `1.01e-13` relative
deltas. This is diagnostic provenance evidence only; it does not convert the
frozen-contract reference to PASS.

## Fail-closed dependency decision

Because the frozen-contract independent reference did not pass, replay was not
run and M3 was not run. No M2 or WP08-D formal point is awarded.

| Item | Status |
|---|---|
| M2 corrected production | `PASS` — accepted evidence unchanged |
| M2 independent reference, frozen contract | `FAIL_CLOSED` |
| M2 replay | `NOT_RUN_FAIL_CLOSED_REFERENCE_DEPENDENCY` |
| M2 decision | `FAIL_CLOSED` |
| M3 production/reference/replay | `NOT_RUN` |
| WP08-D formal points | `0/2` |
| WP08 formal points | `0/8` |

## Validation and governance

Targeted WP08-D/contact tests: 17 passed. Ruff, targeted mypy and compileall
pass for the new independent-reference harness. No full repository suite was
run. Thresholds, fallback policy, mesh, loads, solver tolerances and
production contact mechanics were not changed in this task. The previously
authorized stick-predictor mechanics fix remains the only production mechanics
change represented on the branch.

`FINAL_STATUS = HOLD_OWNER_REVIEW_REQUIRED`  
`NEXT_STEP = Owner review of the contract/runner first-increment provenance;
no replay or M3 until the frozen route is reconciled.`
