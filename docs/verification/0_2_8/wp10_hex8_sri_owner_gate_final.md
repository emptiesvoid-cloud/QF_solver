---
title: "WP10 HEX8-SRI Owner gate"
status: "APPROVE_EXPERIMENTAL_BOUNDED"
---

# WP10 HEX8-SRI Owner gate

The Owner decision is `APPROVE_EXPERIMENTAL_BOUNDED` for the separate
HEX8-SRI research capability. The machine-readable decision is recorded in
[`wp10_hex8_sri_owner_gate_final.json`](../../../qualification/0_2_8/wp10_hex8_sri_owner_gate_final.json).

The decision accepts the isotropic small-strain linear-static formulation with
deviatoric `2×2×2` and volumetric `1×1×1` integration. The executed fine-level
locking-error reductions are `76.0 %` at `ν=0.30` and `61.9 %` at `ν=0.4999`.
Rank, rigid-body, symmetry, stability, bounded distortion, convergence and
two deterministic replays pass. The Timoshenko oracle is sufficient for this
experimental bounded scope; no external correlation is claimed.

The centre-only volumetric term changes the affine nodal-force action. This is
an explicit limitation: no general patch-force, production, universal
incompressibility, arbitrary-distortion or universal locking claim is
approved. Nonlinear, dynamic, contact, HEX8R and hourglass-control routes are
excluded.

HEX8-SRI remains separate from the standard HEX8 implementation and from the
46 element-analysis combinations. No 0.2.7 evidence, WP07–WP09 claim or
standard HEX8 source is changed. Further maturity promotion or scope
expansion requires a new Owner gate.
