# WP12-B HEX20 R1 — dossier de diagnostic

Ce dossier est dérivé en lecture seule de la tentative `dev-8cfe368133a6-attempt-1`. Les preuves originales et le ledger restent dans leur espace d'évidence Owner; aucun fichier R1 n'est réécrit. Le sidecar d'entrée est vérifié par SHA-256 avant tout post-traitement.

- [Cause mécanique et lien matriciel](HEX20_R1_MECHANICAL_ROOT_CAUSE_ANALYSIS.md)
- [Comparaison nodale par face](HEX20_R1_LOAD_VECTOR_COMPARISON.md)
- [Contrat de provenance v1/v2](HEX20_R1_PROVENANCE_SCHEMA_DIAGNOSIS.md)
- [Conditions prospectives R2](HEX20_R2_CORRECTIVE_PLAN.md)
- [Comparaison numérique dérivée](R1_DERIVED_MATRIX_COMPARISON.json) et [script de lecture](analyze_archive.py).

Contrôles locaux : neuf tests purement synthétiques de moments polynomiaux, intégrales QUAD8 et provenance ont passé; Ruff, compilation et `git diff --check` ont passé. Le validateur candidat a vérifié en lecture seule la liaison du sidecar R1 v2, sans changer le statut R1. Les tests d'intégration de face et de pression dans `tests/verification/test_wp12b_hex20_face_quadrature_prepared.py` sont `PREPARED_NOT_AUTHORIZED` et n'ont pas été lancés. Aucun nouveau corps FEM, assemblage global, solve, eigensolve ou réservation n'a été lancé.

Le passage de la règle historique à la règle proposée est démontré par intégration polynomiale : sur `[-1,1]²`, les intégrales QUAD8 historiques sont `−17/27` aux coins et `44/27` aux milieux; la règle corrigée donne `−1/3` et `4/3`. Pour le cube de R1 le jacobien surfacique est `1/4`, donnant les coefficients physiques mentionnés dans les rapports. Les contrôles sur la règle QUAD4 restent identiques; les branches triangulaires et les charges volumiques ne sont pas modifiées. La non-régression FEM et les faces courbes restent à établir sous autorisation.
