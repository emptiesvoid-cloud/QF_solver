---
doc_id: DOC-OWNER-MITC4-LAM-STAT-PLANAR-001
revision: 0.2
status: owner_reviewed
review_mode: owner_review
promotion_target: stable
scope: mitc4-laminate-static
---

# Owner review — MITC4 multicouche statique plan régulier

Cette proposition sépare le sous-périmètre plan régulier du probe courbe
oblique, qui reste explicitement hors de la promotion stable. Trois chargements
et trois niveaux de maillage sont comparés avec une théorie classique des
stratifiés, NAFEMS R0031 et Code_Aster.

| Observable | Valeur fine | Limite | Verdict |
| --- | ---: | ---: | --- |
| Membrane, erreur L2 contraintes par pli | 0,00389 % | 1 % | PASS |
| Flexion, erreur L2 contraintes par pli | 0,25389 % | 1 % | PASS |
| Combiné, erreur L2 contraintes par pli | 0,03791 % | 1 % | PASS |
| QF / NAFEMS, déplacement | 0,45761 % | 1 % | PASS |
| Code_Aster / NAFEMS, déplacement | 0,71029 % | 1 % | PASS |
| QF / Code_Aster, déplacement | 0,87852 % | 1 % | PASS |
| Résidu libre maximal | 2,457e-10 | 1e-8 | PASS |

## Domaine proposé

Le domaine stable proposé est limité aux plaques MITC4 planes, stratifiées
symétriques `[0/90/90/0]`, en élasticité linéaire, petits déplacements,
maillages réguliers et chargements membrane, flexion ou combinés. Les
contraintes sont évaluées dans la zone intérieure documentée, hors singularité.

Le maillage distordu à 15 % et la coque courbe à orientation oblique ne sont
pas inclus. Le probe courbe atteint 2,0434 % après six niveaux et reste donc
dans un périmètre expérimental séparé.

## Questions Owner

### Q1 — Domaine

Le sous-périmètre plan régulier, avec les trois chargements et les exclusions
indiquées, est-il suffisamment défini pour une cible `stable` ?

Réponse Owner : `OUI`.

### Q2 — Critère d’erreur

Les erreurs principales inférieures ou égales à 1 % et le résidu maximal
`2,457e-10` sont-ils acceptables pour ce sous-périmètre ?

Réponse Owner : `OUI`.

### Q3 — Exclusions

Les cas courbes obliques, maillages distordus, S13/S23, singularités de bord,
dommage, rupture et délamination sont-ils correctement exclus ?

Réponse Owner : `OUI`.

### Q4 — Décision

Décision Owner : `stable` pour la plaque stratifiée plane régulière et les
chargements documentés. Le registre machine-readable conserve
`accepted_with_recommendations` avec une cible `stable`.

Owner : Quentin Farinazzo (déclaration électronique)

Date : 2026-08-21

## Artefacts

- `qualification/maturity_evidence_0_2_1/mitc4_laminate_static_planar.json`
- `qualification/vnv/mitc4_laminate_static_planar_stable_001/reference/`
- `output/pdf/mitc4_laminate_static_planar_stable_owner_review.pdf`
- `qualification/maturity_criteria_0_2_1.json`
