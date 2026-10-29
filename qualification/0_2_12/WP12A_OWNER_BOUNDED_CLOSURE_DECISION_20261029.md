# WP12-A — Décision Owner de clôture bornée

**Statut enregistré : WP12A_CLOSED_BOUNDED_FOR_0_2_12_ALPHA**

**Horodatage UTC de transcription opérateur : 2026-10-29T09:15:25.029651+00:00**

**Provenance :** instruction directe de l’Owner dans cette conversation, titre « Décision Owner — Clôture bornée WP12-A pour QF Solver 0.2.12 alpha ». La date ci-dessus est celle de l’enregistrement, pas une heure de signature attestée. Cette transcription n’est pas une signature cryptographique.

## Texte de la décision Owner

Décision Owner — Clôture bornée WP12-A pour QF Solver 0.2.12 alpha

J’approuve explicitement la disposition de clôture bornée définie dans la PR #80, HEAD :

bb10b7da7d27782c4f6a37cb9eb4fc28d53ced23

Verdict approuvé :
WP12A_CLOSED_BOUNDED_FOR_0_2_12_ALPHA

J’accepte la disposition des 20 capacités WP12-A, dont 11 MUST, 8 SHOULD et 1 DEFERRED, exclusivement dans les limites décrites par la matrice de release et le projet de décision Owner.

Je reconnais et accepte explicitement que :

* Les dix expériences ciblées PASS ne constituent pas une qualification générale des capacités.
* Les résultats P0 ne démontrent pas une nouvelle exécution sur le HEAD release.
* La continuité complète après modification de la quadrature QUAD8/HEX20 n’est pas acquise par WP12-A.
* Les résultats numériques absents demeurent NOT_EXPOSED.
* Le support dynamique MPC/RBE n’est pas revendiqué comme qualifié.
* D01 demeure INCONCLUSIVE, avec C4 NOT_ACQUIRED.
* D02 conserve son statut CLOSED_BOUNDED.
* HDF5 reste expérimental et DEFERRED dans le périmètre examiné.
* Les preuves d’assemblage, de réactions et de dispatch API/CLI demeurent bornées.
* Tous les échecs et tentatives historiques restent conservés, sans requalification.

Je limite les revendications de la 0.2.12 alpha aux configurations, routes et contrats effectivement démontrés.

Cette décision clôt uniquement la disposition bornée du chantier interne WP12-A. Elle ne clôt pas WP12 global, WP13 ou les campagnes HEX20 et HEX8-SRI.

Elle ne constitue ni une qualification physique générale, ni une autorisation de calcul supplémentaire, ni une autorisation de publication.

Actions

1. Archiver cette décision Owner avec sa provenance et son horodatage réel.
2. Vérifier la cohérence avec les documents intégrés par la PR #80.
3. Enregistrer le statut WP12A_CLOSED_BOUNDED_FOR_0_2_12_ALPHA dans le suivi approprié, sans modifier les verdicts historiques.
4. Identifier les éventuelles contraintes restantes pour WP12-F et WP13.
5. Ne lancer aucune nouvelle expérience WP12-A sous cette décision.

Résultat attendu :
WP12A_BOUNDED_CLOSURE_RECORDED.

## Références vérifiées

- PR #80 : https://github.com/emptiesvoid-cloud/QF_solver/pull/80 ; HEAD examiné `bb10b7da7d27782c4f6a37cb9eb4fc28d53ced23` ; intégrée le 2026-10-29 à 09:04:06 UTC au commit `de660d6fbeb28044f537cdb6e85235a4e918f417`.
- Matrice intégrée, SHA-256 du blob Git : `8648c776f4d82b065a7bc77390a66b60d54f93035f554e9fa18cf162bb56cc7f`.
- Projet de décision intégré, SHA-256 du blob Git : `606d987f9b7f7a93f86a4dc2d6bc0120f557c1b1c253a9d37fc18d87d1859097`.
- Matrice historique avec renvoi, SHA-256 du blob Git : `cf646086519e3691226bd5b5f36a05e2e2cf5576b36383dbe5e2b7bc19585953`.
- Rapport P0 `WP12A_P0_SCIENTIFIC_RESULTS_AND_DISPOSITION.md`, SHA-256 `28c1fbf527ad2c86c211f64070f0eea01c046d26b96e1a93831da5af934c73ee`.
- Ledger Dynamics v2 `8536e68403c12731b6f14562256bd749bda8bc781ba18c165ebe83164c77f09f` ; ledger historique `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37` ; aucune écriture dans ces ledgers.
