# WP11 — Contrat d’intégration et périmètre retenu

## Identité et état pendant la vérification

Ce dossier traite le WP11 opérationnel v0.2.12 (« intégration, résultats, API
et sérialisation »), distinct du WP11 prospectif « generalized-alpha » de la
partie II de la roadmap. La branche vérifiée au début de cette mission est
`emptiesvoids-cloud/0.2.12`, HEAD `174e2f79f664dd3e4706d0392a90bf255aea5383`,
avec origin `https://github.com/emptiesvoid-cloud/QF_solver.git`. Ce SHA est
le point de départ, pas le SHA final de ce suivi.

Pendant cette revue, le statut officiel reste `WP11=OPEN`. L’autorisation Owner
du 2026-10-25 fixe le périmètre et les critères d’acceptation, mais ne constitue
pas encore le verdict final de clôture. Les entrées historiques du ledger ne
sont pas modifiées.

## Contrat accepté

1. `qf_solver` est la façade publique. L’inventaire v0.2.12 documente 77
   exports : 30 `STABLE` et 47 `PROVISIONAL`; les tests ciblés vérifient
   inventaire, stabilité, pages de référence et signatures critiques.
2. Les entrées modèle utilisent le JSON v1 documenté. `read_inp` reste limité
   au sous-ensemble publié. Les refus et erreurs documentés demeurent
   applicables.
3. Les résultats ordinaires conservent leurs DTO et sérialiseurs propres. Les
   DTO hétérogènes documentés suffisent à WP11 v0.2.12; aucun schéma universel
   ni `load_result()` générique n’est requis.
4. Les schémas versionnés et leurs limites restent spécifiques :
   `qf-modal-newmark-result/v1`, `qf-reduced-harmonic-result/v1`, le wrapper
   D01 `qf-reduced-harmonic-residual-flexibility-result/v1`, le stress D02
   `qf-dynamic-solid-stress/v1` et le stockage HDF5 mixte version `1.0`.
5. Les champs complexes, identités d’entrée, d’opérateur, de base et
   d’exécution restent vérifiés selon les contrats qui les déclarent. Aucun
   résultat de cette revue ne promeut la maturité ou le statut scientifique.
6. `save_result(result, path, *, overwrite=False)` refuse par défaut toute
   destination existante. `overwrite=True` rétablit explicitement la capacité
   de remplacement historique. Les appels à deux arguments vers une nouvelle
   destination restent compatibles; les intégrations qui remplaçaient un
   fichier doivent ajouter le mot-clé. Le CLI fournit `--overwrite` sur les
   commandes qui passent par ce writer.
7. HDF5 conserve la création exclusive et ne supprime, lors d’un échec, que le
   fichier créé et identifié par le writer concerné.

## Décision Owner et séparation des work packages

- D01 reste `INCONCLUSIVE` (`C4=NOT_ACQUIRED`,
  `WP05_FEM_QUALIFICATION=NOT_EVALUATED`).
- C02 reste `CLOSED_BOUNDED` uniquement sur AR/N03. La qualification générale
  du contact et l’équivalence Docker restent non acquises.
- E01 reste `OPEN_WITH_BOUNDED_CERTIFICATES`; équilibre de l’assemblage maître
  `NOT_VERIFIED`, verdict BA global `FAIL`, tangente J2 globale non résolue et
  qualification générale `NOT_ACQUIRED`.
- Ces états n’empêchent pas l’acceptation des contrats API de WP11. Aucune
  promotion scientifique n’est autorisée.
- Les campagnes de V&V numérique et les mesures de performance relèvent de
  WP12. Aucun FEM supplémentaire n’est lancé sans manifeste gelé et
  autorisation distincte. WP12, WP13, merge vers `main`, tag et publication
  sont hors périmètre.

## Gate et preuves

La matrice d’acceptation datée, les preuves exactes et leurs limites figurent
dans [`wp11_acceptance_matrix.tsv`](wp11_acceptance_matrix.tsv). Les commandes
et résultats de tests de cette vérification sont enregistrés dans
[`owner_decision_followup_manifest.json`](owner_decision_followup_manifest.json)
après exécution. L’inventaire de capacités antérieur reste dans
[`capability_traceability_matrix.tsv`](capability_traceability_matrix.tsv).

Les tests d’API, DTO synthétiques et I/O prouvent des contrats d’interface et
de sérialisation; ils ne sont ni une campagne numérique ni une qualification
FEM. Le verdict final `CLOSE` est limité au gate API/intégration v0.2.12 et est
consigné dans la roadmap et le rapport d’évaluation.
