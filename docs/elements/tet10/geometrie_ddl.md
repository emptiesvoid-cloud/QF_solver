---
doc_id: DOC-ELEM-TET10-01
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET10 - Geometrie, ordre des noeuds et ddl

## Connectivite interne

Le TET10 porte quatre sommets et six noeuds d'arete. La convention QF_solver
est:

| Noeud local | Support geometrique |
| ---: | --- |
| 1 a 4 | sommets du tetraedre oriente |
| 5 | arete 1-2 |
| 6 | arete 2-3 |
| 7 | arete 3-1 |
| 8 | arete 1-4 |
| 9 | arete 2-4 |
| 10 | arete 3-4 |

Chaque noeud porte `UX`, `UY`, `UZ`, soit trente ddl elementaires.

## Convention Gmsh

Le type Gmsh 11 place ses deux derniers noeuds sur les aretes 3-4 puis 4-2.
L'importeur applique donc une permutation controlee vers l'ordre interne. Ce
remappage precede les calculs de face, de Jacobien et de charge. Les tests
verifient les six milieux d'arete par leurs coordonnees et leurs identifiants.

## Orientation et reparation

L'orientation primaire utilise les quatre sommets. En cas d'inversion, une
reparation explicite permute aussi les six noeuds d'arete; permuter uniquement
deux sommets corromprait la geometrie quadratique. La permutation complete est
inscrite dans le rapport d'import.

## Geometrie droite ou courbe

Si chaque noeud d'arete est au milieu des deux sommets, le mapping est affine
et le Jacobien constant. Un noeud de bord deplace peut representer une arete
ou une face courbe. A l'interieur d'un maillage, une position incoherente peut
produire un Jacobien variable ou negatif malgre un volume des coins positif.

## Modes rigides

Comme TET4, le noyau attendu comporte trois translations et trois rotations.
Le test doit etre effectue sur un tetraedre oblique, car une geometrie alignee
sur les axes masque certaines erreurs de transformation.

Code: `solveur/elements/solid/tet10.py`,
`solveur/mesh/gmsh_importer.py`. Exigence: `REQ-SOL-003`.

