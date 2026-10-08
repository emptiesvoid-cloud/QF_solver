# WP10 handoff to WP-C01 — state and convergence boundaries

WP10 does not modify contact laws, penalty parameters, active-set updates, friction, or contact search. It preserves the existing transaction and checkpoint machinery while tightening the rule that only a complete accepted composite state is persisted.

WP-C01 must preserve these boundaries:

1. Contact trial/internal variables belong to the same `NonlinearState` composite as displacement, material state, continuation state, and accepted-step metadata.
2. Newton, line-search, tangent-probe, and rejected cutback evaluations must not mutate accepted contact state.
3. A commit publishes contact and material state atomically with the converged displacement/load state. Rollback discards all trial contact history.
4. A checkpoint is written only after accepted-state commit, with counters agreeing across top-level step, accepted metadata, and continuation metadata where present.
5. The existing v2 topology/model signature must bind contact definitions. New component identity metadata also includes contact definitions in the physical identity.
6. Legacy v1 contact history remains unproven and non-resumable. Read-only decoding does not establish contact-history compatibility.
7. Contact convergence/rejection diagnostics must remain attributable to the rejected attempt even if a later cutback converges; trial arrays are not to be serialized as accepted data.
8. No general semi-smooth Newton guarantee is implied. WP-C01 must report contact branch transitions, active-set behavior, and limitations using its own preregistered criteria.

This is an interface handoff only. WP-C01 remains unstarted and requires explicit Owner authorization.
