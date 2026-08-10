---
doc_id: DOC-ELEM-TET10-02
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET10 - Interpolation isoparametrique et Jacobien

## Fonctions quadratiques

Pour les coordonnees barycentriques $L_1+L_2+L_3+L_4=1$:

$$
N_i=L_i(2L_i-1),\quad i=1,\ldots,4,
$$

$$
N_{ij}=4L_iL_j
$$

sur chacune des six aretes. Elles forment une partition de l'unite et
reproduisent tout polynome quadratique complet sur le tetraedre.

## Mapping

Le point de depart est le mapping isoparametrique standard des elements de
Lagrange: les memes fonctions interpolent la geometrie et le deplacement.
Cette convention est celle exposee dans `REF-FEM-BATHE`; elle fixe le sens du
Jacobien avant toute implementation ou test.

La geometrie et le deplacement sont isoparametriques:

$$
\mathbf x(\boldsymbol\xi)=\sum_{a=1}^{10}N_a\mathbf x_a,
\qquad
\mathbf u(\boldsymbol\xi)=\sum_{a=1}^{10}N_a\mathbf u_a.
$$

En definissant $J_{a i}=\partial x_i/\partial\xi_a$, la transformation correcte
des gradients lignes est

$$
\mathbf D_x=\mathbf D_\xi\mathbf J^{-T}.
$$

L'emploi de $J^{-1}$ ne serait correct que pour certaines matrices
symetriques ou diagonales. Un patch oblique dedie protege ce point dans la
suite de tests.

## Jacobien variable

Pour un element courbe, $\det\mathbf J(\boldsymbol\xi)$ varie. QF_solver le
controle aux points de Hammer et sur un lattice barycentrique ferme de 35
points. Le minimum doit etre positif. Ce controle numerique ne constitue pas
une preuve analytique de positivite sur tout le domaine.

## Integration de Hammer sur geometrie droite

Les quatre points sont les permutations de $(a,b,b,b)$:

$$
a=\frac{5+3\sqrt5}{20},\qquad
b=\frac{5-\sqrt5}{20},\qquad
w=\frac{1}{24}.
$$

Les decimales ne sont pas une definition: elles sont seulement l'evaluation
numerique de ces expressions. Chaque point porte le poids $w$; la somme des
quatre poids vaut donc $4w=1/6$, soit le volume du tetraedre de reference.
La regle et sa precision sont reliees en annexe a
[REF-HAMMER-STROUD-1956](../../reference/references.md#ref-hammer-stroud-1956)
et [REF-TETRA-KEAST-1986](../../reference/references.md#ref-tetra-keast-1986).

La somme des poids vaut $1/6$. Pour une geometrie droite et un materiau
constant, cette regle integre exactement le produit quadratique
$\mathbf B^T\mathbf D\mathbf B$.

## Quadrature positive sur geometrie courbe

Lorsque les noeuds milieux quittent les milieux geometriques des aretes,
$\mathbf J$ varie et les gradients physiques contiennent $\mathbf J^{-1}$.
L'integrande de rigidite n'est alors plus un simple polynome quadratique. Une
regle de Hammer a quatre points peut rester stable tout en sous-integrant la
geometrie.

QF_solver applique donc la selection deterministe suivante :

| Geometrie | Critere | Regle de rigidite |
| --- | --- | --- |
| droite | deviation relative maximale des noeuds milieux $\leq 10^{-12}$ | Hammer, 4 points |
| courbe | deviation superieure a $10^{-12}$ | Duffy positive d'ordre 4, 64 points |

La transformation de Duffy utilise

$$
r=a,\qquad s=(1-a)b,\qquad t=(1-a)(1-b)c,
$$

avec le facteur geometrique $(1-a)^2(1-b)$. Les poids sont tous positifs. La
campagne de verification compare la regle de production a une Duffy d'ordre 8,
soit 512 points.

Avant l'integration, le Jacobien est evalue sur un lattice barycentrique ferme
de 35 points. Un minimum non positif interdit l'assemblage. Ce controle reste
un echantillonnage numerique et ne prouve pas analytiquement la positivite sur
chaque point du volume.

Tests: patch affine aligne, patch affine oblique, champ quadratique et
variation de Jacobien dans `tests/unit/test_tet10_element.py`; campagne
`VNV-TET10-GEOMETRY-QUADRATURE-011` dans
`tests/verification/test_tet10_geometry_quadrature_vnv.py`.

References : `REF-FEM-BATHE`, `REF-TETRA-KEAST-1986`.
