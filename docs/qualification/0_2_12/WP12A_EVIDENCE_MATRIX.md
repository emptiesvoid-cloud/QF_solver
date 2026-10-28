# WP12-A — Matrice des preuves

Les chemins `E:\QFSolverAgents\evidence\dynamics` sont externes au dépôt et spécifiques à la machine. SHA-256 vérifiés sur les octets présents. Chaque ligne d’assertion des trois sidecars nomme la preuve qui la contient ; pour WP07, les assertions sont dans la source et le PASS pytest est dans stdout, sans valeurs brutes.

## Identités, archives et décisions

| Cas / nodeid exact | HEAD source / fingerprint | HEAD contrôleur | Tentative, budget et PASS |
|---|---|---|---|
| WP07 harmonique<br>`tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames` | `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66`<br>`969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6` | `148f850412c907e62ae899961afc8ce5b18d0ded` | `dev-a3083df78b03` ; 1 DDL, 300 s ; 1 passed |
| Newmark r3<br>`tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | `5f96dd604fe40279ead0186f49be77e7a0bbeac1`<br>`d4743785db99a79181281429827d0de688e5eae94e9ad285491040aaa75c7a8e` | `b206e6f520e9b03c3c925c3bef20883f01aa9800` | `dev-b81ed5a46142` ; 1 DDL, 300 s ; 1 passed |
| Harmonique réduit<br>`tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation` | `bf88803a8464a805e953013a2593fb06e6ea4659`<br>`dea993f995b07804b5ca9baf9cccb84615bc14313ccac7934694ca24d3f5e995` | `d379820e794653bde65cae193c920b34d38a0fa3` | `dev-0dd64d435dd1` ; 3 DDL, 300 s ; 1 passed |
| Accélération de base complexe<br>`tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` | `7406e34efc28ed8f18c15440115595dfa3dd9ca5`<br>`a7dcb27d51a4b4a99bbf288258581c21f4cffc3e5f899de91de9b3e68d53c6fc` | `1b8d6a76b062039566dbf0f2bd508b7990035dca` | `dev-f5bae47755b8` ; 1 DDL, 300 s ; 1 passed |

Pour chaque cas, les chemins et empreintes ci-dessous sont issus des reçus et décisions :

| Cas | Artefact | Chemin absolu | SHA-256 |
|---|---|---|---|
| WP07 harmonique | rapport | `E:\QFSolverAgents\evidence\dynamics\reports\WP12A_WP07_OWNER_AUTHORIZED_EXECUTION_REPORT.md` | `35bf803b2f6f0e63e1e3ee2a24bbc4898749992f1d9f7309d321aea7ff0ca732` |
| WP07 harmonique | run.json | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-a3083df78b03\attempt-0001\run.json` | `a4042d940255eb7e1f62ca1a9ec6e0df3a2d87cfa39ec407e4e1fbcf4eeb3efa` |
| WP07 harmonique | stdout | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-a3083df78b03\attempt-0001\output\stdout.log` | `65e5de5ab6c0bc9f85dc1c1afeb72a7e080168aeeeb38365260f7b643afe0a35` |
| WP07 harmonique | préflight | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\preflight\pf-5b4d23fc8a97\preflight.json` | `3244c8b4120eb1859f0996e33197f600c356d57d4ff4923086e1edfeec0daff0` |
| WP07 harmonique | manifeste préparé | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\wp12a-wp07-148f850-20261028-r1.json` | `86cd2d513d2686cd2a60f2c7d69e2757bb4473fe33322c61a84d44747c36dea2` |
| WP07 harmonique | manifeste autorisé | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\owner-authorized\wp12a-wp07-148f850-20261028-r1.json` | `d9979ddf0e025adc8e8f8eb9b5834e1b3afd37788fa53df50a53ba89c6d9c006` |
| WP07 harmonique | décision Owner | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\owner-decisions\execution\owner-wp12a-wp07-single-attempt-20261028.json` | `d8257878b3d34077cf8d8cca0581d90bfa5b27042d1edcf32aceb78d9af993b1` |
| Newmark r3 | rapport | `E:\QFSolverAgents\evidence\dynamics\reports\WP12A_NEWMARK_R3_OWNER_AUTHORIZED_EXECUTION_REPORT.md` | `4176d925787d7dafa113b63541b3c2ef22f7d0a32374311bacbb45b115d4503f` |
| Newmark r3 | run.json | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-b81ed5a46142\attempt-0001\run.json` | `632d6cf9fae05d6f868ff9ba6f509ec2d013324e6e426ad9459692d182c26524` |
| Newmark r3 | stdout | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-b81ed5a46142\attempt-0001\output\stdout.log` | `7747b5d8539a52bf9ab14b8c43bc7c01aaf47e433e6c496809228a3059f1c447` |
| Newmark r3 | préflight | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\preflight\pf-3e441fac9f29\preflight.json` | `ee79506bef82e27a6e56bc25b2fb035f363e3a74377d2dd018f6c1b7312e3770` |
| Newmark r3 | manifeste préparé | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\wp12a-newmark-b206-20261028-r3.json` | `665245fc37958161ebe54c473097082f845190f7855dd3e8cc62bf96ef698bed` |
| Newmark r3 | manifeste autorisé | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\owner-authorized\wp12a-newmark-b206-20261028-r3.json` | `67a0dd61ab805e1c1020963fd95c7ca53558ca9aa05c256cb614ecda3974df86` |
| Newmark r3 | décision Owner | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\owner-decisions\execution\owner-wp12a-newmark-r3-20261028.json` | `4b3b56b953216616b005c36f6e9c85855919422fe41f42176a638077372021b3` |
| Newmark r3 | sidecar | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-b81ed5a46142\attempt-0001\output\wp12-newmark-fixed-time-observables.json` | `91b3ac5c8d80ecaaa23e53467e6bd5efdc7025eea27dae9963579b560a88a409` |
| Harmonique réduit | rapport | `E:\QFSolverAgents\evidence\dynamics\reports\WP12A_REDUCED_HARMONIC_OWNER_AUTHORIZED_EXECUTION_REPORT.md` | `4301bbb8bbcf6720cde8fcaf7c53bd8706bee5806cfed5810b2b376c2d0f27b7` |
| Harmonique réduit | run.json | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-0dd64d435dd1\attempt-0001\run.json` | `824644bd9c29b90550701adf34f07ef6287ed974151868ff49d964214113c833` |
| Harmonique réduit | stdout | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-0dd64d435dd1\attempt-0001\output\stdout.log` | `12872ed32abcd8180ec4bd8bc9dfbca4517e08c82837630184765f92cbfb9363` |
| Harmonique réduit | préflight | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\preflight\pf-c9e4f15a38d2\preflight.json` | `af59adef877b89b4e7a2439dbe1fb38b15970aa5523383c8ecac98085ad36143` |
| Harmonique réduit | manifeste préparé | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\wp12a-harmonic-d379-20261028-r1.json` | `5856be36803657f48fcbf02e2ae9efd45dec1952f343cea14658037f02415b54` |
| Harmonique réduit | manifeste autorisé | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\owner-authorized\wp12a-harmonic-d379-20261028-r1.json` | `c4c6bd1eab33907f4fbf82a7aafc4e9d39cb728125375c2c07639a49cb3551a3` |
| Harmonique réduit | décision Owner | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\owner-decisions\execution\owner-wp12a-reduced-harmonic-20261028-r1.json` | `44c2be2560d7c39b6ac8241442d37db7aa45cb47b9eee6ac7c9d74aaafd250d5` |
| Harmonique réduit | sidecar | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-0dd64d435dd1\attempt-0001\output\wp12-harmonic-complex-sweep-observables.json` | `07493ac9822eee2a994b5984d1dffb358d6e3ca268c67a502c2bca381f8a022d` |
| Accélération de base complexe | rapport | `E:\QFSolverAgents\evidence\dynamics\reports\WP12A_BASE_MOTION_OWNER_AUTHORIZED_EXECUTION_REPORT.md` | `86078ea0dcd5e1800d5b4b5cd93949b66d96e57334df555d7b355bbfb857b8e4` |
| Accélération de base complexe | run.json | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-f5bae47755b8\attempt-0001\run.json` | `d4d1d18939b563764ea372067f60b2c9eb7a01db0c613194c02c09880ff8c55a` |
| Accélération de base complexe | stdout | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-f5bae47755b8\attempt-0001\output\stdout.log` | `90c48f87d13728922f442f9ad4137eb2c8f0d48b14318bb32a657d70f4b31b76` |
| Accélération de base complexe | préflight | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\preflight\pf-6e30c9b52af4\preflight.json` | `cd1003124538f487ff28ddfb1ee9375c958c910b006dfa7d69e7f1645e927acf` |
| Accélération de base complexe | manifeste préparé | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\wp12a-base-motion-1b8d-20261028-r1.json` | `a092514ddfd498b41dd190f98c949199c6c0e06b71c94f042c987e09a99b4c12` |
| Accélération de base complexe | manifeste autorisé | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\owner-authorized\wp12a-base-motion-1b8d-20261028-r1.json` | `6a4d6aec14867cb55f079ad79304a5ca006733fd966c054ed3727cce77358770` |
| Accélération de base complexe | décision Owner | `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\owner-decisions\execution\owner-wp12a-base-1b8d-20261028-r1.json` | `801759d68f74020658c35eedbcc4fc34da484dc2f28964061483661257cb3664` |
| Accélération de base complexe | sidecar | `E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\dev-f5bae47755b8\attempt-0001\output\wp12-base-acceleration-complex-sweep-observables.json` | `89174f406f5f1c2e5d9f136612e6355402dd6a4475cdf443e582a5412483255d` |

## Couverture et statut

| Fonctionnalité | Cas / observable et assertion | Oracle / niveau | Portée et statut |
|---|---|---|---|
| Signes, repères et sérialisation | WP07 ; comparaisons SDOF et round-trip ; stdout PASS | C conditionnel K/M + A | 1 DDL, mesures NOT_EXPOSED ; partiellement vérifié |
| Convergence temporelle et énergie | Newmark ; ordres, séries et 34 assertions sidecar | SDOF analytique conditionnel K/M ; B/C | Libre, 1 DDL, non amorti ; vérifié pour le cas |
| Résidu modal | Newmark ; résidu réduit ≤1e-7 | B, cohérence algébrique | Non global ; vérifié pour le cas |
| Projection et reconstruction | Harmonique réduit ; matrices, réponses et 11 assertions | B, voies avec composants partagés | 3 DDL TET4 ; vérifié pour le cas |
| Troncature | Harmonique réduit ; modal nul, résidu libre 1 N | B diagnostique | Pas de borne garantie ; partiellement vérifié |
| Base complexe / repères | Base complexe ; 48 assertions et six phasors | C scalaire conditionnel K/M ; A/B | 1 DDL BEAM2, DC et voisinage d’un mode ; vérifié pour le cas |
| Grands modèles, non-linéaire, validation externe | Aucun de ces quatre cas | D absent | Non vérifié |

## Assertions exactes archivées

Chaque nom ci-dessous est reproduit depuis `assertion_results` du sidecar identifié par son SHA-256 dans le tableau précédent. Les assertions de disponibilité et sérialisation sont de niveau A ; résidus et convergence B ; les comparaisons à la référence sont C seulement sous les limites de partage décrites plus haut.

### Newmark r3 — SHA-256 `91b3ac5c8d80ecaaa23e53467e6bd5efdc7025eea27dae9963579b560a88a409`

| Assertion exacte | État |
|---|---|
| dt=0.0005s beta remains 0.25 | PASS |
| dt=0.0005s ends at fixed final time | PASS |
| dt=0.0005s energy drift <= 1e-10 | PASS |
| dt=0.0005s energy drift is finite | PASS |
| dt=0.0005s execution duration matches fixed final time | PASS |
| dt=0.0005s execution step matches input | PASS |
| dt=0.0005s gamma remains 0.5 | PASS |
| dt=0.0005s has steps+1 samples | PASS |
| dt=0.0005s reduced residual <= 1e-7 | PASS |
| dt=0.0005s reduced residual is finite | PASS |
| dt=0.0005s starts at t=0 | PASS |
| dt=0.001s beta remains 0.25 | PASS |
| dt=0.001s ends at fixed final time | PASS |
| dt=0.001s energy drift <= 1e-10 | PASS |
| dt=0.001s energy drift is finite | PASS |
| dt=0.001s execution duration matches fixed final time | PASS |
| dt=0.001s execution step matches input | PASS |
| dt=0.001s gamma remains 0.5 | PASS |
| dt=0.001s has steps+1 samples | PASS |
| dt=0.001s reduced residual <= 1e-7 | PASS |
| dt=0.001s reduced residual is finite | PASS |
| dt=0.001s starts at t=0 | PASS |
| dt=0.002s beta remains 0.25 | PASS |
| dt=0.002s ends at fixed final time | PASS |
| dt=0.002s energy drift <= 1e-10 | PASS |
| dt=0.002s energy drift is finite | PASS |
| dt=0.002s execution duration matches fixed final time | PASS |
| dt=0.002s execution step matches input | PASS |
| dt=0.002s gamma remains 0.5 | PASS |
| dt=0.002s has steps+1 samples | PASS |
| dt=0.002s reduced residual <= 1e-7 | PASS |
| dt=0.002s reduced residual is finite | PASS |
| dt=0.002s starts at t=0 | PASS |
| minimum displacement convergence order >= 1.8 | PASS |

### Harmonique réduit — SHA-256 `07493ac9822eee2a994b5984d1dffb358d6e3ca268c67a502c2bca381f8a022d`

| Assertion exacte | État |
|---|---|
| comparison modal basis is truncated | PASS |
| direct/full/truncated frequency counts match | PASS |
| first natural frequency is positive | PASS |
| frequency-record counts match requested sweep | PASS |
| full modal basis is complete | PASS |
| full-basis physical free backward errors <= 1e-8 | PASS |
| full-basis reduced backward errors <= 1e-8 | PASS |
| full-basis vector relative error <= 1e-8 | PASS |
| last natural frequency exceeds first | PASS |
| natural-frequency count matches reduced size | PASS |
| truncated and full physical identities match | PASS |

### Accélération de base complexe — SHA-256 `89174f406f5f1c2e5d9f136612e6355402dd6a4475cdf443e582a5412483255d`

| Assertion exacte | État |
|---|---|
| 0 Hz absolute acceleration includes base acceleration | PASS |
| 0 Hz absolute acceleration is available | PASS |
| 0 Hz relative acceleration follows -omega squared U | PASS |
| 0 Hz relative displacement matches full free equation | PASS |
| 0 Hz relative velocity follows i omega U | PASS |
| 4.35864 Hz absolute acceleration includes base acceleration | PASS |
| 4.35864 Hz absolute acceleration is available | PASS |
| 4.35864 Hz absolute displacement includes ground motion | PASS |
| 4.35864 Hz absolute displacement is available | PASS |
| 4.35864 Hz absolute velocity follows i omega U | PASS |
| 4.35864 Hz absolute velocity is available | PASS |
| 4.35864 Hz relative acceleration follows -omega squared U | PASS |
| 4.35864 Hz relative displacement matches full free equation | PASS |
| 4.35864 Hz relative velocity follows i omega U | PASS |
| 8.54293 Hz absolute acceleration includes base acceleration | PASS |
| 8.54293 Hz absolute acceleration is available | PASS |
| 8.54293 Hz absolute displacement includes ground motion | PASS |
| 8.54293 Hz absolute displacement is available | PASS |
| 8.54293 Hz absolute velocity follows i omega U | PASS |
| 8.54293 Hz absolute velocity is available | PASS |
| 8.54293 Hz relative acceleration follows -omega squared U | PASS |
| 8.54293 Hz relative displacement matches full free equation | PASS |
| 8.54293 Hz relative velocity follows i omega U | PASS |
| 8.89162 Hz absolute acceleration includes base acceleration | PASS |
| 8.89162 Hz absolute acceleration is available | PASS |
| 8.89162 Hz absolute displacement includes ground motion | PASS |
| 8.89162 Hz absolute displacement is available | PASS |
| 8.89162 Hz absolute velocity follows i omega U | PASS |
| 8.89162 Hz absolute velocity is available | PASS |
| 8.89162 Hz relative acceleration follows -omega squared U | PASS |
| 8.89162 Hz relative displacement matches full free equation | PASS |
| 8.89162 Hz relative velocity follows i omega U | PASS |
| DC absolute displacement remains unavailable | PASS |
| DC absolute velocity remains unavailable | PASS |
| absolute acceleration responses are available | PASS |
| absolute displacement responses are available | PASS |
| absolute velocity responses are available | PASS |
| frequency records cover the full sweep | PASS |
| full modal basis is complete | PASS |
| relative acceleration responses are available | PASS |
| relative velocity responses are available | PASS |
| serialized absolute_acceleration_responses responses round-trip exactly | PASS |
| serialized absolute_responses responses round-trip exactly | PASS |
| serialized absolute_velocity_responses responses round-trip exactly | PASS |
| serialized execution key is preserved | PASS |
| serialized relative_acceleration_responses responses round-trip exactly | PASS |
| serialized relative_velocity_responses responses round-trip exactly | PASS |
| serialized responses responses round-trip exactly | PASS |

WP07 : les assertions exactes sont inspectables à `tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames` au commit `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66`. Les assertions concernent équation libre, repères, cinématique, disponibilité, masse avant réduction, maturité et trois round-trips ; preuve d’exécution : stdout et run.json ci-dessus. Les valeurs numériques ne sont pas exposées.
