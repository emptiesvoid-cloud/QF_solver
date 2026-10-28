# HEX20 — contrat de décision Owner : cause et correctif

Statut : correctif candidat pour revue ; aucune autorisation scientifique créée.

Le refus historique `HEX20_PRE_RESERVATION_REFUSAL` concernait le contrôleur `268d80c3403df67aa87578e7e17f5c8c0f0ca95f`. Son validateur retournait `owner_decision` sans clé de reçu `decision_id`, alors que le chemin de réservation la lisait directement. Le rapport historique SHA-256 `1dcdb0fba1f105f763d5c68ea15771af22c3eb6b4360d13b24da23fe8fddaa18` est conservé.

La branche canonique examinée est `emptiesvoids-cloud/0.2.12`, HEAD `5f6effa6bfb8d1fba4c6acd2f754de45775f02d0`, tree `49fc88a6416d29f6b3e7e9a22357048ddd188059`. Le contrôleur actuellement désigné par son AGENTS.md est le worktree détaché `C:\Users\fari\.codex\worktrees\wp12-controller-base-1b8d6a7\qf_solver`, HEAD `1b8d6a76b062039566dbf0f2bd508b7990035dca`, tree `c5fe42978125349bb40d0f443560437ee43f239f`, fingerprint `f6d2a49da3e41feab82da740d6155c6fc56e9b0f36e901bd260ca5823a0ff12a`. Sa version plus récente retourne déjà `decision_id` avec `.get`, mais n'exige un identifiant valide que pour WP12-A : HEX20 accepte encore une valeur absente.

Le correctif candidat exige pour `wp12_hex20_affine_diagnostic` un `decision_id` présent et conforme au format existant. Le reçu est vérifié contre la décision imbriquée avant la réservation. Les autres scopes gardent leur contrat existant ; aucun identifiant ni autorisation n'est inventé. Le manifeste reste lié au fingerprint de la source, du contrôleur et aux limites.

Vérifications synthétiques : 244 tests des suites politique, provenance et support HEX20 ainsi que du nouveau contrat passent. Les tests du nouveau contrat couvrent ID valide, absent ou mal formé, incohérence reçu/décision, manifeste non autorisé, source ou contrôleur périmé, budget modifié, argument préflight incompatible, ledger déjà consommé et réservation/archivage simulés sans lancement du corps pytest. Ruff lint, compilation Python, JSON et `git diff --check` passent. Le test simulé remplace le processus enfant et le contrôle du sidecar par des doublures ; il ne constitue pas une preuve mécanique.

Limites de contrat : la désignation du contrôleur est actuellement une règle de l'AGENTS.md canonique, pas une vérification automatique de chemin dans ce validateur générique. Le scope HEX20 ne lie pas le reçu collect-only au manifeste dans le runner : une vérification opérationnelle de son identité est nécessaire. Les tests ne prétendent pas démontrer une protection automatique absente.

Aucune fusion n'est effectuée sans autorisation applicable. Une désignation révisée et un nouveau fingerprint seront nécessaires après intégration avant toute préparation officielle.

## Identités et contrat de référence

Contrôleur officiellement désigné avant correction : HEAD `1b8d6a76b062039566dbf0f2bd508b7990035dca`, fingerprint `f6d2a49da3e41feab82da740d6155c6fc56e9b0f36e901bd260ca5823a0ff12a`. Source scientifique : HEAD `8f2b02b053af70cbaa23378adbd783dd99669b1b`, fingerprint `efe44ae1505eb130e15e8ce8c4ae5311b639353b674c94b393d75387655227fb`. Manifeste R2 historique SHA-256 `2783012c0080b591b3f3d8f1ba8be080e82cc75c9f557357d15b32d7aeccf59b`, reçu collect-only historique SHA-256 `083e2f9cc3b3a562d006ba2b1cc0b463ac0d198fa798374b4464e6c5c010f943` ; leurs identités de contrôleur ne sont pas transférables.

Le cas prévoit 60 DDL, une tentative, 300 s et une RSS surveillée de 4096 MiB. Les assertions historiques R4 restent les critères actifs du code scientifique ; les nouveaux seuils QUAD8 et η∞ restent proposés et non contraignants. Aucune qualification globale ni nouveau résultat scientifique ne découle des contrôles synthétiques.
