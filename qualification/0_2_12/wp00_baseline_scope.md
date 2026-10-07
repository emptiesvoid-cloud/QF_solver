# QF Solver 0.2.12 — WP00 baseline and scope freeze

Status: `WP00_FROZEN`

Record: `wp00_baseline_scope_contract.json`

Capture date: 2026-10-07

## Baseline

Repository: `emptiesvoid-cloud/QF_solver`

Baseline branch: `main`

Baseline commit: `e367fe58b2b9ebb4aef321424ca775e80e82d9ca`

Verified `origin/main`: `e367fe58b2b9ebb4aef321424ca775e80e82d9ca`

Published baseline: annotated tag `v0.2.11`, target
`afd2efa469a18e66581720ff4801f50de7d29eb4` (tag object
`be8114f22c68e1bc6bf0dd35c9f2466c0ca72890`).

At capture, the checkout was clean, only `main` and `origin/main` were present,
there was one worktree and there were no open pull requests. Git and GitHub
references agreed. QF Solver 0.2.11 is publicly verified on GitHub, PyPI and
Zenodo; the version DOI is `10.5281/zenodo.23214487` and the concept DOI is
`10.5281/zenodo.22697897`.

WP00 work is isolated on `codex/v0.2.12-wp00-baseline`. It does not change the
baseline commit, published tag, release assets or any 0.2.11 qualification
decision.

## Release purpose and scope

QF Solver 0.2.12 is a bounded A+NL release: reduced linear structural dynamics,
enriched excitation channels, and targeted consolidation of existing nonlinear
static behavior. Its V&V is scoped to the changed and new methods. It is not a
global solver requalification campaign.

### Core work packages

| WP | Frozen purpose |
|---|---|
| WP00 | Baseline, scope and authorities |
| WP01 | Shared contracts |
| WP02 | Prepared dynamic system |
| WP03 | Excitation channels and phasors |
| WP04 | Modal basis and damping |
| WP05 | Reduced harmonic response |
| WP06 | Modal Newmark transient |
| WP07 | Uniform base acceleration |
| WP08 | Nonlinear stress measures and semantic migration |
| WP09 | Corotational tangent robustness |
| WP10 | Nonlinear accepted states, checkpoint migration and convergence |
| WP11 | Results, serialization and API integration |
| WP12 | Targeted V&V and performance characterization |
| WP13 | Release engineering |

### MUST / OPTIONAL / DEFERRED

| Class | Scope |
|---|---|
| MUST, core | WP00–WP13 as listed above. WP08–WP10 consolidate only existing nonlinear-static scope. |
| OPTIONAL, recommended only | OPTION-A, residual flexibility. `OPTION_A_CORE_DEPENDENCY = NO`; omission does not block the core release. WP00 does not authorize its implementation. |
| OPTIONAL, not selected | OPTION-B, Prepared Campbell; OPTION-C, solid dynamic stress snapshots. |
| DEFERRED | generalized-alpha; reduced shell dynamics; nonlinear transient dynamics; multiplicative finite-strain plasticity; general contact/mortar overhaul; general finite sliding; explicit central-difference dynamics; major new element families; general prestressed modal; general follower loads; distributed rotor expansion; rotor rubbing; GPU rewrite; general MPI/HPC redesign. |

The initial dynamic element scope is TET4, TET10, HEX8, HEX20 and non-rotating
BEAM2, with linear isotropic elasticity, homogeneous fixed supports, admissible
concentrated masses and springs on existing structural DOFs, serial execution,
and the compatible existing backends. The reduced operators must satisfy the
positive-definite assumptions explicitly selected for each method. Unsupported
massless directions fail closed. Shells, unhandled algebraic coordinates,
contact, complex MPC/RBE, rotors, prestressed states and follower loads are out
of scope. A new route rejecting such a model must not break a legacy route that
already accepts it.

The nonlinear track is consolidation, not a new mechanics family. It covers
corotational J2 stress semantics and result migration, robustness and
observability of the existing numerical tangent, accepted states, checkpoint
migration, convergence/failure reporting, and an explicit method-specific
support matrix. It does not add nonlinear transient dynamics, multiplicative
plasticity, general finite-strain plasticity, general contact, or a general
corotational reformulation.

## Method and result scope

| Analysis / method | Element and material scope | Excitation / damping | Result availability and qualification target |
|---|---|---|---|
| Prepared dynamic system | TET4/TET10/HEX8/HEX20/non-rotating BEAM2; isotropic linear elastic | Contracted force/base channels only; no implicit damping matrix | Prepared operator identity and diagnostics; method scope under G02 and G03-DYN |
| Modal basis | Same bounded domain | No excitation in basis construction; basis is undamped, damping assigned separately by an explicit contract | Eigenpairs, residuals, clusters and truncation diagnostics; EXPERIMENTAL, G03-DYN/G04-DYN |
| Reduced harmonic | Same bounded domain | Explicit force phasors; base-acceleration phasors only under WP07 contract; modal damping only if WP01 defines it | Complex response and availability diagnostics; direct/full-basis equivalence only when assumptions, especially damping, are compatible; EXPERIMENTAL |
| Modal Newmark | Same bounded domain | Explicit force histories and, after WP07, uniform base acceleration; no inferred physical damping matrix | Time histories and checkpoint availability are declared by method; EXPERIMENTAL |
| Uniform base acceleration | Same bounded domain | Uniform translational input with explicit axis, units, sign and time/frequency representation | Form equivalent loading using full mass before eliminating constrained DOFs; distinguish relative and absolute response; unavailable reactions are not reported as zero; EXPERIMENTAL |
| OPTION-A residual flexibility | No broader element/material domain than reduced harmonic | Only if compatible with frozen damping semantics | Separate option gate; not a core dependency and not authorized for implementation by WP00 |
| Nonlinear stress migration | Existing corotational J2 nonlinear-static scopes only | Existing static loads | Stress measure identity and legacy migration are explicit; preserve method-specific maturity; targeted G03-NL/G04-NL |
| Corotational tangent | Existing corotational scopes only | Existing static load path | Persist raw and returned tangent diagnostics; preserve method-specific maturity; targeted G03-NL/G04-NL |
| Accepted state/checkpoint | Existing nonlinear-static scopes only | Existing load/continuation state | Safe migration and explicit refusal of ambiguous state; targeted G02/G03-NL/G04-NL |

All newly introduced dynamic methods target `EXPERIMENTAL`. Existing nonlinear
routes retain their record-specific maturity; WP00 grants no promotion.
`NUMERICAL_PASS_IMPLIES_QUALIFICATION = NO`. Analysis family, element family,
material, method and result availability are separate scope dimensions. No
new route inherits an old maturity silently.

WP01 must freeze method-aware maturity, result availability,
serialization/version contracts, physical/operator/excitation identities,
checkpoint migration policy, damping semantics, reaction availability,
relative/absolute frames and qualification-scope selection before numerical
implementation begins. In particular, prescribed modal damping does not
create a complete physical damping matrix C; reaction availability and
full-basis/direct comparisons must reflect that distinction.

## Inherited technical findings

These are confirmed inputs to the relevant WPs, not fixes performed by WP00:

| Finding | Status | Assigned WP | WP00 treatment |
|---|---|---|---|
| Newmark physical identity incomplete | CONFIRMED | WP02 | Record; prepare identity contract |
| Unsafe nonlinear checkpoint v1-to-v2 migration case | CONFIRMED | WP10 | Record; require fail-closed migration |
| Corotational `second_piola_stress` label incorrect | CONFIRMED | WP08 | Record; define stress semantics and migration |
| Corotational tangent uses central differences | CONFIRMED | WP09 | Record; no formulation change in WP00 |
| Returned tangent is symmetrized | CONFIRMED | WP09 | Record raw and returned forms separately |
| Finite-difference step depends on coordinate origin (`max(abs(coords))`) | CONFIRMED | WP09 | Record origin-invariance requirement |
| HEX8 force evaluations | 49 | WP09 | Characterization input |
| HEX20 force evaluations | 121 | WP09 | Characterization input |

For WP08/WP09, if remediation requires a substantial new constitutive
formulation, finite-strain plasticity, or general corotational continuum
reformulation: STOP, record the limitation, and require rescope. Do not silently
expand v0.2.12.

## Current authorities

| Authority | Role | WP00 finding/action |
|---|---|---|
| `PUBLIC_RELEASE_POLICY.md` | Current public release facts and release policy | Its current-release paragraph was stale (0.2.10). WP00 updates only that present-state paragraph to 0.2.11. The selected-distribution/whole-archive separation remains unchanged. |
| `CITATION.cff`, `pyproject.toml` | Current citation, version, license and project metadata | Already identify 0.2.11. Citation has release date 2026-10-07 and version DOI 10.5281/zenodo.23214487; project DOI is concept DOI 10.5281/zenodo.22697897. No edit. |
| `qualification/0_2_11/authorized_selected_package_release_contract_afd2efa.json` | Exact v0.2.11 selected package/tag authorization | Historical, source/hash-bound evidence; immutable and not reused as the v0.2.12 contract. |
| `qualification/0_2_11/publication_verification_0_2_11.json` | Post-publication G09 proof for GitHub, PyPI and Zenodo | Historical release evidence; immutable. |
| `qualification/capability_registry.json`, `qualification/0_2_7/capability_registry_v2.json` | Existing capability registry inputs and generated view | Earlier versioned scope; not a standalone method-aware 0.2.12 maturity authority. Preserve; WP01 defines prospective representation. |
| `qualification/element_analysis_matrix.json` | Existing element/analysis coverage and runtime maturity lookup input | Consumed by current tooling, but its historical scope/date cannot grant maturity to a new method. Preserve; WP01 makes new method maturity explicit. |
| `src/solveur/core/qualification.py`, `src/solveur/verification/traceability.py` | Runtime maturity and model-scope behavior | Executable authority for current behavior; WP01 must prevent silent inheritance by new methods. No code change in WP00. |
| `.github/workflows/quality.yml`, `.github/workflows/docs-tests.yml`, `.github/workflows/publish-pypi.yml` | CI, docs and release execution | Operational workflows; quality is not automatically a tag-triggered gate. No workflow change in WP00. |
| `qualification/0_2_11/wp03_vnv_data_contract.json`, `verification/v2/` | Execution identity, safe resume and evidence projection precedent | Reusable design precedent, not a substitute for dynamic physical/operator/excitation identity. |
| `qualification/0_2_12/wp00_baseline_scope_contract.json` | 0.2.12 baseline/scope authority | Current planning record on the WP00 branch; amendments require explicit scope control. |

No historical 0.2.10 or 0.2.11 decision, result, artifact, maturity or tag is
rewritten. Preserve `HISTORICAL_G03 = FAIL_PRESERVED`,
`HISTORICAL_WP14 = HOLD_NOT_PROMOTED`, and
`WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO`.

## Reference dependency DAG

```text
WP00 -> WP01 -> WP02 -> WP03 / WP04 -> WP05 / WP06 / WP07
                         WP01 -> WP08 -> WP09 -> WP10
WP05 + WP06 + WP07 + WP10 + WP01 -> WP11 -> WP12 -> WP13

OPTION-A: separate authorization after WP01/WP02/WP04/WP05/WP11;
          does not block the core.
```

WP03 and WP04 may proceed once WP01 contracts and the WP02 interface are
frozen. Downstream work must not invent an unresolved prerequisite contract.

## QF0212 release gates

| Gate | Purpose and pass rule | Fail/blocking rule | Evidence | WP00 status |
|---|---|---|---|---|
| G01 Baseline / scope | Exact baseline, scope, exclusions, authorities and historical status are recorded and reviewed. | Baseline drift, scope ambiguity, stale authority left uncorrected, or historical rewrite blocks all implementation. | This contract, this report, Git refs and validation output. | PASS when WP00 deliverables validate. |
| G02 Architecture / identities | WP01/WP02 freeze physical/operator/excitation identity, maturity, result availability, serialization, damping/reactions/frames and checkpoint policy with negative tests. | Any ambiguous identity, implicit damping/reaction, unsafe resume or silent maturity inheritance blocks dependent numerical work. | Versioned contracts, diagrams and positive/negative tests. | NOT RUN. |
| G03 Formulations | Separate DYN and NL verdicts. Each track passes its equations, semantics and fail-closed scope tests independently. | A failure on either track cannot be hidden by the other; blocks the affected track. | Formulation contracts, independent/local checks and reviewed derivations. | DYN NOT RUN; NL NOT RUN. |
| G04 Numerical behavior | Separate DYN and NL verdicts against preregistered metrics, references and limits. | A failed metric, post-hoc threshold change or hidden ambiguity blocks the affected claim. | Hashed execution records with expected/observed/error/threshold/status. | DYN NOT RUN; NL NOT RUN. |
| G05 Non-regression / interfaces | Existing routes, public APIs, serialization and supported checkpoint behavior remain compatible; changed availability is explicit. | Unexplained numerical/API regression or silent state/data loss blocks integration. | Exact-SHA targeted regression results and before/after observables. | NOT RUN. |
| G06 Candidate / audit | Exact source/artifacts, package/docs scans, reproducible build, install probes and claims pass. | Hash/source mismatch, payload or evidence gap blocks tag authorization. | Freeze contract, CI, scans, build manifest and probes. | NOT RUN. |
| G07 Publication | Owner-authorized exact tag/assets are published and downloaded/hash-verified per channel; no whole-archive clearance is implied. | Remote mismatch, extra archive, missing authorization or overstated claims blocks final verdict. | Tag, channel records, downloaded hashes and publication verification record. | NOT RUN. |

G03 and G04 always retain independent `DYN` and `NL` sub-verdicts. A global
gate is PASS only if each required sub-verdict passes; `SKIPPED` or
`NOT_APPLICABLE` is never silently treated as PASS. WP00 closes only G01.

## Non-regressions and WP01 boundary

Preserve the currently supported linear-static routes, direct modal/harmonic/
Newmark routes, non-rotating BEAM2 behavior, supported concentrated-mass and
spring assembly, boundary reduction, nonlinear-static/contact behavior outside
authorized WP08–WP10 scope, existing result readers/serializers, supported
checkpoint readers, API/CLI/import behavior and current package behavior.
Legacy failures and maturity decisions remain attributed to their original
records.

WP01 is limited to contracts, schemas, architecture decisions, migration
rules, compatibility declarations and contract-level positive/negative tests.
It must freeze all nine shared-contract topics listed in the contract before
numerical implementation. It must not implement M/K assembly changes, an
excitation channel, modal reduction, transient integration, base loading,
stress/tangent changes, checkpoint migration code, OPTION-A, or any WP02–WP13
feature.

## WP00 validation and exit

WP00 verified the requested baseline, tag target, clean checkout, worktree and
branch state, remote state and absence of open PRs. The only stale current
authority found was the 0.2.10 latest-release sentence in
`PUBLIC_RELEASE_POLICY.md`; it is corrected on this WP00 branch without
rewriting historical evidence. No numerical implementation or release action
was performed. The machine-readable contract and this report are validated
with JSON parsing, scope assertions and `git diff --check` before WP00 is
committed.

WP00 is closed only on its branch commit. `main`, `v0.2.11`, published artifacts
and all prior records remain unchanged. WP01 is ready to begin after this
closeout, but is not started by WP00.
