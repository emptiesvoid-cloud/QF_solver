---
doc_id: DOC-028-WP05-OWNER-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP05 — final Owner gate

This Owner gate audits commit
`e9d83047b310cd85380551d8096d898090a7cba9` and applies only the WP05
decision. The machine-readable record is
[`wp05_owner_gate_final.json`](../../../qualification/0_2_8/wp05_owner_gate_final.json).
No numerical source, tolerance or 0.2.7 evidence is changed.

## Decision

| Combination | Owner decision | Resulting state |
| --- | --- | --- |
| WEDGE6 linear static | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` |
| WEDGE6 modal | Not in this gate | unchanged |
| WEDGE6 Newmark | Not in this gate | unchanged |
| WEDGE6 harmonic | Not in this gate | unchanged |

The evidence record is [`WP05 WEDGE6 V&V`](wp05_wedge6_vnv.md), with the
pre-declared contract, machine-readable results and maturity delta linked from
that page. The approved scope is Gmsh Prism 6 WEDGE6, homogeneous isotropic
small-strain linear elasticity, linear static analysis, the declared nodal,
body/gravity, TRI3-pressure, QUAD4-pressure and surface-traction contracts,
conforming prism assemblies, declared valid distortions and explicit failure
of invalid geometry. It includes the recorded displacement, Gauss-point
strain/stress, energy, reactions and global equilibrium checks.

## External-oracle limitation

The external result is `PASS_WITH_LIMITATIONS`, not a universal correlation
claim. WP05 audits the controlled 0.2.7 Code_Aster 18.1 PENTA6 artifact by
reference; it does not present that artifact as a new WP05 Code_Aster run. The
artifact contains 12 comparable primary-observable cases and all 12 pass, with
the current numerical source unchanged since the external source commit.

CalculiX C3D6 remains `NOT_COMPARABLE` because its integration convention does
not match the QF `TRI3_X_GAUSS2` contract. No external stress qualification is
claimed without an equivalent sampling contract. This limitation is
compatible with the bounded static promotion because the public claim is
restricted to the recorded QF checks and Code_Aster primary observables.

## Additional limitations

- Modal, Newmark and harmonic WEDGE6 routes are not promoted.
- Nonlinear, J2, Total-Lagrangian, contact, WEDGE15, mixed-mesh and unbounded
  arbitrary-distortion claims remain excluded.
- Automatic orientation repair is not claimed; coincident, nonfinite,
  inverted, wrong-order and negative-Jacobian geometry must fail explicitly.
- The external correlation is limited to the declared tolerance classes and
  primary observables; it does not qualify arbitrary stress sampling.

## Registry reconciliation

The 46 `record_kind=combination` records are counted directly from
[`capability_registry_v2.json`](../../../qualification/0_2_7/capability_registry_v2.json).
The prior WP03 and WP04 decisions are preserved, then the single WP05
promotion is applied:

| State | Source 0.2.7 | After WP05 Owner gate |
| --- | ---: | ---: |
| `QUALIFIED_BOUNDED` | 20 | 32 |
| `EXPERIMENTAL` | 25 | 13 |
| `NOT_QUALIFIED` | 1 | 1 |
| **Total** | **46** | **46** |

The sole `NOT_QUALIFIED` combination remains
`COMB-HEX8-linear_buckling`. `COMB-WEDGE6-linear_static` is distinct from
that record and is now `QUALIFIED_BOUNDED` only within the scope above.

## Integrity result

- all WP05 gates and two deterministic replay lots pass;
- the external limitation is retained rather than hidden or generalized;
- no opportunistic numerical-core or tolerance change was found;
- no 0.2.7 evidence was rewritten;
- no WP06 work is started by this gate.
