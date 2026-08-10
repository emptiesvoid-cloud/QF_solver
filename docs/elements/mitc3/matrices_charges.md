---
doc_id: DOC-ELEM-MITC3-04
revision: 0.1
status: draft technique
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# MITC3+ - Matrices, masse, charges et condensation

## Rigidite enrichie

Avant condensation, $\widehat{\mathbf q}=[\mathbf q^T,\boldsymbol\alpha^T]^T$
contient 18 DDL nodaux et deux rotations internes. La rigidite est

$$
\widehat{\mathbf K}_e=
\int_{\widehat A}
\left(
\mathbf B_m^T\mathbf A\mathbf B_m+
\mathbf B_b^T\mathbf D\mathbf B_b+
\mathbf B_s^T\mathbf A_s\mathbf B_s+
\mathbf B_d^Tk_d\mathbf B_d
\right)\det\mathbf J\,dr\,ds.
$$

Pour un stratifie non symetrique, les termes
$\mathbf B_m^T\mathbf B\mathbf B_b$ et leur transpose sont ajoutes.
L'integration utilise la regle de Dunavant a sept points de degre cinq.

## Condensation statique

Avec

$$
\widehat{\mathbf K}_e=
\begin{bmatrix}\mathbf K_{qq}&\mathbf K_{q\alpha}\\
\mathbf K_{\alpha q}&\mathbf K_{\alpha\alpha}\end{bmatrix},
$$

les amplitudes internes sans charge propre valent

$$
\boldsymbol\alpha=-\mathbf K_{\alpha\alpha}^{-1}
\mathbf K_{\alpha q}\mathbf q.
$$

La matrice assemblee est le complement de Schur

$$
\mathbf K_e=\mathbf K_{qq}
-\mathbf K_{q\alpha}\mathbf K_{\alpha\alpha}^{-1}\mathbf K_{\alpha q}.
$$

Le code effectue une resolution lineaire de $\mathbf K_{\alpha\alpha}$, pas
un inverse explicite. La meme transformation de Guyan projette la masse, afin
que les rotations internes restent coherentes en modal et en dynamique.

## Masse coherente

La masse repartit l'inertie de translation $\rho t$ et l'inertie de rotation
$\rho t^3/12$. Aucune inertie artificielle n'est ajoutee a la rotation de
drilling. Les DDL de drilling sans masse sont condenses par le reducteur
dynamique global.

## Charges coherentes

Une traction surfacique constante $\mathbf p$ produit

$$
\mathbf f_a=\int_A L_a\mathbf p\,dA={A\over3}\mathbf p.
$$

Une traction constante sur une arete $(a,b)$ de longueur $\ell$ produit
$\ell\mathbf t/2$ a chacun des deux noeuds. La pression positive suit la
convention de charge de QF_solver et agit suivant la normale locale negative.
Les forces de gravite utilisent la masse surfacique du materiau.

Code: `Mitc3ShellElement.stiffness_components`, `mass`,
`mitc3_condensation.py` et `DistributedLoadIntegrator`.

