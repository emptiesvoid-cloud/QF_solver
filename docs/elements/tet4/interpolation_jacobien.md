---
doc_id: DOC-ELEM-TET4-02
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET4 - Interpolation et Jacobien

## Coordonnees barycentriques

Les quatre fonctions de forme sont

$$
N_1=1-r-s-t,\qquad N_2=r,\qquad N_3=s,\qquad N_4=t.
$$

Elles verifient partition de l'unite, positivite dans le tetraedre et
propriete de Kronecker $N_i(\mathbf x_j)=\delta_{ij}$.

La geometrie et les deplacements utilisent la meme interpolation:

$$
\mathbf x(r,s,t)=\sum_iN_i\mathbf x_i,
\qquad
\mathbf u(r,s,t)=\sum_iN_i\mathbf u_i.
$$

## Convention de Jacobien

QF_solver definit

$$
J_{a i}=\frac{\partial x_i}{\partial \xi_a},
\qquad \boldsymbol\xi=(r,s,t).
$$

Les gradients physiques, stockes par lignes, sont donc

$$
\frac{\partial\mathbf N}{\partial\mathbf x}
=\frac{\partial\mathbf N}{\partial\boldsymbol\xi}\mathbf J^{-T}.
$$

Pour TET4, $\mathbf J$ est constant. L'implementation calcule directement les
coefficients du polynome $N_i=a_i+b_ix+c_iy+d_iz$ en inversant la matrice
$[\mathbf1\ \mathbf X]$, ce qui est algebriquement equivalent.

## Reproduction d'un champ affine

Si $\mathbf u=\mathbf c+\mathbf H\mathbf x$, l'interpolation nodale reproduit
exactement ce champ. La deformation obtenue est

$$
\boldsymbol\varepsilon=\operatorname{sym}(\mathbf H),
$$

constante dans tout l'element. C'est la base du patch test.

## Conditionnement geometrique

Un determinant positif ne suffit pas a garantir une bonne precision. Une
forte disparite des aretes ou une faible hauteur augmente le conditionnement
de $\mathbf J$ et amplifie les erreurs d'arrondi. Le rapport de qualite publie
volume, aretes min/max et aspect ratio.

Tests: `tests/unit/test_tet4_element.py`,
`tests/verification/test_tet4_analytical.py`.

