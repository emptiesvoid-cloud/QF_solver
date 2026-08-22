---

doc_id: DOC-STABLE-PROMOTION-OPEN-GATES-20260821
revision: 0.1
status: controlled
applicable_version: 0.2.1a0
owner_decision_date: 2026-08-21
certification_claim: none
reviewer: ""
approver: ""
---

# Gates ouverts vers stable

Ce registre complete la decision Owner du 21 aout 2026. Les scopes promus
`stable` sont enregistres dans
`qualification/reviews/owner_stable_promotion_2026-08-21.json`. Les lignes
ci-dessous restent ouvertes et ne sont pas affectees par cette promotion.

## Gates techniques ou d'independance

| Scope | Gate | Point a fermer avant stable |
| --- | --- | --- |
| `mitc3-laminate-dynamic` | `BLOCKED_CRITERIA_FAILED` | Difference externe MITC3/DST superieure a 1 % sur les observables modale, Newmark et harmonique du domaine general. |
| `mitc3-laminate-static-curved` | `BLOCKED_CRITERIA_FAILED` | Convergence et comparabilite encore insuffisantes pour la famille axiale courbe. |
| `tet4-total-lagrangian-structural-v2` | `BLOCKED_OWNER_REVIEW` | Revue independante obligatoire; une decision Owner seule ne peut pas fermer ce gate. |

## Sous-perimetres techniquement prets mais sans decision stable

| Scope | Gate | Decision attendue |
| --- | --- | --- |
| `mitc3-laminate-dynamic-thin-planar` | `BLOCKED_OWNER_REVIEW` | Relecture du sous-perimetre stratifie plan mince avec reference DKT. |
| `mitc3-laminate-static-curved-mixed-transverse` | `BLOCKED_OWNER_REVIEW` | Decision sur les chargements mixte et transverse, sans axial. |
| `mitc4-laminate-dynamic-refined-three-layups` | `BLOCKED_OWNER_REVIEW` | Decision sur les trois layups plans raffines. |

## Scopes conserves hors stable par decision Owner

| Scope | Statut conserve | Limite principale |
| --- | --- | --- |
| `mitc4-laminate-dynamic` | `owner_accepted_experimental_bounded_use` | Dynamique stratifiee courbe et amortissement realiste hors domaine. |
| `orthotropic-solid-tet4-tet10` | `owner_accepted` | Orthotropie homogeneisee uniquement; pas de composite pli-par-pli. |

Les autres domaines non lineaires, contact et grand modele restent suivis dans
la feuille de route avec leur maturite propre. Ils ne doivent pas etre deduits
des promotions lineaires signees.
