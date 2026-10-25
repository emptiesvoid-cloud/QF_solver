# Qualification and evidence guide

**Scope:** interpret evidence records without changing their authority or scope.
**Revision:** 2026-10-25.
For current release status, use the [v0.2.12 roadmap](../../qualification/0_2_12/ROADMAP.md) and release-specific records.

## Implementation is not qualification

Keep these claims separate:

1. **Implemented:** source contains a feature or route.
2. **Tested:** a test exists; this says nothing about whether it ran.
3. **Executed:** a recorded run identifies its code, inputs, environment, and outcome.
4. **Verified:** an applicable oracle checked the implementation under stated assumptions.
5. **Validated:** evidence supports adequacy for an intended physical use; numerical agreement alone may not establish this.
6. **Qualified/bounded:** an authorized decision accepts a named scope with explicit exclusions.

A test PASS is evidence for that test’s oracle and inputs. It does not automatically qualify the route. Historical PASS is bound to the identity, manifest, environment, and scope recorded at the time; it does not demonstrate current-HEAD non-regression.

## Evidence classes

- **Algebraic or invariant verification:** checks identities, residuals, symmetry, conservation-like quantities, or internal consistency.
- **Analytical verification:** compares with an independent solution for a defined idealized problem.
- **Spatial/time convergence:** studies mesh or time-step refinement for a stated observable.
- **External solver comparison:** scoped correlation to another numerical implementation.
- **Software non-regression:** checks behavior across a code change; physical adequacy depends on its oracle.
- **API/IO contract:** checks public compatibility, schema, refusal, or persistence behavior.
- **Performance measurement:** applies only to the recorded machine, environment, model, solver settings, and instrumentation.
- **Static inspection:** establishes what source/docs declare, not a numerical pass.

These classes answer different questions and are not interchangeable.

## Work packages and dispositions

WP numbering is release-specific: WP05 v0.2.11 is gyroscopic rotating modal, while WP05 v0.2.12 is reduced harmonic response. Always include release in a WP reference.

The latest recorded v0.2.12 portfolio state on 2026-10-25 is 19 WPs: 14 positive closures, one historical negative closure, and four open. This is an administrative tally, not qualification coverage.

| Recorded disposition | Meaning in this repository context |
|---|---|
| CLOSED | The recorded gate was accepted within its decision and scope; it is not blanket release qualification. |
| CLOSED_BOUNDED | Closed only within explicit bounded scope and exclusions. |
| CLOSED_NEGATIVE | Historical gate closed with a negative outcome; remediation may remain open. Do not restate it as PASS. |
| INCONCLUSIVE | Available evidence did not resolve the question; it is not PASS. |
| OPEN_WITH_BOUNDED_CERTIFICATES | Some certificates are accepted in narrow scopes while the package remains open. |
| OPEN | No closure decision is recorded. |
| NOT_RUN / NOT_ACQUIRED | No execution or accepted evidence is recorded for the stated item. |

Use the exact definitions in the relevant roadmap, contract, decision, and report if a label has a release-specific meaning.

## Current v0.2.12 distinctions

As recorded by the roadmap: WP-C01 is CLOSED_NEGATIVE with remediation open; WP-C02 is CLOSED_BOUNDED for AR/N03 only; WP-D01 is INCONCLUSIVE; WP-D02 is CLOSED_BOUNDED; WP-E01 is OPEN_WITH_BOUNDED_CERTIFICATES; WP11 is CLOSED for its approved API/integration scope; WP12 and WP13 are OPEN.

The [WP11 closure assessment](../../qualification/0_2_12/wp11_final/closure_gate_assessment.md) and its [traceability matrix](../../qualification/0_2_12/wp11_final/capability_traceability_matrix.tsv) define WP11’s boundary. WP12’s [preparation index](../../qualification/0_2_12/wp12_preparation/README.md), [runner security review](../../qualification/0_2_12/wp12_preparation/wp12_r2_runner_security_review.md), and [rotor regression plan](../../qualification/0_2_12/wp12_rotating_inherited_regression_plan.md) do not authorize campaigns. The runner is RUNNER_READY_FOR_OWNER_SECURITY_REVIEW; scientific execution remains disabled.

## Evidence traceability checklist

Before repeating a claim, identify:

- Applicable scientific contract and its version.
- Source commit/tree and relevant source file identities.
- Fixture/model/mesh identities.
- Exact test or campaign identifier and nodeids.
- Environment and external dependencies.
- Oracle, tolerances, and exclusions.
- Recorded result and Owner decision, if required.
- Whether evidence belongs to current HEAD or a historical snapshot.

Do not rewrite historical evidence to make it appear current. For exact history and provenance consult the manifests and immutable evidence referenced by each report.
