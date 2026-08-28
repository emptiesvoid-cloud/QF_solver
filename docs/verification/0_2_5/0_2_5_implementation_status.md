---
doc_id: DOC-NL-025-019
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 implementation status

Ce document suit l'implementation incrementale a partir du pack de planification
0.2.5. Il ne ferme aucune gate par la seule presence de code. Une gate est fermee
uniquement par une preuve reproductible liee a un SHA final.

## Etat par work package

| WP | Etat | Ce qui est effectivement disponible | Gate | Limite actuelle |
|---|---|---|---|---|
| WP0 | PARTIAL | Cartographie de l'architecture, contrats et tests cibles identifies | 025-G00 OPEN | Baseline complete 0.2.4 et couverture finale non rejouees |
| WP1 | CLOSED_BOUNDED | J2 multi-elements connectes TET4/TET10/HEX8/HEX20, dissipation plastique, rollback, tangent FD, sensibilite coarse/reference/refined, raffinement regulier 1/2/4, chargement cyclique global, bilan energetique `Wext = Ue + Dp` et retry adversarial | 025-G01 PASS | Qualification J2 bornee; les claims externes globaux restent sous G10 |
| WP2 | CLOSED_BOUNDED | Driver Full Newton commun pour la geometrie et TL StVK elastique TET4/HEX8, avec objectivite, tangent sparse, grande rotation, energie, raffinement pre-limit et correlation Code_Aster bornee; le chemin experimental `kinematics=total_lagrangian_j2` TET4/TET10/HEX8/HEX20 reste separe | 025-G02 PASS | Scope Owner: elastic Total-Lagrangian TET4/HEX8 dans le domaine pre-limit teste. J2 finite-kinematic, haut ordre, post-limit et contact restent recherche/ouverts |
| WP3 | CLOSED_BOUNDED | Analyse publique `linear_buckling` avec contribution géométrique initial-stress sparse, route généralisée `eigsh(K, M=-Kg)`, raffinement shift-invert après bracket et fallback diagnostiqué; Euler TET4-TL sur quatre niveaux structurés; sonde externe Code_Aster TET4 avec facteur et mode corrélés; preuves internes TET10/HEX8/HEX20 conservées pour la recherche | 025-G03 PASS | Scope fermé pour la première instabilité tangentielle sparse, TET4 externe et tendance Euler bornée; TET10/HEX8/HEX20 externes, post-buckling, imperfections et prédiction de ruine restent hors qualification |
| WP4 | PARTIAL | Correction arc-length augmentee sparse; cible signee et fenetre bornee `arc_length_stop_mode=max_steps` opt-in; chemin FEM TET4 total-Lagrangian sparse `VV-060` sur 24 pas; campagne interne monotone, restart depuis checkpoint intermédiaire, benchmark reduit shallow-arch traversant le point limite analytique avec erreur d'equilibre `< 1e-8`, chemin `total_lagrangian_j2` adaptatif borne sur TET4/TET10/HEX8/HEX20 `VV-064` vers le facteur 0,5 et télémétrie structurée des retries/cutbacks arc-length `VV-072` | 025-G04 OPEN | Les quatre chemins finite-kinematic restent des preuves internes monotones de recherche; snap-through FEM unifié, post-buckling qualifié, branchement général et corrélation externe restent hors fermeture |
| WP5 | CLOSED_BOUNDED | Contact frictionless sur le résidu/tangent commun; mode opt-in `contact_finite_sliding=true` avec projection bornée, normales actualisées, transitions de facettes, recontact, rollback et sensibilités penalty; corrélation Docker Code_Aster bornée sur historiques compatibles, contrôlée sur 768 et 9 984 TET4 | 025-G05 PASS | Pas de surface-to-surface généralisé, mortar, friction, impact, self-contact ou large sliding non borné; CalculiX reste un support SHOULD |
| WP6 | PARTIAL | Contrat `CompositeNonlinearAssembly` sparse et campagne interne rejouée sur un maillage TET4 connecté à deux éléments couvrant J2 + géométrie, géométrie + contact et J2 + géométrie + contact, complétée par les observations quatre familles TET4/TET10/HEX8/HEX20 et une étude de maillage J2 + géométrie niveaux 1/2/4, toutes via les chemins incrémentaux communs | 025-G06 OPEN | `results/vnv_0_2_5/g06_latest/` est `PASS_INTERNAL_RESEARCH`; il manque une étude de maillage géométrie+contact, les corrélations Code_Aster MUST couplées et les historiques énergie/tangent complets; le contact reste une composition bornée penalty frictionless |
| WP7 | OPEN | Aucun changement de friction qualifiant | 025-G07 NOT_IN_RELEASE_SCOPE | Promotion Owner requise |
| WP8 | CLOSED_BOUNDED | Script reproductible `scripts/benchmark_nonlinear_025.py` avec chemins explicites load-control, geometric_static, arc-length, finite-sliding borné, couplé et finite-kinematic arc-length; temps, DOF, iterations, allocations Python, RSS optionnelle, timers du driver Newton et décomposition élémentaire/sparse/contact; résumés multi-répétitions avec moyenne, médiane, min/max et écart-type; plan d'assemblage nonlinear reutilisant noyaux, matériaux immuables et mappings DDL avec compteurs hit/miss; cache de géométrie de référence Total-Lagrangian avec compteurs hit/miss; accumulation de tangente CSR par chunks avec compteurs de pic et estimation des buffers de staging; vectorisation exploratoire du tangent TL TET4/HEX8 conservée sans écart numérique observé | 025-G08 PASS | Caracterisation de performance bornee, sans claim HPC ou gain universel |
| WP9 | CLOSED_BOUNDED | Raisons structurees pour stagnation, contact, pénétration excessive, buckling, solveur lineaire, éléments invalides et etats non finis; `NumericalConvergenceError.to_dict()`, historique de residu Full Newton, compteur de line-search et campagne adversariale couvrant limites Newton, cutback minimum, élément invalide, mise à jour matériau, contact, pénétration, arc-length et bracket buckling; retry contact injecté, échec au deuxième incrément adaptatif, retry arc-length avec journal de rayon et cas réel `VV-068` de garde de pénétration avec rollback/cutback vérifiés | 025-G09 PASS | Contrat de diagnostic/rollback interne seulement; les gates fonctionnelles restent independantes |
| WP10 | PARTIAL | Archives externes 0.2.4 reutilisables et harnais Code_Aster multi-elements 0.2.5 execute sur maillage régulier partagé | 025-G10 BLOCKED | Les cellules J2 multi-element, grande deformation, flambement et contact restent bornées; G04 et G06 conservent des cellules Code_Aster MUST ouvertes. CalculiX reste SHOULD et non bloquant |
| WP11 | OPEN | Le sweep final `pytest tests -q` a produit `1713 passed, 2 failed, 183 skipped` en `1519,64 s` | 025-G11 OPEN | Échec de la règle de taille `scripts/build_g02_evidence.py` (986 lignes) et d'une assertion de diagnostic buckling; couverture, packaging et smoke restent non exécutés après l'arrêt |
| WP12 | PARTIAL | Pack de planification et present suivi disponibles | 025-G12 OPEN | Owner Review finale et preuves SHA final a produire |

## Tests ciblés observes

## Actualisation externe du WP3

Le harnais `calculix_buckling_025.py` produit désormais une preuve par famille
et conserve les erreurs d'exécution dans le résumé au lieu d'interrompre la
campagne sans artefact. Le générateur borne maintenant le sous-espace de
Lanczos à la taille du système libre, ce qui supprime l'erreur ARPACK des
petits cas TET4/HEX8. Le replay
`results/vnv_0_2_5/calculix_buckling_solid_families_mode1_recorded/summary.json`
reste bloqué : TET4, TET10 et HEX8 restent hors de la bande de corrélation
de 10 % (écarts respectifs d'environ 24,6 %, 45,1 % et 13,4 %) et C3D20
s'arrête nativement dans CalculiX. Le même ordre de nœuds C3D20 passe la
corrélation statique existante ; aucune qualification buckling externe n'est
donc revendiquée et `025-G03`/`025-G10` restent ouverts.
Un probe séparé C3D20 à deux cellules (`results/vnv_0_2_5/calculix_buckling_hex20_cells2_probe/`)
se termine également par `BLOCKED_EXTERNAL_TOOL` avec `double free or corruption
(!prev)` dans l'exécutable CalculiX épinglé ; il est conservé comme diagnostic
externe et ne constitue pas un PASS.

Les tests suivants ont ete executes pendant cette implementation incrementale :

- contrats nonlinear/geometriques et TL : verts ;
- tests J2 multiaxiaux, tangent FD et transactions : verts ;
- benchmark J2 multi-elements connectes sur quatre familles : vert ;
- chemin public `linear_buckling` TET4 avec `eigsh` : vert ;
- campagne interne buckling TET4/TET10/HEX8/HEX20 :
  `PASS_INTERNAL_RESEARCH`, facteurs critiques `63.8164`, `43.2031`, `47.4844`
  et `1.88342`, brackets relatifs sous `1e-4`; les lignes TET10/HEX20 sont
  internes/recherche, cette observation ne ferme pas G03 et le petit TET4 peut
  utiliser le fallback dense interne ;
- référence analytique Euler TET4-TL dans
  `results/vnv_0_2_5/robustness_high_order_latest/euler_buckling/summary.json` :
  `PASS_INTERNAL_RESEARCH` sur `24x6x6 -> 32x8x8`, erreur Euler finale
  `9.489 %`, variation de raffinement et bracket sous les limites internes.
  Cette preuve reste limitée au TET4 et ne ferme pas G03 sans corrélation
  externe et couverture des familles haut ordre ;
- smoke test CLI `linear_buckling` depuis l'exemple SI : vert (`PASS`, maturite
  `research`, donc verdict global `WARNING`) ;
- validation schema des controles `linear_buckling` : verte ;
- smoke profiling TET4/HEX8 avec `benchmark_nonlinear_025.py` : vert ;
- tests adversariaux d'etat non fini et d'arc-length : verts ;
- erreurs numeriques CLI : raison et diagnostics JSON structures : verts ;
- diagnostics Full Newton : historique de residu, backend, tolerance et
  reductions de line-search exportes : verts ;
- `VV-026` remonte egalement les historiques de residu, les ratios de reduction
  et les ordres observes lorsque calculables pour Full Newton et Modified
  Newton ; ces indicateurs restent descriptifs et ne ferment aucune gate par
  eux-memes ;
- `VV-004` couvre maintenant huit etats constitutifs independants ou historiques
  (elastique, proche du seuil, traction, compression, cisaillement,
  rechargement, cycle de cisaillement et chemin non proportionnel), avec un
  balayage explicite du pas FD ; erreur maximale observee `2.12e-10`, sans
  revendication de qualification externe ;
- campagne adversariale Full Newton : `MAX_ITERATIONS`, `SINGULAR_TANGENT`,
  `NAN_DETECTED`, `LINE_SEARCH_FAILURE` et `MIN_INCREMENT_REACHED` classes avec `converged=false` :
  `PASS_INTERNAL_FAILURE_CONTRACT` ;
- la campagne de failure contract classe aussi l'épuisement de continuation en
  `ARC_LENGTH_FAILURE` et l'absence de bracket sparse en `BUCKLING_FAILURE`,
  avec `converged=false` et diagnostics propres aux solveurs ; ces observations
  sont reliées à `VV-050` et ne ferment pas G09 ;
- failure campaign: contact assembly failure injected once during an adaptive
  load step, then cutback `1.0 -> 0.5`, retry at factors `[0.5, 1.0]` and
  committed states preserved; `retry_cases[0].passed = true`. This is an
  internal adversarial contract, not external contact qualification;
- failure campaign: a controlled failure after the first accepted adaptive
  increment preserves the committed prefix `[0.5]`, retries with `0.25` and
  converges at factors `[0.5, 0.75, 1.0]`; this is `VV-051` internal evidence
  and does not close G01/G09;
- les exceptions d'assemblage du driver commun sont maintenant converties en
  `INVALID_ELEMENT`, `MATERIAL_UPDATE_FAILURE` ou `CONTACT_UPDATE_FAILURE`
  avec diagnostics d'increment ; la matrice de failure modes reste toutefois
  incomplete pour les cas contact/path-dependent multi-etapes ;
- le contrat de transaction vérifie désormais le digest du committed avant
  `commit()` ou `rollback()` pour les états matériau et les états génériques;
  une mutation en place pendant un trial est classée `STATE_CORRUPTION` avec
  les digests avant/après. `VV-069` est couvert par deux tests unitaires et la
  campagne adversariale complète est maintenant rejouée avec le statut
  `PASS_INTERNAL_FAILURE_CONTRACT`; la gate G09 reste ouverte jusqu'à ce que
  cette preuve soit régénérée et reliée à un SHA propre ;
- `VV-071` est maintenant rejouable dans la campagne interne : deux positions
  situées hors des triangles sélectionnent respectivement les faces `0` puis
  `1`, conservent un gap `-0.1`, signalent `projection_clamped=true` et le
  mode `bounded_closest_point_node_to_triangle`, puis assemblent une tangente
  sparse non vide. Le test ciblé
  `tests/unit/test_contact_finite_sliding.py` produit `6 passed` après cette
  extension, dont un smoke test du résultat Newton commun avec les diagnostics
  de projection. Le mode est sérialisé par incrément pour éviter toute
  ambiguïté entre projection exacte et projection bornée. Cette observation
  reste bornée au chemin penalty frictionless opt-in et ne ferme pas `G05`.
- l'epuisement de `max_arc_steps` est maintenant expose comme
  `ARC_LENGTH_FAILURE` avec le facteur courant, le facteur cible et le rayon
  final ; le benchmark reduit shallow-arch traverse maintenant le point limite,
  mais ne remplace pas un benchmark FEM snap-through ni la preuve externe ;
- campagne arc-length interne : `PASS_INTERNAL_RESEARCH`, cinq étapes
  monotones, facteur final `1.000054`, résidu relatif maximum `8.73e-11`; cela
  ne constitue pas une preuve snap-through, post-buckling ou corrélation externe ;
- le chemin global arc-length conserve le comportement par défaut `target_load`
  et accepte désormais, de manière opt-in, une cible signée ou une fenêtre
  `max_steps` avec `arc_length_allow_load_factor_turning` et une enveloppe de
  facteur explicite ; les tests dédiés passent, sans fermeture de G04 ;
- benchmark reduit shallow-arch : `PASS_INTERNAL_RESEARCH`, 80 étapes, point
  limite analytique observé à l'étape 14, une inversion de pente de la branche,
  erreur d'équilibre maximale `3.251e-13`; cette observation reste une
  vérification algorithmique et ne ferme pas G04 ;
- restart arc-length depuis `arc.step00000001.npz` : `10 passed` dans la suite
  checkpoint, déplacement final concordant avec le run continu; le contrat de
  reprise est interne et ne ferme pas la preuve de branche/limite-point G04 ;
- campagne `VV-064` avec rayon adaptatif borné :
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`, statut
  `PASS_INTERNAL_RESEARCH`; TET4, TET10, HEX8 et HEX20 atteignent le facteur
  signé `0,5` avec un résidu relatif maximal de `9,62e-08` ou moins. Les
  nombres d'étapes observés sont respectivement `2`, `98`, `122` et `200`.
  Les plages de facteur et de rayon sont exportées par famille et la figure
  `finite_kinematic_arc_length.png` trace les trajectoires et l'adaptation du
  rayon.
  Cette preuve établit un contrat commun de continuation monotone, mais ne
  revendique ni snap-through FEM, ni snap-back, ni post-buckling, ni corrélation
  externe et ne ferme pas `025-G04`.
- assemblage composite sparse et branchement sur le Full Newton commun : verts ;
- benchmark de cout : timers load-control `assembly_seconds`,
  `linear_solve_seconds` et `line_search_seconds` observes sur TET4/HEX8 ;
- plan d'assemblage nonlinear : tests de contrat verts, quatre familles
  convergentes dans `nonlinear_load_control_cache_latest.json`, compteurs
  `element_cache_hits` non nuls et `element_cache_misses=0`; la comparaison
  setup-time reste une observation mono-run sur worktree sale et ne ferme pas
  G08 ;
- benchmark paths `load_control`, `arc_length`,
  `arc_length_finite_kinematic`, `contact` et `coupled` : les chemins TET4
  dédiés convergent avec diagnostics et allocations enregistrés; le chemin
  finite-kinematic est opt-in et accepte les quatre familles. Cette
  caractérisation ne constitue pas une mesure de scaling ni une optimisation
  validée ;
- benchmark finite-kinematic arc-length quatre familles :
  `results/benchmark_0_2_5/arc_length_finite_kinematic_latest.json`, quatre
  lignes `PASS` vers le facteur signé `0.5`. Les temps mur observés sont
  `2.943 s` (TET4), `83.906 s` (TET10), `6.546 s` (HEX8) et `235.151 s`
  (HEX20); les itérations Newton totales sont respectivement `76`, `670`,
  `120` et `1479`, avec un résidu relatif maximal de `9.90e-08` ou moins.
  Le budget de continuation a été porté à `512` pas pour éviter un arrêt
  artificiel du cas HEX20 à `0.499995`; le run reste une observation unique
  sur worktree sale et ne ferme pas `025-G08` ;
- sensibilite au pas de charge sur TET4 connecte : verte, sans seuil invente ;
- sensibilite coarse/reference/refined sur les quatre familles :
  `PASS_INTERNAL_SENSITIVITY`; ecarts reference-versus-refined conserves dans
  la sortie de campagne, sans promotion automatique ;
- raffinement maillage niveaux `1/2/4` et cycle global avec inversion de charge
  sur les quatre familles : `PASS_INTERNAL_MESH_REFINEMENT` et
  `PASS_INTERNAL_CYCLIC`, sans seuil de release invente ;
- bilan énergétique sur le maillage J2 connecté à dix increments pour les quatre
  familles : `PASS_INTERNAL_ENERGY`. Les termes reconstruits sont `Wext`,
  `Ue` et `Dp`; les dissipations aux points de Gauss restent non négatives et
  les erreurs relatives observées sont comprises entre `8.91e-10` et
  `8.64e-09`. Cette preuve est interne et son acceptance band reste une
  décision Owner ;
- rollback adversarial sur TET4 connecté : un trial est volontairement muté
  puis rejeté, le cutback `1.0 -> 0.5` est journalisé, le retry repart de
  l'état committé intact et la solution finale reste cohérente avec la
  référence à pas fixes. Verdict : `PASS_INTERNAL_ROLLBACK`; cette preuve
  n'est pas une revendication d'instabilité matériau ;
- campagne `RobustnessQualificationCampaign` executee en temporaire :
  `PASS_INTERNAL`, tangent FD maximal `7.12e-11`, multi-elements TET4/TET10/
  HEX8/HEX20 `PASS`, raffinement/cycles internes `PASS`, correlation archivee
  `PASS_EXTERNAL_CORRELATION_BOUNDED` ;
- replay Docker du cas Code_Aster RQ-G08 0.2.4 : `PASS_EXTERNAL_CORRELATION`,
  80/80 checks, erreur relative maximale `2.62e-15` ; cette preuve reste un
  patch affine mono-element et ne ferme pas la correlation multi-elements G10 ;
- campagne Code_Aster multi-elements 0.2.5 rejouee dans Docker sur un maillage
  régulier partagé : `PASS_EXTERNAL_CORRELATION` avec 64 checks. TET4/TET10/
  HEX8/HEX20 concordent sur déplacements, réactions, `stress_xx` et PEEQ dans
  la limite de 0,5 %. Pour TET10, le chemin de corrélation active explicitement
  `tet10_nonlinear_quadrature=code_aster_5`, ce qui aligne les cinq points QF
  avec les cinq valeurs `ELGA` Code_Aster. La règle historique Hammer à quatre
  points reste la valeur par défaut et les gates G01/G10 restent ouvertes pour
  leurs critères de qualification plus larges ; aucune tolérance n'a été élargie ;
- builder documentaire engineering : `706 artifacts`, campagne documentaire
  `PASS` ;
- les rapports `targeted_after_*` antérieurs restent archivés pour la
  traçabilité des étapes précédentes ; ils contiennent notamment les anciens
  runs à `70 passed` et ne doivent pas être lus comme l'état courant ;
- readiness targeted courant après le cache de géométrie de référence :
  tests `PASS` (`186 passed, 2 skipped` en `94.06 s`), documentation `PASS`
  (`706 artifacts`), verdict global `NOT_READY` attendu car `025-G00`,
  `G01`, `G02`, `G03`, `G04`, `G05`, `G06`, `G08`, `G09`, `G10`, `G11` et
  `G12` restent ouverts ; aucune gate n'a été modifiée par cette exécution ;
- campagne de robustesse rejouée après intégration du kernel haut ordre dans le
  runner : `results/vnv_0_2_5/robustness_high_order_latest/summary.json`, statut
  global `PASS_INTERNAL`; les quatre lignes finite-kinematic sont `PASS`, avec
  erreurs tangent FD `4.81e-10` (TET4), `5.49e-10` (TET10), `9.65e-10`
  (HEX8) et `4.99e-10` (HEX20). Cette preuve reste interne/recherche et ne
  constitue ni une qualification grandes rotations ni une corrélation externe ;
- campagne de robustesse rejouée avec les lignes buckling haut ordre :
  `results/vnv_0_2_5/robustness_high_order_buckling_latest/summary.json`, statut
  global `PASS_INTERNAL`; TET4/TET10/HEX8/HEX20 ont tous un facteur critique
  fini, un bracket relatif sous `1e-4`, une tangente sparse non vide et un
  résidu de précharge fini. Cette observation interne ne ferme pas G03 : elle
  ne remplace ni Euler, ni la convergence maillage, ni la corrélation externe ;
- campagne de géométrie haut ordre connectée :
  `results/vnv_0_2_5/robustness_high_order_geometric_latest/summary.json`,
  `PASS_INTERNAL_RESEARCH`; TET10 (5 éléments, 78 DDL) et HEX20 (1 élément,
  60 DDL) convergent en 12 itérations, avec résidus maximum respectifs
  `6.70e-13` et `8.52e-13`, `detF` minimum positif et énergie positive. Cette
  preuve est un smoke élastique Saint-Venant-Kirchhoff et ne ferme pas G02.
- smoke de grande déformation `VV-057` : `PASS_INTERNAL_RESEARCH` sur TET4
  et HEX8 sous charge transverse, avec angles de ligne d'extrémité respectifs
  d'environ `34` et `42` degrés, `det(F)` positif et résidus sous `1e-7`.
  Cette preuve élastique bornée ne vaut pas qualification de grande rotation
  plastique, de post-flambement ou de corrélation externe.
- sensibilité maillage grande-déformation `VV-066` : `PASS_INTERNAL_RESEARCH`
  sur les niveaux 1/2 TET4 et HEX8 à l'échelle de charge `1.0`, avec déplacement,
  angle de ligne, énergie, `det(F)`, résidu et coût Newton enregistrés. Les
  variations coarse/refined restent descriptives et ne ferment pas G02 sans
  bande d'acceptation et corrélation externe. Le smoke distinct à l'échelle
  `1.5` converge sur le maillage grossier mais échoue en line-search sur HEX8
  raffiné ; cette limite est conservée explicitement.
- sensibilité maillage grande-déformation haut ordre `VV-067` :
  `PASS_INTERNAL_RESEARCH` sur TET10 et HEX20, niveaux 1/2 à l'échelle de charge
  `0.25`, avec `det(F)` positif et résidus finis. Cette preuve est volontairement
  une étude basse charge et ne revendique ni grande rotation plastique, ni
  convergence maillage qualifiée, ni corrélation externe.
- sensibilité maillage buckling `VV-058` : `PASS_INTERNAL_RESEARCH` sur les
  niveaux assemblés `1/2` pour TET4, TET10, HEX8 et HEX20, avec facteur critique,
  bracket, DDL, NNZ, résidu du mode critique et résidu de précharge archivés.
  La variation coarse/medium
  est une tendance interne bornée, pas une fermeture de convergence maillage,
  et ne ferme pas G03.
- contact frictionnel/frictionless et API cible : verts ;
- branche expérimentale `total_lagrangian_j2` : TET4, TET10, HEX8 et HEX20 convergent via le
  même `NonlinearStaticSolver`, avec récupération objective Green-Lagrange /
  seconde Piola et états aux points d'intégration ; seul Full Newton est accepté
  sur ce chemin, `modified_newton` reste rejeté et `arc_length` est ouvert en
  opt-in pour le périmètre homogène borné de `VV-064` ; cette
  observation reste `PASS_INTERNAL_RESEARCH` et ne ferme pas G02/G06 ;
- campagne `run_finite_kinematic_j2_benchmark` : TET4/TET10/HEX8/HEX20,
  résidu Newton, rotation rigide, PEEQ finite-kinematic et tangent FD
  enregistrés en `PASS_INTERNAL_RESEARCH`; les erreurs de tangent élémentaire
  par différences finies sont de l'ordre de `5e-10` pour TET10 et HEX20. Le
  chemin HEX20 reste un smoke test mono-élément et aucune corrélation externe
  ni promotion de modèle n'en découle ;
- le kernel `total_lagrangian_j2` accepte désormais aussi TET10 et HEX20 dans
  le même driver Full Newton, avec quadrature et récupération des états aux
  points d'intégration propres à chaque famille. Les tests unitaires dédiés
  passent (`tests/unit/test_total_lagrangian_j2.py`); cette extension reste
  `PASS_INTERNAL_RESEARCH` et ne participe pas a la fermeture bornee de
  `025-G02`; l'objectivité, le tangent FD, la convergence de maillage et la
  corrélation externe des familles haut ordre restent a produire avant toute
  promotion.
- contribution contact `contact_mode=penalty` : activation unilatérale sparse
  et convergence de cas TET4 small-strain et TET4 finite-kinematic J2 via le
  même driver Newton ; recherche initiale, frictionless uniquement, sans
  fermeture de G05/G06 ;
- campagne contact commune : `PASS_INTERNAL_RESEARCH`, état ouvert sans
  tangent actif puis état pénétrant avec contact `0` actif et tangent sparse
  `nnz=4`, résidu global maximum `4.91e-09`; les modes `initial` et `updated`
  convergent dans le driver commun, la portée reste penalty frictionless ;
- corrélation externe contact `VNV-CONTACT-CODEASTER-LIAISON-UNIL-001` rejouée
  dans Docker : `PASS_EXTERNAL_CORRELATION`, cinq contrôles passés sur les
  branches compression/fermeture et séparation/ouverture, avec accord exact
  QF/Code_Aster sur le déplacement normal, le gap et l'activation. Cette
  preuve est archivée dans
  `results/vnv_0_2_5/contact_code_aster_liaison_unil/`; elle ne couvre pas le
  contact surface-à-surface, le finite sliding, les normales mises à jour, le
  recontact ni le rollback contact ;
- corrélation externe `VNV-TET4-TL-CALCULIX-STRUCTURAL-008` rejouée avec
  CalculiX 2.20 : `PASS_EXTERNAL_CORRELATION`; quatre niveaux TET4/C3D4,
  erreur QF/CalculiX de charge critique `3.52e-4` au niveau fin, erreur
  CalculiX/Euler `5.91 %`, et erreur de patch Cauchy `1.17e-7`. Cette preuve
  reste bornée à la route TET4 Total-Lagrangian et ne ferme pas G03 ;
- campagne de recontact commune `VV-047` : `PASS_INTERNAL_RESEARCH` sur le
  chemin `[0.25, 1.0, 0.0, 1.0]`, avec activation `[false, true, false, true]`
  et résidus relatifs sous `1e-7`. Les diagnostics par pas exposent désormais
  les contacts actifs, les gaps et le mode de recherche; la preuve reste
  limitée à un triangle plan TET4 et ne ferme pas G05 ;
- campagne de sensibilité penalty : `PASS_INTERNAL_RESEARCH` sur les
  pénalités `1e2` à `1e6`, avec convergence Newton pour chaque valeur,
  pénétration non croissante et `contact_tangent_nnz` exporté par incrément.
  Cette preuve caractérise une tendance locale ; elle ne définit pas une
  pénalité de production, ne remplace pas une étude de conditionnement et ne
  ferme pas G05 ;
- recherche multi-face `VV-055` : `PASS_INTERNAL_RESEARCH` avec deux facettes
  coplanaires et positions compatibles sélectionnant `[0, 1]` en mode
  `contact_search_mode=updated`. Cette observation couvre la sélection locale
  de facette, pas le finite sliding généralisé ni le contact surface-à-surface ;
- traversée mise à jour `VV-056` : `PASS_INTERNAL_RESEARCH` sur deux TET4
  connectés avec charge tangentielle et normale; la séquence de facettes
  observée est `[[0], [0], [1], [1]]`, avec un changement de facette et un
  résidu global sous `1e-7` dans le même driver Newton. Cette preuve reste
  bornée à une surface plane à deux facettes et ne ferme pas G05/G06 ;
- couplage J2/geometrie quatre familles `VV-059` : `PASS_INTERNAL_RESEARCH`
  sur deux éléments connectés TET4, TET10, HEX8 et HEX20, avec le même chemin
  `total_lagrangian_j2`, résidus maximum sous `1e-6` et PEEQ finale observée.
  Cette preuve exclut le contact et ne ferme pas G02/G06 ;
- chemin FEM arc-length `VV-060` : `PASS_INTERNAL_RESEARCH` sur un
  cantilever TET4 total-Lagrangian imparfait, 24 pas sparse, résidu maximum
  `2.54e-10` et `det(F)` minimum `0.999862`. La charge reste monotone dans la
  fenêtre observée ; ce résultat ne ferme pas G04 et expose la dette de
  fusion avec le driver commun ;
- campagne de failure contact : une limite explicite `contact_max_penetration`
  produit `CONTACT_PENETRATION_EXCESSIVE`, `converged=false` et les valeurs de
  pénétration/limite dans les diagnostics. Ce contrat est fail-closed et reste
  une preuve interne ; il ne ferme pas G05/G09 ;
- `VV-068` ajoute un cas réel de garde de pénétration sur un bloc TET4
  multi-éléments : deux essais Newton dépassent transitoirement la limite,
  sont classés `CONTACT_PENETRATION_EXCESSIVE`, puis le cutback converge aux
  facteurs `[0.5, 0.75, 1.0]`. Le déplacement final, la norme de réaction et le
  gap final concordent avec une référence en huit petits pas. Cette preuve
  interne renforce le contrat G09 sans fermer G05/G09 ;
- campagne de couplage interne : `PASS_INTERNAL_RESEARCH` sur un maillage TET4
  connecté à deux éléments et trois chemins (`J2 + géométrie`, `géométrie + contact`, puis `J2 + géométrie +
  contact` avec recherche mise à jour). Les trois cas passent par le même
  résidu/tangent et le même Full Newton; cette observation ne ferme pas G06,
  qui exige encore des cas maillés et des corrélations externes ;
- snapshots de regression et CLI geometric nonlinear : verts.
- génération documentaire engineering : `706 artifacts`, `campaign=PASS` ; les
  contrats de génération ciblés ont produit `27 passed, 2 skipped`.
- audit public contrôlé : `2 passed` après synchronisation du nombre de sources
  publiques (`389`) et du scan de fichiers candidats (`1879`) avec le pack 0.2.5.

Une premiere batterie ciblee de cette tranche a produit **116 passed in 25.67s**;
les sous-batteries executees apres les derniers contrats ont egalement ete
vertes, dont **110 passed in 23.54s** pour le lot V&V/documentation cible. Ruff
est vert sur les fichiers modifies. Le dernier lot cible noyau + integration a
produit **131 passed, 4 skipped in 70.51s**. Aucun test de couverture n'a ete
lance et aucune suite complete 0.2.4/0.2.5 n'est declaree par ce document.

Depuis cette synthese, la batterie implementation ciblee a produit **36 passed
in 22.75s**, la batterie documentation complete **42 passed, 6 skipped in
12.60s**, et Ruff est vert sur les fichiers modifies. Le benchmark régulier
TET4/HEX8 a également été exécuté avec les timers d'assemblage et de résolution.

Le lot ciblé non linéaire (contrats d'état, Newton sparse, assemblage composite,
TL HEX8, dissipation, buckling, sensibilité, cycles, benchmark et campagne
adversariale) a ensuite produit **32 passed in 22.47s**. Les tests ciblés de
corrélation et de génération documentaire ont produit **26 passed, 2 skipped
in 2.20s**, puis **23 passed, 2 skipped in 1.96s** après la mise à jour de la
note de comparabilité TET10. Ruff reste vert sur les fichiers concernés.

La couverture, la suite complete et les campagnes externes ne sont pas declarees
executees par ce document.

Le benchmark finite-kinematic TET4 a ensuite été rejoué après vectorisation du
tangent : **1.34 s** au total, dont **1.10 s** d'assemblage, contre **43.21 s**
et **41.44 s** avant modification sur le même cas. Les déplacements, PEEQ,
résidu et nombre d'itérations restent concordants dans cette observation
unique. Le point HEX8 correspondant est **1.55 s**, dont **1.27 s** d'assemblage
et 17 itérations. Ces résultats restent une caractérisation locale et ne
ferment pas 025-G08.

La campagne Code_Aster multi-elements a ensuite ete rejouee avec une
convention TET10 explicite. Elle produit **64 checks** et
`PASS_EXTERNAL_CORRELATION` : les quatre familles sont comparables sur le
maillage regulier partage, avec 50 points QF et 50 valeurs `ELGA` pour TET10.
Cette preuve ferme le finding de comparabilite TET10, mais ne ferme pas a elle
seule 025-G01/025-G10, qui exigent encore leurs autres preuves et une liaison au
SHA candidat final.

Apres ce correctif, le lot cible non lineaire, correlation et documentation a
produit **54 passed, 2 skipped in 17.17s** et Ruff est vert sur les fichiers
concernes. Cette execution reste ciblee et ne remplace ni la couverture ni la
non-regression complete.

Le bilan énergétique ciblé a ensuite produit **4 passed in 20.67s**. Le replay
des quatre familles donne `PASS_INTERNAL_ENERGY`; les résidus relatifs de bilan
observés sont `1.84e-12` (TET4), `5.49e-09` (TET10), `8.64e-09` (HEX8) et
`8.91e-10` (HEX20). Aucune gate n'est fermée par cette seule observation.

La campagne de rollback adversarial ciblée a ensuite produit **5 passed in
20.98s** dans le lot multi-element. Le retry est reparti avec un déplacement
nul et un digest d'état identique avant/après rejet ; le résultat final diffère
de la référence à pas fixes de `1.25e-07` en déplacement relatif et
`3.35e-09` en PEEQ absolue. Ces valeurs sont archivées comme observation
interne, sans seuil de release ajouté.

La campagne `RobustnessQualificationCampaign` complète a ensuite été rejouée
dans `tmp/vnv_0_2_5_robustness_latest` : `PASS_INTERNAL`, avec
`PASS_INTERNAL_ENERGY` pour les quatre familles et `PASS_INTERNAL_ROLLBACK`.
Cette sortie temporaire n'est pas une preuve liée à un SHA de release.

Depuis cette exécution, la campagne complète temporaire reste `PASS_INTERNAL`
et inclut `PASS_INTERNAL_RESEARCH` pour le couplage borné TET4. Le lot ciblé
checkpoint/contact/couplage/défaillances/documentation a produit **66 passed,
2 skipped in 24.75s**; Ruff est vert sur les fichiers modifiés. La campagne
adversariale typée couvre désormais neuf cas de défaillance directe, plus les
retries contact et backend sparse. La génération engineering a été rejouée avec succès:
`706 artifacts, campaign=PASS`. Ces résultats restent des preuves de travail
et ne ferment aucune gate sans exécution sur un SHA final propre.

Le contrat de panne du backend sparse distingue désormais une factorisation
échouée (`LINEAR_SOLVER_FAILURE`) d'un tangent singulier (`SINGULAR_TANGENT`),
avec le message backend conservé dans les diagnostics. Le cas est couvert par
un test unitaire ciblé; il ne remplace pas une panne réelle d'un solveur
externe et ne ferme pas `025-G09` à lui seul.

Le benchmark de performance expose maintenant les chemins nommés
`load_control`, `arc_length`, `arc_length_finite_kinematic`, `contact` et
`coupled`; leurs profils historiques TET4 passent dans **7 tests** dédiés. Les
timers d'assemblage et de résolution sont aussi renseignés pour l'arc-length.
Un profil HEX20 isolé a ensuite confirmé un
hotspot de validation géométrique répétée : sur le même cas 96-DOF, le temps
total est passé de **114,288 s** à **17,321 s** et l'assemblage de **96,639 s**
à **11,573 s**, avec 22 itérations dans les deux runs. Cette comparaison reste
une caractérisation locale sur worktree sale; elle ne ferme pas 025-G08 et doit
être rejouée sur SHA propre avec comparaison numérique complète.

Une caractérisation load-control à deux répétitions par famille a ensuite été
archivée dans
`results/benchmark_0_2_5/nonlinear_load_control_all_families_repeats2_latest.json`.
Les huit runs TET4/TET10/HEX8/HEX20 convergent; les temps moyens sont
respectivement `0.607 s`, `2.318 s`, `1.028 s` et `16.453 s`, avec assemblage
moyen `0.392 s`, `1.648 s`, `0.747 s` et `11.160 s`. Les CV temporels sont
respectivement `2.46 %`, `0.19 %`, `2.31 %` et `0.16 %`; RSS avant/apres est
également enregistrée quand disponible. Le rapport est attaché à
`e368c0ce00874c16ff1e8fa9158ea0a8cd2dd745` sur un worktree sale : c'est une
mesure de caractérisation, pas une fermeture de `025-G08`.

Apres l'ajout du pipeline de readiness et du typage des erreurs d'assemblage,
le dernier lot cible a produit **59 passed, 2 skipped in 17.21s**. La generation
documentaire engineering reste a **706 artifacts, campaign=PASS**. Le lot TET10
quadrature/correlation a ensuite produit **30 passed in 21.31s**, puis la replay
Docker Code_Aster a produit **64 checks, PASS_EXTERNAL_CORRELATION**. Aucun test
de couverture ni aucune suite complete n'a ete lancee.

Le pipeline de readiness ciblé a ensuite été exécuté après les contrats HEX20,
contact et backend sparse : les étapes tests et documentation passent (**65
passed, 2 skipped**; **706 artifacts, campaign=PASS**), puis l'exécution s'arrête volontairement sur le
contrôle des gates. Les gates `025-G00`, `G01`, `G02`, `G03`, `G04`, `G05`,
`G06`, `G08`, `G09`, `G10`, `G11` et `G12` restent `OPEN`; le rapport est
`results/readiness_0_2_5/targeted_after_hex20.json`. Ce résultat ne lance ni
couverture ni suite complète et ne constitue pas une readiness de release.

Le readiness targeted final après les lots buckling haut ordre, failure contract
et profiling a produit **70 passed, 2 skipped in 34.73s** et
`706 artifacts, campaign=PASS`. Il s'est arrêté au contrôle des gates avec
`025-G00`, `G01`, `G02`, `G03`, `G04`, `G05`, `G06`, `G08`, `G09`, `G10`,
`G11` et `G12` toujours `OPEN`. Le rapport est
`results/readiness_0_2_5/targeted_after_failure_and_performance.json`; aucune
couverture, suite complète, tag, commit ou publication n'a été exécuté.

Le readiness targeted a ensuite été rejoué après l'intégration du benchmark
géométrique haut ordre : **70 passed, 2 skipped in 34.21s**, documentation
`PASS` avec `706 artifacts`, puis arrêt au gate check. Le rapport intermédiaire
est `results/readiness_0_2_5/targeted_after_high_order_geometry.json`.

Après l'intégration de la preuve Euler bornée : **70 passed, 2 skipped in
34.24s**, documentation `PASS` avec `706 artifacts`, puis arrêt au gate check.
Le rapport le plus récent est
`results/readiness_0_2_5/targeted_after_euler_buckling.json`.

Après l'ajout du rollback adversarial multi-étapes, le readiness ciblé a de
nouveau produit **70 passed, 2 skipped**, documentation `PASS` avec
`706 artifacts`, puis s'est arrêté au gate check. Le rapport final est
`results/readiness_0_2_5/targeted_after_euler_and_multistep_failure.json`;
les gates obligatoires restent `OPEN` et aucune couverture ni suite complète
n'a été relancée.

Depuis ce rapport, la campagne de robustesse a été régénérée avec trois preuves
supplémentaires : `VV-058` sensibilité maillage buckling coarse/medium sur les
quatre familles, `VV-059` couplage J2/geometrie connecté sur TET4/TET10/HEX8/
HEX20 et `VV-060` chemin FEM arc-length TET4 total-Lagrangian. La campagne reste
`PASS_INTERNAL`; les tests ciblés noyau/buckling/contact/arc-length ont produit
**40 passed in 58.37s**, les contrôles documentaires ciblés **11 passed**, Ruff
est vert et le générateur engineering reste à **706 artifacts, campaign=PASS**.
La corrélation Code_Aster multi-elements a également été rejouée dans Docker
avec **64 checks, PASS_EXTERNAL_CORRELATION**; elle reste une preuve candidate
du worktree courant tant qu'elle n'est pas rejouée et attachée à un SHA propre.
La couverture, la suite complète et la fermeture des gates n'ont pas été
déclarées par cette tranche.

Le profil composant `VV-061` a ensuite été rejoué sur les quatre familles en
load-control, une répétition par famille. Les quatre calculs convergent. Le
noyau élémentaire représente `0.205 s` (TET4), `0.918 s` (TET10), `0.626 s`
(HEX8) et `10.677 s` (HEX20), tandis que le solveur sparse représente
respectivement `0.058 s`, `0.066 s`, `0.045 s` et `0.065 s`. La mesure confirme
que le coût HEX20 est actuellement dominé par l'intégration/noyau élémentaire;
elle n'est ni un benchmark de scaling ni une fermeture de `025-G08`, car le
worktree est dirty et la répétabilité multi-run sur SHA propre reste requise.

La preuve `VV-062` a ensuite exécuté le chemin `total_lagrangian_j2` avec
recherche contact mise à jour sur TET4, TET10, HEX8 et HEX20. Chaque cas active
la plasticité J2, traverse un état ouvert puis actif avec la même composition
résidu/tangente et conserve un résidu relatif inférieur à `1e-7`; la pénétration
observée reste inférieure à `1e-4` dans ce montage de référence. Il s'agit d'une
preuve interne de composition multi-familles, sans revendication de contact
surface-à-surface, finite sliding, friction ou corrélation externe, et elle ne
ferme pas `G05` ou `G06`.

La preuve `VV-063` compare ensuite, sur les quatre familles, le déplacement du
chemin small-strain avec celui de `total_lagrangian_j2` à une charge `1e-4`.
Les écarts relatifs observés sont de l'ordre de `1e-15`, avec une déformation
plastique nulle dans les deux chemins. Cette cohérence de régime est une preuve
interne utile pour `G02`, mais ne remplace ni une corrélation externe ni une
qualification de grandes déformations plastiques.

La campagne adversariale structurée est désormais agrégée au paquet principal:
les cas `MAX_ITERATIONS`, tangente singulière, non-finis, élément/matériau
invalides, contact, minimum d'incrément, rollback contact, échec backend,
rollback multi-étapes, arc-length et buckling sont archivés sous
`summary.json`. Le statut courant est `PASS_INTERNAL_FAILURE_CONTRACT` : il
reste un contrat interne de défaillance, ne transforme aucun échec en
convergence et ne ferme pas `G09` avant l'attachement à un SHA propre et la
revue de gate.

Le chemin `VV-064` exerce maintenant le même driver sur une continuation
`total_lagrangian_j2` TET4/TET10/HEX8/HEX20 jusqu'à un facteur de charge signé
de `0,5`, avec adaptation du rayon explicitement activée et bornée à `0,1`.
Le résidu relatif maximal observé est inférieur à `1e-7`; la cible actuelle
reste élastique (`PEEQ = 0`), ce qui ne constitue donc pas une qualification de
la plasticité sous arc-length. Cette ouverture est strictement bornée : aucune
revendication de snap-through FEM, snap-back, post-buckling ou corrélation
externe n'est associée à ce résultat.

La preuve `VV-065` ferme un manque de routage identifié pendant l'audit : le
chemin public `geometric_nonlinear_static` compose désormais son assemblage
Total-Lagrangian élastique avec la contribution penalty sparse existante. Sur le
cas TET4 borné, le contact est actif, la pénétration reste sous `1e-3`, le
résidu relatif maximal reste sous `1e-7` et `det(F)` demeure positif. Cette
preuve ne transforme pas le contact en capacité surface-à-surface générale et
ne ferme pas `G05` ou `G06`.

## Decision de maturite

Les nouvelles capacites sont **experimental/research**. Elles ne doivent pas
modifier les revendications stables de 0.2.4 et ne ferment pas les gates 0.2.5.
Le prochain lot prioritaire est désormais la rejouabilité sur SHA propre des
profils et corrélations, puis la fermeture progressive des gates avant toute
claim de solide non linéaire unifié.

Depuis cette synthèse, le pipeline de readiness ciblé a été aligné avec les
tests des work packages constitutifs, géométriques, buckling, contact,
assemblage sparse, failure et performance. Le dernier run ciblé complet
archivé a produit `204 passed, 2 skipped` et un seul échec sur la synchronisation
de l'audit public (`1879` contre `1882` fichiers). La correction a été régénérée
par `scripts/audit_public_documents.py`, puis le test contrôlé ciblé a produit
`2 passed`; le run ciblé complet n'a pas été relancé. La génération documentaire
engineering rejouée ensuite a produit `706 artifacts, campaign=PASS` et l'audit
final reste à `1883 files, 0 findings`. Aucun test de couverture ni aucune suite
complète n'a été exécuté.

Le lot `VV-068` ajoute une preuve adversariale non injectée de contact : le
garde de pénétration rejette deux incréments (`CONTACT_PENETRATION_EXCESSIVE`),
effectue le rollback puis les cutbacks `1.0 -> 0.5` et `0.5 -> 0.25`, et
converge sur les facteurs committés `0.5`, `0.75`, `1.0`. Comparée à une
référence aux facteurs `0.125` à `1.0`, la différence relative de déplacement
est `1.19e-16`, la différence de réaction est nulle et le gap final est
identique. Cette preuve renforce le contrat `G09` mais reste interne, bornée à
un contact frictionless TET4 et ne ferme pas `025-G05` ou `025-G09`.

Le readiness ciblé historique après la campagne arc-length adaptative avait
produit **200 passed, 2 skipped en 169.46 s**, documentation `PASS` avec **706
artifacts**, puis arrêt au gate check. Il ne doit pas être lu comme un run
complet du HEAD après la correction d'audit. Dans cet état historique, les
gates `025-G00`, `G01`, `G02`, `G03`, `G04`, `G05`, `G06`, `G08`, `G09`, `G10`,
`G11` et `G12` étaient `OPEN`; la matrice contrôlée courante fait foi.
Aucune couverture ni suite complète n'a été exécutée dans ce run historique.

Le rapport `results/vnv_0_2_5/release_readiness_targeted_latest.json` reste le
rapport du run arrêté sur l'ancien échec d'audit; il ne doit pas être présenté
comme une readiness courante. Après le correctif, seuls l'audit contrôlé ciblé
et la génération documentaire ont été rejoués. Le SHA observé reste le HEAD
`e368c0ce` dans un worktree encore dirty; il ne constitue donc pas un SHA final
de release.

Après remplacement de l'accumulation globale des triplets par des chunks CSR,
le benchmark ciblé `results/benchmark_0_2_5/nonlinear_load_control_sparse_chunks_latest.json`
reste `PASS` sur TET4/TET10/HEX8/HEX20. Les compteurs de chunks et de pic
d'entrées sont exportés par étape et vérifiés par `test_nonlinear_benchmark`.
Cette optimisation est encore une observation de worktree sale et ne ferme pas
`025-G08`.

## Dernière vérification de packaging

Le build isolé wheel/sdist a produit des artefacts valides dans
`.tmp_release_readiness_025/`. `twine check` passe pour les deux fichiers et
un smoke install depuis le wheel passe dans `.tmp_smoke_install_025/` avec
`solveur.__version__ == 0.2.5a0`. Ces résultats décrivent une préparation
locale de candidat : ils ne constituent ni un tag, ni une publication PyPI,
ni une fermeture de gate tant que la campagne sur SHA propre n'est pas
terminée.

Les replays ciblés de caractérisation ont aussi été archivés sans modifier les
seuils : `geometric_static_all_families_latest.json` passe sur TET4, TET10,
HEX8 et HEX20 avec 18 itérations Newton; `contact_tet4_latest.json` et
`coupled_tet4_latest.json` passent respectivement en 18 et 24 itérations. Ces
trois rapports sont rattachés au SHA `e368c0ce` avec `worktree_dirty=true` et
restent des observations internes; ils ne ferment pas G02, G05, G06 ou G08.

## Vérification ciblée la plus récente

Après la sérialisation explicite du mode de projection finite-sliding et le
contrôle pré-assemblage de `contact_max_penetration`, le run ciblé final a
produit **182 passed en 157,02 s**, sans couverture. Ruff est vert sur les
fichiers modifiés, `git diff --check` ne signale aucune erreur de contenu, et
le benchmark finite-sliding exporte le mode
`bounded_closest_point_node_to_triangle`. La documentation ciblée a produit
**44 passed, 6 skipped**; l'audit public reste à **1883 fichiers, 0 finding**.
Ces résultats restent liés à un worktree dirty et ne ferment aucune gate de
release.

Les contrôles rapides rejoués ensuite ont produit **4 passed** pour le contrat
du pipeline de readiness et **34 passed** pour les tests ciblés contact,
finite-sliding et benchmark. Le profil `targeted` du pipeline répond
`PLANNED`, ce qui vérifie sa construction sans lancer la couverture ni la
campagne complète. Les avertissements Git observés concernent uniquement la
normalisation LF/CRLF de fichiers déjà modifiés; `git diff --check` ne signale
aucune erreur de contenu.

Depuis cette vérification, la campagne `tests/unit/test_nonlinear_multielement.py`
a produit **27 passed en 135,67 s** après l'ajout du raffinement généralisé
sparse. `tests/unit/test_linear_buckling.py` produit **10 passed** et
`tests/unit/test_nonlinear_load_path.py tests/unit/test_nonlinear_checkpoint.py`
produisent **32 passed**. Le buckling interne sélectionne `generalized_eigsh`
sur TET4 et `generalized_eigs_shift_invert` sur les tangentes indéfinies
TET10/HEX8/HEX20, avec un résidu de mode inférieur à `1e-14` sur le replay
quatre familles; le fallback bracketé reste diagnostiqué si ARPACK refuse la
paire. Le test documentaire courant produit **42 passed, 6 skipped** et
l'audit public reste à **1883 fichiers, 0 finding**. Aucun test de couverture
ni aucune suite complète n'a été exécuté; les gates 025-G03, 025-G04 et
025-G09 restent donc ouvertes.

Le benchmark `VV-061` conserve désormais, pour chaque famille et chaque phase
instrumentée, les médianes en plus des moyennes, ainsi que les bornes min/max et
l'écart-type des temps mur répétés. Cette information rend les comparaisons
avant/après moins sensibles à un échantillon isolé; elle reste descriptive,
doit être rejouée sur un SHA propre et ne constitue pas un seuil de performance.

La preuve locale `VV-018` a également été renforcée par
`run_contact_tangent_fd_benchmark`: le contact penalty frictionless à actif
figé reste à gap `-0.1`, sa tangente sparse contient `16` coefficients non nuls,
et l'erreur relative maximale observée sur les pas FD `1e-4`, `1e-6`, `1e-8`
est `6.00e-09`. Ce résultat couvre le voisinage lisse d'un état actif; il ne
couvre ni le kink ouverture/fermeture, ni le finite sliding généralisé, ni une
corrélation externe, et ne ferme pas `025-G05`.

La campagne canonique `VNV-ROBUSTNESS-NONLINEAR-SOLIDS-025` a ensuite été
rejouée après correction du scénario adversarial de buckling : **statut
`PASS_INTERNAL`**, avec `contact_tangent_fd_benchmark =
PASS_INTERNAL_RESEARCH` et `failure_campaign =
PASS_INTERNAL_FAILURE_CONTRACT`. Le passage ciblé associé couvre **76 tests
passés**; il ne lance ni couverture ni suite complète. Les gates restent
volontairement `OPEN`, car ces preuves proviennent encore d'un worktree dirty
et doivent être régénérées sur le SHA candidat avant toute clôture.

## Etat courant apres release hardening — 2026-08-26

Les observations historiques ci-dessus sont supersedees par la qualification
de release hardening suivante. Le candidat source est la révision indiquée par
`source_sha` dans le manifeste généré; le calcul de propreté source est `PASS`
et aucune modification source ne subsiste. Les sorties générées après
checkout sont des preuves dérivées et sont exclues de ce calcul conformément
au contrat `source_sha`.

- `qf_solver.py verify-all --profile engineering` termine en `PASS` sur le
  candidat : 1 636 tests sélectionnés (`1 622 passed`, `14 skipped`),
  187 désélections prévues, sans échec.
- La campagne de couverture finale disponible mesure **88,36 %** avec la
  politique `--cov-fail-under=80`. Elle a signalé uniquement un décalage du
  compteur de l'audit public; l'audit a été régénéré à **1 901 fichiers, 0
  finding** et les tests affectés ont ensuite produit **2 passed**. Les
  derniers changements de code sont dans `solveur.verification`, explicitement
  omis du périmètre coverage, et ne modifient donc pas ce résultat mesuré.
- La documentation engineering a été générée depuis ce SHA exact : **706
  artefacts**, campagne `PASS`; `docs/generated/docs_manifest.json` porte un
  `source_sha` égal au HEAD au moment de la génération.
- Le build isolé a produit `qf_solver-0.2.5a0-py3-none-any.whl` et
  `qf_solver-0.2.5a0.tar.gz`; `twine check`, l'installation fraîche de la
  wheel, les imports publics et l'aide CLI sont passants.
- Ruff, le contrôle mypy progressif CI et `compileall` sont passants. Le
  contrôle mypy exhaustif de tout `src/solveur` reste une dette historique
  hors commande CI et ne constitue pas une nouvelle régression de ce candidat.
- Les preuves Code_Aster J2 bornées et les campagnes internes restent
  disponibles. Les corrélations CalculiX partielles, les profils répétés et
  les capacités avancées non entièrement qualifiées restent documentés comme
  limites; elles ne sont pas promues par ce hardening.

Depuis cette synthèse, `025-G03` a été clôturée en périmètre borné après
correction de la rigidité géométrique initial-stress et rattachement de la
preuve Euler quatre niveaux et de la sonde Code_Aster TET4 au SHA propre
`85c75d06955976251dd54ad782f57f1eb5a7f8f4`. Les limites TET10/HEX8/HEX20
externes, post-buckling et imperfections restent explicitement hors scope.
Les autres gates conservent les statuts indiqués dans la matrice contrôlée;
`025-G07` reste `NOT_IN_RELEASE_SCOPE`. Aucun tag, push GitHub ou upload PyPI
n'a été exécuté.

## G05 controlled closure update

The historical WP5 implementation observations above describe the pre-closure
state and remain intentionally conservative. The current controlled replay is
recorded in `results/vnv_0_2_5/g05_latest/` with source SHA
`a3ab8de707ffc88fc5e39e4f999eb872c9223b73` and `dirty=false`. It reports
`82 passed / 2 skipped` in the contact-focused unit selection, a bounded
penalty sweep from `1e2` to `1e6`, and PASS internal observations for updated
normals, three-facet traversal, recontact and facet-transition rollback.
Code_Aster additional-contact histories pass for the 768- and 9,984-element
TET4 confirmations. Accordingly `025-G05` and WP5 are now
`CLOSED_BOUNDED` / `PASS` only for the explicit node/patch-to-triangulated-
surface frictionless contract. This update does not qualify general
surface-to-surface contact or close G06, G10, G11 or G12.
