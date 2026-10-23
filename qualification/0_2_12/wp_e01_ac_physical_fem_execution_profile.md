# WP-E01-AC — Profil d’exécution FEM physique sécurisé

## Résultat exécutif

WP-E01-AB a bien été bloqué par le garde `test/no-FEM` : COLLECT a accepté 17 nœuds; RUN a donné 16 PASS et 1 FAIL, le seul échec étant `SolverExecutionBlockedError` avant la préparation du solveur et avant l’assemblage. Aucun calcul FEM physique ni coefficient Armijo physique n’a été produit. AC conserve ce garde sans le modifier.

AC livre un descripteur fermé et un validateur de politique sans capacité de lancement. Le profil est volontairement `PREPARATION_ONLY`; aucun worker physique ni superviseur AC de RUN n’est présent. Les contrôles ont simulé 1 profil de préparation accepté et 21 entrées de sécurité refusées (22 cas). Cela valide uniquement des décisions de schéma/politique, pas un chemin FEM.

**Décision : `WP_E01_PHYSICAL_EXECUTION_PROFILE=NOT_READY`.** `COLLECT=NOT_RUN`, `RUN=NOT_RUN`, calcul FEM `NOT_RUN`. La préparation statique du descripteur a été vérifiée; une exécution ne peut pas être autorisée par ce travail.

## Identité et éléments historiques préservés

- Worktree : `C:\wpc01-frictionless-public-integration-wt\wp-e01-x`
- Branche : `codex/wp-e01-x-newton-test-remediation-20261021`
- Baseline AB : `7ab608dca34f62c1ac1dca5803f273164660a52b`
- Arbre baseline : `f3a54eb399e3a2b2723dcb51cb7c56198b2b424d`
- Origine : `https://github.com/emptiesvoid-cloud/QF_solver.git`
- Rapport AB : [wp_e01_ab_armijo_physical_backtracking_report.md](wp_e01_ab_armijo_physical_backtracking_report.md), SHA-256 `ffbd7095b7889939b238d82a0e8c410b1d831a2d4c4c7046ebc7a38e5f9e91f8`.
- Résultat AB conservé : 17/17 collecte acceptée; 16 PASS / 1 FAIL; aucun solveur ni assemblage commencé.
- Preuves AA et AB préexistantes non modifiées.

## Diagnostic de la frontière de sécurité

Le chemin observé est :

```mermaid
flowchart LR
  A[Superviseur AB] -->|pytest + no-native| B[Processus enfant]
  B --> C[pytest / conftest]
  C --> D[Nœud physique AB]
  D --> E[NonlinearStaticSolver.solve]
  E --> F[guarded_solver_entry]
  F --> G[require_solver_execution_allowed]
  G -->|pytest présent / latch / marqueur no-native| H[SolverExecutionBlockedError]
  H -. avant .-> I[Préparation Newton]
  I -. avant .-> J[Assemblage FEM]
```

1. Le décorateur `guarded_solver_entry` vérifie l’autorisation avant le corps de `NonlinearStaticSolver.solve`.
2. `solver_execution_is_forbidden()` refuse notamment si pytest est chargé, si `PYTEST_CURRENT_TEST` existe ou si un marqueur test/no-native est actif. Le latch `_NO_NATIVE_RUNTIME_LATCH` mémorise également la situation au chargement du module.
3. Le superviseur AB exécute pytest avec `QF_SOLVER_NO_NATIVE_EXECUTION=1` et `WPC01_NO_NATIVE_EXECUTION=1`. C’est le contrat normal du profil offline; il explique le refus observé et ne doit pas être contourné.
4. La source protège aussi plusieurs chemins d’analyse/solveur/backend par le même décorateur. La revue de la fermeture du nœud n’a trouvé aucun chemin alternatif déclenché par le test qui exécuterait le solveur avant ce garde.
5. Le garde est une barrière d’environnement test/no-FEM, pas un mécanisme universel d’autorisation : un programme Python ordinaire hors pytest et sans marqueurs peut appeler l’API. Une future exécution physique exigerait donc un superviseur fixe et un manifeste explicitement autorisé; elle ne peut pas être obtenue en nettoyant l’environnement pytest.

La fermeture statique identifiée utilise Python, NumPy et SciPy (dont extensions compilées), plus le code Python de maillage/contact. Aucune initialisation Gmsh, backend FEM natif, worker ou sous-processus de calcul n’a été trouvée dans le chemin épinglé. Le Job Object limite les processus et la mémoire, mais ne fournit pas à lui seul une isolation réseau, une ACL de fichiers, ni un plafond CPU.

## Profil fermé et politique préparée

Descripteur : [wp_e01_ac_physical_fem_profile.json](wp_e01_ac_physical_fem_profile.json).

- ID exact : `E01_PHYSICAL_FEM_BOUNDED`.
- État : `PREPARATION_ONLY`, `execution_authorized=false`, Owner GO `NOT_GRANTED`.
- Cible décrite : le seul nœud `tests/unit/test_wp_e01uvw_newton.py::test_production_contact_newton_rejects_full_step_then_accepts_reduced_step`, classé `NUMERICAL_UNIT`.
- Worker : `null`, `NOT_IMPLEMENTED`; le descripteur ne peut pas démarrer de calcul.
- Sources : 199 chemins/hash couvrant la fermeture enregistrée et le validateur de politique AC. Chaque fichier a été vérifié octet pour octet; toute divergence invalide le profil.
- Limites décrites : un TET4, 4 nœuds, 12 DDL, un incrément, au plus 25 itérations Newton et 9 essais Armijo par itération; 256 MiB mémoire commitée par processus et Job; 120 s murales par phase; 100 s CPU proposés.
- Processus : un worker, aucun descendant, assignation Job avant reprise, kill-on-close, pas de breakaway ni retry. `pytest_in_run=false`.
- Sorties déclarées sous `qualification/0_2_12/wp_e01_ac_execution/`.
- Le manifeste affirme explicitement que l’isolation réseau OS et les ACL de fichiers ne sont pas garanties.

Le validateur [wp_e01ac_profile_policy.py](../../experiments/wp_e01ac_profile_policy.py) n’importe ni solveur, pytest, subprocess, socket, API Windows ou backend natif. Il ne possède aucune fonction de lancement et n’accepte que le mode de préparation. Il exige le digest du profil comme argument externe, un schéma fermé, le jeu exact des champs d’identité dépôt, la correspondance complète du source-map, la cible et classification exactes, les plafonds et la politique processus. Il rejette les clés JSON dupliquées, les champs manquants/supplémentaires, les différences de source, les types booléens substitués à des entiers, les identités incomplètes et les phases RUN/autorisation implicites.

La politique n’accorde pas d’autorisation en lisant l’environnement. Le profil n’est pas signé : il ne devient pas autorisé parce qu’il contient un champ d’autorisation. Un futur GO doit fournir une empreinte externe et l’identité exacte du worker/superviseur, puis faire l’objet d’une nouvelle revue. Les changements du code épinglé ou du manifeste invalident le gel.

## Vérifications exécutées (sans FEM)

- `python -m experiments.wp_e01ac_profile_policy` : **1 accepté, 21 refusés, 22 décisions simulées**.
- Refus couverts : schéma/champ absent, source modifiée, mauvais nœud/module/classification, worktree/origine/branche/HEAD/tree erronés, profil altéré, mémoire ou CPU hors plafond, trop de processus, phase RUN sans GO, worker arbitraire, maillage hors bornes, dimensions booléennes trompeuses, clés JSON dupliquées et état dépôt incomplet.
- Profil réel validé avec son propre digest externe fourni au contrôle : mode `PREPARATION_ONLY`, `execution_authorized=false`; les 199 entrées du source-map correspondaient aux octets des fichiers.
- AST parse et compilation en mémoire : **199 fichiers Python** épinglés, réussis.
- Analyse AST du validateur : imports/capacités de lancement absents.
- `git diff --check` : réussi.
- Aucun pytest, collecte, solve, assemblage FEM, Gmsh, backend, worker ou lancement de sous-processus de campagne.

## Limites et décisions avant une exécution future

Le Job Object AB a démontré l’assignation avant reprise, les plafonds mémoire commités de 256 MiB, le watchdog mural de 120 s, le kill-on-close et la vérification du nettoyage. Les mesures historiques AB étaient 75 427 840 octets durant COLLECT et 108 294 144 octets durant le RUN bloqué; elles ne sont pas une mesure d’un solveur réussi.

Le plafond de 100 s CPU dans le descripteur n’est pas appliqué ni relu par le superviseur AB. Il reste une exigence proposée, pas une garantie. Les limites de scénario sont aussi déclaratives dans ce profil inerte. Réseau et ACL ne sont pas isolés par le Job Object. Ces points, ajoutés à l’absence de worker AC, interdisent le statut prêt à exécuter.

Le nœud actuel importe pytest et déclenche donc le latch no-FEM. La conception future doit séparer les phases :

1. **GO-COLLECT distinct** : collecte uniquement du nœud exact sous pytest/no-FEM, sans exécuter le corps; reçu d’allowlist exact obligatoire.
2. **GO-RUN distinct** : worker non-pytest fixe, source et entrée explicitement épinglées, vérification HEAD/tree/origine/branche, manifeste, reçu COLLECT et limites avant tout import du solveur; création suspendue, assignation Job puis reprise. Aucun argument de cas libre, aucun enfant, aucun retry. Si le garde refuse le worker, arrêt échoué fermé, sans modification du garde.
3. Appliquer et vérifier réellement le plafond CPU ou retirer ce plafond de la promesse; justifier les limites sans les augmenter par défaut. Définir le contrôle réseau/écriture effectif ou conserver explicitement ces limites comme non isolées.
4. Publier reçus, logs, mesures et inventaire des processus avant fermeture du Job; timeout/erreur termine tout le Job et interdit reprise automatique.

Le futur test doit conserver au minimum le résidu avant recherche, direction Newton, alpha initial, chaque alpha essayé, mérite et motif d’acceptation/rejet, état constitutif d’essai et état accepté, puis résidu après acceptation. Le résultat recherché — rejet physique de `alpha=1`, acceptation d’un alpha réduit — exige une exécution distinctement autorisée; aucune valeur Armijo n’est actuellement observée.

## Revue indépendante

Revue read-only effectuée par un reviewer distinct. **Aucun P0.** Les P2 initiaux (égalité bool/int et identité dépôt incomplète) sont corrigés; le reviewer a vérifié les 199 source pins. Il demeure des blocages P1 de préparation d’exécution : aucun worker/superviseur AC, plafond CPU non appliqué, et isolation OS réseau/ACL absente. Ils ne révèlent pas une faille dans le descripteur inerte, mais empêchent le statut prêt à exécuter. Le reviewer a confirmé que le profil doit rester `NOT_READY`, que COLLECT et RUN demandent des autorisations distinctes, et que le worker futur ne doit ni importer le test pytest ni contourner le garde.

## État

| Indicateur | État AC |
|---|---|
| `WP_E01_PHYSICAL_EXECUTION_PROFILE` | `NOT_READY` |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `INCREMENTAL_NEWTON` | `VERIFIED_BOUNDED` — portée historique AA uniquement |
| `GENERAL_SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `AUTHORITATIVE_INTEGRATION` | `PENDING` |
| `PUBLIC_RELEASE` | `NOT_AUTHORIZED` |
| `COLLECT` | `NOT_RUN` |
| `RUN` | `NOT_RUN` |

## SHA-256 et Git

- Garde `src/solveur/core/execution_guard.py`: `fe8624948dab00db74d45da9b86f0cbaf128ea590a16689b5aa4bee99b7c6364` (inchangé).
- Superviseur AB : `f644c6f75bad659d69dff15f33d6618029b5aec663fca17b4e1d106feff29063` (inchangé).
- Helper Job Object : `76e71e833280b92c2478ec8aed187a473bf5f4002e5983c2386f37b58e9bbe62` (inchangé).
- Newton : `678ff73804d721cbe2363b8ec37397ab2bddc18a0baee4cd051c86f834098dc5`.
- Contrôleur Armijo/contact : `0cc106cabe08ff9009d3983449d4e713ae9a51658ecb8ea119e9e879f1809726`.
- Matériau Hencky : `b318dad553073f848b96528c61589ab2015c1eb1dd8fa52cb0bd52d13b09eab2`.
- Driver Newton expérimental : `1a24046913a4544aadba8dbec715f796ef56069f3cdbe813fd871a630950ffb0`.
- Test physique : `973df15eb8fffb8a9fb3af7fcb0365485ce3c582147159556ea1ec2eac3f6e7e`.
- Registry : `8b9e1122c9c014a3e1b79a44320f12f8e9b0611b40535a82e07986b3b5e72c17`.
- Validateur de politique AC : `BE16A84BFC32B76789052597CD833754F4CB847293D68018CBA1DDD1AF461970`.
- Profil AC JSON (inclut les 199 source pins) : `1FACB43FA43A9DFC89436897AD83B097A5ACE8D8A952AA714CB8FA28FD949D70`.
- Rapport : empreinte à recalculer après consignation de la revue finale.

Aucun fichier de production ni le garde-fou historique n’a été modifié. Les seuls nouveaux fichiers AC sont le validateur de préparation, le descripteur inerte et ce rapport.
