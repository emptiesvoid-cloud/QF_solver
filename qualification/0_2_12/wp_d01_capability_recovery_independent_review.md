# WP-D01 capability recovery — revue indépendante

Reviewer : agent indépendant, lecture seule. Aucun test ni calcul FEM n’a été lancé par le reviewer.

## Verdict

- P0 : aucun.
- P1 : aucun défaut de code démontré dans le portage.
- P2 : scope/politique D01 active rattaché à l’ancien worktree `C:\wpc01-frictionless-public-integration-wp-d01-bp-exploratory` et à l’ancienne branche `codex/wp-d01-ch-m3-diagnostic-20261023`; il n’autorise pas le nouveau worktree/commit.
- Fusion du snapshot complet : non recommandée en l’état. La branche d’intégration cible contient des changements C01/E01 non commités, dont deux fichiers en recouvrement avec le portage.

## Points examinés

- Le correcteur n’est créé que sur opt-in et exige un damping physique Rayleigh.
- `rayleigh_structured` reste un choix explicite; `legacy_direct` reste le défaut. La cohérence de la projection directe avec les opérateurs M/K projetés est conservée.
- Le correcteur refuse les amortissements prescrits/non-Rayleigh et conserve le seuil de symétrie sans symétrisation de réparation.
- Les scénarios M1/M2/M3 conservent 8/16/32 éléments, 48/96/192 DDL libres et les deux sélections modales 2/4. Le solveur direct partagé par K/M est décrit comme contrôle interne, pas oracle FEM indépendant.
- Les reçus contiennent des snapshots CSR et des tableaux numériques avec dtype, forme, octets base64 et SHA-256. Le validateur conserve ses exigences et accepte désormais exactement 0 Hz suivi de cinq fréquences strictement positives et croissantes.
- Les scénarios `native_vv` sont refusés par pytest ordinaire; le plugin existant ne peut lever ce refus que sur un nodeid D01 exact enregistré.

## Limites

- La revue ne constitue pas une exécution de l’API harmonique sur modèle FEM.
- Aucun JUnit/archive de la nouvelle identité n’existe encore.
- L’allowlist et le ledger actifs ne sont pas transférés à cette branche; le draft de scope reste inactif.
- Ruff est absent de l’environnement observé.

Recommandation : porter les commits vers l’intégration après préservation/résolution des changements C01/E01 qui se chevauchent, puis faire enregistrer et autoriser séparément le nouveau scope exploratoire avant un quelconque RUN FEM.
