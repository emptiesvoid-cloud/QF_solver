---
doc_id: DOC-ELEM-MITC4-02
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# MITC4 - Interpolation, Jacobien et tying

## Interpolation bilineaire

Sur $-1\le\xi,\eta\le1$:

$$
N_1=\tfrac14(1-\xi)(1-\eta),\quad
N_2=\tfrac14(1+\xi)(1-\eta),
$$

$$
N_3=\tfrac14(1+\xi)(1+\eta),\quad
N_4=\tfrac14(1-\xi)(1+\eta).
$$

Le Jacobien plan est $\mathbf J=\mathbf D_\xi^T\mathbf X_{2D}$ et les
gradients lignes utilisent $\mathbf D_x=\mathbf D_\xi\mathbf J^{-T}$. Son
determinant doit etre positif aux quatre points de Gauss.

## Cisaillement de Reissner-Mindlin

Dans la base locale, les deformations transverses sont

$$
\gamma_{xz}=w_{,x}+\theta_y,
\qquad \gamma_{yz}=w_{,y}-\theta_x.
$$

Une interpolation bilineaire directe impose trop de contraintes lorsque
l'epaisseur diminue et provoque le shear locking.

## Points de tying MITC

Les composantes covariantes sont evaluees aux milieux des quatre cotes:

$$
A=(0,-1),\quad B=(1,0),\quad C=(0,1),\quad D=(-1,0).
$$

La composante suivant $\xi$ interpole A et C en fonction de $\eta$; celle
suivant $\eta$ interpole D et B en fonction de $\xi$:

$$
\tilde\gamma_\xi=\tfrac12[(1-\eta)\gamma_\xi^A+(1+\eta)\gamma_\xi^C],
$$

$$
\tilde\gamma_\eta=\tfrac12[(1-\xi)\gamma_\eta^D+(1+\xi)\gamma_\eta^B].
$$

Le Jacobien transforme ensuite ces composantes vers $(x,y)$. Ce choix reduit
les contraintes parasites sans supprimer physiquement l'energie de
cisaillement.

## Verification du tying

Le code conserve un element `Q4FullShearElement` uniquement comme temoin. Sur
une plaque mince, sa reponse doit se verrouiller alors que MITC4 garde une
convergence utilisable. Cette comparaison fait partie de la preuve, pas de
l'API de production.

References: [REF-MITC4-DVORKIN](../../reference/references.md#ref-mitc4-dvorkin),
[REF-MITC-BATHE](../../reference/references.md#ref-mitc-bathe).

