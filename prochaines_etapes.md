# Prochaines etapes du solveur EF

## Etat de la baseline

Le socle fonctionnel couvre TET4, TET10, MITC4, statique lineaire, modal,
Newmark, harmonique, non-lineaire experimental et grand modele. La
documentation technique MkDocs est construite hors ligne et ses resultats
sont recalcules par l'API publique.

Le tableau de bord genere est la source autoritative pour le nombre de tests,
les verdicts et la revision source. Le projet n'est pas certifie : il vise une
qualification progressive sur des perimetres bornes.

La version 0.2.0 ajoute l'identite QF_solver, l'import Gmsh MSH 4.1 et dix
benchmarks mailles reproductibles. Les criteres mecaniques de ces dix cas
passent; TET10 courbe et J2 restent volontairement en `WARNING` experimental.

## Regles de lecture de la feuille de route

Les cases cochees constituent des constats dates et des preuves historiques;
elles ne remplacent ni le registre de maturite ni une decision Owner par
perimetre. Les nombres de tests, d'artefacts et les performances chiffres ici
sont des instantanes de campagne : le tableau de bord genere reste la source
active.

La politique d'oracle externe active est exclusivement
`theorie -> Code_Aster -> CalculiX`, telle que figee dans
`qualification/external_oracle_policy.json`. Les resultats issus de logiciels
commerciaux ou de tables publiees peuvent etre archives comme contexte
historique, mais ils ne constituent ni une dependance, ni un critere bloquant
de la feuille de route.

## Frontiere de publication V1 / V2

Decision de produit : fermer une premiere version publique utile et
decouvrable avant d'elargir davantage la mecanique.

La V1 ajoute uniquement les trois blocs fonctionnels suivants au socle actuel :

1. elements d'assemblage : `BEAM2`, ressorts, masses concentrees, contraintes
   multipoints et liaisons de type RBE ;
2. contact mecanique : sans frottement en premier, puis frottement de Coulomb
   regularise ;
3. coque triangulaire `MITC3+` a trois noeuds, necessaire pour les maillages
   surfaciques qui ne peuvent pas etre constitues uniquement de quadrangles.
   Son objectif fonctionnel est d'offrir, a terme, les memes familles
   d'analyse et de materiaux que `MITC4`, sans supposer que leurs precisions
   ou leurs domaines de validation sont identiques.

Les autres familles proposees, notamment HEX8, WEDGE, PYRAMID, thermique,
thermoelasticite, `generalized-alpha`, spectres, PSD, hyperelasticite,
endommagement, raffinement adaptatif et sous-structuration avancee, sont
reportees en V2. Elles ne bloquent pas la publication de la V1.

La V1 pourra publier des fonctions de maturites differentes. Une fonction
`experimental` restera accessible si son statut, ses limites et ses preuves
sont visibles; elle ne sera pas presentee comme qualifiee.

## P-OSS - Transition vers une bibliotheque Python open source

Objectif final : publier QF_solver comme bibliotheque Python FEM boite blanche,
installable, documentee et reproductible. La traduction anglaise du site et
des interfaces est reportee apres stabilisation technique; elle ne doit pas
dupliquer les sources de verite francaises avant la mise en place d'une chaine
de traduction controlee.

- [x] figer l'identite publique `qf-solver`, la facade `solveur.api`, les URLs
  de distribution et les regles de version de l'API ;
- [x] preparer contribution, support, securite, conduite, citation et
  formulaires distincts pour defauts et V&V ;
- [x] documenter une checklist de publication et figer la politique de licence
  `Apache-2.0` pour le code et `CC BY 4.0` pour la documentation et les
  exemples originaux ;
- [x] supprimer les references publiques au mode de travail interne, remplacer
  les instructions de developpement par un guide neutre et ajouter un audit
  bloquant de confidentialite avant archive publique ;
- [x] exclure des archives Git les resultats locaux, sites generes, dossiers
  temporaires et etudes V&V de travail; les preuves publiees seront choisies
  explicitement lors de la release ;
- [x] formaliser la frontiere public/prive : une archive `export-ignore` ne
  rend pas prive un fichier commite; les donnees locales, notes de travail,
  configurations de machine et contenus non publics restent hors de
  l'historique du depot public ;
- [ ] realiser un audit humain de l'historique Git, des fichiers suivis et des
  changements indexes; si necessaire, creer un depot public a historique
  propre avant la premiere publication ;
- [ ] definir et revoir les URLs publiques (depot, documentation, paquets,
  releases) avant toute mise en ligne; aucune URL locale ou interne ne doit
  etre publiee ;
- [ ] separer durablement les preuves V&V publiees des etudes de travail
  privees : publier uniquement des paquets relus, compacts et reproductibles ;
- [x] choisir les licences avec revue initiale des dependances et ajouter
  `LICENSE`, `LICENSE-DOCS`, `NOTICE` et `THIRD_PARTY_LICENSES.md` ; la
  verification finale des artefacts publics reste une action Owner ;
- [ ] analyser et purger les donnees, chemins locaux, preuves et modeles qui
  ne peuvent pas etre rendus publics ;
- [ ] publier une premiere release taggee avec archives, notes de version,
  hashes et politique de support explicite ;
- [ ] etablir un processus de revue externe des pull requests et des etudes
  V&V avant toute hausse de maturite ;
- [ ] concevoir la traduction anglaise a partir d'identifiants documentaires
  stables, avec controle des formules, tableaux et verdicts dans les deux
  langues.

## P0 - Fermer la baseline documentaire

Statut : **baseline technique et Owner review documentaire fermees;
revue independante et qualification externe volontairement BLOCKED**. Le dossier de cloture est
`docs/verification/baseline_documentaire_p0.md`.

- [x] definir un contrat V&V generique `study.json` + sorties normalisees,
  comparaison automatique et rapport Markdown obligatoire ;
- [x] declarer Quentin Farinazzo comme auteur et validateur mecanique en
  `self_review`, sans revendiquer une independence inexistante ;
- [x] retirer les logiciels commerciaux des dependances actives : la politique
  `theorie -> Code_Aster -> CalculiX` est acceptee le `2026-07-26` dans
  `qualification/external_oracle_policy.json`; les valeurs publiees restent
  des references historiques non bloquantes ;
- [x] relire le dossier technique consolidant TET4, TET10, MITC4, MITC3+,
  BEAM2, composite borne et methodes : owner review finale enregistree le
  `2026-08-01`, decision `accepted_with_recommendations` ;
- [ ] renseigner les champs `reviewer` et `approver` apres revue independante :
  action humaine, volontairement non pre-remplie ;
- [x] approuver une premiere revision Git, figer les dependances et enregistrer
  la baseline engineering `0.2.0` dans `qualification/baselines/` ;
- [x] classer 61 formules critiques par `REQ-*`, code, fonction, test et
  reference dans `qualification/formulas.json` ;
- [x] traiter toute anomalie de lien, formule, figure ou resultat comme une
  anomalie de configuration ;
- [x] conserver `qualification` bloquant tant que la baseline n'est pas propre et
  approuvee.

Le rapport genere `docs/generated/review_readiness.json` separe couverture
automatique, Owner review et baseline Git. Aucun champ de signature n'est
pre-rempli par le solveur.

Critere de sortie : `mkdocs build --strict`, tests documentaires et revue
humaine sont verts sur Windows et Linux.

## P-DOC - Demonstrations documentees et accessibles par la librairie

Objectif : rendre chaque capacite mecanique demonstrable de deux manieres
coherentes : par une page technique lisible par un ingenieur et par une entree
reproductible de la librairie Python. Le catalogue ne doit pas etre une simple
liste de figures : chaque demonstration doit relier formulation,
implementation, test, resultat et reference bibliographique.

- [x] conserver un catalogue de benchmarks machine-readable avec identifiant,
  famille d'element, analyse, maturite, criteres, exigences et reference HTTPS
  dans `qualification/benchmarks.json` ;
- [x] creer `qualification/demonstrations.json` comme registre transverse de
  vingt-huit demonstrations : onze benchmarks mailles, dix cas V&V executes
  par `QualificationCampaignRunner.run_case()`, six exemples JSON avec dossier
  de preuve v2 et un plan PETSc/MPI 1M DDL sans allocation. Le catalogue couvre
  deja TET4/TET10/MITC4 statique, modal, Newmark, harmonique, J2, orthotropie,
  multicouche et la preparation grand modele; l'execution massive reste une
  campagne d'infrastructure separee ;
- [x] imposer pour chaque entree : `demo_id`, element ou methode, hypotheses,
  modele d'exemple, runner, page documentaire, tests, exigences, maturite,
  references `REF-*`, DOI ou URL, sorties attendues et limites. Le controle
  `DemonstrationCatalog.validate_integrity()` refuse un benchmark, modele,
  page, runner, test, exigence, reference ou sortie minimale orphelin ;
- [x] ajouter dans `solveur.api` `list_demonstrations()`, `run_demonstration()`
  et `run_qualification_case()` avec filtrage par famille, methode et maturite.
  Les fonctions retournent le descripteur, les references et les artefacts de
  preuve; les cas V&V conservent obligatoirement le profil fige du manifeste ;
  des sorties sans dependre du site web ;
- [x] conserver `list_benchmarks()` et `run_benchmark()` comme interface
  retrocompatible pour les onze benchmarks mailles existants ;
- [x] produire une page Markdown par element et par methode comprenant :
  geometrie, ddl, formulation mathematique, integration, algorithme, exemple
  executable, maillage, chargement, conditions limites, tableau de resultats,
  figure de deformee, invariants, convergence, limites et references ; les
  23 pages controlees de `qualification/documentation_review_pages.json`
  couvrent les elements, entites, contacts et methodes disponibles ;
- [x] relier chaque formule importante a un identifiant `FORM-*` ou `REQ-*`,
  une fonction de code, un test et une entree de `docs/reference/references.md`;
  les 44 formules critiques sont controlees par `qualification/formulas.json`
  et le rapport de readiness documentaire ;
- [x] couvrir au minimum les demonstrations TET4 traction/compression,
  membrane et torsion; TET10 patch, flexion et courbe; MITC4 membrane,
  flexion, cisaillement, locking, modal et Newmark; puis les variantes
  orthotropes, multicouches, harmoniques, J2 et grand modele. Le registre
  public contient 28 demonstrations controlees ;
- [x] faire regenerer par l'API les PNG, tableaux, JSON/VTU, rapports Markdown
  et empreintes SHA-256. Aucune valeur numerique ne doit etre recopiee
  manuellement dans la documentation. La campagne engineering du
  `2026-07-29` a regenere 625 artefacts avec manifeste `PASS` ;
- [x] ajouter un test de completude refusant une demonstration orpheline :
  `DemonstrationCatalog.validate_integrity()` controle le benchmark, le modele
  JSON ou generateur explicite, la page, le runner, les exigences, les
  references, les tests et les sorties minimales; les cas negatifs sont dans
  `tests/unit/test_demonstration_registry.py` ;
- [x] publier le catalogue dans le site hors ligne et dans le paquet Python,
  sans inclure de chemins locaux, donnees privees ou contexte d'execution.
  `docs/generated/demonstration_registry.md` est derive du registre
  machine-readable et `list_demonstrations()` expose la meme source ;
- [x] faire realiser une Owner review de chaque page avant de changer sa
  maturite. Les 23 pages ont une decision `accepted_with_recommendations`
  enregistree; une demonstration documentee ne vaut pas, a elle seule,
  qualification.

Critere de sortie : un ingenieur peut partir d'un identifiant de demonstration,
lancer le cas via l'API, lire la formulation et retrouver la reference
bibliographique, les tests et les artefacts correspondants sans chercher dans
des scripts internes.

## P1 - Qualification TET4 statique lineaire

Objectif : obtenir le premier perimetre candidat a une qualification interne.

- [x] completer traction, compression, pression et patch contrainte constante ;
- [x] enregistrer le 14 juillet 2026 l'acceptation engineering interne du
  TET4 lineaire isotrope par Quentin Farinazzo, en auto-revue non independante
  et sans revendication de certification externe ;
- [x] ajouter un panneau mince TET4 sollicite dans son plan, avec champ affine,
  resultante membranaire, cinq maillages en traction et cinq en compression,
  VTU et PNG regeneres ;
- [x] ajouter un arbre circulaire TET4 en torsion de Saint-Venant, avec huit
  maillages, traction terminale coherente, couple, rotation, contraintes, VTU
  et PNG regeneres ;
- [x] produire l'etude `VNV-TET4-TORSION-ANALYTIC-001`, avec huit paires de
  deformees QF_solver/Saint-Venant, resultats normalises, empreintes et rapport
  Markdown ;
- [x] ajouter la sonde `VNV-TET4-TORSION-STRESS-H9-001` a `105 529` TET4,
  soit `4,007` fois h8, et accepter le champ global L2 de contrainte a
  `18,891 %` sous le seuil engineering borne de `20 %` ;
- [x] retirer les etudes externes non reproductibles du plan actif ; la
  comparaison retenue est `theorie -> Code_Aster -> CalculiX`, selon
  `qualification/external_oracle_policy.json` ;
- [x] statuer sur le perimetre TET4 lineaire isotrope; accepter la contrainte
  globale L2 du cas de torsion lisse et conserver hors acceptation les pics
  ponctuels, singularites et extrapolations a d'autres geometries ;
- faire relire independamment le patch TET4 Gmsh et sa reference analytique ;
- [x] ajouter une convergence h quantitative avec ordre observe sur six
  maillages Gmsh, seuil executable et courbe regeneree ;
- [x] qualifier les cas canoniques de pression, force volumique et reactions
  globales; etendre ensuite cette preuve aux maillages multi-elements ;
- [x] borner conditionnement, qualite de maillage et domaine materiau TET4
  dans `tet4-linear-static-v1`, avec politique executable par profil ;
- [x] produire et verifier un dossier de preuve v2 reproductible pour chaque
  cas resolu de la campagne ;
- [x] ajouter un oracle analytique TET4 independant du noyau EF pour traction,
  compression et force volumique, puis le relier a la campagne ;
- mettre en place couverture MC/DC ou justification adaptee uniquement si le
  niveau d'assurance retenu l'exige.

Critere de sortie : aucune exigence orpheline dans le scope
`tet4-linear-static`, aucune anomalie ouverte de severite bloquante, dossier de
preuve relu independamment.

## P2 - Coques MITC4

- [x] figer conventions de repere local et signes faces superieure/inferieure ;
- [x] renforcer patchs membrane, flexion et cisaillement ;
- [x] automatiser une matrice de shear locking de 160 calculs croisant cinq
  maillages, quatre epaisseurs, quatre distorsions et un Q4 temoin ;
- [x] ajouter une courbe de convergence publiee sur six maillages pour Cook et
  cinq maillages pour Scordelis-Lo et le cylindre pince ;
- [x] archiver une table publiee de cylindre pince comme repere historique
  non bloquant (`4,87 %`) ;
- [x] executer le point Cook `64x64` puis `200x200` (40 000 elements) pour
  ecarter une divergence numerique ;
- [ ] auditer independamment la reference et les conditions aux limites Cook:
  la fleche converge vers environ `0,2515`, pas vers la reference `0,2396` ;
- [x] executer CalculiX ou Code_Aster sur un maillage strictement identique
  pour fermer la correlation externe statique : `VNV-MITC4-CONICAL-CUTOUT-
  CODEASTER-DKQ-014` reprend les trois maillages QUAD4, le vecteur de pression
  coherent et les appuis; l'ecart fin vaut `0,3436 %` a la sonde, `1,7565 %`
  sur le vecteur et `2,26e-11 %` sur la resultante de reaction ;
- [x] verifier la distorsion jusqu'a 30 %, le warping par le gate maillage et
  l'energie de rotation de percage ;
- [x] ajouter `VNV-MITC4-CONICAL-CUTOUT-STATIC-012` : panneau annulaire
  conique facettise, ouverture centrale libre, pression normale coherente,
  trois maillages et export PNG/VTU. Cette preuve geometrie complexe est
  supplementaire; elle ne modifie pas l'acceptation statique existante ;
- [x] correler cinematiquement le panneau conique ajoure sur les memes maillages
  avec CalculiX 2.20 S4 (`VNV-MITC4-CONICAL-CUTOUT-CALCULIX-S4-013`) : ecart
  sonde fin `0,0249 %`, ecart vectoriel fin `0,629 %`. Les pics de contrainte
  au bord libre restent publies mais ne sont pas utilises seuls comme critere ;
- [x] fermer la correlation de resultante du panneau conique : la sortie
  CalculiX `RF` reste un diagnostic ambigu avec `CLOAD`, mais Code_Aster
  `REAC_NODA` sur les translations du bord encastre ferme la comparaison de
  resultante au meme maillage (`2,26e-11 %` au niveau fin). Les energies et
  contraintes de faces restent des comparaisons distinctes ;
- comparer resultantes, contraintes de faces et energies a une reference
  independante.

Le perimetre `mitc4-linear-static` est valide pour `engineering_internal` avec
recommandations, tout en restant `candidate` dans le registre de qualification.
Sa matrice locking fine presente une erreur maximale de `2,08 %` face a
Timoshenko et un ratio limite mince de `0,979`. La correlation publiee du
cylindre pince est `PARTIAL_PASS`; une correlation reproductible Code_Aster ou
CalculiX sur maillage identique reste necessaire pour une decision au-dela de
`engineering_internal`.

Critere de sortie : domaine d'emploi MITC4 borne et justifie, avec tendances de
convergence et limites explicitement publiees.

## P2B - Coque triangulaire MITC3+

Objectif V1 : ajouter un element coque triangulaire a trois noeuds pour traiter
les maillages non structures, les raccords topologiques et les surfaces pour
lesquelles un remailleur ne peut pas garantir des quadrangles. Le nom public
sera `MITC3`; la formulation implementee sera documentee comme `MITC3+`.

Le plan de conception et de V&V autoritatif est
`docs/elements/mitc3_plan_implementation.md`.

- [x] figer la formulation `MITC3+` lineaire : triangle a trois noeuds,
  cinematique Reissner-Mindlin, six DDL par noeud, enrichissement interne des
  rotations par bulle cubique et condensation statique locale ;
- [x] conserver 18 DDL assembles et ne jamais exposer les deux parametres
  internes de bulle dans le format JSON, l'API ou les resultats nodaux ;
- [x] definir le repere local, l'ordre nodal, la normale, les signes de
  courbure, les faces `z=+t/2` et `z=-t/2`, ainsi que la compatibilite de bord
  avec MITC4 ;
- [x] implementer rigidite, masse coherente, charges nodales, pression,
  traction surfacique, traction de bord, gravite et force volumique ;
- [x] supporter `shell_isotropic`, puis `shell_laminate` avec matrices
  `A/B/D`, cisaillement transverse, orientation projetee des plis et resultats
  par pli. Le composite reste `experimental` jusqu'a sa campagne dediee ;
- [x] integrer `MITC3` au registre d'elements, au schema JSON, a l'import Gmsh
  TRI3, au controle maillage, aux exports JSON/CSV/VTU et au post-traitement ;
- [x] ajouter les scopes separes `mitc3-linear-static`, `mitc3-modal`,
  `mitc3-transient-dynamic`, `mitc3-harmonic-response` et
  `mitc3-laminate-static` ;
- [x] enregistrer la decision finale Owner sur la statique lineaire isotrope
  le `2026-08-01`, puis accepter modal, Newmark et harmonique le
  `2026-08-02` apres verification de la masse et de la condensation des
  directions sans inertie ;
- [x] completer le patch de flexion explicite et la correlation externe sur
  coque doublement courbe. Le patch de cisaillement constant atteint
  `1,81e-16`; les modes rigides, l'isotropie, l'objectivite, le patch
  membrane, le shear locking, la distorsion, la convergence h et le melange
  `MITC3`/`MITC4` sont couverts par la campagne raffinee `PASS` ;
- [x] comparer le meme maillage de 512 triangles a Code_Aster 18.1.0 DKT :
  ecart membrane `5,96e-8` et flexion `0,007116 %`, verdict
  `PASS_EXTERNAL_CORRELATION` ;
- [x] executer CalculiX 2.20 S3 comme temoin : membrane `0,0086 %`, mais
  flexion trop raide avec `113,086 %` d'ecart; conserver ce resultat en
  `WARNING` et ne pas utiliser S3 comme oracle positif de flexion ;
- [x] raffiner Scordelis-Lo a `20 000` triangles et le cylindre pince a
  `19 600` triangles : erreurs finales `0,4044 %` et `2,0899 %`, avec
  courbes, champs, manifestes et dossier PDF de revue ;
- [x] ajouter l'hemisphere pince a quatre quadrants sur six raffinements et le
  comparer sur les memes maillages a Code_Aster 18.1.0 DKT : au niveau fin,
  ecart a la reference publiee `0,5912 %`, ecart sonde QF/Aster `0,0927 %`,
  ecart de champ nodal `0,1536 %` et increment final `0,2605 %` ;
- [ ] ajouter une reference NAFEMS triangulaire supplementaire comme oracle
  secondaire trace; cette action est recommandee mais non bloquante ;
- [x] publier les formulations forte et faible, les matrices, les points de
  tying, la condensation, les demonstrations, les limites et les preuves sur
  le site technique ;
- [x] maintenir le statut `experimental` jusqu'a Owner review de la statique
  isotrope, puis faire evoluer chaque scope independamment.

Critere de sortie V1 : `MITC3` statique lineaire isotrope utilisable via JSON,
API, CLI et Gmsh, sans mode parasite, avec patch tests, campagne mince,
convergence h, correlation externe et dossier de preuve reproductible. La
parite complete avec MITC4 est un objectif progressif, pas un prerequis masque
pour publier le premier scope MITC3.

## P3 - Dynamique lineaire

La couverture element/analyse est suivie dans
`qualification/element_analysis_matrix.json` et
`docs/verification/matrice_elements_analyses.md`. La priorite n'est plus
seulement de verifier les algorithmes generiques, mais de fermer chaque couple
element/analyse avec sa propre convergence, son oracle et sa decision Owner.

- [x] ajouter les campagnes internes modales, Newmark et harmoniques
  `VNV-*-LINEAR-DYNAMICS-001` pour TET4, TET10, MITC3+, BEAM2 et
  ressort/masse : residus/orthogonalites, vibration libre du premier mode,
  energie et limite statique a `0 Hz`;
- [x] executer `VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020` : correlation
  Code_Aster `3D/TETRA4` sur 135 TET4, avec six modes, Newmark et harmonique
  sur les memes grilles; les ecarts externes sont inferieurs a `1e-9 %` et
  les scopes sont acceptes par l'Owner le `2026-08-02`;
- [x] fermer TET4 modal, Newmark et harmonique dans trois scopes Owner
  separes; conserver le raffinement structurel recommande ;
- [x] executer `VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018` : correlation
  Code_Aster `3D/TETRA10` sur 135 TET10, avec six modes, Newmark et
  harmonique sur les memes grilles; les ecarts sont inferieurs a `1e-9 %` et
  les convergences maillage/pas de temps passent;
- [x] fermer TET10 modal, Newmark et harmonique avec les Owner reviews
  distinctes; le raffinement Newmark maillage/pas de temps est enregistre ;
- [x] executer `VNV-MITC3-DYNAMICS-CODEASTER-DKT-017` : correlation externe
  meme maillage DKT sur six modes (`1,7367 %`), historique Newmark (`0,5496 %`
  RMS) et harmonique (`0,2998 %` RMS), sous le seuil declare de `10 %`;
- [x] fermer MITC3+ modal, Newmark et harmonique par trois Owner reviews
  distinctes; les preuves internes coque courbe, libre-libre, dix modes,
  raffinement temporel et correlation DKT sont disponibles. Le raffinement
  maillage-frequence reste une recommandation ;
- [x] executer `VNV-MITC3-DYNAMIC-EXTENDED-001` : structure libre-libre,
  six modes rigides analytiques, coque cylindrique raffinee et tournee,
  controle `eigh/eigsh` a 2 560 DDL retenus, Newmark et harmonique courbes;
- [x] ajouter `VNV-MITC3-LAMINATE-DYNAMIC-001` : patch membranaire
  analytique, masse coherente, condensation drilling, modal, Newmark et
  harmonique pour le stratifie plan symetrique `[0/90/90/0]`;
- [x] correl(er) les reponses globales MITC3+ multicouches modal, Newmark et
  harmonique sur le meme maillage avec Code_Aster DST dans
  `VNV-MITC3-LAMINATE-DYNAMICS-CODEASTER-DST-019` : ecarts maximaux de
  `3,957 %`, `2,318 %` et `1,345 %`, sous les seuils traces ;
- [x] correl(er) les contraintes planes `S11`, `S22`, `S12` de chaque pli
  MITC3+ avec CalculiX `2.20` `S6 COMPOSITE` dans
  `VNV-MITC3-LAMINATE-PLY-STRESS-CALCULIX-S6-020` : ecart L2 fin `0,09625 %`,
  increment CalculiX final `0,07313 %` sous `0,2 %` ;
- [x] executer la correlation MITC3+ multicouche courbe a orientation projetee
  `VNV-MITC3-LAMINATE-CURVED-PROJECTED-CALCULIX-S6-024` : panneau cylindrique
  facettise, empilement `[0/90/90/0]`, projection de la direction globale dans
  chaque facette et comparaison CalculiX `S6 COMPOSITE`. Les raffinements
  `96x48` puis `128x64` abaissent l'ecart vectoriel `UX/UZ` a `3,4437 %` puis
  `2,0738 %`, avec un increment QF final de `1,2273 %` et un residu libre de
  `3,2487e-10` ;
- [x] fermer le MITC3+ multicouche courbe par une Owner review dediee. Quentin
  Farinazzo accepte le perimetre au statut experimental pour la V0.2.0-alpha le
  `2026-08-09`. Les contraintes par pli, les quantites interlaminaires et les
  cas courbes dynamiques restent hors de cette preuve et sont recommandes pour
  une version ulterieure ;
- [x] fermer BEAM2 modal, Newmark et harmonique par correlations Code_Aster
  axiale et transverse elancee sur les memes grilles :
  `VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019` passe sous `1 %`;
  Owner accepte le domaine borne; la dynamique de poutre epaisse est exclue;
- [x] fermer les preuves externes ressort/masse Newmark et harmonique avec
  Code_Aster `18.1.0` `DIS_T` sur les memes grilles temporelles et
  frequentielles declarees (`VNV-DISCRETE-CODEASTER-SDOF-001`) : ecarts
  statique/modal/Newmark/harmonique de `1,39e-16`, `0`, `3,05e-11` et
  `1,87e-15`; Owner accepte le domaine SDOF translationnel sans amortissement
  ni couplage multi-DDL le `2026-08-02`;
- [ ] conserver la dynamique non lineaire hors V1 et la traiter dans un projet
  de formulation/V&V distinct.

- [x] ajouter la masse coherente MITC4 avec inerties translationnelles et
  rotatoires physiques, sans inertie artificielle de drilling ;
- [x] condenser les directions de drilling effectivement sans masse et
  reconstruire les six ddl nodaux ;
- [x] permettre MITC4 modal et Newmark via API, CLI et exemples JSON ;
- [x] modal : ajouter la convergence de frequence et MAC sur porte-a-faux
  mince (`VNV-MITC4-MODAL-CANTILEVER-002`) ;
- [x] modal : verifier une plaque simplement appuyee et les quatre premiers
  modes de Navier, dont la paire propre double (`VNV-MITC4-MODAL-PLATE-003`) ;
- [x] modal : executer Code_Aster `18.1.0` DKQ sur le meme maillage `32x32` et
  comparer dix modes; ecart maximal `1,609 %`, MAC minimal `0,999998493`
  (`VNV-MITC4-MODAL-CODEASTER-DKQ-004`) ;
- [x] modal : verifier une structure assemblee libre-libre, exactement six
  modes rigides et leur sous-espace analytique ;
- [x] modal : verifier une coque courbe, une distorsion de `20 %`, la
  convergence et l'objectivite par rotation ;
- [x] modal : comparer `eigh/eigsh`, puis executer dix modes sur `2304`
  elements et `7011` DDL actifs sans conversion dense ;
- [x] modal : tentative de validation interne enregistree le `2026-07-16`,
  decision `accepted_with_recommendations`, masse coherente uniquement; la grille est disponible
  en Markdown et PDF dans `docs/verification/revue_mitc4_modale.md` et
  `docs/assets/reviews/revue_mitc4_modale.pdf` ;
- modal : faire remplir la revue independante par une personne autre que
  l'auteur avant toute qualification externe ; modele dans
  `qualification/reviews/mitc4_modal_independent_review_template.md` ;
- [x] Newmark : verifier l'historique signe et la convergence d'ordre deux
  de `T/20` a `T/160` (`VNV-MITC4-NEWMARK-FREE-002`) ;
- [x] Newmark : verifier amortissement analytique et chargement modal force
  (`VNV-MITC4-NEWMARK-DAMPED-FORCED-003`) ;
- [x] Newmark : ajouter impulsion demi-sinus, chirp lineaire et table arbitraire,
  avec convergence temporelle et contraintes de face
  (`VNV-MITC4-NEWMARK-BROADBAND-004`) ;
- [x] Newmark : comparer sur le meme maillage `8x8` avec Code_Aster `18.1.0`
  DKQ; correlations `0,9543` en `UZ` et `0,9560` en `S11`, ecarts de pic
  `5,20 %` et `10,51 %` (`VNV-MITC4-NEWMARK-CODEASTER-DKQ-005`) ;
- [x] Newmark : revue mecanique enregistree par Quentin Farinazzo le
  `2026-07-16`, decision `accepted_with_recommendations` pour l'usage
  engineering interne; registre
  `qualification/reviews/mitc4_transient_dynamic_2026-07-16.json`, Markdown et
  PDF controles ;
- [x] harmonique MITC4 : limite statique, amplitude, phase, resonance amortie
  et sensibilite a l'amortissement (`VNV-MITC4-HARMONIC-MODAL-001`) ;
- [x] demontrer la condensation harmonique exacte avec
  $C=\alpha M+\beta K$, charge directe de drilling et comparaison au systeme
  complexe complet (`VNV-MITC4-HARMONIC-CONDENSATION-002`) ;
- [x] harmonique MITC4 : excitation large bande sur quatre resonances avec
  accord direct/superposition modale complete
  (`VNV-MITC4-HARMONIC-BROADBAND-003`) ;
- [x] harmonique MITC4 : reference publiee NAFEMS 13H et correlations
  reproductibles Code_Aster/CalculiX sur maillage `8x8`, amplitude, frequence
  et `S11` (`VNV-MITC4-HARMONIC-NAFEMS13H-004`) ;
- [x] harmonique MITC4 : exporter les contraintes complexes `S11/S22/S12`
  par face et frequence, puis comparer `S11` a Navier, NAFEMS, Code_Aster et
  CalculiX ;
- [x] harmonique MITC4 : revue mecanique `accepted_with_recommendations` par
  Quentin Farinazzo le `2026-07-15` ;
- [x] harmonique MITC4 : adopter le processus de validation
  `QF_solver <-> Navier <-> NAFEMS publie <-> CalculiX/Code_Aster` ;
- [x] harmonique MITC4 : executer CalculiX S4/S8R sur le cas 13H; retenir S8R
  pour la sensibilite et tracer le `WARNING` `S11/NAFEMS=5,168 %` ;
- [x] harmonique MITC4 : executer Code_Aster `18.1.0` avec DKQ sur le cas
  13H; ecarts QF_solver de `3,364 %` en frequence, `1,900 %` en deplacement
  et `3,272 %` en `S11`, tous sous `5 %` ;
- [ ] harmonique MITC4 : obtenir une revue independante des correlations
  Navier, NAFEMS, Code_Aster et CalculiX avant toute hausse de maturite ;
- [x] ajouter chargements multi-composantes, calage de Rayleigh sur deux cibles
  modales et reprise de calcul; campagne
  `VNV-MITC4-NEWMARK-OPERATIONAL-006` `PASS`, addendum mecanique a revoir ;
- [x] documenter la masse coherente comme seule formulation acceptee et garder
  les matrices concentrees hors scope.

Critere de sortie : chaque methode possede reference analytique, invariant,
test de non-regression et exemple CLI/API.

## P4 - Grands modeles

- [x] ajouter l'orchestrateur `large-campaign`, son mode plan sans allocation,
  l'agregation JSON/Markdown et la telemetrie RSS processus ;
- [x] installer et figer le runtime Docker PETSc `3.25.1`, puis executer
  `P4-PETSC-100K-001` et `P4-PETSC-1M-001` sur deux rangs MPI ;
- [x] distribuer la matrice AIJ, le vecteur, les elements et les ddl entre
  rangs; accord mono/deux-rangs `2,92e-16` sur le petit cas ;
- [x] vectoriser par lots gradients, matrices `B` et rigidites TET4 : gain
  assemblage `x10,36` a 100k et `x2,88` a 1M, sans ecart numerique ;
- [x] assembler en blocs BAIJ `3x3`, convertir en AIJ avant GAMG et executer
  le niveau `3M`: `3 000 000` DDL, `5 821 794` TET4, `88,68 s`, `PASS` ;
- [x] mesurer la scalabilite forte 1/2/4 rangs sur 1M; accelerations `1,45`
  et `1,65`, efficacite quatre rangs limitee a `41,18 %` ;
- [x] supprimer la replication globale des noeuds/connectivites par rang avec
  lecture HDF5 par hyperslabs et tables de noeuds compactes locales ;
- [x] eliminer le rassemblement global des deplacements par une sortie MPI-IO
  collective `float64`, accompagnee de metadonnees et verifiee par empreinte ;
- [x] distribuer aussi les tableaux de blocages et charges en lecture HDF5
  chunkee: charges possedees par plage de DDL, blocages gardes pour le halo
  elementaire ou la ligne PETSc possedee; smoke MPI `PASS` avec norme de charge
  conservee ;
- [x] mettre en place la reprise PETSc depuis une solution terminee avec
  empreinte de modele, ainsi que le post-traitement TET4 HDF5 par blocs avec
  checkpoint atomique; preuve sur `477 042` TET4, reprise apres `131 072`,
  energie a `4,14e-13` du solveur et restart KSP en zero iteration ;
- [x] publier memoire pic, temps, iterations et versions MPI/PETSc ;
- [x] comparer GAMG et Hypre/BoomerAMG sur 1M/4 rangs : accord deplacement
  `3,40e-12`; GAMG reste le defaut (`24,41 s`, `0,759 GB/rang`) devant Hypre
  (`52,30 s`, `2,47 GB/rang`) malgre `18` iterations contre `53` ;
- [x] activer et tracer le repartitionnement des grilles grossieres GAMG a
  partir de quatre rangs; gain KSP mesure de `12,66` a `12,20 s` ;
- [x] mesurer la scalabilite faible a charge locale constante sur 1/2/4 rangs:
  efficacites `100/72,6/41,6 %`, verdict `WARNING` sous le seuil `60 %` ;
- [x] implementer un partitionnement de graphe PETSc/PT-Scotch avec
  redistribution reelle des elements; petit cas MPI verifie avec accord
  deplacement `3,06e-16` face au partitionnement contigu ;
- [x] corriger le proprietaire MPI des lignes du graphe pour les nombres
  d'elements non divisibles par le nombre de rangs, ajouter le trace
  `QF_SOLVER_MPI_TRACE=1` et la lecture HDF5 par plages contigues ;
- [x] stabiliser le partitionnement graphe sur `264 600` DDL et `1 029 000`
  DDL en quatre rangs: `PASS`, ecart graphe/contigu `2,24e-13` sur 1M,
  cut-face ratio `0,514 %`, imbalance `1,009` ;
- [ ] conserver le graphe en option experimentale tant qu'il n'a pas demontre
  un gain net de temps total et de memoire sur plusieurs topologies; le
  partitionnement contigu reste le defaut ;
- [x] tracer les tailles de halo nodal par rang dans `audit_large.json`
  (`local_owned_node_counts`, `local_halo_node_counts`,
  `halo_node_ratio_max`) ;
- [x] tracer les communications MPI estimees et niveaux multigrilles PETSc:
  `mpi_communication` dans `audit_large.json` et
  `preconditioner_diagnostics` dans `summary.json` avec `pc_mg_levels`,
  tailles matricielles et `matrix_info` ;
- [x] ajouter le profilage PETSc detaille `-log_view`, son parseur sans
  execution de contenu, les rapports JSON/Markdown et une campagne quatre
  rangs sur bloc, poutre et plaque pour expliquer quantitativement
  l'efficacite au-dela de deux rangs; a environ `254k` DDL, le bloc demande
  `49` iterations contre `161` pour la poutre et `136` pour la plaque, tandis
  que `PCSetUp` reste entre `0,546` et `0,613 s` ;
- [x] tester cinq reglages GAMG/Hypre sur bloc, poutre et plaque, soit quinze
  calculs quatre rangs; tous `PASS`, ecart deplacement maximal `1,96e-11`;
  GAMG seuil `0.01` gagne `18,0/5,3/7,3 %`, insuffisant pour changer le defaut
  selon la regle de gain minimal `10 %` sur chaque topologie.

Critere de sortie : cas 1M+ reproductible sur infrastructure identifiee, sans
conversion dense ni JSON monolithique.

## P4B - Politique de choix du solveur lineaire

Constat : la factorisation directe LU est une reference numerique utile pour
les V&V et les petits/moyens modeles. Elle reste correcte sur le cas Newmark
TET10 raffine a `50 112` DDL, mais une factorisation a demande environ
`4,5 Go` de memoire virtuelle. Ce cout interdit d'en faire le choix implicite
pour les calculs de grande taille : il s'agit d'une limite de ressources, pas
d'une invalidation de la solution LU.

- [x] definir une politique de selection explicite, exposee par l'API, les
  resultats et l'audit, sans basculement silencieux de methode ;
- [x] reserver LU/direct aux V&V, diagnostics, petits/moyens modeles et cas a
  plusieurs seconds membres lorsque le budget memoire estime est acceptable :
  les routes statique, Newmark et harmonique publient l'estimation et refusent
  le direct lorsque `enforce_direct_memory_budget` est active ;
- [x] choisir `CG` avec preconditionneur seulement pour un systeme reduit
  symetrique defini positif, et verifier cette hypothese dans l'audit : une
  Cholesky bornee prouve les petits systemes et `assume_spd` reste une
  declaration explicite et tracee pour les grands systemes, jamais deduite de
  la seule diagonale positive ;
- [x] choisir `MINRES` pour les systemes symetriques indefinis et
  `GMRES`/`BiCGSTAB` uniquement lorsqu'une non-symetrie est documentee : la
  politique lineaire refuse CG sans preuve SPD bornee ou declaration explicite
  `assume_spd`, et recommande MINRES pour un systeme symetrique non prouve SPD ;
- [x] imposer `PETSc KSP + GAMG` comme trajectoire par defaut pour le TET4
  statique distribue : `LargeLinearStaticSolver` utilise `KSP CG + GAMG` par
  defaut; la comparaison Hypre/BoomerAMG reste une optimisation conditionnelle,
  a ne mener que si une topologie ou un conditionnement la justifie ;
- [x] estimer avant calcul le nombre de coefficients et la memoire de
  factorisation directe. Emettre un avertissement ou refuser LU au-dela d'un
  budget configure ; la memoire d'assemblage et le cout de sortie grand modele
  restent traites par le chemin HDF5/PETSc ;
- [x] enregistrer pour la statique lineaire standard le solveur demande et
  finalement utilise, sa justification, preconditionneur, tolerances,
  iterations, residu, absence de repli, temps et estimation memoire dans les
  sorties JSON et l'audit ; les diagnostics PETSc restent portes par le mode
  grand modele et les routes Newmark/harmonique seront alignees avant de
  revendiquer une dynamique grand modele ;
- [x] comparer LU, CG, MINRES, GMRES et BiCGSTAB a la voie directe sur un
  systeme SPD et un systeme non symetrique controles (`VNV-LINEAR-SOLVERS-001`),
  avec ecart de solution et residu executables; le benchmark poutre confirme
  separement l'accord sur un systeme EF symetrique ;
- [x] aligner les diagnostics des matrices effectives Newmark et harmoniques :
  contrat reel/complexe, symetrie, estimation LU, budget optionnel, methode
  effectivement utilisee, reutilisation Newmark et temps par frequence sont
  exposes dans le resultat JSON et l'audit. La dynamique grand modele reste un
  chantier distinct, sans promesse implicite de passage a l'echelle ;
- [x] comparer PETSc aux voies SciPy sur les modeles TET4 distribues, avec
  accord de solution et residu avant toute conclusion de performance :
  `VNV-LARGE-PETSC-SCIPY-001` resout le meme bloc HDF5 par SciPy et PETSc/GAMG
  sur deux rangs Docker, avec un ecart de deplacement `1,02e-12` et des residus
  sous `1e-7`. Cette preuve ne se substitue pas aux campagnes de performance 1M+ ;
- [ ] etendre cette politique aux matrices effectives Newmark et harmonique
  distribuees, avec post-traitement resume ou chunke avant de revendiquer une
  dynamique grand modele.

Critere de sortie : aucun calcul ne selectionne LU par defaut sans estimation
de ressources et toute selection automatique reste explicable, reproductible
et visible dans le dossier de preuve.

## P5 - Non-lineaire et TET10

### P5.1 - Loi J2 en petites deformations

- [x] conserver les tests unitaires de tangente algorithmique par differences
  finies en regime plastique, y compris depuis un etat commite ;
- [x] creer `VNV-J2-MATERIAL-CYCLIC-001` avec rapport JSON/Markdown et chemins
  proportionnels, non proportionnels, decharge et recharge ;
- [x] verifier plusieurs directions de chargement elastiques et plastiques avec
  une erreur relative de tangente inferieure a `1e-6` ;
- [x] verifier la condition de plasticite, la croissance monotone de la
  deformation plastique cumulee et une dissipation plastique non negative ;
- [x] couvrir plasticite parfaite (`H=0`) et ecrouissage isotrope (`H>0`) ;
- [x] ajouter un essai uniaxial material-point compare a la loi bilineaire et
  publier les courbes contrainte-deformation et variable interne ;
- [x] comparer les quatre increments monotones a une reference publiee de
  plaque elastoplastique sous charge uniforme; conserver les increments
  inverses hors comparaison car la reference utilise un ecrouissage
  cinematique ;
- [x] executer la meme histoire monotone avec CalculiX `2.20` isotrope sur un
  C3D8 homogene; accord exact en `S11/PEEQ`, ecart de deformation `1,76e-7`
  relatif et ecart d'energie `0,1317 %` sous la limite `0,5 %`
  (`VNV-J2-CALCULIX-ISOTROPIC-002`) ;
- [x] ajouter Code_Aster `18.1.0` `VMIS_ISOT_LINE` comme seconde
  implementation externe dans `VNV-J2-CODEASTER-VMIS-ISOT-LINE-004` :
  contrainte axiale, deformation plastique equivalente, contraintes
  laterales et homogeneite du patch affine passent a mieux que `4,34e-16`
  relatif. La conversion entre module d'ecrouissage plastique QF_solver et
  pente totale `D_SIGM_EPSI=E H/(E+H)` est explicite et testee ;
- [x] renforcer la campagne TET4 multi-elements monotone avec equilibre,
  deformation plastique analytique et independance sur `3/6/12` increments ;
- [x] ajouter `VNV-J2-TET4-CYCLIC-003` sur `140` TET4 avec cycle d'amplitude
  croissante `+300/-360/+420 MPa`; ecart oracle `5,02e-11`, croissance
  plastique prouvee aux deux inversions et residu maximal `2,41e-8`.
- [x] ajouter `VNV-J2-TET10-CYCLIC-001` sur `140` TET10 droits, quatre points
  de Hammer et un cycle commite charge/decharge/recharge; l'erreur de chemin
  plastique est `8,73e-10`, l'erreur de contrainte `5,96e-11` et le residu
  maximal `4,14e-9`.
- [x] executer `VNV-TET10-J2-CODEASTER-STRUCTURAL-025` sur le meme maillage
  TET10/TETRA10 avec six facteurs monotones : ecart UX final `0,03175 %`,
  PEEQ RMS `0,55084 %` et residu QF maximal `7,40079e-11`.
- [x] enregistrer l'Owner review du `2026-08-09` : acceptation bornee pour
  usage interne experimental, sans hausse de maturite generale.
- [x] lancer `VNV-TET10-J2-CODEASTER-COMPLEX-026` sur un support en L :
  `1 039` noeuds, `457` TET10, charges combinees `FX=3 MN` et `FY=-6 MN`,
  ecart RMS deplacement `0,01245 %`, ecart final `0,00227 %`, PEEQ RMS
  `1,84443 %`, ratio petites deformations `1,95357 %` et residu maximal
  `1,97226e-9` ; la campagne est `PASS_EXTERNAL_CORRELATION`, Owner review
  a faire.

### P5.2 - Robustesse du solveur non lineaire

- [x] prouver que les etats internes ne sont commites qu'apres convergence et
  qu'un increment rejete restaure exactement le dernier etat accepte ;
- [x] tester reduction et croissance adaptatives du pas, nombre maximal de
  coupures et diagnostic explicite de non-convergence; les rejets sont exposes
  dans `solver.rejection_log` et les parametres incoherents sont refuses ;
- [x] comparer Newton complet, Newton modifie et line-search sur le meme cycle
  `VNV-J2-NONLINEAR-METHODS-004`: Newton complet et Armijo convergent en `33`
  iterations et concordent sur la reponse axiale; le champ transverse faiblement
  retenu reste sensible a la methode. Newton modifie ne converge pas au premier
  dechargement et reste non recommande pour les inversions plastiques ;
- [x] corriger la line-search sur inversion plastique multi-elements : le
  residu des passages par charge nulle est normalise par la charge de reference;
  la campagne `VNV-J2-TET4-CYCLIC-003` passe avec Armijo (erreur chemin
  plastique `3,70e-13`, residu relatif maximal `1,60e-12`) ;
- [x] ajouter checkpoint/reprise NPZ atomique des deplacements, du facteur de
  charge et des variables internes avec empreinte du modele; identite calcul
  continu/reprise prouvee sur un cycle J2. Adaptatif et arc-length restent
  explicitement hors de ce premier contrat ;
- [x] tracer par increment iterations, norme du residu, corrections, travaux
  interne/externe trapezoidaux, desequilibre de travail, coupures de pas et
  statut de commit; ne pas assimiler ce diagnostic a une decomposition exacte
  energie elastique/dissipation plastique ;
- [x] verifier la reproductibilite sur `12/24/48` increments du meme cycle
  dans `VNV-J2-STEP-SENSITIVITY-005`, avec comparaison aux retournements,
  reponse finale, travaux et courbe PNG; sensibilite d'etat `9,49e-11` et
  convergence du travail `24 -> 48` increments inferieure a `2 %`.

### P5.3 - Non-linearite geometrique

- [x] figer une formulation totale lagrangienne TET4 avec Green-Lagrange,
  Piola-Kirchhoff 2 et Saint-Venant-Kirchhoff, distincte du J2 petites
  deformations; domaine et limites documentes ;
- [x] implementer le noyau de verification objectif, sa force interne, son
  energie et sa tangente geometrique/materielle consistante sans modifier le
  chemin petites deformations qualifie ;
- [x] verifier l'assemblage sur `192/648/1536/5184/12288/24000` TET4 : patch affine,
  rotation rigide, Newton, jacobien courant et grande fleche; invariants
  `PASS`, variation de fleche reduite de `19,09 %` a `3,81 %` ;
- [x] enregistrer la validation mecanique interne de Quentin Farinazzo en
  `self_review`, avec statut `engineering_internal_validated_with_recommendations`;
  le perimetre reste `research` et ne constitue pas une revue independante ;
- [x] integrer un premier chemin public `geometric_nonlinear_static` au routeur,
  aux sorties JSON et a l'API/CLI, borne a TET4 homogene, charges nodales mortes,
  Newton complet, minimum `6` et defaut `10` increments; maturite `research` ;
- [x] verifier rotation rigide sans contrainte, traction avec grande rotation,
  poutre en grand deplacement et flambement d'Euler ; les preuves sont reunies
  dans les campagnes `001` a `010` et la revue structurelle V2 ;
- [x] ajouter une reference d'elastica d'Euler sous charge morte; fleche
  `-0,60013`, ecart fin `6,91 %`, reference informative hors effets 3D ;
- [x] demontrer par `3/6/10/12/24` increments que `6/10/12/24` donnent le meme
  equilibre a `8,10e-16` relatif; minimum technique `6`, recommandation et
  valeur par defaut `10` increments ;
- [x] correler les six maillages avec CalculiX `2.20` C3D4 dans Docker;
  ecart maximal de fleche `1,86e-7` relatif ;
- [x] mettre en cache les gradients/volumes et vectoriser force et tangente;
  les trois anciens niveaux passent d'environ `198,7 s` a `6,90 s` ;
- [x] executer `VNV-TET4-TL-STRESS-005` : patch affine fini PK2/Cauchy/energie
  sur quatre maillages, erreur maximale inferieure a `1e-11` ;
- [x] executer `VNV-TET4-TL-BUCKLING-EULER-006` : tangente precontrainte et
  charge critique analytique d'Euler; ecart fin `5,87 %`, variation finale
  `3,31 %`; correlation externe encore recommandee ;
- [x] executer le point d'acceptation `64x16x16`, soit `98 304` TET4 et
  `56 355` DDL : erreur Euler reduite a `1,896 %`, charge QF `818,415`,
  CalculiX `818,696` et ecart meme maillage `0,0343 %` ;
- [x] executer `VNV-TET4-TL-POSTBUCKLING-007` : trois colonnes imparfaites,
  `120` pas arc-length creux par chemin, residu maximal `9,53e-9` et
  `det(F)` minimal `0,9832` ;
- [x] produire pour ces trois benchmarks les rapports Markdown, courbes,
  deformees PNG, resultats normalises et manifestes SHA-256 avant la nouvelle
  revue mecanique ;
- [x] correler contrainte finie et flambement propre sur maillage identique avec
  CalculiX `2.20` C3D4: erreur Cauchy `1,17e-7`, ecart Pcr fin `0,035 %` ;
- [x] correler avec Code_Aster `18.1.0` TETRA4: erreur PK2 `8,54e-5` et
  ecart maximal de branche imparfaite jusqu'a `0,8 Pcr` de `1,69e-9`; documenter
  `RIGI_GEOM` solide 3D comme non applicable au flambement propre meme formulation ;
- [x] revue structurelle V2 acceptee avec recommandations par Quentin Farinazzo
  le `2026-07-18`: push-forward Cauchy, erreur Euler h5, trois amplitudes
  d'imperfection, arc-length et correlations CalculiX/Code_Aster ;
- [x] borner la validation interne aux charges nodales mortes et au domaine
  documente ; pression suiveuse, contact, plasticite en deformation finie,
  endommagement et qualification externe restent explicitement hors scope.

### P5.4 - Consolidation TET10

- [x] qualifier au niveau elementaire les Jacobiennes variables et les
  quadratures sur elements droits, courbes, distordus et proches des limites
  de qualite dans `VNV-TET10-GEOMETRY-QUADRATURE-011`; regle automatique
  Hammer-4/Duffy-64, erreur courbe `7,51e-7` et rejet du Jacobien negatif ;
- [x] completer le patch affine et la convergence structurelle en `h` dans
  `VNV-TET10-STRUCTURAL-CONVERGENCE-012`, avec quatre maillages TET4/TET10 par
  probleme : erreur TET10 `5,76e-15` en traction, `1,179 %` en flexion et
  `0,00250 %` sur la rotation de torsion; erreur de contrainte de torsion
  `0,991 %` et equilibre de charge `2,27e-16` ;
- [x] verifier masse, modal, chargements de face quadratiques et recuperation
  nodale dans `VNV-TET10-MASS-MODAL-LOADS-013` : masse courbe a `3,57e-16`,
  resultante/moment de pression a `9,10e-18`/`4,71e-16`, contrainte recuperee
  a `8,72e-16` et premiere paire modale a `0,434 %` de la theorie ;
- [x] correler le cas de torsion courbe sur le meme maillage avec CalculiX
  `2.20` C3D10 dans `VNV-TET10-CALCULIX-C3D10-014` : ecart relatif du champ
  complet `6,84e-5` et de la rotation terminale `6,45e-5`, sous `1e-4` ;
- [x] caracteriser la flexion quasi-incompressible dans
  `VNV-TET10-NEAR-INCOMPRESSIBLE-015` sur trois maillages et quatre valeurs de
  `nu` : a `nu=0,499`, compliance TET10 `94,83 %` contre `8,48 %` pour le
  temoin TET4; conserver l'incompressibilite exacte hors scope ;
- [x] revue mecanique TET10 lineaire acceptee avec recommandations par Quentin
  Farinazzo le `2026-07-18`, en `self_review`, pour le domaine borne ;
- [x] conserver J2, grandes transformations, incompressibilite exacte et TET10
  avance hors du scope accepte jusqu'a campagnes reproductibles dediees ;
- [ ] executer `REC-TET10-001` sur une piece a geometrie rentrante TET10 avec
  chargements combines et correlation Code_Aster; conserver le statut
  experimental jusqu'a Owner review de ce cas.
- [ ] en toute fin du developpement, executer `REC-TET10-002` sur des pieces et
  assemblages beaucoup plus complexes, des maillages importants, des charges
  combinees et plusieurs codes de reference, notamment Conastin, CalculiX et
  Code_Aster, avant acceptation totale ou qualification externe.

Critere de sortie : loi J2 material-point et structure multi-elements prouvees,
gestion transactionnelle des etats internes testee, puis TET10 consolide. La
non-linearite geometrique constitue un scope distinct et ne peut pas etre
deduite de la seule convergence du solveur petites deformations.

## P6 - Composites et stratifies (socle constitutif demarre)

### P6.1 - Conventions et materiaux orthotropes

- [x] figer les axes materiau `1-2-3`, les angles de pli, le sens positif et la
  transformation entre repere materiau, repere element et repere global ;
- [x] implementer une couche orthotrope elastique avec constantes reciproques,
  controles de positivite et matrice reduite en contraintes planes ;
- [x] verifier analytiquement les matrices `Q` et `Qbar` pour `0`, `90` et
  `+/-45 deg`, ainsi que l'invariance par rotation.

### P6.2 - Theorie classique des stratifies

- [x] definir la sequence d'empilement, les interfaces en epaisseur, les
  matrices `A/B/D`, les resultantes membrane/flexion et les couplages ;
- [x] prendre en charge stratifies symetriques, equilibres et non symetriques,
  puis les chargements thermiques seulement dans un scope ulterieur ;
- [x] comparer `A/B/D` a des solutions analytiques et imposer `B=0` pour les
  empilements symetriques dans les tests de verification.

### P6.3 - MITC4 multicouche

- [x] integrer les contributions pli par pli sans modifier le MITC4 isotrope
  qualifie, avec resultats contraintes/deformations aux faces de chaque pli ;
- [x] verifier le cisaillement transverse, l'orientation sur coques courbes,
  le couplage membrane-flexion et la sensibilite au shear locking ;
- [x] conserver l'element composite au statut `experimental` jusqu'aux patch
  tests, etudes de convergence et correlations externes.

### P6.4 - Criteres et V&V composites

- [x] introduire d'abord contrainte/deformation maximale, Tsai-Hill et Tsai-Wu;
  garder Hashin, Puck et l'endommagement progressif hors premier perimetre ;
- [x] construire des cas analytiques `[0]`, `[0/90]s`, `[+45/-45]s`, traction
  hors axe et plaque stratifiee en flexion ;
- [x] publier la convergence structurelle MITC4 multicouche sur membrane,
  flexion croisee et flexion angle-ply dans `VNV-COMP-STRUCTURAL-CONVERGENCE-002`;
- [x] correler le panneau `[0/90]s` avec CalculiX `2.20` S8R composite dans
  `VNV-COMP-CALCULIX-S8R-003`: ecart fin de fleche `0,0310 %`;
- [x] completer par le benchmark NAFEMS R0031/1 et une correlation Code_Aster
  `18.1.0` DST/DSQ dans `VNV-COMP-NAFEMS-R0031-CODEASTER-004`: ecart fin
  QF/NAFEMS `0,458 %`, Code_Aster/NAFEMS `0,710 %`, QF/Code_Aster `0,251 %`;
  cinq maillages jusqu'a `160x32`, increments finaux `0,0967 %` et `0,0920 %`;
- [x] realiser la revue mecanique composite distincte; Quentin Farinazzo a
  enregistre le `2026-07-26` une acceptation engineering interne avec
  recommandations, en mode `self_review` et sans certification revendiquee ;
- [x] traiter la recommandation sur les contraintes par pli hors singularites
  dans `VNV-COMP-PLY-STRESS-005` : erreurs L2 fines de `0,00389 %` en
  membrane, `0,254 %` en flexion, `0,0379 %` en charge combinee et `1,056 %`
  sur le maillage interieur distordu de `15 %`.
- [x] implementer `reference_direction` projete sur chaque facette et executer
  `VNV-COMP-CURVED-ASSEMBLY-006` : erreur angulaire `1,4e-14 deg`, increments
  finaux `1,063 %` sur cylindre et `0,875 %` sur assemblage plie; le cas a
  facettes gauches reste correctement refuse par le profil qualifiable.
- [x] correler la coque cylindrique `[0/90]s` avec CalculiX `2.20` S8R dans
  `VNV-COMP-CURVED-CALCULIX-S8R-007` : ecart vectoriel fin `0,225 %`,
  increment final QF `0,245 %` et CalculiX `0,0376 %`.
- [x] fermer `ANOM-COMP-CURVED-ORIENTATION-001` dans
  `VNV-COMP-CURVED-ORIENTATION-008` : orientations CalculiX tangentielles par
  rangee et par pli, empilement `[0/+45/-45/90]`, cinq maillages jusqu'a
  `96x48`; ecart vectoriel fin `1,839 %` sous le seuil externe borne de `3 %`.
- [x] ajouter `VNV-COMP-CONICAL-CUTOUT-009` : panneau annulaire conique
  stratifie `[0/+45/-45/90]`, ouverture centrale libre, projection locale des
  axes par facette, resultats par pli, VTU/PNG et convergence sur trois
  maillages. La fleche sonde se stabilise a `0,0588 %`; cette evidence reste
  interne et `experimental` jusqu'a correlation externe dediee ;
- [x] correler les deplacements du panneau composite conique ajoure avec
  CalculiX S8R COMPOSITE; la comparaison de contraintes par pli hors bord
  libre reste une etape distincte ouverte ;
- [x] executer l'essai exploratoire
  `VNV-COMP-CONICAL-CUTOUT-CALCULIX-S8R-010` avec une charge nodale de bord
  identique : statut `WARNING`, ecart vectoriel `29,17 % -> 10,10 %` mais
  sonde encore trop sensible au bord libre. Ne pas utiliser ce resultat comme
  validation; remplacer la charge par une sollicitation reguliere et comparer
  les contraintes par pli sur un chemin a distance fixee ;
- [x] executer `VNV-COMP-CONICAL-CUTOUT-CALCULIX-S8R-011` avec le vecteur de
  pression coherent QF transfere aux noeuds de coin communs : ecart de sonde
  fin `0,728 %`, ecart vectoriel fin `1,608 %`, increments QF/CalculiX
  `0,0588 %`/`0,260 %`. Cette correlation cinematique reguliere passe sous le
  seuil borne de `3 %`; elle ne valide ni la quadrature de pression native
  CalculiX ni les contraintes par pli au bord libre ;
- [x] ajouter `VNV-COMP-CONICAL-CUTOUT-PLY-STRESS-CALCULIX-S8R-012` :
  extraction des contraintes tangentielles par pli sur la couronne
  `0,38 <= eta <= 0,62`, a distance normalisee de l'ouverture, avec
  comparaison CalculiX S8R dans les axes materiau. L'ecart L2 fin est
  `0,298 %`, et les increments finaux QF/CalculiX sont `0,611 %`/`0,480 %` ;
  les pics de bord libre et `S13` restent hors critere ;
- [ ] traiter `REC-COMP-CURVED-MODELFORM-001` avec un oracle coque de meme
  ordre ou une reference analytique de stratifie courbe; ne pas generaliser
  le seuil croise MITC4/S8R de `3 %`.

La campagne `VNV-COMP-ANALYTIC-001` passe six controles sous `1e-12`, la
campagne structurelle `002` passe, et les correlations CalculiX `003` et
NAFEMS/Code_Aster `004` passent. La campagne de contraintes par pli `005`
passe egalement. La correlation externe courbe `007` passe dans son domaine
axial borne. La campagne `008` ferme aussi l'anomalie d'orientation oblique,
avec une recommandation sur l'ecart de formulation MITC4/S8R. Le scope reste
`experimental` jusqu'a l'ajout d'assemblages industriels complexes;
`S13` interlaminaire reste hors acceptation.

### P6.5 - Solides orthotropes TET4 et TET10

- [x] rediger la specification `orthotropic_3d`, ses constantes reciproques,
  les orientations materiau, sorties et limites de premiere version ;
- [x] implementer la loi 3D et sa transformation globale sans modifier le
  chemin isotrope qualifie ;
- [x] integrer la loi au TET4 puis au TET10, avec resultats dans les axes
  globaux et materiau ;
- [x] executer les huit preuves `SPEC-COMP-SOLID-001..008`: les preuves
  `001..005` passent dans `VNV-ORTHOTROPIC-SOLID-KERNEL-001`; la correlation
  externe `007` passe sur une eprouvette trouee et une equerre dans
  `VNV-ORTHOTROPIC-SOLID-EXTERNAL-002`; la convergence `006` passe dans la
  campagne `003` avec reserve de precision TET4; la non-regression isotrope
  `008` passe dans la campagne `004` ;
- [x] preparer puis signer la revue mecanique des solides orthotropes le
  `2026-07-22` : `docs/verification/revue_solides_orthotropes.md` et
  `qualification/reviews/orthotropic_solids_2026-07-22.json` ;
- [x] etendre la convergence TET4 a `4 951` et `9 820` elements : l'ecart de
  fleche descend monotoniquement a `16,83 %` puis `11,75 %` ;
- [x] accepter les conventions d'orientation, les contraintes en axes
  materiau/global, les patchs affines, l'objectivite et les correlations
  externes pour le domaine statique lineaire borne ;
- [x] enregistrer le statut
  `engineering_internal_validated_with_recommendations`, sans revendication de
  certification externe ;
- [x] implementer le champ `cylindrical_tangent` pour TET4/TET10 standard :
  repere circonferentiel/axial/radial evalue au centroide, valide par tests de
  rotation de repere et d'assemblage global ;
- [ ] qualifier ce champ sur une structure cylindrique ou conique avec
  raffinement et oracle externe; les fibres a courbure arbitraire, les champs
  interpoles aux points de Gauss et le grand modele restent hors scope ;
- [x] implementer la campagne reelle de contraintes proches des singularites avec
  raffinement, chemins a distance controlee, moyennes regularisees et
  correlations Code_Aster ;
- [x] executer la campagne controlee avec deux raffinements supplementaires et
  ajouter la seconde correlation CalculiX sur les memes chemins et moyennes de
  bande ; QF_solver/Code_Aster est a la precision machine et l'ecart maximal
  QF_solver/CalculiX vaut `0,000193 %`.
- [x] poursuivre `VNV-ORTHOTROPIC-SINGULAR-STRESS-005` avec deux maillages
  encore plus fins et une recuperation compacte quadratique ponderee par les
  volumes : les huit niveaux atteignent `86 469` TET4 pour le trou et
  `237 358` TET4 pour l'equerre. Les increments finaux chemin/bande valent
  `1,342 % / 0,125 %` et `1,625 % / 3,420 %`, sous le seuil `5 %`.
  Code_Aster sur maillage identique passe a mieux que `5,4e-9 %`. La bande
  nodale CalculiX de l'equerre differe encore de `6,357 %` car son extrapolation
  n'utilise pas le meme operateur de recuperation; elle reste un diagnostic
  `WARNING` non bloquant, trace dans le digest controle.
- [x] traiter la demande humaine de deux pieces supplementaires avec
  `VNV-ORTHOTROPIC-ADDITIONAL-STRESS-006` : encoche arrondie et double trou
  sur cinq raffinements, jusqu'a `55 935` TET4. Les increments finaux
  chemin/bande valent `0,611 % / 0,868 %` et `4,404 % / 0,556 %`;
  les cartes `S11` QF_solver/Code_Aster sont publiees. Quentin Farinazzo a
  enregistre `accepted_with_recommendations` le `2026-07-29`, avec maintien
  des chemins, bandes et exclusions des pics ponctuels singuliers ;
- [x] definir le protocole de surete `VNV-ORTHOTROPIC-SINGULAR-STRESS-005` :
  classification des pics finis ou singuliers, chemins a distance fixe,
  moyennes de bande, quatre maillages et correlation analytique/Code_Aster/
  CalculiX ;
- [x] brancher l'orthotropie lineaire sur le modal TET4/TET10 et verifier
  frequences, residus propres et orthogonalite par la limite isotrope ;
- [x] brancher l'orthotropie lineaire sur Newmark TET4/TET10 et verifier
  champs, residus et energie par la limite isotrope ;
- [x] etendre le grand modele statique TET4 aux materiaux `orthotropic_3d` et
  `composite_orthotropic_3d` dans les backends SciPy, PETSc et matrix-free,
  ainsi que dans l'audit et le post-traitement ;
- [x] conserver hors scope dommage, delaminage, plasticite anisotrope et
  grandes deformations ;
  - [x] executer un benchmark modal orthotrope avec convergence de `24` a
    `96` TET4 et correlation Code_Aster `18.1.0` `3D/TETRA4` sur meme
    maillage : erreur theorique fine `0,0309 %`, ecart modal externe
    `2,00e-12 %` (`VNV-ORTHOTROPIC-MODAL-NEWMARK-010`) ;
  - [x] executer une convergence temporelle Newmark orthotrope de `2 ms` a
    `62,5 us` et une correlation transitoire Code_Aster sur `0,25 ms` : RMS
    normalise `9,00e-13 %`, ecart entre les deux pas QF_solver les plus fins
    `2,89 %` sous le seuil de stabilisation `5 %`
    (`VNV-ORTHOTROPIC-MODAL-NEWMARK-010`) ;
- [x] executer PETSc/MPI sur un modele TET4 orthotrope representatif de plus
  d'un million de DDL : `VNV-ORTHOTROPIC-LARGE-STATIC-009` passe avec
  `1 029 000` DDL, deux rangs, `89` iterations, residu `4,354e-18`, audit et
  manifeste `PASS`; le modal et Newmark distribues restent hors scope.

La specification controlee est dans
`qualification/specifications/composite_solids.json`; le statut est
`engineering_internal_validated_with_recommendations`. Le dossier de passage en revue est
centralise dans `docs/verification/dossier_validation_owner.md`.

Critere d'entree : ne commencer P6 qu'apres stabilisation de P5.2. Critere de
sortie initial : calcul elastique lineaire multicouche reproductible, conventions
figees, resultats par pli et preuves analytiques; aucune revendication de rupture
ou de dommage qualifiee a ce stade.

## P7 - Fermeture fonctionnelle de la V1

### P7.1 - BEAM2

- [x] definir un element poutre 3D de Timoshenko a deux noeuds et six DDL par
  noeud : `UX`, `UY`, `UZ`, `RX`, `RY`, `RZ` ;
- [x] figer le repere local, l'orientation de section et les signes de
  `N`, `Vy`, `Vz`, `T`, `My`, `Mz` ;
- [x] accepter les proprietes `A`, `Iy`, `Iz`, `J`, `E`, `G`, densite et
  facteurs de correction de cisaillement ;
- [x] implementer rigidite, masse coherente, chargements nodaux et repartis ;
  la masse concentree est traitee separement en P7.2 ;
- [x] ajouter traction, torsion, flexion dans les deux plans, poutre epaisse,
  modes rigides, modal et convergence vers Euler-Bernoulli ;
- [x] comparer aux solutions analytiques et a Code_Aster `18.1.0` Docker sur
  une section generale identique : axial, torsion et flexion elancee passent
  sous `1 %` dans `VNV-BEAM2-CODEASTER-POUDE-001`; le cisaillement epais et la
  dynamique externe restent ouverts ;
- [x] corriger puis verifier la masse BEAM2 par correlation modale externe :
  la masse Hermite transverse avec inertie rotatoire Timoshenko est comparee a
  Code_Aster `18.1.0` `POU_D_E` dans
  `VNV-BEAM2-MODAL-CODEASTER-POUDE-002`; les six modes du porte-a-faux elance
  passent sous `1 %`, avec un ecart maximal observe de `0,0265 %`. La
  dynamique de poutre epaisse, l'amortissement et les assemblages restent
  ouverts ;
- [x] documenter formulation, limites, demonstrations et references dans le
  catalogue public de la librairie.

### P7.2 - Ressorts et masses concentrees

- [x] ajouter des ressorts translationnels et rotationnels entre un noeud et
  le sol ou entre deux noeuds ;
- [x] autoriser une raideur scalaire par direction et une matrice locale
  symetrique validee ;
- [x] ajouter des masses nodales avec masse translationnelle, centre de masse
  documente et tenseur d'inertie symetrique positif ;
- [x] verifier energie elastique, forces opposees, masse totale, invariance par
  rotation et frequences analytiques masse-ressort ;
- [x] correler le SDOF ressort-masse au sol avec Code_Aster `18.1.0` `DIS_T`
  dans `VNV-DISCRETE-CODEASTER-SDOF-001` : la fleche statique passe a
  `1,39e-14 %` et la premiere frequence est identique a la precision machine.
  Les inerties excentrees, rotations et assemblages restent ouverts ;
- [x] refuser les raideurs negatives non explicitement classees comme
  experimentales et les inerties non physiques.

### P7.3 - MPC et RBE

- [x] definir une contrainte lineaire generale
  `sum(a_i * q_i) = b` avec validation des DDL et detection des conflits ;
- [x] appliquer les MPC par elimination creuse comme voie normale et conserver
  une formulation multiplicateurs de Lagrange pour verification ;
- [x] ajouter une liaison `RBE2` rigide avec translations et rotations du
  noeud maitre, offsets compris ;
- [x] ajouter une liaison de distribution `RBE3` sans rigidite artificielle,
  avec projection rigide ponderee, conservation du torseur et mode scalaire
  `weighted` explicitement limite ;
- [x] detecter contraintes redondantes, cycles et conflits ; les mecanismes
  restent signales par les diagnostics de rang existants ;
- [x] verifier mouvement de corps rigide, reactions, energie et comparaison
  matrice complete/systeme condense ; le patch sur structure EF assemblee est
  couvert par la future campagne externe P7.6 ;
- [x] garder les noms RBE comme analogies fonctionnelles documentees, sans
  revendiquer une compatibilite implicite avec un format proprietaire.

### P7.4 - Contact sans frottement

- [x] limiter le premier scope aux petites transformations, `linear_static`
  et au contact unilateral noeud-triangle a normale initiale figee ;
- [x] definir gap, normale, signe de pression et convention maitre/esclave ;
- [x] implementer le contact noeud-surface par active-set avec multiplicateurs
  de Lagrange exacts, sans penalite cachee ;
- [x] verifier les conditions de Kuhn-Tucker : gap positif, pression
  compressive et complementarite, ainsi que l'equilibre global ;
- [x] ajouter les tests de separation sans traction, fermeture sous
  compression et rejet des DDL tangents non stabilises par la matrice ;
- [x] refuser projection hors triangle, triangle degenere, methode iterative,
  MPC/RBE, normale invalide et non-convergence de l'active-set ;
- [x] verifier la convergence structurelle TET4 de la reaction normale sur
  quatre maillages (`VNV-CONTACT-TET4-STRUCTURAL-001`) ;
- [x] correler ouverture/fermeture normale avec Code_Aster `18.1.0` dans
  Docker epingle (`VNV-CONTACT-CODEASTER-LIAISON-UNIL-001`) ;
- [x] classer le contact sans frottement borne `engineering_ready_bounded`
  apres Owner review et demonstration de robustesse de l'active-set sur des
  faces EF deformables. Les trois
  orientations orthogonales d'un triangle maitre, un coin a deux contacts
  actifs et un triangle a trois noeuds maitres elastiques sont maintenant
  couverts. `VNV-CONTACT-DEFORMABLE-MASTER-003` confirme le transfert
  barycentrique vers des maitres mobiles. `VNV-CONTACT-TET4-MASTER-FACE-004`
  ajoute une face frontiere TET4 deformable et confronte la reponse couplee a
  une compliance EF obtenue independamment. Les extensions surface-surface,
  grand glissement et changement topologique restent `experimental`.
- [x] accepter une liste `master_faces` de triangles explicites et selectionner
  une seule facette compatible dans la geometrie initiale
  (`VNV-CONTACT-MASTER-SURFACE-005`). Cette extension reste bornee : aucun
  changement de facette, de normale ou recherche apres deformation n'est
  revendique ;
- [x] ajouter `contact_search_mode="updated"` pour une iteration bornee sans
  frottement qui relocalise la facette et la normale en petites translations ;
  `VNV-CONTACT-MASTER-SURFACE-005` verifie une commutation de la face 0 a la
  face 1, d'abord sur plan puis sur deux facettes pliees avec normale
  analytique. Un patch esclave discret a trois noeuds commute aussi
  coheremment vers la facette pliee, base de comparaison surface Code_Aster.
  Grand glissement et contact surface-surface restent ouverts ;
- [x] rendre les caps d'iterations et la tolerance de recherche strictement
  verifiables par `check-mesh` et a l'execution : les valeurs non finies,
  non entieres ou non positives sont refusees, sans troncature silencieuse ;
- [x] correler l'etat actif de cette face TET4 avec Code_Aster `18.1.0`
  `3D/TETRA4` et `LIAISON_DDL` (`VNV-CONTACT-CODEASTER-TET4-MASTER-004`),
  en distinguant cette cinematique active de la detection `LIAISON_UNIL` deja
  correlee ;
- [x] correler la normale finale d'une facette pliee avec Code_Aster `18.1.0`
  Docker et `LIAISON_DDL` (`VNV-CONTACT-CODEASTER-FOLDED-NORMAL-006`) : les
  trois deplacements sont a la precision machine. Cette preuve impose la
  facette finale et ne revendique pas la detection externe de commutation ;
- [x] comparer la commutation de facette a Code_Aster `18.1.0` sans ensemble
  actif impose : `VNV-CONTACT-CODEASTER-FOLDED-SEARCH-007` utilise
  `DEFI_CONTACT/CONTINUE` autonome sur une surface pliee et retrouve le
  deplacement moyen du patch QF_solver a `0,1157 %` (seuil `1 %`). La
  correspondance paire-a-paire des deux discretisations reste explicitement
  hors preuve ;
- [x] preparer l'Owner review sans la signer :
  `qualification/reviews/contact_v1_linear_static_bounded_pending.json`
  porte les preuves, limites et recommandations; la decision et la signature
  restent volontairement `pending` et `null` ;
- [x] traiter la demande Owner review `more_evidence_required` du `2026-07-29`
  avec `VNV-CONTACT-ADDITIONAL-MODELS-008` : coin a deux normales, rampe
  facettisee a trois esclaves et bloc deformable de `576` TET4 a deux contacts
  passent ;
- [x] comparer ces trois modeles sur dix paliers avec Code_Aster 18.1.0 :
  coin et rampe sont confondus, la branche fermee du bloc TET4 est confondue
  a partir de `0,2`, et CalculiX confirme QF_solver avant contact a
  `4,78e-5 %`. Le raffinement a `768` TET4 abaisse l'ecart de transition
  QF_solver/Code_Aster de `5,2565 %` a `4,3400 %`, sous le seuil `5 %` ;
- [x] confirmer ce passage avec un calcul proche de 10 000 elements :
  `VNV-CONTACT-CODEASTER-ADDITIONAL-H10K-010` contient `9 984` TET4 et
  donne un ecart maximal QF_solver/Code_Aster de `3,3029e-12 %` sur toute
  la courbe, avec un jeu final inferieur a `1e-15 m` ;
- [x] enregistrer l'Owner review du scope
  `contact-v1-linear-static-bounded` en
  `accepted_for_bounded_engineering_use`, datee et signee le `2026-07-29`
  dans `qualification/reviews/contact_v1_linear_static_bounded_2026-07-29.json` ;
- [ ] demontrer une surface EF generalisee au-dela du patch borne et etendre
  la recherche mise a jour au grand glissement sans frottement.

### P7.5 - Contact avec frottement

- [x] etendre le contact normal par une loi de Coulomb regularisee, limitee
  aux petites transformations et au contact noeud-triangle ;
- [x] distinguer clairement adhesion, glissement et retour sur le cone de
  frottement `||t_t|| <= mu p` ;
- [x] ajouter l'historique d'iteration local et les diagnostics de changement
  d'etat ; la tangente de stick est exposee, la tangente Newton complete
  reste a faire ;
- [x] verifier le bloc glissant analytique, la borne de Coulomb, la
  dissipation locale, l'inversion de charge et la sensibilite de la force
  saturee a la regularisation ;
- [x] ajouter une boucle adhesion-glissement a memoire et verifier le
  changement de sens ainsi que la dissipation incrementale ;
- [x] verifier l'independance au pas pour une rampe tangentielle a pression
  normale constante ;
- [x] ajouter un repli structurel TET4 : apres echec du point fixe, les deux
  efforts de glissement actifs sont resolus avec la contrainte normale exacte;
  la campagne `VNV-CONTACT-FRICTION-TET4-STRUCTURAL-002` verifie quatre
  maillages, gap, cone de Coulomb et branches `stick`/`slip` ;
- [x] ajouter une globalisation de secours : si la racine hybride de
  glissement echoue, une region de confiance sur le meme residu actif est
  tentee et tracee comme `active_slip_least_squares` ;
- [x] intercaler une Newton de branche active consistante : reponses unitaires
  exactes du systeme selle, derivee analytique de Coulomb et recherche
  lineaire d'Armijo, tracee comme `active_slip_consistent_newton`; les echos
  hybrides et Newton sont testes separement avant le repli par region de
  confiance ;
- [x] obtenir une correlation externe en glissement sature avec Code_Aster
  `18.1.0` Docker epingle : `VNV-CONTACT-FRICTION-CODEASTER-CONTINUE-003`
  donne `0,6070 %` d'ecart en `UX`; l'adhérence reste explicitement hors
  correlation car les regularisations tangentielles different ;
- [x] executer l'essai exploratoire Code_Aster en adhesion nominale : l'etat
  `stick` est bien retrouve dans QF_solver, mais `UX` differe de `396,20 %`
  faute de compliance tangentielle equivalente. Le resultat est classe
  `non_comparable`, sans masquer l'ecart ni le presenter comme echec mecanique ;
- [x] rejeter la calibration scalaire de penalite Code_Aster : deux charges
  d'adhesion de controle donnent respectivement `107,16 %` et `167,32 %`
  d'ecart avec un decalage de branche. L'adhesion externe reste ouverte et ne
  sera pas forcee par ajustement de parametre ;
- [ ] lineariser les changements d'ensemble actif et de normale pour les cas
  fortement non lineaires, puis etendre la correlation externe aux structures
  deformables et a l'adhérence comparable ;
- [ ] garder hors V1 qualifiable le grand glissement, l'usure, la cohesion,
  le contact thermique et les lois dependantes de la vitesse.

### P7.6 - Publication V1

- [x] exposer les preuves internes de contact par API
  `run_contact_verification(...)` et CLI `verify-contact`, avec dossier de
  resultats, rapports et manifestes regroupes ;
- [x] integrer `BEAM2`, ressorts/masses, MPC/RBE et contact dans l'API, le
  schema JSON, la CLI generique, les audits, les exports et le catalogue des
  demonstrations. La non-regression `rbe2_rigid_arm.json` couvre desormais le
  chemin API -> audit -> JSON/VTU -> CLI et verifie le transport du moment de
  liaison vers la reaction imposee ;
- [x] fournir au moins une demonstration analytique, une V&V externe, un cas
  d'erreur et un test d'integration par nouvelle famille : BEAM2 est correle
  en statique et modal, ressorts/masses en SDOF et RBE2 par
  `VNV-RBE2-CODEASTER-RIGID-ARM-001` avec Code_Aster epingle, et les deux
  contacts ont leurs campagnes bornees. Les extensions non couvertes restent
  explicitement experimentales ;
- [x] publier la matrice de maturite dans `docs/etat/capacites.md` et les
  exclusions dans `docs/etat/limites.md` : assemblage lineaire borne,
  BEAM2/ressorts/MPC-RBE experimentaux et contacts explicitement limites. La
  branche de glissement sature est correlee; l'adhesion reste
  `non_comparable` avec l'oracle externe ;
- [x] executer la campagne complete Windows et construire le site hors ligne :
  le `2026-07-29`, `pytest` donne `926 passed, 12 skipped`, le profil
  `verify-all engineering` donne `886 passed, 9 skipped, 23 deselected`,
  Ruff, `compileall`, MITC4 quick, TET10 et la campagne documentaire de
  `625` artefacts sont PASS ;
- [x] verifier l'archive prospective locale : `407` fichiers exportes,
  `0` constat, avec exclusion explicite des instructions de travail internes,
  des resultats, du site genere, des repertoires temporaires et des etudes
  V&V de travail ;
- [ ] confirmer la meme baseline dans la matrice CI Linux et inspecter
  manuellement le contenu de l'archive publique finale ;
- [x] fermer l'audit technique de confidentialite et choisir les licences de
  la V0.2.0-alpha. Au `2026-08-10`, la source publique compte `992` fichiers
  inspectes sans constat, l'archive propre `1102` fichiers sans constat et la
  nouvelle histoire publique un seul commit sans constat historique. Les
  licences retenues sont Apache-2.0 pour le code et CC BY 4.0 pour la
  documentation originale. La publication distante reste une action Owner
  distincte et n'est pas executee automatiquement ;
- [x] ajouter un prefiltre de chemins dans l'historique atteignable avec
  `scripts/audit_git_history.py`; tout constat impose une revue de contenu ou
  la creation d'un historique public propre, sans pretendre remplacer cette
  Owner review. Le passage du `2026-07-29` trouve `145` chemins d'etudes
  historiques dans `13` commits : aucun secret n'est etabli, mais la revue
  manuelle ou un historique public neuf reste obligatoire ;
- [x] formaliser la politique de controles proportionnes dans
  `docs/controle_qualite.md` : tests unitaires et V&V cibles pendant une
  iteration locale, integration seulement aux frontieres touchees, baseline
  complete reservee aux releases, refactorings transverses, dependances et
  regenerations controlees. La CI conserve la campagne exhaustive apres push.

Critere de sortie V1 : les assemblages lineaires sont reproductibles et
documentes; le contact sans frottement possede une campagne V&V complete; le
contact avec frottement est au minimum demonstrable, borne et explicitement
classe selon ses preuves. Aucun element reporte en V2 ne bloque ce jalon.

### Gel technique V0.2.0-alpha du 10 aout 2026

- [x] suite complete Windows : `1091 passed`, `17 skipped`, aucun echec ;
- [x] site hors ligne strict : `711` artefacts, aucune ressource locale
  manquante ;
- [x] MITC4 multicouche dynamique accepte par l'Owner pour un usage
  engineering experimental borne, avec reserve modale 10 000 QUAD4 ;
- [x] histoire publique neuve creee dans un depot local separe, avec identite
  Git `noreply`, sans les 12,2 Go de preuves V&V de travail ;
- [ ] confirmer la matrice CI Linux/Windows sur le commit public ;
- [ ] realiser l'audit Owner du grand modele et autoriser explicitement le
  push public.

## Post V0.2.0-alpha - preparation V0.2.1

Cette section regroupe les approfondissements reportes apres la fermeture de
l'alpha. Ils ne bloquent pas l'acceptation experimentale bornee du cas TET10
J2, mais ils bloquent toute hausse de maturite generale.

- [ ] refaire `VNV-TET10-J2-CODEASTER-COMPLEX-026` sur au moins deux niveaux
  de maillage et publier la convergence des deplacements, de la PEEQ moyenne
  et des energies ;
- [ ] comparer les champs de contraintes et de deformations hors de l'angle
  rentrant, avec une bande d'exclusion et une regle de moyenne documentees ;
- [ ] controler les rotations, les deformations locales maximales et le
  critere petites deformations, au-dela du seul ratio deplacement/longueur ;
- [ ] ajouter un chemin charge/decharge/recharge sur une geometrie complexe et
  verifier le stockage et la restauration des variables internes ;
- [ ] completer la correlation externe TET10 J2 avec Code_Aster et CalculiX
  sur une geometrie complexe, avec versions et decks traces ;
- [ ] soumettre le dossier complexe a une nouvelle Owner review avant toute
  evolution de `experimental` vers une maturite superieure ;
- [ ] ne pas presenter les pics de contrainte aux angles rentrants comme des
  valeurs acceptables sans etude de convergence et regularisation explicite.

## Gel V0.2.0-alpha avant publication

Date de l'etat : **2026-08-10**. Le perimetre V0.2.0-alpha est gele par Owner,
mais le push public n'est pas encore autorise. Le dossier de reference est
`docs/verification/release_v020_alpha_freeze.md` et son PDF de
relecture est `output/pdf/qf_solver_v020_alpha_freeze_owner_review.pdf`.

Etat technique consolide :

- TET4, TET10 et MITC3 modal/Newmark/harmonique, BEAM2 dynamique et entites
  discretes : decisions Owner `accepted_for_bounded_engineering_use` du
  2026-08-02, avec leurs recommandations de raffinement ;
- TET10 J2 structurel / Code_Aster : correlation technique `PASS`, maturite
  `experimental` bornee, decision Owner enregistree ;
- MITC4 multicouche dynamique plan : trois empilements testes en modal,
  Newmark et harmonique, correlation technique `PASS`, statut `experimental`
  conserve et reserve modale 10 000 QUAD4 ;
- MITC3 multicouche courbe a orientation projetee : preuve disponible,
  statut `experimental` borne ;
- licences, audit public, archive, site MkDocs strict, Ruff et compilation :
  `PASS` au dernier controle ;
- suite pytest complete : execution interrompue apres plus de dix minutes,
  sans verdict final ; ce point doit etre rejoue par lots puis en campagne
  complete avant le tag ;
- le tag local `v0.2.0-alpha` est cree apres le gate pytest ; aucun push public
  ne doit etre realise avant l'audit Owner du grand modele.

Les travaux post-alpha ne sont pas detailles dans le dossier de release ; ils
seront definis apres la publication et apres l'audit Owner du grand modele.
Le gel signifie que le perimetre et les limites de la V0.2.0-alpha ne changent
plus.

Checklist de fermeture avant publication :

- [x] enregistrer la decision Owner du gel V0.2.0-alpha ;
- [x] integrer les decisions dynamiques du 2026-08-02 et les validations
  recentes MITC3+/TET10 J2 ;
- [ ] relancer les tests longs par lots, puis executer une campagne complete
  avec resultat archive et sans timeout ;
- [ ] auditer humainement l'historique Git et le contenu exact de l'archive ;
- [ ] confirmer les URLs publiques et l'absence de donnees ou modeles prives ;
- [x] creer le tag local `v0.2.0-alpha` apres le gate pytest ;
- [ ] pousser uniquement apres l'audit Owner du grand modele et accord
  explicite.

## Commandes de pilotage

## Pages techniques et Owner review

### P-DOC-R2 - Refonte de lisibilite avant Owner review

Statut : **revision 0.2 acceptee; revision 0.3 acceptee documentairement avec
recommandations et ecarts V&V ouverts**. La decision 0.2 reste valide et
immuable. La revision 0.3 ne remplace pas les decisions mecaniques par
perimetre et ne vaut pas revue independante.

- [x] reorganiser le manuel dans l'ordre `element -> demonstration ->
  resultats et post-traitement -> limites -> references`, puis `methodes`,
  puis annexes communes uniquees en fin de volume ;
- [x] remplacer le rendu PDF Markdown par une source LaTeX controlee, avec
  equations vectorielles, matrices et fractions rendues nativement; ne pas
  publier de notation de secours telle que `frac`, `^` ou matrices texte ;
- [x] limiter taille, largeur et nombre des equations affichees dans le flux
  principal; les derivations longues et matrices completes vont en annexes
  referencees ;
- [x] relier chaque convention de Jacobien, interpolation et quadrature a son
  point de depart, une reference bibliographique, une formule `FORM-*`, le
  code et le test associes ;
- [x] expliciter pour chaque element le chargement: support, repere, signe,
  unite, resultant, moment, conservation, conditions de rejet et test ;
- [x] ajouter sur les demonstrations controlees les deformations
  initiale/deformee clairement
  distinguables, le champ de contrainte, les deformations, les invariants et
  les valeurs aux points d'integration lorsqu'elles sont pertinentes ;
- [x] corriger et publier les comparaisons QF/reference MITC4 disponibles;
  les figures TET10, courbes de residu logarithmiques et tableaux matriciels
  sont egalement corriges ;
- [x] relancer les cas Newmark a maillage structurel raffine avant toute
  conclusion sur une correlation externe : TET4 a `9 893` elements et TET10
  a `9 893` elements / `50 112` DDL avec etude maillage/pas de temps, ecart
  RMS final TET10 de `1,2403 %` ;
- [x] verifier visuellement chaque page PDF en rendu raster A4,
  puis enregistrer la revue Owner sans remplir aucune decision a l'avance.

Etat consolide du 2026-08-01 : TET10 flexion, residus logarithmiques, tableaux
matriciels et comparaisons QF/reference MITC4 disponibles sont integres. Le
PDF natif comporte TET4, TET10, MITC4, MITC3, BEAM2, les entites discretes,
les liaisons, le contact et les methodes de resolution.

La cloture automatique 0.3 couvre `33` couples element-analyse, `7` contrats
de chargement et `12` familles de methodes. Les cartes de contraintes et
deformations ainsi que les vues externes disponibles sont publiees. Quatre
absences d'oracle restent classees `gap_documented`; elles sont des actions
V&V et non des passes mecaniques.

Owner review du 2026-08-01 : decision
`accepted_with_recommendations`, tracee dans
`qualification/reviews/technical_manual_owner_review_2026-08-01.json`, puis
validation finale du PDF regenere tracee dans
`qualification/reviews/technical_manual_owner_review_final_2026-08-01.json`.
La relecture documentaire est fermee. Les
actions ouvertes sont la generalisation des champs de contraintes et
deformations, davantage de courbes de convergence, une correlation externe
par element et methode lorsque realisable, et les vues QF/reference
synchronisees. Le composite statique borne est integre a la V1; ses extensions
dynamiques, dommage et delaminage restent hors de cette acceptation.

- [x] convertir les equations de ressorts et masses concentrees en LaTeX natif ;
- [x] ajouter en annexe les liens de publications primaires, dont
  Hammer-Stroud pour la quadrature des simplexes ;
- [x] publier la convention d'epaisseur `shell_down`, `shell_middle`,
  `shell_up` et conserver les deux limites lorsque le plan moyen est une
  interface composite ;
- [x] integrer les pages composites au dossier technique principal V1 avec
  leur maturite explicite ;
- [x] publier des cartes colorees de contrainte/deformation pour chaque cas
  ou ces champs pilotent la conclusion mecanique ;
- [x] ajouter une correlation analytique ou Code_Aster/CalculiX pour chaque
  couple element-methode revendique, ou documenter explicitement l'absence
  d'oracle reproductible.

Critere technique atteint le `2026-08-01` : le PDF 0.3 de `277` pages est
genere depuis LaTeX, les equations sont lisibles, chaque element contient son
exemple et ses sorties, et les annexes ne rompent plus le fil de lecture. Le
PDF corrige porte l'empreinte
`ec06c572e27c45d2d1159c3eef2a0ed84eadda4adfc3a28e009c3eb7b36d1708`.
La decision Owner du `2026-08-01` est `accepted_with_recommendations`, tracee
dans `qualification/reviews/technical_manual_owner_review_0_3_2026-08-01.json`.
Elle ferme la qualite documentaire mais laisse ouverts les ecarts V&V
`PAIR-MITC3-LAMINATE` et `PAIR-MITC3-LAMINATE-DYN`. Les campagnes dediees
TET10 J2 et MITC4 multicouche dynamique ont depuis apporte une evidence
`verified_development_external_correlation`; la correlation structurelle TET10
J2 avec Code_Aster est tracee, mais la maturite `experimental` et la Owner
review restent ouvertes. Ces lignes interdisent toute extrapolation de maturite hors campagne
dediee et decision Owner.

- [x] executer `VNV-MITC4-LAMINATE-DYNAMIC-001` : modal, Newmark et
  harmonique sur `[0/90/90/0]`, masse coherente, condensation de drilling et
  post-traitement par pli ;
- [x] correl(er) ce cas avec Code_Aster sur meme maillage dans
  `VNV-MITC4-LAMINATE-DYNAMICS-CODEASTER-DST-018` : les ecarts maximaux sont
  `1,678 %` (modes), `0,422 %` (Newmark) et `0,205 %` (harmonique), tous sous
  les seuils traces. Le cas multicouche courbe a axe materiau projete est
  couvert separement par `VNV-COMP-CURVED-ORIENTATION-008` contre CalculiX;
  il valide la projection en statique, non la dynamique courbe complete ;
- [x] soumettre le perimetre MITC4 multicouche dynamique a une Owner review
  : Quentin Farinazzo l'accepte le `2026-08-10` pour un usage engineering
  experimental borne. La dynamique courbe, les stratifies non symetriques,
  le dommage, la rupture et la delamination restent exclus ;
  distincte. Le statut actuel est `verified_development`, pas Owner accepte.
- [x] executer la tentative de reference Code_Aster sur `10 000` QUAD4 pour
  `[45/-45/-45/45]` dans `VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023` ; les
  quatre frequences sont archivees, mais le controle a posteriori Code_Aster
  signale une alarme sur le mode 3 ;
- [ ] fermer la preuve modale MITC4 multicouche a `10 000` QUAD4 : le chemin
  QF_solver SciPy atteint environ `7,383e-6` de residu apres `30 000`
  iterations, au-dessus de `1e-7`. La prochaine action est un backend
  PETSc/SLEPc ou AMG avant toute correlation mode par mode.

Controles de cloture automatique du `2026-08-01` : `1022 passed`,
`13 skipped`; Ruff, `compileall`, MkDocs strict, QF_solver quick et MITC4
quick sont `PASS`. L'audit de publication analyse `649` fichiers avec
`0` constat. La baseline documentaire inclut desormais `pypdf==6.10.0` et
la decouverte Pandoc/MiKTeX n'embarque plus aucun chemin de poste.

- [x] produire une page Markdown par element et par methode avec geometrie,
  DDL, formulation, integration, algorithme, cas executable, maillage,
  chargement, conditions limites, resultats, deformee, invariants,
  convergence, limites et references ;
- [x] separer les pages des solveurs direct, CG, MINRES, GMRES, BiCGSTAB et
  arc-length ;
- [x] creer le registre controle
  `qualification/documentation_review_pages.json` sans decision pre-remplie ;
- [x] ajouter les formulations fortes et faibles detaillees TET4, TET10,
  MITC4 et BEAM2, avec au moins dix tests/invariants documentes par famille ;
- [x] composer les equations LaTeX dans le PDF et verifier automatiquement le
  minimum de dix pages par formulation principale : la premiere version
  affichait encore des equations trop grandes ou degradees; la refonte
  `P-DOC-R2` doit remplacer ce rendu avant Owner review ;
- [x] effectuer l'Owner review du dossier consolide couvrant chaque page avec
  `docs/verification/owner_review_pages_techniques.md`; decision finale
  `accepted_with_recommendations` du `2026-08-01` ;
- [x] enregistrer la decision Owner sur la revision complementaire 0.3 apres
  confirmation explicite du PDF de 277 pages et de son empreinte SHA-256 ;
- [ ] ne changer une maturite qu'apres Owner review enregistree et preuves
  V&V suffisantes. Une demonstration documentee ne vaut pas qualification.

```powershell
python -m pytest
python -m ruff check solveur mitc4 scripts tests
python .\qf_solver.py verify-all --profile engineering --json-report .\results\verification\verify_all_engineering.json
python .\scripts\build_docs.py --profile engineering
python .\qf_solver.py qualification-readiness --scope tet4-linear-static
python .\qf_solver.py qualification-readiness --scope mitc4-linear-static
python .\scripts\run_mitc4_vnv.py --output .\results\VNV-MITC4-LINEAR-V1
python .\scripts\run_mitc4_modal_vnv.py --output .\results\VNV-MITC4-MODAL-CANTILEVER-002
python .\scripts\run_mitc4_modal_plate_vnv.py --output .\results\VNV-MITC4-MODAL-PLATE-003
python .\scripts\run_code_aster_modal_vnv.py --output .\results\VNV-MITC4-MODAL-CODEASTER-DKQ-004 --mesh-size 32
python .\scripts\run_mitc4_modal_extended_vnv.py --output .\results\VNV-MITC4-MODAL-EXTENDED-005
python .\scripts\run_mitc4_newmark_vnv.py --output .\results\VNV-MITC4-NEWMARK-FREE-002
python .\scripts\run_mitc4_newmark_extended_vnv.py --output .\results\VNV-MITC4-NEWMARK-DAMPED-FORCED-003
python .\scripts\run_mitc4_newmark_broadband_vnv.py --output .\results\VNV-MITC4-NEWMARK-BROADBAND-004
python .\scripts\run_code_aster_newmark_vnv.py --output .\results\VNV-MITC4-NEWMARK-CODEASTER-DKQ-005
python .\scripts\run_mitc4_newmark_operational_vnv.py --output .\results\VNV-MITC4-NEWMARK-OPERATIONAL-006
python .\scripts\run_mitc4_harmonic_vnv.py --output .\results\VNV-MITC4-HARMONIC-MODAL-001
python .\scripts\run_mitc4_harmonic_condensation_vnv.py --output .\results\VNV-MITC4-HARMONIC-CONDENSATION-002
python .\scripts\run_mitc4_harmonic_broadband_vnv.py --output .\results\VNV-MITC4-HARMONIC-BROADBAND-003
python .\scripts\run_mitc4_nafems13h_vnv.py --output .\results\VNV-MITC4-HARMONIC-NAFEMS13H-004
python .\scripts\run_code_aster_nafems13h_vnv.py --output .\results\VNV-MITC4-HARMONIC-CODEASTER13H-DKQ-007
python .\scripts\run_j2_material_vnv.py --output .\results\VNV-J2-MATERIAL-CYCLIC-001
python .\scripts\run_calculix_j2_vnv.py --output .\results\VNV-J2-CALCULIX-ISOTROPIC-002
python .\scripts\run_j2_structural_vnv.py --output .\results\VNV-J2-TET4-CYCLIC-003
python .\scripts\run_j2_methods_vnv.py --output .\results\VNV-J2-NONLINEAR-METHODS-004
python .\scripts\run_j2_step_sensitivity_vnv.py --output .\results\VNV-J2-STEP-SENSITIVITY-005
python .\scripts\run_composite_analytic_vnv.py --output .\results\VNV-COMP-ANALYTIC-001
python .\scripts\run_composite_structural_vnv.py --output .\results\VNV-COMP-STRUCTURAL-CONVERGENCE-002
python .\scripts\run_calculix_composite_vnv.py --output .\results\VNV-COMP-CALCULIX-S8R-003
python .\scripts\run_composite_nafems_code_aster_vnv.py --output .\results\VNV-COMP-NAFEMS-R0031-CODEASTER-004
python .\qf_solver.py large-campaign --output .\results_large\P4-CAMPAIGN-PLAN-001 --targets 100000 1000000 3000000 --solver-backend petsc
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action weak
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action preconditioners -Execute
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action profile -Execute
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action tuning -Execute
python .\qf_solver.py postprocess-large --input .\model.h5 --displacements .\benchmark\displacements.bin --output .\post --chunk-size 65536
```

Le scope harmonique MITC4 est accepte avec recommandations pour l'usage
engineering interne. Le scope Newmark MITC4 est valide avec recommandations
pour l'usage engineering interne depuis le `2026-07-16`; une revue independante
et une baseline Git propre restent requises avant toute qualification externe.
