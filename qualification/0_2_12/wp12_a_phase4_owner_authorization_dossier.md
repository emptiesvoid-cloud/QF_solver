# QF Solver v0.2.12 — WP12-A Phase 4
## Dossier Owner : réinscription WP07, manifestes et préparation de décision

Date : 2026-10-27

**Statut courant : `WP12A_FOUR_CASES_PREPARED_OWNER_DECISION_PENDING`.** WP12-A demeure `OPEN`. Aucun calcul FEM, eigensolve, analyse harmonique ou Newmark n’a été exécuté. Aucune tentative n’a été réservée. Les résultats ci-dessous distinguent les faits de configuration des résultats historiques.

## 1. Identités canoniques

| Objet | Identité vérifiée |
|---|---|
| Branche de release | `emptiesvoids-cloud/0.2.12` |
| HEAD distant courant | `fc8a31476cb3eba0bdc764604d3e366c09ed78df` |
| Tree du HEAD courant | `f771b0d20c21f6ab5e6ff29b5d0232a7493dabf7` |
| Merge PR #38 | `fc8a31476cb3eba0bdc764604d3e366c09ed78df`, parent de base `d64e6036…`, parent PR `6ce7d763…` |
| PR #38 | `MERGED`, le 2026-10-27; net final : 10 fichiers WP12-A (cinq tests, cinq documents) |
| Checkout scientifique | `E:\QFSolverAgents\wp12-dynamics`, branche `codex/wp12-dynamic-harmonic-verification`, HEAD `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66`, tree `a6bcf6a3cea4bdc9ab17adcf53ce2151a2bc4758`, propre |

Les quatre nodeids sont présents et collectables sur le HEAD canonique. Pour chacun, le fingerprint source officiel calculé sur le candidat `fc8a314` est identique au fingerprint calculé dans le worktree scientifique `630d22b`. Cette identité de contenu ne signifie pas que le test a été exécuté sur la branche de release : le worktree d’exécution inscrit par le mandat reste celui à `630d22b`.

### Contrôleur et politique

Depuis `d64e6036` jusqu’à `fc8a314`, le contrôleur, son plugin et la politique n’ont pas changé. SHA-256 des trois fichiers au HEAD courant :

| Fichier | SHA-256 |
|---|---|
| `scripts/development_autonomous.py` | `e307547a47e7d1c58224eb74a52211c47bc4270a86e875a6af0d56496bfc4500` |
| `scripts/development_autonomous_pytest_plugin.py` | `9b8fd647434469b1f6e26085d148bb81f22d5a87b4dbaac11c087173e5577df5` |
| `development_autonomous_policy.json` | `cdcdda2b9dc6cb0a23241b7d62ccd56403a76a731d022c6e86f37c3cb82245d0` |

Le fingerprint de contrôleur calculé par `_controller_provenance()` / `_stable_fingerprint()` est **`ba98996f9167fdbd02b6bb0af882f8c34ac8cc5c15205c2634c3ecc25765dd26`**, pour le checkout propre `C:\Users\fari\.codex\worktrees\wp12a-phase4-canonical\qf_solver`, HEAD `fc8a314`, tree ci-dessus, Python 3.13.1, pytest 8.4.1, psutil 7.2.2. Le fingerprint complet inclut l’identité Git et le chemin du checkout, en plus des empreintes de fichiers et du runtime; il diffère donc du `5e822518…` des anciens manifestes préparés depuis le checkout contrôleur à `d64e6036`.

**Blocage de la voie de lancement configurée :** les règles du dépôt pointent le launcher partagé vers `E:\QFSolverAgents\wp12-policy-final`. Ce checkout est sur `4bf52792f46988b84fecf11ebe3bd5fe078975ef`, en retard de 45 commits, avec `development_autonomous_policy.json` modifié localement. Ses hashes runner/plugin/policy sont `509c5e5d…`, `c1cf6238…`, `a805f55d…`. Il n’a pas été utilisé ni modifié. Les nouveaux manifests ci-dessous sont liés au checkout propre `fc8a314`, donc le launcher configuré ne peut pas les accepter avec son identité actuelle. Avant une exécution future, le contrôleur partagé doit être synchronisé et propre selon une procédure revue, puis les manifests doivent être préparés avec l’identité exacte du launcher choisi.

## 2. Quatre sentinelles et critères

| Cas | Nodeid exact | Fingerprint source | Enregistrement / DDL | Oracle et critères existants |
|---|---|---|---|---|
| WP07 historique | `tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames` | `969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6` | Scope `wp12_dynamics`; enregistrement courant périmé `6db5b459…`, HEAD d’inscription `e64493e…`; 1 UX libre, 300 s. Allowlist exact déjà présente. | BEAM2 SDOF, 1,25 Hz, accélération complexe `1,7j`; oracle sur l’équation libre complète `-(M r)[f] a/(Kff−ω²Mff)`. Repères relatif/absolu, `x_g=−a/ω²`, relations vitesse/accélération et round-trip JSON. Déplacement : `rel=1e-11`, `abs=1e-13`; autres comparaisons `pytest.approx`. Oracle mécanique et tolérances inchangés. |
| Newmark | `tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | `65e4078b1735de9adb258d1438fed39dcd69c1b68fa3560afb69896da60bdff8` | Enregistrement actif conforme; 1 DDL, 300 s. | BEAM2 SDOF libre, `q0=1e-3 m`, `t_final=0,08 s`, `dt=0,002/0,001/0,0005 s`, solution analytique de déplacement/vitesse/accélération. `β=0,25`, `γ=0,5`; ordre observé de déplacement ≥ 1,8, résidu d’équilibre réduit ≤ `1e-7`, dérive énergétique relative ≤ `1e-10`. Le résidu dépend de la normalisation modale; l’identité d’énergie est interne à l’assemblage. |
| Harmonique réduit | `tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation` | `bd65535cfeaff0af932fb33e556ded5c1762f2dd90a5467793bdc01c6daca50c` | Enregistrement actif conforme; 3 DDL sélectionnés (TET4 à 12 DDL, trois translations bloquées sur nœuds 0/2/3); 300 s. | Compare solveur direct et base modale complète à base tronquée sur fréquences DC, demi-fréquence propre et points ±2 % près des fréquences propres extrêmes. Erreurs arrière réduite et libre physique ≤ `1e-8`; erreur vectorielle complète/directe ≤ `1e-8`. La différence de troncature est mesurée, sans prétention à une borne générale d’erreur. |
| Accélération de base | `tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` | `969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6` | Enregistrement actif conforme; 1 UX libre, 300 s. | BEAM2, phasor `0,7−0,4j`, fréquences DC, moitié de fréquence propre et ±2 % autour de la résonance. Équation libre complète avec couplage inertiel; contrôles des déplacements relatifs/absolus, vitesse, accélération, disponibilité à DC et round-trip. Réponses comparées avec `rel=1e-11`, `abs=1e-13` (et disponibilité prescrite). |

Les quatre formulations restent `EXPERIMENTAL`. Les résultats historiques de développement Newmark/harmonique/base-acceleration (au HEAD `d9deddb…`) ne sont pas des résultats de l’exécution actuelle. L’ancien échec du node WP07 historique après sérialisation reste `FAIL` et inchangé.

## 3. Réinscription prospective WP07

Le nodeid historique est enregistré dans **`wp12_dynamics`**, non dans `wp12_wp07`. L’inscription historique à `e64493e…` porte `6db5b459…`; le fingerprint courant est `969dd027…`. L’inventaire officiel diffère dans le module complet `test_wp07_uniform_base_acceleration.py`, tandis que l’AST du test ciblé demeure `a69d54576ad5989bd34fed0a98b20b4ab046fd516adf8bf1663cff2e004cfe45`. Le delta vient des imports et du helper d’archivage ajouté en `1f609e52`, puis de la plomberie d’identifiants de série ajoutée en `d9deddbd`; le code solveur, l’oracle, les assertions numériques et tolérances ne sont pas la cause du changement.

Le contrôleur utilise la dernière entrée `nodeid_registration_records` pour un nodeid dans le scope demandé. `register_wp12_nodeid()` refuse le couple cible/fingerprint seulement s’il est déjà l’enregistrement le plus récent; sinon il ajoute une nouvelle entrée. La cible existe déjà dans `allowed_nodeids`, donc aucune nouvelle allowlist ni modification de schéma n’est nécessaire. Aucune collision n’existe avec l’enregistrement d’un autre scope. **Aucune inscription n’a été exécutée.**

Commande à faire approuver, puis exécuter seulement depuis le contrôleur canonique synchronisé et propre :

```powershell
python scripts\development_autonomous.py register-nodeid `
  --worktree wp12_dynamics `
  --target "tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames" `
  --reason "Prospective source revision after archive-helper changes; preserve historical record and unchanged WP07 oracle." `
  --selected-dofs 1 `
  --selection-basis "One free UX DDL in the harmonic BEAM2 base-acceleration fixture." `
  --timeout-seconds 300
```

Cette opération modifie le registre de politique et doit append-only préserver la ligne `6db5…` ainsi que le FAIL historique. Elle doit être décidée séparément de toute décision d’exécution. Après cette modification, le SHA de politique et donc le fingerprint de contrôleur changera : il faudra préparer **quatre nouveaux manifests après la réinscription**, même si les trois templates Phase 4 existent déjà.

Le manifeste WP07 historique ne peut pas être préparé actuellement : `_wp12_active_registration()` refuse son fingerprint actif `6db5…` face au source `969dd…`. Cela justifie le statut alternatif de livraison demandé par le mandat.

## 4. Manifestes et provenance

### Trois anciens templates Phase 2 conservés

Les fichiers Phase 2 n’ont pas été remplacés ni modifiés; leurs SHAs restent `c657172d…` (Newmark), `e649468c…` (harmonique), `6d9bff0e…` (accélération de base). Ils sont `PREPARED_NOT_AUTHORIZED`, sans réservation, et liés au même source `630d22b…`, mais à l’ancien fingerprint complet contrôleur `5e822518…` associé au checkout à `d64e6036`. Le contrôleur `fc8a314` les refuse par identité de contrôleur périmée; ne pas demander une décision Owner sur ces anciennes empreintes.

### Templates Phase 4 créés en lecture contrôlée

Trois IDs inédits ont été préparés avec `prepare-manifest` depuis le checkout propre `fc8a314`. Cette commande n’a pas réservé d’essai et n’a pas changé l’Owner decision. Les fichiers existants n’ont pas été écrasés.

| Cas | ID Phase 4 | SHA-256 exact | Source fingerprint | Controller fingerprint | État |
|---|---|---|---|---|---|
| Newmark | `wp12a-newmark-20261027-p4-fc8a-01` | `bfd557c991a73a6f77b100aa3bdaf67e6f86562157f40b31682d8025cb6e6302` | `65e4078b1735de9adb258d1438fed39dcd69c1b68fa3560afb69896da60bdff8` | `ba98996f9167fdbd02b6bb0af882f8c34ac8cc5c15205c2634c3ecc25765dd26` | `PREPARED_NOT_AUTHORIZED` |
| Harmonique | `wp12a-harmonic-20261027-p4-fc8a-01` | `b52a984355dae9fb7729a25a694ddec22c193470539ea100e848dbec99d572c8` | `bd65535cfeaff0af932fb33e556ded5c1762f2dd90a5467793bdc01c6daca50c` | `ba98996f9167fdbd02b6bb0af882f8c34ac8cc5c15205c2634c3ecc25765dd26` | `PREPARED_NOT_AUTHORIZED` |
| Accélération de base | `wp12a-base-motion-20261027-p4-fc8a-01` | `c9a4f225133fbe5f74749ec2a187018c7000ec91f79c1a006dc8b4a904d07a00` | `969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6` | `ba98996f9167fdbd02b6bb0af882f8c34ac8cc5c15205c2634c3ecc25765dd26` | `PREPARED_NOT_AUTHORIZED` |

Tous trois lient le même worktree source propre `E:\QFSolverAgents\wp12-dynamics` (branche et HEAD détaillés §1), le mandat `DEVELOPMENT_AUTONOMOUS-WP12-DYNAMICS-2026-10-26-v1`, une tentative par processus, plafond de 10 par nodeid et 130 total, 300 s, 1 cas par tentative, DDL 1/3/1. Ressources : RSS mesurée souple 4 096 MiB, 16 processus, sorties 64 MiB au total / 32 MiB par flux, temporaires 512 MiB, archives 256 MiB. Les templates sont liés au contrôleur propre du checkout ci-dessus; ils ne sont pas prêts à être passés au launcher configuré actuellement sous `E:\QFSolverAgents\wp12-policy-final`, et ils deviendront périmés si la politique est modifiée pour réinscrire WP07.

Aucun manifest ne sera préparé pour le quatrième cas avant l’approbation et l’inscription append-only WP07. Les quatre templates finaux devront être recréés après stabilisation conjointe de la politique et du contrôleur de lancement. Aucun Owner decision `OWNER_AUTHORIZED` n’a été écrit.

## 5. Ledger et budget cumulé

Ledger consulté en lecture seule : SHA-256 `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`. Il n’a pas changé pendant la préparation des trois nouveaux templates; aucun des trois nouveaux IDs n’y figure.

| Nodeid | Tentatives historiques (tous enregistrements) | Résultats ledger | Plafond / reste avant une nouvelle décision |
|---|---:|---|---|
| Newmark | 3 / 10 | `PASS`, `PYTEST_FAILED`, `PASS` | 7 restantes par nodeid |
| Harmonique réduit | 1 / 10 | `PASS` | 9 restantes |
| Accélération de base | 1 / 10 | `PASS` | 9 restantes |
| WP07 historique | 0 / 10 | aucun record; refus fingerprint avant réservation | 10 restantes |
| **Campagne dynamique** | **5 / 130** | aucun nouvel essai Phase 4 | **125 restantes**, sans autorisation nouvelle |

Ces comptes ne donnent pas le droit d’exécuter. Toute tentative doit être décidée avec son propre manifeste exact. Une assertion échouée, un timeout, une interruption, un écart d’identité ou une impossibilité d’archiver impose l’arrêt; aucune relance implicite. Préserver toute preuve, y compris en cas d’échec.

## 6. Vérifications Phase 4, sans calcul scientifique

| Contrôle | Résultat observé |
|---|---|
| PR #38 intégrée au HEAD canonique | `PASS`; état GitHub `MERGED`, merge commit exact `fc8a314…` |
| Diff de politique et fichiers contrôleur depuis `d64e6036` | inchangés |
| Empreintes des quatre nodeids, candidat et source `630d22b` | trois inscriptions actives concordent; le nodeid WP07 historique concorde sur le contenu courant mais son enregistrement actif reste stale |
| Tests synthétiques autorisés (MPC/RBE, archivage, DTO, politique) | **37 PASS / 0 FAIL** |
| Collect-only des quatre nodeids scientifiques | **4 collectés / 0 exécuté** |
| Ruff, py_compile, JSON policy | PASS |
| Réinscription ou modification de politique | NOT_RUN |
| Manifestes WP07 historique / OWNER_AUTHORIZED Phase 4 | NOT_PREPARED / NOT_AUTHORIZED |
| FEM, modal, harmonique, Newmark, réservation ledger | **NOT_RUN / aucune réservation** |

Le succès des tests synthétiques est un résultat de développement borné, pas une qualification scientifique. Les résultats historiques Newmark/harmonique/base restent rattachés à leurs HEAD, manifests et décisions d’origine. G03, MITC4, WP-D01, l’ancien échec WP07 et tous les autres négatifs demeurent inchangés.

## 7. Décisions Owner, arrêts et clôture proposée

### Décisions à séparer

1. **Réinscription WP07** : approuver ou refuser l’ajout append-only du fingerprint `969dd027…` dans `wp12_dynamics`, avec conservation vérifiée de l’entrée `6db5…` et de l’échec historique. Cette décision n’autorise pas un calcul.
2. **Exécution Newmark** : décision distincte liée au SHA manifeste final après synchronisation du launcher; le template Phase 4 courant est `bfd557c9…` mais ne doit pas être approuvé tant qu’il est lié à un contrôleur différent du chemin de lancement prescrit.
3. **Exécution harmonique** : décision distincte, liée au manifeste final recalculé; template courant `b52a9843…` sous la même réserve.
4. **Exécution accélération de base** : décision distincte, liée au manifeste final recalculé; template courant `c9a4f225…` sous la même réserve.
5. **Exécution WP07 historique** : après la décision 1, produire un manifeste inédit sous le fingerprint contrôleur stabilisé; demander ensuite une décision Owner distincte sur son SHA-256 exact. Elle n’est pas encore disponible.

Chaque décision d’exécution doit lier l’ID et SHA exacts du manifeste, nodeid, source HEAD/tree/fingerprint, contrôleur, worktree, budget, oracle, critères et sortie. Les décisions historiques `OWNER_AUTHORIZED` ne sont pas transférables.

### Conditions d’arrêt

Ne rien exécuter si le checkout scientifique, le contrôleur partagé ou la politique diverge du manifeste; si l’entrée WP07 n’est pas active au fingerprint courant; si un nodeid ne collecte pas exactement; si le manifeste n’est pas reconnu `OWNER_AUTHORIZED`; si une tentative est déjà réservée; ou si les caps de temps, sorties, processus ou archivage ne sont pas respectés. Ne pas corriger un seuil après échec.

### Proposition de clôture bornée

Après éventuelles quatre exécutions autorisées, conserver les pass/fail individuels comme résultats de développement, rapprocher les observables avec les oracles déclarés, et obtenir un Owner disposition distinct. Une éventuelle clôture de WP12-A serait limitée aux quatre sentinelles et aux contrats testés, sans requalifier les historiques, sans fermeture de WP12/WP13, et sans prétention de validation physique générale. Jusque-là, `WP12=OPEN` et `WP12A_FOUR_CASES_PREPARED_OWNER_DECISION_PENDING`.


## Mise à jour après décisions Owner — quatre cas prêts à décision

L’Owner a approuvé la désignation du contrôleur propre C: et la réinscription append-only WP07. Ce bloc supersède les passages antérieurs qui indiquaient une inscription ou un quatrième manifeste encore en attente. Les preuves historiques et les anciens manifests restent intacts.

### Contrôleur stabilisé

- Launcher canonique désigné : `C:\Users\fari\.codex\worktrees\wp12a-phase4-canonical\qf_solver\scripts\development_autonomous.py`.
- Branche : `emptiesvoids-cloud/wp12a-canonical-controller`.
- HEAD : `8d436639e01df69caebf3dd7091d019aa002a3a2`; tree `5f5cffc470246b1e39006cf8ead9a06d3928273f`; checkout propre.
- Controller fingerprint définitif pour cette identité : `4fdf219b0ffae811ea5ebeb9b73c791270192379cb9fdc3e60b68457622be931`.
- SHA-256 runner `e307547a47e7d1c58224eb74a52211c47bc4270a86e875a6af0d56496bfc4500`; plugin `9b8fd647434469b1f6e26085d148bb81f22d5a87b4dbaac11c087173e5577df5`; politique `d0c148f74f56559a180ff23c03220bf906a2bf45285901b21730904b337412a5`.
- AGENTS.md pointe maintenant explicitement vers ce launcher. Le changement est dans la [PR brouillon #41](https://github.com/emptiesvoid-cloud/QF_solver/pull/41); aucun merge n’a été effectué.
- Le checkout historique `E:\QFSolverAgents\wp12-policy-final` reste intact à `4bf52792f46988b84fecf11ebe3bd5fe078975ef`, avec sa modification locale de politique. Il n’a pas été utilisé, réinitialisé ni écrasé.

Tout changement futur de HEAD, tree, chemin, runtime, runner, plugin ou politique modifierait l’identité du contrôleur et invaliderait les manifests ci-dessous. Si PR #41 est fusionnée avant l’exécution, recalculer l’identité et préparer de nouveaux manifests.

### Réinscription append-only WP07 effectuée

Le contrôleur officiel a recalculé `969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6` sur le worktree source propre `E:\QFSolverAgents\wp12-dynamics`, HEAD `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66`, tree `a6bcf6a3cea4bdc9ab17adcf53ce2151a2bc4758`.

`register-nodeid` a ajouté la révision 2 dans le scope existant `wp12_dynamics`, avec 1 DDL, 300 s et la justification Owner approuvée. L’ancien enregistrement `6db5b4597252082012fa38b1ed5cba02190562746556d5eabd1f74a256e0f8da`, son HEAD `e64493e…`, le FAIL historique et tous les reçus sont préservés. L’allowlist reste inchangée à 13/13. La source `solveur`, l’oracle, les tolérances et les critères n’ont pas été modifiés.

### Quatre manifests Phase 4 préparés

Les manifests suivants ont été créés après le commit final de la branche contrôleur à approuver. Chacun est `PREPARED_NOT_AUTHORIZED`; `owner_decision.status=NOT_AUTHORIZED`. Aucun n’est une autorisation ou une réservation. Ils lient le même source HEAD/tree et le contrôleur ci-dessus.

| Décision d’exécution Owner distincte | Nodeid | ID du manifest | SHA-256 à approuver exactement | DDL | Limite |
|---|---|---|---|---:|---|
| 1 — WP07 harmonique historique | `tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames` | `wp12a-wp07-harmonic-20261027-p5-8d4366` | `84e24e2f0aae4bacc7e101005bdb1e3e8ea52a13dd87eb5d7331263a9657808d` | 1 | 1 exécution demandée, 300 s maximum |
| 2 — Newmark | `tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | `wp12a-newmark-20261027-p5-8d4366` | `c49303a09ec8c88ed9ec7ac4f2715cc61d9ca861e432568234e8a96ab06e9413` | 1 | 1 exécution demandée, 300 s maximum |
| 3 — Harmonique réduit | `tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation` | `wp12a-harmonic-20261027-p5-8d4366` | `5aa236d0b6ec98295e9debad7037c2d5515258c43c6036dbdf15a03b64fe4588` | 3 | 1 exécution demandée, 300 s maximum |
| 4 — Accélération de base | `tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` | `wp12a-base-motion-20261027-p5-8d4366` | `63033d80f5c3700f9cfc524dc9c871dc71bc8dcd3572cce76a2e51e3e8833ddf` | 1 | 1 exécution demandée, 300 s maximum |

Les limites supérieures du mandat restent 10 tentatives par nodeid et 130 au total; le choix demandé ici est une première exécution par cas. RSS 4 096 MiB est une observation souple; 16 processus, sortie totale 64 MiB / 32 MiB par flux, temporaire 512 MiB, archive 256 MiB. Une divergence d’identité, un statut différent de `OWNER_AUTHORIZED`, une réservation antérieure, un dépassement de limite ou un échec d’archivage impose l’arrêt.

Le SHA du ledger après la réinscription et la préparation est toujours `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`; aucun des quatre nouveaux IDs ne figure dans le ledger. Il reste cinq tentatives historiques sur 130; aucune tentative Phase 4 n’a été lancée.

### Prochaine action et clôture

L’étape suivante est d’obtenir **quatre décisions Owner séparées**, chacune approuvant uniquement le nodeid, l’ID et le SHA-256 indiqués dans sa ligne. Aucune décision ancienne ne se transfère. Après validation des quatre états `OWNER_AUTHORIZED` par le contrôleur, les cas pourront être lancés séparément et séquentiellement avec le launcher épinglé; conserver toutes les sorties, même en cas d’échec.

Aucun test synthétique ni collect-only n’a été relancé après l’inscription et la préparation des manifests; ces opérations ont validé la configuration et n’ont exécuté aucun solveur. Les 37 tests synthétiques PASS et les quatre nodeids collectés mentionnés plus haut correspondent au contrôle antérieur sur le candidat `fc8a314`. La campagne scientifique reste à faire et aucun statut de qualification ne change. WP12 reste `OPEN`; une éventuelle clôture WP12-A serait bornée aux quatre sentinelles et soumise à disposition Owner après résultats.
