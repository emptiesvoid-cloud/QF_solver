# WP12 — Préparation du cadre V&V et suivi des snapshots

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## État opérationnel courant — WP12-B, 2026-10-26

Verdict : **WP12_B_BLOCKED_WITH_EXACT_OWNER_ACTIONS**. Les checkouts source/runner et le venv dédiés sont en place, le manifeste pilote v3 passe `VALIDATE` comme `STRUCTURALLY_VALID_NOT_AUTHORIZED`, et les contrôles synthétiques du runner passent. Aucun compte/ACL Windows, trust store ou décision signée n'est provisionné; le build Windows est sous le minimum du script. Le lancement scientifique reste bloqué en code par l'absence d'attestation du processus enfant. Aucun test scientifique n'a été lancé. Lire le [rapport de configuration](wp12_b_configuration_report.md), le [dossier d'actions Owner](wp12_b_owner_actions.md), la [revue du manifeste v3](wp12_b_pilot_manifest_review.md) et la [revue du runner](wp12_b_runner_review.md).

Les sections WP12-0, R, S, X et A ci-dessous sont des snapshots de leurs étapes respectives; leur présence ne remplace pas l'état courant ni n'autorise une campagne.

État préparatoire au 2026-10-25, branche `emptiesvoids-cloud/0.2.12`, code cible `00428adf38e9397340ac136f6f503a268eb671da`, Git tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. L'arbre de travail était propre au début de WP12-0. Les futurs documents de préparation ne font pas partie du code ciblé par les campagnes.

Ce dossier décrit le périmètre, les preuves, les campagnes et les contrôles d'exécution proposés. Il n'autorise aucun test, calcul FEM, solveur, benchmark, promotion scientifique ou changement de statut. Les six manifestes WP12-0 et leurs révisions R1/R2/R3 restent `PREPARED_NOT_AUTHORIZED` jusqu'à décision Owner. Le manifeste de pilote WP12-A est séparément `FROZEN_NOT_AUTHORIZED`; il n'est ni signé ni exécutable.

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
- Schémas : [manifeste préparatoire](wp12_prepared_manifest.schema.json), [unité d'exécution figée](wp12_execution_manifest.schema.json), [décision Owner signée v2](wp12_owner_decision.schema.json), [trust store public](wp12_owner_trust_store.schema.json)
- [Registre des risques](wp12_risk_register.md)
- [Décisions Owner requises](wp12_owner_decisions_required.md)
- [Plan de non-régression rotor existant](../wp12_rotating_inherited_regression_plan.md)

Les preuves historiques demeurent dans leurs emplacements v0.2.11/v0.2.12 existants et ne sont ni déplacées ni réécrites. Les tableaux de ce dossier les citent sans les requalifier comme essais du code cible. Depuis WP12-A, le chemin scientifique EXECUTE est inconditionnellement bloqué par le code; ni une décision ni une signature ne lèvent cette barrière. VALIDATE et SELF_TEST restent les seuls modes pertinents de cette préparation. Aucun test scientifique n'est autorisé par ces documents.

## WP12-R2 — Durcissement préparatoire

L'addendum [WP12-R2 sécurité et écarts](wp12_r2_runner_security_review.md) décrit le vérificateur Ed25519, les Job Objects Windows testés avec des processus factices, le ledger append-only logique, la collecte statique de provenance et le mode distinct de synchronisation distante. La confiance Owner n'est pas provisionnée et `EXECUTE` reste désactivé.

Les six manifestes WP12-0 sont conservés octet pour octet. Les nouvelles révisions [WP12-1 à WP12-6](revisions/manifest_revision_index.json) restent `PREPARED_NOT_AUTHORIZED`; l'index relie chaque révision au SHA-256 de son original et au candidat scientifique WP12-0. Les révisions ne sont ni une autorisation ni une preuve d'exécution.

WP12-R2 est `PREPARATION_ONLY`; `NUMERICAL_EXECUTION_NOT_PERFORMED`; `WP12_STATUS=OPEN`.

## WP12-S — Revue de sécurité Owner et périmètre WP12-1

La [revue de sécurité Owner](wp12_s_owner_security_assessment.md) conclut `SECURITY_REVIEW_WITH_BLOCKERS`. La [matrice des contrôles](wp12_s_security_controls_matrix.md) distingue les garanties synthétiques, les protections partielles et les limites absentes; la [checklist Owner](wp12_s_owner_action_checklist.md) décrit les prérequis de confiance, d'isolation, de reçus et d'approbation sans configurer de secrets ou paramètres système.

La [revue de scope WP12-1](wp12_s_wp12_1_scope_review.md) relève notamment un nodeid Newmark qui appelle `solve_model`, des dépendances checkpoint non linéaires hors de l'inventaire direct, et des champs de fixture/environnement/ressource encore à figer. Ces documents sont préparatoires : aucune campagne ni décision Owner n'est autorisée par leur présence. WP11 reste CLOSED; WP12 et WP13 restent OPEN.

## WP12-X — Orchestration synthétique

L'[orchestrateur SELF_TEST WP12-X](wp12_x_synthetic_orchestration.md) orchestre uniquement les cas factices fixes du runner, avec journal temporaire chaîné et reçus vérifiés. Les propositions de partition des neuf nodeids sont tracées dans les [révisions R3 préparatoires](revisions/manifest_scope_proposal_index.r3.json); R1/R2 restent inchangés, le scope reste en attente de décision Owner et `EXECUTE` est inconditionnellement bloqué.

## WP12-A — Préparation du pilote Owner

Les documents [plan d'activation](wp12_a_activation_plan.md), [dossier Owner](wp12_a_owner_decision_package.md), [revue du manifeste pilote](wp12_a_pilot_manifest_review.md), [état de sécurité de l'environnement](wp12_a_environment_security_report.md) et [revue du chemin d'exécution](wp12_a_runner_execution_review.md) préparent uniquement une éventuelle revue Owner. Le manifeste [wp12_a_pilot_manifest_v1.json](wp12_a_pilot_manifest_v1.json) cible un seul nodeid et porte son SHA-256 dans le dossier; il n'est pas signé ni autorisé. L'attestation [wp12_a_isolation_attestation.json](wp12_a_isolation_attestation.json) consigne des contrôles manquants. Il n'existe pas de rapport d'issue de pilote, car aucun lancement scientifique n'a eu lieu.

WP12-A est **BLOCKED_SECURITY** : confiance Owner non provisionnée, protections NTFS insuffisantes, compte non dédié, absence de venv isolé/ancrage externe, limites CPU/stockage/threads non dures et résolution du plugin entre checkouts non figée. WP11 reste CLOSED; WP12 et WP13 restent OPEN.

## WP12-B — Déblocage opérationnel Windows

La configuration courante et les faits hôte sont dans [wp12_b_configuration_report.md](wp12_b_configuration_report.md). Les actions administratives préparées, leurs commandes de preview/application et le rollback sont dans [wp12_b_owner_actions.md](wp12_b_owner_actions.md). Le manifeste [v2](wp12_b_pilot_manifest_v2.json) reste préservé; le [v3](wp12_b_pilot_manifest_v3.json) lie le runner corrigé et demeure `FROZEN_NOT_AUTHORIZED`. La [répartition R4 des neuf nodeids](wp12_b_nodeid_partition_r4.json) formalise le découpage préparatoire accepté par l'Owner et signale les divergences SHA historiques sans modifier ces snapshots; elle ne vaut pas autorisation scientifique. La [revue du runner](wp12_b_runner_review.md) consigne les tests synthétiques et le blocage d'`EXECUTE`.

WP12-B reste `PREPARATION_ONLY`; `NUMERICAL_EXECUTION_NOT_PERFORMED`; `WP12_STATUS=OPEN`. WP11 reste CLOSED et WP13 OPEN.
