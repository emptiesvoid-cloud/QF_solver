# QF Solver knowledge base

**Scope:** repository-level technical orientation for QF Solver.
**Revision:** 2026-10-25.
**Reference:** current repository checkout; recheck release status and qualification state in their registries.

## Start here

QF Solver is a Python finite-element solver and engineering-analysis library. It contains solid, beam, shell, discrete, linear, dynamic, nonlinear, contact, and rotating-machinery routes. The repository includes established capabilities as well as experimental and narrowly bounded work. Presence in source code is not evidence of general scientific qualification.

Use this knowledge base in three steps:

1. **Orientation:** read this page, then [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).
2. **Domain understanding:** read [CAPABILITIES.md](CAPABILITIES.md), [MECHANICS.md](MECHANICS.md), or [ARCHITECTURE.md](ARCHITECTURE.md), as appropriate.
3. **Evidence and implementation:** follow their links to current source, tests, contracts, reports, and Owner decisions. Use [QUALIFICATION.md](QUALIFICATION.md) to interpret evidence scope.

## Navigation by task

| If the question is about… | Start with |
|---|---|
| What the project does and its current boundaries | [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) |
| Where a feature is implemented | [ARCHITECTURE.md](ARCHITECTURE.md), [DEVELOPMENT.md](DEVELOPMENT.md) |
| Whether a capability exists and its limits | [CAPABILITIES.md](CAPABILITIES.md) |
| What is integrated in the v0.2.12 candidate | [v0.2.12 release inventory](releases/v0.2.12.md) |
| Formulations, conventions, or physical assumptions | [MECHANICS.md](MECHANICS.md) |
| Impact of changing a shared module | [DEPENDENCIES.md](DEPENDENCIES.md) |
| Tests and verification routes | [TESTING.md](TESTING.md) |
| Meaning and provenance of qualification claims | [QUALIFICATION.md](QUALIFICATION.md) |
| Terms used by the code and qualification records | [GLOSSARY.md](GLOSSARY.md) |

## Technical source map

- Public package and API: [public facade](../../src/qf_solver/__init__.py), [API implementation](../../src/solveur/api/public.py), [API stability reference](../reference/api_stability.md).
- Analysis routing and model: [router](../../src/solveur/core/router.py), [model](../../src/solveur/core/model.py).
- Capability index: [docs/capabilities/index.md](../capabilities/index.md). It is a useful cumulative index; current code and release-specific normative records control technical conclusions.
- Current v0.2.12 state: [roadmap](../../qualification/0_2_12/ROADMAP.md), [WP00 baseline](../../qualification/0_2_12/wp00_baseline_scope.md), [WP11 closure assessment](../../qualification/0_2_12/wp11_final/closure_gate_assessment.md), [WP12 preparation](../../qualification/0_2_12/wp12_preparation/README.md).
- Historical rotating machinery: [rotating-modal guide](../mechanics/rotating-modal.md), [Campbell guide](../mechanics/campbell.md), [v0.2.11 verification index](../verification/0_2_11/README.md).

## Normative reading rules

- Read the applicable release-specific contract for equations, inputs, tolerances, refusals, and acceptance scope.
- Read source code to establish what the checked-out implementation actually does.
- Read the linked report, manifest, evidence identity, and Owner decision before repeating a qualification claim.
- Keep historical results separate from evidence executed on the current HEAD.
- Do not infer a supported element/material/analysis combination from separate support for each component.
- The cumulative capability index currently has controlled-candidate documentation status; it is an orientation aid, not the sole normative source.
- Repository safety and execution rules in [AGENTS.md](../../AGENTS.md) take precedence over this orientation material.

## Using this context outside the repository

A conversation assistant without repository access can be given [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) as portable context. When the repository is available, provide [INDEX.md](INDEX.md) as the entry point and let the assistant follow only the task-relevant pages and linked source records. These are plain Markdown files and do not require a provider-specific feature.

## Version and qualification snapshot

The last published release identified by the repository changelog is v0.2.11. The v0.2.12 branch is an integration candidate and must not be described as a published release. As recorded in the 2026-10-25 v0.2.12 roadmap, WP11 is CLOSED for its approved operational API and integration scope; WP12 and WP13 remain OPEN. The WP12 runner is at RUNNER_READY_FOR_OWNER_SECURITY_REVIEW and does not authorize scientific execution. Recheck the [roadmap](../../qualification/0_2_12/ROADMAP.md) and [WP12 preparation index](../../qualification/0_2_12/wp12_preparation/README.md) whenever current status matters.
