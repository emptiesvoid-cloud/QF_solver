---
doc_id: DOC-029-WP08-AREA-SUPPORTED-CONTACT-R1-13-RESULTS
revision: 1.0
status: owner_accepted_experimental_with_limitations
applicable_version: 0.2.9-development
---

# WP08 area-supported contact R1.13 — results for Owner review

## Verdict

`PASS_CANDIDATE_DIAGNOSTIC_ONLY_WITH_MESH_SENSITIVITY`

All six frozen production cases passed their per-case diagnostic gates on the
R1.13 source: stick and slip on M1, M2, and M3. This is useful new-source
evidence that the bounded contact route converges on these cases. It is not a
formal WP08 qualification or a mesh-convergence pass. The contract explicitly
has no frozen mesh-delta acceptance threshold, and the slip displacement is
strongly mesh-sensitive.

## Provenance and authorization

| Item | Value |
|---|---|
| Branch | `codex/wp08-area-contact-r1-13` |
| Execution/source SHA | `b5dde151ff827f140e0431c3cf45a4c18871d5cd` |
| Source bundle SHA-256 | `8b77205273d9570f1588af06bd103fe5d2a2a4c1e7f559d5733564a25aad5aff` |
| M1 contract SHA-256 | `a81c9b07d9bfc457c8ef5ab48cfd9dcc1f4eab8430f6fc04136889c3229c790a` |
| M1 final SHA-256 | `b4035a3d58f48cdfe9901336f81d2037f47857c7fab0ef6d5bb42f85187804b3` |
| M2/M3 contract SHA-256 | `08c568984bd63f66bc7cf30be5407b190ac351cec6f3543f11cb839d09322b4f` |
| M2/M3 execution-binding digest | `824c6d94cacc423104482e469d926524210b3a863ef78538b03526d14b1ea613` |
| M2/M3 final SHA-256 | `37415a0d37728b88072a163ec93da2358c4d9294391de3bc774bed741fd9b33e` |
| Frozen contract document SHA-256 | `21aef0621553c01cf4183e317d919bf78f2b27a9b2f74af301e3f843b5c951d6` |

The M1 and M2/M3 bindings use the same execution SHA and 982-file source
inventory. M1 evidence was reverified before the M2/M3 binding was frozen. The
R1.12 M4 numerical failure remains preserved and unchanged; R1.13 did not rerun
M4. The R1.12 one-attempt authorization was not reused: this M1/M2/M3 campaign
was run under the active Owner task requesting these levels for Owner review.

Raw evidence is in the local campaign root:

```text
qualification/0_2_9/wp08_surface_stiffness_remediation/
  area_supported_r1_13_newton_merit_20260927/
```

The root contains the frozen contracts/bindings, six raw NPZ/result/telemetry
sets, process manifests and logs, and the split M1 and M2/M3 final records.
The post-run audit checked 34 referenced evidence files by SHA-256. These raw
files remain local/untracked; no push or merge was performed.

## Per-case results

Every case completed 8/8 load steps and passed its frozen per-case diagnostic
gates. The terminal state matched the requested stick/slip case. Force and
moment columns below are the recorded relative equilibrium errors.

| Mesh | Case | Gate | Active slave nodes | Active area fraction | Terminal state | Force balance | Moment balance |
|---|---|---|---:|---:|---|---:|---:|
| M1 | stick | PASS | 4 | 1.000 | stick | 1.48e-16 | 2.53e-16 |
| M1 | slip | PASS | 4 | 1.000 | slip | 6.31e-16 | 1.40e-15 |
| M2 | stick | PASS | 9 | 1.000 | stick | 7.42e-16 | 1.74e-15 |
| M2 | slip | PASS | 9 | 1.000 | slip | 3.10e-15 | 1.14e-14 |
| M3 | stick | PASS | 25 | 1.000 | stick | 2.99e-15 | 2.43e-15 |
| M3 | slip | PASS | 20 | 0.875 | slip | 2.16e-14 | 6.55e-14 |

All six child processes exited with code 0. Artifact hashes and process
manifests match. The result schema does not expose a reliable fallback count;
therefore this report makes **no zero-fallback claim**.

## Mesh-refinement observations

These deltas are descriptive only; the frozen R1.13 contract deliberately
does not define a mesh-convergence threshold.

| Case | Transition | Common-node displacement relative delta | Reaction resultant relative delta | Reaction moment relative delta | Normal contact resultant relative delta | Active area |
|---|---|---:|---:|---:|---:|---:|
| stick | M1→M2 | 1.652% | 6.13e-16 | 1.84e-6 | 0.574% | 1.000→1.000 |
| stick | M2→M3 | 0.973% | 2.44e-15 | 9.53e-7 | 0.244% | 1.000→1.000 |
| slip | M1→M2 | 24.883% | 2.48e-15 | 6.54e-7 | 0.139% | 1.000→1.000 |
| slip | M2→M3 | 24.541% | 1.86e-14 | 4.48e-6 | 1.142% | 1.000→0.875 |

The slip route is converging algebraically at each mesh, but its displacement
field is not mesh-stable under this hierarchy. M3 also has a smaller active
contact area. These are material limitations for any claim of spatial
convergence or general predictive accuracy; they are not hidden by the
per-case PASS labels.

## What changed and what did not

R1.13 aligns the active-slip Newton direction/Jacobian and Armijo merit with the
same pressure-normalized residual. The strict maximum per-contact residual
gate (`1e-9`) remains unchanged. The geometry, mesh hierarchy, material,
boundary conditions, load history, friction coefficient, surface stiffness,
iteration limits, enumeration guard, backend, and fallback policy were not
changed for this campaign. No solver code changed after execution.

## Validation and limits

- Targeted contact/runner tests: **78 passed**.
- Targeted mypy on `slip_root.py`: PASS.
- `compileall`: PASS.
- Document-registry JSON and `git diff --check`: PASS.
- Ruff: unavailable in the environment.
- Full test suite: not run.
- Independent global FEM/Newton reference: not run.
- Replay of the R1.13 solves: not run.
- External solver correlation: not run.
- Formal WP08 points: none awarded by this campaign; ledger unchanged.

The R1.13 policy digest is recorded as context only; the governing solver
policy was not enforced by this diagnostic runner. The R1.11 M1/M2/M3 results
are historical context, not substitutes for R1.13 evidence. R1.12 M4 remains
`FAIL_CLOSED_NUMERICAL` and is not reclassified by these M1/M2/M3 results.

## Owner decision

The Owner accepted the evidence as experimental with limitations on
2026-09-27. This does not imply formal WP08 requalification, mesh convergence,
zero fallbacks, independent-solver validation, or resolution of the R1.12 M4
failure. See the [Owner decision](wp08-area-supported-contact-r1-13-owner-decision.md)
and its [machine-readable record](../../../qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_13_newton_merit_20260927/r1_13_owner_decision.json).

Machine-readable audit: `qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_13_newton_merit_20260927/r1_13_final_audit.json`.
