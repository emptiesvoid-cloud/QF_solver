# WP11 v0.2.12 — Décision Owner et revue de contrat

- **Date :** 2026-10-25
- **Branche examinée :** `emptiesvoids-cloud/0.2.12`
- **HEAD vérifié au début de la revue :** `174e2f79f664dd3e4706d0392a90bf255aea5383`
- **Commit code/API vérifié :** `84de7837f90406aedfbccd3f9af560958d49819d`
- **Origine :** `https://github.com/emptiesvoid-cloud/QF_solver.git`

## Décisions de portée

L’Owner accepte les DTO de résultats hétérogènes dès lors que leur contrat est
documenté. Aucun schéma universel de résultat ni `load_result()` générique
n’est requis pour v0.2.12. Les schémas versionnés, leurs règles de refus et
leurs limites restent applicables.

Les statuts scientifiques restent strictement inchangés : D01
`INCONCLUSIVE`; C02 `CLOSED_BOUNDED` sur AR/N03 uniquement; E01
`OPEN_WITH_BOUNDED_CERTIFICATES`. Ces statuts ne bloquent pas en soi
l’acceptation des contrats API WP11 et ne peuvent pas être promus par cette
revue.

WP11 couvre l’intégration des interfaces, la traçabilité, les contrats de
résultats, la sérialisation, la compatibilité documentée et les refus. La V&V
numérique et la performance relèvent de WP12. Toute exécution FEM supplémentaire
nécessite son propre manifeste gelé et une autorisation distincte.

## Revue documentaire et approbation

GPT-6 Luna a examiné les contrats API, les serializers, le writer JSON, les
points d’entrée CLI, les tests ciblés et la couverture documentaire. Le
comportement historique de `save_result` a été comparé au baseline : l’ancien
writer remplaçait une cible, tandis que le writer actuel refusait son
remplacement. La compatibilité est conservée pour les destinations nouvelles;
les clients qui remplaçaient un fichier doivent désormais choisir explicitement
`overwrite=True` ou `--overwrite`. Cette rupture ciblée est documentée dans
[`api_results_serialization_audit.md`](api_results_serialization_audit.md) et
vérifiée par la matrice d’acceptation.

L’Owner approuve la politique de contrats et le périmètre de WP11 décrits
ci-dessus. Cette approbation constitue une traçabilité de revue et de politique
pour les références API en `controlled_candidate`; elle n’est ni une
approbation de publication du package/site ni une promotion scientifique.

## État et décision de clôture

Le statut normatif a été maintenu `WP11=OPEN` pendant les contrôles et la
finalisation des preuves. Après leur réussite, WP11 est clôturé pour le seul
gate opérationnel API/intégration v0.2.12. Le verdict motivé et les preuves
exactes sont consignés dans
[`closure_gate_assessment.md`](closure_gate_assessment.md). Le registre de tests
de suivi référence le SHA exact testé dans
[`owner_decision_followup_manifest.json`](owner_decision_followup_manifest.json).
