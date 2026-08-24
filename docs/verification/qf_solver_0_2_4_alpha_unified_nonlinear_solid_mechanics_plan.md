---
doc_id: DOC-NL-024-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.4a0
reviewer: ""
approver: ""
---

# Plan 0.2.4 alpha - Unified Nonlinear Solid Mechanics

## Statut et regle de travail

Ce document conserve le plan d'architecture et de verification initial de
`0.2.4a0`. Il ne constitue pas, a lui seul, une promotion de maturite ni une
decision de release. L'implementation incrementale a ensuite ete autorisee par
la decision Owner explicite `accepted_with_recommendations`; son etat courant
est trace en sections 14 et 15.8. La source de verite des gates est
`qualification/reviews/qf_solver_0_2_4a0_gate_status.json`.

La cible est une infrastructure commune de mecanique non lineaire des solides
a petites deformations. Elle doit separer la cinematique elementaire, la loi
constitutive, l'etat materiau et l'algorithme global de Newton, sans degrader
les chemins lineaires qualifies par `0.2.3a0`.

## 1. Executive summary

Les constats et le perimetre recommandes dans les sections 1 a 13 sont le
snapshot de planification ayant precede l'implementation. Le scope actuellement
accepte est le J2 small-strain experimental borne sur TET4, TET10, HEX8 et
HEX20, avec Full Newton comme unique chemin qualifie. Il est documente dans la
revue Owner et ne transforme pas les limites multi-elements, cycliques ou de
validation physique en capacites qualifiees.

L'audit confirme que QF Solver dispose deja d'un chemin non lineaire material
commun: `AnalysisRouter` selectionne `NonlinearStaticSolver`, qui assemble un
residu et une tangente sparse, appelle le solveur lineaire commun, puis
commet les etats J2 lorsque l'increment converge. Des controles de cutback,
line search, checkpoint et restauration existent egalement.

Le noyau reste cependant couple par convention: chaque element TET4, TET10,
HEX8 et HEX20 decide lui-meme comment appeler `stress_tangent_state`; les
etats sont des dictionnaires copies en profondeur et ne possedent pas de
contrat explicite trial/committed. La convergence ne publie pas encore une
taxonomie stable de causes d'echec. Le chemin Total Lagrangian TET4 et le
solveur de contact sont des chemins distincts qui ne doivent pas etre fusionnes
dans cette release.

Le MUST recommande pour `0.2.4a0` est J2 petites deformations a ecrouissage
isotrope, avec TET4 et TET10 comme elements de reference, Newton complet,
etat transactionnel, cutback/retry et diagnostics par increment. HEX20 est un
SHOULD: son J2 est deja borne en interne mais sans correlation J2 externe.
HEX8 reste hors scope promu de mecanique non lineaire tant qu'une campagne
structurale dediee n'a pas fourni de preuves explicites. Tous les gates
proposes restent ouverts jusqu'a une revue Owner et a des preuves attachees au
SHA final.

## 2. Audit de l'etat actuel

### 2.1 Chaine effectivement executee

```text
FiniteElementModel.analysis.type = nonlinear_static
  -> AnalysisRouter.solve()
  -> NonlinearStaticSolver.solve()
  -> GlobalAssembler (charges, DDL imposes) + DofManager
  -> _assemble_internal_tangent()
  -> ElementRegistry + MaterialFactory par element
  -> element.internal_force_tangent_state(...)
  -> material.stress_tangent_state(strain, previous_state)
  -> CSR tangent globale + residu externe - interne
  -> LinearSystemSolver / solver_backend
  -> Newton, line search ou cutback
  -> commit_material_states() ou abandon du trial
  -> SolveResult, post-traitement et audit
```

| Composant | Fichier / symbole | Responsabilite observee | Maturite / preuves existantes | Dette utile a traiter |
| --- | --- | --- | --- | --- |
| Dispatch | `src/solveur/core/router.py`, `AnalysisRouter.solve` | Selectionne lineaire, modal, non lineaire materiau, TL et dynamique. | Teste par API/CLI. | Les deux chemins non lineaires n'ont pas le meme contrat. |
| Driver J2 | `src/solveur/core/nonlinear.py`, `NonlinearStaticSolver` | Newton, modified Newton, line search, arc-length, load path, adaptive stepping. | J2 interne, tests de chemin/rollback/checkpoint. | Options disperses dans `analysis.parameters`; diagnostics d'echec non structures. |
| Assemblage | `NonlinearStaticSolver._assemble_internal_tangent` | Construit force interne et CSR tangent. | Sparse sur le chemin Newton standard. | Recreation material/element a chaque evaluation; convention `hasattr`. |
| Etat | `src/solveur/core/material_state.py` | Table par element et point de Gauss, copie profonde, commit, serialisation. | Rollback par rejet de copie; checkpoint teste. | Pas de type trial/committed explicite ni transaction atomique exposee. |
| Controles | `src/solveur/core/nonlinear_controls.py` | `NonlinearStep`, increment adaptatif, travail incremental. | Tests de validation et sensibilite d'increments. | Pas de rapport de non-convergence normalise. |
| Loi J2 | `src/solveur/materials/solid.py`, `VonMisesElastoplasticMaterial` | Return mapping von Mises, ecrouissage isotrope, plastic strain, tangente algorithmique. | Campagne material `PASS_INTERNAL`; anomalie historique ANOM-0002 declaree resolue. | Le contrat utilise deformation totale et dictionnaires; FD de tangente doit etre requalifie comme gate dedie. |
| Elements solides | `tet4.py`, `tet10.py`, `hex8.py`, `hex20.py` | B, integration, force interne et tangente locale. | TET4/TET10 J2 bornes; HEX8/HEX20 J2 disponibles au contrat local mais non promus faute de V&V structurale/externe dediee. | Boucles constitutives dupliquees dans chaque element. |
| Backend lineaire | `src/solveur/core/linear_methods.py`, `solver_backend.py` | Resolution de la linearisation globale. | Backends SciPy/PETSc existants. | Le contrat non lineaire ne publie pas encore tous les diagnostics backend. |
| TL TET4 | `core/geometric_nonlinear.py`, `elements/solid/tet4_total_lagrangian.py` | Saint-Venant-Kirchhoff, configuration de reference. | Scope research borne, preuves propres. | Chemin specifique TET4; ne pas fusionner avec J2 small-strain. |
| Contact | `src/solveur/contact/solver.py` | Active set et friction regularisee. | Scope borne distinct. | Contrat d'etat et convergence distinct, hors chantier. |

### 2.2 Capacites et elements

| Element | Elastique lineaire | J2 actuel | Tangente / etat | V&V non lineaire actuel | Candidat 0.2.4 |
| --- | --- | --- | --- | --- | --- |
| TET4 | `accepted_for_release_0_2_3` | `owner_accepted_experimental_bounded_use` | 1 point de Gauss, etat J2 par dictionnaire | Material path, cyclic structural interne, sensibilite d'increments, correlations existantes bornees | MUST |
| TET10 | `accepted_for_release_0_2_3` | `owner_accepted_experimental_bounded_use` | 4 points J2, meme convention | Correlation J2 monotone bornee; geometries/cycles complexes exclus | MUST |
| HEX8 | `accepted_for_release_0_2_3` | Contrat local J2 disponible, non promu | Interface element presente, sans scope structural declare | Aucun gate J2 de release | COULD, uniquement apres decision et V&V dediee |
| HEX20 | `accepted_for_release_0_2_3` | `owner_accepted_experimental_bounded_use` | 27 points J2, etats commites testes | Preuve J2 interne seulement; J2 externe, grandes deformations et contact exclus | SHOULD |

### 2.3 Preuves et limites deja connues

- La campagne de materiau J2 est `PASS_INTERNAL`, couvre elasticite,
  declenchement, chargement/dechargement/rechargement et ne fabrique aucune
  correlation Abaqus absente.
- La campagne de methodes caracterise Newton complet et Newton avec line
  search comme convergents; `modified_newton` y est `NON_CONVERGED`.
- La sensibilite d'increments J2 est documentee sur 12, 24 et 48 increments.
- Les tests de `load_path` injectent un rejet et verifient que l'essai suivant
  repart du deplacement et de l'etat committes.
- `ANOM-0002` affirme qu'une tangente J2 precedemment incoherente a ete
  remplacee par une tangente radiale directionnelle, avec erreur FD inferieure
  a `1e-6`. Cette assertion historique doit devenir une preuve reproductible
  explicite de `NL-G02`, pas une hypothese de release.
- La correction arc-length actuelle densifie la tangente via `toarray()` et
  appelle `numpy.linalg.solve`. Elle est incompatible avec un objectif sparse
  general et reste hors MUST de `0.2.4a0`.

### 2.4 Tests actuellement associes au chemin non lineaire

| Domaine | Tests / campagne actuelle | Ce que la preuve etablit | Ce qu'elle n'etablit pas |
| --- | --- | --- | --- |
| Etats et increments | `tests/unit/test_nonlinear_load_path.py`, `tests/unit/test_nonlinear_checkpoint.py` | Chemin signe, rejet injecte, reprise et incompatibilites connues. | Contrat transactionnel type et causes d'echec normalisees. |
| Loi locale J2 | `tests/verification/test_j2_material_vnv.py`, `src/solveur/verification/j2_material.py` | Chemins materiau internes et absence honnete de reference Abaqus. | Validation physique generale ou correlation externe complete. |
| Methodes Newton | `tests/verification/test_j2_methods_vnv.py`, `src/solveur/verification/j2_methods.py` | Newton complet/line search convergent sur le cas caracterise; modified Newton non convergent. | Robustesse universelle ou choix automatique de methode. |
| Sensibilite de pas | `tests/verification/test_j2_step_sensitivity_vnv.py` | Stabilite observee sur 12/24/48 increments. | Independance absolue au pas ou aux maillages. |
| TET4/TET10 structures | `tests/verification/test_j2_structural_vnv.py`, `test_tet10_j2_structural_vnv.py` | Scope J2 borne des tetraedres. | HEX8/HEX20 J2 externe ou chargements complexes generalises. |
| HEX20 J2 | `tests/integration/test_hex20_workflow.py`, `tests/unit/test_hex20_campaign.py` | Newton, etats commites et 27 points locaux. | Correlation J2 externe. |

## 3. Couplages et gap analysis

### Couplages acceptables a conserver

| Couplage | Motif |
| --- | --- |
| Element -> cinematique, B, quadrature et integration de force/tangente | Responsabilite FEM locale naturelle. |
| Material model -> etat de son point de Gauss | Une loi doit definir ses variables internes. |
| Driver global -> LinearSystemSolver | La resolution lineaire appartient a Newton global. |
| Router -> drivers distincts material small-strain, TL et contact | Les hypotheses physiques et les maturites sont differentes. |

### Couplages a eliminer ou encadrer

| Couplage actuel | Risque | Cible 0.2.4 |
| --- | --- | --- |
| Chaque element detecte `hasattr(stress_tangent_state)` et appelle directement J2. | Duplication, contrat implicite, extension fragile. | Un protocole constitutif unique retourne une reponse typpee. |
| `MaterialStateTable` est une table de `dict` copies ad hoc. | Corruption difficile a diagnostiquer; cout memoire opaque. | Session transactionnelle avec state commis et trial separes. |
| `NonlinearStaticSolver` cree material et element a chaque assemblage. | Cout et dependances cachees. | Fabrique/cache de runtime explicite, invalide seulement au changement de modele. |
| Les epreuves de convergence et les erreurs sont des chaines de texte. | Impossible de distinguer iteration, solveur lineaire, NaN ou increment minimal. | Enum de causes et rapport d'increment structure. |
| Arc-length convertit une tangente CSR en dense. | Explosion memoire et rupture de la politique sparse. | Hors MUST; future formulation creuse distincte avant promotion. |

## 4. Architecture cible proposee

La cible est evolutive et doit etre introduite par adaptateurs retrocompatibles,
sans big-bang ni modification des formulations lineaires.

```text
Element kinematics (B, quadrature, u)
  -> ConstitutiveModel.evaluate(total_strain, committed_state, context)
  -> ConstitutiveResponse(stress, algorithmic_tangent, trial_state, diagnostics)
  -> NonlinearElementResponse(f_internal, K_tangent, point_trials)
  -> NonlinearAssemblyResult(residual, CSR tangent, trial_states, diagnostics)
  -> NonlinearSolver.solve_increment()
  -> IncrementController (commit | rollback | cutback | retry)
  -> NonlinearResult + IncrementReport[]
```

| Contrat cible | Responsabilite | Regle de compatibilite |
| --- | --- | --- |
| `ConstitutiveModel` | Evaluation locale sans connaitre l'element ou le solveur global. | Conserver d'abord la semantique deformation totale de J2; toute API incrementale doit etre explicitement decidee. |
| `ConstitutiveResponse` | Contrainte, tangente algorithmique, trial state et diagnostics locaux. | Aucun etat commis ne doit etre mute pendant `evaluate`. |
| `MaterialStateSession` | Initialiser, produire les vues trial, commit ou rollback. | Le resultat d'un increment echoue est inobservable dans l'etat commis. |
| `NonlinearElement` | Integrer les reponses de Gauss en force interne/tangente locale. | Ne connait ni J2 en particulier ni le backend lineaire. |
| `NonlinearAssembly` | Retourner CSR, force, essais et statistiques. | Pas de `toarray()` dans le chemin Newton standard. |
| `NonlinearSolver` | Newton, criteres, line search, echec et rapports. | Le solveur lineaire n'est appele qu'ici. |
| `IncrementController` | Politique de pas, cutback, retry et arret. | Options centralisees, serialisables et checkpointables. |

`SolveResult` peut rester l'enveloppe publique existante. Une extension
retrocompatible doit ajouter un `nonlinear` structure contenant les rapports
par increment plutot que de modifier silencieusement les champs actuels.

## 5. Perimetre recommande au demarrage (historique)

### MUST - condition de candidature 0.2.4a0

1. J2 petites deformations isotrope avec ecrouissage actuellement supporte,
   reemballe dans le contrat constitutif commun sans changement de resultat.
2. Etat material trial/committed, commit atomique et rollback exact.
3. TET4 et TET10 dans le contrat commun, avec leurs nombres de points de
   Gauss et leurs limitations actuelles explicitement conserves.
4. Newton complet comme reference, criteres residu et correction explicitement
   rapportes, detection NaN/Inf/singularite/solveur lineaire.
5. Cutback/retry adaptatif configure centralement et checkpoint compatible ou
   explicitement refuse avec cause structuree.
6. Pyramide V&V, correlations externes reproductibles dans le sous-scope
   existant, et gate `NR-0.2.3` vert.

### SHOULD - seulement si les gates MUST sont deja verts

- Migration de HEX20 vers le contrat commun et V&V elementaire J2/FD; sa
  promotion reste conditionnee a des preuves externes J2 supplementaires.
- Mode line search `off | auto | on`, retenu uniquement si les cas difficiles
  montrent un benefice mesure sans masquer un tangent incorrect.
- Diagnostics de cout: temps constitutif, temps assemblage, nombre de points,
  memoire estimee des etats.

### COULD - reporter sans penaliser le MUST

- HEX8 J2, apres une campagne structurale complete et une decision de promotion.
- Tangente arc-length strictement sparse, continuation avancee et branch
  switching.
- Kinematic hardening, viscoplasticite, dommage et autres lois.
- Integration du contact ou du Total Lagrangian dans une abstraction future.

## 6. Requirements matrix

| Requirement planifie | Metrique / critere | Implementation future | Verification | Gate |
| --- | --- | --- | --- | --- |
| NL-REQ-01 Separation constitutive | Aucun element ne reference J2 nommement. | Contrat constitutif et adaptateur. | Test d'architecture. | NL-G01, NL-G03 |
| NL-REQ-02 Etat transactionnel | Rollback bitwise/structurellement identique. | Session d'etat. | Echec injecte. | NL-G05 |
| NL-REQ-03 J2 elastique/plastique | Reponse analytique et hydrostatique correcte. | J2 de reference. | Niveau 0. | NL-G02 |
| NL-REQ-04 Tangente algorithmique | FD directionnelle dans regimes elastique/plastique. | Reponse constitutive. | Etude pas de perturbation. | NL-G02 |
| NL-REQ-05 Force/tangente element | `f_int` et `df_int/du` coherents. | Contrat element. | Niveau 1. | NL-G03 |
| NL-REQ-06 Newton explicable | Residu, correction, iterations et cause disponibles. | Driver/resultat. | Niveau 2. | NL-G04 |
| NL-REQ-07 Pas robuste | Cutback/retry/min increment determines. | Controles centralises. | Increment difficile. | NL-G06 |
| NL-REQ-08 Pas de contamination lineaire | Resultats 0.2.3 non alteres. | Router/adaptateurs. | Suite NR. | NL-G11 |
| NL-REQ-09 Correlation externe | Courbes et champs comparables. | Scripts V&V. | Code_Aster/CalculiX. | NL-G08 |
| NL-REQ-10 Evidence rejouable | SHA, environnement, seuils et artefacts lies. | Manifestes/documents. | Audit evidence. | NL-G12 |

Les seuils nouveaux ne seront pas fixes arbitrairement. Les seuils deja
archives dans `qualification/benchmarks.json` restent applicables. Les seuils
FD, convergence par correction, energie et correlations nouvelles seront
proposes apres une campagne de conditionnement puis approuves par l'Owner
avant de devenir des criteres Reject.

### 6.1 Table d'acceptation a completer avant Phase B

| Requirement | Metrique | Target | Warning | Reject | Justification attendue |
| --- | --- | --- | --- | --- | --- |
| Constitutive analytic | Erreur contrainte / ep sur chemin connu | Seuil existant si applicable. | A definir apres baseline. | A definir apres baseline. | Convention Voigt, conditionnement, reference. |
| Tangente FD | Erreur directionnelle `C_alg` vs FD | Plage stable observee. | Sensibilite au pas. | Erreur hors plage justifiee. | Sweep de perturbation et regimes elastique/plastique. |
| Newton | Residu relatif et correction relative | Tolerance configuree satisfaite. | Stagnation detectee. | Max iterations / NaN / singularite. | Echelle de force et deplacement. |
| Correlation externe | Courbe force-deplacement, reactions, stress, ep | Seuil specifique au benchmark. | Ecart local explique. | Ecart global hors seuil. | Meme mesh, BC, increment et post-traitement. |
| Sensibilite | Variation maillage/pas de charge | Convergence documentee. | Variation non monotone. | Extrapolation non justifiee. | Etude a trois niveaux au minimum lorsque pertinente. |
| Energie | Imbalance si une energie est definie | Seuil issu du cas. | Mesure informative. | Incoherence non expliquee. | Hypotheses de charge et de materiau. |

## 6.2 Taxonomie de failure modes proposee

La forme publique finale devra reutiliser `SolverError` lorsque cela reste
retrocompatible, mais aussi exposer une cause machine-readable dans chaque
rapport d'increment. Les categories candidates sont:

| Code | Sens | Action de l'increment controller |
| --- | --- | --- |
| `MAX_ITERATIONS` | Les criteres n'ont pas ete satisfaits a temps. | Cutback ou echec final. |
| `MIN_INCREMENT_REACHED` | Un retry demanderait un pas inferieur au minimum. | Arret non silencieux. |
| `LINEAR_SOLVER_FAILURE` | La linearisation n'a pas ete resolue par le backend. | Cutback si admissible, sinon echec. |
| `SINGULAR_TANGENT` | Tangente non inversible ou conditionnement rejete. | Echec trace; jamais de dernier vecteur masque. |
| `NAN_DETECTED` | Etat, residu ou correction non fini. | Rollback immediat et echec trace. |
| `MATERIAL_UPDATE_FAILURE` | Return mapping ou etat local invalide. | Rollback et diagnostic element/point. |
| `INVALID_ELEMENT` | Geometrie, integration ou B invalide. | Erreur d'entree, sans retry numerique. |
| `STATE_CORRUPTION` | Invariant trial/committed rompu. | Echec bloquant et preservation du dernier commit. |
| `LINE_SEARCH_FAILURE` | Aucune reduction ne satisfait la regle retenue. | Cutback seulement si policy autorisee. |

## 7. V&V matrix

| Niveau | Cas a preparer | Observables obligatoires | Statut initial |
| --- | --- | --- | --- |
| V0 Constitutive | Elastic, yield onset, traction uniaxiale, unload/reload, cisaillement pur, hydrostatique, multi-increment, rollback, FD tangent. | Stress, plastic strain, equivalent plastic strain, yield function, tangent error. | PASS_INTERNAL_INITIAL; paquet `qualification/vnv/j2_unified_nonlinear_024/reference/v0_material/`. |
| V1 Element | Patch elastique, etat plastique homogene, deformation constante, element distordu, integration points, `f_int` et K par FD. | Force, energie si applicable, tangent locale, etats Gauss. | PASS_INTERNAL_INITIAL pour TET4/TET10; contrat local HEX8/HEX20 couvert par tests, sans promotion structurale. |
| V2 Global | Mono-element, barre multi-elements, flexion, load/unload, increment echoue, cutback, tolerance/load-step/mesh sensitivity. | Historiques residu, DDL, reactions, plasticite, pas/retries. | PASS_INTERNAL_INITIAL pour sensibilite 12/24/48, maillage TET4 `h=0.36/0.24/0.18` et caracterisation Newton; rollback/cutback testes. |
| V3 Reference | Barre J2 analytique, cas interpretable de plastification progressive, benchmark publie si retenu. | Courbe force-deplacement, onset, energie si definie. | PASS_INTERNAL_INITIAL sur la reference analytique bilineaire; aucune validation physique revendiquee. |
| V4 Correlation | Meme modele Code_Aster / CalculiX; Abaqus seulement si disponible. | Courbes, reactions, contraintes, ep, champ plastique et seuil. | PASS_EXTERNAL_CORRELATION pour TET10/Code_Aster et PASS_INTERNAL pour le point materiau/C3D8 CalculiX; aucune qualification HEX8/HEX20 J2 externe. |

### Verification de tangente algorithmique

La verification comparera des directions de deformation normalisees a la
derivee numerique de la contrainte autour d'etats elastique, au seuil et
plastiques. Une etude de sensibilite au pas de perturbation etablira la plage
ou les erreurs de troncature et d'arrondi ne dominent pas. La tolerance finale
sera derivee de cette etude, des conventions Voigt et des niveaux existants
plutot que choisie pour faire passer le test.

## 8. Benchmarks et performance

| Benchmark | Taille cible | Mesures | Objectif |
| --- | --- | --- | --- |
| Material point J2 | 1 point | evaluations, tangent FD, allocation et etat | Isoler la loi. |
| Barre TET4/TET10 | Petite a moyenne | Newton iterations, assembly, solve lineaire, etats | Reference de convergence. |
| Flexion multi-elements | Moyenne | Pas, cutbacks, residus, plastic zone | Robustesse globale. |
| HEX20 SHOULD | Petite a moyenne | Cout par 27 points, memoire etats, preuves locales | Evaluer cout sans revendiquer HPC. |

Les benchmarks ne seront pas des tests CI longs. La CI conservera des cas
deterministes courts; les profils de temps/memoire iront dans une campagne
separee. La release ne revendiquera pas une capacite HPC ou multi-million de
DDL du fait de cette tranche.

## 9. Hors scope explicite

- Nouveaux elements, WEDGE, PYRAMID et nouvelle physique.
- Contact generalise et couplage contact-plasticite.
- Hyperelasticite, dommage, fracture, creep, viscoplasticite et thermo-plasticite.
- Grandes transformations generalisees: Total Lagrangian TET4 reste une
  famille distincte en research, soumise a sa propre feuille de route.
- Non lineaire explicite, nouvelle GUI et refonte HPC/PETSc.
- Promotion automatique d'un element ou d'une correlation externe.

## 10. Phasage d'implementation initial (historique)

| Phase | Dependances | Livrable et condition de passage |
| --- | --- | --- |
| A Audit and requirements | Revue Owner de ce plan. | Decisions de scope, contrat et seuils de travail. |
| B Constitutive core | A. | J2, etat, tangent FD et V0 verts (`NL-G02`). |
| C Element nonlinear contract | B. | TET4/TET10 force/tangente/etats V1 verts (`NL-G03`). |
| D Global Newton driver | C. | Diagnostics et convergence V2 verts (`NL-G04`). |
| E Increment management | D. | Commit/rollback/cutback/retry verts (`NL-G05`, `NL-G06`). |
| F Robustness | E. | Line search seulement si mesuree utile; taxonomie des echecs. |
| G External correlation | F. | Cas externes reproductibles et limites ecrites (`NL-G07` a `NL-G09`). |
| H Full non-regression | G. | `NR-0.2.3` et controle performance verts (`NL-G10`, `NL-G11`). |
| I Evidence and Owner review | H. | SHA final, docs et decision Owner (`NL-G12`, `NL-G13`). |

## 11. Impact de fichiers estime au demarrage

Cette liste est prospective; aucun de ces fichiers n'est modifie par le plan.

| Zone | Fichiers probablement concernes | Nature future |
| --- | --- | --- |
| Driver / resultats | `core/nonlinear.py`, `nonlinear_controls.py`, `results.py`, `errors.py` | Contrats, diagnostics, causes d'echec. |
| Etats | `core/material_state.py`, `core/nonlinear_checkpoint.py`, `io/nonlinear_checkpoint.py` | Transaction, serialisation et reprise. |
| Materiaux | `materials/solid.py`, `materials/factory.py` | Reponse constitutive J2 et adaptateur. |
| Elements MUST | `elements/solid/tet4.py`, `tet10.py`, `elements/registry.py` | Integration par contrat commun. |
| Elements SHOULD/COULD | `hex20.py`, `hex8.py` | Seulement apres gate de scope. |
| API / dispatch | `api/public.py`, `core/router.py`, schemas associes | Options compatibles et exposition diagnostics. |
| V&V | tests unitaires/integration/verification et `docs/verification/*` | Matrices, artefacts et gates. |

## 12. Definition of Done proposee au demarrage

`0.2.4a0` pourra etre candidate seulement si QF Solver possede un noyau commun
de mecanique non lineaire des solides pour le MUST approuve: J2 verifiee
independamment, tangente algorithmique verifiee par FD, etats trial/committed
transactionnels, Newton et incrementation tracables, correlations bornes et
non-regression 0.2.3 verte. Le statut devra rester borne aux elements, cas,
maillages et references effectivement demontres.

## 13. Decisions Owner initialement ouvertes (historique)

Ces questions ont servi a cadrer l'implementation. Elles ne sont plus des
conditions en attente pour le scope experimental accepte; la decision et les
limitations courantes sont portees par `DOC-NL-024-002` et le registre des
gates.

1. Approuver le MUST recommande `TET4 + TET10`, avec HEX20 en SHOULD et HEX8
   hors perimetre promu tant qu'une campagne structurale dediee n'est pas
   disponible; son contrat local reste toutefois teste.
2. Confirmer que le contrat constitutif initial conserve une entree en
   deformation totale pour compatibilite, avant toute evolution incrementale.
3. Confirmer que `modified_newton` reste caracterise mais non promu par defaut.
4. Confirmer que l'arc-length dense, Total Lagrangian et contact restent hors
   scope de cette tranche.
5. Decider si la line search doit etre `off` par defaut et activee seulement
   apres preuve de robustesse mesurable.
6. Approuver la methode de fixation des seuils nouveaux apres baseline, et non
   avant l'etude de conditionnement.
7. Confirmer les solveurs externes disponibles et autorises pour les futures
   correlations (Code_Aster, CalculiX, Abaqus eventuel).

## 14. Journal d'implementation 0.2.4a0

Ce journal ne ferme pas, a lui seul, les gates de release. Il distingue les
tranches implementees des preuves restantes; RQ-G08 est toutefois fermee dans
son scope externe borne, conformement au registre des gates.

| Tranche | Etat | Fichiers principaux | Verification |
| --- | --- | --- | --- |
| Contrat constitutif | PARTIAL_DONE | `src/solveur/core/nonlinear_contracts.py`, `materials/solid.py` | Reponse typee pour materiaux lineaire, non lineaire et J2; compatibilite legacy conservee. |
| Etat trial/committed | PARTIAL_DONE | `src/solveur/core/material_state.py`, `core/nonlinear.py` | Session commit/rollback ajoutee aux chemins adaptive et arc-length; tests transactionnels. |
| Contrat elementaire | PARTIAL_DONE | `elements/solid/tet4.py`, `tet10.py`, `hex8.py`, `hex20.py` | Les quatre elements utilisent l'adaptateur constitutif commun; aucune qualification HEX8 J2 ajoutee. |
| Diagnostics Newton | PARTIAL_DONE | `core/nonlinear.py`, `core/nonlinear_controls.py`, `core/errors.py` | Residu initial, final et historique des residus par increment; causes machine-readable pour les echecs principaux. |
| Telemetrie des cutbacks | PARTIAL_DONE | `core/nonlinear.py` | Le journal des increments rejetes conserve maintenant la cause machine-readable ou le type d'exception; les echecs non finis sont classes `NAN_DETECTED`. |
| Options Newton | PARTIAL_DONE | `src/solveur/core/nonlinear_controls.py`, `core/nonlinear.py` | `NonlinearSolverOptions` centralise les controles communs en conservant les valeurs legacy. |
| Resultat et rollback arc-length | PARTIAL_DONE | `core/nonlinear.py`, `core/nonlinear_controls.py` | Les options Newton sont exportees dans le resultat; les increments arc-length echoues rollbackent explicitement; `NonlinearStep` expose le residu initial et la cause d'echec. |
| V&V constitutive | PASS_INTERNAL_INITIAL | `tests/unit/test_nonlinear_contracts.py` | Etat commis immuable; tangente J2 comparee par differences finies, erreur relative observee < `1e-7`. |
| V0 constitutive supplementaire | PASS_INTERNAL_INITIAL | `tests/unit/test_nonlinear_constitutive_vv.py` | Hydrostatique sans plasticite, cisaillement pur sur la surface J2 et repetabilite depuis l'etat commis. |
| V1 contrat elementaire | PASS_INTERNAL_INITIAL | `tests/unit/test_nonlinear_element_contracts.py` | TET4, TET10, HEX8 et HEX20 retournent force interne, tangente sparse-compatible et etats trial J2 a tous les points d'integration; la tangente TET4/TET10 est aussi comparee par difference finie avec erreur relative < `1e-7`. |
| V2 diagnostics Newton | PASS_INTERNAL_INITIAL | `tests/unit/test_nonlinear_load_path.py`, `tests/verification/test_j2_structural_vnv.py`, `tests/verification/test_j2_step_sensitivity_vnv.py`, `tests/verification/test_j2_methods_vnv.py`, `qualification/vnv/j2_unified_nonlinear_024/reference/v2_methods/` | Un echec controle par maximum d'iterations expose `MAX_ITERATIONS`, residu initial/final et historique par increment; les cutbacks exposent leur cause; TET4/TET10, sensibilite de pas et comparaison Newton sont vertes. |
| V2 sensibilite maillage | PASS_INTERNAL_INITIAL | `src/solveur/verification/j2_step_sensitivity.py`, `qualification/vnv/j2_unified_nonlinear_024/reference/v2_mesh_sensitivity/summary.json`, `qualification/external_reference_digests/j2_unified_nonlinear_024.json` | TET4 homogene sur trois niveaux; ecart d'etat maximal `1.1668553682347042e-09`, residu maximal `4.245472723492014e-09`; limite aux cas testes. |
| Performance bornee | PASS_INTERNAL_INITIAL | `src/solveur/verification/j2_performance.py`, `tests/unit/test_nonlinear_performance.py` | Caracterisation reproductible TET4/TET10: DDL, etats Gauss, temps total, iterations, residu et pic Python; aucune revendication HPC. |
| Correlation externe Code_Aster | PASS_EXTERNAL_CORRELATION | `qualification/vnv/external/code_aster_tet10_j2_structural/reference/summary.json` | Docker `simvia/code_aster:18.1.0`, digest `sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`; quatre checks externes PASS, dont RMS de trajectoire `2.1729e-4`. |
| Correlation externe CalculiX | PARTIAL_EXTERNAL | `qualification/vnv/external/calculix_j2/reference/summary.json` | Docker `qf-solver/calculix-nafems13h:2.20`; point materiau homogene/C3D8 sous deformation imposee, contrainte axiale et PEEQ conformes a la theorie; preuve externe partielle et non une qualification d'element QF. |
| Paquet V&V 0.2.4 initial | PASS_INTERNAL_INITIAL | `qualification/vnv/j2_unified_nonlinear_024/reference/vnv_manifest.json` | V0, V1 TET4/TET10, V2 sensibilite de pas/maillage et methodes Newton rejoues ensemble; aucun gate Owner ferme automatiquement. |
| Regression ciblee | PASS_TARGETED | tests solids/nonlinear/J2 | `91 passed, 3 skipped` sur le perimetre cible le 2026-08-24. |
| Regression ciblee elements/workflows | PASS_TARGETED | tests unitaires et integration solids | `78 passed` sur contrats, non-lineaire, TET4/TET10, HEX8/HEX20 et workflows le 2026-08-24. |
| Non-regression unit/integration | PASS_WITH_AUDIT_SYNC | tests unitaires et integration hors benchmark/large/evidence | `1380 passed, 107 deselected` lors de la campagne initiale; l'audit public courant est resynchronise a `1832` fichiers. |
| Gates complets | PARTIAL_SHA_PENDING | `DOC-NL-024-002`, `qualification/reviews/qf_solver_0_2_4a0_gate_status.json`, `qualification/external_reference_digests/j2_unified_nonlinear_024.json` | V0-V4 et RQ-G08 sont documentes; la decision Owner est enregistree. L'attachement au SHA final et la fermeture documentaire restent ouverts. |

Les modifications restent volontairement en worktree de developpement. Aucun
commit, tag ou push `0.2.4a0` n'est realise dans cette tranche. La version de
package locale est bien `0.2.4a0`; le SHA de release reste a fixer avant toute
fermeture de `NL-G11` et `NL-G12`.

## 15. Extension planifiee - Robustness Qualification — Nonlinear Solids

Cette section conserve l'extension de planification initiale. Les sous-sections
15.1 a 15.4 sont des artefacts historiques; la section 15.8 donne l'etat
execute. Elle ne transforme pas les limites multi-elements, cycliques ou de
validation physique en qualification de release.

### 15.1 Work packages initialement prevus (historique)

| WP | Work package | Livrable attendu | Statut avant implementation |
| --- | --- | --- | --- |
| RQ-NL-01 | Matrice J2 commune TET4/TET10/HEX8/HEX20 | Matrice element x loi x integration x etat, avec scope promu et exclusions explicites. | PLANNED |
| RQ-NL-02 | Chemins constitutifs multiaxiaux | Traction, cisaillement, dechargement, rechargement et chemin non proportionnel avec oracle independant. | PLANNED |
| RQ-NL-03 | Verification du consistent tangent | Sweep de differences finies en regimes elastique, seuil et plastique, plusieurs directions et pas. | PLANNED |
| RQ-NL-04 | Robustesse trial/commit/rollback | Tests d'echecs Newton, cutback, retry et egalite de l'etat commis a tous les points de Gauss. | PLANNED |
| RQ-NL-05 | Sensibilite maillage et pas de charge | Trois niveaux de maillage au minimum, sweep de pas et cas plastiques distordus HEX8/HEX20. | PLANNED |
| RQ-NL-06 | Benchmark commun des quatre elements | Meme geometrie, conditions aux limites et historique de charge pour TET4/TET10/HEX8/HEX20. | PLANNED |
| RQ-NL-07 | Correlation externe | Cas reproductibles Code_Aster et/ou CalculiX, avec limites de comparabilite documentees. | PLANNED |
| RQ-NL-08 | Taux de convergence Newton | Mesure de la reduction du residu et comparaison tangent coherent/tangent approche. | PLANNED |
| RQ-NL-09 | Audit du workflow de release | Proposition d'orchestrateur dry-run: tests, coverage, V&V, gates, SHA, build, smoke install, rapport. | PLANNED |

### 15.2 Tests prevus au demarrage (historique)

| Test a preparer | Couverture attendue |
| --- | --- |
| `tests/unit/test_robustness_j2_multiaxial.py` | Traction, cisaillement, unload/reload, rechargement et chemin non proportionnel. |
| `tests/unit/test_robustness_tangent_fd.py` | Consistent tangent contre differences finies, regimes et pas de perturbation. |
| `tests/unit/test_robustness_state_transactions.py` | Trial, commit, rollback, echec injecte, retry et absence de contamination. |
| `tests/verification/test_robustness_solid_matrix_vnv.py` | Qualification J2 commune des quatre elements sur une matrice de cas. |
| `tests/verification/test_robustness_distorted_hex_vnv.py` | HEX8/HEX20 distordus en regime plastique, geometrie et integration. |
| `tests/verification/test_robustness_common_benchmark_vnv.py` | Comparaison force-deplacement, reactions, von Mises, PEEQ, energie et iterations. |
| `tests/verification/test_robustness_newton_rate_vnv.py` | Taux de reduction du residu et comportement du tangent coherent. |
| `tests/integration/test_release_readiness_pipeline.py` | Orchestration dry-run et arret propre sur gate ou SHA incoherent. |

### 15.3 Inventaire initial des preuves et artefacts

Les artefacts ci-dessous restent a creer et devront porter le SHA, les versions
des dependances, l'environnement d'execution et les parametres de calcul:

- `qualification/external_reference_digests/robustness_nonlinear_solids_024.json`;
- un manifeste V&V de la matrice TET4/TET10/HEX8/HEX20;
- rapports des chemins multiaxiaux et de la verification tangentielle FD;
- journaux trial/commit/rollback, cutback et retry, avec etats avant/apres;
- tableaux de sensibilite au maillage et au pas de charge;
- cas et rapports de maillage distordu HEX8/HEX20;
- courbes `force_displacement`, `stress_peeq`, `energy_iterations` et
  `newton_rate`;
- rapport de benchmark commun avec temps, iterations, residus et memoire;
- rapports de correlation Code_Aster/CalculiX, ou justification d'absence;
- rapport machine-readable de readiness de release.

Les resultats devront distinguer `PASS_INTERNAL`, `PASS_EXTERNAL_CORRELATION`,
`BLOCKED` et `MORE_EVIDENCE_REQUIRED`. Une comparaison externe ne pourra pas
etre presentee comme validation physique sans preuve experimentale distincte.

### 15.4 Requirements supplementaires

| Requirement | Metrique | Target / Reject | Preuve | Gate |
| --- | --- | --- | --- | --- |
| RQ-REQ-01 Matrice commune | Quatre elements, meme contrat J2 et memes observables. | Aucun element declare qualifie sans sa preuve complete. | Matrice element x cas. | RQ-G02 |
| RQ-REQ-02 Chemins multiaxiaux | Erreur contre oracle, yield, unload/reload et PEEQ. | Seuils fixes apres baseline et approuves Owner. | Rapport constitutif. | RQ-G03 |
| RQ-REQ-03 Tangente coherente | Erreur FD et stabilite sur sweep de pas. | Hors plage justifiee = reject. | Courbes et tableau FD. | RQ-G04 |
| RQ-REQ-04 Transaction d'etat | Etat commis identique apres echec et retry. | Toute contamination = reject. | Checksum/etats Gauss. | RQ-G05 |
| RQ-REQ-05 Robustesse discretisation | Sensibilite maillage/pas et cas HEX distordu. | Pas d'extrapolation hors domaine observe. | Etudes de convergence. | RQ-G06 |
| RQ-REQ-06 Comparaison commune | Ecarts force, reactions, contraintes, PEEQ, energie, Newton. | Seuils par metrique apres baseline. | Benchmark quatre elements. | RQ-G07 |
| RQ-REQ-07 Correlation externe | Meme geometrie, BC, materiau et historique autant que possible. | Ecart non explique = bloque le scope concerne. | Rapports Code_Aster/CalculiX. | RQ-G08 |
| RQ-REQ-08 Taux Newton | Reduction du residu par iteration, stagnation/divergence detectees. | Aucune revendication quadratique sans mesure. | Rapport Newton. | RQ-G09 |
| RQ-REQ-09 Release dry-run | Pipeline complet et SHA coherent. | Echec ou mismatch bloque la readiness. | `release_readiness.json`. | RQ-G10 |

### 15.4.1 Traceabilite supplementaire

| Requirement | Formule / contrat | Implementation future | Test | Evidence | Gate |
| --- | --- | --- | --- | --- | --- |
| RQ-REQ-01 | Meme loi J2, memes observables et integration explicite. | Adaptateur constitutif commun des quatre elements. | `test_robustness_solid_matrix_vnv.py`. | Matrice element x cas. | RQ-G02 |
| RQ-REQ-02 | Surface de charge J2 et evolution multiaxiale. | Chemins d'increment et oracle independant. | `test_robustness_j2_multiaxial.py`. | Rapport des trajectoires. | RQ-G03 |
| RQ-REQ-03 | `C_algorithmic` compare a `d sigma / d epsilon`. | Exposition du tangent coherent. | `test_robustness_tangent_fd.py`. | Sweep FD et erreurs. | RQ-G04 |
| RQ-REQ-04 | Etat commis preserve apres echec. | Session transactionnelle et retry. | `test_robustness_state_transactions.py`. | Journal/checksum Gauss. | RQ-G05 |
| RQ-REQ-05 | Convergence en h et sensibilite au pas. | Cas distordus et controle d'increment. | `test_robustness_distorted_hex_vnv.py`. | Tableaux de sensibilite. | RQ-G06 |
| RQ-REQ-06 | Comparaison des champs et bilans globaux. | Harness de benchmark commun. | `test_robustness_common_benchmark_vnv.py`. | Courbes et metriques. | RQ-G07 |
| RQ-REQ-07 | Equivalence de modele et historique externe. | Exporteurs/adaptateurs de correlation. | Campagne Code_Aster/CalculiX. | Rapports externes. | RQ-G08 |
| RQ-REQ-08 | Reduction du residu par iteration. | Instrumentation du driver Newton. | `test_robustness_newton_rate_vnv.py`. | Rapport de taux. | RQ-G09 |
| RQ-REQ-09 | Chaine deterministe et arret sur erreur. | Orchestrateur de readiness dry-run. | `test_release_readiness_pipeline.py`. | `release_readiness.json`. | RQ-G10 |

### 15.5 V&V supplementaire

| Niveau | Scope | Observables | Statut |
| --- | --- | --- | --- |
| V5 | J2 commun sur TET4/TET10/HEX8/HEX20 | Stress, von Mises, PEEQ, reactions, energie, iterations. | PASS_INTERNAL_ACCEPTED_OWNER |
| V6 | Chemins multiaxiaux et non proportionnels | Yield, tangent, etats et sensibilite au chemin. | PASS_INTERNAL_ACCEPTED_OWNER |
| V7 | HEX8/HEX20 distordus en plastique | Jacobien, forces, tangent, convergence et champs. | PASS_INTERNAL_ACCEPTED_OWNER |
| V8 | Benchmark commun quatre elements | Courbes et metriques communes sur meme histoire. | PASS_INTERNAL_ACCEPTED_OWNER |
| V9 | Taux de convergence Newton | Residus, ratios de reduction, tangent coherent/approche. | PASS_INTERNAL_ACCEPTED_OWNER |
| V10 | Correlation externe | Comparaison champs et trajectoires, limites et environnement. | PASS_EXTERNAL_CORRELATION_BOUNDED |

### 15.6 Release gates supplementaires

| Gate | Condition de fermeture | Etat initial |
| --- | --- | --- |
| RQ-G01 | Scope, requirements et seuils approuves par l'Owner. | ACCEPTED_WITH_RECOMMENDATIONS |
| RQ-G02 | Matrice J2 des quatre elements complete et sans promotion abusive. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G03 | Tous les chemins multiaxiaux constitutifs sont rejouables et traces. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G04 | Consistent tangent FD conforme aux seuils approuves. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G05 | Trial/commit/rollback verifie sans contamination d'etat. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G06 | Maillage, pas de charge et HEX distordu documentes. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G07 | Benchmark commun et toutes les metriques comparees. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G08 | Correlations externes rejouees dans le scope borne et limites explicites. | PASS_EXTERNAL_CORRELATION_BOUNDED |
| RQ-G09 | Taux Newton mesure et interprete sans extrapolation. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G10 | Workflow dry-run complet, SHA coherent, wheel/sdist installables. | ACCEPTED_WITH_RECOMMENDATIONS |

### 15.7 Automatisation de readiness, sans publication

La proposition d'audit est une commande dry-run idempotente suivant exactement:

`tests -> coverage -> V&V -> gate check -> SHA consistency -> build wheel/sdist -> smoke install -> release readiness report`

Chaque etape doit produire un resultat machine-readable; une erreur doit
arreter la chaine et enumerer les blockers. Le workflow ne doit appeler ni
`twine upload`, ni creation de tag, ni push. La decision de release reste
exclusivement Owner.

Les work packages, tests, preuves et gates ci-dessus ont servi de contrat de
travail. La tranche implementee ci-dessous ferme RQ-G08 dans son scope
externe borne; les extensions multi-elements et cycliques restent distinctes.

### 15.8 Etat d'implementation et preuves internes

La premiere tranche de l'extension a maintenant ete implementee et rejouee,
sans fermeture automatique des gates Owner ou externes:

| Element | Etat | Preuve |
| --- | --- | --- |
| Support J2 commun TET4/TET10/HEX8/HEX20 | PASS_INTERNAL | `src/solveur/verification/robustness_nonlinear_solids.py` et matrice V&V. |
| Chemins traction/cisaillement/unload-reload/non proportionnel | PASS_INTERNAL | `qualification/vnv/robustness_nonlinear_solids_024/reference/summary.json`. |
| Consistent tangent FD | PASS_INTERNAL | Erreur relative maximale `7.1168e-11`, limite interne `1e-6`. |
| Trial/commit/rollback | PASS_INTERNAL | Transaction check et `tests/unit/test_robustness_state_transactions.py`. |
| HEX8/HEX20 distordus | PASS_INTERNAL | Jacobiennes positives, forces/tangentes finies et plasticite active. |
| Benchmark global commun | PASS_INTERNAL | Quatre elements, historique `[0.25, 0.5, 0.75, 1.0]`, residus sous `1e-7`. |
| Correlation Code_Aster des quatre elements | PASS_EXTERNAL_CORRELATION_BOUNDED | `qualification/external_reference_digests/rqg08_j2_common_024.json` et `docs/verification/rqg08_external_j2_common_024.md`, 80 controles, patch affine a un element. |
| Readiness complete | PENDING | La chaine dry-run existe; SHA final et worktree propre restent requis. |

Cette evidence interne ne constitue ni une validation physique, ni une
qualification externe, ni une revendication de scalabilite multi-million de
DDL.

## Extension Owner - preuve RQ-G08 et promotion ulterieure

La decision Owner `accepted_with_recommendations` autorise le perimetre
experimental interne 0.2.4a0. RQ-G08 est maintenant fermee dans son scope
externe borne; le plan conserve les work packages suivants pour une promotion
plus large:

| ID | Objectif | Gate |
| --- | --- | --- |
| RQ-NL-10 | Correlation J2 externe commune sur TET4/TET10/HEX8/HEX20 avec meme historique et observables complets. | PASS_EXTERNAL_CORRELATION_BOUNDED |
| RQ-NL-11 | Cas multi-elements et convergence en maillage pour assemblage et redistribution plastique. | RQ-G06/RQ-G07 |
| RQ-NL-12 | Travail externe, energie elastique et dissipation plastique. | RQ-G07 |
| RQ-NL-13 | Echec Newton reel, rollback, cutback, retry et equivalence avec une reference fine. | RQ-G05/RQ-G06 |
| RQ-NL-14 | Analyse des ecarts PEEQ et profilage du cout HEX20. | RQ-G10 |

Full Newton est le seul chemin qualifie pour 0.2.4a0. Modified Newton reste
hors production. `RQ-G08` est ferme pour le patch affine a un element; le
chantier 0.2.5 pourra etendre la preuve aux cas multi-elements, cycliques et
physiques.
