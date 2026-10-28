# WP12-A — Récupération du pipeline après campagne

**Statut :** `WP12A_POST_CAMPAIGN_RECOVERED_OWNER_DECISIONS_READY`

Cette récupération corrige le chemin d’écriture des sidecars et renouvelle les
preuves de préparation des trois cas restants. Aucun corps de test scientifique,
assemblage, résolution, réservation ou nouvelle tentative n’a été exécuté.

## État historique préservé

- WP07 reste `WP12A_WP07_SCIENTIFIC_PASS`; aucune relance n’a eu lieu.
- L’essai Newmark `dev-301ba3b31a43` reste `PYTEST_FAILED`. Le writer avait
  refusé le manifeste dans `owner-authorized/` avant les assertions. Aucune
  série numérique du test n’a été archivée; son verdict mécanique reste non
  établi. L’essai consommé n’a pas été répété.
- Les anciens préflights harmonique réduit et accélération de base, liés à
  l’ancien état du ledger, restent conservés comme reçus périmés. Ils n’ont pas
  été réutilisés.
- Le ledger générique demeure au SHA-256
  `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`.
  Le ledger Dynamics v2 demeure au SHA-256
  `3000ea966c1803a845c2a3b9694a663eebe65d8a62b61f07d4876232ac2b19a2`.
  Son lien vers le ledger générique est intact. Le total reste **7/130**; aucun
  des trois préflights ni la préparation des manifestes n’a touché le ledger.

## Corrections intégrées

Le défaut Newmark venait du contrat de chemin des trois writers de sidecar : ils
acceptaient le répertoire d’autorisation WP12 Dynamics mais pas son enfant
direct `owner-authorized/`, utilisé par les manifestes enregistrés par décision
Owner. La correction, intégrée par la PR #57 (`5d3d239aae90506efa2db40ff9af115e794f7bea`),
fait valider au writer la politique capturée, son empreinte, la racine de
preuves et le répertoire d’autorisation exact. Elle permet le répertoire
Dynamics prévu et son enfant direct `owner-authorized/`; elle refuse les
répertoires imbriqués, les liens symboliques et les chemins hors racine. Les
contrôles d’identité du manifeste, d’état Owner, de nodeid et d’écriture
atomique sont maintenus.

La validation stricte du ledger n’a pas été assouplie. Un préflight reste lié au
SHA-256 exact du ledger observé. Après une réservation, les anciens préflights
et manifestes des cas suivants sont refusés; ils doivent être renouvelés selon
la [procédure juste-à-temps](WP12A_DYNAMIC_JUST_IN_TIME_PREPARATION.md).

La désignation canonique a été épinglée de façon univoque par la PR #58,
fusionnée au commit `7827a0a8c57f6be42da496627de26f8a1a7fca85`. La branche
release était au HEAD `7827a0a8c57f6be42da496627de26f8a1a7fca85`, tree
`05c6074ffc5453aa5ca8e6f34ed170c788a9735e`. La désignation officielle pointe
vers le checkout contrôleur propre et détaché :

`C:\Users\fari\.codex\worktrees\wp12-shared-controller-dynreg-20261028\qf_solver\scripts\development_autonomous.py`

Ce checkout reste épinglé à HEAD `b206e6f520e9b03c3c925c3bef20883f01aa9800`,
tree `6f16b0d1d5fe204707e6b784355d34c943f18db5`, fingerprint officiel
`e48d4e61f04df2819431465130b12c3d36f24f6f92fbdf8221f44190442e1e08`. Ses
empreintes de fichiers sont : runner
`de4405a4df9622ff6295092c7383f71ee2a91eb19877ea7a6123fa728d7062a1`, plugin
`3011c1c311703c0a0c4df86518105ea636fc340236be79c11ab7a4d3e07cc707`, politique
`323aa88e0050ae960252ac3eaa2624505de120022d24a31ec3eb5f2626230250`.

Le worktree scientifique est propre sur la branche
`codex/wp12-dynamic-harmonic-verification`, HEAD
`5f96dd604fe40279ead0186f49be77e7a0bbeac1`, tree
`bf0b50b95355281f480e7fbab4139bd1cefc1900`. Son commit ne modifie que
l’instrumentation des writers de sidecar; le solveur, les équations, les
oracles et les critères restent inchangés.

Les trois inscriptions source append-only pointent vers ce HEAD :

| Cas | Nodeid | Empreinte source | DDL libres | Timeout |
|---|---|---|---:|---:|
| Newmark | `tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | `d4743785db99a79181281429827d0de688e5eae94e9ad285491040aaa75c7a8e` | 1 | 300 s |
| Harmonique réduit | `tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation` | `3a8c1324d0563214911e8f9abca87c09ddf98907d5d8ab01c822640c82baa4fe` | 3 | 300 s |
| Accélération de base | `tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` | `f16bbeea012b8c86924215156b1ffbac23d2248d0b0194067bcd9af36a3c3909` | 1 | 300 s |

L’allowlist active reste à 13 nodeids; l’historique des inscriptions a été
étendu de manière append-only. Le mandat demeure
`DEVELOPMENT_AUTONOMOUS-WP12-DYNAMICS-2026-10-26-v1`, avec 10 tentatives
maximum par nodeid et 130 au total.

## Validation technique

- Suite synthétique locale complète : **254 réussis, 0 échoué, 0 ignoré,
  0 erreur**.
- CI de la PR #58 : `WP12 controller / synthetic contracts` **PASS**,
  également **254 réussis, 0 échoué, 0 ignoré, 0 erreur**.
- Ruff, compilation Python, validation JSON de la politique et
  `git diff --check` : PASS.
- Tests synthétiques spécifiques : les trois writers acceptent le chemin
  `owner-authorized/` prévu, refusent un sous-répertoire imbriqué, préservent
  les sidecars lors d’un échec contrôlé et refusent l’écrasement. Le test de
  campagne démontre qu’une mutation temporaire de ledger rend le préflight
  ancien invalide et qu’un nouveau reçu/manifeste se lie au nouvel état.
- La première exécution ciblée de tests d’archives a révélé un dépassement de
  longueur de chemin Windows dans des noms de fixtures synthétiques. Les noms
  ont été raccourcis; le rerun a réussi (24 réussis).

Ces contrôles n’exécutent aucun corps scientifique. Les préflights ci-dessous
sont des collect-only officiels, pas des résultats FEM.

## Préflights et manifestes renouvelés

Tous les artefacts suivants ont été préparés par le contrôleur désigné, avec le
worktree scientifique ci-dessus et le même snapshot de ledger v2. Chaque reçu
rapporte un seul nodeid exact, `skip_markers=[]`,
`bodies_executed=false`, `attempt_reserved=false` et `ledger_touched=false`.
Les empreintes de ledger avant/après sont identiques.

| Cas | Préflight et SHA-256 du reçu | Manifeste et SHA-256 | État et budget |
|---|---|---|---|
| Newmark | `pf-3e441fac9f29` — `ee79506bef82e27a6e56bc25b2fb035f363e3a74377d2dd018f6c1b7312e3770` | `wp12a-newmark-b206-20261028-r3` — `665245fc37958161ebe54c473097082f845190f7855dd3e8cc62bf96ef698bed` | `PREPARED_NOT_AUTHORIZED`; 1 DDL; 300 s |
| Harmonique réduit | `pf-2fcc74d2b9f8` — `727a150b4de6a05813f6e43cfdcef8576bc2b35711d52a8352b41d2c9534334f` | `wp12a-harmonic-reduced-b206-20261028-r2` — `9582fca0ede9dac00edd6a4db40c16c639d38ac3da87abdde16edf4d1d100f7c` | `PREPARED_NOT_AUTHORIZED`; 3 DDL; 300 s |
| Accélération de base | `pf-9fc2c85db93f` — `ce1f7c087ace8c1b919d5354d435a99e1f0079c4ff30689ccc21814b29ba2945` | `wp12a-base-motion-b206-20261028-r2` — `c863f217e0a701f584a4d913ba5f352deb23b465c692cba5d5cf8b9009f1388b` | `PREPARED_NOT_AUTHORIZED`; 1 DDL; 300 s |

Chaque manifeste référence son reçu et SHA-256, la source exacte, le controller
fingerprint et le mandat. Son `owner_decision.status` reste `NOT_AUTHORIZED`.
Le manifeste n’est pas une permission d’exécuter.

### Dépendance au ledger et ordre sûr

Les trois reçus et manifestes sont liés au ledger v2
`3000ea966c1803a845c2a3b9694a663eebe65d8a62b61f07d4876232ac2b19a2` et à son
prédécesseur immuable `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`.
Les dossiers sont distincts, mais **ne constituent pas une autorisation
séquentielle garantie** : la réservation de Newmark invalidera les préflights
et manifestes harmonique/base préparés sur ce snapshot. Il faut conserver ces
artefacts sans les écraser, puis refaire officiellement le collect-only,
préparer un nouveau manifeste et demander une nouvelle décision Owner pour le
cas suivant. Aucune décision attachée à un manifeste périmé ne se transfère.

Le compte vérifié avant toute nouvelle réservation est : Newmark **4/10**
(3 tentatives du ledger historique + 1 tentative Dynamics v2 consommée),
harmonique réduit **1/10**, accélération de base **1/10**, total **7/130**.
Les plafonds ne sont pas modifiés.

## Critères et observabilité à examiner après autorisation

- **Newmark :** comparaison à la solution analytique SDOF conditionnelle aux
  opérateurs scalaires préparés; `dt = 0.002, 0.001, 0.0005 s`, temps final
  `0.08 s`, `beta=0.25`, `gamma=0.5`. Critères existants : ordre minimal de
  convergence de déplacement `>= 1.8`, résidu d’équilibre réduit relatif
  `<= 1e-7`, dérive énergétique relative `<= 1e-10`. Les erreurs vitesse et
  accélération sont observées, sans seuil d’acceptation déclaré. Le résidu est
  modal/réduit, pas global FEM.
- **Harmonique réduit :** balayage autour des fréquences propres, comparant
  solution directe, base modale complète et base tronquée à deux modes. Les
  observables séparent erreur de voie/base complète et différence combinée de
  troncature; les réponses complexes, amplitudes, phases, conditionnement et
  erreurs arrière sont archivés. Critères déclarés dans le test : erreurs
  arrière réduite et physique libre `<= 1e-8`; erreur relative vectorielle
  base complète/directe `<= 1e-8`.
- **Accélération de base :** balayage complexe avec excitation `0.7 - 0.4j`
  et comparaison de l’équation libre, des vitesses/accélérations, des repères
  relatifs/absolus, du signe et de la sérialisation. Le sidecar actuel n’archive
  pas les valeurs de référence complexes ni les écarts réponse-vers-référence;
  cette limite reste `NOT_EXPOSED` et ne doit pas être comblée par inférence.

## Décisions Owner requises et statut

Une nouvelle décision explicite est requise pour chacun des trois nouveaux
manifestes; les anciens SHA et décisions ne s’appliquent pas. Le dossier
Newmark ci-dessus est le premier candidat à examiner. Si Newmark est autorisé
et réservé, ne pas exécuter harmonique ou base avec leurs manifestes actuels :
renouveler d’abord leurs préflights et manifestes après l’archivage de Newmark,
puis solliciter leurs décisions distinctes. Cela préserve le séquencement
Newmark → harmonique réduit → accélération de base et évite une autorisation
devenue incompatible.

La correction permet maintenant l’archivage du sidecar; elle n’établit pas le
verdict mécanique de l’essai Newmark consommé. Aucun PASS de développement ne
constitue une qualification formelle et aucune maturité WP12-A n’est promue.
