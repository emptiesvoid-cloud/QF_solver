---
doc_id: DOC-027-007
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 External Oracle Preflight

## Purpose

This plan determines whether an independent C3D6/PENTA6 comparison is
available before WEDGE6 implementation. It is a preflight, not evidence of a
WEDGE6 result.

## Required comparability record

For each candidate tool and deck, record:

- solver name, version, container/image digest or executable fingerprint;
- element name, node order, local axes, shape-function convention and
  integration rule;
- geometry, units, material, thickness/section and mesh hash;
- BCs, load application, load sign and reference/load-factor convention;
- observable definition and sampling location;
- stress/strain measure and any conversion used;
- command, input deck, output files, exit status and artifact digests.

The comparison classification is one of `PASS_EXTERNAL`,
`PASS_WITH_LIMITATIONS`, `NOT_FORMULATION_COMPATIBLE`,
`SKIPPED_UNAVAILABLE` or `FAIL_EXTERNAL`. `SKIPPED_UNAVAILABLE` and
`NOT_FORMULATION_COMPATIBLE` are never PASS.

## C3D6 / PENTA6 preflight

| Check | Required result before WP07 GO |
| --- | --- |
| Availability | executable/container and version are reproducible, or explicit unavailable record |
| Topology | C3D6/PENTA6 node order and face map are controlled |
| Kinematics | displacement, strain and stress measures are equivalent or transformable |
| Integration | quadrature and sampling are documented |
| Loads/faces | nodal, face and reaction conventions are identical |
| Mesh | identical mesh or a controlled physical-equivalence map exists |
| Outputs | displacement, reaction and selected internal observable are extractable |
| Replay | same deck and command reproduce the recorded output |

If the tool is unavailable, retain the preflight as `SKIPPED_UNAVAILABLE` and
keep external correlation as a limitation. Do not install a heavyweight stack
solely to turn a planned row green.

## Planned observables

The first WEDGE6 external study should prefer displacement, total reaction and
load-displacement curves. Stress recovery is included only where the external
sampling and measure are comparable. Pointwise stress values at a singularity
are not primary evidence.

## Stop conditions

Stop the comparison and request Owner review if the kinematics, load path,
observable or node map is ambiguous; if an external failure cannot be
reproduced; or if a new tolerance would be needed after seeing the results.
