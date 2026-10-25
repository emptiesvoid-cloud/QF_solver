# WP11 — Évaluation du gate de clôture

## Conclusion

**Décision de rapport : `OPEN_WITH_ACTIONS`.** L’inventaire de la façade, les contrats documentés, les tests de sérialisation synthétiques et les corrections P2 exécutables sont démontrés. Le gate global d’intégration reste ouvert : la roadmap exige un gate complet sans en publier une matrice d’acceptation détaillée, aucune revue Owner de clôture n’est enregistrée et aucun test d’intégration FEM n’a été exécuté sous un manifeste d’exécution autorisé et gelé.

Ce libellé est une catégorie de ce rapport. Il n’est pas ajouté à la roadmap comme statut normatif.

## État des critères

| Critère | État | Preuve et limite |
| --- | --- | --- |
| Identité de départ | **PASS** | Branche `emptiesvoids-cloud/0.2.12`, origin attendu, HEAD initial `4bd6abb704f39cda758a3f0a36d8cd71d81da554`; identité/push consignés dans le rapport de livraison. |
| Façade publique et stabilité | **PASS ciblé** | 77 exports, 30 `STABLE` et 47 `PROVISIONAL`; tests inventaire, classification, signatures critiques et documentation candidat passés. |
| Entrées et résultats documentés | **PASS documentaire** | JSON modèle v1 et limites `.inp` documentés; résultats ordinaires propres aux analyses; aucune exigence trouvée pour un schéma universel ou `load_result()`. |
| Contrats de résultat versionnés | **PASS ciblé** | Modal-Newmark, harmonique réduit, wrapper D01, D02 et HDF5 ont chacun leur contrat; round-trips synthétiques Modal-Newmark, réduit, D01 et HDF5 sélectionnés passent. |
| Absence de corruption silencieuse | **PASS pour les défauts reproduits** | Refus JSON sur cible existante; course de création HDF5 ne supprime pas le fichier concurrent; HarmonicResult refuse des listes désalignées; métadonnées dérivées incohérentes v1 refusées. |
| Provenance, complexité et identités | **PARTIEL** | Les DTO et checkpoints conservent les identités déclarées et les phasors réel/imaginaire. Seuls les contrats ciblés ont été testés; aucun flux de calcul ou checkpoint complet n’a été exécuté. |
| Maturités et statuts scientifiques | **PASS comme préservation** | C01, C02, D01, D02 et E01 restent limités aux états propres documentés. Aucun résultat de ce dossier ne les promeut. |
| Gate d’intégration complet | **OUVERT** | Aucune campagne FEM réduite n’a été lancée; aucun nouveau manifeste avec entrées gelées, budget, allowlist de nodeids et décision Owner n’a été fourni. Les tests historiques n’ont pas été rejoués. |
| Décision de clôture | **OUVERTE** | La reprise est autorisée par la mission, mais la clôture administrative ou scientifique appartient à l’Owner. La décision sur les formats hétérogènes et le séquencement est demandée ci-dessous. |

## Findings

- **P0 : aucun identifié** dans les audits API et sérialisation exécutés.
- **P1 : aucun défaut WP11 de code identifié** dans ce périmètre. Les limites scientifiques E01 et les gates D01 non acquis demeurent des limites des work packages propriétaires.
- **P2 corrigés :** remplacement silencieux de JSON, suppression possible d’un fichier HDF5 concurrent, troncation par `zip()` d’un résultat harmonique, et métadonnées dérivées contradictoires dans deux DTO versionnés.
- **P2 résiduel :** certains types visibles dans la signature de `FiniteElementModel` ne sont pas exportés comme symboles autonomes par la façade. `load_model()` est le chemin documenté et les signatures existantes concordent; décision d’ergonomie non bloquante.
- **Décision Owner résiduelle :** suffisance des contrats résultat hétérogènes et portée du séquencement D01/C02 au regard du gate WP11.

## Tests et exclusions

Quatorze fonctions de test explicites ont réussi, avec zéro échec et zéro saut. Elles couvrent l’inventaire/API, les refus, les DTO synthétiques D01/Modal-Newmark/harmonique et l’I/O HDF5. Ruff, compilation/import ciblés et `git diff --check` réussissent également. Les nodeids exacts et commandes figurent dans `regression_manifest.json`.

Aucun assemblage FEM ou solveur n’a tourné. Les tests de campagnes, les simulations D02/C01/C02/E01, la dynamique réduite, les campagnes grandes tailles, Docker, MPI et solveurs externes sont exclus. Ils ne peuvent pas être remplacés par les round-trips synthétiques. Un gate d’intégration qui exige une exécution FEM reste à démontrer avec un mandat concret gelant l’identité source et des entrées, le budget et les nodeids autorisés.

## Proposition

Maintenir `WP11=OPEN` en attendant les réponses Owner dans `owner_decision_request.md` et, si exigé, un mandat ciblé d’intégration FEM. Ce dossier n’inscrit aucun nouveau statut à la roadmap et ne modifie pas le ledger historique.
