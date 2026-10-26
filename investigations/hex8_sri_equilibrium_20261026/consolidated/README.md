# HEX8-SRI — dossier scientifique consolidé

**Statut : `EXPERIMENTAL_GLOBAL_PASS_BOUNDED`**

**Convergence spatiale : `SPATIAL_CONVERGENCE_NOT_ASSESSED`**

**Recommandation : `RESEARCH_ONLY`**

Ce dossier consolide la preuve élémentaire du poids de Gauss, les six calculs globaux historiques autorisés, leurs archives et les protocoles de validation encore à autoriser. Il ne constitue ni une qualification générale ni une décision d’intégration en production.

## Documents

- [Rapport scientifique principal](HEX8_SRI_RESEARCH_REPORT.md)
- [Résumé pour revue Owner](OWNER_REVIEW_SUMMARY.md)
- [Audit de formulation](THEORY_AND_FORMULATION_AUDIT.md)
- [Reproductibilité des six calculs](CAMPAIGN_REPRODUCIBILITY.md)
- [Comparaison structurelle bornée](STRUCTURAL_COMPARISON.md)
- [Limites connues](KNOWN_LIMITATIONS.md)
- [Matrice de provenance](PROVENANCE_MATRIX.md)
- [Index des preuves vérifiées](EVIDENCE_INDEX.json)
- [Empreintes des pièces sources](SHA256SUMS.txt)
- [Résultats des six cas](SIX_CASES_RESULTS.csv)
- [Différences des matrices assemblées archivées](FORMULATION_PAIRWISE_DIFFERENCES.csv)
- Figures : [déplacement moyen chargé](figures/loaded_face_displacement.svg) et [conditionnement](figures/condition_number.svg)
- [Matrice proposée pour la campagne suivante](../NEXT_CAMPAIGN_MATRIX.csv)
- [Matrice complémentaire patch/distorsion/stabilité](../SUPPLEMENTAL_VALIDATION_MATRIX.csv)
- Protocoles de [convergence](MESH_CONVERGENCE_PROTOCOL.md), [quasi-incompressibilité](NEAR_INCOMPRESSIBLE_PROTOCOL.md), [distorsion et stabilité](DISTORTION_STABILITY_PROTOCOL.md), [référence indépendante](INDEPENDENT_REFERENCE_PLAN.md)
- [Matrice de risques d’intégration](INTEGRATION_RISK_MATRIX.csv)
- [Synthèse publique prudente](PUBLIC_RESEARCH_SYNTHESIS.md)
- [Journal de décisions et écarts de processus](DECISION_LOG.md)

## Ce qui a été exécuté dans cette mission

Seuls des contrôles statiques, des tests unitaires synthétiques, la vérification SHA-256 et le post-traitement des états déjà archivés ont été exécutés. Aucun nouvel assemblage, calcul FEM, résolution, calcul modal ou eigensolve n’a été lancé par l’agent principal. Les essais synthétiques construisent de petits tableaux de ressorts ou de géométrie; ils ne chargent pas le solveur.

Les six résolutions citées ici sont les résultats historiques fournis par l’Owner et vérifiés par leurs manifestes, reçus et archives. Leur PASS est limité aux critères effectivement figés dans cette campagne.

## Index d’intégrité

`EVIDENCE_INDEX.json` décrit 71 pièces sources indexées. Le sous-ensemble d’archive structurelle contient exactement six sidecars JSON et six états NPZ. Les fichiers originaux restent dans leur namespace historique et ne sont ni déplacés ni réécrits. Le SHA indiqué dans `SHA256SUMS.txt` concerne les preuves sources, pas les documents dérivés de ce dossier.

Un reçu `run.json` lie directement son manifeste et son reçu de préflight, mais ne porte pas le SHA du sidecar et du NPZ. Le lien calcul→sidecar est donc corroboré par le nodeid unique, l’empreinte de manifeste, le fingerprint scientifique, les identités du contrôleur et la référence SHA du NPZ portée par le sidecar. Cette limite est explicitée dans l’index.
