---
doc_id: DOC-028-WP13-02C2-HARMONIC-HARNESS-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP13-02C2 harmonic harness/evidence correction

WP13-02C2 is a harness-only micro-check. It does not rerun the frozen
WP13-02C harmonic campaign and does not modify its contract, gates, solver
formulation, result manifest or archive.

The corrected record is
[manifest.json](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02c2_harmonic_harness/manifest.json)
with its machine-readable micro-check arrays in
[wp13_02c2_harness_arrays.npz](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02c2_harmonic_harness/wp13_02c2_harness_arrays.npz).
The evidence schema is
[wp13_02c_harmonic_evidence.schema.json](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02c_harmonic_evidence.schema.json).

## Corrections covered

The harness gathers interface displacement states and dynamic forces from
independent family-local element incidences; it does not assign both sides
from the same global slice. The interface energy denominator records
the product of the Ffree L2 norm and the response L2 norm, including both
norms and the numerator.

The replay comparator covers complete complex displacement, reaction and
residual arrays, amplitudes, phases, interface states, force/work metrics and
status. All nine rejection cases are executed and require exact exception
type, message pattern and traceback path matches. The manifest freezes the
evaluator, schema, contract, repository and environment digests before any
future C3 numerical campaign.

The modal coordinate is archived as q = phi^H M x together with amplitude,
phase, source and normalization. It is diagnostic evidence only; no
first-mode-dominated claim is created.

The original C campaign remains explicitly nonconforming under the corrected
evidence schema and is preserved unchanged. No 0.2.7, Newmark, numerical
kernel, formulation, gate or maturity record was changed.
