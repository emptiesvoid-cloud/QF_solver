# WP12-B HEX20 — restauration prospective des assertions R4

**Statut :** `HEX20_PROSPECTIVE_ASSERTION_RESTORATION_REVIEW_READY`

**Base scientifique :** candidat C3, `37a4176deeeb42ec75e51c3d621cce170e9718e1`

**Branche de correction :** `emptiesvoids-cloud/wp12b-hex20-r4-assertions`
**Portée :** correction prospective du diagnostic HEX20; aucune nouvelle exécution FEM.

## 1. Assertions historiques C1

La source de référence est le test `tests/unit/test_wp12b_hex20_affine_patch.py` du commit C1 `26fe6c60c4d6459857636ee97a2f7135355c191f`, nodeid `test_wp12b_hex20_uniaxial_traction_patch`. Les assertions suivantes ont été comparées à C3. Les formules et tolérances sont reprises sans changement.

| Contrôle R4 | Formule et critère historiques | Restauration prospective |
|---|---|---|
| Statut et maillage | `result.status == "PASS"`; `result.audit.mesh_status == "PASS"` | Oui, assertions après écriture du sidecar |
| Identité de cas | 20 nœuds, 1 élément, 60 déplacements; déplacements finis | Oui; la sélection reste un HEX20 à 60 DDL |
| Déplacement affine | `assert_allclose(u, u_affine, rtol=1e-10, atol=1e-13 m)` | Oui, mêmes valeurs et mêmes unités |
| Contrainte récupérée | Voigt `[σxx, σyy, σzz, 0, 0, 0]`; `rtol=1e-10`, `atol=1e-4 Pa` | Oui; comparaison après capture du vecteur récupéré et de son écart |
| Énergie interne | `abs(U - U_exact) <= 1e-10 * U_exact`; `U_exact = 0.5 σxx εxx` pour le cube de volume `1 m³` | Oui; volume `1 m³` rendu explicite dans les paramètres |
| Travail externe | `abs(W - 2 U_exact) <= 1e-10 * U_exact` | Oui, formule et tolérance inchangées |
| Résidu libre | `free_relative_residual <= 1e-10` | Oui |
| Équilibre des forces | `force_balance_relative_error <= 1e-12` | Oui |
| Équilibre des moments | `moment_balance_relative_error <= 1e-12` | Oui |
| Identité énergie linéaire | `linear_energy_identity_relative_error <= 1e-10` | Oui |
| Convergence solveur | `result.solver["converged"] is True` | Oui |

Les bilans historiques portent sur les métriques d’équilibre produites par l’audit du solveur. C1 n’imposait pas de comparaison indépendante du vecteur complet des réactions. Le sidecar continue d’archiver les réactions brutes et l’audit d’équilibre.

## 2. Assertations restaurées et exclusions

Le nouveau helper `assert_historical_r4_acceptance` réapplique les assertions du tableau après `write_diagnostic_sidecar`. Le test conserve en plus les contrôles diagnostiques structurels C3 : un appel de solveur, une capture de K/F/DDL contraints, cinq intégrations de face, formes attendues et valeurs finies. Le calcul R4 de déplacement n’est pas dupliqué : il est appliqué par le helper avec les constantes historiques.

Les métriques numériques de qualité d’élément sont conservées dans `result.audit.diagnostic["element_quality"]`. L’assertion historique R4 était `mesh_status == "PASS"`; C1 ne définissait pas de seuil quantitatif de qualité à réappliquer. Aucun seuil nouveau n’est ajouté.

Les comparaisons nodales QUAD8, `F - somme(des faces de production)`, `r_affine_eta_inf` et `K_production @ u_affine` contre les forces de bord analytiques sont des observables diagnostiques, pas des assertions historiques. Les limites proposées `η∞ <= 1e-10` et `rtol=1e-12 / atol=1e-6 N` restent inactives en attente d’une décision Owner.

## 3. Observables et contrat du sidecar

Le sidecar passe au schéma `qfsolver-wp12b-hex20-affine-diagnostic-v2`. L’écriture atomique sans écrasement a lieu avant les assertions restaurées. Il contient :

- K en CSR, F assemblé, les DDL fixes/libres et les empreintes de matrice;
- `u_affine`, `K @ u_affine`, les résidus libres/contraints et l’erreur arrière avec formule et unité;
- les vecteurs nodaux de production et QUAD8 par face, leurs différences signées par DDL, leurs résultantes et moments analytiques;
- `F - somme(vecteurs de faces de production)`, sa définition et son unité N;
- les déplacements calculés, le maximum absolu, les réactions, les bilans, l’énergie interne, le travail externe et leurs unités;
- les contraintes Voigt récupérées, l’oracle attendu et la différence en Pa;
- le statut du maillage, les métriques de qualité, les métadonnées de convergence du solveur, le temps et les métadonnées d’identité/tentative.

Les différences QUAD8 sont définies comme **vecteur de charge nodale intégré par la production moins vecteur nodal géométrique QUAD8**, en N. `K` reste la matrice de production; sa comparaison à la force indépendante de bord n’est pas présentée comme un oracle indépendant de rigidité. Les deux erreurs arrière archivées ont des dénominateurs explicitement distingués : l’une compare `K u_affine` à `F` sur les équations libres; l’autre compare `K_production u_affine` au vecteur indépendant de bord.

Les limites historiques sont enregistrées sous `historical_r4_assertions`; les observations sans seuil sont sous `observed_without_acceptance_threshold`; les limites proposées sont identifiées `OWNER_APPROVAL_REQUIRED; NOT ASSERTED`.

## 4. Différence scientifique C3 → correction

La géométrie HEX20, sa numérotation, les 24 DDL imposés/36 libres, les cinq faces chargées, les tractions, le champ affine, l’oracle géométrique QUAD8 et le mécanisme de capture K/F ne changent pas. La correction rétablit les vérifications mécaniques de C1 qui manquaient à C3 et ajoute les valeurs nécessaires à leur audit dans le sidecar. Elle ne change ni formulation, ni chargement, ni tolérance, ni critère diagnostique proposé.

Le schéma du sidecar est incrémenté en v2 afin de distinguer clairement les nouvelles propriétés et le renommage de la comparaison de bord de rigidité de production.

## 5. Vérifications réalisées

- Tests synthétiques du support et du sidecar : **5 PASS**; ils emploient un faux résultat, sans solveur FEM. L’un force une assertion de contrainte à échouer après écriture, puis vérifie que le sidecar et son SHA-256 restent disponibles.
- Ruff lint sur les trois fichiers modifiés : **PASS**.
- Ruff format `--check` sur les trois fichiers : **PASS**.
- `py_compile` sur les trois fichiers : **PASS**.
- `git diff --check` : **PASS**.
- Aucun corps du nodeid HEX20, assemblage, résolution, réservation ou collect-only n’a été lancé.

## 6. Identité, préflight et manifeste

La correction est sur une branche dédiée issue du HEAD d’intégration `8450df7d1b2d6ff598747560978aaf610729028b`, qui contient C3; elle ne revient pas à C1. Le commit scientifique est `060dcba6637eac2022ecbb90304319adbce42588`, tree `834bddd6c3c318b5f749221db1ff7fda1ddee007`. Les SHA-256 des trois fichiers source/test modifiés sont :

| Fichier | SHA-256 |
|---|---|
| `tests/unit/test_wp12b_hex20_affine_diagnostic.py` | `3219cd922d0bbec444876dc05161dde8e35d8e2566e7456054f703dc1179d932` |
| `tests/unit/wp12b_hex20_diagnostic_support.py` | `865d38430e5044d72916cc7d1be42bad4cdf2f8628e0a232748168161cd52925` |
| `tests/unit/test_wp12b_hex20_diagnostic_support.py` | `7c05e0899db890fdf5184445b6cf065c78fed5b3d175098ffe8a81091898940a` |

En appliquant en lecture seule l’algorithme de fingerprint du contrôleur canonique au worktree corrigé, son inventaire actuel produit `8182476a4e8ae4229d5f071d1200f4debc9526f4bee1a02605e4334cb9f299de` sur 507 fichiers. Cette valeur **n’est pas proposée comme fingerprint complet** : l’inventaire ne lie pas `tests/unit/wp12b_hex20_diagnostic_support.py` (`support_module_bound=False`). Le fingerprint devra être recalculé après une correction et une revue du contrat d’inventaire.

L’inscription actuelle du contrôleur est pour C3 : le fingerprint enregistré est `0d4838a1db01ba0690fb6fcce61244f5031c4ab86fccc3ecacd9a47687209cef`. Elle désigne le worktree `C:\Users\fari\.codex\worktrees\wp12b-hex20-reconciliation\qf_solver` et la branche `emptiesvoids-cloud/wp12b-hex20-consolidation`, pas le worktree de correction `C:\Users\fari\.codex\worktrees\wp12b-hex20-r4-restore\qf_solver` et sa branche dédiée. En outre, le contrôleur canonique calcule l’inventaire à partir des sources `src/solveur`, `experiments`, du module pytest cible et des fichiers de configuration/conftest; il n’inclut pas le module de support importé `tests/unit/wp12b_hex20_diagnostic_support.py`. La provenance de ce helper est bien hachée dans le sidecar, mais pas liée par l’inventaire de l’inscription. Par conséquent, l’inscription existante ne suffit pas à lier l’identité source complète de cette correction.

La correction du contrôleur partagé est hors de cette branche et n’a pas été faite. Avant tout préflight officiel, le responsable du contrôleur devra :

1. faire évoluer son inventaire de sources pour lier le module de support importé (ou proposer un mécanisme équivalent qui lie tous les imports de test pertinents);
2. réviser le rattachement du worktree/branche dans le scope selon son contrat, puis ajouter une révision append-only de l’inscription pour le nouveau HEAD/fingerprint et les mêmes 60 DDL, sans remplacer le reçu ni l’inscription historique;
3. exécuter un nouveau collect-only officiel sur l’identité corrigée et vérifier un seul item, sans skip;
4. créer un nouveau manifeste distinct après acceptation de l’identité scientifique.

Le reçu `pf-036904402cab` à `E:\QFSolverAgents\evidence\wp12b-hex20-affine-diagnostic-consolidated\worktrees\wp12_hex20_affine_diagnostic\preflight\pf-036904402cab\preflight.json` a été relu sans modification; son SHA-256 vérifié est `ad9d7836ec6839cc619377cdd67c2ffff45271666088a65a566f686286fe1a44`. Le manifeste PREPARED_NOT_AUTHORIZED conservé à `E:\QFSolverAgents\evidence\wp12b-hex20-affine-diagnostic-consolidated\authorizations\wp12_hex20_affine_diagnostic\WP12B-HEX20-AFFINE-DIAGNOSTIC-R1-CTRL6422.json` a le SHA-256 vérifié `4090711004c87895c067c61d576098eef87e961ee0802c623dd6d0b3f6dc09db`. Ils restent des artefacts historiques inchangés, ni remplacés ni réutilisés pour cette identité.

## 7. Décisions Owner encore requises

- Revoir et accepter le code scientifique corrigé et sa nouvelle identité Git.
- Décider séparément si les limites proposées de `η∞` et de différences de charges deviennent des seuils d’acceptation.
- Faire corriger puis réviser la provenance/inventaire du contrôleur, et autoriser le nouveau préflight et le manifeste correspondant.
- Toute exécution FEM nécessite ensuite l’autorisation applicable au manifeste exact; ce rapport ne vaut pas autorisation ni résultat scientifique.

**Aucune conclusion `SCIENTIFIC_PASS` n’est émise.** Le résultat R4 historique `HEX20=PYTEST_FAILED / ROOT_CAUSE_INCONCLUSIVE` est conservé sans modification.
