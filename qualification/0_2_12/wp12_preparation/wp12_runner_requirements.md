# WP12-R — Exigences et état du runner contrôlé

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Ce document conserve le protocole préparatoire WP12-0 et constate l'implémentation WP12-R. Le runner vérifie les manifestes, exécute seulement des processus factices via SELF_TEST et refuse toujours EXECUTE. Cela ne constitue ni une autorisation de campagne ni une preuve scientifique.

## 1. Comparaison des mécanismes existants

| Mécanisme | Contrôles utiles observés | Limite pour WP12 |
|---|---|---|
| `scripts/development_autonomous.py` + `development_autonomous_policy.json` | Sélection de worktree/branche, nodeids enregistrés, inventaire source, origine de `solveur`, tentatives/ledger et journaux; limite de sortie capturée. | Runner de développement ciblé D01/C01/E01, pas un runner de qualification WP12. Les worktrees, scopes, branches, nodeids et budgets sont différents; RSS/process/temp/disk sont des observations périodiques souples, pas des limites OS. |
| `scripts/run_wpc02_ar_native_pytest.py` | Modèle de runner one-shot; vérification de manifeste/source, identité Git, refuse les résultats existants, journal de tentatives, timeout et suivi de processus. | Verrouillé sur anciens manifestes/sources N10/N13 et sorties C02; ne peut pas être rebondi sur le candidat WP12 et ne doit jamais écrire dans les archives N10. |
| `scripts/run_wp06_verification.py` et `scripts/record_wp05_gyro_evidence.py` | Orchestration historique de preuves rotor. | Les scripts écrivent dans des chemins gelés v0.2.11 et certains écrivent sans refus d'écrasement. Incompatibles avec une exécution future WP12 sans wrapper/sortie nouvelle revue. |
| `.github/workflows/quality.yml` | CI de PR/main, sélection de tests et couverture; utile en sentinelle logicielle. | Les runs CI ne sont pas actuellement présents pour le HEAD de base; le workflow n'émet pas automatiquement un manifeste scientifique WP12 ou des budgets par test. CI ne vaut pas qualification FEM. |
| `scripts/run_wp12_scaling.py` | Mesure ancienne de grandes tailles existante. | Le nom WP12 est réutilisé depuis v0.2.7; contrat/résultats dans l'espace 0.2.7. Pas un harness de performance v0.2.12. |

La préparation s'inspire des mécanismes forts ci-dessus sans hériter de leurs permissions, statuts, fichiers, sorties ou budgets.

## 2. Protocole requis avant tout lancement futur

1. **Décision d'autorisation** : Owner nomme un campaign ID, approuve le SHA-256 exact du manifeste et les limites numériques, essais, nœuds, environment et destination; aucun autre test n'est sélectionné implicitement. Chaque nouveau scope exige un nouveau manifeste.
2. **Identité source** : checkout dédié, commit et tree attendus, branche/ancestry précisés, index/worktree propres, aucun sous-module/modification non suivi non explicitement inventorié. Vérifier aussi l'origine réelle de `solveur.__file__`, le Python, les dépendances, les roues et les versions des bibliothèques natives.
3. **Nœuds exacts** : une commande enfant par nodeid explicite, pas de répertoire/module/suite globale. Les cas paramétrés ont leurs IDs résolus et approuvés avant le freeze; aucun `--collect-only` ne sert à deviner le scope après autorisation. Contrôler les tests réellement sélectionnés avant qu'un appel solver soit possible.
4. **Entrées** : calculer SHA-256 de chaque fixture, modèle, mesh, contrat et fichier de référence avant l'exécution; capturer la génération déterministe inline quand aucune fixture externe n'existe. Figer valeurs d'environnement, ordre, seeds et BLAS/OpenMP/MKL threads.
5. **Ressources** : valeurs explicites CPU, nombre de threads, mémoire, temps par nœud/campagne, espace temporaire/sortie. Les limites appliquées doivent être distinguées des seuils surveillés. Sur Windows, un polling RSS/descendants est soft; si une limite mémoire forte est un critère, utiliser une contrainte OS Job Object/container adéquate ou bloquer le lancement. Ne pas annoncer un plafond dur non imposé.
6. **Tentatives** : une seule tentative proposée par nodeid, aucune relance automatique. Toute nouvelle tentative exige un diagnostic et l'approbation d'une nouvelle hypothèse/version de manifeste. Un FAIL scientifique reste archivé, pas effacé par un PASS ultérieur.
7. **Destinations exclusives** : `qualification/0_2_12/wp12_evidence/<campaign_id>/<run_id>/`; créer uniquement si inexistant et refuser tout écrasement. Jamais `qualification/0_2_11`, un répertoire C02 gelé, ou un dossier de preuves partagé. En cas de collision, stopper.
8. **Journal et reçu** : copier manifeste et SHA-256, sources/fixtures, commande exacte, stdout/stderr avec plafonds, exit code, temps wall/CPU, RSS/peak observé, OS/process descendants, versions, seed, statut, raisons de skip/timeout, artefacts; produire inventaire SHA-256 signé/revu hors processus solver. Distinguer écriture atomique et garantie de durabilité.
9. **Arrêt sûr** : refuser mismatch de SHA/tree/source hash, dirty tree, origin inattendue, nodeids inattendus, fixtures modifiées, ressource inconnue, destination déjà présente ou manifeste non approuvé. À timeout/erreur environnement, terminer les descendants, sceller l'état partiel et sortir `NOT_RUN/INCONCLUSIVE` sans retry automatique.
10. **Interprétation** : enregistrer oracle et seuil gelés avant lancement; convertir aucun skip en PASS; les données brutes et échecs sont immuables. Pas de promotion de maturité/statut par le runner.

## 3. État préparatoire conservé

Les manifestes par lot gardent l'identité source proposée `00428adf…` et son tree `df4ec667…`; ils n'ont pas été réécrits. Les limites CPU/RAM/thread/timeout qui ne sont pas gelées par un contrat restent `null` et `PROPOSED — OWNER_APPROVAL_REQUIRED`; elles ne sont pas implicitement empruntées aux runners voisins. Les campagnes WP12-1 à WP12-4 n'ont pas une couverture complète d'empreintes pour tous les chemins listés; WP12-5 n'a ni nodeid/scénarios figés ni inventaire de hachages; WP12-6 n'a pas encore d'identité de commit final. La validation statique expose ces écarts. Aucun de ces six manifestes n'est autorisé.

## 4. Implémentation WP12-R

- `scripts/run_wp12_qualification.py` expose VALIDATE, SELF_TEST et EXECUTE.
- Les contrats et identités Git sont dans `scripts/wp12_runner/contracts.py`; journaux, reçus et chemins exclusifs dans `evidence.py`; supervision des seuls enfants factices dans `process.py`.
- Les manifestes d'exécution unitaires et les décisions Owner séparées ont des schémas JSON dédiés. Un statut `APPROVED` et une enveloppe Ed25519 structurellement correcte ne prouvent pas l'identité du signataire.
- L'exécution réelle reste désactivée par conception dans WP12-R. Aucun solveur, test QF, overlay C02, test rotor ni benchmark scientifique n'a été exécuté.
- Les tests autorisés sont isolés dans `tests/unit/test_wp12_qualification_runner.py` et ne doivent importer aucun module de calcul QF Solver.

Les détails d'utilisation, le modèle de confiance, les limites de confinement et les résultats de tests sont dans le [guide](wp12_runner_usage.md), le [modèle de sécurité](wp12_runner_security_model.md), l'[audit](wp12_runner_audit.md) et le [registre des écarts](wp12_runner_residual_gaps.md).

## Addendum WP12-R2

L'état R2 courant, les limites démontrées, les statuts R-01..R-11 et les décisions Owner restantes sont dans [wp12_r2_runner_security_review.md](wp12_r2_runner_security_review.md). Le schéma de décision Owner a été versionné en v2 pour inclure `scientific_identity`, `runner_identity`, `not_before_utc` et `expires_utc`; la signature est vérifiée uniquement contre un trust store public piné dans HKLM. Aucun trust store réel n'est configuré.

Le runner utilise désormais un Windows Job Object pour les seuls processus factices SELF_TEST. Les limites durement imposées sont le nombre de processus actifs, la mémoire agrégée lorsqu'elle est précisée et la terminaison à la fermeture du Job. Wall time est supervisé et les sorties sont plafonnées par le collecteur; aucun quota CPU dur, plafond de threads ou de stockage, ni isolation des permissions de fichiers n'est fourni.

Un ledger JSONL verrouillé relie chaque tentative à une chaîne SHA-256; il reste modifiable par tout acteur disposant des droits d'écriture. Les métadonnées d'environnement sont recueillies sans import QF/NumPy/SciPy et marquent les libraries réellement chargées comme non vérifiables. SYNC est un mode séparé, jamais déclenché par VALIDATE.
