# WP-D01-GIT-RECONCILIATION — rapport

Date : 2026-10-24

## Verdict

`D01_RECONCILED_READY_NOT_MERGED`

Le portage D01 est conservé dans un candidat propre, linéaire depuis le HEAD officiel. Le merge de la branche officielle n’a pas été effectué : Git refuse le fast-forward dans un worktree sale parce que deux fichiers locaux suivis seraient écrasés. Aucune option forcée, aucun nettoyage, reset, stash ou déplacement de référence n’a été utilisé.

## Références et branches

- Officielle `codex/v0.2.12-integration` : HEAD `b86ba5c1b0a66b67eee850ae394710840491204f`, tree `121593fb947b03626d3822f94cd4459b9d336284`.
- Candidat initial D01 : `9fa2a260bac6fcc31f92ddd8b60cc6c9bd64f331`, tree `d6c93865ea3870c7caa7a2043aa2173d2a94132d`.
- Candidat avec rapport de statut précédent : `dbf6bb8753c3d828fed1662d0fd2f9ea6272c8e8`, tree `6bd9e9b04bc571e508a53af5effe956679754559`.
- Base officielle vérifiée ancêtre du candidat. Aucun commit de merge dans cette chaîne.
- Worktree candidat : `C:\Users\fari\.codex\worktrees\wp-d01-safe-merge-20261024`, branche `codex/wp-d01-safe-merge-20261024`, propre avant ce rapport.
- Worktree officiel : `C:\Users\fari\Documents\projet\SAFRAN\solveur\tmp\qf-v0.2.12-integration`.

Le rapport `wp_d01_safe_merge_report.md` est le compte rendu de la première tentative et reste inchangé. Le présent document le complète et décrit l’inventaire, la sauvegarde vérifiée et la répétition du fast-forward.

## Inventaire et sauvegarde des changements locaux

L’inventaire Git a couvert 111 worktrees : 23 étaient sales au moment du contrôle. Aucun n’a été nettoyé ou modifié par cette mission, hors création explicite du worktree temporaire de répétition décrit ci-dessous. Dans la cible officielle, l’index était propre et le worktree portait cinq modifications suivies et deux fichiers non suivis :

```text
M  AGENTS.md
M  development_autonomous_policy.json
M  scripts/development_autonomous.py
M  tests/unit/test_corotational_j2_corrected.py
M  tests/unit/test_development_autonomous_policy.py
?? qualification/0_2_12/wp_e01_j2_global_tangent_feasibility_2026-10-24.md
?? tests/unit/test_wp_e01_j2_global_phase2.py
```

Les copies exactes sont conservées sous `C:\Users\fari\.codex\backups\wp-d01-git-reconciliation-20261024`, avec les chemins relatifs préservés. SHA-256 de chaque contenu, identique entre cible et sauvegarde :

| Fichier | SHA-256 |
|---|---|
| `AGENTS.md` | `DE8E40E425F3531A3EEEBA09F783911BC45A04E2EA9EC8C35476AC82DBD1F931` |
| `development_autonomous_policy.json` | `526FF918A60717C24C24B0BFDAE42FF4E1270FCDC740F4FFD0CD6E898FC62875` |
| `qualification/0_2_12/wp_e01_j2_global_tangent_feasibility_2026-10-24.md` | `A3C25E6990EEC1E4331C492B35CFFFF58DC0F5C5B6EFD107295610286B883A27` |
| `scripts/development_autonomous.py` | `3509F4FCAE45C74A367B13B4C0706EDD7A993E2C5DF98497511F186A00989ACB` |
| `tests/unit/test_corotational_j2_corrected.py` | `88CFB760757DE0A767E8FC98022ABAC1D1ED255F512C2CA1E49299B076397D5A` |
| `tests/unit/test_development_autonomous_policy.py` | `170D3130576F245B8ED7FB28E23E3F9DDB6E71A1299F2D09BE440FA707AC58B0` |
| `tests/unit/test_wp_e01_j2_global_phase2.py` | `D6AD36BEDB8541638AD4DE8BDE572091F473AB78C45162D286E1A74A26283A2D` |

Ces fichiers locaux — y compris les changements d’autonomie D01/C01/E01 présents dans les deux modules partagés — ne figurent pas dans le commit candidat. Les éléments E01 non suivis, `AGENTS.md`, la politique locale et le test corotational ne sont pas incorporés au diff D01.

## Portage et chevauchements

Les cinq commits du portage D01 transportés depuis la base sont :

```text
5fef29ae feat(wp-d01): add sparse residual flexibility core
5fbad035 feat(wp-d01): integrate opt-in harmonic correction
0c01316b feat(d01): restore opt-in residual flexibility harmonic path
e038cdc1 docs(d01): record residual flexibility port readiness
9fa2a260 docs(d01): mark exploratory scope non-consumable
```

Les commits documentaires de suivi déjà présents au snapshot `80fa80d9` sont :

```text
dbf6bb87 docs(d01): record safe merge status
1a8d6fd3 docs(d01): record git reconciliation evidence
80fa80d9 docs(d01): clarify reconciled candidate scope
```

La chaîne au snapshot `80fa80d9` comprend donc huit commits depuis la base. Le diff y compte 23 chemins (portage, rapports et pièces documentaires D01). Le présent commit actualise uniquement ce rapport; il n’ajoute aucun chemin ni modification scientifique.

Le candidat ne remplace pas la projection `rayleigh_structured` de la base. Le comportement harmonique historique reste le défaut; la correction est opt-in et le correcteur refuse le damping non-Rayleigh.

Les deux chemins communs ont été examinés par blocs :

- `scripts/development_autonomous.py` : D01 ajoute uniquement l’acceptation contrôlée de la grille expérimentale gelée (0 Hz puis cinq fréquences positives strictement croissantes), sans modifier les nouvelles règles locales de registre/ledger, de bootstrap ou les ajouts E01/C01.
- `tests/unit/test_development_autonomous_policy.py` : D01 modifie seulement le payload d’essai D01 correspondant à cette grille et ajoute ses cas de refus; les tests locaux E01/C01/D01 du registre restent hors candidat.

Les plages des hunks locaux et D01 dans ces deux fichiers ne se chevauchent pas. Cependant, l’opération de fast-forward Git refuse un fichier suivi modifié localement dès lors que le commit entrant le met aussi à jour, même si les hunks sont distincts.

La répétition dans le worktree isolé `C:\Users\fari\.codex\worktrees\wp-d01-safe-ff-rehearsal-20261024` a copié les sept fichiers depuis la sauvegarde puis exécuté `git merge --ff-only dbf6bb8753c3d828fed1662d0fd2f9ea6272c8e8`. Git a refusé avec le message « Your local changes to the following files would be overwritten by merge » pour les deux fichiers partagés et a abandonné. HEAD du rehearsal est resté `b86ba5c1...`; les sept SHA-256 y concordent encore avec la sauvegarde. La même opération n’a pas été tentée sur le worktree officiel.

## Vérifications sur le candidat

Les nodeids natifs collectés sont exactement :

```text
tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M1]
tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M2]
tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M3]
```

- Tests algébriques/contrats D01 sans assemblage de modèle : **69 PASS**.
- Pytest ordinaire du module natif : **3 SKIPPED**; aucun corps M1/M2/M3 exécuté.
- Collect-only : trois nodeids exacts.
- AST et compilation en mémoire : 17 fichiers Python, PASS.
- Imports ciblés des modules modal/harmonique/correcteur : PASS avec `src` ajouté au chemin d’import.
- `git diff --check` : PASS.
- Ruff : indisponible.
- Aucun calcul FEM, assemblage K/M, modalisation de modèle ou solveur natif exécuté pendant cette mission.

Un rapport antérieur consigne une exécution accidentelle, lors de la mission précédente, du module complet `test_reduced_harmonic.py` qui contenait des petites fixtures FEM. Aucun scénario M1/M2/M3 n’avait été lancé; cet incident n’est pas utilisé comme preuve de qualification et n’a pas été répété ici.

## Revue indépendante

La revue indépendante de cette réconciliation confirme : candidat propre et linéaire depuis la base; sauvegarde 7/7 exacte; index cible initial propre; seuls deux chemins se chevauchent; les autres modifications locales sont absentes du candidat. Elle recommande de ne pas merger avant réconciliation/preservation des fichiers locaux partagés. P0 : aucun. Finding opérationnel bloquant : worktree cible sale et fast-forward refusé; la revue qualifie ce blocage P1. Le refus exact est également observé dans la répétition locale ci-dessus.

## État final et suite minimale

Le commit D01 n’est **pas** atteignable depuis `codex/v0.2.12-integration`, qui reste à `b86ba5c1...` avec ses sept changements locaux intacts. Le candidat D01 est propre et prêt dans sa branche isolée. Pour intégrer ensuite : faire préserver/traiter les changements locaux par leurs responsables, obtenir un worktree cible propre sans les inclure à la branche D01, puis refaire la revue et effectuer le fast-forward normal. Ne pas forcer le déplacement de la branche.

Statuts conservés : `WP_D01_STATUS=INCONCLUSIVE`, `C4=NOT_ACQUIRED`, `WP05_FEM_QUALIFICATION=NOT_EVALUATED`, `WP11=PAUSED_BY_OWNER`.
