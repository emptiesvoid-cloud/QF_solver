# WP-E01-AV — Diagnostic et correction ciblée du RUN Newton–Armijo

## Conclusion

Le RUN AU reste **FAIL** et toutes ses preuves d’origine sont préservées. La cause démontrée est un défaut d’instrumentation dans le worker AG : son observateur d’assemblage remplaçait le dictionnaire `contact_diagnostics` appartenant à la contribution Newton par un dictionnaire privé. L’assemblage GF4 écrivait bien l’état d’essai complet dans le dictionnaire privé; la contribution, qui lisait son propre dictionnaire après retour d’assemblage, ne le recevait donc jamais.

Le correctif du worker transmet maintenant le dictionnaire fourni par l’appelant à l’assembleur et observe ce même objet. Aucun état de contact n’est créé artificiellement. Le garde de complétude de production reste actif; la validation d’état précède toujours le commit.

Le test unitaire ciblé passe (**9 passed**), Ruff et les contrôles syntaxiques passent. La revue indépendante finale ne relève aucun P0/P1/P2 sur le changement ciblé. **Aucun Docker, COLLECT, RUN, worker FEM ou calcul scientifique n’a été lancé après cette correction.** Le nouveau gel est une identité source statique; l’image Docker historique est périmée par rapport au worker et ne peut pas servir à une exécution de ce gel.

## Identités et préservation

- Dépôt : `https://github.com/emptiesvoid-cloud/QF_solver.git`.
- Branche : `codex/wp-e01-ag-docker-native-fem-vnv`.
- HEAD initial : `0b044b3b2787c41a3b06c596d2b4dac914df88ca`.
- Commit source AV : `bdec1cb5874d0b03ddd977263679336cd0a8e7c4`.
- Tree du commit source AV : `da09256da0e7b9fb4fa10ae653f6c06e04898e9f`.
- Le commit initial AU, ses manifestes, le verdict FAIL, les reçus, journaux et le dossier externe de preuves n’ont pas été modifiés.
- Le manifeste RUN AU reste lié à SHA-256 `ff91d01325b99eaef7ea5a56b9c64811a270902d08a14eac00daabe20e26f243`.
- L’image `sha256:4dd620505509972e6b8520185a43cae46306e1c170b3dc0719d409cca332c2d5` est enregistrée comme **STALE_FOR_THIS_SOURCE_FREEZE** : elle ne contient pas le worker et le registre corrigés.

Gel source sans autorisation d’exécution : [wp_e01av_source_freeze.json](wp_e01av_source_freeze.json), SHA-256 `4258fc2657f0f2832c3b515881b03fdb9814a0e01d1aea822775b8e83e3a3c0e`. Il contient 533 pins correspondant exactement à l’inventaire source attendu; les 533 valeurs ont été relues contre les fichiers présents et aucun écart ne subsiste. Le manifeste déclare explicitement `collect_go_id=null`, `run_go_id=null` et Docker `NOT_RUN`.

## Diagnostic de la cause

### Chemin de l’état

1. Le scénario canonique est `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA`; son modèle sélectionne `gf_contact_v1`.
2. `assemble_gf_contact` (`src/solveur/contact/gf_fe_contact.py`) renvoie ses diagnostics, dont `gf_trial_contact_state`.
3. `_MaterialLoadControlContribution.evaluate` (`src/solveur/core/nonlinear/load_control.py`) passe `self.contact_diagnostics` à l’assembleur, puis lit `gf_trial_contact_state` dans **ce même** dictionnaire pour former `last_trial_contact_state`.
4. L’ancien wrapper `capture_assembly` du worker copiait `kwargs`, puis remplaçait `contact_diagnostics` par un dictionnaire local. L’assembleur remplissait ce dictionnaire local et le worker enregistrait ces données, mais le dictionnaire conservé par la contribution restait incomplet.
5. Le callback de finalisation vérifie que l’état d’essai est complet avant d’écrire `trial.contact_state`. Il lève `NumericalConvergenceError` si cet invariant n’est pas respecté.
6. Dans le driver, la finalisation précède `transaction.commit()`. Le chemin d’échec annule la transaction; aucun commit d’état incomplet n’est effectué.

**Champ manquant dans le dictionnaire de la contribution :** `gf_trial_contact_state`. Le payload GF4 lui-même était produit par l’assembleur; il était perdu au passage entre le wrapper d’observation et le consommateur. Le défaut est classé **WORKER / instrumentation et contrat de sortie**, confiance élevée. Aucun défaut des équations, de l’assemblage GF4, de Newton ou de la loi de contact n’est démontré.

Le texte d’erreur historique dit « Candidate B » alors que le scénario gelé est GF4. C’est un libellé générique trompeur du garde de finalisation; le scénario est déterminé par le manifeste et `gf_contact_v1`. Le code de production et ce libellé n’ont pas été modifiés.

### Pourquoi le faible mérite ne suffit pas

Le mérite Armijo mesure le comportement du résidu pour les essais de pas. Il ne remplace pas la validation de l’état constitutif/contact nécessaire à l’acceptation du pas de charge. Le driver valide cet état avant commit, y compris lorsqu’un critère de convergence ou d’acceptation floor-aware conduit à la finalisation.

La trace prouve les décisions de recherche linéaire ci-dessous; elle ne fournit pas un résultat de solveur complet. Le champ `converged_under_frozen_relative_tolerance=false` du reçu est un contrôle d’acceptation du worker : après l’exception, aucun résultat `SolveResult` ni résidu relatif final exploitable n’était disponible. Ce booléen n’est donc pas une mesure indépendante d’échec de convergence. Le branchement exact (critère relatif ordinaire ou acceptation floor-aware) et la valeur du résidu relatif final sont **NOT_RECORDED**. Rien ne justifie de classifier cet événement comme divergence de Newton.

## Résultats numériques AU conservés

Les deux replays configurés dans l’unique opération RUN ont produit la même histoire numérique :

| Étape | Mérite initial (N) | Essais Armijo | Décision |
|---|---:|---|---|
| 1 | 0.8660254037844386 | α=1 : 13.043364313475424; α=0.5 : 3.7854140850566926; α=0.25 : 0.6016607470874248 | rejets α=1 et 0.5; acceptation α=0.25 après 2 réductions |
| 2 | 0.6016607470874248 | α=1 : 0.08581211766875732 | acceptation α=1 |
| 3 | 0.08581211766875732 | α=1 : 0.00014075840786308667 | acceptation α=1 |
| 4 | 0.00014075840786308667 | α=1 : 2.182020284783493e-12 | acceptation α=1 |

Les deux replays terminent ensuite avec `Candidate B contact assembly did not provide a complete trial contact state.`; ils n’établissent ni équilibre global, ni commit, ni réaction finale. Valeurs observées : `commit_count=0`, état accepté retourné absent, contrôle `single_accepted_commit=false`, contrôle `final_load_factor_is_one=false`. Le contrôle d’immutabilité des états acceptés et d’essai après les probes est vrai dans la trace historique. Le driver rollbacke le trial lorsque cette erreur de convergence remonte.

Verdict scientifique historique : **RUN FAIL**; les observations de backtracking sont exploitables dans leur portée, mais aucun résultat Newton–Armijo convergé n’est certifié. Ce verdict n’est pas reclassé.

## Comparaison des replays et sérialisation

Le reçu historique brut portait `deterministic_replay_equal=false`, car il comparait aussi des durées variables. Après application, en post-traitement seulement, de la projection du worker corrigé, les signatures des deux objets RUN complets sont identiques :

`c6ca95e8929a323f685103f8b14ebadd594c230d4f8e8be6e2fbe21a8e8f360a`

Cette comparaison retire uniquement les champs de durée recensés dans `_OPERATIONAL_TIMING_FIELDS` (durées d’assemblage, de solve linéaire, de recherche linéaire, de noyau/scatter, de setup, ainsi que durées murales et durées GF4). Les valeurs chronométriques originales restent dans les reçus et les journaux; elles ne sont pas réécrites. Les autres champs du run complet — résidus, réactions si présentes, historique Armijo, états, commits, contrôles, diagnostics et erreurs — restent dans la signature. Les tests vérifient à la fois que changer chaque durée ne modifie pas la signature et que changer des valeurs scientifiques la modifie.

Le reçu ne peut être `PASS` que si les deux replays existent, sont chacun `PASS`, ont des signatures égales, et que l’ensemble exact des contrôles scientifiques gelés est présent avec chaque valeur littéralement `true`. Aucun critère numérique ni seuil n’a été changé.

## Correction appliquée

Fichiers modifiés, sans changement de `src/` :

- `experiments/wp_e01ag_docker_worker.py` : nouvel observateur `_observe_assembly` qui réutilise l’objet `contact_diagnostics` fourni par la contribution; dictionnaire privé seulement si aucun sink n’est fourni. Ajout du gate fermé sur les contrôles gelés, de la signature des données complètes après retrait des durées opérationnelles, et du constructeur de reçu RUN qui conserve les diagnostics et durées brutes. Aucun état n’est fabriqué et aucun assemblage physique n’est changé.
- `tests/unit/test_wp_e01ag_worker_state_capture.py` : tests synthétiques sur le passage du sink complet, l’absence d’état fabriqué, les refus, les contrôles d’acceptation, la comparaison de replay et la conservation d’un reçu FAIL. Aucun solveur, modèle, maillage ou calcul FEM n’est construit.
- `tests/conftest.py` : classification `PURE_UNIT` conservée et hash du test mis à jour.

Empreintes :

| Fichier | SHA-256 |
|---|---|
| `experiments/wp_e01ag_docker_worker.py` | `7b8e0271e9b34c2613f40f44fca9fe76a001c5236be6cfb826861f5f031d8717` |
| `tests/unit/test_wp_e01ag_worker_state_capture.py` | `0a1102249fe7fcb5c62a130d319690d5448928ea0941e3a230fc120acf7c011a` |
| `tests/conftest.py` | `e25fa090326cd15d2d13f0516ba0d1c0d5ea07a5c7d09f780582d8ec8a2f1bf7` |
| `src/solveur/core/nonlinear/solver.py` (inchangé) | `678ff73804d721cbe2363b8ec37397ab2bddc18a0baee4cd051c86f834098dc5` |
| `src/solveur/core/nonlinear/load_control.py` (inchangé) | `bf9d4c8f443704d8db408b6f9c3c1dd27941877fc76e83b37d05b09bad9530b9` |
| `src/solveur/contact/gf_fe_contact.py` (inchangé) | `358ddeee37de89a301f2fdb7033c366e6b17824ff098ed6035a36b27efa11d98` |

## Vérifications et revue

- Test ciblé final : `python -m pytest -q -p no:cacheprovider tests/unit/test_wp_e01ag_worker_state_capture.py` — **9 passed in 0.56s**.
- Ruff : `python -m ruff check experiments/wp_e01ag_docker_worker.py tests/unit/test_wp_e01ag_worker_state_capture.py tests/conftest.py` — **All checks passed**.
- `py_compile` des trois fichiers et `git diff --check` — réussis.
- Vérification statique du gel : 533 pins, 0 mismatch; entrée test `PURE_UNIT` et hash concordants.
- Une tentative de test antérieure au résultat final a été conservée dans la chronologie : 9 skips quand le hash de registre était périmé; après actualisation, 8 pass / 1 échec dû à un `deepcopy` manquant dans le test synthétique; le fixture a été corrigé et le résultat final est 9 pass. Aucun de ces essais n’a exécuté de FEM.
- Revue indépendante, lecture seule et distincte : transfert du sink, refus d’état incomplet, gate d’acceptation et portée des signatures examinés; **aucun P0/P1/P2 résiduel**. Aucun Docker ou test n’a été lancé par le reviewer.

## Preuves AU archivées

Répertoire RUN conservé : `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag-evidence\WP-E01-AP-COLLECT-20261022-5D50B1E9A1A14B4EAB66EB4A2B849302\RUN`.

| Artefact | SHA-256 |
|---|---|
| `run_receipt.json` | `bc2aa0b42ea1473c405192eabe73c3c420292ca11003a1b53f988684a2fc8760` |
| SHA canonique interne du reçu worker | `0ca59924705a280cf0fd181709915a2bd8117ca4397102e1996aa6ddf715c5d8` |
| `host-receipt.json` | `34879489d4188db9e9017796ea4ad54f13bfeaa288c15263915b1d848a1f7aa4` |
| `host-receipt.pending.json` | `0b902e3a0ae471cc30baba0a5afac192ad339eda4cd29cef860626110322fdb5` |
| `docker-combined.log` | `254b4f630af5bb2addcc00520c6da1299dd65e97ae668935b90f081e2e96cf8a` |
| `worker.stdout.log` | `425dd4d08df32c9105d81f7adc6b4859bf9cb5828390b23c1e9394c6704bebc7` |
| `worker.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `container-config.json` | `54660b76b647dcabe3fc380c08e1c3edc7f28cead0fca58eb4848606d4e51c13` |

Le reçu hôte historique dit `REJECTED`, exit code `1`, `timed_out=false`, `oom_killed=false`, `worker_accepted=false`; nettoyage `REMOVED_CONFIRMED_NOT_FOUND`. La configuration Docker archivée indiquait réseau `none`, rootfs lecture seule, limites 1 GiB / 2 CPU / 64 PID, capacités supprimées et `no-new-privileges`. Ce sont des preuves de l’exécution AU, pas de la nouvelle image/identité source AV.

## Statut et prochaine étape

- Cause : **WORKER / instrumentation du sink d’état**, démontrée.
- Correctif ciblé : appliqué dans le worker; source de production inchangée.
- Tests unitaires ciblés : passés.
- Déterminisme : deux runs historiques identiques après retrait des seuls champs de durée; résultat global AU reste **FAIL**.
- Gel source : prêt, 533 pins vérifiés; image d’exécution périmée.
- `COLLECT=NOT_RUN`; `RUN=NOT_RUN` après correction.
- `PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`.
- Convergence globale, équilibre avec contact et qualification scientifique générale : non établis.

Prochain chemin minimal : reconstruire et inspecter une image Docker liée au commit source AV; émettre un nouveau manifeste/allowlist et un nouvel identifiant d’évidence; obtenir un GO-COLLECT distinct; vérifier la collecte; puis obtenir un GO-RUN distinct pour une unique campagne. Le GO AU est consommé et ne couvre pas cette nouvelle identité. Ne pas réutiliser l’image ou les manifestes RUN AU.
