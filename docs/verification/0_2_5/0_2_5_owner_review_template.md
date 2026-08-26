---
doc_id: DOC-NL-025-017
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 Owner Review template

## Review identity

| Field | Value |
|---|---|
| Candidate SHA | PENDING |
| Evidence digest | PENDING |
| Review date | PENDING |
| Owner | PENDING |
| Proposed decision | PENDING |

Allowed decisions: `more_evidence_required`, `accepted_with_recommendations`,
`accepted_for_bounded_experimental_use`, `accepted_for_release_0_2_5`.

Only `accepted_for_release_0_2_5`, after G11 passes on the exact candidate SHA,
can close G12.

## Planning approval questions

1. Approve the MUST/SHOULD/COULD boundary and optional friction policy?
2. Approve TET4/HEX8 as MUST and TET10/HEX20 as SHOULD for large deformation?
3. Approve Total Lagrangian StVK as the elastic geometric baseline, subject to
   audit, or request a different formulation?
4. Select the bounded J2+geometric model: corotational small-strain J2, a newly
   planned finite-strain plasticity model, or removal of J2+geometry from MUST?
5. Approve one Crisfield spherical arc-length method as the initial continuation
   target?
6. For frictionless contact, preserve the existing active-set multiplier method
   as reference, adopt penalty, or plan augmented Lagrangian from the start?
7. Confirm Full Newton as the only production-qualified nonlinear strategy?
8. Confirm the 0.2.4 coverage policy as the baseline rather than creating a new
   percentage target?
9. Confirm Code_Aster as primary external reference and rules for N/A tools?
10. Confirm that external numerical correlation is not a physical-validation
    claim?
11. Confirm triple coupling and Coulomb friction do not block 0.2.5a0?
12. Approve the gate dependencies and STOP/GO policy?

## Final release questions

1. Are all mandatory gate records complete on the candidate SHA?
2. Are objectivity, consistent tangent and transactional-state proofs adequate?
3. Are buckling and arc-length claims bounded to demonstrated problem classes?
4. Is contact enforcement sensitivity acceptable and documented?
5. Are coupled formulations mathematically approved and externally correlated?
6. Are all 0.2.4 capabilities free of unexplained regression?
7. Are performance and memory limits honestly stated?
8. Do public docs avoid claiming unqualified friction/high-order/triple coupling?
9. Do wheel/sdist/docs/smoke artifacts match the candidate SHA?
10. Does the Owner authorize an Owner-controlled tag, GitHub Release and PyPI
    publication as separate operations?

## Decision

**Owner decision:** PENDING

**Conditions/recommendations:** PENDING

**Signature:** PENDING
