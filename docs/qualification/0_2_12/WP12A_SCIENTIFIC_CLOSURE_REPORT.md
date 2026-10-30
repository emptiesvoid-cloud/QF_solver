# WP12-A — Rapport de clôture scientifique proposé

**Statut : WP12A_SCIENTIFIC_CLOSURE_REVIEW_READY.** Quatre expériences ciblées ont un PASS de développement traçable. Cette proposition demande une décision Owner ; elle ne clôture ni WP12 dans son ensemble ni la qualification du solveur. Audit des fichiers disponibles au 28 octobre 2026 ; release vérifiée au commit `914c8e49f6723cb3c7485362b3b7ef04e3976fa8`.

## Résultats et portée

| Cas | Série | Résultat vérifié | Niveau de preuve |
|---|---|---|---|
| WP07 harmonique | dev-a3083df78b03 | PASS ; SDOF à 1,25 Hz, excitation 1,7i ; résultats numériques bruts NOT_EXPOSED | A, B par assertions, C conditionnel aux matrices assemblées |
| Newmark r3 | dev-b81ed5a46142 | PASS, 34/34 ; ordres déplacement 1,99724 et 1,99931 ; énergie libre et résidus réduits archivés | A, B, C analytique SDOF conditionnel à K/M |
| Harmonique réduit | dev-0dd64d435dd1 | PASS, 11/11 ; écart complet/direct maximal 2,27963e-16 ; résidu libre 2,48253e-16 N | A, B ; comparaison directe partage assemblage et solveur, pas C indépendant de ces éléments |
| Base complexe | dev-f5bae47755b8 | PASS, 48/48 ; fréquence propre 8,717275 Hz, résidu libre maximal 1,590e-15 N | A, B, C scalaire conditionnel à K/M |

A = contrat d’implémentation ; B = vérification numérique ; C = comparaison indépendante dans la limite des composants partagés ; D = validation physique externe. **Aucun niveau D n’est acquis par ces quatre essais.** Ces niveaux sont non exclusifs et concernent les cas, pas les fonctionnalités entières.

## Analyse et restrictions

WP07 vérifie à 1 DDL la réponse relative et absolue et le signe de l’excitation avec une équation scalaire partageant l’assemblage ; `rel=1e-11, abs=1e-13` pour les déplacements, tolérances pytest par défaut pour la cinématique. Les matrices, réponses et erreurs mesurées sont NOT_EXPOSED ; aucun résidu ni bilan d’énergie n’est affirmé. Le PASS ne les reconstitue pas.

Newmark β=0,25, γ=0,5, temps final 0,08 s, pas 0,002/0,001/0,0005 s : déplacements et références SDOF, ordres ≥1,8, résidus réduits ≤1e-7 et dérive énergétique relative ≤1e-10. L’énergie concerne une vibration libre sans force et sans amortissement ; le résidu modal n’est pas un résidu FEM global. Le travail extérieur est nul par construction mais non mesuré dans un champ archivé.

Harmonique réduit : matrices, réponses complexes et résidus sont archivés. La base complète/directe partage modèle, assemblage et composants de résolution. La base tronquée a une charge projetée nulle, réponse nulle, résidu modal nul et résidu physique libre de 1 N ; cela illustre qu’un résidu projeté nul n’est pas une garantie d’erreur physique. L’écart tronqué/direct n’est pas une borne garantie de troncature.

Base complexe : convention `exp(+i omega t)`, 0,7−0,4i m/s² hors DC, fréquences 0, 0,5, 0,98 et 1,02 fois la fréquence propre ; les déplacements et vitesses absolus DC restent indisponibles et une phase de phasor nul est indéfinie. Référence scalaire et résidu libre partagent les opérateurs assemblés.

## Historique des tentatives

Les deux ledgers officiels comptent 10/130 tentatives : cinq héritées et cinq v2. SHA-256 historique `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`, Dynamics v2 courant `01aec735ca1f7bfc06f4873df533089bda3f9253555911885ef5dc5b9ba9dd88`. Le prédécesseur v2 est lié au ledger historique ; les deux échecs Newmark restent consommés.

### Historique

| Nodeid (fonction) | Série | État |
|---|---|---|
| `test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | `dev-42c3e52f32fc` | `PASS` |
| `test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | `dev-a81c2f0d9e74` | `PYTEST_FAILED` |
| `test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | `dev-74c6cb1e73a1` | `PASS` |
| `test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation` | `dev-7b5e16653765` | `PASS` |
| `test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` | `dev-9a95b817d69d` | `PASS` |

### Dynamics v2

| Nodeid (fonction) | Série | État |
|---|---|---|
| `test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | `dev-301ba3b31a43` | `PYTEST_FAILED` |
| `test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | `dev-b81ed5a46142` | `PASS` |
| `test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation` | `dev-0dd64d435dd1` | `PASS` |
| `test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames` | `dev-a3083df78b03` | `PASS` |
| `test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` | `dev-f5bae47755b8` | `PASS` |

Les refus avant réservation des décisions harmonique réduit et base complexe après mutation du ledger sont archivés sous `E:\QFSolverAgents\evidence\dynamics\refusals` ; ils ne sont pas des tentatives. Le Newmark `dev-301ba3b31a43` est PYTEST_FAILED à la publication du sidecar (infrastructure), avant assertions finales ; son verdict mécanique est non établi. Le Newmark historique `dev-a81c2f0d9e74` reste PYTEST_FAILED, sans reclassement. Les préflights collect-only ne sont pas des exécutions scientifiques ; les manifestes préparés non autorisés ne sont pas des autorisations.

L’index historique Newmark référence le ledger **vivant** avec son SHA-256 d’alors `0c519e3cbc4db33b4c520a4bcfa5aec92e7688deb4979449e9394d3f768932c0`, différent du SHA courant. L’instantané `E:\QFSolverAgents\evidence\dynamics\reports\wp12a-newmark-r3-owner-20261028\ledger-final-snapshot.json` a bien l’empreinte historique : divergence temporelle expliquée, index historique conservé inchangé.

Les chemins d’archives sont locaux à la machine Windows ; les SHA-256 et chemins sont des références de vérification, non un stockage immuable ou une preuve cryptographique d’auteur. Les identités différentes des quatre exécutions ne prouvent pas, à elles seules, une exécution des quatre cas sur un HEAD scientifique unique actuel. Voir [matrice des preuves](WP12A_EVIDENCE_MATRIX.md), [lacunes](WP12A_REMAINING_VALIDATION_GAPS.md) et [préparation release](WP12A_RELEASE_READINESS.md).
