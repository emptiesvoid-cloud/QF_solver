---
doc_id: DOC-VV-TET4-REVIEW-001
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Decision interne TET4 lineaire isotrope

## Decision

Quentin Farinazzo accepte le 14 juillet 2026 le TET4 lineaire isotrope pour
un usage engineering interne dans le domaine explicitement teste.

| Champ | Valeur |
| --- | --- |
| Decision | `accepted` |
| Perimetre | `tet4-linear-static` |
| Mode de revue | `self_review` |
| Independence | `not_independent` |
| Visibilite du projet a la decision | `private` |
| Revendication de certification | aucune |

Le registre machine-readable est
`qualification/reviews/tet4_linear_isotropic_2026-07-14.json`.

## Preuves retenues

- patch 3D a contrainte constante;
- cinq maillages de traction et cinq maillages de compression;
- six maillages de flexion avec comparaison Timoshenko;
- huit maillages de torsion circulaire avec comparaison Saint-Venant;
- une sonde de contrainte h9 a `105 529` TET4, soit `4,007` fois h8;
- bilans des forces, moments, reactions, residus et energies;
- maillages, resultats VTU, PNG et manifestes SHA-256 regenerables.

## Resultats de convergence

| Cas | Maillages | Resultat principal | Conclusion |
| --- | ---: | --- | --- |
| Traction | 5 | erreur deplacement max `4,94e-15` | champ affine reproduit |
| Compression | 5 | erreur deplacement max `4,94e-15` | symetrie lineaire reproduite |
| Flexion | 6 | erreur fine `7,71 %`, ordre `1,377` | convergence monotone acceptee |
| Torsion, rotation | 8 | erreur fine `3,07 %`, ordre `1,499` | convergence monotone acceptee |
| Torsion, contraintes h8 | 8 | erreur L2 fine `29,06 %` | convergence lente mais coherente |
| Torsion, sonde h9 | 1 calcul fin | rotation `1,242 %`, contrainte L2 `18,891 %` | PASS sous seuil global `20 %` |

## Domaine accepte

L'acceptation couvre les petits deplacements et petites deformations, le
materiau elastique lineaire isotrope 3D, `E > 0 Pa`, `0 <= nu <= 0,45`, les
deplacements nodaux, reactions, equilibres globaux, identite energetique et
champs affines de deformation et de contrainte. Pour l'arbre circulaire lisse
de Saint-Venant, elle couvre aussi l'erreur globale L2 de contrainte sous le
seuil documente de `20 %` au niveau h9.

## Exclusions obligatoires

Cette decision ne couvre pas les pics ponctuels de contrainte, les
singularites, la quasi-incompressibilite au-dela de `nu = 0,45`, les grandes
transformations, la plasticite, le contact, la fatigue, la rupture ou une
certification reglementaire externe.

Lors de la publication future sur un depot Git public, cette page, le registre
JSON, les donnees de maillage, les courbes et les limitations devront rester
publies ensemble. Une auto-revue ne devra pas etre presentee comme une revue
independante.
