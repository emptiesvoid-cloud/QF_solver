# 026-G14 Capability Coverage

Status: `PASS_WITH_LIMITATIONS`

This audit checks the public capability registry against the controlled
qualification and verification records. It covers registry completeness and
claim consistency; it does not promote a capability merely because code exists.

## Inventory

- Public capabilities in the registry: `33`
- Public element-analysis mappings: `44`
- Unregistered public capabilities: `0`
- Registry-only capabilities without implementation: `0`
- Duplicate or orphan public capability IDs: `0`
- Unbounded public maturity claims found: `0`

No capability is classified as `COVERED_FULL`. The current public evidence is
bounded by gate, element family, formulation, mesh, load, solver route and
observable.

## Coverage classes

The machine-readable classification is in
[`g14_capability_coverage.json`](../../../qualification/0_2_6/g14_capability_coverage.json).

| Class | Count | Meaning |
| --- | ---: | --- |
| `COVERED_FULL` | 0 | No unrestricted capability claim is approved. |
| `COVERED_BOUNDED` | 16 | The registry and evidence support a declared bounded scope. |
| `EXPERIMENTAL_ONLY` | 15 | The route is visible and tested or inventoried, but is not a qualified general capability. |
| `NOT_QUALIFIED` | 2 | The route is explicitly outside the qualified scope. |
| `DEFERRED` | 0 | Deferred subscopes are recorded separately rather than hiding a capability. |
| `DEAD_OR_STALE` | 0 | No active capability was removed by this audit. |

Important bounded boundaries remain explicit:

- G07 TL is Owner-qualified only for its tested TET4 domain; HEX8 complete
  history is not qualified and TET10/HEX20 remain research routes.
- G08 buckling is first-factor/first-mode and family-specific; HEX8 remains
  `MORE_EVIDENCE_REQUIRED` in the active Owner review.
- G10 finite-kinematic J2 and coupled nonlinear routes remain experimental,
  deferred or not qualified.
- G13 external evidence is representative and bounded; non-comparable and
  superseded records do not support active claims.

## Release cleanup

The audit does not close the release. Historical full-regression findings,
version/test reconciliation, historical documentation metadata, provenance
SHA review, stale-route/test inventory, environment-dependent audits and the
G15 Owner release review remain tracked in
[`g14_release_cleanup_items.json`](../../../qualification/0_2_6/g14_release_cleanup_items.json).

Full regression is `SKIPPED_BY_POLICY` for G14 and is reserved for the release
cleanup/final release sweep.
