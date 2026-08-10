---
doc_id: DOC-COMP-002
revision: 0.1
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Theorie classique des stratifies

## Empilement et interfaces

Les plis sont declares **de la face inferieure vers la face superieure**. Pour
une epaisseur totale `h`, l'origine est le plan moyen geometrique :

\[
z_0=-\frac{h}{2},\qquad
z_k=z_{k-1}+t_k,\qquad
z_n=+\frac{h}{2}.
\]

Chaque `LaminaPly` associe un materiau `OrthotropicLamina`, une epaisseur
strictement positive, un angle et un nom facultatif. L'angle suit les
conventions de la [lamelle orthotrope](lamelle_orthotrope.md).

## Cinematique

La theorie classique suppose les normales droites et ne decrit pas le
cisaillement transverse. La deformation dans le plan varie lineairement dans
l'epaisseur :

\[
\boldsymbol\varepsilon(z)
=\boldsymbol\varepsilon^0+z\boldsymbol\kappa,
\]

avec

\[
\boldsymbol\varepsilon^0=
\begin{bmatrix}\varepsilon_x^0&\varepsilon_y^0&\gamma_{xy}^0\end{bmatrix}^T,
\qquad
\boldsymbol\kappa=
\begin{bmatrix}\kappa_x&\kappa_y&\kappa_{xy}\end{bmatrix}^T.
\]

Cette convention fixe le signe des matrices de couplage. Une courbure positive
augmente la composante correspondante lorsque `z` augmente vers la face
superieure.

## Matrices A, B et D

Pour le pli `k`, `Qbar_k` est constant entre `z_(k-1)` et `z_k`. L'integration
exacte en epaisseur donne :

\[
\mathbf A=\sum_{k=1}^{n}\overline{\mathbf Q}_k(z_k-z_{k-1}),
\]

\[
\mathbf B=\frac12\sum_{k=1}^{n}\overline{\mathbf Q}_k
(z_k^2-z_{k-1}^2),
\]

\[
\mathbf D=\frac13\sum_{k=1}^{n}\overline{\mathbf Q}_k
(z_k^3-z_{k-1}^3).
\]

Les unites SI sont respectivement `N/m`, `N` et `N.m`. La matrice generalisee
est symetrique :

\[
\begin{bmatrix}\mathbf N\\\mathbf M\end{bmatrix}
=
\begin{bmatrix}\mathbf A&\mathbf B\\\mathbf B&\mathbf D\end{bmatrix}
\begin{bmatrix}\boldsymbol\varepsilon^0\\\boldsymbol\kappa\end{bmatrix}.
\]

`ClassicalLaminate.resultants` applique cette relation et
`generalized_strains` resout le systeme inverse sans former explicitement
l'inverse de `ABD`.

## Empilements symetriques, equilibres et non symetriques

**Symetrique.** Un empilement miroir par rapport au plan moyen conduit a
`B=0`. Une deformation de membrane pure ne genere alors aucun moment.

**Equilibre.** Des contributions `+theta` et `-theta` equivalentes annulent
les termes extensional-cisaillement `A16` et `A26`. Cela n'impose pas a lui
seul `D16=D26=0`.

**Non symetrique.** `B` peut etre non nul. Le couplage membrane-flexion est un
resultat physique et ne doit pas etre supprime numeriquement.

Les fonctions `is_symmetric` et `is_balanced` controlent directement les
couplages mecaniques obtenus, avec une tolerance relative explicite.

## Demonstrations analytiques

Materiau : `E1=135 GPa`, `E2=10 GPa`, `nu12=0,3`, `G12=5 GPa`; chaque pli
mesure `0,125 mm`.

| Empilement bas vers haut | Epaisseur | Propriete verifiee | Resultat |
| --- | ---: | --- | ---: |
| `[0]` | 0,125 mm | `A=Q t`, `B=0`, `D=Q t^3/12` | PASS |
| `[0/90/90/0]` | 0,500 mm | norme de `B` | `8,53e-14 N` |
| `[+45/-45/-45/+45]` | 0,500 mm | `A16=A26=0` | exact a l'arrondi |
| `[0/90]` | 0,250 mm | couplage `B11=-B22` | `983,117 N` |

Pour `[0/90/90/0]`, la matrice de membrane en `MN/m` vaut :

\[
\mathbf A=
\begin{bmatrix}
36.4933&1.51007&0\\
1.51007&36.4933&0\\
0&0&2.50000
\end{bmatrix}.
\]

Les tests imposent egalement la positivite de `ABD`, l'identite
`charges -> deformations -> charges` et l'egalite d'energie entre axes
materiau et axes elementaires aux faces et au milieu de chaque pli.

## Recuperation par pli

`ply_results` retourne pour chaque pli les valeurs `lower`, `middle` et
`upper` : coordonnee `z`, deformation et contrainte dans les axes elementaires,
puis deformation et contrainte dans les axes materiau. Aux interfaces, les
deformations sont continues mais les contraintes peuvent etre discontinues,
ce qui est physiquement attendu lorsque l'orientation change.

## Limites de P6.2

- aucune dilatation thermique ou hygroscopique;
- aucun cisaillement transverse `G13/G23`;
- aucun offset de surface de reference;
- aucune integration dans MITC4;
- les criteres de premier pli sont traites dans un module separe; aucun
  endommagement ni aucune degradation de rigidite;
- aucune revendication de validation structurelle composite.

Reference : [REF-COMP-JONES](../reference/references.md#ref-comp-jones).
