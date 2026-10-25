# WP12-0 — Périmètre et critères de préparation

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## 1. Identité de préparation

Repository `emptiesvoid-cloud/QF_solver`; branche `emptiesvoids-cloud/0.2.12`; code cible proposé `00428adf38e9397340ac136f6f503a268eb671da`; tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. HEAD local et branche distante étaient identiques lors du contrôle initial. Le checkout était propre. Le code et les tests ciblés n'ont pas changé depuis l'identité de base du présent audit; les documents WP12-0 seront ajoutés dans un commit documentaire distinct. Toute modification ultérieure des sources ou tests invalide les identités de campagne et impose une nouvelle revue avant autorisation.

## 2. Frontière scientifique

WP12 vérifie sur une identité candidate gelée les formulations et comportements de v0.2.12 déjà retenus au WP00, la non-régression des routes supportées susceptibles d'être affectées par l'intégration, les limites contractuelles, ainsi que les performances effectivement promises. Il ne constitue pas une qualification générale de chaque capacité expérimentale.

Le périmètre doit conserver des verdicts séparés :

- **DYN** : systèmes préparés et identités physiques, excitations, bases modales, harmonique réduit, Newmark modal, accélération uniforme de base, diagnostics de troncature et récupération des contraintes D02 dans leurs domaines contractés.
- **NL** : lois et états WP08–WP10, tangent/équilibre Newton dans le périmètre borné, transactions et checkpoints; les routes E01 restent bornées et expérimentales.
- **CONTACT** : conserver le résultat négatif C01 et sa remédiation ouverte; C02 demeure limité à AR/N03. Aucune généralisation à tout contact, au frottement, au glissement fini ou au solveur Docker.
- **HÉRITÉ / TRANSVERSAL** : chemins classiques affectés par les changements partagés, rotation expérimentale héritée, Campbell, MPC/RBE bornés, API/CLI, résultats, IO, dispatch et contrôles des backends réellement disponibles.
- **PERFORMANCE** : mesures descriptives liées à une machine, une version logicielle, une taille et un scénario fixés. Aucune extrapolation générale depuis un petit cas synthétique.

Le périmètre et ses exclusions sont subordonnés à [wp00_baseline_scope.md](../wp00_baseline_scope.md), [wp00_baseline_scope_contract.json](../wp00_baseline_scope_contract.json) et aux contrats versionnés WP02–WP10. D01 reste `INCONCLUSIVE`, D02 `CLOSED_BOUNDED`, E01 `OPEN_WITH_BOUNDED_CERTIFICATES`, C01 `CLOSED_NEGATIVE` avec remédiation ouverte et C02 `CLOSED_BOUNDED` uniquement AR/N03. WP11 reste `CLOSED` pour son gate API/intégration. WP12 et WP13 restent `OPEN`.

## 3. Définitions des états de preuve

La matrice sépare le statut historique du statut du code cible. Les états suivants n'ont pas d'équivalence implicite :

| État | Sens obligatoire |
|---|---|
| `HISTORICAL_PASS` | Un rapport ou reçu enregistre PASS pour son identité, contrat, modèle et périmètre historiques cités; aucune assertion sur le code cible. |
| `CURRENT_PASS_EVIDENCED` | Résultat acquis après exécution autorisée, lié par hashes au commit/tree et aux fixtures cibles, satisfaisant le contrat applicable. Aucun élément de la matrice n'a cet état à WP12-0. |
| `FAIL` | Échec observé sous le contrat et l'identité indiqués; il reste visible jusqu'à décision formelle appropriée. |
| `INCONCLUSIVE` | Preuve insuffisante, contradictoire ou non concluante; ne vaut ni PASS ni FAIL. |
| `NOT_RUN` | Le contrôle n'a pas été exécuté sur le commit/tree cible proposé. C'est l'état courant des futures campagnes numériques WP12. |
| `NOT_ACQUIRED` | La preuve contractuelle requise n'existe pas ou n'a pas pu être obtenue dans le périmètre considéré. |
| `STATIC_INSPECTION_ONLY` | Existence et structure vérifiées par lecture de sources/fichiers, sans import, collecte ni exécution; ce n'est pas une preuve scientifique. |
| `NOT_APPLICABLE` | Contrôle hors du domaine contracté, avec justification explicite; jamais utilisé pour cacher un échec ou un résultat manquant obligatoire. |

Un rapport qui dit « tests présents » établit seulement la présence des définitions. Un `pytest` antérieur au changement de projection ne couvre pas la nouvelle projection. Un PASS d'un test d'identité, de refus, de serialization ou de point matériau ne qualifie pas à lui seul une chaîne FEM complète.

## 4. Principes d'acceptation

1. Lier chaque résultat au commit, tree, statut propre, versions d'environnement, fichiers source/test/fixture et commande exacte. Toute différence non autorisée donne `STOP/INCONCLUSIVE`, pas un PASS réutilisé.
2. Réutiliser les seuils contractuels déjà gelés. Aucun seuil ne peut être choisi, resserré ou relâché après observation. Une lacune de seuil bloque le verdict concerné jusqu'à décision Owner ou reste explicitement non-gating.
3. Conserver les verdicts scientifiques distincts (DYN, NL, contact borné, options expérimentales) et les états `FAIL`, `INCONCLUSIVE`, `NOT_RUN`, `NOT_ACQUIRED`, skips et ambiguïtés.
4. Pour les contrôles indépendants, distinguer oracle analytique/référence indépendante, invariant, résidu algébrique, comparaison de deux routes partageant du code, convergence spatiale, convergence temporelle et comparaison de solveur externe.
5. Les résultats historiques peuvent réduire le besoin de réexécuter une preuve immuable seulement quand son identité et son domaine restent valables. Une dépendance transverse modifiée appelle un contrôle actuel adapté; elle ne transforme pas le résultat historique en défaut ni ne rouvre automatiquement son WP.
6. Aucun résultat préparatoire, test ordinaire ou runner de développement ne vaut autorisation ni preuve de qualification de campagne.

## 5. Conditions proposées de clôture WP12

Une recommandation de clôture ne serait envisageable qu'après : (a) décision Owner sur le périmètre exact et les exclusions; (b) manifestes d'exécution approuvés et figés; (c) contrôles MUST exécutés sur une identité source propre et vérifiable; (d) critères numériques contractuels satisfaits sans ajustement post-hoc; (e) échecs, ambiguïtés, skips et preuves absentes traités ou acceptés explicitement avec portée bornée; (f) preuve de non-régression API/IO/dispatch et des dépendances partagées touchées; (g) bilan de performance dans les limites réellement déclarées; (h) dossier de preuve consolidé et revue Owner.

Ces conditions ne requièrent pas une qualification générale de C01, C02 hors AR/N03, D01, E01, rotor, HPC ou de toutes les physiques expérimentales. Elles n'autorisent ni clôture automatique ni publication. Aucune décision de statut n'est prise ici.
