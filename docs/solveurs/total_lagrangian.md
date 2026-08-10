---
doc_id: DOC-SOL-009
revision: 0.1
status: research
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET4 total lagrangien

<span class="maturity research">research</span>

Cette page fige la formulation choisie pour commencer la non-linearite
geometrique. Le noyau reste separe du TET4 petites deformations et n'est pas
encore expose dans l'API de resolution.

## Configuration et mesures

Les coordonnees de reference sont notees $\mathbf X$ et les coordonnees
courantes $\mathbf x=\mathbf X+\mathbf u$. Le gradient de deformation est

$$
\mathbf F=\frac{\partial\mathbf x}{\partial\mathbf X}
=\mathbf I+\sum_a \mathbf u_a\otimes\nabla_X N_a.
$$

La deformation de Green-Lagrange et la contrainte de Piola-Kirchhoff 2 sont

$$
\mathbf E=\frac12(\mathbf F^T\mathbf F-\mathbf I),\qquad
\mathbf S=\lambda\,\mathrm{tr}(\mathbf E)\mathbf I+2\mu\mathbf E.
$$

La loi Saint-Venant-Kirchhoff est hyperelastique et objective, mais elle n'est
pas adaptee aux tres grandes deformations de nombreux materiaux reels. Elle est
retenue comme formulation de verification des grandes rotations et de la
tangente, pas comme loi universelle.

## Force interne et tangente

Avec $\mathbf P=\mathbf F\mathbf S$ et le volume de reference $V_0$,

$$
\mathbf f_a^{int}=V_0\,\mathbf P\nabla_XN_a.
$$

La tangente consistante utilise

$$
\frac{\partial P_{iJ}}{\partial F_{kL}}
=\delta_{ik}S_{LJ}+F_{iI}\,\mathbb C_{IJKL}\,F_{kK}.
$$

Le premier terme est geometrique; le second est materiel. Cette separation est
verifiee par differences finies sur un etat combinant extension et cisaillement.

## Premiers controles automatiques

- tangente a l'origine identique au TET4 lineaire;
- rotation rigide de `73 deg` sans force interne ni energie;
- extension homogene finie comparee a l'energie analytique;
- tangente consistante comparee par differences finies;
- rejet d'une configuration courante inversee.

## Assemblage vectorise

La geometrie de reference est immuable en formulation totale lagrangienne. Les
volumes $V_0$, gradients $\nabla_XN_a$, indices de DDL et indices creux sont
donc calcules une seule fois. Pour tous les elements, QF_solver evalue ensuite
par lots :

$$
F_{iJ}^{(e)}=\delta_{iJ}+\sum_a u_{ai}^{(e)}N_{a,J}^{(e)},
\qquad
f_{ai}^{(e)}=V_0^{(e)}P_{iJ}^{(e)}N_{a,J}^{(e)}.
$$

La tangente locale reste exactement la tangente consistante du noyau scalaire.
Des tests comparent force, energie et matrice assemblee entre les deux chemins.

## Campagne multi-elements

`VNV-TET4-TL-ASSEMBLY-002` couvre six maillages de `192` a `24 000` TET4.
Patch affine, rotation rigide, residu Newton et positivite de `det(F)` passent.
La variation de fleche finale vaut `3,81 %` et l'ecart a l'elastica d'Euler
`6,91 %`. Le resultat assemble devient `PASS_ASSEMBLY`.

L'elastica utilise une poutre inextensible d'Euler-Bernoulli sous charge morte.
Elle ne represente ni le cisaillement transverse, ni les effets locaux 3D de
l'encastrement et du chargement.

## Reference elastica

Avec $\theta(s)$ la rotation de la fibre moyenne, $P$ la charge verticale morte
et $EI$ la rigidite de flexion, l'oracle resout

$$
\theta''(s)=\frac{P}{EI}\cos\theta(s),\qquad
\theta(0)=0,\qquad \theta'(L)=0.
$$

La geometrie deformee est reconstruite par

$$
x'(s)=\cos\theta(s),\qquad z'(s)=\sin\theta(s),qquad x(0)=z(0)=0.
$$

Le probleme aux limites est resolu independamment du maillage TET4. A faible
charge, il retrouve $z(L)=-PL^3/(3EI)$.

La sensibilite `3/6/10/12/24` increments montre que `6/10/12/24` atteignent la
meme fleche a `8,10e-16` relatif. Le minimum technique vaut `6`; la valeur
recommandee et la valeur par defaut valent `10`. La convergence lente observee
est donc spatiale.

La correlation Docker CalculiX `2.20` emploie exactement les memes C3D4,
blocages et charges. `*ELASTIC + NLGEOM` utilise Green-Lagrange et
Piola-Kirchhoff 2 selon le manuel CalculiX. L'ecart maximal de fleche vaut
`1,86e-7` relatif sur les six niveaux.

## Campagne structurelle V2

Le post-traitement expose maintenant, au point constant de chaque TET4, le
gradient de deformation, Green-Lagrange, PK2, Cauchy, l'energie volumique et
`det(F)`. Trois campagnes separent explicitement :

- le patch de contraintes et d'energie `VNV-TET4-TL-STRESS-005` ;
- le flambement linearise par tangente precontrainte
  `VNV-TET4-TL-BUCKLING-EULER-006` ;
- le suivi post-critique creux avec imperfections
  `VNV-TET4-TL-POSTBUCKLING-007`.

Les resultats, formulations et limites sont regroupes dans
[la campagne structurelle V2](../verification/tet4_total_lagrangian_structural_v2.md).
Ils restent candidats a une nouvelle revue mecanique.

## Limites avant integration

- charges mortes uniquement dans un premier temps;
- aucune pression suiveuse;
- aucun J2 en deformation finie;
- aucun contact; flambement et post-flambement restent au statut `research` ;
- pas de revendication engineering avant les benchmarks structurels et la
  revue mecanique.

## Contrat documentaire de la methode

| Rubrique exigee | Contenu et preuve |
| --- | --- |
| Geometrie et DDL | TET4 de reference, 4 noeuds et 12 translations. |
| Formulation mathematique | $F$, Green-Lagrange, Piola-Kirchhoff 2 et push-forward Cauchy. |
| Integration et algorithme | Total lagrangien, force/tangente, Newton incremental et assemblage vectorise. |
| Exemple executable | `python .\qf_solver.py solve --input .\examples\tet4_geometric_nonlinear_static.json --output .\results\tl.json` |
| Maillage, chargement et conditions limites | Cas unitaires/assemblages; charges mortes, minimum 6 increments, recommande 10. |
| Tableau de resultats et figure | Rapports V&V et [deformees structurelles](../verification/tet4_total_lagrangian_structural_v2.md). |
| Invariants | Objectivite, tangente, energie, equilibre et contraintes finies. |
| Convergence | Raffinement, increments et correlations CalculiX/Code_Aster. |
| Limites et references | Statut research; `REF-FEM-BATHE`, exigences TL. |

Owner review documentaire requise; cette page n'etend aucune decision.
