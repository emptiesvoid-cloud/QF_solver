---
doc_id: OWNER-REVIEW-ST-01-A-TET4-001
revision: 0.1
status: owner_reviewed
---

# Owner review ST-01-A - TET4

Cette fiche demande une decision sur une promotion eventuelle de
`owner_accepted` vers `stable` pour un domaine strictement borne : TET4
isotrope, petits deplacements, statique lineaire, modal, Newmark lineaire et
harmonique sans amortissement.

La decision ne doit pas etre deduite automatiquement du statut technique
`PASS_EXTERNAL_CORRELATION`. Elle doit etre completee par l'Owner, datee et
signee.

## Dossier de preuve

Le resume principal est
`qualification/maturity_evidence_0_2_1/tet4_stable_batch_01/summary.json` et le
rapport detaille est
`qualification/maturity_evidence_0_2_1/tet4_stable_batch_01/report.md`.

| Cas | Geometrie | Elements retenus | Modal | Newmark | Harmonique | Maillage modal |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Reference | prismatique | 135 | `2.738e-11` | `6.380e-13` | `6.981e-13` | `3.417 %` |
| Epais | prismatique court/epais | 582 | `5.226e-13` | `6.375e-14` | `1.634e-13` | `2.396 %` |
| Cylindrique | arbre circulaire | 504 | `5.668e-12` | `6.869e-13` | `1.307e-13` | `3.720 %` |

Les trois preuves Code_Aster utilisent l'image `18.1.0` epinglee par digest,
avec meme maillage, meme grille temporelle et meme grille frequentielle.

## Point de verification ferme techniquement

Sur le cas prismatique court/epais, un cinquieme niveau a ete calcule jusqu'a
`25 766` elements TET4. L'increment statique final est maintenant de
`4.972 %`, sous le seuil commun de `10 %`; l'increment modal est de `2.396 %`.
Le warning precedent est ferme techniquement par raffinement, sans relacher
le seuil. La decision de maturite reste toutefois manuelle.

## Questions Owner

1. Les trois geometries TET4 et les quatre routes d'analyse couvrent-elles le domaine propose ? Réponse Owner : `OUI`.
2. Les correlations Code_Aster meme-maillage, les residus et les invariants sont-ils acceptables ? Réponse Owner : `OUI`.
3. Le raffinement supplementaire de la geometrie epaisse, avec un increment statique final de `4.972 %`, est-il suffisant ? Réponse Owner : `OUI`.
4. Les exclusions isotropie, petits deplacements, absence d'amortissement et absence de non-linearite sont-elles suffisantes ? Réponse Owner : `OUI`.
5. La maturite `stable` est-elle acceptable pour ce domaine borne, sans extrapolation ? Réponse Owner : `OUI`.
6. Decision : `stable`, `accepted_with_recommendations` ou maintien `owner_accepted` ? Réponse Owner : `stable`.

## Decision

- Reponse Owner : `stable` avec recommandations non bloquantes
- Date : 2026-08-21
- Owner : Quentin Farinazzo (déclaration électronique)
- Domaine accepte : .......................................................
- Exclusions confirmees : .................................................
