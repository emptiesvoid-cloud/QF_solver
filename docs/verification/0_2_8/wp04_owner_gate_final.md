---
doc_id: DOC-028-WP04-OWNER-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP04 — final Owner gate

This Owner gate audits commit
`0496467120997b0c23f6817eb2f6e76eeda698d8` and applies only the WP04
decisions. The machine-readable decision record is
[`wp04_owner_gate_final.json`](../../../qualification/0_2_8/wp04_owner_gate_final.json).
No numerical source, tolerance or 0.2.7 evidence is changed.

## Decisions

| Combination | Decision | Resulting state |
| --- | --- | --- |
| MITC3 linear static | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` |
| MITC3 modal | `REJECT` | `EXPERIMENTAL` |
| MITC3 Newmark | `REJECT` | `EXPERIMENTAL` |
| MITC3 harmonic | `REJECT` | `EXPERIMENTAL` |
| MITC4 linear static | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` |
| MITC4 modal | `REJECT` | `EXPERIMENTAL` |
| MITC4 Newmark | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` |
| MITC4 harmonic | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` |

The four approvals remain bounded by the frozen WP04 scopes, oracles,
tolerances, convergence cases, invariants, dynamic amplitude/phase checks,
energy checks and two deterministic replays documented in
[`WP04 MITC V&V`](wp04_mitc_vnv.md). MITC4 modal is explicitly rejected for
promotion because its replay residual is `2.6317020430528298e-08`, above the
predeclared `1e-08` gate. MITC3 dynamic routes are rejected for promotion
because the required executable independent shell oracles are absent.

## Registry reconciliation

The reconciliation reads the 46 `record_kind=combination` records directly
from [`capability_registry_v2.json`](../../../qualification/0_2_7/capability_registry_v2.json),
then applies the finalized WP03 and WP04 deltas:

| State | Source 0.2.7 | Final 0.2.8 |
| --- | ---: | ---: |
| `QUALIFIED_BOUNDED` | 20 | 31 |
| `EXPERIMENTAL` | 25 | 14 |
| `NOT_QUALIFIED` | 1 | 1 |
| **Total** | **46** | **46** |

The sole `NOT_QUALIFIED` combination is
`COMB-HEX8-linear_buckling`. `COMB-WEDGE6-linear_static` remains
`EXPERIMENTAL`; it is not converted into, or confused with, the HEX8
buckling status.

## Integrity result

- claims remain bounded to the recorded scopes;
- no opportunistic numerical-core change was found;
- no tolerance was retuned;
- 0.2.7 evidence remains untouched;
- the owner record stores SHA-256 digests for the WP04 evidence and document.

WP05 is not started by this gate.
