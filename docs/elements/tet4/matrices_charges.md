---
doc_id: DOC-ELEM-TET4-03
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET4 - Matrices elementaires et charges

## Matrice deformation-deplacement

Avec $N_{i,x}=b_i$, $N_{i,y}=c_i$, $N_{i,z}=d_i$, le bloc nodal est

$$
\mathbf B_i=
\begin{bmatrix}
b_i&0&0\\0&c_i&0\\0&0&d_i\\
c_i&b_i&0\\0&d_i&c_i\\d_i&0&b_i
\end{bmatrix}.
$$

L'ordre de Voigt est
$(\varepsilon_{xx},\varepsilon_{yy},\varepsilon_{zz},\gamma_{xy},
\gamma_{yz},\gamma_{xz})$; les cisaillements sont des deformations
ingenieur.

## Rigidite

Pour l'elasticite isotrope lineaire,

$$
\mathbf K_e=V\mathbf B^T\mathbf D\mathbf B.
$$

L'integration a un point est exacte puisque $\mathbf B$ et $\mathbf D$ sont
constants. La matrice est symetrisee numeriquement par
$(\mathbf K_e+\mathbf K_e^T)/2$.

## Masse coherente

La masse utilise

$$
\mathbf M_e=\frac{\rho V}{20}
\begin{bmatrix}
2\mathbf I&\mathbf I&\mathbf I&\mathbf I\\
\mathbf I&2\mathbf I&\mathbf I&\mathbf I\\
\mathbf I&\mathbf I&2\mathbf I&\mathbf I\\
\mathbf I&\mathbf I&\mathbf I&2\mathbf I
\end{bmatrix}.
$$

Sa somme vaut $3\rho V$ car chaque direction de translation porte la masse
totale.

## Charges de volume

Une densite de force constante $\mathbf b$ produit
$\mathbf f_i=V\mathbf b/4$. Pour la gravite,
$\mathbf b=\rho\mathbf g$ et une densite strictement positive est requise.

Le controle d'assemblage ne se limite pas a la valeur appliquee au noeud. Il
verifie que la somme des contributions elementaires restitue la force totale
attendue et que le moment resultant autour de l'origine correspond a
$\sum_i \mathbf x_i\times\mathbf f_i$. Ce controle detecte les erreurs de
repere, d'unite, de signe ou de face avant la resolution.

## Tractions et pression

Sur une face triangulaire plane de normale sortante $\mathbf n$,

$$
\mathbf f_e^\Gamma=\int_\Gamma\mathbf N^T\mathbf t\,d\Gamma.
$$

Une pression positive est compressive: $\mathbf t=-p\mathbf n$. L'integrateur
calcule aussi resultante et moment autour de l'origine pour auditer les signes
et les unites.

Pour chaque chargement distribue, le rapport indique donc: type de charge,
support geometrique, repere, unite attendue, force resultante, moment
resultant et ecart de conservation. Une pression ou traction est refusee si
la face n'appartient pas a l'element; une orientation invalide est une erreur
de maillage, pas une correction automatique.

Code: `solveur/loads/integration.py`, `solveur/core/assembler.py`.
