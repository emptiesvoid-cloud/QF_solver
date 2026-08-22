# Changelog

## 0.2.1a0 - 2026-08-13

Cette alpha consolide le processus de verification et validation de QF_solver.
Elle conserve la baseline `0.2.0a0` immuable et ne revendique aucune
certification externe.

- Ajout du registre machine-readable `qualification/release_vv_0_2_1.json`.
- Ajout de `qf-solver release-vv`, de `run_release_vv()` et d'un pack JSON,
  Markdown et manifeste SHA-256.
- Separation explicite entre calcul numeriquement passe, readiness des preuves,
  revue Owner et statut de publication.
- Les scopes candidats dont les preuves publiques controlees manquent restent
  en `WARNING`; ils ne sont pas presentes comme qualifies.
- Ajout du controle de compatibilite avec le tag `v0.2.0-alpha` et son commit.
- Retrait de la livraison web et de ses dependances : la documentation de
  release reste en Markdown, PDF, figures locales et artefacts V&V versionnes.
- Migration du noyau MITC4 canonique vers
  `solveur.elements.shell.mitc4`; les imports et la commande historiques
  restent des facades de compatibilite depreciees en `0.2.x`.

## 0.2.0a0 - 2026-08-13

Cette version alpha est la premiere publication open source preparee de
QF_solver. Le code est sous Apache-2.0 et la documentation ainsi que les
exemples originaux sont sous CC BY 4.0. Les fonctionnalites marquees
`experimental` ou `research` restent hors de toute revendication de
qualification et doivent etre utilisees avec une revue mecanique adaptee.

- Ajout des informations d'auteur, de citation et de licence.
- Ajout de l'inventaire des dependances et des regles de redistribution.
- Conservation des niveaux de maturite et des limites de validation existants.
- Gel du perimetre alpha avec decisions Owner tracees pour TET4/TET10/MITC3
  en modal, Newmark et harmonique, BEAM2 dynamique et entites discretes.
- Inclusion des preuves Owner recentes MITC3+ multicouche courbe a orientation
  projetee et TET10 J2 structurel, en conservant leur statut experimental borne.
- La campagne MITC4 multicouche dynamique est acceptee par l'Owner pour un
  usage engineering experimental borne; la tentative modale a 10 000 QUAD4
  conserve une reserve numerique explicite.
- Adoption d'un layout `src/` pour isoler le paquet installable du repertoire
  de travail. Le noyau MITC4 historique reste sous `src/solveur/elements/shell/mitc4` et l'API
  generaliste dans `src/solveur`.
- Deplacement du conteneur PETSc/MPI dans `tools/containers/large`; Docker
  reste une aide de reproductibilite optionnelle et ne fait pas partie du
  runtime standard.
- Reduction de la wheel aux sources, exemples et registres d'execution. Le
  manuel, les tests et les decisions de revue restent publics dans le depot
  GitHub et ne sont pas dupliques dans les archives PyPI.

### Documentation technique

- Ajout d'un contrat documentaire uniforme par element et methode.
- Ajout des pages direct, CG, MINRES, GMRES, BiCGSTAB et arc-length.
- Ajout de figures BEAM2, ressort-masse et RBE2 regenerees par l'API.
- Ajout d'un registre `pending_owner_review` qui interdit d'assimiler une
  demonstration documentee a une qualification.
- Ajout des formulations forte/faible TET4, TET10, MITC4 et BEAM2, de leurs
  matrices de tests et des sous-chapitres BEAM2.
- Le dossier PDF compose les equations LaTeX et controle automatiquement un
  minimum de dix pages pour chaque formulation elementaire principale.

### Consolidation de l'alpha

- Consolidation du manuel technique, des cartes de contraintes et deformations,
  des contrats de chargement, des convergences et des vues
  QF_solver/reference. La decision documentaire Owner est enregistree sans
  effet automatique sur les maturites mecaniques.
- Ajout d'une couverture machine-readable de 33 couples element-analyse,
  sept contrats de chargement et douze familles de methodes.
- Ajout de `pypdf==6.10.0` a l'extra et a la baseline documentaire. La
  decouverte de Pandoc et MiKTeX utilise `PATH`, des variables QF_solver ou
  l'API portable des repertoires utilisateur, sans chemin de poste dans les
  sources. L'audit public repasse a `649` fichiers et `0` constat.
- Enregistrement de l'Owner review MITC3+ statique lineaire en
  `accepted_for_bounded_engineering_use` le 1er aout 2026.
- Ajout d'une matrice machine-readable element/analyse distinguant capacite
  implementee, verification automatique, Owner review et domaines non
  supportes. Elle met en evidence les campagnes dynamiques encore manquantes.

- Ajout du benchmark MITC3+ de l'hemisphere pince a ouverture `18 deg`, six
  raffinements et reconstruction des quatre quadrants. Au niveau fin,
  QF_solver/Code_Aster DKT differe de `0,0927 %`, le champ nodal de `0,1536 %`
  et QF_solver se situe a `0,5912 %` de la reference publiee `0,0924`.
- Ajout des figures separees de geometrie, convergence, deformees comparees et
  champ Code_Aster, ainsi que du patch de flexion explicite
  `kappa_x/kappa_y/kappa_xy`.

- Correction de l'interpolation de cisaillement MITC3+ : le facteur `2/3`
  multiplie desormais tout le premier groupe de l'equation (17) de Lee, Lee
  et Bathe. Le patch de cisaillement constant atteint `1,81e-16` et la
  baseline precedente est marquee `SUPERSEDED`.
- Ajout des raffinements MITC3+ Scordelis-Lo `20 000` triangles et cylindre
  pince `19 600` triangles, avec erreurs respectives `0,4044 %` et
  `2,0899 %`, champs, courbes, manifestes et PDF d'Owner review.
- Optimisation de l'assemblage des charges distribuees par contributions
  creuses locales, supprimant un vecteur global intermediaire par charge.
- Regeneration des correlations MITC3+ : ecart de flexion Code_Aster DKT
  `0,007116 %`; CalculiX S3 reste un temoin negatif a `113,086 %`.
- Ajout de `VNV-J2-CODEASTER-VMIS-ISOT-LINE-004`, seconde implementation
  externe J2 executee avec Code_Aster 18.1.0 epingle. La conversion
  `D_SIGM_EPSI=E H/(E+H)` est explicite; contrainte, plasticite equivalente,
  contraintes laterales et homogeneite passent a la precision machine.
- Fermeture de `VNV-ORTHOTROPIC-SINGULAR-STRESS-005` sur huit raffinements,
  jusqu'a `237 358` TET4, avec recuperation compacte ponderee par volume,
  correlation Code_Aster bloquante et comparaison nodale CalculiX diagnostique.
- Ajout de trois modeles de contact demandes en Owner review : coin a deux
  normales, rampe facettisee et bloc TET4 deformable a deux esclaves.
- Ajout de deux pieces orthotropes de contrainte, encoche arrondie et double
  trou, avec cinq raffinements, cartes `S11` et correlation Code_Aster.
- Enregistrement de l'Owner review des contraintes singulieres en
  `accepted_with_recommendations`, datee du 29 juillet 2026.
- Ajout de `VNV-CONTACT-CODEASTER-ADDITIONAL-009` : dix paliers sur le coin,
  la rampe et le bloc TET4. Deux courbes sont confondues; le bloc passe sur la
  branche fermee; son raffinement a `768` TET4 abaisse l'ecart de transition
  de `5,2565 %` a `4,3400 %`, sous le seuil Owner review de `5 %`.
- Ajout de `VNV-CONTACT-CODEASTER-ADDITIONAL-H10K-010` : confirmation du
  bloc deformable sur `9 984` TET4. QF_solver et Code_Aster donnent un ecart
  maximal de courbe de `3,3029e-12 %`; la decision Contact V1 est enregistree
  `accepted_for_bounded_engineering_use`.
- Fermeture de la baseline Windows de preparation V1 : `926` tests passent,
  le profil engineering est PASS, le site regenere `625` artefacts, l'audit
  public analyse `579` fichiers sans constat et l'archive prospective en
  exporte `407` sans inclure les instructions de travail internes.
- Correction de l'execution directe de `scripts/release_readiness.py` et ajout
  d'un test CLI. Le verdict reste volontairement `NOT_READY` jusqu'au choix de
  licence, au gel de l'arbre Git et au tag `0.2.0`.

- Preparation de publication open source : URLs de projet packagees, contrat
  de stabilite API, guide de contribution, politique de securite, support,
  modele de pull request, formulaires GitHub et checklist de publication.
  La licence reste volontairement `Proprietary` jusqu'a une decision explicite
  du proprietaire du projet.

- Ouverture de P6.1 avec la lamelle orthotrope plane `OrthotropicLamina`, les
  transformations `Q/Qbar`, les controles de positivite et les preuves
  analytiques `0/90/+/-45 deg`.
- Ajout de la theorie classique des stratifies avec plis et interfaces,
  matrices `A/B/D`, resultantes, inversion generalisee et contraintes aux
  faces de chaque pli; preuves `[0]`, `[0/90]s`, `[+45/-45]s` et `[0/90]`.
- Ajout du materiau `shell_laminate` dans MITC4 statique avec couplage `B`,
  cisaillement transverse `G13/G23`, contraintes par pli, exemple JSON et
  controles d'objectivite, coque facettisee et shear locking.
- Ajout des indicateurs non degradants contrainte/deformation maximale,
  Tsai-Hill et Tsai-Wu, avec facteurs de reserve et synthese du pli critique.
- Ajout de `VNV-COMP-ANALYTIC-001`: six oracles analytiques, enveloppes de
  rupture, rapport Markdown et manifeste SHA-256.
- Ajout de `VNV-COMP-STRUCTURAL-CONVERGENCE-002`: membrane et flexion de
  stratifies sur sept niveaux de maillage, avec separation explicite entre
  oracle analytique applicable et stabilisation d'un panneau couple.
- Ajout de `VNV-COMP-CALCULIX-S8R-003`: correlation externe reelle entre
  MITC4 et CalculiX 2.20 S8R composite, avec ecart fin de fleche `0,0310 %`.
- Ajout de `VNV-COMP-NAFEMS-R0031-CODEASTER-004`: benchmark NAFEMS R0031/1
  execute avec QF_solver MITC4 et Code_Aster 18.1.0 DST/DSQ sur cinq maillages
  jusqu'a `5 120` elements; ecarts fins sur `UZ(E)` de `0,458 %` et `0,710 %`,
  avec increments finaux inferieurs a `0,1 %`.
- Ajout de `VNV-COMP-CONICAL-CUTOUT-PLY-STRESS-CALCULIX-S8R-012` :
  correlation de contraintes par pli sur une couronne conique a distance
  normalisee du bord libre. L'ecart L2 fin QF_solver/CalculiX S8R est
  `0,298 %`; `S13`, pics de bord libre et delaminage restent hors scope.
- Ajout de la specification future `orthotropic_3d` pour TET4/TET10, avec
  orientations, sorties, programme V&V et limites explicites.
- Implementation `research` de `orthotropic_3d` et
  `composite_orthotropic_3d` pour TET4/TET10, avec repere global ou
  `e1/e2_hint`, sorties dans les axes globaux/materiau et exemples JSON.
- Ajout de `VNV-ORTHOTROPIC-SOLID-KERNEL-001`: loi, tractions,
  cisaillements, objectivite, energie, patchs affines et modes rigides
  `SPEC-COMP-SOLID-001..005` PASS.
- Ajout de `VNV-ORTHOTROPIC-SOLID-EXTERNAL-002`: deux geometries 3D maillees
  complexes, eprouvette perforee et equerre, comparees sur maillage identique
  a Code_Aster 18.1.0 TETRA4 et CalculiX 2.20 C3D4. Les six controles de
  deplacement et contrainte passent; `SPEC-COMP-SOLID-007` est couvert.
- Ajout de `VNV-ORTHOTROPIC-SOLID-CONVERGENCE-003`: convergence hors axes sur
  quatre maillages TET4/TET10 et reference TET10 fine. Le TET10 atteint
  `0,292 %`; le TET4 converge mais conserve `21,66 %` d'ecart en flexion.
- Ajout de `VNV-ORTHOTROPIC-ISOTROPIC-NONREGRESSION-004` et mise en cache de
  la matrice isotrope : equivalence numerique sous `2,50e-16`, ratios temps et
  memoire sous `1,25`. Les specifications `001..008` sont couvertes.

### TET4 total lagrangien structurel V2

- Ajout du post-traitement fini par element : `F`, Green-Lagrange, PK2,
  Cauchy, energie et `det(F)`.
- Ajout des campagnes `VNV-TET4-TL-STRESS-005`,
  `VNV-TET4-TL-BUCKLING-EULER-006` et
  `VNV-TET4-TL-POSTBUCKLING-007`.
- Ajout d'une recherche de charge critique par tangente precontrainte et d'un
  suivi arc-length creux sans matrice augmentee dense.
- Ajout des rapports Markdown, PNG et manifestes SHA-256 associes; statut
  `research`, en attente d'une nouvelle revue mecanique.
- Correlation externe CalculiX `2.20` C3D4 sur contrainte finie et flambement
  propre: ecart Cauchy `1,17e-7` et ecart de charge critique fine `0,035 %`.
- Correlation externe Code_Aster `18.1.0` TETRA4 sur PK2 et colonne imparfaite:
  ecarts `8,54e-5` et `1,69e-9`; flambement propre solide marque non applicable
  pour l'operateur `RIGI_GEOM` au lieu d'utiliser une formulation differente.
- Ajout du chemin public `geometric_nonlinear_static` pour TET4 homogene sous
  charges nodales mortes, avec Newton complet, sorties finies et maturite
  `research` bloquee par le profil qualification.
- Ajout du point de flambement `VNV-TET4-TL-BUCKLING-H5-010` a `98 304` TET4:
  erreur Euler `1,896 %`, accord CalculiX `0,0343 %` et revue structurelle V2
  `accepted_with_recommendations` par Quentin Farinazzo.
- Demarrage de la consolidation TET10 avec selection de quadrature : Hammer a
  4 points sur geometrie droite, Duffy positive a 64 points sur geometrie
  courbe et controle du Jacobien sur 35 points avant assemblage.
- Ajout de `VNV-TET10-GEOMETRY-QUADRATURE-011` : erreur matricielle courbe
  `7,51e-7` face a Duffy ordre 8, amelioration superieure a quatre ordres de
  grandeur face a Hammer et rejet controle des geometries inversees.
- Ajout de `VNV-TET10-STRUCTURAL-CONVERGENCE-012` sur 24 calculs TET4/TET10:
  patch de traction au bruit machine, erreur de flexion TET10 `1,179 %`,
  erreur de rotation de torsion `0,00250 %` et erreur de contrainte `0,991 %`.
- Extension du chargement coherent de torsion aux faces quadratiques T6 avec
  correction discrete de resultante et conservation du couple a `2,27e-16`.
- Ajout de `VNV-TET10-MASS-MODAL-LOADS-013` : masse courbe, pression T6,
  recuperation nodale et premier couple modal verifies; ecart frequentiel
  maximal `0,434 %` et residu propre `9,74e-11`.
- Ajout de `VNV-TET10-CALCULIX-C3D10-014` sur un arbre courbe strictement
  identique : ecarts QF_solver/CalculiX de `6,84e-5` sur le champ complet et
  `6,45e-5` sur la rotation terminale.
- Ajout de `VNV-TET10-NEAR-INCOMPRESSIBLE-015` : a `nu=0,499`, le TET10
  conserve `94,83 %` de la compliance de Timoshenko contre `8,48 %` pour le
  TET4 temoin; l'incompressibilite exacte reste hors scope.
- Ajout de la revue mecanique TET10 lineaire en PDF autonome de 11 pages, avec
  catalogue des modeles et sept figures incorporees sans lien externe.
- Validation interne TET10 lineaire `accepted_with_recommendations` par Quentin
  Farinazzo le `2026-07-18`; campagne finale sur pieces complexes et
  correlations multi-solveurs differee avant acceptation totale.
- Centralisation des quadratures triangulaires positives T3/T6 dans le module
  solide commun, utilise par les charges et les oracles V&V.

### Validation modale MITC4

- Ajout des etudes analytiques `VNV-MITC4-MODAL-CANTILEVER-002` et
  `VNV-MITC4-MODAL-PLATE-003` avec convergence h, MAC, residus et
  orthogonalite masse.
- Verification des dix premiers modes de Navier, y compris trois paires
  propres doubles comparees par sous-espaces.
- Publication automatique des courbes, de la deformee et des tableaux dans le
  site technique hors ligne.
- Ajout de sondes temporelles Newmark optionnelles et de
  `VNV-MITC4-NEWMARK-FREE-002`: historique cosinus, convergence d'ordre deux,
  retour de periode, energie et residu dynamique.
- Ajout de `VNV-MITC4-NEWMARK-DAMPED-FORCED-003` avec decroissance amortie,
  puissance dissipative, force modale sinusoidale et deux solutions fermees.
- Ajout de la reponse harmonique MITC4 avec condensation/reconstruction
  complexe du drilling, limite statique, amplitude, phase, resonance et
  sensibilite a l'amortissement dans `VNV-MITC4-HARMONIC-MODAL-001`.
- Demonstration et implementation du complement de Schur harmonique exact
  pour `C=alpha*M+beta*K`, incluant charge directe `RZ`, `rayleigh_beta > 0`
  et comparaison au systeme complexe complet dans
  `VNV-MITC4-HARMONIC-CONDENSATION-002`.
- Le scope `mitc4-modal` est `candidate`; la revue mecanique doit etre refaite
  et une revue independante reste obligatoire avant qualification externe.

### Non-linearite, dynamique et grand modele

- correction de la recherche lineaire non lineaire aux passages par charge
  nulle par normalisation avec la charge de reference;
- validation et journalisation des pas adaptatifs, avec plafond explicite des
  coupures et tests de reduction, croissance, rollback et erreurs d'entree;
- ajout de `VNV-J2-NONLINEAR-METHODS-004`: accord Newton complet/Armijo sur la
  reponse axiale et caracterisation de l'echec de Newton modifie en inversion
  plastique;
- ajout du checkpoint/restart non lineaire NPZ atomique avec deplacements,
  facteur de charge, etats J2 committes, empreinte physique et preuve
  d'identite entre calcul continu et repris;
- ajout des diagnostics incrementaux non lineaires: corrections, travaux
  interne/externe trapezoidaux, desequilibre, coupures et commit;
- ajout de `VNV-J2-STEP-SENSITIVITY-005` sur `12/24/48` increments avec
  comparaison des retournements et de l'etat final;
- ajout du noyau de recherche TET4 total lagrangien Saint-Venant-Kirchhoff,
  avec objectivite, energie et tangente consistante verifiees;
- extension de `VNV-TET4-TL-ASSEMBLY-002` a
  `192/648/1536/5184/12288/24000` elements: invariants assembles `PASS`,
  variation finale de fleche `3,81 %` et ecart elastica `6,91 %`;
- ajout de `VNV-TET4-TL-STEPS-004`: identite de la fleche avec `6/10/12/24`
  increments a `8,10e-16` relatif; minimum technique `6`, valeur recommandee
  et valeur par defaut `10`;
- ajout de `VNV-TET4-TL-CALCULIX-003` sur six maillages identiques C3D4;
  ecart maximal de fleche QF_solver/CalculiX `1,86e-7` relatif;
- ajout d'un oracle d'elastica Euler sous charge morte et de courbes de
  convergence/deformee pour la revue mecanique;
- vectorisation de la force et tangente TET4-TL avec cache de la geometrie de
  reference; les trois anciens niveaux sont acceleres d'environ `28,8x` sur la
  machine de campagne;
- ajout d'une evaluation de force interne TET4-TL sans construction inutile
  de la tangente pendant la recherche lineaire;
- ajout au plan P6 du futur perimetre composites: orthotropie, theorie des
  stratifies, MITC4 multicouche, criteres de rupture et campagne V&V;
- ajout de `postprocess-large`: contraintes, deformations, von Mises, volumes
  et energies TET4 ecrits par blocs HDF5 avec checkpoint atomique et reprise;
- preuve sur `477 042` TET4: reprise apres `131 072` elements, environ
  `536k elements/s` et accord energetique solveur/post-traitement `4,14e-13`;
- ajout de `benchmark-large --restart-from`, avec validation SHA-256 du modele
  et lecture de la tranche de deplacement possedee par chaque rang; reprise
  PETSc quatre rangs en zero iteration et ecart de deplacement nul;
- ajout de `petsc-tuning-report` et de cinq presets GAMG/Hypre executes dans
  des processus MPI separes sur bloc, poutre et plaque;
- campagne de quinze calculs `PASS`, ecart deplacement maximal `1,96e-11`;
  GAMG seuil `0.01` gagne `18,0/5,3/7,3 %`, mais GAMG par defaut est conserve
  car le seuil de gain `10 %` n'est pas atteint sur toutes les topologies;
- ajout de `petsc-profile-report` et d'une campagne `-Action profile` sur bloc,
  poutre et plaque a environ 254k DDL, avec journaux `-log_view`, rapports
  JSON/Markdown, manifeste et diagnostics des communications/evenements;
- campagne PETSc quatre rangs multi-topologie `PASS`: `49/161/136` iterations
  et `1,96/6,24/5,11 s` dans `KSPSolve`; le setup GAMG reste voisin de
  `0,55-0,61 s` et le defaut n'est pas modifie;
- ajout de `large-preconditioners` et `large-scaling-report`, avec comparaison
  des deplacements par blocs, rapports JSON/Markdown et preuves SHA-256;
- comparaison 1M/4 rangs GAMG contre Hypre/BoomerAMG: accord `3,40e-12`, GAMG
  retenu car plus rapide et plus leger sur le cas mesure;
- activation tracee du repartitionnement des grilles grossieres GAMG a partir
  de quatre rangs et separation des temps setup/iterations KSP;
- campagne de scalabilite faible 1/2/4 rangs, classee `WARNING` avec une
  efficacite minimale de `41,6 %`;
- lecture PETSc multi-rangs par hyperslabs HDF5, connectivite locale et table
  compacte des noeuds references, sans replication des grands tableaux;
- sortie distribuee `displacements.bin` par MPI-IO collectif, sans
  rassemblement sur le rang racine, avec metadonnees, controle de taille et
  manifeste SHA-256;
- executions distribuees `PASS` sur quatre rangs a `1 029 000` DDL en
  `25,30 s` et `3 000 000` DDL en `64,00 s`, avec residus inferieurs a
  `1,1e-18`;
- ajout d'un runtime Docker PETSc/MPI epingle, avec `mpi4py 4.1.2`,
  PETSc/`petsc4py 3.25.1` et `h5py 3.13.0`;
- correction du backend PETSc multi-rangs : partition contigue des elements,
  matrice/vecteur distribues, Dirichlet homogene symetrique et rassemblement
  des deplacements uniquement sur le rang racine;
- execution `PASS` des jalons `107 811` et `1 029 000` DDL sur deux rangs,
  avec residus `1,82e-15` et `5,22e-15` et preuves SHA-256;
- vectorisation batchee des gradients, matrices `B` et rigidites TET4, avec
  gains d'assemblage `x10,36` a 100k et `x2,88` a 1M sans ecart numerique;
- assemblage PETSc BAIJ par blocs nodaux `3x3`, conversion AIJ avant GAMG et
  execution `PASS` du cas 3M en `88,68 s` avec residu `9,00e-19`;
- scalabilite forte 1/2/4 rangs sur 1M, avec acceleration maximale `1,65` et
  efficacite quatre rangs `41,18 %`;
- ajout de `large-campaign` pour planifier ou executer une serie TET4
  `100k/1M/3M+`, avec readiness par niveau, rapports JSON/Markdown, preuve
  SHA-256 et distinction explicite entre montee en taille et scalabilite MPI;
- ajout de la telemetrie RSS processus en complement de `tracemalloc` pour les
  benchmarks grands modeles;
- extension de `VNV-MITC4-MODAL-CODEASTER-DKQ-004` a dix modes sur `32x32`:
  ecart maximal QF/Code_Aster `1,609 %`, MAC minimal `0,999998493`;
- ajout de `VNV-MITC4-MODAL-EXTENDED-005`: structure assemblee libre-libre,
  coque cylindrique distordue et `eigsh` sur `7011` DDL actifs, tous `PASS`;
- ajout d'une grille de revue modale independante qui doit etre signee par une
  personne autre que l'auteur avant qualification externe;
- gel du scope dynamique sur la masse coherente; les formulations `lumped` et
  `concentrated` sont documentees hors scope et rejetees explicitement;
- tentative de validation interne du scope `mitc4-modal` par Quentin Farinazzo
  le `2026-07-16`, decision provisoire `accepted_with_recommendations`;
- ajout des histoires Newmark independantes par contribution de charge, du
  calage de Rayleigh sur deux cibles modales et de leur tracabilite;
- ajout de `VNV-MITC4-NEWMARK-OPERATIONAL-006`: superposition, decroissance
  analytique et identite calcul continu/reprise checkpoint `PASS`;
- validation mecanique interne du scope `mitc4-transient-dynamic` par Quentin
  Farinazzo le `2026-07-16`, decision `accepted_with_recommendations`, revue
  Markdown/PDF et registre machine-readable controles;
- ajout de `VNV-MITC4-NEWMARK-BROADBAND-004`: impulsion demi-sinus, chirp,
  table arbitraire, contraintes transitoires de face, bilan d'energie et
  convergence temporelle face a un oracle modal par exponentielle de matrice;
- ajout de la correlation locale Code_Aster `18.1.0` DKQ transitoire sur le
  meme maillage `8x8`: correlations `0,9543` en `UZ` et `0,9560` en `S11`,
  ecarts de pic `5,20 %` et `10,51 %`, verdict `PASS`;
- ajout des lois `half_sine_pulse` et `linear_chirp`, de leur validation
  stricte et des sondes `history_shell_stress_probes`;
- gel par SHA-256 des six preuves harmoniques dans
  `qualification/baselines/mitc4_harmonic_2026-07-15.json`; la baseline code
  reste candidate jusqu'a un commit Git propre;
- ajout de la correlation locale Code_Aster `18.1.0` DKQ sur NAFEMS 13H:
  ecarts QF_solver de `3,364 %` en frequence, `1,900 %` en deplacement et
  `3,272 %` en contrainte `S11`, avec verdict `PASS`;
- ajout du runner Docker epingle, du maillage ASTER, de la reconstruction
  testee de `S11`, du rapport Markdown et de la figure comparative;
- ajout des contraintes harmoniques complexes MITC4 `S11/S22/S12`, avec reel,
  imaginaire, amplitude et phase par face, element et frequence;
- correlation `S11` NAFEMS 13H: `30,819 MPa` pour QF_solver, ecarts `1,477 %`
  a Abaqus S4R, `1,412 %` a S4, `2,626 %` a NAFEMS et `3,730 %` a Navier;
- decision interne du scope harmonique MITC4 portee a
  `accepted_with_recommendations` par Quentin Farinazzo le `2026-07-15`;
- ajout de `VNV-MITC4-HARMONIC-BROADBAND-003`: excitation decentree de
  `0,1-16 Hz`, quatre familles de resonance et comparaison plein champ a une
  superposition complete de `175` modes, avec erreur maximale `2,411e-7`;
- ajout de `VNV-MITC4-HARMONIC-NAFEMS13H-004`: reproduction du Test 13H
  publie par Abaqus/Standard, avec ecarts S4R de `2,442 %` en amplitude et
  `0,866 %` en frequence;
- ajout d'une fiche de revue harmonique controlee, techniquement prete mais
  explicitement non signee et `pending`;
- ajout d'une correlation externe controlee avec la table Abaqus/Standard S4R
  publiee pour le cylindre pince, incluant provenance, limites, rapport et PNG;
- ajout de la masse coherente MITC4, incluant masse surfacique et inerties
  rotatoires Reissner-Mindlin sans inertie artificielle de drilling;
- ajout d'une condensation objective des directions de drilling sans masse,
  avec reconstruction des six ddl pour le modal et Newmark;
- ajout des scopes `mitc4-modal` et `mitc4-transient-dynamic`, de deux formules
  controlees et des exemples CLI/API associes;
- ajout de `VNV-MITC4-SHEAR-LOCKING-001`: 160 calculs epaisseur, maillage et
  distorsion, erreur fine maximale `2,08 %` et Q4 verrouillant temoin;
- ajout des convergences MITC4 Cook, Scordelis-Lo et cylindre pince, avec six
  niveaux Cook (`4,52 %` a `64x64`) et cinq niveaux Scordelis-Lo (`0,31 %`) et
  cylindre pince (`7,26 %`);
- extension Cook a `64x64` et point isole `200x200` (40 000 elements), montrant
  une reponse stabilisee vers `0,2515` et declenchant une revue de reference;
- justification de `drilling_scale=1e-4` par une sensibilite de `1e-6` a
  `1e-2`, avec variation de plateau maximale `9,50e-6`;
- ajout du runner `scripts/run_mitc4_vnv.py`, de rapports Markdown, PNG et
  manifeste de preuves; correlation Abaqus a maillage identique maintenue en attente;
- ajout de la sonde de contrainte de torsion h9 a `105 529` TET4, soit
  `4,007` fois h8, avec assemblage creux chunked, CG/Jacobi et manifeste;
- passage de l'erreur globale L2 de contrainte de `29,06 %` a `18,89 %`,
  sous un seuil engineering borne de `20 %` pour l'arbre circulaire lisse;
- ajout des PNG h9 QF_solver/Saint-Venant pour la deformee, le von Mises et
  l'ecart de contrainte, publies automatiquement dans le site apres controle
  SHA-256;
- ajout de l'etude V&V TET4 de torsion sur huit maillages, avec champs
  QF_solver/Saint-Venant comparables, PNG, VTU, empreintes et Markdown;
- ajout de `import_torsion_vnv_study` et du cas torsion a
  `vnv-import-benchmark`;
- decision interne de torsion portee a `accepted` apres la sonde h9, avec
  maintien explicite des pics ponctuels et singularites hors domaine accepte;
- ajout du lanceur `qf-solver-docs` / `scripts/serve_docs.py`, limite a
  `127.0.0.1`, pour ouvrir le manuel dans le navigateur systeme sans lien
  local cliquable dans une interface de developpement;
- suppression des badges de statut parasites dans la navigation et
  renforcement du contraste du titre principal.

### Identite QF_solver et benchmarks mailles

- Adoption de l'identite publique `QF_solver`, distribution `qf-solver`, CLI
  `qf-solver` et lanceur `qf_solver.py`.
- Conservation temporaire de `solveur-ef` et `main_solveur.py` avec
  avertissement de deprecation jusqu'a 0.3.0.
- Ajout de l'import Gmsh MSH 4.1 ASCII/binaire, groupes physiques, charges,
  remappage deterministe et rapport d'import SHA-256.
- Ajout du catalogue controle de huit benchmarks structures mailles et des
  commandes `benchmarks` et `benchmark`.
- Ajout des pages individuelles, deformees, champs, criteres et artefacts MSH,
  JSON et VTU regeneres pour les huit benchmarks.
- Decoupage des formulations TET4, TET10 et MITC4 en cinq chapitres chacune.
- Correction de l'ordre des deux dernieres aretes TET10 lors de l'import Gmsh.
- Correction critique de la transformation des gradients TET10 de
  $J^{-1}$ vers $J^{-T}$, protegee par un patch test oblique.

### Durcissement P0

- Ajout du site technique MkDocs Material hors ligne, organise par fondements,
  elements, solveurs, demonstrations, verification et reference.
- Migration du manuel theorique monolithique vers 79 pages controlees et un
  registre documentaire machine-readable; l'ancien chemin devient une
  redirection de compatibilite.
- Ajout d'une campagne documentaire reproductible generant deformees, courbes,
  tableaux, modeles, resultats et manifeste SHA-256 depuis l'API publique.
- Ajout de MathJax local, du profil de construction `engineering` et du gate
  `qualification` exigeant revision Git et revues documentaires approuvees.
- Ajout des controles documentaires et visuels responsifs sous Playwright.
- Ajout de la tracabilite executable de 18 formules TET4, TET10 et MITC4 vers
  exigences, sections, fonctions, tests et references.
- Ajout d'une convergence h TET4 calculee sur quatre maillages Gmsh, avec
  ordre observe, monotonie, erreur fine et residus comme criteres executables.
- Separation du statut numerique et de `RunVerdict`, avec codes de sortie
  stables `0`, `2`, `3`, `4`, `5`.
- Ajout du registre machine-readable des exigences et de la readiness par
  scope.
- Passage du manifeste de preuve en v2, compatible en lecture avec v1.
- Correction de la tangente algorithmique J2 et du post-traitement TET10
  chemin-dependant.
- Rejet explicite des singularites, valeurs non finies et parametres
  dynamiques instables.
- Ajout de la CI Windows/Linux Python 3.10/3.13, couverture de branches,
  typage progressif et baselines verrouillees.
- Ajout d'une factorisation LU sparse reutilisable pour Newmark et suppression
  de la conversion dense de la masse initiale.
- Passage du modal par defaut a `eigsh` et ajout de la garde
  `dense_modal_max_dofs` avant `eigh`.
- Remplacement de la masse concentree TET10 par une masse coherente integree.
- Ajout des controles TET10 de noeuds d'arete et de jacobiens echantillonnes.
- Ajout de l'extrapolation nodale elastique TET10 et de la campagne
  `verify-tet10` avec patch, energie et convergence.
- Ajout des chargements repartis coherents TET4/TET10/MITC4: pesanteur,
  force volumique, pression, traction de surface et traction de bord MITC4.
- Ajout du bilan force/moment par contribution dans les resultats et l'audit,
  avec validation stricte, exemple CLI/API et tests analytiques.

## 0.1.0 - qualification-ready baseline

- Ajout des profils de verification `quick`, `engineering`, `strict` et
  `qualification`.
- Ajout du dossier de preuve `evidence` via CLI et API.
- Ajout du resume `qualification_summary` dans les resultats JSON.
- Ajout des metadonnees auditables: version solveur, schema JSON, unites,
  profil de verification, maturite et niveau de preuve.
- Ajout de la matrice de qualification dans `docs/qualification_matrix.md`.

## Politique de version

- `patch`: correction sans changement volontaire de schema ou de resultat.
- `minor`: nouvelle fonctionnalite compatible.
- `major`: changement de schema, d'API ou de comportement numerique attendu.
