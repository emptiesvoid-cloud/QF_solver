---
doc_id: DOC-PLAN-MITC3-001
revision: 0.1
status: planned
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# Plan de mise en place du MITC3+

## 1. Objectif

Ajouter a QF_solver une coque triangulaire a trois noeuds afin de traiter :

- les maillages surfaciques non structures produits par Gmsh ou un remailleur ;
- les fermetures et transitions topologiques impossibles en quadrangles purs ;
- les coques facettisees comportant simultanement des triangles et des
  quadrangles ;
- les analyses isotropes puis multicouches deja accessibles au MITC4.

Le type saisi dans les modeles sera `MITC3`. La formulation visee est le
`MITC3+` lineaire de Lee, Lee et Bathe, et non un triangle constant obtenu en
decoupant artificiellement un MITC4.

La parite fonctionnelle visee comprend a terme :

| Capacite | Cible MITC3 |
| --- | --- |
| Statique lineaire isotrope | V1, premier scope accepte |
| Charges distribuees | V1 |
| Post-traitement faces superieure/inferieure | V1 |
| Masse coherente et modal | V1 apres statique |
| Newmark lineaire | V1 apres modal |
| Harmonique direct et modal | V1 apres modal |
| Stratifies `shell_laminate` | V1 experimental |
| Gmsh TRI3 et maillages mixtes TRI3/QUAD4 | V1 |
| Grandes rotations, flambement et post-flambement | V2/research |
| Dommage, delaminage et contact entre plis | Hors scope |

## 2. Decision de formulation

### 2.1 Pourquoi MITC3+

Le MITC3 historique est economique, mais son comportement en flexion et sur
maillages distordus n'offre pas la meme robustesse que MITC4. Le MITC3+
enrichit les rotations par une fonction bulle cubique interne et construit un
champ de cisaillement transverse suppose. Les deux parametres internes sont
condenses au niveau elementaire : le systeme global conserve trois noeuds,
six DDL par noeud et une matrice de taille `18 x 18`.

Cette option est retenue parce qu'elle :

- conserve la compatibilite lineaire le long des trois aretes ;
- cible explicitement la reduction du shear locking ;
- ne cree pas de noeud ou de DDL global supplementaire ;
- possede une litterature de formulation et de benchmarks identifiable ;
- permet une comparaison directe avec MITC4 sans pretendre a leur identite.

### 2.2 Cinematique

Chaque noeud porte :

```text
UX, UY, UZ, RX, RY, RZ
```

Dans le repere local `(e1, e2, e3)`, le deplacement Reissner-Mindlin est ecrit
schematiquement :

```text
u(xi, eta, z) = u0(xi, eta) + z * theta(xi, eta) x e3
```

Les translations de la surface moyenne sont interpolees avec les trois
fonctions barycentriques lineaires. Les rotations tangentielles recoivent en
plus une bulle cubique nulle sur le contour :

```text
Nb = 27 * L1 * L2 * L3
```

La bulle n'altere donc pas la continuite inter-element le long des aretes.

### 2.3 Condensation locale

Avant condensation, les DDL sont repartis entre les 18 DDL nodaux `q` et les
deux amplitudes internes `a`. La rigidite locale est partitionnee :

```text
[ Kqq  Kqa ] [q] = [fq]
[ Kaq  Kaa ] [a]   [ 0]
```

Sous reserve que `Kaa` soit inversible, la rigidite assemblee est :

```text
Kcond = Kqq - Kqa * inv(Kaa) * Kaq
```

L'implementation utilisera une resolution lineaire de `Kaa`, jamais un inverse
explicite. La symetrie sera restauree uniquement a l'arrondi :

```text
Kcond = 0.5 * (Kcond + Kcond.T)
```

La preuve devra verifier que la condensation reproduit la reponse du systeme
elementaire enrichi non condense.

### 2.4 Cisaillement transverse suppose

Le cisaillement ne sera pas obtenu uniquement par l'interpolation compatible.
Un champ suppose MITC sera reconstruit a partir de valeurs de tying definies
sur les aretes et d'un mode interne associe a la bulle. Les equations exactes,
l'emplacement des points et la convention covariante seront recopies depuis
la publication primaire dans la specification de formulation avant codage.

Cette etape est bloquante : aucune approximation ad hoc ou reutilisation des
quatre tying points MITC4 n'est acceptee.

### 2.5 Membrane, flexion et drilling

La rigidite sera decomposee et auditable :

```text
K = Km + Kb + Ks + Kd
```

avec membrane, flexion, cisaillement transverse et stabilisation de drilling.
La stabilisation `Kd` devra :

- supprimer le mode local de rotation normale non physique ;
- ne pas polluer les cinq autres modes rigides ;
- rester inferieure a 1 % de l'energie totale sur les benchmarks acceptes ;
- faire l'objet d'une etude de sensibilite, sans recopier aveuglement le
  `drilling_scale` de MITC4.

Une formulation membrane triangulaire enrichie ou lissee ne sera ajoutee que
si les patch tests et les cas distordus montrent que le champ lineaire de base
est insuffisant. Ce changement devra etre une decision V&V explicite.

## 3. Architecture logicielle

### 3.1 Modules cibles

```text
solveur/
  elements/
    shell/
      common.py
      frames.py
      mitc3.py
      mitc3_condensation.py
      mitc4.py
  post/
    shell_results.py
  verification/
    mitc3_static.py
    mitc3_locking.py
    mitc3_dynamic.py
```

Le partage avec MITC4 sera limite aux operations reellement communes :

- construction et controle du repere local ;
- transformation des 6 DDL nodaux ;
- contrats materiau isotrope et stratifies ;
- utilitaires de resultantes et de contraintes par face ;
- conventions de serialisation.

Les interpolations, tying points, quadratures et condensations resteront dans
des modules MITC3. Aucun branchement `if node_count == 3` ne doit contaminer le
noyau MITC4 valide.

### 3.2 Contrats publics

Exemple JSON :

```json
{
  "elements": [
    {"type": "MITC3", "nodes": [0, 1, 2], "material": "skin"}
  ],
  "materials": {
    "skin": {
      "type": "shell_isotropic",
      "E": 70000000000.0,
      "nu": 0.3,
      "thickness": 0.002,
      "density": 2700.0
    }
  }
}
```

Le registre declarera :

```text
MITC3: 3 noeuds, SHELL_DOFS, shell_isotropic | shell_laminate
```

L'API publique existante `load_model -> check_mesh -> solve_model` ne changera
pas. Les anciens modeles MITC4 conserveront strictement leur comportement.

### 3.3 Import, charges et sorties

L'import Gmsh associera les triangles de surface d'ordre 1 au type `MITC3`.
Les groupes physiques devront fonctionner pour :

- blocages et charges nodales ;
- pression normale coherente ;
- traction surfacique globale ou locale ;
- traction lineique sur une arete ;
- gravite et force volumique equivalent surfacique.

Le post-traitement produira au minimum :

- resultantes membrane `N11`, `N22`, `N12` ;
- moments `M11`, `M22`, `M12` ;
- efforts tranchants `Q1`, `Q2` ;
- contraintes et deformations aux faces superieure et inferieure ;
- energie membrane, flexion, cisaillement et drilling ;
- pour les stratifies, contraintes/deformations dans les axes du pli aux
  positions lower/middle/upper.

## 4. Materiaux composites

MITC3 reutilisera `LaminateShellMaterial` et la theorie classique des
stratifies deja employee par MITC4 :

```text
[N]   [A B] [epsilon0]
[M] = [B D] [kappa  ]
```

La direction materiau globale sera projetee dans le plan de chaque triangle.
Un rejet explicite sera emis si cette direction est presque parallele a la
normale locale. Les rigidites de cisaillement transverse utiliseront `G13` et
`G23` avec la convention de correction documentee.

Le scope composite initial couvre :

- stratifies homogenes par zones ;
- epaisseur et empilement constants par element ;
- couplages `A/B/D` ;
- axes materiau variables par projection geometrique ;
- contraintes par pli hors singularites.

Il exclut :

- continuite automatique des axes sur une surface topologiquement ambigue ;
- delaminage, endommagement progressif et contact interlaminaire ;
- contrainte normale `S33` qualifiee ;
- rupture de pli utilisee comme critere de certification.

## 5. Validation du maillage

Le controle MITC3 devra mesurer :

- aire orientee et aire absolue ;
- longueur minimale et maximale des aretes ;
- aspect ratio et rayon inscrit/circonscrit ;
- angle minimal et maximal ;
- ecart a la planeite de la facette ;
- orientation coherente des normales entre triangles adjacents ;
- aretes libres, non-manifold et triangles dupliques ;
- compatibilite des aretes MITC3/MITC4 dans les maillages mixtes.

Valeurs de depart a confirmer par la campagne :

| Mesure | Engineering | Qualification |
| --- | --- | --- |
| Angle minimal | warning sous 20 deg | refus sous 15 deg |
| Angle maximal | warning au-dessus de 140 deg | refus au-dessus de 150 deg |
| Aspect ratio | warning au-dessus de 10 | refus au-dessus de 20 |
| Aire relative | warning sous `1e-8` | refus sous `1e-10` |
| Normales adjacentes | rapportees | refus si incoherence non voulue |

Ces seuils ne seront pas declares valides avant etude de sensibilite.

## 6. Plan de developpement

### Phase A - Specification executable

1. Ajouter les exigences `REQ-MITC3-*` et les references primaires.
2. Figer ordre nodal, repere, signes, tying points et quadratures.
3. Ecrire des oracles elementaires independants du code de production.
4. Ajouter des tests attendus en echec pour le registre, le JSON et le maillage.

Sortie : specification relue, sans calcul de production revendique.

### Phase B - Statique isotrope elementaire

1. Implementer repere, interpolations et matrices membrane/flexion.
2. Implementer cisaillement suppose et bulle.
3. Implementer condensation locale et drilling.
4. Ajouter pression, tractions, gravite et forces volumiques.
5. Integrer assemblage, API, CLI, JSON, VTU et audit.

Sortie : element `experimental`, utilisable seulement avec profil engineering.

### Phase C - V&V statique

1. Modes rigides et spectre de rigidite.
2. Patchs membrane, flexion, cisaillement et champ mixte.
3. Plaque mince en flexion, Cook, Scordelis-Lo et cylindre pince triangules.
4. Matrice de shear locking en epaisseur, raffinement et distorsion.
5. Comparaison MITC3/MITC4 sur geometrie et densite de maillage comparables.
6. Maillage mixte MITC3/MITC4 avec patch traversant l'interface.
7. Correlations Code_Aster/CalculiX sur maillage identique.

Sortie : Owner review du scope `mitc3-linear-static`.

### Phase D - Masse et dynamique

1. Implementer une masse coherente avec inerties translationnelles et
   rotatoires physiques.
2. Traiter les directions sans masse par condensation/reconstruction.
3. Verifier masse totale, centre de masse, inertie, symetrie et positivite.
4. Ajouter modal, Newmark puis harmonique.
5. Rejouer les cas MITC4 equivalents avec maillages triangules.

Sortie : scopes dynamiques revus separement; la statique ne depend pas de leur
acceptation.

### Phase E - Stratifies

1. Brancher `LaminateShellMaterial`.
2. Verifier matrices `A/B/D`, couplages et rotation des axes.
3. Verifier contraintes par pli et resultantes integrees.
4. Tester stratifies symetriques, non symetriques, equilibres et non
   equilibres.
5. Comparer aux solutions analytiques CLT et a Code_Aster/CalculiX.

Sortie : scope `mitc3-laminate-static` maintenu experimental jusqu'a revue.

## 7. Campagne de tests minimale

### Tests unitaires

- fonctions barycentriques, partition de l'unite et gradients ;
- invariance par permutation cyclique des noeuds ;
- changement de signe controle pour permutation inverse ;
- orthonormalite du repere local ;
- symetrie et finitude de `K` et `M` ;
- six modes rigides ;
- absence de mode parasite supplementaire ;
- equivalence condensee/non condensee ;
- resultante et moment exacts des charges coherentes ;
- orientation des plis et invariance par rotation globale ;
- qualite triangle et rejet des aires nulles.

### Verification mecanique

| Etude | Preuve |
| --- | --- |
| `VNV-MITC3-PATCH-001` | membrane, flexion, cisaillement, mixte |
| `VNV-MITC3-LOCKING-002` | limite mince et contraste triangle temoin |
| `VNV-MITC3-DISTORTION-003` | angles, aspect ratio et convergence |
| `VNV-MITC3-COOK-004` | convergence de fleche |
| `VNV-MITC3-SCORDELIS-005` | coque courbe facettisee |
| `VNV-MITC3-PINCHED-006` | verrouillage membrane/flexion |
| `VNV-MITC3-MIXED-MESH-007` | interface MITC3/MITC4 |
| `VNV-MITC3-LOADS-008` | forces et moments globaux |
| `VNV-MITC3-MODAL-009` | frequences, residus, MAC |
| `VNV-MITC3-NEWMARK-010` | ordre temporel et energie |
| `VNV-MITC3-HARMONIC-011` | limite statique, amplitude et phase |
| `VNV-MITC3-LAMINATE-012` | `A/B/D` et contraintes par pli |

### Seuils de depart

- patch regulier : erreur relative <= `1e-10` ;
- patch distordu : erreur relative <= `1e-8` ;
- residu statique libre : <= `1e-8` ;
- erreur fine des benchmarks statiques : <= `5 %` sauf justification ;
- ratio de fleche mince : >= `0.90` ;
- energie de cisaillement en limite mince : < `1 %` ;
- energie drilling : < `1 %` ;
- residu modal : <= `1e-8` ;
- MAC externe : >= `0.95` ;
- erreur de periode Newmark : <= `2 %`.

Ces seuils sont des objectifs de campagne. Ils ne valent pas acceptation tant
que les references, maillages et grandeurs comparees n'ont pas ete revus.

## 8. Risques et decisions bloquantes

| Risque | Reponse |
| --- | --- |
| Shear locking | Champ suppose MITC3+ et matrice epaisseur/maillage |
| Mauvais comportement membrane | Patchs distordus; enrichissement seulement si prouve necessaire |
| Mode parasite de drilling | Spectre elementaire, energie et sensibilite |
| Condensation instable | Conditionnement de `Kaa`, erreur claire, test d'equivalence |
| Normales incoherentes | Controle topologique et reorientation explicite |
| Orientation composite discontinue | Rapport de discontinuite et visualisation des axes |
| Precision inferieure a MITC4 | Comparaison a cout et densite comparables, limites publiees |
| Regression MITC4 | Aucun changement de formulation MITC4, campagne complete obligatoire |

## 9. Definition de termine

Le premier perimetre MITC3 est termine lorsque :

1. l'import Gmsh, JSON, API et CLI resolvent un modele statique isotrope ;
2. les tests unitaires et les douze familles V&V applicables sont traces ;
3. aucun mode parasite ou locking non borne n'est observe ;
4. les maillages mixtes MITC3/MITC4 passent un patch d'interface ;
5. les resultantes, energies et reactions sont equilibrees ;
6. une correlation externe sur maillage identique est disponible ;
7. la documentation mathematique et les demonstrations sont publiees ;
8. l'Owner review statue explicitement sur le domaine d'emploi.

Les scopes modal, Newmark, harmonique et composite peuvent ensuite gagner en
maturite independamment. La disponibilite dans le code ne signifie jamais, a
elle seule, que le scope est valide.

## 10. References de depart

- Lee, Y., Lee, P.-S. et Bathe, K.-J., *The MITC3+ shell element and its
  performance*, Computers & Structures 138 (2014), 12-23,
  https://doi.org/10.1016/j.compstruc.2014.02.005.
- Jeon, H.-M., Lee, Y., Lee, P.-S. et Bathe, K.-J., *The MITC3+ shell element
  in geometric nonlinear analysis*, Computers & Structures 146 (2015),
  91-104, https://doi.org/10.1016/j.compstruc.2014.09.004.
- Lee, C. et Lee, P.-S., *The strain-smoothed MITC3+ shell finite element*,
  Computers & Structures 223 (2019), 106096,
  https://doi.org/10.1016/j.compstruc.2019.07.005.
- Bathe, K.-J. et Dvorkin, E. N., *A four-node plate bending element based on
  Mindlin/Reissner plate theory and a mixed interpolation*, International
  Journal for Numerical Methods in Engineering 21 (1985), 367-383,
  https://doi.org/10.1002/nme.1620210213.

Les equations de production devront etre reliees a des numeros d'equation de
la publication primaire dans `qualification/formulas.json` avant
implementation.
