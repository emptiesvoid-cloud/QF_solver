# WP12-B HEX20 — intégration et préparation Owner

**Statut : `HEX20_OWNER_EXECUTION_DECISION_PENDING_CANONICAL_CONTROLLER_INTEGRATION`**

Ce dossier clôt la revue technique autorisée. Il ne vaut ni autorisation de fusion ni autorisation FEM.

## État des PR

| PR | État | Identité | Résultat |
|---|---|---|---|
| [#48 — restauration prospective des assertions R4](https://github.com/emptiesvoid-cloud/QF_solver/pull/48) | MERGED | source `8f2b02b053af70cbaa23378adbd783dd99669b1b`; merge `b649d73a1c76c5ce8749b5cdc24f6106e0fc4081` | assertions et captures examinées; aucune exécution scientifique nouvelle |
| [#49 — inventaire des dépendances WP12](https://github.com/emptiesvoid-cloud/QF_solver/pull/49) | OPEN, DRAFT, mergeable | branche `codex/wp12b-hex20-source-inventory`; commit de code `1c5b71967f94600662d9e2032156b5fa526ed4a5` | PR distincte dépendant de #48; revue Owner/mainteneur et intégration encore requises |

GitHub ne rapporte actuellement aucun contrôle CI pour ces PR. Aucun échec CI n’est donc disponible à corriger.

## Revue de #48

La restauration reprend les contrôles du test R4 C1 `26fe6c60c4d6459857636ee97a2f7135355c191f`, sans changer leur grandeur, formule ou tolérance :

| Assertion historique | Critère conservé |
|---|---|
| Statuts | `result.status == PASS`, `mesh_status == PASS`, solveur convergé |
| Identité et déplacements | 20 nœuds, 1 HEX20, 60 déplacements finis; `allclose(u, u_affine, rtol=1e-10, atol=1e-13 m)` |
| Contrainte récupérée | Voigt `[σxx, σyy, σzz, 0, 0, 0]`; `rtol=1e-10`, `atol=1e-4 Pa` |
| Énergie interne | `abs(U − U_exact) <= 1e-10 U_exact`; `U_exact = 0.5 σxx εxx × 1 m³` |
| Travail externe | `abs(W − 2 U_exact) <= 1e-10 U_exact` |
| Équilibre | résidu libre `<=1e-10`; erreurs relatives forces et moments `<=1e-12`; identité énergie linéaire `<=1e-10` |

Le test écrit le sidecar avant ses assertions, y compris le contrôle de statut et les assertions R4. Le schéma `qfsolver-wp12b-hex20-affine-diagnostic-v2` capture le vecteur de contraintes récupérées et son écart, les énergies, réactions, résidus, qualité, convergence et temps, en plus de K/F et des comparaisons de charges. L’écriture atomique refuse l’écrasement; un test synthétique provoque un échec d’assertion puis vérifie la conservation du sidecar et de son SHA-256.

L’oracle de charge QUAD8 sélectionne les faces depuis les coordonnées, calcule aire et normales géométriquement, puis applique `t = σ·n` et les poids nodaux QUAD8. Il n’appelle ni la table de faces HEX20 ni le code de quadrature de production. Les différences nodales restent des observables sans seuil. `K` est explicitement identifié comme assemblage de production, pas comme oracle indépendant. Les seuils proposés pour `η∞` et les charges restent inactifs (`OWNER_APPROVAL_REQUIRED; NOT ASSERTED`).

Le diff de #48 ne modifie aucune archive R4, aucun ledger, aucune ancienne inscription, aucun seuil, solveur ou contrôleur. L’état historique demeure `HEX20=PYTEST_FAILED / ROOT_CAUSE_INCONCLUSIVE`; aucun PASS rétroactif n’est revendiqué.

## Correction de provenance proposée par #49

Le runner calcule désormais un inventaire transitif statique des imports Python locaux accessibles depuis le nodeid, les `conftest.py` ancêtres et les `__init__.py` de ses packages. Il suit également les `pytest_plugins` littéraux, les alias `importlib.import_module` et les `__import__` à noms/fromlist littéraux. Il refuse les imports dynamiques non résolubles et les imports wildcard locaux au lieu de produire une empreinte incomplète. Les arbres `src/solveur/**/*.py` et `experiments/**/*.py`, déjà inventoriés en entier, restent couverts par l’inventaire existant.

À l’inscription, les chemins et SHA-256 des dépendances additionnelles sont ajoutés à l’enregistrement append-only. L’inscription active les recalcule avant usage et refuse une dépendance absente, modifiée ou un ancien enregistrement sans cette liste lorsque le test en importe. Les anciens enregistrements restent lisibles; un changement de source exige une nouvelle révision d’inscription. Aucune modification de `development_autonomous_policy.json` ou du contrôleur partagé épinglé n’a été faite.

Nodeid prospectif inchangé :

`tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual` — **60 DDL**.

### Identités et empreintes

| Élément | Identité / SHA-256 |
|---|---|
| Branche scientifique | `emptiesvoids-cloud/wp12b-hex20-r4-assertions` |
| HEAD / tree scientifique | `8f2b02b053af70cbaa23378adbd783dd99669b1b` / `6cf64ee5008c73da6eb06f39d01d8b08a3fb1be1` |
| Empreinte scientifique recalculée avec l’inventaire proposé | `efe44ae1505eb130e15e8ce8c4ae5311b639353b674c94b393d75387655227fb` — 508 fichiers |
| Dépendances locales enregistrées dans ce calcul | `tests/conftest.py` `8bbc1d99632bf3ba9563769100e88eaf8a8c645fc240d4e56e2e339b276669a0`; `tests/unit/conftest.py` `71ed98e5a7c11c64529a1098518c6e16467dc6f84d45336d4103ebf74e6fc2f6`; `tests/unit/wp12b_hex20_diagnostic_support.py` `865d38430e5044d72916cc7d1be42bad4cdf2f8628e0a232748168161cd52925` |
| Fichiers scientifiques R4 restaurés | test `3219cd922d0bbec444876dc05161dde8e35d8e2566e7456054f703dc1179d932`; support `865d38430e5044d72916cc7d1be42bad4cdf2f8628e0a232748168161cd52925`; tests synthétiques `7c05e0899db890fdf5184445b6cf065c78fed5b3d175098ffe8a81091898940a` |
| Base canonique actuelle | HEAD `b649d73a1c76c5ce8749b5cdc24f6106e0fc4081`; tree `0d9d0b620a14ab0c02812242fbbd597683252c8c` |
| Commit de code candidat #49 (avant le commit de ce rapport) | HEAD `1c5b71967f94600662d9e2032156b5fa526ed4a5`; tree `6105a8a14d868c9c0eaac1ab149520cd97786a31` |
| Fingerprint contrôleur candidat à ce commit et dans ce worktree | `917b0628a4fe10a7093b134d25916536d88e541f7cdbd50bab1e2ebc279708e5` |
| Entrées contrôleur au commit candidat | runner `8d0a6338836771021e7ecc504e1f1924eacc2803cfe86637924a1a8ca81545b1`; plugin pytest `3011c1c311703c0a0c4df86518105ea636fc340236be79c11ab7a4d3e07cc707`; politique `f91b22d17022e4cce21b53066167eba1b90dfc426fc0087dc6fce312632bdecc` |

Le fingerprint contrôleur candidat lie aussi le chemin absolu, la branche, HEAD/tree et l’environnement Python (`3.13.1`), pytest (`8.4.1`) et psutil (`7.2.2`). C’est une valeur de contrôle du commit de code #49 dans son worktree local, **pas** une identité canonique utilisable par un manifeste. Le commit documentaire de ce rapport modifie HEAD; la valeur complète changera donc avec le nouveau tip de PR. Le fingerprint définitif doit être recalculé dans le worktree canonique après intégration.

## Vérifications

- `tests/unit/test_development_autonomous_policy.py`: **176 PASS**, tests synthétiques du contrôleur uniquement.
- `tests/unit/test_wp12b_hex20_diagnostic_support.py`: **5 PASS**, tests synthétiques; aucun appel au solveur.
- Ruff lint, compilation Python et `git diff --check`: **PASS** sur les fichiers de contrôleur modifiés.
- Ruff lint, format check et compilation Python des trois fichiers scientifiques de #48: **PASS**.
- Le `ruff format --check` complet des deux fichiers du contrôleur signale des écarts déjà présents sur la base canonique; le contrôle effectué sur les versions de base échoue aussi. Le diff formatter ne signale aucune ligne ajoutée par #49. Les réécritures sans rapport, notamment dans WP07, ont été exclues du patch.
- PR #49 ne rapporte aucun contrôle CI à cet instant.
- Aucun corps de test HEX20, FEM, assemblage, solveur, collect-only, réservation ou manifeste nouveau n’a été exécuté ou créé.

## Préflight, manifestes et préconditions restantes

L’intégration du contrôleur #49 n’a pas été autorisée et n’a pas eu lieu. La politique canonique pointe encore vers C3 au worktree `C:\Users\fari\.codex\worktrees\wp12b-hex20-reconciliation\qf_solver`, branche `emptiesvoids-cloud/wp12b-hex20-consolidation`; son enregistrement conserve la source HEAD `31ef7593eeefa339aa1a5768df0b9c5751d66206` et l’ancien fingerprint `0d4838a1db01ba0690fb6fcce61244f5031c4ab86fccc3ecacd9a47687209cef`. Il ne lie pas la source actuelle `8f2b02b…` ni son empreinte `efe44ae…`.

En conséquence, aucun nouveau reçu officiel collect-only ni manifeste PREPARED_NOT_AUTHORIZED n’existe pour cette identité. Le reçu C3 `pf-036904402cab` (`ad9d7836ec6839cc619377cdd67c2ffff45271666088a65a566f686286fe1a44`) et son ancien manifeste (`4090711004c87895c067c61d576098eef87e961ee0802c623dd6d0b3f6dc09db`) ont été relus et leurs hashes correspondent; ils restent inchangés, obsolètes pour la source restaurée et non réutilisés.

Après revue et intégration de #49 par les responsables autorisés :

1. Recalculer le fingerprint complet du contrôleur depuis le worktree canonique exact.
2. Faire une nouvelle inscription append-only du nodeid exact sur le worktree scientifique propre retenu, avec le fingerprint `efe44ae…`, 60 DDL et sa justification; conserver l’inscription C3 historique.
3. Exécuter le préflight officiel collect-only sur ce nodeid et vérifier un item collecté, sans skip ni corps de test.
4. Préparer un nouveau manifeste `PREPARED_NOT_AUTHORIZED`; ne pas réutiliser le manifeste R1.
5. Soumettre l’identité, le reçu, le hash du nouveau manifeste et les budgets à une décision Owner distincte avant toute réservation ou exécution.

Décision distincte encore ouverte : activer ou laisser purement observationnels les limites diagnostiques proposées (`η∞ <= 1e-10`, charges `rtol=1e-12`, `atol=1e-6 N`). Elles ne sont pas nécessaires pour préserver les assertions R4 et ne sont pas activées par #48 ou #49.

**Conclusion :** le code de restauration R4 est intégré; le correctif d’inventaire est prêt en PR #49. Le dossier ne peut pas encore lier une décision d’exécution à un manifeste valide. Statut final actuel : `HEX20_OWNER_EXECUTION_DECISION_PENDING_CANONICAL_CONTROLLER_INTEGRATION`. Aucune qualification scientifique n’est revendiquée.
