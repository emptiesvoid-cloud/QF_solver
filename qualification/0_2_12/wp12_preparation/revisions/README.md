# WP12-R2 — Révisions préparatoires des manifestes

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Ces six documents révisés ne remplacent pas silencieusement les manifestes WP12-0; ceux-ci restent dans le dossier parent. L'[index](manifest_revision_index.json) contient le SHA-256 exact de chaque manifeste d'origine et de sa nouvelle révision.

| Lot | Révision R2 |
|---|---|
| WP12-1 | [Contrats de projection modale](wp12_1_execution_manifest.r2-prepared.json) |
| WP12-2 | [Dynamique et D02](wp12_2_execution_manifest.r2-prepared.json) |
| WP12-3 | [Non-linéaire et contact borné](wp12_3_execution_manifest.r2-prepared.json) |
| WP12-4 | [Non-régression transversale et héritée](wp12_4_execution_manifest.r2-prepared.json) |
| WP12-5 | [Scénarios de performance proposés](wp12_5_execution_manifest.r2-prepared.json) |
| WP12-6 | [Consolidation prospective](wp12_6_execution_manifest.r2-prepared.json) |

Toutes les révisions conservent `PREPARED_NOT_AUTHORIZED`. Les inventaires WP12-1..4 identifient les blobs du candidat scientifique `00428adf38e9397340ac136f6f503a268eb671da` / tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. Les alias de chemins découverts par inspection du tree restent signalés comme changements de périmètre à approuver. Aucun test, fixture scientifique ou commande n'est exécuté depuis ces manifestes.

WP12-5 ne dispose pas encore d'un harness v0.2.12, d'un inventaire source/test ou de valeurs de workload gelées. WP12-6 ne peut pas connaître son identité finale avant les campagnes précédentes. Les fixtures inline ne sont pas matérialisées pour calculer leur hash; les écarts C01 et l'overlay C02 requis sont conservés.
