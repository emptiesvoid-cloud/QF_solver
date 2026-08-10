---
doc_id: DOC-FEM-003
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Materiaux

## Elasticite isotrope 3D

Avec $E$ et $\nu$:

$$
\lambda=\frac{E\nu}{(1+\nu)(1-2\nu)},\qquad
\mu=\frac{E}{2(1+\nu)}.
$$

La matrice $\mathbf D$ associe les trois composantes normales par $\lambda$ et
place $\mu$ sur les cisaillements d'ingenieur. Les controles imposent $E>0$ et
$-1<\nu<0.5$. Une densite strictement positive est necessaire en modal,
Newmark et harmonique.

## Coque isotrope

La loi en contraintes planes utilise:

$$
\mathbf D_p=\frac{E}{1-\nu^2}
\begin{bmatrix}1&\nu&0\\\nu&1&0\\0&0&(1-\nu)/2\end{bmatrix}.
$$

Les rigidites de membrane et de flexion sont respectivement proportionnelles
a $t$ et $t^3/12$. Le cisaillement transverse inclut le facteur de correction
de la formulation MITC4.

## Elasticite orthotrope 3D

La loi `orthotropic_3d` utilise neuf constantes independantes
`E1/E2/E3`, `nu12/nu13/nu23` et `G12/G13/G23`. La reciprocite construit une
souplesse symetrique dans les axes materiau; sa positivite est controlee avant
calcul. Les tenseurs de deformation et de contrainte sont tournes explicitement
entre le repere global et le repere materiau, avec cisaillements d'ingenieur
pour les deformations. La formulation, le JSON et les preuves TET4/TET10 sont
donnes dans la [page des solides orthotropes](../composites/solides_orthotropes.md).

## Plasticite J2

La loi experimentale utilise un retour radial de von Mises et un ecrouissage
isotrope. L'etat contient la deformation plastique et la variable cumulee.
La tangente algorithmique depend de la direction d'ecoulement. La campagne
`VNV-J2-MATERIAL-CYCLIC-001` la verifie par differences finies, controle les
invariants de plasticite et compare la traction monotone a la theorie
bilineaire ainsi qu'a quatre points exacts publies par Abaqus. La loi reste
neanmoins hors du scope stable : la correlation cyclique avec un logiciel
independant compatible avec l'ecrouissage isotrope et la campagne structurelle
multi-elements ne sont pas encore terminees.

## Lamelle orthotrope composite

Le socle experimental `OrthotropicLamina` implemente la loi reduite en
contraintes planes et sa rotation entre axes elementaires et materiau. Les
conventions, equations et demonstrations `0/90/+/-45 deg` sont detaillees dans
[la page composite](../composites/lamelle_orthotrope.md). Aucun calcul MITC4
multicouche n'est encore autorise.
