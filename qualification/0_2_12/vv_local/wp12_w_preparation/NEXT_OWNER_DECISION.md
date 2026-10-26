# Next Owner decision — WP12-W proposal

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**

This is a decision request template, not an approval. No W manifest, exact test nodeid, mesh file, attempt record or result exists yet.

## Decision requested after V2 review

1. Review the V2 receipt and outcome, including the full 24-column operator comparison, gamma assumptions, U3 archived residual/reaction/energy re-evaluation and every FAIL/INCONCLUSIVE condition. Preserve the U3 FAIL.
2. Decide whether the proposed longitudinal W1 (`16×4×4`) and coupled uniform-transverse W2 (`8×8×8`) are sufficient to answer the next mechanical question. Acknowledge that W2 changes `ny` and `nz` together and cannot separate them.
3. If separate y/z attribution is required, decide whether to prepare `8×8×4` and/or `8×4×8` as additional cases; these are not silently added here.
4. Approve or revise, before any run, the independent residual method, exact model/fixture generation and hashes, solver/backend, output definitions, acceptance logic, resource limits, one-attempt policy, evidence destination and local-environment limitations.
5. Require an exact manifest SHA-256 and one exact nodeid per separately approved campaign unit.

## Proposed sequencing

V2 review first. If V2 is FAIL or has an unexplained/inconclusive oracle, stop and decide on investigation before W. If the bounded H1 checks are interpretable, prepare the W manifest and evidence locations, then obtain a separate explicit Owner decision for W1/W2 before creating/running meshes. Any future pass remains evidence for those specific meshes and routes, not WP12 closure.

No execution, mesh creation, solver run, threshold change, maturity promotion, WP status change or release action is requested by this document.
