# 0.2.6 G07 Step B1 — Arc-Length Targeted Evidence

Evidence ID: `026-G07-B1-ARC-LENGTH-001`  
Baseline start SHA: `eb105657f1d5f1a0994f5598327a290358f37e7e`  
Execution source SHA: `84087a22dd51fe1445a5dad51fc690bfe8b7c85e`  
Gate status preserved: `026-G07 = NOT_STARTED`  
Functional source changed: `NO`

The complete machine-readable record is
[`g07_b1_arc_length_evidence.json`](../../../qualification/0_2_6/g07_b1_arc_length_evidence.json).
The runner is [`run_g07_b1_arc_length.py`](../../../scripts/run_g07_b1_arc_length.py).
This step is targeted evidence only; it does not modify TL, change a
formulation, or close G07.

## Predeclared ARC-002 design

The same TET4 snap-through benchmark and fixed solver regime were evaluated
with two arc-length radii (`0.01` and `0.02`) on two conforming meshes:

| Mesh | Definition | `R_SMALL` | `R_NOMINAL` |
| --- | --- | --- | --- |
| `M_COARSE` | reference two-TET4 bipyramid | 160 steps | 80 steps |
| `M_REFINED` | one-to-eight conforming refinement, 16 TET4 | 160 steps | 80 steps |

Before execution, case validity required completion of the declared step
window, a detected branch turn, finite load/displacement/residual/determinant
fields, non-duplicate path points, and positive `det(F)`. The bounded
sensitivity report uses relative turning-point changes when both turning
points exist; no universal numerical stability threshold is introduced.

### Result

The two coarse-mesh settings completed finite continuous paths with one
turning point each. Their relative turning-point changes were:

- load factor: `3.6021e-12`;
- control displacement: `1.7822e-08`.

Both refined-mesh settings also completed with solver status `PASS`, finite
fields, positive minimum `det(F)` (`0.8886481`) and continuous paths, but no
turning point was observed in either predeclared window. They are therefore
classified `DEFER`, not PASS or solver failure. The mesh turning-point
sensitivity comparison is not available for this refined series.

`ARC-002 = DEFER`: the run provides discriminating bounded evidence, but the
turning-point sensitivity gap remains open. A future case must use an
equivalent refined boundary/load discretization or an Owner-approved compatible
continuation window before this gap can be closed.

## ARC-003 restart and rollback

Three route-native cases were executed on the nominal coarse benchmark:

| Case | Result | Evidence |
| --- | --- | --- |
| restart before turn | `PASS_BOUNDED` | checkpoint step 75, suffix error `0`, final state digest equal |
| restart after turn | `PASS_BOUNDED` | checkpoint step 76, suffix error `0`, final state digest equal |
| controlled rollback near turn | `PASS_BOUNDED` | explicit `MAX_ITERATIONS`, rollback before retry, clean retry |

The before-turn restart was replayed. Classification, checkpoint step, state
digest and final digest were identical. No ghost state was detected.

## Step B1 conclusion

Runtime assertions passed for all eight recorded runtime rows (four ARC-002
cases, three ARC-003 cases and one restart replay): deterministic replay,
finite runtime fields, no silent PASS and state integrity. External calculation
was not run by policy. No numerical regression was observed and no functional
source changed.

`G07_B1 = PARTIAL`  
`ARC-003 = PASS_BOUNDED`  
`ARC-002 = DEFER`  
`ARC_LENGTH_OWNER_CANDIDATE = PASS_WITH_LIMITATIONS / ARC-002_DEFERRED`

The remaining blocking gap is the refined-mesh turning-point comparability in
ARC-002. G07 remains `NOT_STARTED`; Owner closeout is not yet ready.
