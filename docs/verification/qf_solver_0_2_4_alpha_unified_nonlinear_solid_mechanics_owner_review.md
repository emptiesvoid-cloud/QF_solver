---
doc_id: DOC-NL-024-002
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.4a0
reviewer: ""
approver: ""
---

# Gates et revue Owner - 0.2.4 alpha Unified Nonlinear Solid Mechanics

## Regle de lecture

Les gates ci-dessous distinguent les preuves bornees fermees des conditions de
release encore dependantes du SHA final. La decision Owner est enregistree comme
`accepted_with_recommendations` pour le perimetre experimental
`PASS_INTERNAL` avec une correlation externe bornee ajoutee depuis. Cette
decision ne signe ni le code ni une release: le SHA final et la fermeture
documentaire restent distincts et tracables.

La tranche initiale du contrat constitutif, de l'etat transactionnel et des
preuves de robustesse est executee. Elle est completee par la correlation
externe bornee RQ-G08, fermee pour son patch affine a un element, sans
qualification physique ou promotion multi-elements.

## Etat de travail au 2026-08-24

La tranche initiale fournit deja un contrat constitutif commun, une session
trial/committed, des diagnostics Newton structures et un assemblage extrait
dans un module dedie. Les preuves internes actuellement observees sont :

- V0 J2 : hydrostatique, cisaillement pur, tangente par differences finies et repetabilite d'etat;
- V1 element : TET4, TET10, HEX8 et HEX20 sur le contrat force/tangente/etat
  local; les quatre elements restent dans le perimetre experimental interne;
  la tangente TET4/TET10 est comparee par difference finie avec erreur
  relative < `1e-7`;
- V2 initial : maximum d'iterations, causes d'echec, rollback et cutback traces;
  chaque increment expose maintenant son historique de residus;
- sensibilite au maillage TET4 bornee : trois niveaux `h = 0.36, 0.24, 0.18`,
  ecart d'etat maximal `1.1668553682347042e-09` et residus maximaux
  `4.245472723492014e-09`;
- campagne J2 globale : TET4, TET10, sensibilite au pas et comparaison des
  methodes Newton : `4 passed`;
- caracterisation performance bornee TET4/TET10 ajoutee; elle mesure le cout
  total, les iterations, les etats et le pic d'allocation Python sans
  revendiquer la scalabilite HPC;
- non-regression hors campagnes longues : `1380 passed, 107 deselected`;
- V&V existante selectionnee : `69 passed, 14 skipped, 79 deselected`.
- correlation Code_Aster TET10 structurelle executee dans Docker `simvia/code_aster:18.1.0`, digest `sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`, statut `PASS_EXTERNAL_CORRELATION`;
- correlation CalculiX 2.20 executee dans Docker `qf-solver/calculix-nafems13h:2.20`, statut `PARTIAL_EXTERNAL` sur un point materiau homogene/C3D8 a deformation imposee; cette preuve reste lineaire/partielle et ne qualifie pas le J2 commun HEX8/HEX20.
- correlation J2 externe commune `VNV-RQ-G08-J2-COMMON-024` executee dans Docker Code_Aster 18.1.0 pour TET4/TET10/HEX8/HEX20; `80` controles, statut `PASS_EXTERNAL_CORRELATION_BOUNDED`, ecart maximal `< 2.7e-15`.
- paquet V&V initial rejoue : `qualification/vnv/j2_unified_nonlinear_024/reference/vnv_manifest.json`, avec V0 constitutif, V1 TET4/TET10 et V2 sensibilite pas/maillage/methodes; statut `PASS_INTERNAL_INITIAL`.
- suite documentaire complete : `42 passed, 6 skipped` (`tests/documentation`).
- wheel et sdist construits localement; smoke import depuis la wheel : `PASS`.
  La version package candidate est `0.2.4a0`; le SHA final sera renseigne
  après la campagne complète et le commit local de préparation.
- etat machine-readable des gates : `qualification/reviews/qf_solver_0_2_4a0_gate_status.json`; decision Owner enregistree, aucun claim de release et aucun SHA final declare.

Ces resultats sont des preuves internes acceptees avec recommandations pour le
scope experimental, completees par une correlation externe bornee. Le
rattachement des preuves au SHA final et la fermeture documentaire de release
restent requis. RQ-G08 est fermee pour le patch affine a un element; les
correlations multi-elements, cycliques et physiques restent hors scope.

## Matrice des release gates

| Gate | Exigence | Preuve attendue | Etat |
| --- | --- | --- | --- |
| NL-G01 | Architecture approuvee | Contrats, audit de couplage, decision Owner. | ACCEPTED_WITH_RECOMMENDATIONS |
| NL-G02 | Constitutive unit verification | J2 V0, tangent FD, etat et seuils traces. | PASS_INTERNAL_INITIAL |
| NL-G03 | Element contract verification | TET4/TET10 MUST: force, tangent, Gauss et distorsion. | PASS_INTERNAL_INITIAL |
| NL-G04 | Newton verification | Residus, corrections, convergence et causes d'echec. | PASS_INTERNAL_INITIAL |
| NL-G05 | Commit / rollback | Echecs injectes, reprise, aucune contamination d'etat. | PASS_INTERNAL_INITIAL |
| NL-G06 | Adaptive stepping | Cutback, retry, increment minimal et logs. | PASS_INTERNAL_INITIAL |
| NL-G07 | Analytical / reference benchmarks | Cas interpretable et sensibilites documentes. | PASS_INTERNAL_INITIAL |
| NL-G08 | External correlations | Code_Aster reproductible dans le scope borne retenu. | PASS_EXTERNAL_CORRELATION_BOUNDED |
| NL-G09 | Mesh and load-step convergence | Sensibilites et limites publiees. | PASS_INTERNAL_INITIAL |
| NL-G10 | Performance sanity | Cout Newton/assembly/state sans regression majeure inexpliquee. | PASS_INTERNAL_INITIAL |
| NL-G11 | Full regression 0.2.3 | Suite lineaire, dynamique, modal, harmonic, solids, MITC et V&V pertinente verte. | PASS_CURRENT_WORKTREE_PENDING_SHA |
| NL-G12 | Documentation and evidence closure | Matrice de tracabilite et artefacts lies au SHA final. | PARTIAL_SHA_PENDING |
| NL-G13 | Owner review | Decision explicite, scope et limitations signes. | ACCEPTED_WITH_RECOMMENDATIONS |

## Matrice de tracabilite minimale

| Requirement | Formule / comportement | Code futur | Tests | Evidence | Gate |
| --- | --- | --- | --- | --- | --- |
| NL-REQ-03 / J2 | Yield, return mapping, ecrouissage isotrope. | Constitutive core. | V0 material. | Rapport J2. | NL-G02 |
| NL-REQ-04 / tangent | `d sigma / d epsilon` algorithmique. | Constitutive response. | FD directions/pas. | Courbes erreur FD. | NL-G02 |
| NL-REQ-05 / element | `f_int` et `df_int / du`. | TET4/TET10 contract. | Patch et FD element. | Summaries V1. | NL-G03 |
| NL-REQ-06 / Newton | Equilibre global et criteres explicites. | Global driver. | Cas V2. | Historiques residu. | NL-G04 |
| NL-REQ-02 / state | Commit apres convergence, rollback sinon. | State session. | Echecs injectes. | Checkpoint/retry evidence. | NL-G05 |
| NL-REQ-07 / stepping | Cutback et arret au pas minimal. | Increment controller. | Cas difficile. | Journal increments. | NL-G06 |
| NL-REQ-08 / regression | Chemins lineaires inchanges. | Router/adaptateurs. | NR-0.2.3. | Rapport final. | NL-G11 |

## Registre des risques

| ID | Risque | Prob. | Gravite | Detection | Mitigation | Gate |
| --- | --- | --- | --- | --- | --- |
| R1 | Tangente incoherente avec convergence apparente. | Moyenne | Haute | FD local + taux de reduction Newton. | Gate tangent et comparaison tangent approximative. | NL-G02, NL-G04 |
| R2 | Etat commis contamine par un essai echoue. | Moyenne | Haute | Echecs injectes, checksum/egalite des etats. | Transaction explicite, rollback atomique. | NL-G05 |
| R3 | Loi locale correcte mais residu global incorrect. | Moyenne | Haute | FD element, forces/reactions. | Contrat element et benchmarks V2. | NL-G03, NL-G04 |
| R4 | Resultat dependant des increments. | Haute | Haute | Sweep pas de charge. | Cutback, sensibilite et limites. | NL-G06, NL-G09 |
| R5 | Resultats justes pour un seul element. | Moyenne | Haute | Matrice TET4/TET10/SHOULD. | MUST multi-element; promotions separees. | NL-G03, NL-G08 |
| R6 | Architecture liee a J2. | Moyenne | Moyenne | Revue de dependances. | Protocole constitutif sans nom d'element. | NL-G01 |
| R7 | Regression du chemin lineaire 0.2.3. | Moyenne | Haute | Full regression. | Adaptateurs, router stable et NR obligatoire. | NL-G11 |
| R8 | Memoire excessive des etats Gauss. | Moyenne | Moyenne | Profil et estimation par point. | Mesures, serialisation ciblee, pas de copies inutiles. | NL-G10 |
| R9 | Tests sans vraie plastification. | Moyenne | Haute | Verification yield/plastic path. | V0/V1 avec assertions sur ep et yield. | NL-G02, NL-G03 |
| R10 | Usage abusif de "validated". | Moyenne | Haute | Revue vocabulary/evidence. | Distinguer verification, correlation et validation physique. | NL-G12, NL-G13 |

## Checklist Owner avant implementation

- [ ] Le scope MUST/SHOULD/COULD est approuve.
- [ ] Les exclusions TL, contact, grandes deformations et nouveaux elements sont acceptees.
- [ ] La semantique deformation totale du contrat J2 initial est acceptee.
- [ ] Le comportement de non-convergence public (erreur structuree ou resultat) est decide.
- [ ] La politique line search et modified Newton est decidee.
- [ ] Le protocole de fixation des tolerances FD/convergence est accepte.
- [ ] Les correlations externes faisables et leurs environnements sont identifies.
- [ ] Aucun gate n'est considere ferme avant preuves attachees au SHA final.

## Decision Owner enregistree

Decision Owner : `accepted_with_recommendations` pour le perimetre
experimental de la 0.2.4a0. La correlation externe J2 commune est maintenant
fermee pour le scope borne du patch affine a un element; cette preuve
n'autorise aucune revendication de validation physique ni d'extrapolation
multi-elements.

## Extension proposee - Robustness Qualification — Nonlinear Solids

Cette extension est executee pour les preuves internes et la correlation
externe bornee du perimetre experimental. Elle ne couvre pas la qualification
multi-elements, cyclique ou physique des TET4, TET10, HEX8 et HEX20.

### Work packages

- `RQ-NL-01`: matrice J2 commune des quatre elements et limites de promotion;
- `RQ-NL-02`: traction, cisaillement, dechargement/rechargement et chemin
  multiaxial non proportionnel;
- `RQ-NL-03`: consistent tangent verifie par differences finies;
- `RQ-NL-04`: trial/commit/rollback, echec injecte, cutback et retry;
- `RQ-NL-05`: sensibilite au maillage et au pas de charge, avec HEX8/HEX20
  distordus en plastique;
- `RQ-NL-06`: benchmark commun meme geometrie et meme historique de charge;
- `RQ-NL-07`: correlations Code_Aster et/ou CalculiX lorsque comparables;
- `RQ-NL-08`: mesure du taux de convergence Newton;
- `RQ-NL-09`: audit et dry-run du workflow de readiness de release.

### Tests a preparer

- `tests/unit/test_robustness_j2_multiaxial.py`;
- `tests/unit/test_robustness_tangent_fd.py`;
- `tests/unit/test_robustness_state_transactions.py`;
- `tests/verification/test_robustness_solid_matrix_vnv.py`;
- `tests/verification/test_robustness_distorted_hex_vnv.py`;
- `tests/verification/test_robustness_common_benchmark_vnv.py`;
- `tests/verification/test_robustness_newton_rate_vnv.py`;
- `tests/integration/test_release_readiness_pipeline.py`.

### Preuves a produire

- manifeste `robustness_nonlinear_solids_024.json` lie au SHA final;
- digest suivi `qualification/external_reference_digests/rqg08_j2_common_024.json`;
- rapport externe suivi `docs/verification/rqg08_external_j2_common_024.md`;
- archive brute `qualification/vnv/external/rqg08_j2_common_024/reference/summary.json`;
- rapports multiaxiaux, tangent FD, transactions et sensibilites;
- preuves HEX8/HEX20 distordues;
- courbes force-deplacement, contraintes de von Mises, PEEQ, reactions,
  energie et iterations Newton;
- rapport de convergence Newton et correlations externes;
- `release_readiness.json` issu d'un dry-run complet.

### Gates supplementaires

| Gate | Condition | Etat |
| --- | --- | --- |
| RQ-G01 | Scope, requirements et seuils approuves. | ACCEPTED_WITH_RECOMMENDATIONS |
| RQ-G02 | Matrice J2 TET4/TET10/HEX8/HEX20 complete. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G03 | Chemins multiaxiaux verifies. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G04 | Consistent tangent FD conforme. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G05 | Trial/commit/rollback sans contamination. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G06 | Maillage, pas de charge et distorsion qualifies. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G07 | Benchmark commun et metriques comparees. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G08 | Correlations externes documentees dans le scope borne. | PASS_EXTERNAL_CORRELATION_BOUNDED |
| RQ-G09 | Taux de convergence Newton mesure. | PASS_INTERNAL_ACCEPTED_OWNER |
| RQ-G10 | Workflow dry-run et SHA consistency conformes. | ACCEPTED_WITH_RECOMMENDATIONS |

Le workflow propose est:

`tests -> coverage -> V&V -> gate check -> SHA consistency -> build wheel/sdist -> smoke install -> release readiness report`

Il ne doit effectuer ni publication PyPI, ni tag, ni push automatique. La
decision Owner est enregistree; le workflow reste un dry-run de readiness.
Les preuves multi-elements, cycliques et de validation physique restent des
conditions de promotion ulterieure.

## Mise a jour d'implementation pour revue Owner

La campagne interne `VNV-ROBUSTNESS-NONLINEAR-SOLIDS-024` a ete executee sur
les quatre elements. Elle est disponible dans
`qualification/vnv/robustness_nonlinear_solids_024/reference/summary.json` et
dans le digest `qualification/external_reference_digests/robustness_nonlinear_solids_024.json`.

Resultats observes:

- constitutif multiaxial : `PASS_INTERNAL`;
- consistent tangent FD : erreur maximale `7.1168e-11`;
- trial/commit/rollback : `PASS`;
- HEX8 et HEX20 distordus : `PASS_INTERNAL`;
- benchmark global commun : TET4, TET10, HEX8 et HEX20 `PASS_INTERNAL`;
- correlation externe J2 commune : `PASS_EXTERNAL_CORRELATION_BOUNDED` sur
  TET4/TET10/HEX8/HEX20, 80 controles, image Code_Aster epinglee;
- readiness SHA et publication : `PASS_LOCAL_PENDING_SHA`, sans tag, push ou upload.

Les gates `RQ-G02` a `RQ-G07` et `RQ-G09` sont donc renseignes comme
`PASS_INTERNAL_ACCEPTED_OWNER`. `RQ-G08` est ferme comme
`PASS_EXTERNAL_CORRELATION_BOUNDED`; `RQ-G10` reste
`ACCEPTED_WITH_RECOMMENDATIONS` tant qu'aucun SHA de release n'est attache.

## Decision Owner integree - accepted_with_recommendations

Decision fournie par l'Owner : `accepted_with_recommendations` pour le
perimetre experimental `PASS_INTERNAL` de la 0.2.4a0.

- Q1 a Q6 : `OUI`.
- Q7 : `OUI`; Full Newton est le seul chemin qualifie et utilisable dans ce
  perimetre.
- Q8 : `CONDITIONNELLEMENT`; `RQ-G08` est fermee pour le patch affine borne,
  tandis que le scope multi-elements/cyclique reste conditionnel.
- Q9 : `OUI`; les correlations CalculiX lineaires HEX8/HEX20 sont acceptees
  comme preuves externes partielles uniquement.
- Q10 a Q12 : `OUI`.

Modified Newton reste non qualifie et doit etre verrouille, desactive ou
explicitement documente hors production. Aucune revendication de validation
externe ou physique n'est autorisee sur la seule base des preuves internes.
La publication PyPI automatique reste interdite.

## RQ-G08 - portée fermée et travaux de promotion ultérieure

| ID | Work package | Preuve attendue | Priorite |
| --- | --- | --- | --- |
| RQ-NL-10 | Correlation J2 externe commune TET4/TET10/HEX8/HEX20 | Même matériau, historique, résultant de traction, von Mises, PEEQ, onset et état final avec Code_Aster. | PASS_EXTERNAL_CORRELATION_BOUNDED |
| RQ-NL-11 | Benchmark multi-elements et convergence en maillage | Redistribution plastique, etats Gauss, assemblage global et trois niveaux de maillage minimum. | Haute |
| RQ-NL-12 | Bilan energetique | Travail externe, energie elastique, dissipation plastique et positivite. | Haute |
| RQ-NL-13 | Echec reel, rollback, cutback et retry | Etat commis intact, pas reduit et etat final equivalent a la reference. | Haute |
| RQ-NL-14 | Analyse PEEQ et profilage HEX20 | Sensibilite formulation/integration/maillage et temps Gauss, constitutif, tangent, Newton et copies. | Moyenne |

`RQ-G08` est fermé pour le périmètre borné documenté. Les work packages
RQ-NL-11 à RQ-NL-14 restent nécessaires avant toute promotion plus large.
