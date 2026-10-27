# Journal de décisions, provenance et écarts

## 2026-10-27 — Préparation de la convergence HEX8-SRI

- Base : branche `research/hex8-sri-equilibrium`, HEAD de départ `c3f6b29b89f3e551dd66112c2efa72fceb222281`. Aucun calcul FEM, assemblage global ou eigensolve nouveau n’a été lancé.
- Ajout d’un pilote sparse strictement gardé, d’une spécification immutable de 24 cas, de fonctions de post-traitement d’archives et de tests unitaires synthétiques. Le post-traitement distingue les différences entre maillages d’une erreur contre référence et refuse cette dernière sans oracle qualifié et incertitude documentée.
- Contrôles : 13 nodeids unitaires exécutés individuellement, 21 tests/paramètres PASS; Ruff check, format check et analyse AST PASS. Aucun nodeid du module FEM de convergence n’a été collecté ou exécuté.
- Cinq nodeids unitaires préexistants de qualité géométrique passent aussi. Sept géométries de la matrice complémentaire ont été évaluées avec les seuls déterminants/Jacobiens échantillonnés et métriques de forme; aucune matrice de rigidité, assemblage ou résolution n’a été appelée. Le severe shear reste échantillonné positif (`scaled J_min≈0.2502`); les géométries étirées montrent que `scaled J=1` ne détecte pas seul les rapports d’aspect 100/200.
- Le pilote a généré 24 manifests brouillons non autorisés, liés au HEAD scientifique `7ff2809a854e1434619c261195e78b901be0ea78`, fingerprint `1fce68d6b2f2702c794e37d73c16414e0d0e4c0f2837331e5792b6fbfb414555` et identité contrôleur provisoire `0d6286ec…`. Les 24 hashes sont contrôlés contre `SHA256SUMS.txt`; tous portent `execution_authorized=false`, `do_not_execute=true`, sans préflight.
- Le contrôleur `codex/hex8sri-controller-registration` n’inscrit que la campagne historique de six cas; aucune extension ni préflight n’est fabriqué. La demande exige que le chemin du manifeste soit passé au child exclusivement depuis l’entrée contrôleur enregistrée.
- Timoshenko reste une vérification de signe, unité, ordre de grandeur et tendance seulement. L’oracle 3D de précision mixte n’est ni installé ni qualifié. La précision continue ne pourra pas être affirmée sans cette référence.
- Les six archives historiques, les preuves originales et leurs SHA restent inchangés. Les fichiers de préparation sont de nouveaux artefacts sur la branche scientifique.

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
| 2026-10-27 — relance de recherche | Vérification en lecture seule de l’identité science et des six archives | Science `c3f6b29b89f3e551dd66112c2efa72fceb222281`, remote identique; index des 71 pièces et six états intacts |
| 2026-10-27 — oracle poutre | Vérification analytique de la charge, l’encastrement, la moyenne Q1 de face et deux facteurs de cisaillement | Timoshenko ≈32,062/32,072 mm; contrôle indépendant d’échelle/tendance, pas oracle 3D serré |
| 2026-10-27 — première convergence | Préparation du pilote sparse et des 24 cas `3 formulations × 2 ν × 4 niveaux` | Statut `PREPARED_NOT_AUTHORIZED`; aucun nodeid inscrit ou exécuté; 8,3 h max séquentielles proposées |
| 2026-10-27 — contrôleur | Vérification du contrôleur officiel avant nouveau préflight | Scope actuel limité à 6 anciens nodeids, 180 s/1 024 MiB et module structurel; extension de configuration nécessaire, aucune modification appliquée |
| 2026-10-27 — référence indépendante | Vérification des backends locaux et préparation du plan mixte 3D | DOLFINx/FEniCSx/PETSc/scikit-fem absents; aucun oracle numérique 3D ni fingerprint final; précision physique toujours non évaluée |
| 2026-10-27 — contrôles | Tests synthétiques explicites du générateur de maillage/charge et de l’oracle analytique | 8 nodeids, 16 paramètres PASS; aucun test FEM, assemblage ou eigensolve lancé |
| Périmètre | Aucun changement release v0.2.12, contrôleur, politique ou seuil scientifique | Travail limité à la branche scientifique et aux documents/outils de recherche |

Les fichiers d’origine sont conservés. Les commits de ce dossier ajoutent uniquement post-traitement, géométrie de maillage, planning synthétique et documentation; ils ne réécrivent ni le HEAD historique de campagne ni les reçus.
