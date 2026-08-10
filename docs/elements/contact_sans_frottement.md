---
doc_id: DOC-ELEM-CONTACT-001
revision: 0.3
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Contact unilateral sans frottement

## Perimetre V1

Cette premiere implementation traite un contact **noeud esclave - triangle
maitre** en statique lineaire, petites transformations. Elle est classee
`experimental`. Elle sert a verifier le chemin numerique et les conventions
de signe; elle ne remplace pas encore une formulation de contact surface a
surface a grands glissements.

Le triangle maitre est defini par trois noeuds globaux ordonnes. Le noeud
esclave doit se projeter strictement dans ce triangle a l'etat initial. Par
defaut la normale est figee pendant tout le calcul. Le mode experimental
`contact_search_mode="updated"` est la seule exception bornee : il reconstruit
la facette et la normale entre deux resolutions, sans frottement. Il n'y a ni
grand glissement, ni contact surface-surface, ni usure.

Une surface maitre bornee peut aussi etre fournie par `master_faces`, une liste
de triangles explicites. QF_solver retient alors la facette dont la projection
initiale est compatible et dont la distance normale est minimale; l'index de
la face retenue est publie dans l'audit. La selection n'est pas recalculee
apres deformation par defaut. Le mode experimental
`contact_search_mode="updated"` reevalue facette et normale a partir de la
position courante, jusqu'a stabilisation. Il est limite aux petites
translations, sans frottement; il ne constitue pas une formulation de grand
glissement ou surface-surface.

## Geometrie, gap et signe

Soient $x_s$ le noeud esclave, $x_i$ les trois noeuds maitres, $n$ la normale
unitaire du triangle et $b_i$ les coordonnees barycentriques de la projection
initiale. Le gap normal est :

$$
g(u)=g_0+n^T\left(u_s-\sum_{i=1}^{3}b_i u_i\right),
\qquad
g_0=n^T\left(x_s-\sum_{i=1}^{3}b_i x_i\right).
$$

Le vecteur global $B$ est tel que $g(u)=g_0+Bu$. La convention est :

- $g>0$ : separation;
- $g=0$ : contact ferme;
- $g<0$ : penetration interdite;
- $p=-\lambda\geq0$ : pression compressive.

La paire de contact respecte les conditions de Kuhn-Tucker :

$$
g\geq0,\qquad p\geq0,\qquad gp=0.
$$

Elles sont publiees dans l'audit sous la forme gap, pression, statut actif et
residu de complementarite. La force de contact est $\lambda B^T$ : elle est
dirigee vers le maitre sur l'esclave et repartie sur les noeuds maitres selon
les poids barycentriques. Son torseur est donc equilibre pour cette paire.

## Resolution active-set

Les blocages de Dirichlet sont d'abord elimines par la meme transformation
affine que les MPC. Pour un ensemble actif $A$, QF_solver resout exactement :

$$
\begin{bmatrix}
K_r & B_A^T\\
B_A & 0
\end{bmatrix}
\begin{bmatrix}z\\\lambda_A\end{bmatrix}
=
\begin{bmatrix}f_r\\-g_0-Bu_0\end{bmatrix}.
$$

Un contact est ajoute s'il penetre; il est retire si sa pression devient
tensile. L'iteration s'arrete lorsque l'ensemble actif ne change plus. Une
matrice selle singuliere, une solution non finie ou le nombre maximal
d'iterations atteint leve `NumericalConvergenceError`.

## Exemple executable

Le fichier `examples/frictionless_contact_plane.json` comprend un noeud au-dessus
d'un plan triangulaire, un ressort normal et une
charge de compression. Il montre une fermeture a $g=0$ avec une pression
positive. Remplacer la charge par une traction laisse le contact inactif.

```powershell
python .\qf_solver.py solve --input .\examples\frictionless_contact_plane.json --output .\results\contact.json
```

## Controles et limites

Le lecteur JSON et `check-mesh` refusent : projection hors triangle, triangle
degenere, indices invalides, methode iterative, analyse autre que
`linear_static`, et combinaison avec MPC/RBE. Les directions tangentielles
libres doivent etre physiquement stabilisees par le modele : un contact sans
frottement ne les bloque pas.

Sont hors scope : contact surface-surface, face maitre EF deformable
generalisee, grandes rotations, grande penetration, changement de normale,
non-lineaire materiau, dynamique et modal. Plusieurs paires noeud-triangle
fixes sont couvertes par le test de coin. Un triangle a noeuds maitres
elastiques est aussi verifie par `VNV-CONTACT-DEFORMABLE-MASTER-003`. Une
face frontiere TET4 deformable est maintenant soumise a une preuve interne
independante de compliance dans `VNV-CONTACT-TET4-MASTER-FACE-004`: le
deplacement normal barycentrique, le gap et la pression sont retrouves au
seuil machine. Ces preuves bornees ne constituent pas une formulation de face
EF generalisee. La convergence
interne d'une structure TET4 est desormais couverte par
`VNV-CONTACT-TET4-STRUCTURAL-001`. La correlation externe de la loi normale
equivalente est obtenue par Code_Aster `LIAISON_UNIL` dans
[`VNV-CONTACT-CODEASTER-LIAISON-UNIL-001`](../verification/contact_code_aster_vnv.md).
Elle confirme le cas discret ouverture/fermeture, sans changer le statut
`experimental`: les geometries de contact plus variees, les faces EF
deformables generalisees et les correlations externes associees restent a
verifier. Une correlation distincte de l'etat actif d'une face TET4 est
desormais disponible dans `VNV-CONTACT-CODEASTER-TET4-MASTER-004`: elle
utilise la meme raideur solide et l'equation barycentrique imposee avec
`LIAISON_DDL`. La detection active-set reste prouvee separement par
`LIAISON_UNIL`.

Le mode optionnel `contact_search_mode="updated"` reconstitue la facette et
sa normale a partir d'une configuration deplacement bornee, sans frottement.
`VNV-CONTACT-MASTER-SURFACE-005` couvre une commutation sur deux triangles
plans puis sur deux triangles plies : la seconde normale et le gap final sont
verifies analytiquement. Cette preuve reste interne. Elle n'autorise ni grand
glissement, ni topologie de contact variable, ni contact surface-surface.

Les trois orientations cartesianes d'un meme triangle et d'une meme charge
normale sont aussi testees. Elles restituent chacune un gap nul, une pression
de `100 N` et un deplacement normal de `-0.1 m`. Un coin orthogonal a deux
triangles maitres verifies aussi deux ensembles actifs simultanes : les
reactions analytiques `100 N` et `200 N` sont retrouvees. Ces tests
renforcent le controle de la normale geometrique figee et de l'active-set;
ils ne transforment pas les triangles maitres en faces deformables et ne
changent donc pas le statut de la fonction.

La formulation est reliee a `REQ-CONTACT-001`, `FORM-CONTACT-001` et aux
tests `tests/unit/test_frictionless_contact.py`,
`tests/verification/test_frictionless_contact_structural_vnv.py` et
`tests/verification/test_contact_deformable_master_vnv.py`,
`tests/verification/test_contact_tet4_master_vnv.py` et
`tests/verification/test_contact_master_surface_vnv.py`.

## Contrat documentaire et demonstration

| Rubrique exigee | Contenu et preuve |
| --- | --- |
| Geometrie et DDL | Noeud esclave, triangle/surface maitre, translations et normale orientee. |
| Formulation mathematique | Gap signe, Kuhn-Tucker et reaction normale compressive. |
| Integration et algorithme | Projection barycentrique et active-set borne. |
| Exemple executable | `python .\qf_solver.py solve --input .\examples\frictionless_contact_surface.json --output .\results\contact.json` |
| Maillage | Surface triangulee et assemblages TET4 structurels. |
| Chargement et conditions limites | Compression et supports supprimant les modes rigides. |
| Tableau de resultats | [Rapport V&V](../verification/contact_structurel_tet4_vnv.md). |
| Figure de deformee | Maillage initial, contact actif et deformee ci-dessous. |
| Invariants | $g_n\ge0$, $p_n\ge0$, $g_np_n=0$, equilibre et absence de traction. |
| Convergence | Raffinements et correlation Code_Aster jusqu'a environ 10 000 TET4. |
| Limites | Petites transformations, recherche bornee, pas de grand glissement. |
| References | `FORM-CONTACT-001`, `REQ-CONTACT-001` et manifestes V&V. |

![Deformee de contact generee](../assets/generated/contact_structural_deformation.png){ .result-figure }

Le scope borne conserve son Owner review existante; cette synthese ne change
pas son perimetre.
