# WP12-A — Plan d'activation contrôlée

PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN

## Objet et état de départ

Ce plan prépare une éventuelle décision pour une seule unité de test, WP12-1-PILOT-001. L'accord Owner de principe permet de préparer cette unité; il ne constitue ni une signature Ed25519, ni une autorisation authentifiée, ni une levée des blocages de sécurité. La revue WP12-S au commit f2c1be4fdeef3cc041f01a4af8b5664395908491 est SECURITY_REVIEW_WITH_BLOCKERS. Dans WP12-A, le code conserve REAL_EXECUTION_ENABLED=False et le chemin scientifique EXECUTE refuse inconditionnellement toute demande.

Le code du runner a sa propre identité : commit a26901217826b9c5740066f1acbbc245e1a15519, tree ef0e3556c08b768642b6c3fee4d8669cbc9ecf16. L'identité scientifique WP12-0 reste séparée : commit 00428adf38e9397340ac136f6f503a268eb671da, tree df4ec667bf746b042c900fad1f86bf542e1a437b. Le checkout scientifique observé est propre et détaché à cette identité. Aucun commit documentaire ultérieur ne remplace l'identité du code runner déclarée dans le manifeste.

## Périmètres préparatoires

La répartition proposée des neuf nodeids historiques est conservée dans [l'index R3](revisions/manifest_scope_proposal_index.r3.json) et les manifestes [WP12-1](revisions/wp12_1_execution_manifest.r3-scope-proposal.json), [WP12-2](revisions/wp12_2_execution_manifest.r3-scope-proposal.json) et [WP12-3](revisions/wp12_3_execution_manifest.r3-scope-proposal.json). La proposition est : six tests en WP12-1, deux transferts en WP12-2 et un transfert en WP12-3. Les manifestes originaux et R1/R2 sont conservés par leurs empreintes. Le découpage reste PENDING_OWNER_DECISION; aucun de ces neuf nodeids n'est autorisé par ce plan.

Le pilote ciblé comprend uniquement :

tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form

Il contrôle la cohérence algébrique de la projection symétrique structurée avec la forme bilinéaire dense sur des matrices inline. Ses assertions existantes sont reprises sans changement. Ce pilote n'est ni une validation de modèle FEM ni une qualification modale générale.

## État de préparation et gates

| Gate | État constaté | Résultat |
|---|---|---|
| Identité scientifique et runner | Deux identités distinctes fixées dans le manifeste | PASS documentaire seulement |
| Hash du test et de la fixture inline | Hash du fichier et extraction canonique vérifiés statiquement | PASS documentaire seulement |
| Structure du manifeste | JSON valide selon le schéma v3 | PASS de syntaxe seulement |
| Trust store Owner, pin HKLM et signature | Absents; aucune clé réelle n'a été créée | BLOCKED_SECURITY |
| Checkout et archives en lecture seule pour le compte d'exécution | ACL observées autorisent l'écriture depuis le contexte actuel | BLOCKED_SECURITY |
| Environnement isolé et origine d'import | Pas de compte dédié/venv; origine d'import solveur non vérifiée | BLOCKED_SECURITY |
| Limites CPU, threads et stockage | CPU, threads et stockage ne sont pas des plafonds durs | BLOCKED_SECURITY tant que l'Owner n'accepte pas un environnement adapté |
| Plugin du runner depuis le checkout scientifique | argv ne définit pas un chemin d'import/cwd reproductible entre checkouts | BLOCKED_MANIFEST |
| Runner scientifique | EXECUTE refusé inconditionnellement | BLOCKED_SECURITY |

Les budgets numériques du manifeste sont des propositions de préparation, pas des budgets approuvés. Les limites indiquées comme dures décrivent les capacités du Job Object disponibles pour certains mécanismes; elles n'ont pas été démontrées sur un processus scientifique. Le temps CPU est classé soft, conformément à la capacité observée. Les limites de threads et de stockage restent soft.

## Ordre exigé avant tout lancement ultérieur

1. Faire statuer l'Owner sur la répartition WP12-1/2/3 et sur le périmètre précis de cette unité.
2. Résoudre les blockers d'isolation dans l'état de sécurité, sans réduire les exigences par commodité.
3. Figer une méthode déterministe pour exécuter le test depuis le checkout scientifique tout en chargeant le plugin depuis le commit runner exact; lier le cwd, l'environnement enfant et les chemins de sortie à une nouvelle révision de manifeste.
4. Provisionner la racine de confiance Owner hors checkout et vérifier le pin/ACL par une revue indépendante. Aucune clé privée ne doit entrer dans le dépôt, les journaux ou le chat.
5. Construire et valider avec vecteurs synthétiques la décision Owner signée qui lie le hash final du manifeste, les deux identités Git, le nodeid, l'environnement, la destination et une seule tentative.
6. Faire une revue indépendante du code du chemin d'exécution activable. Aujourd'hui, ce chemin n'existe pas : EXECUTE demeure un stub de refus.
7. Présenter le dossier au gate Owner. La confirmation explicite de l'unité exacte, plus une décision cryptographiquement authentifiée, serait encore requise après résolution des gates techniques.

Si une condition échoue, arrêter avec DENY_EXECUTION; ne pas transformer le refus en NOT_RUN ou en résultat scientifique. Il n'existe pas de rapport d'issue du pilote, car aucune tentative n'a été réservée ou lancée.

## Décisions de statut

WP11 reste CLOSED sur son périmètre API/intégration. WP12 et WP13 restent OPEN. WP12-A est WP12_A_BLOCKED_SECURITY; les documents R3 ne changent pas le statut officiel des campagnes et ne valent pas décision Owner.
