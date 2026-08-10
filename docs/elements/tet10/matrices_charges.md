---
doc_id: DOC-ELEM-TET10-03
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET10 - Rigidite, masse et charges coherentes

\begingroup\small
\setlength{\parskip}{0pt}
\setlength{\abovedisplayskip}{4pt}
\setlength{\belowdisplayskip}{4pt}

## Rigidite

La matrice deformation-deplacement contient dix blocs construits a partir des
gradients physiques. Pour une regle d'integration $\mathcal G$, la rigidite est

$$
\mathbf K_e=\sum_{g\in\mathcal G}w_g\det\mathbf J_g
\mathbf B_g^T\mathbf D_g\mathbf B_g.
$$

La regle comporte quatre points de Hammer sur un element droit et 64 points
Duffy sur un element courbe. Ce choix est verifie face a une reference Duffy
d'ordre 8. La symetrisation finale ne remplace pas les tests d'energie, de
modes rigides et de convergence de quadrature.

En non-lineaire materiau, chaque point de Hammer possede actuellement son etat
commis. Cette voie a quatre etats reste `experimental` et hors du perimetre de
la campagne de quadrature courbe. Son extension exigera une migration controlee
des etats internes vers la regle enrichie.

## Masse coherente

$$
\mathbf M_e=\int_{\hat\Omega}\rho
[\mathbf N^T\mathbf N\otimes\mathbf I_3]\det\mathbf J\,d\hat\Omega.
$$

QF_solver utilise une transformation de Duffy et une quadrature
Gauss-Legendre d'ordre cinq, soit 125 points. Ce choix coute plus cher que la
rigidite mais couvre le Jacobien variable et la masse quadratique coherente.
Sur la geometrie courbe de verification, la masse physique obtenue par
$\sum M_{ij}/3$ differe de l'integration Duffy d'ordre huit de seulement
$3,57\times10^{-16}$. La plus petite valeur propre de la matrice elementaire
reste strictement positive.

## Charge de volume

La meme quadrature integre $\mathbf N^T\mathbf b$. Une gravite exige une
densite positive. Une force volumique est definie par unite de volume courant
initial, dans les unites du modele.

## Faces quadratiques

Chaque face a six noeuds ordonnes: trois sommets puis les aretes 1-2, 2-3,
3-1 de la face. Une regle triangulaire d'ordre cinq integre

$$
\mathbf f_e^\Gamma=\int_\Gamma\mathbf N^T\mathbf t\,d\Gamma.
$$

Pour une traction constante sur une face droite, les contributions nodales
des sommets peuvent etre nulles et celles des trois noeuds milieux non nulles;
ce comportement est celui de la charge coherente quadratique, pas une perte
de charge. La resultante et le moment permettent de le verifier.

Code: `solveur/loads/integration.py`. Tests: pression TET10 et conservation de
resultante dans `tests/unit/test_distributed_loads.py`.

Sur une face T6 courbe, la regle d'ordre cinq est comparee a une reference
d'ordre neuf: erreurs relatives de $9,10\times10^{-18}$ sur la resultante et
$4,71\times10^{-16}$ sur le moment. La meme quadrature T3/T6, centralisee dans
`solveur/elements/solid/quadrature.py`, sert aux pressions, tractions et cas V&V.

\endgroup
