# WP13-RBE integration preparation report

Date: 2026-10-21
Repository: `https://github.com/emptiesvoid-cloud/QF_solver.git`
Dedicated branch: `codex/wp13-rbe-integration-20261021`

## Decision and outcome

The Owner approved bounded maturity for the RBE2, RBE3 rigid-body projection,
and acyclic MPC reduction scopes in
`wp13_rbe_owner_maturity_decision.json`. This report records the integration
preparation and regression; it does not merge or publish the change.

The source implementation and its tests were integrated by cherry-picking only
WP13 commit `dc3fed78a33e7557e0214916dbdcf659ed5944ab` onto the verified latest
v0.2.12 work-package baseline. The seven targeted modules then passed **100
tests, 0 failures, 0 skips** on the integration checkout. The original WP13
qualification report and its 100-pass result are preserved byte-for-byte.

## Authoritative target discovery

The checkout remote is `origin
https://github.com/emptiesvoid-cloud/QF_solver.git`. At inspection, the only
remote development branch was `origin/main` at `e367fe58b2b9ebb4aef321424ca775e80e82d9ca`,
the v0.2.11 line. No authoritative v0.2.12 integration branch was present.
The latest sequential local v0.2.12 work-package baseline was
`codex/v0.2.12-wp10-nonlinear-state-checkpoints` at
`1d7fef04094d2f4b920795b4b3c25f052fcf21c0`; it is used as a reviewed
integration base, not represented as the canonical release target.

The integration worktree is
`<legacy-worktree>\solveur\tmp\wp13-rbe-integration`.
It was created separately from active work-package worktrees. The implementation
commit is `d07fdf72e487ac35e2ef9afaccc8d9c46f25d4bd`. It contains only the 11
WP13 RBE/MPC implementation, test and documentation files. There were no merge
conflicts. The RBE implementation files at the chosen base matched the
pre-WP13 implementation, so the cherry-pick did not replace a newer RBE/MPC
implementation. No E01, C02, D01, public solver dispatch, or other work-package
files were changed by the implementation commit.

## Integrated regression

Command from the integration checkout, with one numerical-library thread and
external Code_Aster execution disabled:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:QF_SOLVER_RUN_EXTERNAL='0'; python -m pytest -q tests/unit/test_rbe_links.py tests/unit/test_mpc_reduction.py tests/unit/test_backend_edge_matrix_contracts.py tests/unit/test_mesh_validation.py tests/unit/test_mesh_validation_edge_contracts.py tests/unit/test_code_aster_rbe.py tests/unit/test_wp13_02_mixed_dynamic_validation.py
```

Observed result: **100 passed in 3.33 seconds**, exit code 0; shell wall time
was approximately 5.9 seconds. No external Code_Aster job was launched. This
is a fresh run on the integration checkout, distinct from the original 100-pass
run and the historical 89-pass result.

The frozen source qualification identity remains source commit
`dc3fed78a33e7557e0214916dbdcf659ed5944ab`, Git tree
`81516bf096a4d66443d88479325f8e32a23ff698`, qualification report SHA-256
`8a2805b9be7010e11c0f097e5445f74d1a57290a89137879fb18f119c707c7a4`. The
integration checkout has its own tree identity because it is based on the
WP10 commit and contains the approved WP13 patch rather than the source branch's
other ancestry.

The following implementation and test file SHA-256 values were recomputed on
the integration checkout and match the frozen WP13 source report:

| File | SHA-256 |
| --- | --- |
| `src/solveur/core/rbe.py` | `3031c1c106c220e96c8b2e16dd0fe57a5efe028792891962867b8351ec95793c` |
| `src/solveur/core/constraints.py` | `428f9d2bd907859e37a2dc8ea7e86102d804c1ec61c3473051cf85ab4fca9b41` |
| `src/solveur/io/constraint_schema.py` | `08735d9c518097053597967dabc9f2aa2630a5b836d9daa1931502332ea50a6a` |
| `src/solveur/mesh/validation.py` | `2f80e5f2f17f5138ac875bc32d9e46ad416a9941b11ba13688188ec23b4642b6` |
| `src/solveur/mesh/validation_rank.py` | `b286c05fa98dd0d1eb6c14e6b6e51fa567c25b01c61838c870874d6bdb71ee7b` |
| `tests/unit/test_rbe_links.py` | `d730601b7d7c284273537cb987d5518d76334b81324adf58451833344428d815` |
| `tests/unit/test_mpc_reduction.py` | `c6d2c0c5685ed9d614c4ae696db4fffe322409904e7fa19e9abff859880ea009` |
| `tests/unit/test_mesh_validation_edge_contracts.py` | `aef73bb9dbc1c1996bd81caedafbf070028c5c895b589f9f3b5f9a4807126557` |

The historical audit's Git blob is identical in the frozen source and
integration commits. Its frozen source working-tree SHA-256 is
`649c84dd94b05e0a107979131e9f2fcfd2f26b96bcefce1cc6c1bc92d17b0c74`; the
integration worktree checks it out with CRLF endings, so a raw working-file
hash differs while the Git blob and document content remain unchanged.

## Owner-approved maturity matrix

| Capability | Approved status | Boundaries |
| --- | --- | --- |
| `RBE2_LINEAR_STATIC` | `QUALIFIED_BOUNDED_OWNER_APPROVED_PENDING_INTEGRATION` | Small-displacement linear statics and tested rigid-arm/acyclic constraint configurations. `tie_rotations` only where mechanically meaningful. |
| `RBE3_RIGID_BODY_PROJECTION_LINEAR_STATIC` | `QUALIFIED_BOUNDED_OWNER_APPROVED_PENDING_INTEGRATION` | Six reference DOFs; translational support DOFs; positive weights; full-rank geometry with `sigma_min/sigma_max > 1e-12`. |
| `MPC_REDUCTION_ACYCLIC_LINEAR_STATIC` | `QUALIFIED_BOUNDED_OWNER_APPROVED_PENDING_INTEGRATION` | Verified affine, compatible, acyclic linear-static constraints. |
| `RBE3_WEIGHTED` | `VERIFIED_BOUNDED` | Per-component algebraic interpolation/extrapolation. General spatial moment preservation is not guaranteed. |
| `MPC_RANK_DIAGNOSTIC` | `VERIFIED_BOUNDED` | Maximum 180 active DOFs; dense reduced-system diagnostic with conservative threshold, not a universal rank oracle. |

The runtime `capability_registry_v2.json` and compatibility preflight were not
changed. Their current key does not distinguish an RBE/MPC constraint scope
from all other linear-static routes; changing it here could grant a broader
capability than the Owner approved. Accordingly, this branch documents the
approved capability-specific maturity, while runtime maturity output remains
unchanged until a separately reviewed exact-scope registry mechanism is
available. `AUTHORITATIVE_INTEGRATION` remains `PENDING` because a canonical
v0.2.12 integration target has not been identified. `PUBLIC_RELEASE` remains
`NOT_AUTHORIZED`.

## User examples

Two SI input decks and their independent analytical responses are included:

* `examples/rbe2_rigid_offset_combined_wrench.json` with
  `docs/elements/rbe_user_examples.md`: one rigid arm, offset `(2,1,0) m`,
  combined slave force and master moment, explicit spring/support reactions.
* `examples/rbe3_unequal_weight_projection.json` with the same guide: six
  supports on three opposite coordinate-axis pairs with unequal positive
  weights `1,2,3`; expected force distribution follows `H^T` and closes both
  resultant and moment.

These are reproducible model inputs with analytically derived reference values.
Both input decks were parsed by `JsonModelReader` with `PYTHONPATH=src`; no
assembly or solve was performed for them. They are not external correlations.
Their response calculations and scope limits are documented in the example
guide.

## Independent review and limitations

An independent read-only reviewer examined the original WP13 source changes.
After the implementation corrected the rank-warning fallback finding, the
reviewer reported no open P0/P1/P2 findings. That review checked RBE2 arm signs
and the six-mode RBE3 projection identity, but it did not execute tests. The
integration cherry-pick was conflict-free and preserves the reviewed source
patch; the integration-branch documentation and examples received primary
agent self-review. There was no separate reviewer re-execution of the
integration tests.

The original Code_Aster 18.1.0 one-arm RBE2 correlation remains
`HISTORICAL_NOT_RERUN`; Docker was unavailable in the qualification campaign.
There is no external RBE3 correlation. Remaining limitations include dense
rank checking only through 180 active DOFs, no general rank analysis of all
redundant MPC compositions, no large-model cost characterization, no mesh
refinement convergence campaign, and no qualification for modal, harmonic,
transient, nonlinear, contact, or general Nastran behavior.

## Source and Git provenance

Frozen source provenance:

* Approved source commit: `dc3fed78a33e7557e0214916dbdcf659ed5944ab`
* Approved source Git tree: `81516bf096a4d66443d88479325f8e32a23ff698`
* Source qualification report SHA-256:
  `8a2805b9be7010e11c0f097e5445f74d1a57290a89137879fb18f119c707c7a4`
* Historical audit SHA-256:
  `649c84dd94b05e0a107979131e9f2fcfd2f26b96bcefce1cc6c1bc92d17b0c74`

The implementation and integration-report hashes, complete final integration
tree hash, and final clean HEAD are recorded in the campaign completion
message after the documentation commit.

## Final status

* `RBE2_LINEAR_STATIC`: Owner-approved `QUALIFIED_BOUNDED`, pending authoritative integration.
* `RBE3_RIGID_BODY_PROJECTION_LINEAR_STATIC`: Owner-approved `QUALIFIED_BOUNDED`, pending authoritative integration.
* `MPC_REDUCTION_ACYCLIC_LINEAR_STATIC`: Owner-approved `QUALIFIED_BOUNDED`, pending authoritative integration.
* `RBE3_WEIGHTED`: `VERIFIED_BOUNDED`.
* `MPC_RANK_DIAGNOSTIC`: `VERIFIED_BOUNDED`, at most 180 active DOFs.
* `EXTERNAL_CODE_ASTER_CORRELATION`: `HISTORICAL_NOT_RERUN`.
* `AUTHORITATIVE_INTEGRATION`: `PENDING`.
* `PUBLIC_RELEASE`: `NOT_AUTHORIZED`.

The next decision is to designate or create the authoritative v0.2.12
integration target and review this branch for final merge approval. No merge
or publication was performed.
