---
doc_id: DOC-FEM-004
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Assemblage, charges et blocages

## Numerotation des ddl

Le gestionnaire construit un indice compact a partir des besoins de chaque
type d'element. Un solide active trois translations; une coque active trois
translations et trois rotations. Un modele mixte n'invente donc pas de ddl
inutiles aux noeuds purement solides.

## Assemblage creux

Pour chaque element, la matrice locale est projetee dans les indices globaux.
Le mode standard accumule les triplets puis construit une matrice SciPy CSR;
le mode grand modele utilise des blocs et, avec PETSc, une matrice AIJ
preallouee.

$$
\mathbf K=\sum_e\mathbf A_e^T\mathbf K_e\mathbf A_e,
\qquad
\mathbf f=\sum_e\mathbf A_e^T\mathbf f_e.
$$

## Chargements coherents

Les forces volumiques, la gravite, les tractions et pressions sont integrees
avec $\mathbf N^T$. L'audit conserve leur resultante et leur premier moment.
Une pression morte suit la normale de la geometrie de reference; une pression
suiveuse n'est pas prise en charge.

## Conditions de Dirichlet

Le mode standard extrait le probleme libre $\mathbf K_{ff}\mathbf u_f=mathbf
f_f$. Les reactions sont recuperees sur les ddl bloques a partir du residu
global. En PETSc, les lignes/colonnes sont traitees sans matrice dense.

Un modele bien contraint supprime exactement les modes rigides necessaires.
Un sur-blocage peut produire un calcul numeriquement regulier mais
mecaniquement faux; il doit etre repere par la comparaison des reactions et du
champ de deformation.
