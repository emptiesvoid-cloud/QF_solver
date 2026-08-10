---
doc_id: DOC-ELEM-MITC4-03
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# MITC4 - Matrices, charges et rotation de drilling

## Decomposition de la rigidite

La rigidite locale est publiee par contributions:

$$
\mathbf K_e=\mathbf K_m+\mathbf K_b+\mathbf K_s+\mathbf K_d,
$$

$$
\mathbf K_m=\int_A\mathbf B_m^T\mathbf A\mathbf B_m\,dA,
\quad
\mathbf K_b=\int_A\mathbf B_b^T\mathbf D\mathbf B_b\,dA,
$$

$$
\mathbf K_s=\int_A\mathbf B_s^T\mathbf S\mathbf B_s\,dA.
$$

Pour une coque isotrope, $\mathbf A\propto Et$, $\mathbf D\propto Et^3/12$
et $\mathbf S\propto\kappa Gt$. Les quatre points de Gauss $2\times2$
integrent toutes les contributions.

## Courbures et signes

Les conventions locales sont

$$
\kappa_x=\theta_{y,x},\quad
\kappa_y=-\theta_{x,y},\quad
\kappa_{xy}=\theta_{y,y}-\theta_{x,x}.
$$

Elles determinent le signe des moments et des contraintes aux faces. Changer
la normale ou la connectivite inverse les labels top/bottom.

## Rotation de drilling

$\theta_z$ n'appartient pas a la cinematique physique minimale de la facette
plane. Une penalisation controlee utilise

$$
\gamma_d=\theta_z-\tfrac12(v_{,x}-u_{,y}),
\qquad
\mathbf K_d=\int_A k_d\mathbf B_d^T\mathbf B_d\,dA.
$$

Cette raideur stabilise l'assemblage mais ne doit pas dominer membrane ou
flexion. Sa valeur est tracee dans le materiau et les audits energetiques.

## Charges

La traction surfacique est integree aux quatre points de Gauss. Une pression
positive agit suivant la normale opposee. Une traction d'arete est repartie
lineairement entre les deux noeuds de l'arete. Les moments nodaux explicites
restent des charges nodales sur `RX`, `RY` ou `RZ`.

Code: `mitc4/material.py`, `solveur/loads/integration.py`.

## Matrice de masse coherente

Pour les analyses modales et Newmark, la vitesse d'un point situe a la cote
$z$ dans l'epaisseur est deduite de la vitesse de la surface moyenne et des
rotations tangentielles. L'energie cinetique integree dans l'epaisseur donne

$$
T_e=\frac12\int_A\left[
\rho t\,\dot{\mathbf u}_0^T\dot{\mathbf u}_0+
\frac{\rho t^3}{12}
(\dot\theta_x^2+\dot\theta_y^2)
\right]dA.
$$

Avec les fonctions bilineaires $N_i$, la matrice locale implementee est

$$
\mathbf M_e=\int_A\mathbf N^T
\operatorname{diag}\left(
\rho t,\rho t,\rho t,
\frac{\rho t^3}{12},\frac{\rho t^3}{12},0
\right)\mathbf N\,dA.
$$

Elle est integree aux quatre points de Gauss puis transformee vers le repere
global. Le zero associe a $\theta_z$ est volontaire: ajouter une inertie de
drilling modifierait artificiellement les frequences propres. QF_solver traite
cette direction par condensation lorsque l'assemblage la laisse effectivement
sans masse.

Les invariants testes sont la symetrie, la semi-positivite, la masse
translationnelle $\rho tA$, les inerties $\rho t^3A/12$ et l'objectivite sous
rotation rigide.

### Precision, stockage et masse concentree

La masse coherente conserve les couplages nodaux issus de $N_iN_j$. Son
stockage creux suit le voisinage du maillage et son produit matrice-vecteur a
un cout proportionnel au nombre de coefficients non nuls. Elle reproduit
l'energie cinetique de l'interpolation MITC4 et constitue l'unique formulation
acceptee dans les scopes modal, Newmark et harmonique.

Une masse concentree serait diagonale, donc moins couteuse a stocker et a
inverser. Elle modifie toutefois la repartition modale, les frequences hautes
et les inerties rotatoires; aucune regle de lumping MITC4 n'a encore ete
verifiee dans QF_solver. Elle reste donc hors scope et une demande explicite
`mass_formulation: lumped` ou `concentrated` est rejetee.
