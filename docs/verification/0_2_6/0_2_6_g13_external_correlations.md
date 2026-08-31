# 026-G13 External Correlations

Status: **PASS_WITH_LIMITATIONS**. This work package consolidates the external and independent
evidence already recorded for G04-G12. It does not change any closed gate and it
does not promote a research route. No new external case was executed in this
run: the local environment has no `Code_Aster`, `CalculiX`, `ccx` or `as_run`
executable available.

## Scope and decision rule

The machine-readable sources are:

- `qualification/0_2_6/g13_external_evidence_registry.json`
- `qualification/0_2_6/g13_external_coverage_matrix.json`
- `qualification/0_2_6/g13_missing_evidence_matrix.json`

The registry uses these classifications:

- `EXTERNAL_FULL`: all declared metrics for the selected benchmark are covered
  by a comparable independent run;
- `EXTERNAL_BOUNDED`: useful independent evidence exists, but the declared
  benchmark, formulation, mesh, observable or path is bounded;
- `INTERNAL_ONLY`: no external oracle is required for the current claim;
- `NOT_COMPARABLE`: an external result exists or was considered, but the
  formulation or observable mapping is not equivalent;
- `SUPERSEDED`: retained historical evidence excluded from active metrics;
- `MISSING`: a potentially useful comparable result was not executed or is not
  available.

`EXTERNAL_FULL` is never a general physical-validation claim. A correlation is
only consumed for the family, route, mesh, load history and observable recorded
in its row.

## Consolidated inventory

| Gate | Capability / family | Reference | Classification | Active result | Limitation |
| --- | --- | --- | --- | --- | --- |
| G04 | linear static, applicable cases | analytical/invariant | EXTERNAL_BOUNDED | 20 configured analytical checks pass; configured error 0 at `1e-10` | closed-form preconditions do not cover every constrained case |
| G04 | linear static | Code_Aster | MISSING | no run | executable unavailable; no external claim in G04 closeout |
| G04 | linear static | CalculiX | MISSING | no run | executable unavailable; no external claim in G04 closeout |
| G05 | DISCRETE modal/Newmark/harmonic | Code_Aster 18.1.0 | EXTERNAL_FULL | selected SDOF static/frequency/history checks pass | selected SDOF only |
| G05 | BEAM2 modal | Code_Aster 18.1.0 | EXTERNAL_FULL | modes 1-6; maximum recorded error `2.6486e-4` vs `1%` | selected beam benchmark only |
| G05 | BEAM2 Newmark/harmonic | Code_Aster 18.1.0 | EXTERNAL_FULL | maximum recorded error `4.7473e-13` vs `1e-7` | selected response histories only |
| G05 | TET4 modal/Newmark/harmonic | Code_Aster 18.1.0 | EXTERNAL_FULL | same-mesh and selected refinement checks pass | other registered families lack comparable decks |
| G05 | TET10/HEX8/HEX20/MITC3/MITC4 | Code_Aster | MISSING | not executed | no current same-SHA compatible deck |
| G06 | small-strain J2, four solid families | Code_Aster 18.1.0 | EXTERNAL_FULL | 64 checks; max relative errors are recorded in source evidence | small-strain J2 only; TET10 uses the declared external quadrature convention |
| G08 | first linearized buckling factor/mode | CalculiX 2.20 | EXTERNAL_BOUNDED | TET4/TET10/HEX8 rows pass; original HEX20 row blocked | first-mode bounded screen |
| G08 | HEX20 first mode | CalculiX 2.20 | EXTERNAL_BOUNDED | one/two/three-cell rescue passes the existing `10%` screen | diagnostic MAC has no Owner threshold |
| G08 | solid eigen-buckling | Code_Aster | NOT_COMPARABLE | excluded | no equivalent modelisation |
| G08 | historical positive-load Euler screen | analytical | SUPERSEDED | excluded | invalid load definition for the active compression benchmark |
| G09 | unilateral normal contact, TET4 | Code_Aster 18.1.0 | EXTERNAL_BOUNDED | active branch checks pass; transition warning retained | exact unilateral constraint is not the QF penalty law |
| G09 | elastic pre-contact TET4 | CalculiX 2.20 | EXTERNAL_BOUNDED | pre-contact tie-breaker passes | does not exercise contact detection or penalty enforcement |
| G10 | arc-length shallow-arch research route | Code_Aster 18.1.0 | EXTERNAL_BOUNDED | 75 common points and one turning point | research evidence; G07 is unchanged |
| G10 | TL elasticity TET4 | Code_Aster 18.1.0 | EXTERNAL_BOUNDED | bounded stress/column comparisons pass | research evidence; G07 is unchanged |
| G10 | TL elasticity HEX8 | Code_Aster 18.1.0 | EXTERNAL_BOUNDED | matched displacement/reaction and residual pass | full QF path/internal measures incomplete |

Full provenance, commands, artifact paths and digests remain in each source
artifact referenced by the registry. The source SHA in each row is the SHA of
the numerical execution, not the later evidence-aggregation commit.

## Gap assessment

### Blocking for a future promotion

- finite-kinematic J2: no formulation-compatible independent external evidence;
- J2 plus geometry: no independent coupled correlation;
- geometry plus contact: the available external models are not apples-to-apples;
- triple coupling: no independent external correlation.

These were candidate blockers for future promotion, but the Owner review
reclassified them as acceptable missing evidence for the current release because
those routes are not presented as qualified. They remain hard blockers for any
future promotion of the respective research claims.

### Valuable but non-blocking for current bounded gates

- G04 Code_Aster/CalculiX comparison;
- G05 external decks for TET10, HEX8, HEX20, MITC3 and MITC4;
- broader G08/G09 family and law comparisons.

The current gates explicitly retain bounded scope and do not claim exhaustive
external coverage. These gaps are therefore deferred rather than silently
treated as PASS.

### Low value or deferred

G12 has an internal, hardware-specific bounded performance characterization;
there is no defined external scaling oracle. No external performance campaign
was selected for G13.

## Owner closeout

The Owner audited all 18 records and accepted the following classification:

- `OWNER_EXTERNAL_FULL`: the four selected G05 Code_Aster studies and the
  64-check G06 small-strain J2 correlation;
- `OWNER_EXTERNAL_BOUNDED`: the G04 analytical evidence, G08 CalculiX
  evidence, G09 unilateral/pre-contact evidence and G10 research-route
  evidence;
- `OWNER_NOT_COMPARABLE`: the G08 Code_Aster solid buckling route;
- `OWNER_MISSING_ACCEPTED`: unavailable G04 tools, missing G05 high-order
  decks, and external evidence for routes that are already unqualified or
  experimental;
- `OWNER_BLOCKING`: none for a currently public qualified claim.

The historical positive-load Euler screen remains `SUPERSEDED` and is excluded
from active metrics. No `MISSING`, `NOT_COMPARABLE` or `SUPERSEDED` record is
used as a qualification PASS. On that basis, `026-G13` is closed as
`PASS_WITH_LIMITATIONS`; the closeout record is
`qualification/0_2_6/g13_owner_closeout.json`.

## Active claim boundary

The following active statuses are unchanged:

- G04, G05, G06, G08, G09, G10, G11 and G12 retain their existing
  `PASS_WITH_LIMITATIONS` decisions;
- G07 remains `NOT_STARTED` and is not promoted by G13;
- finite-kinematic J2 and coupled nonlinear routes remain experimental or
  research-only;
- CalculiX remains a supporting correlation route when comparable, not a
  mandatory universal oracle;
- no `MISSING`, `NOT_COMPARABLE` or `SUPERSEDED` row contributes as a PASS.

## Reproduction and next use

The registry can be consumed by G14 without rerunning any numerical campaign.
The next external execution should select only a gap with a controlled
executable, comparable formulation and predeclared metrics. If those
preconditions are absent, the correct result remains `MISSING` or
`NOT_COMPARABLE`, never a synthetic pass.
