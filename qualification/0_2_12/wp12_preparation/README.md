# WP12-0 — Préparation du cadre V&V

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

État préparatoire au 2026-10-25, branche `emptiesvoids-cloud/0.2.12`, code cible `00428adf38e9397340ac136f6f503a268eb671da`, Git tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. L'arbre de travail était propre au début de WP12-0. Les futurs documents de préparation ne font pas partie du code ciblé par les campagnes.

Ce dossier décrit le périmètre, les preuves, les campagnes et les contrôles d'exécution proposés. Il n'autorise aucun test, calcul FEM, solveur, benchmark, promotion scientifique ou changement de statut. Chaque manifeste reste `PREPARED_NOT_AUTHORIZED` jusqu'à une décision Owner explicite et une relecture de l'identité, des commandes, des limites et des destinations.

## Documents

- [Périmètre et critères d'acceptation](wp12_scope_and_acceptance.md)
- [Matrice globale des capacités et preuves](wp12_capability_evidence_matrix.tsv)
- [Revue des dépendances et de la projection modale](wp12_source_dependency_review.md)
- [Revue de provenance C02 AR/N03](wp12_c02_provenance_review.md)
- [Plan des lots WP12-1 à WP12-6](wp12_campaign_plan.md)
- [Gabarit de manifeste](wp12_execution_manifest_template.json)
- [Manifeste WP12-1](wp12_1_execution_manifest.json) · [WP12-2](wp12_2_execution_manifest.json) · [WP12-3](wp12_3_execution_manifest.json)
- [Manifeste WP12-4](wp12_4_execution_manifest.json) · [WP12-5](wp12_5_execution_manifest.json) · [WP12-6](wp12_6_execution_manifest.json)
- [Exigences et état du runner WP12-R](wp12_runner_requirements.md)
- [Guide d'utilisation en modes VALIDATE / SELF_TEST / EXECUTE](wp12_runner_usage.md)
- [Modèle de confiance et limites de sécurité](wp12_runner_security_model.md)
- [Audit du runner et contrôles synthétiques](wp12_runner_audit.md)
- [Registre des écarts résiduels du runner](wp12_runner_residual_gaps.md)
- Schémas : [manifeste préparatoire](wp12_prepared_manifest.schema.json), [unité d'exécution figée](wp12_execution_manifest.schema.json), [décision Owner séparée](wp12_owner_decision.schema.json)
- [Registre des risques](wp12_risk_register.md)
- [Décisions Owner requises](wp12_owner_decisions_required.md)
- [Plan de non-régression rotor existant](../wp12_rotating_inherited_regression_plan.md)

Les preuves historiques demeurent dans leurs emplacements v0.2.11/v0.2.12 existants et ne sont ni déplacées ni réécrites. Les tableaux de ce dossier les citent sans les requalifier comme essais du code cible. Le runner WP12-R n'autorise que VALIDATE statique et SELF_TEST synthétique; toute exécution scientifique est refusée et nécessite une décision Owner, un ancrage de confiance vérifiable et une isolation OS adaptée.
