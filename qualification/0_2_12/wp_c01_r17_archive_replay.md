# WP-C01-R17 — Rejeu des archives R16 hors FEM

**Verdict du rejeu :** `B_STAR_R16_ARCHIVE_REPLAY_PASS`.

**Verdict de la tentative FEM historique :** `B_STAR_INTEGRATED_FEM_SMOKE_FAIL`, conservé sans modification. Le test avait échoué après la fin du solveur parce qu'il appelait `.get()` sur les événements sérialisés en chaînes JSON. R17 qualifie uniquement le rejeu hors FEM des archives existantes; il ne réécrit pas le résultat de la tentative.

## Provenance

- Branche de la tentative : `codex/wp-c01-r16-integrated-smoke`.
- HEAD de la tentative : `860ad6f195f06b302a8a46e343934472bdd1ff67`, tree `1a4caa9335c9c3bb11f9a5652236ce3d7db6fcda`.
- Nodeid consommé : `tests/verification/test_wp_c01_r16_integrated_bstar_smoke.py::test_r14_slip_configuration_on_integrated_solver`.
- Fixture gelée : SHA-256 `b74c57cae86d94b4cbfdae0c298ea98aa660f70159c72eb4b72f0ee4b5eee3e5`.
- Résultat brut R16 SHA-256 `43917c4e2f6e4ac4e72db26a327adbe32a98ef679d043425f787250bf0794752`.
- `run.json` SHA-256 `6498c1da512c9e425e2adee7d5be9c03f32d69b07da43a0a19854960230dfee3`.
- Ledger de la tentative SHA-256 `84ee055eeacbc0905885226083aea398b75221e56957d573ca44a6e12b889caa`; entrée 1 conservée à `PYTEST_FAILED`.
- Résultat R14 de comparaison SHA-256 `ecaaf3480f0c29d209a1c68c063447bd335a7494901b7d1e23d3313e76cc56f9`.
- Postprocesseur hors FEM `scripts/replay_wp_c01_r16_archive.py`; sa révision fail-closed vérifie les empreintes exactes R14/R16 et refuse un moment brut non fini ou supérieur à `0.002 N.m`.
- Rejeu reproductible du postprocesseur [wp_c01_r17_replay_cli.json](wp_c01_r17_replay_cli.json), SHA-256 `59144a0a4fa5a0b077a043c7328eefcbe78da9bbd0af5339455b0b16ed202478`.

Les archives R14/R16, le journal pytest original et le ledger ont été lus sans écriture. Aucun solveur FEM n'a été lancé. Le rejeu versionné est [wp_c01_r17_archive_replay.json](wp_c01_r17_archive_replay.json), SHA-256 `ecdd2a5a3bed3f2aeac1f2f593e7e7bdf937d84cfeecdaad5127a5189952ac17`.

## Résultats du rejeu

Les 106 événements JSON ont été décodés : 9 paliers acceptés sur 9, stick aux pas 1–7 et slip aux pas 8–9. Le contact reste actif et sa pression positive sur les neuf paliers. Le gap absolu maximal vaut `1.3877787807814457e-17 m`. L'excès Coulomb maximal en stick est `0 N`; l'écart absolu maximal à `mu*p` en slip est `5.4569682106375694e-12 N`.

Les tolérances existantes sont conservées : marge stick `1e-6 N`; saturation slip `rel=1e-8`, `abs=1e-6 N`. Les coordonnées, déplacements, objet de contact et états acceptés R16 correspondent exactement aux données comparables R14. Aucune tolérance n'a été élargie.

## Bilan indépendant de moments R16

Les réactions d'appui existent dans `audit.equilibrium.reactions` (12 DDL fixes). Le calcul indépendant utilise ces réactions R16, la fixture gelée, les déplacements R16, les charges, les ressorts `-k*u` et les forces de contact nodales calculées par `B*ᵀF_t` et la contribution normale. Il n'emploie pas le champ solver `raw_moment_imbalance_about_origin` pour établir le bilan.

Au point de référence commun `[0,0,0] m`, le moment extérieur + réactions d'appui + ressorts est `[-1.3642420526593924e-12, 1.2079226507921703e-12, -4.547473508864641e-13] N.m`. Les forces de contact généralisées B* ont une résultante et un moment nuls. La norme du moment combiné est `1.8780385144291777e-12 N.m`, sous la limite inchangée de `0.002 N.m`. Le champ solver archivé est utilisé uniquement comme recoupement : `[-1.8189894e-12, 1.8189894e-12, 0] N.m`; la correction post-traitée est nulle.

`R16_RAW_MOMENT=ACQUIRED`. Un nouvel essai R18 pour acquérir ce bilan n'est pas requis.

## Contrat et limites conservés

`small_rotation_work_conjugate` reste expérimental et opt-in; `legacy` reste le défaut inchangé. Le mode reste limité aux petites rotations et à une paire initiale gelée. Aucun seuil numérique d'angle n'est imposé par le runtime. La tangente globale cohérente en slip et le glissement fini ne sont pas qualifiés. La convergence spatiale générale n'est pas acquise. Cette preuve ne constitue ni une qualification générale ni un certificat scientifique.

Le nouveau lecteur `tests/verification/wp_c01_r16_smoke_contract.py` accepte les événements objet et chaînes JSON, et rejette les chaînes mal formées ou les formes JSON non objet. Il exige un contact actif sur chacun des neuf checkpoints. `scripts/replay_wp_c01_r16_archive.py` épingle les SHA-256 des archives R14/R16 et de la fixture, reconstruit le bilan ci-dessus, refuse le résultat avant de publier PASS si le moment brut dépasse la limite inchangée, et refuse d'écraser le rapport de sortie. Les tests unitaires non FEM couvrent ces contrats ainsi que les formats du lecteur; aucun test ni le script n'appelle le solveur.

La version fail-closed a été rejouée sur les archives originales, sans modification : le rapport CLI conserve le SHA-256 `59144a0a4fa5a0b077a043c7328eefcbe78da9bbd0af5339455b0b16ed202478`. La révision du postprocesseur, après ces contrôles, a le SHA-256 `d8983f6342081fb6c9c0a08363075eb990d9b9c5f1ffbb188461176e991f291c`. Les 18 tests unitaires, Ruff, `py_compile` et `git diff --check` passent.
