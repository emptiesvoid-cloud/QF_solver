---
doc_id: DOC-NL-025-029
revision: 0.1
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

The existing common-driver run is a genuine sparse two-element TET4 path:

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
displacement continues. This demonstrates the intended internal branch
diagnostic, but it is still a minimal research path and not a qualified FEM
release scope.

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

### Code_Aster external result

The pinned Docker image was executed with the same unperturbed two-element
TET4 geometry, load distribution and apex displacement control. The Code_Aster
run completed and produced a complete history, but its reaction-derived load
factor is monotone and does not reproduce the QF turning point. This is a real
executed deviation, not an unavailable-tool `N/A`:

| Quantity | Observed value |
|---|---:|
| Image | `simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435` |
| External path | complete |
| External turning points | `0` |
| External status | `FAIL_EXTERNAL_BRANCH_REQUIREMENT` |

The complete QF-versus-Code_Aster branch correlation therefore remains
unresolved. The external result must not be labelled
`PASS_EXTERNAL_CORRELATION_BOUNDED`.

## Gate decision

```text
025-G04 = OPEN
OWNER DECISION = REQUIRED
MESH DECISION = OPEN_MISSING_REQUIRED_LEVELS
CODE_ASTER = FAIL_EXTERNAL_BRANCH_REQUIREMENT
CONTRACT LOWERED = NO
```

## Exact remaining blockers

1. Explain or correct the QF/Code_Aster branch discrepancy on the identical
   FEM case and archive a complete correlated branch.
2. Execute and archive the required coarse/medium/fine/refined arc-length
   branch study, or obtain an explicit bounded-refinement Owner decision.
3. Link a published or externally reproducible FEM snap-through reference.
4. Regenerate a final controlled G04 pack only after the preceding evidence is
   available.

Until these blockers are addressed, no qualified arc-length production claim
is made. G03, G05 and G06 remain unchanged.
