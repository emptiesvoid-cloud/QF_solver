---
doc_id: DOC-028-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP01 maturity baseline

This record audits the 46 active combination records from the public 0.2.7
capability registry at the frozen baseline
`9a0d2ab8e8fc3509f0f7ea53bb93db0bd7d99ca5`. It is a planning disposition,
not a qualification-state change. The 0.2.7 registry and all its historical
evidence remain unchanged.

The machine-readable source is
[`qualification/0_2_8/wp01_maturity_matrix.json`](../../../qualification/0_2_8/wp01_maturity_matrix.json).
It preserves the exact source-registry digest, every combination identifier,
the required next proof, test, oracle, tolerance policy, exit gate and risk.

## Disposition policy

- `KEEP_QUALIFIED`: retain the current bounded 0.2.7 state; WP01 adds no claim.
- `PROMOTABLE_WITH_EXISTING_EVIDENCE`: reserved for a record with complete
  evidence and an explicit existing Owner decision. No record meets that bar.
- `NEEDS_MINOR_VNV`: an existing bounded implementation and evidence basis
  require a frozen replay, predeclared tolerance and Owner decision.
- `NEEDS_MAJOR_VNV`: a missing comparable oracle, route-level evidence or
  scope expansion prevents a small administrative closure.
- `KEEP_EXPERIMENTAL`: a deliberate technical boundary remains out of scope.
- `NOT_QUALIFIED_TO_CLOSE`: the active record has an explicit unresolved
  qualification gap.

Every future numerical tolerance must name its observable, numerical value and
provenance before a run. Case-dependent values are allowed only when justified
by mesh, formulation and oracle. Retuning after a result is forbidden.

## Matrix summary

| Disposition | Count |
| --- | ---: |
| `KEEP_QUALIFIED` | 20 |
| `PROMOTABLE_WITH_EXISTING_EVIDENCE` | 0 |
| `NEEDS_MINOR_VNV` | 9 |
| `NEEDS_MAJOR_VNV` | 8 |
| `KEEP_EXPERIMENTAL` | 8 |
| `NOT_QUALIFIED_TO_CLOSE` | 1 |

## Combination dispositions

| Family | Routes and WP01 disposition |
| --- | --- |
| BEAM2 | static, modal: `NEEDS_MINOR_VNV`; Newmark, harmonic: `NEEDS_MAJOR_VNV`. |
| DISCRETE | static, modal: `NEEDS_MINOR_VNV`; Newmark, harmonic: `NEEDS_MAJOR_VNV`. |
| MITC3 | static: `NEEDS_MINOR_VNV`; modal, Newmark, harmonic: `NEEDS_MAJOR_VNV`. |
| MITC4 | static, modal, Newmark, harmonic: `NEEDS_MINOR_VNV`. |
| TET4 | static, modal, Newmark, harmonic, linear buckling: `KEEP_QUALIFIED`; nonlinear load control and geometric nonlinear static: `KEEP_EXPERIMENTAL`. |
| TET10 | static, modal, Newmark, harmonic, linear buckling: `KEEP_QUALIFIED`; nonlinear load control and geometric nonlinear static: `KEEP_EXPERIMENTAL`. |
| HEX8 | static, modal, Newmark, harmonic: `KEEP_QUALIFIED`; linear buckling: `NOT_QUALIFIED_TO_CLOSE`; nonlinear load control and geometric nonlinear static: `KEEP_EXPERIMENTAL`. |
| HEX20 | static, modal, Newmark, harmonic, linear buckling: `KEEP_QUALIFIED`; nonlinear load control and geometric nonlinear static: `KEEP_EXPERIMENTAL`. |
| WEDGE6 | modal: `KEEP_QUALIFIED`; static: `NEEDS_MAJOR_VNV`. |

## Evidence findings and priority candidates

The source registry confirms that each active record has a declared
implementation path, tests and recorded evidence references. It also records
where those references are inherited from earlier releases rather than a new
0.2.8 decision. That distinction prevents an administrative promotion.

1. **BEAM2 and DISCRETE static/modal** have existing element, workflow and
   external/analytical evidence routes. Their remaining closure is a frozen
   0.2.8 replay manifest, predeclared observables/tolerances and an Owner
   decision. Their transient and harmonic routes need a comparable history or
   frequency-response oracle and remain major work.
2. **MITC4** has the strongest shell basis: existing static, modal, transient
   and harmonic V&V paths need an explicit frozen replay and Owner decision,
   not a new formulation. **MITC3 static** has a similar narrow path.
3. **MITC3 modal, transient and harmonic** lack the comparable independent
   decks stated by the inherited record, so they are major V&V rather than a
   maturity relabel.
4. **WEDGE6 static** remains major: its 0.2.7 Owner decision explicitly kept
   it experimental. The existing Code_Aster PENTA6 affine same-mesh policy is
   reusable only within its declared `1e-6` scope; refinement and distortion
   need separately approved pre-execution tolerances.
5. **HEX8 buckling** remains not qualified. The prior diagnostic evidence is
   not a closure: it needs a three-level refinement, comparable independent
   oracle, replayed eigenpair evidence and Owner decision.

The detailed candidate records in the machine-readable matrix name the exact
test file to add, oracle/reference, tolerance policy, exit gate and risk. No
candidate changes public maturity until its stated gate passes.

## WP03 BEAM2 and DISCRETE V&V

The completed technical campaign for BEAM2 and DISCRETE static/modal routes is
documented in [`WP03 V&V`](wp03_beam2_discrete_vnv.md). It records the frozen
analytical oracles, tolerances, invariants, two replays and bounded decisions.
The four dynamic routes were intentionally not decided by that WP03A record;
their separate bounded analytical campaign is documented in
[`WP03B dynamic V&V`](wp03b_dynamic_vnv.md). WP03B preserves every WP03A
static/modal decision. The resulting bounded maturity decisions are recorded
by the [`final WP03 Owner gate`](wp03_owner_gate_final.md): seven routes are
`QUALIFIED_BOUNDED`; DISCRETE Newmark remains `EXPERIMENTAL`.

## Explicit boundaries

The eight nonlinear combination records remain `KEEP_EXPERIMENTAL`: this WP
does not expand nonlinear scope, finite-kinematic J2, friction, GPU or
distributed nonlinear execution. No mixed-mesh, PYRAMID5, HEX8R, SRI, B-bar or
hourglass production claim is created by WP01.
