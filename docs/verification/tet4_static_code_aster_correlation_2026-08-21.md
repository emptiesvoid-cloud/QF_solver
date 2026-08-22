---
doc_id: DOC-UNREGISTERED-VERIFICATION-TET4-STATIC-CODE-ASTER-CORRELATION-2026-08-21
revision: 0.1
status: draft
applicable_version: 0.2.1a0
reviewer: ''
approver: ''
---

# Corrélation statique TET4 / Code_Aster

| Champ | Valeur |
| --- | --- |
| Étude | `VNV-TET4-STATIC-CODEASTER-TETRA4-021` |
| Date | `2026-08-21` |
| Domaine | TET4 isotrope, petites déformations, statique linéaire |
| Oracle | Code_Aster `18.1.0`, élément `TETRA4` |
| Maillage | identique entre QF_solver et Code_Aster |
| Critère externe | écart de déplacement inférieur à `1 %` |

## Résultat

La campagne utilise quatre niveaux de maillage d'un porte-à-faux 3D. La
charge est répartie sur la face terminale par pondération de surface, puis
appliquée avec les mêmes nœuds dans les deux solveurs.

| Éléments | Écart relatif `UZ` QF_solver / Code_Aster |
| ---: | ---: |
| 100 | `3.96e-12 %` |
| 135 | `1.71e-11 %` |
| 202 | `2.08e-10 %` |
| 313 | `8.05e-11 %` |

La corrélation structurelle externe est donc **PASS** avec une marge très
large sous `1 %`. Les détails machine sont disponibles dans
`qualification/vnv/external/code_aster_tet4_static/reference/summary.json`.

## Limite de convergence

L'incrément de flèche entre les deux derniers maillages est d'environ `4,64 %`.
Ce résultat est identique dans les deux solveurs et provient du caractère non
imbriqué des maillages Gmsh successifs. Il ne remet pas en cause l'accord entre
les opérateurs, mais il empêche encore la promotion générale `stable` tant
qu'une étude h propre, avec maillages imbriqués ou extrapolation de Richardson,
n'a pas été produite.

La comparaison avec la formule poutre 1D de Timoshenko reste un diagnostic de
flexion et ne constitue pas le critère primaire de cette corrélation 3D.

## Artefacts

- `summary.json` : métriques, contrôles et verdict ;
- `report.md` : tableau de résultats ;
- `tet4_static_code_aster.png` : flèches et écarts en échelle logarithmique ;
- `h1/` à `h4/` : maillages, decks et sorties Code_Aster ;
- `vnv_manifest.json` : provenance de l'étude.
