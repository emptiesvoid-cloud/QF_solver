---
title: "WP10 HEX8 selective reduced integration research gate"
status: "EXPERIMENTAL_BOUNDED_CANDIDATE"
---

---
doc_id: DOC-028-WP10-VNV-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP10 HEX8 selective reduced integration research gate

WP10 evaluates a separate research-only SRI kernel. The frozen
[formulation](wp10_hex8_sri_formulation.md) and
[contract](../../../qualification/0_2_8/wp10_hex8_sri_contract.json) keep the
qualified HEX8 implementation unchanged.

The candidate integrates the deviatoric contribution at the standard eight
Gauss points and the volumetric contribution at the element centre. On the
declared structured cantilever campaign, the fine-level relative displacement
error reduction is `76.0 %` for `ν=0.30` and `61.9 %` for `ν=0.4999`. The
SRI error decreases over levels `4/8/16` in both cases. Symmetry, six rigid
body modes, rank, affine strain, energy and invalid-orientation checks pass;
two complete campaign replays are deterministic.

## Decision and limitations

The technical decision is `EXPERIMENTAL_BOUNDED_CANDIDATE`. This is not a
public capability or maturity promotion. The affine strain and energy checks
pass, but the centre-only volumetric term changes the affine nodal force
action (`0.87495` relative diagnostic). Therefore no general patch-force,
production accuracy, external industrial correlation or universal locking
claim is made. An independent Owner gate is required before any public
exposure or maturity decision.

The scope is limited to isotropic small-strain linear-static HEX8 SRI on the
executed structured bending and nearly-incompressible cantilever cases. The
variant is absent from the public element registry and compatibility
descriptor. HEX8R, hourglass control, nonlinear, modal, Newmark, harmonic,
buckling, mixed-large and PYRAMID5 maturation remain excluded.
