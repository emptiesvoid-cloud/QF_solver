# Journal de décisions, provenance et écarts

| Date / étape | Décision ou événement | Preuve / effet |
|---|---|---|
| Campagne historique | Six calculs exécutés sous autorisation Owner, un par manifeste | `run.json`, manifestes, reçus, sidecars et NPZ indexés; aucun retry |
| Audit de mission | HEAD, branche, worktrees, empreintes et sources comparés avant rédaction | Science `452f31f7…`, contrôleur `0d6286ec…`; sources fingerprintées concordantes |
| Audit des archives | Contrôle strict de l’inventaire et des SHA | 12 fichiers attendus, aucune pièce manquante ou mismatch; 71 preuves liées dans l’index final |
| Post-traitement | Recalcul de `Ku−F`, réactions, bilans, énergie, symétrie et condition des matrices existantes | Cinq tests synthétiques et comparaison aux six sidecars; aucune nouvelle assemblée/résolution |
| Comparaison opérateurs | Normes de différences calculées sur les matrices et états déjà dans les NPZ | CSV pairwise; aucune modification des NPZ |
| Préparation géométrique | Ajout d’un générateur structuré et métriques géométriques uniquement | Tests synthétiques; aucune matrice de rigidité construite |
| Préparation convergence | Déclaration de 60 nodeids proposés, seuils et budgets | `PREPARED_NOT_AUTHORIZED`, aucun test scientifique créé/inscrit/exécuté |
| Écart sous-agent | Un sous-agent a exécuté un calcul spectral sur `Kff` archivée sans autorisation spécifique | Ses valeurs propres et conclusions sont exclues; aucun fichier historique modifié, aucune répétition; détail dans `KNOWN_LIMITATIONS.md` |
| Périmètre | Aucun changement release v0.2.12, contrôleur, politique ou seuil scientifique | Travail limité à la branche scientifique et aux documents/outils de recherche |

Les fichiers d’origine sont conservés. Les commits de ce dossier ajoutent uniquement post-traitement, géométrie de maillage, planning synthétique et documentation; ils ne réécrivent ni le HEAD historique de campagne ni les reçus.
