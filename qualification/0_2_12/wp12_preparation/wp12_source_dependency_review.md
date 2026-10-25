# WP12-0 — Revue des dépendances et projection modale

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## Identité et preuves disponibles

Base locale et distante contrôlée : `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`, arbre de travail propre. Les commits examinés sont `1f3148fc0ad533c1a8518fd13e206778be2b07c4` (projection structurée) et `b5501e1ce93c0a98daf952b81927699a2e36fc06` (tests). Les blobs au HEAD sont `e363e0b35e8a628dcd63fa8d18fb97fd8b1534db` pour `modal_basis.py`, `3f333730620246110e5e51ceb91ddc3cd2cec642` pour `modal_basis_numerics.py` et `20889499b60cdd4fa79b2a2d2f76626279ed3e8e` pour `test_modal_symmetric_projection.py`.

Ce qui suit est une lecture statique des diffs, sources, contrats et rapports. Aucun des cinq nouveaux tests n'a été lancé; aucun solveur ou calcul n'a été invoqué. Les PASS des rapports cités restent attachés aux sources et scénarios historiques.

## Changement de projection

Dans [modal_basis.py](../../../src/solveur/core/analyses/modal_basis.py), `ModalBasis.from_prepared` calcule une seule fois les métriques d'asymétrie de K et réutilise le booléen d'égalité exacte. K et M restent refusées si l'erreur relative de symétrie excède `1e-12`; cette limite provient du contrat WP04, elle n'a pas été changée. M conserve la projection bilinéaire existante.

Pour K exactement symétrique dans son stockage sparse, [modal_basis_numerics.py](../../../src/solveur/core/analyses/modal_basis_numerics.py) calcule `K @ Φ`, évalue chaque bilinéaire du triangle supérieur, puis recopie le scalaire dans l'entrée symétrique. Cela utilise l'identité mathématique pour K symétrique exacte; la matrice globale K n'est ni réparée ni moyennée. Les zéros explicites sont éliminés avant l'inspection de l'égalité exacte. Si K est tolérée par le contrôle relatif mais pas exactement symétrique bit-à-bit, le code conserve l'ancienne expression `Φ.T @ (K @ Φ)`. L'entrée au-dessus de `1e-12` reste refusée.

Les contrôles en aval visibles restent actifs : matrices finies, symétrie projetée, erreur de paire propre, résidu et orthogonalité de masse. Le contrat WP04 conserve les limites `1e-12` symétrie, `1e-8` résidu et orthogonalité, `1e-8` écart relatif de cluster, ainsi que le seuil SPD numérique documenté; ces seuils sont des critères de leurs contrats, pas une preuve formelle SPD.

Le même train d'intégration comprend une option distincte `rayleigh_structured`: pour Rayleigh déclarée, `Cr = αMr + βKr` est comparée à la projection directe avec la limite existante `1e-8`; `legacy_direct` reste la voie par défaut. La preuve D01 archivée sur opérateurs M3 est limitée à ces opérateurs et ne couvre pas à elle seule le nouveau `Kr` sur plusieurs bases/maillages ni tous ses consommateurs.

## Graphe de dépendance concret

```text
PreparedDynamicSystem (M_full, K_full, P, identités)
        │
        ├── ModalBasis.from_prepared
        │      ├── Mr = Φᵀ M Φ                 (voie inchangée)
        │      └── Kr = project(K, Φ)          (voie structurée si K exacte)
        │              │
        │              ├── reduced_harmonic : Zr(ω)=Kr+iωCr−ω²Mr
        │              ├── modal_newmark : opérateur de raideur réduit Kr
        │              ├── damping Rayleigh structurée (optionnelle)
        │              └── diagnostic/flexibilité résiduelle (reprojection et comparaison)
        │
        └── WP07 accélération de base
               ├── excitation WP03 projetée dans Φ
               ├── harmonique réduit WP05
               └── transitoire Newmark modal WP06
```

| Classe d'impact | Composant / preuve | Motif et action de contrôle |
|---|---|---|
| Directement affecté | WP04 `ModalBasis`: `Mr`, `Kr`, diagnostics et digest d'identité | K exacte prend désormais la voie structurée; faible variation de dernier bit possible même si la formule est équivalente. Exécuter les cinq tests ciblés et un oracle analytique modal indépendant. |
| Directement affecté | WP05 harmonique réduit | Le consommateur lit `basis.projected_stiffness` comme `Kr` (`reduced_harmonic.py`, formation de l'impédance). Inclure oracle complexe indépendant et route plein-basis/directe dans leurs limites distinctes. |
| Directement affecté | WP06 Newmark modal | Le consommateur lit `Kr` dans l'équation modale. Inclure un oracle analytique transitoire et une comparaison plein-basis/directe; la seconde partage davantage de code. |
| Affecté indirectement | WP07 base uniforme | Compose WP03, WP04, WP05 et WP06; vérifier ses oracles harmoniques et transitoires si cette route reste dans le scope de livraison. |
| Potentiellement affecté | Flexibilité résiduelle D01 | Reprojette `ΦᵀKΦ`, compare à la base puis symétrise pour la factorisation; une petite différence peut changer son gate d'égalité. D01 est optionnelle, `INCONCLUSIVE`, pas un prérequis général; contrôler son refus par défaut et son opt-in si inclus au scope. |
| Non affecté directement | WP02 préparation de M/K/P/identité physique et WP03 construction des canaux | Les commits ciblés ne modifient pas ces fichiers; leurs preuves propres restent séparées de l'utilisation de `Kr` par la base. |
| Non affecté | Routes classiques hors `ModalBasis` et rotor dense | Pas de dépendance directe identifiée dans les imports/appels du code inspecté; des routes communes (router, résultats, sérialisation) restent à vérifier par WP12-4. |
| Indéterminé | Clients externes/persisted DTO qui interprètent le digest de base ou les octets projetés | Aucun inventaire hors dépôt n'est disponible; vérifier la compatibilité documentée et ne pas supposer une identité sérialisée stable au dernier bit. |

## Contrôles statiques et nœuds candidats présents

Les cinq nœuds ajoutés par `b5501e1` couvrent les cas suivants :

- `tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form`
- `tests/unit/test_modal_symmetric_projection.py::test_modal_basis_uses_structured_projection_for_exact_symmetric_k`
- `tests/unit/test_modal_symmetric_projection.py::test_from_prepared_reuses_one_sparse_symmetry_difference`
- `tests/unit/test_modal_symmetric_projection.py::test_tolerated_near_symmetric_k_falls_back_to_historical_bilinear_path`
- `tests/unit/test_modal_symmetric_projection.py::test_from_prepared_rejects_significantly_asymmetric_stiffness`

Compléments ciblés, définis dans les fichiers présents :

- WP04 : `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators` et `::test_prepared_modal_basis_supports_each_wp00_family`.
- WP05 : `tests/unit/test_reduced_harmonic.py::test_reduced_impedance_matches_independent_analytical_sdof_amplitude_and_phase`, `::test_coupled_two_dof_complex_response_uses_full_projected_operators` et `::test_full_basis_reduced_harmonic_matches_direct_rayleigh_route_and_zero_hz`.
- WP06 : `tests/unit/test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection`, `::test_full_basis_matches_direct_newmark_when_damping_and_excitation_match` et `::test_restart_matches_continuous_run_and_refuses_corrupt_or_incompatible_checkpoint`.
- WP07 : `tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames` et `::test_transient_base_sdof_matches_independent_constant_acceleration_solution`.

Ces noms sont résolus par inspection de source, pas par `pytest --collect-only`; les commandes demeurent des propositions futures. Les rapports WP04–WP07 enregistrent des PASS historiques et les seuils de contrat, mais les runs ciblés sont antérieurs à `1f3148f`; ils restent utiles pour leurs sources d'origine. Le rapport D01 de projection/réduction documente une relecture de l'archive M3, mais M1/M2 manquent et cela ne démontre pas le nouveau `Kr` sur WP04–WP07.

## Ensemble minimal proposé

1. Les cinq tests `test_modal_symmetric_projection.py` : branche exacte, calcul structuré, unique passe de symétrie, fallback quasi symétrique et refus hors tolérance.
2. Un test analytique WP04 sur système couplé à masse non diagonale et un cas modal de famille WP00.
3. Un oracle complexe WP05 (amplitude/phase) et un cas de comparaison directe plein-basis distinct, sans confondre leurs niveaux d'indépendance.
4. Un oracle analytique Newmark WP06 et le refus/reprise de checkpoint exact; la comparaison directe reste un contrôle de non-régression, pas un oracle indépendant.
5. Les oracles indépendants WP07 si l'accélération de base est dans la portée candidate; sinon documenter l'exclusion et conserver le verdict historique.

Pour éviter de surcharger le gate, les suites complètes WP04–WP07, les grilles de maillage générales et l'optique D01 expérimentale ne sont pas exigées par ce changement seul. Le rejet, le fallback, la tolérance et les critères gelés ne peuvent pas être modifiés après observation.
