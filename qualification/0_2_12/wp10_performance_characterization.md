# WP10 — Bounded performance and memory characterization

## Method

Compared the exact WP09 baseline commit `eb3dde63d487f5a88f9dd34e043ca561407018f7` with the WP10 working tree using the same Python process version, fixture helper, TET4 model, 12 physical DOFs, empty material state, and temporary local NPZ file. The baseline was checked out in a temporary detached worktree and removed cleanly after measurement. Each timing is a median and empirical p95 over 100 iterations for snapshot/transaction calls or 30 iterations for identity and file operations. Measurements include warm filesystem/runtime effects and are not a benchmark suite.

## Results

| Operation | WP09 median / p95 (ms) | WP10 median / p95 (ms) | Interpretation |
|---|---:|---:|---|
| Detached state snapshot | 0.0203 / 0.0286 | 0.0175 / 0.0230 | No material change at this fixture scale |
| Begin trial + rollback | 0.1883 / 0.2460 | 0.1987 / 0.2609 | Small lifecycle-marker/digest overhead, within noisy microbenchmark scale |
| `model_signature_v2` | 0.0705 / 0.0937 | 0.0685 / 0.1059 | Unchanged; component digest computation is additional at save/load boundary |
| Checkpoint save | 4.0195 / 6.6557 | 4.4482 / 5.2539 | Median +10.7%; identity and metadata integrity digests add bounded serialization/hash work |
| Checkpoint load with model verification | 0.8360 / 0.9867 | 1.1954 / 1.3327 | Median +43.0%; load verifies metadata integrity and component identities in addition to v2 signature/topology |
| Checkpoint size | 1300 bytes | 1917 bytes | +617 bytes for explicit identity metadata, integrity digest, and lifecycle state |

The p95 values are noisy and do not consistently increase in the same proportion as medians. The measurements cover one tiny state and do not measure full nonlinear Newton runtime, a large material/contact state, network storage, or a long rejection history.

## Cost interpretation

- The new identity digests are computed at checkpoint boundaries, not each Newton iteration.
- State transaction isolation continues to use the existing detached composite copies and deterministic digests; no global cache was introduced.
- Rejection history is copied with accepted continuation metadata. Long runs with frequent rejections may grow checkpoint size; no history truncation was introduced because it would discard failure provenance.
- No measured evidence supports a claim about global solver speed or production-scale checkpoint scaling.

## Status

The bounded measurements support accepting the added checkpoint-boundary cost for stronger restart evidence, subject to the above scale limitation. Global Newton performance remains a separate, unmeasured quantity in WP10.
