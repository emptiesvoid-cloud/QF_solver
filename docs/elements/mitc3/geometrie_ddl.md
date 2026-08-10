---
doc_id: DOC-ELEM-MITC3-01
revision: 0.1
status: draft technique
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# MITC3+ - Geometrie, DDL et reperes

## Triangle de reference

Le domaine parent est

$$
\widehat A=\{(r,s)\mid r\geq0,\ s\geq0,\ r+s\leq1\}.
$$

Les noeuds 1, 2 et 3 occupent respectivement $(0,0)$, $(1,0)$ et $(0,1)$.
La connectivite positive impose

$$
(\mathbf x_2-\mathbf x_1)\times(\mathbf x_3-\mathbf x_1)
\quad\hbox{oriente suivant la normale de face }+\mathbf e_3.
$$

Deux triangles voisins parcourent leur arete commune en sens opposes. Cette
condition est verifiee pour les maillages MITC3 purs et mixtes MITC3/MITC4.

## Repere local

QF_solver construit

$$
\mathbf e_1={\mathbf x_2-\mathbf x_1\over
\|\mathbf x_2-\mathbf x_1\|},\qquad
\mathbf e_3={(\mathbf x_2-\mathbf x_1)\times(\mathbf x_3-\mathbf x_1)
\over\|(\mathbf x_2-\mathbf x_1)\times(\mathbf x_3-\mathbf x_1)\|},
$$

$$
\mathbf e_2=\mathbf e_3\times\mathbf e_1.
$$

La matrice $\mathbf R=[\mathbf e_1^T;\mathbf e_2^T;\mathbf e_3^T]$ transforme
les vecteurs globaux en composantes locales. La face superieure est
$z=+t/2$ suivant $+\mathbf e_3$.

## DDL et transformation

Chaque noeud porte

$$
\mathbf q_a=[u_a,v_a,w_a,\theta_{x,a},\theta_{y,a},\theta_{z,a}]^T.
$$

Le bloc nodal est $\operatorname{diag}(\mathbf R,\mathbf R)$ et la
transformation de l'element contient trois blocs. Ainsi

$$
\mathbf q_l=\mathbf T\mathbf q_g,\qquad
\mathbf K_g=\mathbf T^T\mathbf K_l\mathbf T.
$$

Les deux amplitudes de rotation de bulle sont locales a l'element. Elles ne
figurent ni dans la numerotation globale ni dans les fichiers de resultats.

Code: `Mitc3ShellElement.local_frame` et `transform_dofs`.
Tests: rotation rigide, invariance par rotation et inversion d'orientation.

