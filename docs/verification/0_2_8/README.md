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

## WP04 MITC3 and MITC4 V&V

The WP04 frozen contract, executable replays and bounded decision delta are
recorded in [`WP04 MITC V&V`](wp04_mitc_vnv.md) and its
[`machine-readable evidence`](../../../qualification/0_2_8/wp04_mitc_vnv.json)
and [`WP04 maturity matrix`](../../../qualification/0_2_8/wp04_maturity_matrix.json).
The final decisions are recorded in the [`WP04 Owner gate`](wp04_owner_gate_final.md)
and [`machine-readable Owner record`](../../../qualification/0_2_8/wp04_owner_gate_final.json).
MITC3 static, MITC4 static, MITC4 Newmark and MITC4 harmonic are technical
`QUALIFIED_BOUNDED` within their bounded scopes. MITC3 modal/Newmark/harmonic
remain `EXPERIMENTAL` because no executable independent shell oracle is
present. MITC4 modal also remains `EXPERIMENTAL`: its deterministic replay
misses the frozen relative-residual gate, and that tolerance was not relaxed.
Across the 46 source combinations: 32 are `QUALIFIED_BOUNDED`, 13 are
`EXPERIMENTAL`, and `COMB-HEX8-linear_buckling` is the sole
`NOT_QUALIFIED` combination. WEDGE6 static is distinct and is qualified only
within the bounded scope recorded by WP05.

## Explicit boundaries

The eight nonlinear combination records remain `KEEP_EXPERIMENTAL`: this WP
does not expand nonlinear scope, finite-kinematic J2, friction, GPU or
distributed nonlinear execution. No mixed-mesh, PYRAMID5, HEX8R, SRI, B-bar or
hourglass production claim is created by WP01.

## WP05 WEDGE6 static V&V

WP05 closes the technical V&V campaign for the WEDGE6 linear-static candidate
identified by WP01 as `NEEDS_MAJOR_VNV`. The bounded technical decision,
predeclared contract, current replays, face-load checks, geometry failure
paths and the audited Code_Aster evidence are recorded in
[`WP05 WEDGE6 V&V`](wp05_wedge6_vnv.md), its
[`machine-readable evidence`](../../../qualification/0_2_8/wp05_wedge6_vnv.json)
and [`maturity delta`](../../../qualification/0_2_8/wp05_maturity_matrix.json).
The decision is `QUALIFIED_BOUNDED` for the exact static scope after the
separate Owner gate; the public maturity is now `QUALIFIED_BOUNDED` within
that scope, with the limitations recorded in the
[`WP05 Owner gate`](wp05_owner_gate_final.md). The machine-readable Owner record is
[`wp05_owner_gate_final.json`](../../../qualification/0_2_8/wp05_owner_gate_final.json).
Modal, Newmark and harmonic WEDGE6 routes are not promoted.

## WP06 HEX8 linear-buckling assessment

WP06 audits the sole `NOT_QUALIFIED` combination,
`COMB-HEX8-linear_buckling`, using the frozen
[`HEX8 buckling contract`](../../../qualification/0_2_8/wp06_hex8_buckling_contract.json)
and executable [`campaign evidence`](../../../qualification/0_2_8/wp06_hex8_buckling_vnv.json).
The technical decision remains `NOT_QUALIFIED`: the Euler factor and
three-level refinement gates failed in both declared boundary configurations,
the invalid-orientation case did not fail closed, current CalculiX execution
was unavailable, and the two complete replay digests differed. The passing
preload, `Kg`, eigen-residual and mode-shape sub-checks do not override those
failed closure gates.

The [`WP06 maturity delta`](../../../qualification/0_2_8/wp06_maturity_matrix.json)
records no promotion and reconciles the unchanged global state as 32
`QUALIFIED_BOUNDED`, 13 `EXPERIMENTAL` and one `NOT_QUALIFIED`, exactly
`COMB-HEX8-linear_buckling`. WEDGE6 static remains distinct. No 0.2.7 evidence
or numerical source was changed, and no Owner promotion gate is requested
while the technical decision is negative.

## WP06B HEX8 buckling root-cause remediation

WP06B starts from `be8fbd99d8a3d3b8e4ee3b8d867842389b063061` and reuses the
WP06 scope and tolerances without retuning. The
[`WP06B contract`](../../../qualification/0_2_8/wp06b_hex8_buckling_contract.json)
classifies the Euler/refinement failures as model/scope limitations, the
original invalid-orientation probe as a test-oracle problem, and the replay
tail variation as sparse-solver start nondeterminism. The minimal remediation
fixes only the latter two test/replay issues: a fixed ARPACK start vector is
used, and a true mirrored HEX8 connectivity is tested.

After remediation, invalid geometry, robustness and two complete deterministic
replays pass. The Euler factor and mesh-refinement gates still fail in the
unchanged scope, and the current CalculiX oracle remains unavailable. The
[`WP06B evidence`](../../../qualification/0_2_8/wp06b_hex8_buckling_vnv.json)
and [`WP06B maturity delta`](../../../qualification/0_2_8/wp06b_maturity_matrix.json)
therefore retain `COMB-HEX8-linear_buckling` as `NOT_QUALIFIED`; no public
promotion or Owner gate is applied. No 0.2.7 evidence is changed and WP07 is
not started.

## WP07 mixed TET4/WEDGE6/HEX8 linear static

WP07 audits the existing family-generic architecture for one conforming
mixed-solid `linear_static` workflow. The frozen
[`WP07 contract`](../../../qualification/0_2_8/wp07_mixed_static_contract.json),
executable [`WP07 evidence`](../../../qualification/0_2_8/wp07_mixed_static_vnv.json)
and [`WP07 candidate matrix`](../../../qualification/0_2_8/wp07_mixed_static_matrix.json)
record the subsystem audit, affine/interface/load gates, Gmsh path, explicit
failure contract and two deterministic replays.

All declared technical gates pass, producing
`QUALIFIED_BOUNDED_CANDIDATE` for the exact conforming TET4/WEDGE6/HEX8
linear-static scope. The result is still pending a separate Owner gate: WP07
does not apply a public maturity relabel, does not qualify dynamic or other
analysis routes, and does not claim an external solver correlation. No 0.2.7
evidence or prior WP01-WP06B record is changed.
