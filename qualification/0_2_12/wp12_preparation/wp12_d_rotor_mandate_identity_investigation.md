# WP12-D rotor mandate identity investigation

**Status:** `ROTOR_MANDATE_METADATA_INVESTIGATED`

**Controller reviewed:** `74fc463a8ff91a07620e4c63c542a6c29e9fd3fa`

**Prospective fix:** `CONTROLLER_FIX_READY_FOR_REVIEW` when its branch checks pass
**Scientific execution in this change:** none

## Finding

The policy has two distinct values: the top-level legacy `mandate_id` is
`DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v1`, while
`worktrees.rotor.development_mandate_id` is
`DEVELOPMENT_AUTONOMOUS-WP12-ROTOR-2026-10-26-v1`.

The WP12 manifest preparation and validation path did not include or check a
mandate identifier. In `run_pytest`, only D01 initialized `ledger_context`;
the WP12 branch validated its manifest but left that value unset. The shared
reservation code consequently fell back to the top-level policy mandate when
writing the ledger key and the run receipt. This is the confirmed replacement
point: **runner execution path → fallback used for ledger and receipt**. The
policy and rotor scope themselves contain the correct rotor mandate.

## Scope and impact

The reviewed run records identify `worktree_id=rotor`, the eight exact
registered nodeids, the approved source identity, controller identity,
registration fingerprints and selection records. Runtime budgets came from
the rotor entry and match its envelope: 300 seconds, 4096 MiB sampled RSS, 16
processes, 32 MiB per output stream, 64 MiB total output, 512 MiB temporary
space and 256 MiB archive size. All eight ledger entries are `PASS`, one per
nodeid, under the rotor evidence root. There is no observed evidence that the
runner selected another scope, source, budget, evidence root or ledger file.

The defect is therefore a provenance and accounting-namespace defect, not
evidence of a different scientific test being selected. It remains material:
the manifest did not bind the declared rotor mandate, and the receipt/ledger
name the generic mandate. The ledger's scope-specific file kept rotor records
separate from other scopes, but its mandate header and attempt keys are not the
ones declared by the rotor policy. Because all eight one-attempt slots and the
eight-attempt cap were consumed, the records show the full rotor allowance;
they must not be rerun. A reviewer/Owner must decide whether the runs are
receivable as evidence produced under the intended rotor mandate. This fix
does not retroactively amend or relabel them.

Changing the prospective mandate while reusing a ledger whose header names the
generic mandate is deliberately fail-closed: the existing ledger is rejected
as an identity/schema mismatch before a new node-ledger reservation. Do not
create a fresh ledger to bypass consumed attempts. Any future rotor work needs
a separately reviewed mandate/ledger decision and fresh Owner authorization.

## Historical evidence inventory (read-only)

Ledger SHA-256: `70d78c4d98916a42d8be5e25af1afb41d34882742272041a75e3a8cd7ee33219`.
Each receipt is the corresponding `run.json` in the recorded rotor run
directory. No historical file was edited.

| Owner authorization / case | Exact nodeid | Manifest SHA-256 | `run.json` SHA-256 |
|---|---|---|---|
| `ROTOR-PRF-20261026-GYRO01` | `tests/unit/test_rotating_modal_cases.py::test_gyro01_zero_speed_matches_modal_frequencies_multiplicity_and_subspaces` | `d9236834e600f8a0e73405f7a2025c9a329d252126b994292e497cc8340f3021` | `092e9022e4f73328466223ce3389675a841dce8e57c136585be3988c09f39cc4` |
| `ROTOR-PRF-20261026-DISK-MATRIX` | `tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_unit_speed_gyro_blocks_match_contract` | `8341b8f2d4dda06634b233bd75dfceb22f2b099a89ba7544b7568726ea9d2c22` | `e64bbf3da22bfd051fc271726ce7a2842d711932d6200b0ef4255a4b8c9ad78a` |
| `ROTOR-PRF-20261026-DISK-ASSEMBLY` | `tests/unit/test_rotating_disk_gyro.py::test_assembled_gyro_uses_same_global_dof_map_and_has_zero_quadratic_work` | `c075304ba73bb2a3e333bd48f76c98cd16779aaf52df727b2d09d9126a8a37be` | `f2f8dad399634523d87b7d2f8a483e2aadc2f5fc0cd21a234f9aece6c9920849` |
| `ROTOR-PRF-20261026-QEP-P100` | `tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[100.0]` | `9cb2af11067b89ff0fe16dfaa8038ad174d1153d980eda7d9eba7d8366e89c6f` | `004ba3db0a8af45e4ba986a2bbd08ed1a52bab92e33286f4a4afc37067a965ce` |
| `ROTOR-PRF-20261026-QEP-N100` | `tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[-100.0]` | `a51262c595d97de563478625b2ddbada6b69dda99f241f3d48be84d544375f6f` | `277aa4bb6cf3ee053aa44d9300a53c6c1ddb95c6fed5034236155a1b6fabd9ad` |
| `ROTOR-PRF-20261026-MAC-AMBIG` | `tests/unit/test_modal_tracking.py::test_competing_source_modes_make_the_global_assignment_ambiguous` | `1f68be769c022f01075afff650b7d3b047b2cf93f87518506ca69eeca4b2dc65` | `ea97cef8f649117c804f3c6f675915efc9e4d1ee4a9288a0cae1c15505c7139f` |
| `ROTOR-PRF-20261026-CAMPBELL-SWEEP` | `tests/unit/test_campbell.py::test_campbell_sweep_reuses_one_model_and_serializes_complex_source_results` | `08dfb4ab26fb0a797940004464121e58863e86bd3b294d0f82f0649457e64cbc` | `6546a4e2dce36ec2d0d16863ca5e1f318514f5c8494a27a4528e4749e45f4c15` |
| `ROTOR-PRF-20261026-CAMPBELL-ROUTER` | `tests/unit/test_campbell.py::test_campbell_is_exposed_through_model_schema_and_analysis_router` | `1913757b15f2f4a0aaa36bd04ca56a9454ef47fa8670e741b22a604bd0562440` | `ca335b3046553b2260239743696c30e3b5b4d0b1fa8fde27788791fe7456e0cc` |

The ledger hash, all eight manifest hashes and all eight receipt hashes were
recomputed from the existing evidence tree during this read-only review.

## Prospective contract

The controller change adds the scope's `development_mandate_id` to every new
WP12 prepared execution manifest, requires an exact match during validation,
and returns that value in the manifest receipt. After the Owner-authorized
manifest validates, `run_pytest` obtains the scope's ledger context for every
WP12 scope. The separate D01 predecessor-ledger path remains unchanged.
Budgets, allowlists, scope identity, selection, and scientific sources are
unchanged. A pre-existing generic-mandate ledger is refused rather than
silently migrated, rewritten or treated as unused.

Synthetic tests exercise valid and mismatched manifests for every registered
WP12 scope, verify scope-mandate selection in the runner before attempt
creation, and verify refusal without mutation when a legacy generic ledger is
present. They stop before attempt reservation and never launch pytest or import
the solver.
