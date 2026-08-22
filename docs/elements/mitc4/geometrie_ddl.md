---
doc_id: DOC-ELEM-MITC4-01
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# MITC4 - Geometrie, ddl et repere local

## Facette de coque

Le MITC4 de QF_solver est une facette plane a quatre noeuds fondee sur la
cinematique de Reissner-Mindlin. Chaque noeud possede

$$
(u,v,w,\theta_x,\theta_y,\theta_z),
$$

soit 24 ddl par element. Les trois translations et trois rotations sont
exprimees globalement dans le modele, puis transformees dans la base locale de
la facette.

## Construction de la base

Les diagonales donnent la normale provisoire:

$$
\mathbf d_1=\mathbf x_3-\mathbf x_1,
\qquad \mathbf d_2=\mathbf x_4-\mathbf x_2,
\qquad \mathbf e_3=\frac{\mathbf d_1\times\mathbf d_2}
{\|\mathbf d_1\times\mathbf d_2\|}.
$$

La premiere arete non degeneree parmi 1-2, 4-3, 1-4 et 2-3 est projetee dans
le plan:

$$
\tilde{\mathbf e}_1=\mathbf a-(\mathbf a\cdot\mathbf e_3)\mathbf e_3,
\qquad \mathbf e_1=\tilde{\mathbf e}_1/\|\tilde{\mathbf e}_1\|,
$$

puis $\mathbf e_2=\mathbf e_3\times\mathbf e_1$. La matrice
$\mathbf R=[\mathbf e_1^T;\mathbf e_2^T;\mathbf e_3^T]$ est orthonormale.

## Transformation des ddl

Le bloc nodal vaut $\operatorname{diag}(\mathbf R,\mathbf R)$ et la
transformation elementaire est sa repetition sur quatre noeuds. La rigidite
globale est

$$
\mathbf K_e^g=\mathbf T^T\mathbf K_e^l\mathbf T.
$$

## Orientation

La connectivite doit suivre une boucle coherente. Deux elements voisins
doivent parcourir leur arete commune en sens oppose. L'importeur detecte les
orientations incoherentes et ne les repare jamais automatiquement, car la
normale porte les conventions de face superieure et inferieure.

Code: `solveur/elements/shell/mitc4/element.py`. Exigence: `REQ-SOL-002`.

