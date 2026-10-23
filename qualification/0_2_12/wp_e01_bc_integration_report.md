# WP-E01-BC — Controlled integration report

Date: 2026-10-23
Branch: `codex/v0.2.12-integration`
Integration baseline: HEAD `6b17ad538e90b5f63b61a66110a57ba6d479a63d`, tree `4d74385d6171ff139f07cbada7d4bf4a13b36b88`
E01 source snapshot: branch `emptiesvoids-cloud/wp-e01-ba-slave-bounded`, HEAD `3dc2f423e82ddb12fd82b8f23e764e757bad8278`, tree `212130de39ff9c59aa93ce652b67e8b2e1ce86c7`

## Decision and outcome

Owner decision BC approves recommendation B: `WP_E01=OPEN_WITH_BOUNDED_CERTIFICATES`. E01 is present in the v0.2.12 integration as an experimental capability set. It is not a release gate, does not close WP-E01, and does not close WP11, WP12, or WP13. No merge to `main`, release, tag, or publication is authorized.

The integration is intentionally selective. It adds the isolated Hencky material-point kernel and directional material-point tangent, binds their existing numerical tests to exact hashes, and carries the E01 evidence archive. It does not transplant the E01 branch’s contact/Newton implementation or research element/global adapters.

## Repository and compatibility audit

The E01 source worktree was clean at the HEAD/tree above. The integration target was clean at its required starting HEAD/tree. E01 is not an ancestor of the integration branch. The branches share merge base `1d7fef04094d2f4b920795b4b3c25f052fcf21c0`; the E01 source branch contains 716 commits not in the integration branch and its total diff is too broad for a branch merge.

The independent read-only reviewer found:

- 53 overlapping source/test paths between E01 and the current C02 tip, primarily in `src/solveur/contact/` and GF2/GF3/GF4 contact implementations. Whole-branch import or replacement of those paths is unsafe.
- Five shared paths in the E01 delta overlap post-base D02 changes: `src/solveur/__init__.py`, `src/solveur/api/__init__.py`, `src/solveur/api/public.py`, `src/solveur/core/constraints.py`, and `src/solveur/mesh/validation.py`. None was changed here.
- WP08 and WP09 are shared ancestors. StVK total-Lagrangian implementations already exist in the WP08–WP10 integration; no duplicate E01 StVK source was added.
- No P0 was identified. The unresolved J2 global tangent and C02/D02 shared-path overlap remain P1 blockers to broad E01 solver/contact integration and general qualification. They do not block the isolated material-point addition or documentation of the historical bounded certificate with its original identity.

A final independent read-only review of the selected integration and the BC roadmap overlay found no P0/P1. Its follow-up confirmed that the standalone `ROADMAP.md` explicitly states the current BC status and keeps the pre-BC roadmap as a byte-identical historical snapshot; the report’s overlay, snapshot, `pyproject.toml`, and BA/BB evidence hashes match the files. No unresolved P2 remains for this documentation issue. The reviewer did not edit files or run tests.

The source branch’s report and qualification artifacts were copied without modification: 134 `wp_e01*` files, the pre-BC source-snapshot roadmap (preserved as `wp_e01_source_snapshot_ROADMAP.md`), and its byte-preserved owner-provided roadmap. Hash comparison found 0 differences across all 134 files and the source-snapshot roadmap. The WP08/WP09 evidence referenced by the E01 audit was already present on the target. The integration progress ledger states the BC status as current and labels its earlier “not integrated” text as the original snapshot. The current `ROADMAP.md` is an integration overlay that states the BC decision and links to the preserved Owner roadmap and pre-BC snapshot; it prevents a standalone reader from mistaking the historical E01 row for the current integration status.

## Integrated files and identities

| File | SHA-256 | Scope |
|---|---|---|
| `src/solveur/materials/finite_strain_hencky.py` | `B318DAD553073F848B96528C61589AB2015C1EB1DD8FA52CB0BD52D13B09EAB2` | Experimental 3D Hencky kinematics, energy/stress response, and local force-only algebra. |
| `src/solveur/materials/finite_strain_hencky_tangent.py` | `31109BBBF2353F9BBD86B7A7B0E5FE776016FDD1638550848B58B8BD4AFEF135` | Experimental directional first-Piola material tangent. |
| `tests/unit/test_wp_e01m_hencky_material_point.py` | `CDD2651E9427C0E64284A75671D83D4F14CDD916A979759BE0422F44DDE84BFC` | Existing 41-case objectivity, energy, kinematics, and local-force suite. |
| `tests/unit/test_wp_e01q_hencky_tangent.py` | `A99BCC6EA32BFF3E2A669D2923380033F23E587AAB95F612AB4047F98B7D7B50` | Existing 35-case material-point tangent suite. |
| `tests/unit/conftest.py` | `8763EA8CC581C376A667EA8AE3DED5958A2DD52D47E3106694B3F2374A219A52` | Additive exact-hash registrations; refuses changed registered test modules before their collection/import and marks them `numerical_unit`. |
| `pyproject.toml` | `5E2D09BFD4995659E8BCC83BA0C8A3D5B87B688F20F5842DC894CA2DCCC59904` | Adds the `numerical_unit` marker description only. |
| `qualification/0_2_12/wp_e01_bb_global_scientific_audit_and_closure_readiness.md` | `C2E83B63128FA4A0CC985C516C75D7FCAEB54DFC252D4D47311AFAEF045CB88F` | Historical integration audit; unchanged. |
| `qualification/0_2_12/wp_e01_ba_bounded_slave_certificate_report.md` | `7EACE9F62649BD452B058AD318A2489682D22FE0EB1A9AEC739C9B05DF1F1FCA` | Historical scoped certificate report; unchanged. |
| `qualification/0_2_12/ROADMAP.md` | `24714841583EA6AF3F27F4A841C0B0A5DDC1496C85AEC46B4B2671E2E945C27B` | Current integration overlay; records `OPEN_WITH_BOUNDED_CERTIFICATES` and points to the preserved canonical roadmap and historical snapshot. |
| `qualification/0_2_12/wp_e01_source_snapshot_ROADMAP.md` | `48021A7773895C354806446AB89E317B968CFEE5F2618790F4487FBF11195A6D` | Byte-preserved pre-BC source snapshot; historical status intentionally retained. |

The Hencky modules are referenced only by each other and their tests. Static search found no import from `solveur.materials` factory/export files, element dispatch, public API, production assembly, or Newton modules. The public capability registry is unchanged.

## Verification performed

Static checks:

- `python -m py_compile` on both Hencky kernels, the scoped unit conftest, and both test modules: passed. This did not import or execute a scientific solve.
- Hash verification: both test modules match the frozen E01 identities; all copied E01 artifacts match the source worktree byte-for-byte.
- Safety review: registered test imports are NumPy, pytest, Decimal, and the isolated Hencky modules. No subprocess, network client, public solver, Gmsh initialization, native backend, or filesystem write is present in the two test modules.
- `git diff --check` passes for the changed implementation, configuration, ledger, and current BC report/roadmap overlay. Running it across the entire staged evidence archive reports trailing spaces already present in byte-preserved historical Markdown; those archived bytes were left unchanged to retain provenance hashes.

Targeted numerical unit tests on the integration branch, with BLAS/OpenMP threads set to one:

| Command scope | Result |
|---|---:|
| Hencky material-point module (41 cases) + directional-tangent module (35 cases) | **76 passed**, 0 failed, 1.67 s pytest time. |
| Selected WP08/WP09/WP10/D02 unit regressions | **54 passed**, 0 failed, 3 deselected, 6.27 s pytest time. |

The second command covered `test_wp08_contract.py`, WP09 independent-reference and closeout tests, WP10 TET4/HEX20 extension contracts and checkpoint/state helper contracts, and D02 roundoff/dynamic-stress checks. It explicitly deselected the two WP10 nodes that call `solve_model` and the D02 transient free-vibration node that calls `ModalNewmarkTransientSolver.solve`. No integration test that invokes `LinearStaticSolver` was run: the added material-point modules do not alter that route, and the Owner did not authorize a new FEM solve. Existing integration and solver APIs were checked statically instead.

The root test policy attempts its pre-existing optional Gmsh availability probe during collection; the selected test bodies neither initialize Gmsh nor invoke a native solver. No Docker, worker, public nonlinear solve, contact route, or physical FEM case was launched.

## Evidence-based maturity matrix

| Capability | Status for its exact evidence scope | Limit |
|---|---|---|
| StVK / total-Lagrangian | Existing WP08–WP10 bounded scope retained | No broader E01 claim; no duplicate source added. |
| Hencky material-point response | `VERIFIED_BOUNDED` (41/41 original cases also passed on this target) | Experimental, direct import only; no production material factory or global FEM route. |
| Hencky directional material tangent | `VERIFIED_BOUNDED` for the 35 tested material-point cases | The multi-step checks do not establish a robust convergence plateau; scientific gate remains unfrozen. |
| Hencky TET4/HEX8 local force algebra | Included within the 41-case local force-reference tests | Force-only local algebra; not shared-node assembly, constraints, reactions, or a production element tangent. |
| Hencky element tangent adapter | Not integrated | It depends on shared element classes and requires a separate target-specific compatibility review. |
| J2 direct element evidence | Historical D4R 65-pass bounded evidence preserved | Does not resolve global assembly/tangent evidence. |
| J2 global tangent | `UNRESOLVED` | Historical failures and weak-direction caveats remain; no threshold or formulation change. |
| GF4 TET4 Newton–Armijo slave subsystem | `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED` for source commit `524c15a0355a3033d92f7a723b27e1ca5752d3bd`, tree `9d0820780d1499a8488d295c740f8debd767eeee`, and image `sha256:026266d6794175608d476510353573b1784fbdae073f8cedf7873f84121ac01c` | Historical certificate only; not a verification of this integration HEAD or its runtime code. |
| Master assembly equilibrium | `NOT_VERIFIED` | Explicitly outside the approved slave certificate. |
| General scientific qualification | `NOT_ACQUIRED` | No overall formulation, release, or work-package qualification inferred. |

## Excluded changes and remaining risks

No E01 changes were imported into contact laws/assembly, nonlinear assembly or solver, Newton/Armijo, public API/export files, constraints, mesh validation, J2 production code, checkpoint formats, worker/supervisor/Docker profiles, global assembly, experimental Newton tests, or the Hencky element/global adapter. The target D02 and C02 worktrees were not modified. The E01 source worktree was not modified.

The residual P1 risks are the unresolved global J2 tangent, target-specific qualification of any future shared contact/Newton integration, and open WP11/WP12/WP13 decision gates. These do not change the selected experimental material-point scope. E01 remains open. No E01 result closes WP11, WP12, or WP13.

## Final repository identity

Starting integration HEAD/tree: `6b17ad538e90b5f63b61a66110a57ba6d479a63d` / `4d74385d6171ff139f07cbada7d4bf4a13b36b88`. The implementation is limited to the files listed above, the copied E01 evidence archive, this report, the current roadmap overlay and its byte-preserved source snapshot, and the BC status addition to the integration ledger. The final code commit and final repository HEAD/tree are recorded in the accompanying Git history and delivery summary. The E01 source branch remains at `3dc2f423e82ddb12fd82b8f23e764e757bad8278`; no `main` merge, tag, release, or publication was performed.
