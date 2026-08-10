---
doc_id: DOC-ELEM-MITC3-03
revision: 0.1
status: draft technique
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# MITC3+ - Formulation forte et faible

## Cinematique de Reissner-Mindlin

Dans le repere de facette,

$$
\mathbf u(x,y,z)=
\begin{bmatrix}
u_0+z\theta_y\\
v_0-z\theta_x\\
w_0
\end{bmatrix}.
$$

Les normales restent droites mais peuvent tourner par rapport a la surface
moyenne. Les deformations generalisees sont

$$
\boldsymbol\varepsilon_m=
[u_{0,x},v_{0,y},u_{0,y}+v_{0,x}]^T,
$$

$$
\boldsymbol\kappa=
[\theta_{y,x},-\theta_{x,y},\theta_{y,y}-\theta_{x,x}]^T,
$$

$$
\boldsymbol\gamma_s=
[w_{0,x}+\theta_y,w_{0,y}-\theta_x]^T.
$$

## Equations fortes

Sur une facette sans inertie, les resultantes verifient

$$
\nabla_s\cdot\mathbf N+\mathbf p_t=\mathbf0,\qquad
\nabla_s\cdot\mathbf Q+p_n=0,
$$

$$
\nabla_s\cdot\mathbf M-\mathbf Q+\mathbf m=\mathbf0.
$$

Les conditions naturelles prescrivent les efforts conjugues aux translations
et rotations. Les conditions essentielles prescrivent les DDL nodaux.

## Travail virtuel

La formulation faible recherche $\mathbf q$ telle que

$$
\delta W_{\mathrm{int}}(\mathbf q,\delta\mathbf q)
=\delta W_{\mathrm{ext}}(\delta\mathbf q)
\quad\forall\delta\mathbf q\in\mathcal V_0,
$$

avec

$$
\delta W_{\mathrm{int}}=
\int_A\left(
\delta\boldsymbol\varepsilon_m^T\mathbf N+
\delta\boldsymbol\kappa^T\mathbf M+
\delta\boldsymbol\gamma_s^T\mathbf Q
\right)dA.
$$

Pour un isotrope:

$$
\mathbf N=\mathbf A\boldsymbol\varepsilon_m,\quad
\mathbf M=\mathbf D\boldsymbol\kappa,\quad
\mathbf Q=\mathbf A_s\boldsymbol\gamma_s.
$$

Pour un stratifie:

$$
\begin{bmatrix}\mathbf N\\\mathbf M\end{bmatrix}
=
\begin{bmatrix}\mathbf A&\mathbf B\\\mathbf B&\mathbf D\end{bmatrix}
\begin{bmatrix}\boldsymbol\varepsilon_m\\\boldsymbol\kappa\end{bmatrix}.
$$

L'interpolation MITC intervient uniquement dans l'operateur de cisaillement;
les termes de membrane et de flexion proviennent des derives des fonctions
P1 et enrichies.

## Dynamique

La forme semi-discrete est

$$
\mathbf M\ddot{\mathbf q}+\mathbf C\dot{\mathbf q}
+\mathbf K\mathbf q=\mathbf f(t).
$$

Le modal resout $\mathbf K\boldsymbol\phi=\omega^2\mathbf M\boldsymbol\phi$.
Newmark et l'harmonique reutilisent exactement les matrices condensees
documentees dans la page suivante.

