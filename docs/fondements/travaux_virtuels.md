---
doc_id: DOC-FEM-001
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Hypotheses et travaux virtuels

## Hypotheses communes

Le perimetre lineaire suppose une geometrie de reference fixe, de petites
deformations, des lois constitutives locales et un chargement quasi-statique
ou dynamique lineaire. Les equations sont exprimees en SI dans le perimetre
qualifiable.

Pour un solide elastique de domaine $\Omega$, le principe des travaux virtuels
s'ecrit:

$$
\int_\Omega \delta\boldsymbol\varepsilon^T\boldsymbol\sigma\,d\Omega
=\int_\Omega \delta\mathbf u^T\mathbf b\,d\Omega
+\int_{\Gamma_t}\delta\mathbf u^T\bar{\mathbf t}\,d\Gamma
+\delta\mathbf u^T\mathbf f_n.
$$

Avec $\mathbf u\simeq\mathbf N\mathbf q$, $\delta\boldsymbol\varepsilon
=\mathbf B\delta\mathbf q$ et $\boldsymbol\sigma=\mathbf D\mathbf B\mathbf q$:

$$
\mathbf K_e=\int_{\Omega_e}\mathbf B^T\mathbf D\mathbf B\,d\Omega,
\qquad
\mathbf f_e=\int_{\Omega_e}\mathbf N^T\mathbf b\,d\Omega
+\int_{\Gamma_e}\mathbf N^T\bar{\mathbf t}\,d\Gamma.
$$

Cette equation explique pourquoi les charges reparties doivent etre integrees
avec les memes fonctions de forme que le deplacement: elles sont
energetiquement coherentes, pas simplement partagees entre noeuds.

## Dynamique

Le probleme semi-discret devient:

$$
\mathbf M\ddot{\mathbf u}+\mathbf C\dot{\mathbf u}
+\mathbf K\mathbf u=\mathbf f(t).
$$

La matrice de masse est coherente par defaut. L'amortissement disponible est
de Rayleigh, $\mathbf C=\alpha\mathbf M+\beta_R\mathbf K$; il doit etre
identifie sur une plage de frequences et non choisi pour stabiliser
artificiellement une reponse.

## Non-lineaire

Le residu est $\mathbf r(\mathbf u)=\mathbf f_{ext}-\mathbf f_{int}(\mathbf u)$.
La resolution cherche $\mathbf r=\mathbf0$ avec une tangente materielle. Les
formulations disponibles restent en petits deplacements; elles ne representent
pas une non-linearite geometrique generale.
