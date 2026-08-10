---
doc_id: DOC-ELEM-MITC4-04
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# MITC4 - Resultantes, faces et qualite

## Resultantes de coque

Le post-traitement separe deformation membrane $\boldsymbol\varepsilon_m$,
courbure $\boldsymbol\kappa$ et cisaillement transverse
$\boldsymbol\gamma_s$. Les resultantes sont

$$
\mathbf N=\mathbf A\boldsymbol\varepsilon_m,
\qquad \mathbf M=\mathbf D\boldsymbol\kappa,
\qquad \mathbf Q=\mathbf S\boldsymbol\gamma_s.
$$

Elles sont exprimees dans le repere local de la facette.

## Faces inferieure et superieure

Avec $z\in[-t/2,t/2]$ mesure suivant $\mathbf e_3$:

$$
\boldsymbol\varepsilon(z)=\boldsymbol\varepsilon_m+z\boldsymbol\kappa,
\qquad
\boldsymbol\sigma(z)=\mathbf C_{ps}\boldsymbol\varepsilon(z).
$$

QF_solver exporte `bottom` a $z=-t/2$ et `top` a $z=+t/2$, avec contraintes
principales planes et von Mises. Une inversion de connectivite echange le sens
physique des faces.

## Planarite et distorsion

Le noyau projette les quatre noeuds sur le plan moyen local. Le validateur
mesure l'ecart hors plan avant projection, les quatre angles internes, le
rapport des aretes, l'aire projetee et les determinants de Jacobien.

Une facette legerement non planaire peut produire `WARNING`; une aire nulle,
un Jacobien negatif ou une orientation voisine incoherente produit `FAIL`.
Pour une coque fortement courbe, il faut raffiner afin que chaque facette
reste une approximation locale credible.

## Limite de recuperation

Les resultantes et faces sont actuellement evaluees au centre pour la sortie
compacte, avec points d'integration disponibles dans l'audit. Les pics aux
coins et singularites de bord ne sont pas une valeur de conception sans etude
de convergence locale.

Code: `solveur/post/stress.py`, `solveur/mesh/validation.py`.

