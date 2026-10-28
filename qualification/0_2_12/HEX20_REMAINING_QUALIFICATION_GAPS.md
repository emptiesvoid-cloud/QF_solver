# HEX20 — limites de qualification restantes

Aucune qualification scientifique générale ne résulte du correctif de contrôleur ni des tests synthétiques. L'échec R4 `PYTEST_FAILED / ROOT_CAUSE_INCONCLUSIVE` est inchangé et aucune nouvelle résolution HEX20 n'a été exécutée.

Le préflight doit être renouvelé après intégration et désignation du contrôleur, puis son identité vérifiée explicitement pour le scope HEX20, dont le manifeste générique ne lie actuellement pas le reçu. La désignation du contrôleur repose sur l'AGENTS.md canonique ; le validateur générique compare le fingerprint du manifeste au contrôleur courant mais ne vérifie pas lui-même le chemin désigné. Ces limites ne doivent pas être assimilées à des protections automatiques.

Une nouvelle décision Owner liée au manifeste final, au contrôleur, à la source, au nodeid, aux critères et aux budgets est nécessaire avant une tentative. Les limites de ressources sont surveillées et ne constituent pas une isolation matérielle. Les critères diagnostiques proposés ne sont pas des CASE_GATE approuvés. La comparaison à une référence 3D indépendante et la couverture des autres géométries, chargements et routes HEX20 restent à établir séparément.

## Identités et contrat de référence

Contrôleur officiellement désigné avant correction : HEAD `1b8d6a76b062039566dbf0f2bd508b7990035dca`, fingerprint `f6d2a49da3e41feab82da740d6155c6fc56e9b0f36e901bd260ca5823a0ff12a`. Source scientifique : HEAD `8f2b02b053af70cbaa23378adbd783dd99669b1b`, fingerprint `efe44ae1505eb130e15e8ce8c4ae5311b639353b674c94b393d75387655227fb`. Manifeste R2 historique SHA-256 `2783012c0080b591b3f3d8f1ba8be080e82cc75c9f557357d15b32d7aeccf59b`, reçu collect-only historique SHA-256 `083e2f9cc3b3a562d006ba2b1cc0b463ac0d198fa798374b4464e6c5c010f943` ; leurs identités de contrôleur ne sont pas transférables.

Le cas prévoit 60 DDL, une tentative, 300 s et une RSS surveillée de 4096 MiB. Les assertions historiques R4 restent les critères actifs du code scientifique ; les nouveaux seuils QUAD8 et η∞ restent proposés et non contraignants. Aucune qualification globale ni nouveau résultat scientifique ne découle des contrôles synthétiques.
