---
doc_id: DOC-ELEM-TET4-07
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET4 - De la formulation forte a la formulation faible

## 1. Probleme continu

On considere un solide elastique occupant le domaine ouvert
$\Omega\subset\mathbb R^3$, de frontiere
$\partial\Omega=\Gamma_u\cup\Gamma_t$, avec
$\Gamma_u\cap\Gamma_t=\varnothing$. L'inconnue est le deplacement
$\mathbf u:\Omega\rightarrow\mathbb R^3$.

La formulation forte de l'equilibre quasi-statique est

$$
-\nabla\cdot\boldsymbol\sigma(\mathbf u)=\mathbf b
\qquad\text{dans }\Omega,
$$

avec les conditions aux limites

$$
\mathbf u=\overline{\mathbf u}\quad\text{sur }\Gamma_u,
\qquad
\boldsymbol\sigma\mathbf n=\overline{\mathbf t}
\quad\text{sur }\Gamma_t.
$$

Pour les petites deformations :

$$
\boldsymbol\varepsilon(\mathbf u)
=\frac12\left(\nabla\mathbf u+\nabla\mathbf u^T\right),
\qquad
\boldsymbol\sigma=\mathbb C:\boldsymbol\varepsilon.
$$

La loi isotrope est definie positive si $E>0$ et $-1<\nu<1/2$. La limite
$\nu\rightarrow1/2$ est mathematiquement admissible pour le continu mais
provoque le verrouillage volumique du TET4 deplacement.

## 2. Espaces admissibles

L'espace cinematiquement admissible et l'espace des variations sont

$$
\mathcal U=
\left\{\mathbf u\in[H^1(\Omega)]^3:
\mathbf u=\overline{\mathbf u}\text{ sur }\Gamma_u\right\},
$$

$$
\mathcal V=
\left\{\mathbf v\in[H^1(\Omega)]^3:
\mathbf v=\mathbf0\text{ sur }\Gamma_u\right\}.
$$

Le choix $H^1$ exige des deplacements continus mais autorise des gradients
discontinus entre elements. C'est exactement le comportement d'un assemblage
TET4 conforme : $\mathbf u_h$ est $C^0$ et les contraintes sont constantes
par element, donc generalement discontinues aux faces.

## 3. Passage a la formulation faible

On multiplie l'equilibre par une variation $\mathbf v\in\mathcal V$, puis on
integre sur $\Omega$ :

$$
-\int_\Omega\mathbf v\cdot
\left(\nabla\cdot\boldsymbol\sigma\right)\,d\Omega
=\int_\Omega\mathbf v\cdot\mathbf b\,d\Omega.
$$

L'identite de Green donne

$$
\int_\Omega
\boldsymbol\varepsilon(\mathbf v):\boldsymbol\sigma(\mathbf u)\,d\Omega
=
\int_\Omega\mathbf v\cdot\mathbf b\,d\Omega
+\int_{\Gamma_t}\mathbf v\cdot\overline{\mathbf t}\,d\Gamma.
$$

La formulation faible consiste donc a trouver $\mathbf u\in\mathcal U$ tel
que, pour tout $\mathbf v\in\mathcal V$,

$$
a(\mathbf v,\mathbf u)=\ell(\mathbf v),
$$

$$
a(\mathbf v,\mathbf u)=
\int_\Omega\boldsymbol\varepsilon(\mathbf v):
\mathbb C:\boldsymbol\varepsilon(\mathbf u)\,d\Omega,
$$

$$
\ell(\mathbf v)=
\int_\Omega\mathbf v\cdot\mathbf b\,d\Omega+
\int_{\Gamma_t}\mathbf v\cdot\overline{\mathbf t}\,d\Gamma.
$$

La symetrie majeure de $\mathbb C$ implique la symetrie de $a$. Sous des
blocages supprimant les mouvements rigides, l'inegalite de Korn assure la
coercivite et donc l'unicite du probleme lineaire.

## 4. Sous-espace discret TET4

Sur un tetraedre $\Omega_e$, les fonctions barycentriques lineaires sont

$$
N_a(\mathbf x)=\alpha_a+\beta_ax+\gamma_ay+\delta_az,
\qquad a=1,\ldots,4.
$$

L'approximation est

$$
\mathbf u_h(\mathbf x)=
\sum_{a=1}^4N_a(\mathbf x)\mathbf d_a
=\mathbf N(\mathbf x)\mathbf d_e.
$$

Les gradients $\nabla N_a$ sont constants. En notation de Voigt a
cisaillements d'ingenieur,

$$
\boldsymbol\varepsilon_h=\mathbf B_e\mathbf d_e,
$$

avec $\mathbf B_e$ constante. L'insertion dans la forme bilineaire conduit a

$$
\mathbf K_e
=\int_{\Omega_e}\mathbf B_e^T\mathbf D\mathbf B_e\,d\Omega
=V_e\mathbf B_e^T\mathbf D\mathbf B_e.
$$

Cette egalite explique a la fois l'efficacite du TET4 et ses limites : un seul
etat de deformation est disponible dans chaque element.

## 5. Charges coherentes

Une force volumique constante produit

$$
\mathbf f_e^{\,b}
=\int_{\Omega_e}\mathbf N^T\mathbf b\,d\Omega
=\frac{V_e}{4}
\begin{bmatrix}\mathbf b\\\mathbf b\\\mathbf b\\\mathbf b\end{bmatrix}.
$$

Sur une face triangulaire de sommets $i,j,k$ et de traction constante,

$$
\mathbf f_{e,i}^{\,t}
=\mathbf f_{e,j}^{\,t}
=\mathbf f_{e,k}^{\,t}
=\frac{A_f}{3}\overline{\mathbf t}.
$$

Ces expressions conservent la resultante et le premier moment. Une pression
$p$ utilise $\overline{\mathbf t}=-p\mathbf n$ avec la normale de face
orientee vers l'exterieur.

## 6. Consistance et convergence

La partition de l'unite et la reproduction lineaire donnent

$$
\sum_aN_a=1,
\qquad
\sum_aN_a\mathbf x_a=\mathbf x.
$$

Le TET4 reproduit donc exactement les translations, rotations infinitesimales
et champs de deplacement affines. Cette propriete est necessaire au patch
test de contrainte constante, mais elle n'assure pas seule une bonne
convergence en flexion ou pres d'un gradient de contrainte.

Pour une famille reguliere de maillages et une solution suffisamment lisse,
l'erreur d'energie attendue est d'ordre $O(h)$ et l'erreur $L^2$ de
deplacement d'ordre $O(h^2)$. Ces ordres sont asymptotiques; les singularites,
les tetraedres aplatis et l'incompressibilite les degradent.

## 7. Residus et estimateurs elementaires

Le residu fort dans un TET4 sans force volumique variable est

$$
\mathbf r_e=\mathbf b+\nabla\cdot\boldsymbol\sigma_h.
$$

Comme $\boldsymbol\sigma_h$ est constante,
$\nabla\cdot\boldsymbol\sigma_h=\mathbf0$ dans l'interieur. L'information
d'erreur provient alors principalement des sauts de traction entre elements :

$$
\mathbf j_f=
\boldsymbol\sigma_h^+\mathbf n^+
+\boldsymbol\sigma_h^-\mathbf n^-.
$$

Une contrainte nodale lissee ne remplace pas ce controle et ne doit jamais
etre interpretee comme une nouvelle solution EF.

## 8. Matrice minimale de tests

| ID | Preuve | Observable | Critere |
| --- | --- | --- | --- |
| TET4-FW-01 | Partition de l'unite | $\sum N_a$ | erreur `< 1e-14` |
| TET4-FW-02 | Reproduction affine | $\mathbf u_h-\mathbf u$ | erreur `< 1e-12` |
| TET4-FW-03 | Translation rigide | $\mathbf K_e\mathbf d$ | norme `< 1e-10` |
| TET4-FW-04 | Rotation rigide | energie | `< 1e-10` |
| TET4-FW-05 | Patch contrainte constante | $\sigma_{xx},\sigma_{xy}$ | erreur `< 1e-10` |
| TET4-FW-06 | Charge volumique | force et moment | conservation `< 1e-12` |
| TET4-FW-07 | Pression de face | force et moment | conservation `< 1e-12` |
| TET4-FW-08 | Energie | $2U-\mathbf u^T\mathbf f$ | relatif `< 1e-9` |
| TET4-FW-09 | Raffinement | norme energie | pente coherente avec $O(h)$ |
| TET4-FW-10 | Incompressibilite | conditionnement/erreur | limite documentee |

## 9. Exemple reproductible

```powershell
python .\qf_solver.py solve --input .\examples\tet4_static.json `
  --output .\results\tet4_formulation_faible.json
python -m pytest tests\unit\test_tet4_element.py `
  tests\verification\test_meshed_benchmarks.py
```

Le rapport doit contenir volume oriente, residu libre, energie, reactions,
deplacement maximal et controles de maillage.

## 10. Limites et references

- formulation deplacement, donc verrouillage volumique pres de $\nu=0.5$;
- deformation et contrainte constantes par element;
- flexion et gradients de contrainte exigeant un raffinement important;
- aucune convergence ponctuelle revendiquee sur une singularite;
- qualite du maillage obligatoire avant resolution.

References : `REF-FEM-BATHE`, `REF-SOLID-INDUSTRIAL`, code
`solveur/elements/solid/tet4.py`, exigences `REQ-SOL-001`,
`REQ-MESH-001` et `REQ-CMP-003`.
