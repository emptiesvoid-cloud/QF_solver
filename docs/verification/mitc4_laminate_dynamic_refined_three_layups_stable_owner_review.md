---
doc_id: DOC-OWNER-MITC4-LAM-DYN-REFINED-STABLE-001
revision: 0.2
status: owner_reviewed
review_mode: owner_review
promotion_target: stable
scope: mitc4-laminate-dynamic-refined-three-layups
---

# Owner review : MITC4 multicouche dynamique raffiné

Ce sous-périmètre couvre trois empilements symétriques plans :
`[0/90/90/0]`, `[45/-45/-45/45]` et `[0/45/45/0]`. Les calculs comprennent
les voies modale, Newmark et harmonique. Le troisième empilement contient un
cas avec amortissement proportionnel à la masse.

## Résultats au niveau fin `48x12`

| Empilement | Erreur modale | Erreur Newmark | Erreur harmonique |
| --- | ---: | ---: | ---: |
| `[0/90/90/0]` | 0,1303 % | 0,0272 % | 0,0144 % |
| `[45/-45/-45/45]` | 0,3792 % | 0,4841 % | 0,2613 % |
| `[0/45/45/0]` | 0,1281 % | 0,0669 % | 0,0349 % |

Le maximum primaire fin est `0,4841 %`, inférieur à la limite de `1 %`.
La série externe utilise `24x6`, `36x9` et `48x12`; les niveaux
intermédiaires restent publiés, même lorsque l'empilement angle-ply dépasse
1 %. Le niveau fin est donc nécessaire et ne doit pas être masqué.

## Décision Owner enregistrée

La décision Owner du 21 août 2026 est **stable pour ce sous-périmètre borné**.
Le registre machine-readable porte la décision `accepted_with_recommendations`
avec une cible de promotion `stable`. Cette formulation conserve la
recommandation technique sans confondre une promotion interne avec une
certification externe.

## Domaine et exclusions

La cible `stable` est proposée uniquement pour les trois empilements plans,
les petits déplacements, les petites rotations, la masse cohérente avec
condensation du drilling et les analyses modale/Newmark/harmonique documentées.

Restent exclus : le cas de réserve à `10 000 QUAD4` dont le résidu modal est
insuffisant, les coques courbes dynamiques, les empilements non symétriques,
les grandes déformations, la calibration d'amortissement par essai, le
dommage, la rupture et la délamination.

## Questions Owner

### Q1 — Preuves et convergence

Les trois empilements et les trois niveaux de maillage, avec les résultats
finaux sous 1 %, couvrent-ils suffisamment ce sous-périmètre ?

Réponse Owner : `OUI`.

### Q2 — Dynamique et amortissement

Les invariants modaux, la convergence Newmark, la réponse harmonique et le cas
amorti sont-ils acceptables dans les limites indiquées ?

Réponse Owner : `OUI`.

### Q3 — Exclusions

Les limites concernant 10 000 éléments, les géométries courbes, le dommage,
la rupture et la délamination sont-elles acceptables ?

Réponse Owner : `OUI`.

### Q4 — Décision

Décision Owner : `stable` pour le sous-périmètre déclaré ; le registre
machine-readable conserve `accepted_with_recommendations` comme décision
traçable et cible `stable`.

Owner : Quentin Farinazzo (déclaration électronique)

Date : 2026-08-21

Déclaration : la promotion stable est acceptée pour les trois empilements
plans et les analyses couvertes. Elle ne s'étend pas aux exclusions listées.

## Artefacts

- `qualification/maturity_evidence_0_2_1/mitc4_laminate_dynamic.json` ;
- `qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/` ;
- `docs/verification/mitc4_laminate_dynamic_extended_owner_review.md` ;
- `output/pdf/mitc4_laminate_dynamic_extended_owner_review.pdf`.

Cette décision ne doit pas être extrapolée aux coques courbes, au cas
`10 000 QUAD4` ou aux mécanismes d'endommagement exclus.
