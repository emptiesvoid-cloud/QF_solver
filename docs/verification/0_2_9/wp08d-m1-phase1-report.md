# WP08-D Phase-1 M1 execution report

## Scope and provenance

This report records the one authorized WP08-D Phase-1 production execution at
M1, its independent NumPy KKT reference, and its deterministic production
replay. The governing branch was advanced locally and remotely to the runner
integration merge before execution; the evidence branch remained
`0.2.9-wp08d-m1-phase1` until final evidence integration.

- governing SHA after runner merge: `d2a333a6427de1ce02e7719b4eca5b8ef0eb5bab`
- runner SHA authorized: `6683af19818bffe4771e21677cca47f3f440e6e1`
- contract digest: `d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a`
- governing policy digest: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`
- M1: 16 nodes, 12 TET4 elements, 48 DOFs; seven frozen load increments
- route: initial fixed-face normal Lagrange active-set with regularized Coulomb,
  serial direct backend, no fallback

No M2, M3, H4, WP05, WP06, WP07, or full repository suite was run.

## Production M1

`qualification/0_2_9/wp08d_phase1/M1/result.json` is valid and terminally
`PASS`; its non-certifying generic result warning is the pre-existing
engineering-profile maturity warning, not a numerical failure.

The frozen path accepted all seven increments. The final state is an
open-contact state: active contact count `0`, all four contact states `open`,
minimum slave gap `0.002968439216367153`, zero pressure, zero contact
resultants, and zero cumulative dissipation. This is reported as
`PASS_OPEN_NO_CONTACT`; it does not claim that stick/slip was exercised.

Equilibrium from the production result:

- force relative error: `4.8074305725478e-15`
- moment relative error: `7.806091302554032e-15`
- selected displacement: `0.017039071688671508`
- reaction resultant: `[149.9999999999991, -7.105427601002e-14, 999.9999999999951]`
- reaction moment: `[500.00000000000057, -921.9999999999918, -74.99999999999977]`

The primary run's telemetry contains flushed lifecycle/step events and all
seven accepted increments. A runner route-context defect discovered after
that run suppressed the internal `ASSEMBLY_END`/`LINEAR_SOLVE_*` route events
in this primary JSONL; the raw numerical result is unaffected. The defect was
fixed in the tooling before replay. The primary limitation is preserved here,
not silently repaired in the raw file.

## Independent reference

The matching independent M1 reference uses an independently assembled dense
TET4 elastic matrix, explicit fixed-DOF KKT constraints, and the pure NumPy
KKT/return-map module. It imports no production contact routine. The frozen
load path is replayed for all seven increments. Because the production state
is open contact, the reference is the contract's `open_no_contact` KKT case.

Final reference checks:

- status: `PASS_REFERENCE`
- force equilibrium: `6.247799189332917e-15`
- moment equilibrium: `1.1073971008993349e-14`
- minimum slave gap: `0.0029684392163672295`
- full displacement relative delta: `4.322414648920085e-15`
- selected displacement relative delta: `0.0`
- reaction relative delta: `2.9124602944169367e-15`
- moment relative delta: `3.4278894313603834e-15`
- normal/tangential contact resultant deltas: `0.0` / `0.0`
- cumulative dissipation delta: `0.0`

An earlier reference-only artifact with a mismatched scalar displacement
extractor is preserved under
`qualification/0_2_9/wp08d_phase1/independent_reference/M1_pre_observable_fix/`.
The final `independent_reference/M1/` evidence uses the corrected production
definition (maximum absolute displacement component).

## Deterministic replay

The second production execution was the explicitly authorized M1 replay. Its
result and raw fields match the primary result within the replay contract
(`relative <= 1e-12`, `absolute <= 1e-14`). The replay checker returned
`PASS`; all compared scalar/vector observables were identical at serialized
precision, the seven-increment path length and terminal status matched, and
the corrected telemetry route emitted the internal static-route lifecycle and
linear-solve events.

## Governance decision

- production mechanics changed: `NO`
- thresholds changed: `NO`
- solver parameters changed: `NO`
- fallback changed: `NO`
- M2: `NOT_RUN`
- M3: `NOT_RUN`
- WP08-D formal status: `PREPARATION_ONLY_PHASE1_EVIDENCE`
- WP08-D formal points: `0/2`
- WP08 formal points: `0/8`
- qualification claim: `NO_FORMAL_WP08D_CLOSURE`

This M1 evidence does not satisfy the M2→M3 refinement gate. Owner review is
required before any M2 authorization.

The final governing remote SHA and the dedicated evidence commit are recorded
in `qualification/0_2_9/wp08d_phase1/wp08d_m1_phase1_final.json` and in the
Git handoff accompanying this report.
