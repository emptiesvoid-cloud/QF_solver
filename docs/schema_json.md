---
doc_id: DOC-IO-001
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Schema JSON du solveur EF

Ce document decrit le format d'entree et les sorties stables de la v1 du
solveur. Le format reste volontairement simple: JSON lisible, indices de noeuds
zero-based et un seul modele par fichier.

Le lecteur applique une validation stricte avant construction du modele:
champs requis, types, indices, tailles de connectivite, materiaux references et
ddl connus sont controles avec des messages localises.

## Entree modele

Champs obligatoires:

- `nodes`: liste de coordonnees `[x, y, z]`.
- `elements`: liste d'elements avec `type`, `nodes` et `material`.
- `materials`: dictionnaire de materiaux references par nom.

Champs optionnels:

- `analysis`: chaine (`"linear_static"`) ou objet avec `type`, `method` et
  parametres de methode.
- `schema_version`: entier, `1` par defaut. Toute autre version est refusee.
- `units`: objet de metadonnees d'unites. Par defaut: `{"system": "SI"}`.
- `verification_profile`: `quick`, `engineering`, `strict` ou
  `qualification`. Par defaut: `engineering`.
- `fixed_dofs`: conditions aux limites nodales.
- `loads`: charges nodales.
- `distributed_loads`: pesanteur, forces volumiques, pressions, tractions de
  surface et tractions de bord integrees de maniere coherente.
- `springs`: ressorts lineaires au sol ou entre deux noeuds.
- `concentrated_masses`: masses nodales avec excentration et inertie optionnelles.
- `multipoint_constraints`: equations lineaires entre DDL nommes.
- `rbe2`: liaisons rigides maitre/esclaves avec bras geometrique.
- `rbe3`: liaisons de distribution ponderee sans raideur ajoutee.
- `contacts`: paires noeud esclave - triangle maitre, ou selection initiale sur
  une liste de triangles maitres explicites, avec frottement optionnel.

Analyses supportees:

- `linear_static`: statique lineaire.
- `modal`: analyse modale TET4/TET10/MITC3/MITC4/BEAM2 avec densite positive.
- `nonlinear_static`: petits deplacements TET4/TET10.
- `geometric_nonlinear_static`: TET4 total lagrangien Saint-Venant-Kirchhoff,
  charges nodales mortes, Newton complet; statut `research`.
- `transient_dynamic`: dynamique lineaire TET4/TET10/MITC3/MITC4/BEAM2 par
  integration temporelle Newmark avec densite positive; les coques MITC3 et
  MITC4 exigent `drilling_scale > 0`.
- `harmonic_response`: reponse frequentielle lineaire
  TET4/TET10/MITC3/MITC4/BEAM2 avec densite positive. Les coques MITC3 et
  MITC4 exigent `drilling_scale > 0`; les amortissements de
  Rayleigh `rayleigh_alpha` et `rayleigh_beta` sont compatibles avec la
  condensation exacte des directions de drilling sans masse.

Elements supportes:

- `BEAM2`: 2 noeuds, ddl `UX UY UZ RX RY RZ`, materiau
  `beam_isotropic`; statut initial `experimental`.
- `MITC4`: 4 noeuds, ddl `UX UY UZ RX RY RZ`, materiau `shell_isotropic`.
- `MITC3`: 3 noeuds, ddl `UX UY UZ RX RY RZ`, materiaux `shell_isotropic`
  et `shell_laminate`; les scopes dynamiques restent en developpement.
- `TET4`: 4 noeuds, ddl `UX UY UZ`, materiaux `isotropic_3d`,
  `orthotropic_3d`, `composite_orthotropic_3d`, `nonlinear_isotropic_3d` ou
  `von_mises_elastoplastic_3d`.
- `TET10`: 10 noeuds, ddl `UX UY UZ`, memes materiaux solides que TET4.

Materiaux:

- `beam_isotropic`: `E`, `G` ou `nu`, `A`, `Iy`, `Iz`, `J`; optionnels
  `density`, `kappa_y`, `kappa_z` et `reference_vector=[dx,dy,dz]`.
- `isotropic_3d`: `E`, `nu`, optionnel `density`.
- `orthotropic_3d`: `E1/E2/E3`, `nu12/nu13/nu23`, `G12/G13/G23`, orientation
  globale implicite, matrice `orientation`, ou couple `e1/e2_hint`.
- `composite_orthotropic_3d`: meme loi 3D, avec `homogenization` et
  `provenance` obligatoires; statut `research`.
- `nonlinear_isotropic_3d`: `E`, `nu`, `hardening`, optionnel `density`.
- `von_mises_elastoplastic_3d`: `E`, `nu`, `yield_stress`, optionnel
  `hardening_modulus`, `density`.
- `shell_isotropic`: `E`, `nu`, `t`, optionnels `shear_factor`,
  `drilling_scale`, `density` ou `rho`.
- `orthotropic_lamina`: socle constitutif experimental avec `E1`, `E2`,
  `nu12`, `G12`, et optionnellement `density` ou `rho`. Il est utilisable
  directement comme loi constitutive et par les plis de `shell_laminate`.
- `shell_laminate`: coque MITC4 multicouche experimentale. `plies` est une
  liste bas-vers-haut; chaque pli exige `E1`, `E2`, `nu12`, `G12`, `G13`,
  `G23`, `thickness`, et accepte `angle_deg`, `density`/`rho` et `name`.
  `reference_direction=[dx,dy,dz]` peut definir un axe global continu projete
  dans chaque facette; un vecteur nul ou parallele a la normale locale est
  refuse.
  Le sous-objet optionnel `strengths` contient `Xt/Xc/Yt/Yc/S12` et
  `f12_star`; `strain_allowables` contient `e1t/e1c/e2t/e2c/g12`. Seule
  l'analyse `linear_static` est autorisee.

## Ressorts et masses concentrees

Les listes `elements` et `materials` peuvent etre vides dans un modele discret
pur, mais le modele doit alors contenir au moins un ressort.

Un ressort definit `node_a`, un `node_b` optionnel, une liste `dofs`, et
exactement un champ parmi :

- `stiffness`: scalaire ou vecteur diagonal de meme longueur que `dofs`;
- `stiffness_matrix`: matrice carree symetrique positive semi-definie.

`coordinate_system` vaut `global` par defaut. En repere `local`, une matrice
`orientation` orthonormee directe `3x3` est obligatoire.

Une masse concentree definit `node` et `mass > 0`. `center_of_mass` est le
vecteur global du noeud vers le centre de masse. `inertia` est le tenseur
`3x3` au centre de masse, exprime dans le repere global. Il doit etre
symetrique, positif semi-defini et respecter l'inegalite triangulaire des
moments principaux.

Voir [Ressorts et masses concentrees](elements/entites_discretes.md) et
`examples/spring_mass_oscillator.json`.

## MPC et RBE

Le premier terme de chaque `multipoint_constraints[].terms` est le DDL
dependant dans la reduction creuse. Chaque terme fournit `node`, `dof` et
`coefficient`; l'equation vaut la somme des produits egale a `value`.

`rbe2` contient un `master`, des `slaves` et `tie_rotations` optionnel. Il
impose les translations rigides a partir des translations et rotations du
maitre. `rbe3` contient un `reference`, des paires `independents`
`node/weight` et un `mode`.

Le mode par defaut `rigid_body_projection` requiert trois noeuds independants
non degeneres, des poids strictement positifs et les six DDL de reference. Il
preserve le travail virtuel d'un torseur, donc sa resultante et son moment. Le
mode `weighted` est explicite, accepte un sous-ensemble `dofs` et normalise
les poids, mais il ne garantit pas le moment pour une geometrie 3D.

Ces liaisons sont actuellement limitees a `linear_static`. Voir
[Liaisons MPC et RBE](elements/liaisons_mpc_rbe.md) et
`examples/rbe2_rigid_arm.json`.

## Contact unilateral

Une entree `contacts` declare un `slave_node` et exactement l'un des deux
champs suivants : `master_nodes` avec trois indices, ou `master_faces` avec
une ou plusieurs faces triangulaires ordonnees. Dans ce second cas, la face
dont la projection initiale est compatible et la plus proche est retenue de
maniere deterministe. Cette selection est figee pendant le calcul. Un `name`
facultatif et une `gap_tolerance` strictement positive peuvent etre fournis.
Le contact est borne a `linear_static` avec la methode `direct` ou `spsolve`;
MPC et RBE sont refuses dans cette premiere version. Pour activer
le frottement regularise, fournir simultanement un
`friction_coefficient > 0` et un `tangential_stiffness > 0`.

```json
{
  "contacts": [{
    "name": "support_plane",
    "slave_node": 3,
    "master_nodes": [0, 1, 2],
    "gap_tolerance": 1.0e-10,
    "friction_coefficient": 0.5,
    "tangential_stiffness": 10000.0
  }]
}
```

Le noeud esclave doit se projeter dans le triangle maitre et les directions
tangentielles doivent etre stabilisees par le modele. Voir
[Contact unilateral sans frottement](elements/contact_sans_frottement.md),
[Contact unilateral avec frottement](elements/contact_avec_frottement.md) et
`examples/frictionless_contact_plane.json`.

La selection initiale sur deux faces adjacentes est illustree par
`examples/frictionless_contact_surface.json` :

```json
{
  "contacts": [{
    "name": "two_face_support",
    "slave_node": 4,
    "master_faces": [[0, 1, 2], [1, 3, 2]]
  }]
}
```

Ce champ ne fournit pas une recherche de contact actualisee ni du contact
surface-surface par defaut : la facette est choisie une fois, dans la
geometrie initiale. Le parametre d'analyse experimental
`contact_search_mode: "updated"` active une iteration de petites translations
qui peut changer la facette retenue. Il est limite au contact sans frottement,
aux normales relocalisees par iteration et a
`contact_search_max_iterations`; `contact_max_iterations` et
`contact_search_max_iterations` doivent etre des entiers strictement positifs,
et `contact_search_tolerance` un reel fini strictement positif. Ces champs sont
verifies par `check-mesh` avant toute resolution; grand glissement et topologie
variable restent hors scope.

Pour le frottement a memoire, `analysis.contact_load_steps` repartit une
charge proportionnelle et `analysis.contact_load_history` fournit un tableau
de facteurs, une ligne par increment et une colonne par charge nodale. Les
charges reparties sont refusees dans ce chemin de charge V1.

Conditions et charges:

```json
{"node": 0, "dofs": ["UX", "UY", "UZ"]}
{"node": 1, "dof": "UX", "value": 1000.0}
```

## Chargements repartis coherents

Les charges reparties sont declarees dans le tableau racine
`distributed_loads`. Elles sont integrees avec les fonctions de forme de
l'element puis assemblees dans le vecteur global. Les anciennes charges
ponctuelles `loads` restent compatibles. L'ordre utilise par
`load_factors_by_load` est toujours: toutes les charges nodales, puis toutes
les charges reparties, dans l'ordre du JSON.

Types disponibles:

| Type | Support | `value` | Unite SI | Cible |
| --- | --- | --- | --- | --- |
| `gravity` | TET4, TET10, MITC4 | `acceleration` a 3 composantes | m/s2 | `elements` ou tous |
| `body_force` | TET4, TET10, MITC4 | vecteur a 3 composantes | N/m3 | `elements` ou tous |
| `pressure` | faces TET4/TET10, surface MITC4 | scalaire | Pa | `element`, `face` |
| `surface_traction` | faces TET4/TET10, surface MITC4 | vecteur a 3 composantes | Pa | `element`, `face` |
| `edge_traction` | aretes MITC4 | vecteur a 3 composantes | N/m | `element`, `edge` |
| `line_load` | BEAM2 | vecteur a 3 composantes | N/m | `element` |

Exemples:

```json
"distributed_loads": [
  {"type": "gravity", "acceleration": [0.0, 0.0, -9.81]},
  {"type": "body_force", "value": [1000.0, 0.0, 0.0], "elements": [0, 1]},
  {"type": "pressure", "element": 2, "face": 0, "value": 250000.0},
  {
    "type": "surface_traction",
    "element": 3,
    "face": 1,
    "value": [1000.0, 0.0, 0.0],
    "coordinate_system": "global"
  },
  {"type": "edge_traction", "element": 4, "edge": 2, "value": [0.0, -50.0, 0.0]}
]
```

Pour `gravity`, chaque materiau cible doit definir une densite strictement
positive. Pour une coque, la force surfacique integree vaut
$\rho t\mathbf a$. Pour `body_force`, le vecteur est une force par unite de
volume; sur MITC4 il est multiplie par l'epaisseur `t`.

Une pression positive est **compressive**:

$$
\mathbf t_p=-p\mathbf n_{ext}.
$$

La normale exterieure est determinee par la connectivite orientee. Les faces
solides, zero-based, sont:

| `face` | TET4 sommets | TET10 noeuds de face |
| ---: | --- | --- |
| 0 | `[1, 2, 3]` | `[1, 2, 3, 5, 9, 8]` |
| 1 | `[0, 3, 2]` | `[0, 3, 2, 7, 9, 6]` |
| 2 | `[0, 1, 3]` | `[0, 1, 3, 4, 8, 7]` |
| 3 | `[0, 2, 1]` | `[0, 2, 1, 6, 5, 4]` |

Pour MITC4, `face` est omis ou vaut `0`. Les aretes sont `[0,1]`, `[1,2]`,
`[2,3]`, `[3,0]` pour `edge=0..3`.

Les tractions vectorielles acceptent `coordinate_system: "global"` ou
`"local"`. Sur une face solide, la base locale est construite avec
$\mathbf e_1$ tangent au premier axe parametrique, $\mathbf e_3$ normale
exterieure et $\mathbf e_2=\mathbf e_3\times\mathbf e_1$. Sur MITC4, elle est
la base locale documentee dans le manuel theorique. La pression ne depend pas
de ce champ: elle suit toujours la normale de la geometrie initiale.

La v1 ne traite que des charges mortes en petits deplacements.
`follower: true` est reconnu mais refuse avec une erreur explicite; il faudra
une formulation grandes transformations et une tangente de charge avant de
l'autoriser.

## Sortie `results.json`

La resolution statique ecrit:

- `status`, `analysis`, `method`, `message`;
- `node_count`, `element_count`, `ndof`, `max_displacement`;
- `displacements`: valeurs nodales par ddl actif;
- `element_results`: deformations, contraintes, resultantes, points
  d'integration et invariants;
- pour les coques stratifiees, `shell_sections` publie `shell_down`,
  `shell_middle` et `shell_up` suivant l'axe local `e3`; une interface au plan
  moyen conserve ses deux limites materielles;
- `nodal_results`: contraintes/deformations nodales moyennees quand
  disponibles;
- `solver`: methode, convergence, residus;
- `material_states`: etat interne final des materiaux chemin-dependants par
  element et point d'integration, si present;
- `mesh_report`: statut maillage et details;
- `audit`: trace boite blanche complete;
- `run_verdict`: verdict d'acceptation `PASS`, `WARNING` ou `FAIL`, distinct du
  statut numerique historique `status`;
- `qualification_summary`: verdict machine-readable avec `status`,
  `blocking_errors`, `warnings`, `trust_score`,
  `trust_score_non_certifying`, `evidence_level`, `verification_profile` et
  `maturity`. Le `trust_score` est conserve uniquement pour compatibilite et
  ne doit jamais servir de critere d'acceptation.

La resolution modale ecrit:

- `modes`: valeurs propres, frequences et formes modales;
- `audit`: matrices et controles disponibles.

Le solveur modal par defaut est `eigsh`. Le parametre positif
`dense_modal_max_dofs`, egal a `2000` par defaut, borne toute conversion vers
`eigh`; le depassement produit une erreur d'entree explicite.

La resolution dynamique transitoire ecrit aussi:

- `velocities`: vitesses nodales finales;
- `accelerations`: accelerations nodales finales;
- `solver.time_history`: pas, temps, facteur de charge, energies, maxima et
  residu dynamique;
- `solver.residual_history`: residu dynamique par pas.
- `solver.effective_factorization_reused`: indique si une LU sparse constante
  a ete reutilisee;
- `solver.effective_factorization_count` et
  `solver.effective_factorization_solve_count`: nombres de factorisations et
  de resolutions effectives.

La resolution harmonique ecrit:

- `frequency_response`: reponse complexe convertie en reel, imaginaire,
  amplitude et phase par noeud et ddl;
- `peak_response`: frequence et amplitude maximale;
- `solver.residual_norms`: residus complexes par frequence.
- `solver.dynamic_reduction`: diagnostic de condensation et de reconstruction
  des rotations de drilling MITC4.
- `solver.harmonic_condensation`: strategie de complement de Schur et support
  de l'amortissement proportionnel a la rigidite.

Parametres dynamiques principaux:

- `time_step` ou `dt`: pas de temps;
- `steps` ou `time_steps`: nombre de pas;
- `newmark_beta`, `newmark_gamma`: parametres du schema;
- `rayleigh_alpha`, `rayleigh_beta`: amortissement proportionnel;
- `modal_damping_targets`: exactement deux objets
  `{frequency_hz, damping_ratio}`. QF_solver calcule les coefficients de
  Rayleigh qui reproduisent ces deux taux; ce champ est exclusif de
  `rayleigh_alpha` et `rayleigh_beta`;
- `load_function`: `constant`, `linear_ramp`, `sine`, `half_sine_pulse` ou
  `linear_chirp`;
- `load_frequency_hz`: frequence du sinus;
- `pulse_duration`: duree positive de l'impulsion demi-sinus;
- `chirp_start_hz`, `chirp_end_hz`, `chirp_duration`: bornes et duree du
  chirp lineaire;
- `load_table`: table interpolee de `{time, factor}`;
- `load_factors`: facteurs globaux par pas;
- `load_factors_by_load`: facteurs par index de charge, nodales d'abord puis
  reparties. Chaque valeur est une liste non vide; le dernier facteur est
  conserve lorsque la liste est plus courte que le calcul;
- `initial_displacements`, `initial_velocities`: conditions initiales nodales.
- `history_probes`: liste optionnelle de sondes signees `{node, dof, label}`;
  chaque pas exporte deplacement, vitesse et acceleration sans materialiser
  tout le champ temporel nodal.
- `history_shell_stress_probes`: liste optionnelle de sondes MITC4
  `{node, face: top|bottom, component: S11|S22|S12, label}`;
- `checkpoint_path`: fichier NPZ atomique ecrit pendant le calcul;
- `checkpoint_interval`: periodicite positive en nombre de pas, le dernier pas
  etant toujours sauvegarde;
- `checkpoint_keep_steps`: conserve aussi une copie versionnee par numero de pas;
- `restart_from`: reprend un calcul depuis un checkpoint NPZ compatible.

La reprise verifie une empreinte du modele, des materiaux, conditions aux
limites, charges et parametres physiques. Une modification de ces donnees
invalide volontairement le checkpoint. L'historique retourne apres reprise ne
contient que les pas recalcules et `solver.history_is_partial` vaut `true`.
La sortie `solver.damping_definition` trace les cibles modales et les
coefficients obtenus. Chaque ligne de `time_history` publie aussi
`load_component_factors` dans l'ordre stable des contributions assemblees.

Pour `nonlinear_static`, les memes quatre champs `checkpoint_path`,
`checkpoint_interval`, `checkpoint_keep_steps` et `restart_from` sauvegardent
les deplacements, le facteur de charge et les variables internes J2 committes.
La reprise est disponible pour les pas de charge fixes, y compris un
`load_path` signe. Elle refuse actuellement `adaptive_load_steps` et
`arc_length`. La sortie non lineaire ajoute `restart_step`,
`history_is_partial`, `checkpoint_files` et `checkpoint_model_signature`.
Chaque objet de `solver.steps` contient aussi `last_correction_norm`,
`cumulative_correction_norm`, `incremental_internal_work`,
`incremental_external_work`, `relative_work_imbalance`,
`load_step_cutbacks`, `state_committed` et `work_diagnostics_available`.
Les travaux sont integres par la regle trapezoidale et ne constituent pas, a
eux seuls, une preuve de dissipation plastique.

Parametres de performance et modaux:

- `assembly_chunk_size`: nombre d'elements assembles par bloc sparse;
- `mass_formulation`: seule la valeur `consistent` est acceptee pour les
  analyses modales, Newmark et harmoniques. Les valeurs `lumped` et
  `concentrated` sont hors scope et provoquent une erreur d'entree explicite;
- `modal_shift_hz` ou `modal_shift_eigenvalue`: cible optionnelle du shift-invert;
- `arpack_which`, `arpack_tolerance`, `arpack_maxiter`, `arpack_ncv`: controles
  explicites du solveur modal sparse.

Les entrees Newmark doivent respecter `gamma >= 0.5` et
`beta >= 0.25 * (gamma + 0.5)^2`. Les coefficients de Rayleigh sont finis et
positifs ou nuls. Les temps d'une `load_table` sont finis, positifs ou nuls et
strictement croissants. Le profil `qualification` n'accepte que les unites SI
canoniques declarees.

## Sortie `audit`

L'audit contient:

- `dof_map`, `element_dofs`, `boundary`;
- `vectors`, `matrices`, `element_audits`;
- `load_assembly`: resultante, moment a l'origine et contribution de chaque
  charge nodale ou repartie;
- `mesh_details`: topologie, composantes, noeuds isoles et contraintes;
- `post_results`: deplacement local, contraintes, resultantes et invariants;
- `equilibrium`: residus, reactions, energies;
- `checks`: controles `PASS`, `WARNING`, `FAIL`.

## Sortie `mesh_report`

`check-mesh --json-report mesh_report.json` ecrit:

- `status`, `errors`, `warnings`;
- `details.node_count`, `element_count`, `element_types`;
- `details.components`: noeuds, elements, types, charges et blocages;
- `details.element_quality`: mesures geometriques par element;
- `details.quality_thresholds`: seuils de qualite utilises;
- `details.mechanical_rank`: estimation de rang sur petits modeles.

## Dossier `evidence`

La commande `evidence` et l'API `save_evidence` ecrivent un dossier de preuve
reproductible. Le dossier contient au minimum:

- `input.json`: entree exacte archivee pour le calcul;
- `results.json`: resultat complet;
- `audit.md`: audit lisible;
- `mesh_report.json`: rapport maillage;
- `solver_settings.json`: analyse, methode, parametres et metadata de
  qualification;
- `qualification_summary.json`: verdict machine-readable;
- `evidence_manifest.json`: manifeste de tracabilite.

Le manifeste v2 `evidence_manifest.json` contient:

- `manifest_schema_version`;
- `created_at_utc`;
- version du solveur, revision Git et etat du working tree;
- commande exacte, Python, plateforme, paquets, BLAS et environnement de
  parallelisme;
- empreintes des baselines de dependances verrouillees;
- empreinte SHA-256 de l'entree et synthese de couverture des exigences;
- chemin source de l'entree quand il est connu;
- analyse, methode, statut resultat, version schema JSON, unites et profil;
- copie du `qualification_summary`;
- liste des fichiers avec `role`, chemin relatif, taille en octets et SHA-256.

Le manifeste ne se signe pas lui-meme: ses empreintes couvrent les artefacts de
preuve ecrits a cote de lui.

La commande `verify-evidence --input evidence_dir` relit ce manifeste,
recalcule tailles et SHA-256, puis retourne `PASS` ou `FAIL`. Avec
`--json-report`, elle ecrit un rapport contenant une ligne par artefact
controle.

La lecture des manifestes v1 reste supportee. Toute nouvelle preuve est ecrite
en v2.

## Exemples officiels testes

- `examples/tet4_static.json`
- `examples/tet4_compression.json`
- `examples/tet4_body_force.json`
- `examples/tet4_pressure.json`
- `examples/tet10_static.json`
- `examples/mitc4_shell_static.json`
- `examples/tet4_modal_unit.json`
- `examples/mitc4_modal_cantilever.json`
- `examples/mitc4_newmark_cantilever.json`
- `examples/tet4_nonlinear_static.json`
- `examples/tet4_geometric_nonlinear_static.json`
- `examples/tet4_elastoplastic_static.json`
- `examples/tet4_transient_dynamic.json`
- `examples/tet4_dynamic_free_vibration.json`
- `examples/tet4_dynamic_sdof_free_vibration.json`
- `examples/tet4_dynamic_tabulated_load.json`
- `examples/tet4_harmonic_response.json`
- `examples/tet4_harmonic_sdof_response.json`
- `examples/mitc4_harmonic_cantilever.json`
- `examples/beam2_cantilever.json`
- `examples/spring_mass_oscillator.json`

Ces fichiers sont executes par la suite de tests via API et CLI.

Un exemple volontairement invalide est aussi disponible pour tester les audits
partiels:

- `examples/invalid_inverted_tet4.json`

## Format grand modele

Le mode grand modele utilise HDF5 ou NPZ, documente dans
`docs/grand_modele.md`. Il ne remplace pas le JSON v1: il sert aux modeles
TET4 statiques lineaires qui ne doivent pas etre materialises sous forme de
gros dictionnaires JSON.
