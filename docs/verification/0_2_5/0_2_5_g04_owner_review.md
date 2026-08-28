---
doc_id: DOC-NL-025-029
revision: 0.2
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: "Owner"
approver: ""
---

# QF Solver 0.2.5a0 Owner review: 025-G04

## Decision identity

| Field | Value |
|---|---|
| Gate | `025-G04` |
| Owner decision | `REQUIRED` |
| Qualified source SHA | recorded in `results/vnv_0_2_5/g04_latest/evidence_manifest.json` |
| Qualified source worktree | `CLEAN` at evidence start |
| Evidence pack | `results/vnv_0_2_5/g04_latest/` |
| Evidence manifest | `results/vnv_0_2_5/g04_latest/evidence_manifest.json` |
| Contract lowered | `NO` |

This review records the available evidence and the reasons the gate cannot be
closed. It is not a release decision and does not authorize a tag, push or
package publication.

## Contract audit

The G04 contract requires all of the following in the same bounded scope:

- a true FEM branch crossing a limit point and continuing post-limit;
- complete load-factor/displacement and reaction histories;
- a coarse/medium/fine/refined branch study, or an explicit Owner-approved
  bounded refinement decision;
- restart before or near the turn, plus controlled rollback and retry;
- analytical or published branch reference;
- the mandatory Code_Aster external correlation of the complete branch;
- clean-source provenance and digest-controlled evidence.

The contract does not accept a reduced shallow-arch model as a FEM proof, does
not accept Newton convergence alone, and does not allow a monotone external
path to stand in for a missing post-limit correlation.

## Evidence assessment

### QF Solver common-driver FEM

The common-driver run is a genuine sparse two-element TET4 path:

| Quantity | Observed value |
|---|---:|
| Nodes / global DOF | `5 / 15` |
| Continuation steps | `80` |
| Arc-length radius | `0.02` |
| Control DOF | `14` |
| Load-factor range | `[-0.0373265418, -0.0007272447]` |
| Control-displacement range | `[-0.9419440185, -0.0115649488]` |
| Turning points | `1`, around step `75` |
| Maximum relative residual | `2.8114e-11` |
| Minimum `det(F)` | `0.4414340033` |
| Evidence status | `PASS_INTERNAL_RESEARCH` |

The signed load factor reverses between steps 76 and 77 while the control
displacement continues. The targeted tangent diagnostic finds the smallest
reduced-tangent eigenvalue crossing from positive to negative at the turn,
with a reassembled free residual below `5e-13` and positive `det(F)`. This
demonstrates the intended internal branch diagnostic, but it is still a
minimal research path and not a qualified FEM release scope.

### Restart and rollback

The controlled internal helpers pass restart checks before and after the
observed turn. They reproduce the continuation suffix, displacement endpoint
and material state. The adversarial run injects a failure after two Newton
corrections at step 76 and records a radius reduction from `0.02` to `0.01`
with a clean retry.

These results are `PASS_INTERNAL_RESEARCH`. They do not provide the missing
external correlation or mesh study.

### Reduced analytical reference

The reduced shallow-arch equation remains useful for algorithmic verification
and crosses its analytical limit point. It is not a finite-element reference
for closing G04.

### Code_Aster external branch diagnostic

The historical Code_Aster result was an executed configuration mismatch, not a
solver disagreement. QF applies a positive reference force with a negative
load factor, hence the physical loading is downward; the old Code_Aster deck
applied `FZ=+1/3` and followed the upward branch. It also measured the mean
`CROWN/DZ`, while QF controls apex node N5 `UZ` (global DOF 14), and used an
unmatched continuation window.

The corrected pinned Docker replay uses the same unperturbed two-element TET4
geometry, `FZ=-1/3`, `APEX/DZ`, and a `0..0.96` window sampled at 160 intervals.
It produces a complete branch and one turning point. QF-versus-Code_Aster is
compared by apex displacement, because the solvers do not use the same
arc-length parameterization:

| Quantity | Observed value |
|---|---:|
| Image | `simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435` |
| External path | complete |
| External turning points | `1` |
| Maximum branch load-factor difference | `4.8719e-07` |
| Peak-normalized maximum difference | `1.3052e-05` |
| Turning-load difference | `6.3485e-08` |
| External diagnostic status | `RESOLVED_CONFIGURATION_MATCH` |

This is bounded code-to-code diagnostic evidence. It removes the historical
external-deviation blocker but is neither physical validation nor sufficient to
close G04 on its own. The detailed parameter audit is recorded in
`0_2_5_g04_external_branch_diagnostic.md`.

## Gate decision

```text
025-G04 = OPEN
OWNER DECISION = REQUIRED
MESH DECISION = OPEN_MISSING_REQUIRED_LEVELS
CODE_ASTER = RESOLVED_CONFIGURATION_MATCH
CONTRACT LOWERED = NO
```

## Exact remaining blockers

1. Link and reproduce a published FEM snap-through branch reference. The
   current two-element configuration is custom and no exact public reference
   has been identified.
2. Execute and archive the required coarse/medium/fine/refined arc-length
   branch study, or obtain an explicit bounded-refinement Owner decision.
3. Regenerate a final controlled G04 pack only after the preceding evidence is
   available.

Until these blockers are addressed, no qualified arc-length production claim
is made. G03, G05 and G06 remain unchanged.
