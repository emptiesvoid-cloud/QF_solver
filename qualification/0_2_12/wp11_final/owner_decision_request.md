# WP11 — Décisions demandées à l’Owner

## Proposition de l’équipe

Conserver le statut officiel `WP11=OPEN` jusqu’à la décision Owner. Le dossier relève les contrats et intégrations présents, corrige quatre défauts démontrés de sérialisation/écriture et passe les tests non-FEM sélectionnés. La catégorie de rapport proposée est **`OPEN_WITH_ACTIONS`** : le gate opérationnel « complet » n’a pas de critères d’acceptation détaillés approuvés dans les documents consultés, et aucune campagne FEM n’a été autorisée par un manifeste gelé.

## Questions à trancher

1. **Format des résultats** — Les résultats ordinaires hétérogènes, leurs sérialiseurs documentés et les contrats versionnés propres aux routes suffisent-ils à WP11? Recommandation : oui pour le contrat actuel; ne pas imposer de schéma global ni de `load_result()` sans besoin consommateur approuvé.
2. **Séquencement** — La roadmap opérationnelle classe D01/D02 et E01 avant WP11. Le code D01 est maintenant présent sur cette branche, mais ses rapports maintiennent `WP_D01_STATUS=INCONCLUSIVE`, `C4=NOT_ACQUIRED` et `WP05_FEM_QUALIFICATION=NOT_EVALUATED`. Le port technique suffit-il à l’ordre d’intégration, ou exige-t-on la clôture scientifique D01 avant WP11? Recommandation : maintenir les statuts D01 et demander une décision explicite; ne pas assimiler intégration du code à clôture D01.
3. **C02** — Le code d’intégration est présent et l’Owner a limité `CLOSED_BOUNDED` à WP-C02-AR/N03. Qualification générale contact et équivalence Docker restent `NOT_ACQUIRED`. Confirme-t-on que ce scope borné suffit pour l’inventaire WP11 et que la qualification générale C02 n’est pas une dépendance? Recommandation : traiter uniquement le scope AR/N03 comme intégré.
4. **Démonstration d’intégration** — La preuve statique, les tests d’API et les round-trips synthétiques suffisent-ils au gate d’intégration? Si une exécution FEM réduite est nécessaire, fournir avant lancement une décision Owner qui fixe le SHA/tree, les entrées/manifests/hashes, le budget, la liste exacte de nodeids et la classification de preuve. Aucun calcul n’est demandé ou exécuté par ce dossier.
5. **Clôture** — Après les réponses ci-dessus, l’Owner peut accepter la matrice comme démonstration suffisante et prononcer la clôture, ou maintenir `OPEN` en nommant les gates de preuve à satisfaire. Le présent rapport ne modifie pas le statut normatif.

## Limites scientifiques explicitement préservées

- `WP_D02=CLOSED_BOUNDED` reste attaché à ses fixtures et à son périmètre de récupération.
- `WP_E01=OPEN_WITH_BOUNDED_CERTIFICATES`; le certificat GF4 concerne uniquement le sous-système esclave TET4 exact. L’équilibre de l’assemblage maître reste `NOT_VERIFIED`, le verdict BA global reste `FAIL` et la qualification scientifique générale reste `NOT_ACQUIRED`.
- `WP_D01_STATUS=INCONCLUSIVE`, `C4=NOT_ACQUIRED` et `WP05_FEM_QUALIFICATION=NOT_EVALUATED` restent inchangés.
- `WP_C02_STATUS=CLOSED_BOUNDED` s’applique seulement à AR/N03; `GENERAL_CONTACT_QUALIFICATION` et `DOCKER_EQUIVALENCE` restent `NOT_ACQUIRED`.
- Les historiques N06/N08 et Docker en échec sont préservés. Le chemin B* C01 est expérimental borné et ne ferme pas sa remédiation.

Les résultats de WP11 sont des preuves d’API/I/O et de non-régression; ils n’accordent pas de qualification FEM ou industrielle.
