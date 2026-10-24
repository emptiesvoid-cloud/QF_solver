# WP-D01 — Capability recovery: residual flexibility WP05

Date : 2026-10-24. Workstream isolé : `codex/wp-d01-residual-flexibility-20261024`.

## Résultat

Verdict : `D01_RESIDUAL_FLEXIBILITY_PORT_READY`.

La véritable correction mode-acceleration est raccordée à `ReducedHarmonicResponseSolver` comme option strictement opt-in. Le chemin par défaut WP05 demeure inchangé. Aucune exécution FEM, collecte native ou qualification n’a eu lieu. La fusion dans `codex/v0.2.12-integration` est différée pour ne pas toucher aux modifications C01/E01 déjà présentes dans ce worktree.

## Provenance historique et formulation

Le noyau du correcteur a été retrouvé dans le développement D01 historique, notamment le commit `554075d355d74cc6afa4119b3b3ab372d5f47ffc`; le raccord à l’analyse harmonique est dans `8633575de961a738dad1408d50da7ccf52839418`. La caractérisation native et ses métriques proviennent du protocole BJ (`fec6016190c0275f2323ec12868260415dbf1c9a`), et l’instrumentation des opérandes de damping du travail CG/CH (`8a8587f8`). Le snapshot source historique utilisé pour contrôler les scénarios est `e6b63dfe7c1c3a00fd897c107a2322a3172ff96f`.

Pour la convention phasor `u(t)=Re[U exp(+iωt)]`, avec `Z=K+iωC−ω²M` et `u_m=Φq`, le correcteur calcule `r=f−Zu_m`, retire la composante de raideur dans la base retenue via `q_r=(ΦᵀKΦ)⁻¹Φᵀr`, puis résout `Kδ=r−KΦq_r` et retourne `u_m+δ`. Les contrôles de compatibilité opérateur/base, symétrie, SPD, orthogonalité massique, cohérence de projection et résidu de résolution restent fail-closed; aucune régularisation ni symétrisation de K/M/C n’est introduite.

Pour Rayleigh structuré, la matrice réduite est calculée comme `C_r=αM_r+βK_r` après contrôle de cohérence avec la projection directe. La flexibilité résiduelle n’accepte que le damping Rayleigh physique vérifié. Aucune route Rayleigh ne remplace l’amortissement non-Rayleigh.

## Modifications

- Port du noyau `residual_flexibility.py`, du contrat de configuration et du wrapper de résultats typé dans WP05.
- Activation du correcteur seulement lorsque `residual_flexibility.enabled=true`; la configuration absente conserve le chemin WP05 ordinaire.
- Le scénario expérimental M1/M2/M3 sélectionne explicitement `rayleigh_structured` et les comptes modaux `(2,4)`; les deux méthodes modales comparent une base identique à chaque compte.
- Port du collecteur de preuves opérandes damping : matrices CSR K/M/C, modes, projection et tableaux numériques exacts hachés.
- Le validateur d’archives exige maintenant une grille de six valeurs composée de 0 Hz en premier puis cinq valeurs positives strictement croissantes. Il continue de refuser les grilles incomplètes ou invalides; les tests historiques C4 et leurs résultats ne changent pas.
- Les nodeids natifs sont marqués `NATIVE_AUTH_REQUIRED` par le conftest; pytest ordinaire ne les exécute pas. Le mécanisme spécialisé reste limité à un nodeid exact enregistré.

## Vérifications

- Tests algébriques/ciblés : **87 PASS** (correcteur synthétique, projection Rayleigh, sérialisation d’opérandes, contrats de métriques et validation du payload/ledger).
- Appel pytest ordinaire du module natif : **3 SKIPPED**, donc aucun corps M1/M2/M3 lancé.
- `--collect-only` : exactement les nodeids M1, M2, M3 ci-dessous.
- Compilation Python (`compileall`) : PASS.
- `git diff --check` et `git diff --cached --check` : PASS.
- Ruff : non exécuté car la commande `ruff` est absente; aucune dépendance installée pendant la mission.

Nodeids collectés :

```text
tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M1]
tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M2]
tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M3]
```

## Revue et gel de développement

Revue indépendante : aucun P0/P1 de code; un P2 opérationnel persiste. Le registre actif D01 pointe encore vers l’ancien worktree/ancienne branche, et son ledger M3 historique ne doit pas être réinitialisé. Un nouveau scope inactif et un budget préparatoire, liés à la nouvelle identité, sont dans `wp_d01_capability_recovery_dev_scope_draft.json`. Ils ne constituent ni une autorisation RUN ni une activation de policy.

L’agent de revue confirme également l’absence d’archive/JUnit sous cette nouvelle identité et n’a pas exécuté le code scientifique. L’étude de réponse harmonique native demeure donc à faire sous un scope séparément activé.

## Identité, fusion et classifications

Commit de portage : `0c01316b54b80171b8b0a5a0c79c7769d1031577`.

La cible `codex/v0.2.12-integration` contient des changements C01/E01 non commités, notamment des modifications de `scripts/development_autonomous.py` et `tests/unit/test_development_autonomous_policy.py`, également touchés ici. Pour protéger ces changements, aucun merge n’a été réalisé. Le worktree source de la campagne est isolé et propre après le commit du rapport.

État conservé :

```text
WP_D01_STATUS=INCONCLUSIVE
C4=NOT_ACQUIRED
WP05_FEM_QUALIFICATION=NOT_EVALUATED
GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED
WP11=PAUSED_BY_OWNER
FEM_RUN=NOT_RUN
```

La preuve future requiert : enregistrer/autoriser le nouveau scope au HEAD final, conserver le ledger historique, collect-only exact, puis une décision Owner distincte. Aucune promotion scientifique ne découle de ce portage.
