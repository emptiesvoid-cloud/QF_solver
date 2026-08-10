---
doc_id: DOC-ELEM-MITC3-02
revision: 0.2
status: draft technique
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# MITC3+ - Interpolation, bulle et tying

## Fonctions lineaires

Avec $L_1=1-r-s$, $L_2=r$ et $L_3=s$, les translations de la surface moyenne
sont interpolees par

$$
\mathbf u_0(r,s)=\sum_{a=1}^{3}L_a(r,s)\mathbf u_a.
$$

## Enrichissement des rotations

La bulle cubique vaut

$$
f_4=27rs(1-r-s).
$$

Elle est nulle sur les trois aretes. Les fonctions de rotation corrigees sont

$$
f_a=L_a-\frac13 f_4,\qquad a=1,2,3.
$$

Les rotations tangentielles utilisent alors quatre fonctions : trois valeurs
nodales et une amplitude interne. Cette construction preserve la trace
lineaire sur le contour et enrichit la flexion a l'interieur.

## Points de tying

Les cisaillements covariants compatibles $\gamma_{rt}$ et $\gamma_{st}$ sont
evalues aux points

$$
A=(1/6,2/3),\quad B=(2/3,1/6),\quad C=(1/6,1/6),
$$

et aux trois points proches du barycentre

$$
D=(1/3+d,1/3-2d),\quad
E=(1/3-2d,1/3+d),\quad
F=(1/3+d,1/3+d),
$$

avec $d=10^{-4}$. Le champ suppose reconstruit les deux composantes
covariantes suivant les equations (15) a (17) de la publication primaire.
Sa partie constante est notamment

$$
\widehat{\gamma}_{rt}^{\,c}
=\frac{2}{3}\left(
\gamma_{rt}^{(B)}-\frac{1}{2}\gamma_{st}^{(B)}
\right)
+\frac{1}{3}\left(
\gamma_{rt}^{(C)}+\gamma_{st}^{(C)}
\right),
$$

$$
\widehat{\gamma}_{st}^{\,c}
=\frac{2}{3}\left(
\gamma_{st}^{(A)}-\frac{1}{2}\gamma_{rt}^{(A)}
\right)
+\frac{1}{3}\left(
\gamma_{rt}^{(C)}+\gamma_{st}^{(C)}
\right).
$$

Les parentheses sont essentielles : le facteur $2/3$ multiplie les deux
termes du premier groupe. Un patch automatise impose successivement
$\gamma_{xz}$, $\gamma_{yz}$ puis les deux composantes et exige une
reproduction a la precision numerique.

Le passage aux composantes cartesiennes utilise le Jacobien de la facette.

Cette interpolation est la difference essentielle avec un triangle de
Reissner-Mindlin a cisaillement complet. Elle evite de surcontraindre la
condition de cisaillement nul lorsque $t/L$ devient petit.

## Jacobien

Pour les coordonnees locales $\mathbf x_a=(x_a,y_a)$,

$$
\mathbf J=
\begin{bmatrix}
\partial x/\partial r&\partial y/\partial r\\
\partial x/\partial s&\partial y/\partial s
\end{bmatrix}.
$$

$\det\mathbf J$ est constant pour une facette P1 et doit etre strictement
positif. Une valeur nulle ou negative bloque la resolution.

Code : `rotation_shape_functions`, `assumed_covariant_shear` et `_jacobian`.

## Reference primaire

Y. Lee, P.-S. Lee et K.-J. Bathe, *The MITC3+ shell element and its
performance*, Computers & Structures 138 (2014), equations (15) a (17),
DOI `10.1016/j.compstruc.2014.02.005`.
