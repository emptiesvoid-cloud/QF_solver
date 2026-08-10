---
doc_id: DOC-ELEM-TET10-07
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET10 - Formulation forte, faible et isoparametrique

## 1. Probleme continu

Le TET10 discretise le meme probleme d'elasticite tridimensionnelle que le
TET4 :

$$
-\nabla\cdot\boldsymbol\sigma=\mathbf b\quad\text{dans }\Omega,
\qquad
\boldsymbol\sigma=\mathbb C:\boldsymbol\varepsilon(\mathbf u).
$$

Les conditions essentielles sont imposees sur $\Gamma_u$ et les tractions
$\boldsymbol\sigma\mathbf n=\overline{\mathbf t}$ sur $\Gamma_t$.

## 2. Formulation faible

Trouver $\mathbf u\in\mathcal U$ tel que, pour toute variation
$\mathbf v\in\mathcal V$,

$$
\int_\Omega
\boldsymbol\varepsilon(\mathbf v):\mathbb C:
\boldsymbol\varepsilon(\mathbf u)\,d\Omega
=
\int_\Omega\mathbf v\cdot\mathbf b\,d\Omega
+\int_{\Gamma_t}\mathbf v\cdot\overline{\mathbf t}\,d\Gamma.
$$

Le TET10 est conforme dans $[H^1]^3$ : les deplacements sont continus aux
faces, mais les gradients et contraintes peuvent rester discontinus.

## 3. Interpolation quadratique

Dans le tetraedre de reference, les coordonnees barycentriques verifient
$L_1+L_2+L_3+L_4=1$. Les dix fonctions sont

$$
N_i=L_i(2L_i-1),\quad i=1,\ldots,4,
$$

$$
N_{ij}=4L_iL_j
\quad\text{pour les six aretes}.
$$

La geometrie et le deplacement emploient les memes fonctions :

$$
\mathbf x(\boldsymbol\xi)=\sum_{a=1}^{10}N_a\mathbf x_a,
\qquad
\mathbf u_h(\boldsymbol\xi)=\sum_{a=1}^{10}N_a\mathbf d_a.
$$

Cette construction isoparametrique represente exactement une geometrie
affine et approxime les faces/aretes courbes par des polynomes quadratiques.

## 4. Jacobien et gradients physiques

Le Jacobien est

$$
\mathbf J(\boldsymbol\xi)
=\frac{\partial\mathbf x}{\partial\boldsymbol\xi}
=\sum_a\mathbf x_a\otimes\nabla_\xi N_a.
$$

Les gradients physiques sont obtenus par

$$
\nabla_xN_a=\mathbf J^{-T}\nabla_\xi N_a.
$$

Contrairement au TET4, $\mathbf J$, $\det\mathbf J$ et $\mathbf B$ peuvent
varier dans l'element. Un Jacobien positif aux seuls sommets n'est pas une
preuve suffisante pour une geometrie fortement courbe; les points de
quadrature et des points geometriques supplementaires doivent etre controles.

## 5. Forme discrete

La rigidite elementaire est

$$
\mathbf K_e
=\int_{\widehat\Omega}
\mathbf B^T(\boldsymbol\xi)\mathbf D\mathbf B(\boldsymbol\xi)
\det\mathbf J(\boldsymbol\xi)\,d\widehat\Omega.
$$

La masse coherente vaut

$$
\mathbf M_e
=\int_{\widehat\Omega}
\rho\mathbf N^T\mathbf N
\det\mathbf J\,d\widehat\Omega.
$$

Les deux integrales sont evaluees par quadrature tetraedrique. Le choix de
regle doit etre trace car un sous-calcul peut introduire des modes parasites
et un sur-calcul augmente le cout sans corriger une geometrie invalide.

## 6. Charges de face quadratiques

Sur une face a six noeuds,

$$
\mathbf f_e^t=
\int_{\widehat\Gamma}
\mathbf N_\Gamma^T\overline{\mathbf t}
J_\Gamma\,d\widehat\Gamma.
$$

Pour une pression, la normale et le Jacobien surfacique sont evalues a chaque
point. Les noeuds medians rendent la repartition nodale non uniforme, mais la
resultante et le moment doivent rester conserves.

## 7. Consistance et ordres attendus

Le TET10 reproduit exactement tout champ affine sur une geometrie affine. Il
peut aussi reproduire un champ quadratique compatible avec son espace
d'interpolation, mais les contraintes associees et leur integration dependent
du mapping.

Sur une famille reguliere et pour une solution lisse, l'erreur d'energie
attendue est $O(h^2)$ et l'erreur de deplacement $L^2$ est $O(h^3)$. Les
geometries courbes mal placees, Jacobians proches de zero et singularites
degradent ces ordres.

## 8. Recuperation et projection

Les contraintes sont evaluees aux points de Gauss :

$$
\boldsymbol\sigma_g=\mathbf D\mathbf B_g\mathbf d_e.
$$

Une extrapolation vers les noeuds est un post-traitement. Elle doit publier
sa matrice, son conditionnement et la methode de moyennage entre elements.
La verification accepte d'abord les contraintes aux points d'integration,
plus proches de la formulation variationnelle.

## 9. Matrice minimale de tests

| ID | Preuve | Critere |
| --- | --- | --- |
| TET10-FW-01 | Kronecker aux dix noeuds | `< 1e-14` |
| TET10-FW-02 | Partition de l'unite | `< 1e-14` |
| TET10-FW-03 | Reproduction affine oblique | `< 1e-11` |
| TET10-FW-04 | Champ quadratique | erreur conforme a la quadrature |
| TET10-FW-05 | Six modes rigides | valeurs propres proches de zero |
| TET10-FW-06 | Jacobien courbe | positif sur tous les points controles |
| TET10-FW-07 | Masse totale | erreur `< 1e-10` |
| TET10-FW-08 | Pression quadratique | force/moment conserves |
| TET10-FW-09 | Convergence structurelle | pente $O(h^2)$ en energie attendue |
| TET10-FW-10 | Correlation C3D10 | observables hors singularites |

## 10. Exemple et limites

```powershell
python .\qf_solver.py solve --input .\examples\tet10_static.json `
  --output .\results\tet10_formulation_faible.json
python -m pytest tests\unit\test_tet10_element.py `
  tests\verification\test_tet10_geometry_quadrature_vnv.py
```

Limites : ordre des noeuds medians strict, geometries courbes a controler,
cout de quadrature/assemblage eleve, contraintes ponctuelles singulieres non
acceptables et verrouillage volumique a etudier pres de l'incompressibilite.

References : `REF-FEM-BATHE`, `REF-SOLID-INDUSTRIAL`, code
`solveur/elements/solid/tet10.py`, exigences `REQ-SOL-003`,
`REQ-MESH-001` et `REQ-CMP-003`.
