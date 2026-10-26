# Matrice de provenance et confiance

| Preuve / résultat | Source principale | SHA contrôlé | Liaison | Statut et limite |
|---|---|---|---|---|
| Six manifestes | `campaign_preparation/manifest_<case>.json` | Oui; chacun indexé | `run.json` contient cas, nodeid, SHA manifeste | PASS intégrité; manifestes historiques autorisés |
| Six reçus preflight et checksums | namespace de run contrôleur | Oui; reçus liés à `run.json`, sidecar SHA vérifié | Nodeid, fingerprint, SHA manifeste | PASS; corps de test non exécuté pendant preflight |
| Six reçus calcul | namespace de run contrôleur | Oui pour `run.json`, stdout, stderr | Identité contrôleur/science, code, tentative, source fingerprint | PASS; `run.json` ne pointe pas directement sur sidecar/NPZ |
| Six sidecars | archive historique | Oui; hash calculé et indexé | Manifest identity, science/controller identity, state SHA | PASS |
| Six états NPZ | archive historique | Oui; référence SHA du sidecar concordante | Matrices `K/Kff`, `F`, `u`, DOFs, réactions, etc. | PASS; état numérique d’origine, aucune réécriture |
| Recalcul résidu/réactions/bilans/énergie | `archive_audit.py` exécuté sur NPZ existants | Résultats dérivés; preuves sources inchangées | Comparaison exacte à précision float64 sidecar | Cohérence interne, non oracle indépendant |
| Différences `K` et `u` par formulation | `FORMULATION_PAIRWISE_DIFFERENCES.csv` | Source NPZ référencée par SHA dans chaque ligne | Matrices/états archivés appariés par `ν` | Post-traitement, aucun assemblage/résolution |
| Facteur 8, `Kdev/Kvol/Ktotal` | `operator_comparison_results.json`, script et rapport antérieurs | Tous indexés et hashés | Cube affine, référence énergétique fermée, tests rouge/vert décrits | Preuve exacte du cas analytique; généralisation limitée |
| Tendance de convergence historique | rapports WP10 commités | SHA Git de la branche | Oracle Timoshenko, niveaux 4/8/16 | Preuve séparée, bornée, raffinement axial seulement |
| Distorsion / maturité WP13-12 | contrat, runner et manifeste historiques | Version historique commitée; non modifiée | Critères retenus dans le manifeste | Gates énergie/équilibre FAIL; famille `stretched` dupliquée |
| Études futures | protocoles et CSV proposés ici | Hash des documents dans livraison Git | Aucun manifeste/exécution autorisé créé | `PREPARED_NOT_AUTHORIZED` |

## Règles de provenance

- Les originaux de campagne résident dans leur namespace historique; aucun déplacement, renommage ou remplacement n’a été fait.
- `SHA256SUMS.txt` est un index des pièces sources, pas une signature d’approbation Owner.
- L’index n’infère pas PASS lorsqu’un critère est observé sans seuil.
- Les états K-u sont conservés avec unités SI; une conversion mm/mJ ne modifie jamais les valeurs sources.
- Le résumé public ne publie aucun chemin local de machine.
