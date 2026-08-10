---
doc_id: DOC-ELEM-000
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Elements finis disponibles

## BEAM2

Poutre droite de Timoshenko 3D a deux noeuds et six DDL par noeud. Le noyau
initial couvre traction, torsion, flexion biaxiale, cisaillement transverse,
masse coherente et efforts nodaux locaux. Sa maturite reste `experimental`
jusqu'a fermeture de la campagne P7.1.

## Entites discretes

Les ressorts au sol ou entre deux noeuds et les masses nodales excentrees sont
disponibles en statique et dynamique lineaires. Leurs matrices sont assemblees
directement dans les DDL actifs, sans materiau artificiel.

## Liaisons MPC et RBE

Les contraintes multipoints sont eliminees par transformation affine en
statique lineaire. Les liaisons `RBE2` rigides et `RBE3` ponderees sont
documentees avec leurs limites dans [MPC et RBE](liaisons_mpc_rbe.md).

## Contact unilateral

Le contact est un chemin `experimental` borne a un noeud esclave face a un
triangle maitre, en petits deplacements et statique lineaire. La fermeture
normale est resolue par active-set et multiplicateurs de Lagrange; une
regularisation de Coulomb permet en plus les etats d'adhesion et de
glissement. Voir [Contact sans frottement](contact_sans_frottement.md) et
[Contact avec frottement](contact_avec_frottement.md).

| Element | Modele | Ddl/noeud | Integration principale | Maturite |
| --- | --- | ---: | --- | --- |
| TET4 | Solide 3D lineaire | 3 | Exacte, deformation constante | `stable` en statique lineaire |
| TET10 | Solide 3D quadratique | 3 | Hammer-4 droit, Duffy-64 courbe, masse Duffy-125 | `stable_after_reinforced_tests` en lineaire |
| MITC4 | Coque Reissner-Mindlin | 6 | $2\times2$ et tying MITC | `stable` en statique lineaire |
| MITC3+ | Coque triangulaire Reissner-Mindlin | 6 | Tying MITC et bulle condensee | `experimental` |
| BEAM2 | Poutre de Timoshenko 3D | 6 | Forme fermee | `experimental` |
| Ressort/masse | Entite discrete | 1 a 6 | Assemblage nodal | `experimental` |
| MPC/RBE | Liaison cinematique | variable | Elimination affine | `experimental` |
| Contact normal/tangent | Noeud-triangle unilateral | translations | Active-set Lagrange + Coulomb regularise | `experimental` |

Le choix de l'element est une hypothese de modelisation. Une maille plus fine
ne corrige pas automatiquement une cinematique inadaptee, une singularite ou
un comportement materiau absent.

## Questions avant selection

- Le champ attendu est-il volumique, surfacique ou domine par la flexion ?
- L'epaisseur est-elle petite devant les autres dimensions ?
- Le materiau approche-t-il l'incompressibilite ?
- Les contraintes locales ou seulement les resultantes sont-elles requises ?
- Une reference ou une etude de convergence existe-t-elle pour cette famille ?

Les pages suivantes decrivent les equations effectivement codees, et non une
definition generique de manuel.

## Parcours de formulation

Chaque famille possede une page de derivation continue, a lire apres les
chapitres courts : [TET4](tet4/formulation_complete.md),
[TET10](tet10/formulation_complete.md) et
[MITC4](mitc4/formulation_complete.md). Elles relient hypotheses, equations,
code, tests et demonstrations maillees. Le futur triangle de coque est defini
dans la [documentation MITC3+](mitc3.md) et son
[plan de mise en place](mitc3_plan_implementation.md).
