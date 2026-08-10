---
doc_id: DOC-ELEM-TET4-06
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET4 : derivation complete

Cette page derive la formulation effectivement utilisee par `tet4.py`. Les
composantes de Voigt sont ordonnees $[xx,yy,zz,xy,yz,zx]$; les trois dernieres
deformations sont des cisaillements d'ingenieur.

## 1. Domaine, approximation et degres de liberte

Sur un volume $\Omega_e$, le champ de deplacement est approche par

$$
\mathbf u_h(\mathbf x)=\mathbf N(\mathbf x)\mathbf q_e,
\qquad
\mathbf q_e=[u_1,v_1,w_1,\ldots,u_4,v_4,w_4]^T.
$$

Les quatre fonctions barycentriques $N_i=L_i$ satisfont $\sum_iN_i=1$ et
$\sum_iN_i\mathbf x_i=\mathbf x$. Ainsi, tout mouvement rigide et tout champ
affine $\mathbf u=\mathbf a+\mathbf H\mathbf x$ sont reproduits exactement.
La contrepartie est une deformation uniforme par element.

## 2. Mapping et gradients

Le tetraedre de reference $(r,s,t)$ est defini par

$$
L_1=1-r-s-t,\quad L_2=r,\quad L_3=s,\quad L_4=t.
$$

Avec $\mathbf x=\sum_iL_i\mathbf x_i$, le Jacobien est constant. Dans le
code, l'ecriture equivalente est la matrice nodale

$$
\mathbf A=\begin{bmatrix}1&x_1&y_1&z_1\\1&x_2&y_2&z_2\\
1&x_3&y_3&z_3\\1&x_4&y_4&z_4\end{bmatrix},
\qquad
N_i=a_i+b_ix+c_iy+d_iz,
$$

ou la ligne $i$ de $\mathbf A^{-1}$ fournit $(a_i,b_i,c_i,d_i)$. Le volume
oriente vaut $V=\det(\mathbf A)/6$. Un volume non strictement positif est
rejete avant toute matrice de rigidite.

## 3. Deformations et loi isotrope

La relation deformation-deplacement est

$$
\boldsymbol\varepsilon=\mathbf B\mathbf q_e,
\qquad \mathbf B=[\mathbf B_1\ \mathbf B_2\ \mathbf B_3\ \mathbf B_4],
$$

$$
\mathbf B_i=\begin{bmatrix}
b_i&0&0\\0&c_i&0\\0&0&d_i\\c_i&b_i&0\\0&d_i&c_i\\d_i&0&b_i
\end{bmatrix}.
$$

Pour l'elasticite isotrope 3D, avec $\mu=E/[2(1+\nu)]$ et
$\lambda=E\nu/[(1+\nu)(1-2\nu)]$,

$$
\mathbf D=\begin{bmatrix}
\lambda+2\mu&\lambda&\lambda&0&0&0\\
\lambda&\lambda+2\mu&\lambda&0&0&0\\
\lambda&\lambda&\lambda+2\mu&0&0&0\\
0&0&0&\mu&0&0\\0&0&0&0&\mu&0\\0&0&0&0&0&\mu
\end{bmatrix}.
$$

La convention de cisaillement d'ingenieur explique les coefficients $\mu$ sur
les trois dernieres diagonales. Les controles materiau refusent notamment
$E\le0$ et les valeurs de $\nu$ hors domaine physique code.

## 4. Travaux virtuels, rigidite et masse

Le principe des travaux virtuels discret donne

$$
\delta\mathbf q_e^T\left[\int_{\Omega_e}\mathbf B^T\boldsymbol\sigma\,d\Omega
-\mathbf f_e\right]=0.
$$

En elasticite lineaire homogene, $\mathbf B$ et $\mathbf D$ sont constants :

$$
\boxed{\mathbf K_e=V\mathbf B^T\mathbf D\mathbf B},\qquad
\mathbf f_{int,e}=V\mathbf B^T\boldsymbol\sigma.
$$

La masse coherente vient de $\int\rho\mathbf N^T\mathbf N\,d\Omega$ :

$$
\mathbf M_{ij}=\frac{\rho V}{20}
\begin{cases}2\mathbf I_3&i=j,\\\mathbf I_3&i\ne j.\end{cases}
$$

Un TET4 libre a six modes rigides : trois translations et trois rotations
infinitesimales. C'est un invariant de formulation, pas une instabilite.

## 5. Charges coherentes

Une force volumique uniforme $\mathbf b$ et une traction uniforme
$\bar{\mathbf t}$ sur une face triangulaire de surface $A_f$ donnent

$$
\mathbf f_e^{vol}=\frac{V}{4}[\mathbf b,\mathbf b,\mathbf b,\mathbf b]^T,
\qquad
\mathbf f_{face}=\frac{A_f}{3}[\bar{\mathbf t},\bar{\mathbf t},\bar{\mathbf t}]^T.
$$

Pour une pression, $\bar{\mathbf t}=-p\mathbf n$ selon la normale sortante.
Le solveur verifie resultante et moment resultant dans son audit de charges.

## 6. Demonstration : traction d'un tetraedre contraint

Si seul le ddl $u_{1x}$ reste libre, une force $F$ appliquee a ce ddl conduit
a $K_{ff}=V(\lambda+2\mu)$ et donc

$$
u_{1x}=\frac{F}{V(\lambda+2\mu)},\qquad
\sigma_{xx}=(\lambda+2\mu)u_{1x}=\frac{F}{V}.
$$

Le cas [TET4 statique](../../demonstrations/solides.md) controle cette
relation, la symetrie de $K$, le residu et l'equilibre global. Le
[patch TET4 maille](../../demonstrations/benchmarks/tet4_patch.md) etend la
preuve a un champ affine sur un maillage non structure.

## 7. Limites de la demonstration

L'exactitude affine ne garantit ni la convergence en flexion ni la qualite des
contraintes pres d'une singularite. Le TET4 peut verrouiller en volume quand
$\nu\to0.5$ et sa contrainte est discontinue entre elements. Ces effets sont
des limites de modele, non des erreurs de post-traitement.

## Tracabilite

| Objet | Code | Preuve | Exigence |
| --- | --- | --- | --- |
| $B$, $K_e$, $M_e$, charges de face/volume | `solveur/elements/solid/tet4.py` | `test_tet4_element.py`, `test_distributed_loads.py` | `REQ-SOL-001`, `REQ-LOAD-001` |
| Volume et orientation | `solveur/mesh/quality.py` | element inverse ou degenere refuse | `REQ-MESH-001` |
| Patch et convergence | campagne benchmark | `BM-SOL-TET4-PATCH-001` | `REQ-CMP-003` |

Reference principale : [REF-FEM-BATHE](../../reference/references.md#ref-fem-bathe).
