---
doc_id: DOC-ELEM-TET10-06
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET10 : derivation complete

Le TET10 est un element isoparametrique quadratique a dix noeuds et trente
ddl de translation. Cette formulation est disponible, mais reste
`experimental` dans le profil de qualification actuel.

## 1. Base barycentrique et ordre local

Les sommets portent $L_1,\ldots,L_4$. Les noeuds 5 a 10 sont, dans cet ordre,
les milieux des aretes $(1,2)$, $(2,3)$, $(3,1)$, $(1,4)$, $(2,4)$ et $(3,4)$.
Les fonctions de forme sont

$$
N_i=L_i(2L_i-1)\ (i=1,\ldots,4),\qquad
N_{ij}=4L_iL_j.
$$

Elles satisfont $N_a(\mathbf x_b)=\delta_{ab}$ et $\sum_{a=1}^{10}N_a=1$.
Une permutation de noeuds milieux modifie la geometrie et est donc une erreur
de connectivite, pas une simple convention d'affichage.

## 2. Transformation isoparametrique

La meme base approxime geometrie et deplacement :

$$
\mathbf x(r,s,t)=\sum_{a=1}^{10}N_a\mathbf x_a,
\qquad
\mathbf u_h(r,s,t)=\sum_{a=1}^{10}N_a\mathbf u_a.
$$

En posant $\mathbf D_r=\partial\mathbf N/\partial(r,s,t)$,

$$
\mathbf J=\mathbf D_r^T\mathbf X,\qquad
\nabla_x\mathbf N=\mathbf D_r\mathbf J^{-1}.
$$

Contrairement au TET4, $\mathbf J$, $\mathbf B$ et $\det\mathbf J$ varient
aux points d'integration. Un Jacobien doit rester positif aux points controles;
un test ponctuel positif ne garantit pas seul une geometrie courbe admissible.

## 3. Matrices elementaires

Chaque bloc $\mathbf B_a$ est construit avec les gradients physiques de
$N_a$, selon la meme convention de Voigt que le TET4. Les integrations sont

$$
\mathbf K_e=\sum_gw_g\det(\mathbf J_g)\mathbf B_g^T\mathbf D\mathbf B_g,
$$

$$
\mathbf M_e=\sum_gw_g\det(\mathbf J_g)\rho\mathbf N_g^T\mathbf N_g.
$$

La rigidite utilise la regle Hammer a quatre points; la masse coherente une
quadrature Duffy a 125 points. Les poids et points de quadrature appartiennent
a l'implementation et sont testes contre symetrie, masse positive et champ
constant.

## 4. Consistance et demonstration de patch

Pour une geometrie affine, les identites $\sum_aN_a=1$ et
$\sum_aN_a\mathbf x_a=\mathbf x$ assurent la reproduction exacte d'un champ
deplacement affine. Un champ quadratique est representable par les fonctions
de forme, mais son exactitude mecanique depend aussi de la quadrature, de la
geometrie et des conditions aux limites.

Le [patch TET4](../../demonstrations/benchmarks/tet4_patch.md) sert de
reference minimale d'equilibre affine; la [poutre TET4/TET10]
(../../demonstrations/benchmarks/cantilever.md) compare la convergence en
flexion. Le [cylindre de Lame](../../demonstrations/benchmarks/tet10_lame.md)
teste une geometrie courbe et un champ de contraintes connu.

## 5. Qualite et limites

La qualite doit etre evaluee sur la geometrie quadratique : aretes courbes,
variation du determinant de Jacobien et orientation aux points d'integration.
Une maille TET10 generee par simple ajout de milieux d'aretes est droite; elle
ne devient courbe que si les noeuds milieux sont deplaces de facon coherente.
Les contraintes sont evaluees a des points definis par le post-traitement :
elles ne sont pas automatiquement des valeurs nodales exactes.

## Tracabilite

| Objet | Code | Preuve | Exigence |
| --- | --- | --- | --- |
| Fonctions, Jacobien, $B$ et quadrature | `solveur/elements/solid/tet10.py` | `test_tet10_element.py` | `REQ-SOL-003` |
| Orientation et qualite | `solveur/mesh/quality.py` | validation TET10 | `REQ-MESH-001` |
| Geometrie courbe | benchmark Lamé | `BM-SOL-TET10-LAME-001` | `REQ-CMP-003` |

Reference principale : [REF-FEM-BATHE](../../reference/references.md#ref-fem-bathe).
