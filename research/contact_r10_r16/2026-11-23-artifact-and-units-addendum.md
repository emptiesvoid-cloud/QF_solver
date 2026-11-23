# Addendum R10/R16 — rapprochement des archives et unités

**Date :** 2026-11-23

**Base de travail :** `origin/0.3.0` à `30a14c102014f87071f74095654d03c162e524bf`

**Portée :** rejeu d’archives et tests synthétiques seulement. Aucun calcul FEM, aucun changement de seuil et aucune réécriture d’un verdict historique.

## Résultat de la recherche d’archives

Les magasins de runs, sauvegardes locales accessibles, worktrees et archives de session ont été recherchés par nom et par SHA-256. Les entrées attendues ci-dessous n’ont pas été retrouvées comme fichiers ayant l’empreinte annoncée :

| Artefact attendu | SHA-256 annoncé | Résultat |
|---|---|---|
| R1.10 M3 slip `raw.npz` | `303155ed2635300888824f7bfd2e45e737bfd374b0c49431a794e294207ec5ab` | absent |
| R1.10 M3 slip `result.json` | `e7d377f87b0e9b7d7f8377936cee390eae1b8fbd6c9a3825fe87e65a13fc2e86` | absent |
| R1.10 M3 slip telemetry | `66ebd74a6ca2e04cdb699ebe18d20366275dbd280f6470ef2c1ce4ead49daeec` | absent |
| R1.10 M4 slip initial `failure.json` | `acf5c531efc5ee40cd41686e31ca06a15e0d7df2f7be16b24a1704b082e5e2f0` | absent ; SHA référencé par le manifeste de processus |
| R1.10 M4 slip initial telemetry | `95db722c0be8b3acba0c53102f45490469ee85738667627fe3a92c91527c83aa` | absent ; SHA référencé par le manifeste de processus |
| R14 `result.json` | `ecaaf3480f0c29d209a1c68c063447bd335a7494901b7d1e23d3313e76cc56f9` | absent |
| R16 `result.json` | `43917c4e2f6e4ac4e72db26a327adbe32a98ef679d043425f787250bf0794752` | absent |
| R16 `run.json` | `6498c1da512c9e425e2adee7d5be9c03f32d69b07da43a0a19854960230dfee3` | absent |

Le manifeste du processus M4 initial est disponible et lie le code retour `1`, les SHA attendus des sorties et le stderr conservé. Le stderr initial lui-même est présent et son SHA-256 est `a2c8c663a4a346c51b67587ff80c8c0da9340eb1d6e3b68a120db559bd106818`. Le statut de l’exécution initiale reste `FAIL_CLOSED_PROCESS_OR_RESULT`.

Une capture **forensique R2 distincte** de M4 est, elle, complète et vérifiable. Son contrat est `190910ae3d9c8ca8afdd1e4742a97b57984fd54e9bac5a79db45bc4ddb533583`, sa source est `50b3d35809b49457a5c7cebac017d63daf17b06e`, et ses SHA sont `67637a5bd4b08a73c16f38aba9c847386f35f2c3bb4e5fb8bf1e75476021b190` pour `failure.json` et `f23b56151bd432aef3c55baa746a359ea39044af8a45ae92258ea765e2b5f031` pour la télémétrie. Ce rejeu confirme le diagnostic d’unités, mais ne remplace pas les octets manquants de la tentative initiale.

Le fichier de configuration R14 est disponible et vérifié : `examples/contact/frictional_bstar_small_rotation/model_r14_bstar_slip.json`, SHA-256 `b74c57cae86d94b4cbfdae0c298ea98aa660f70159c72eb4b72f0ee4b5eee3e5`. Le supplément d’analyse R14 est aussi disponible, SHA-256 `4549585f921bc665913db403a9e1cf2547e4c53f4b66e7989129ad3049092f6c`; il contient des métriques compactes, mais pas le résultat brut qui permettrait de refaire le rejeu complet.

## R1.10 M4 slip — unités et séquence du pas 7

La lecture historique comparait une norme de résidu physique à un seuil normalisé. Cette comparaison d’unités était incorrecte. Le seuil numérique et le verdict `FAIL_CLOSED` restent inchangés.

Dans `src/solveur/contact/slip_root.py`, le solveur construit d’abord le résidu tangentiel physique par contact, en newtons. Pour le contrôle d’acceptation, il calcule ensuite :

\[
\rho_i = \frac{\lVert r_i\rVert}{\max(\mu\max(p_i,0),\;1\;\mathrm{N})},
\qquad \rho_{\max}=\max_i \rho_i.
\]

Ainsi, `residual_norm` est en **N**, tandis que `scaled_residual_norm`, `maximum_scaled_contact_residual` et le seuil `1e-9` sont **sans dimension**. Le dénominateur est une force, `max(μp, 1 N)`. Le fichier `slip_root.py` a le même SHA-256 (`9f80875f368136b0d1f926a301f0f9a8bc17beda02f0c769756e08cefa884b42`) aux commits source R1.10 `5aeab8733164fb26bbb167f1000212388392bb5d` et R2 `50b3d35809b49457a5c7cebac017d63daf17b06e`.

Le stderr initial contient `residual=1.504e-07` après terminaison `xtol`. Il s’agit de la norme physique arrondie en N ; le `failure.json` initial n’étant pas retrouvé, son résidu normalisé exact et son dénominateur ne sont pas récupérables.

La capture forensique R2 fournit les valeurs exactes pour le contact le plus défavorable :

| Grandeur | Valeur | Unité |
|---|---:|---|
| Résidu physique du contact 65 | `5.495876940920163e-8` | N |
| Pression normale du contact 65 | `17.415553382026697` | N |
| Limite de frottement `μp`, avec `μ=0.3` | `5.224666014608009` | N |
| Échelle `max(μp, 1 N)` | `5.224666014608009` | N |
| Résidu normalisé maximal | `1.0519097154830292e-8` | sans dimension |
| Tolérance contractuelle | `1e-9` | sans dimension |

Le résidu normalisé maximal est environ `10.519` fois la tolérance ; le rejet est donc correct. La norme physique globale des 45 contacts glissants est `1.5037868322441332e-7 N`, distincte du maximum normalisé par contact.

Séquence reconstituée sur R2 : six pas acceptés, puis rejet et rollback du pas 7 ; l’ensemble actif direct atteint 25 itérations et visite 10 ensembles ; la recherche least-squares termine avec `success=true`, statut `xtol`, 3 évaluations, mais ne passe pas le contrôle physique ; le raffinement semismooth ne réduit pas le résidu ; le candidat seed de la projection couplée est rejeté et l’énumération exhaustive reste bloquée par le garde `81 > 8`. Le garde a fonctionné comme prévu. Les données ne départagent pas de façon concluante l’effet de `xtol`, le conditionnement, la précision du solveur linéaire ou l’interaction non lisse. Aucun défaut mécanique unique n’est démontré.

## R1.10 M3 — fraction de nœuds et fraction d’aire

Les agrégats versionnés donnent pour M3 slip `20/25` nœuds esclaves actifs, soit `80 %`, mais `87.5 %` de l’aire de contact pondérée active. Ce sont deux mesures différentes. Les cinq nœuds de la rangée `y=1 m` sont rapportés ouverts. Les sorties brutes M3 sont absentes ; ces valeurs sont vérifiées dans l’audit compact, pas recalculées depuis les forces/nœuds bruts. Aucun mécanisme unique d’ouverture n’est établi. M3 reste `PASS_DIAGNOSTIC_GATES`, sans qualification formelle ni seuil de convergence maillage gelé.

## R14/R16 — lecteur, états et portée des métriques

Le lecteur R16 historique appelait `.get()` sur des événements déjà sérialisés en chaînes JSON. La reproduction synthétique produit bien `AttributeError`; le lecteur corrigé décode les mappings et les chaînes JSON, puis refuse les JSON malformés ou qui ne sont pas des objets. La correction existait déjà dans le worktree C01 historique à `06fce7a47d41223955755c34e7238376b3c4a7b5`. Le commit de la tentative `860ad6f195f06b302a8a46e343934472bdd1ff67` et le commit R17 `0f70192413d99486e114e2cae040ad298ac09395` ne sont pas présents dans la base d’objets accessible ; l’intégration source `9035adff88b42e2ed8172260ead7c74485494d88` y est présente.

Le statut historique de R16 reste `PYTEST_FAILED` : l’échec du lecteur est intervenu après le retour du solveur. Le rapport R17 déjà versionné annonce un rejeu hors FEM `B_STAR_R16_ARCHIVE_REPLAY_PASS`, mais il n’a pas pu être reproduit ici car le résultat et `run.json` liés aux SHA ci-dessus sont absents. Le statut du solveur, le statut du test/runner et celui du rejeu hors ligne restent distincts.

R14 porte sur une paire nœud-triangle gelée, `finite_sliding=false`, sous petites rotations. Son statut solveur enregistré est `PASS`; le verdict initial du postprocesseur `B_STAR_SLIP_FAILED` est conservé. Le supplément R14 rapporte séparément `B_STAR_STICK_SLIP_VALIDATED_EXPLORATORY`, qui ne vaut pas qualification générale.

Des contrôles d’arithmétique ont été refaits sur les valeurs compactes du supplément R14 et la fixture SHA-vérifiée, sans prétendre refaire le rejeu brut : 9 pas acceptés et actifs, états stick 1–7 puis slip 8–9 ; au pas 9, la norme de la force tangentielle enregistrée et la capacité `μp` diffèrent de `1.82e-12 N` ; le vecteur des forces généralisées B* par nœud somme à zéro, et son moment calculé aux coordonnées de la fixture est nul. Les charges de la fixture, réactions d’appui et réactions de ressort du supplément reproduisent le moment extérieur combiné `[-1.3642420526593924e-12, 1.2079226507921703e-12, -4.547473508864641e-13] N·m`, de norme `1.8780385144291777e-12 N·m`, sous la limite historique `0.002 N·m`. L’écart de contact enregistré est `1.3877787807814457e-17 m`. Ces contrôles portent sur les champs dérivés du supplément ; ils ne remplacent pas le résultat R14 absent.

Les marges d’essai Coulomb des pas 8 et 9 (`15494.836561 N` et `15600.001459 N`) sont reconstruites depuis le déplacement accepté, la référence de glissement précédente, `k_t` et la pression acceptée. Elles ne sont pas émises par la télémétrie `CONTACT_STATE` et ne doivent pas être présentées comme des mesures directes. R16/R14 ne qualifient ni le glissement fini, ni une tangente globale cohérente en glissement, ni une route de contact générale ; aucun seuil numérique d’angle n’est imposé par le runtime.

## Correctif compact et vérifications

Un décodeur d’archives générique a été ajouté sous `scripts/contact_archive_telemetry.py` avec des tests unitaires sous `tests/unit/test_contact_archive_telemetry.py`. Il n’est pas appelé par le solveur et n’altère aucune archive. Ce petit port n’est pas encore câblé au script de rejeu R16, qui n’est pas présent sur `0.3.0` ; il ne prétend donc pas avoir rejoué ni corrigé ce script dans cette branche. Le code de production R10 n’a pas été changé : son normaliseur compare déjà le résidu sans dimension à la tolérance correspondante.

Sur la base `30a14c102014f87071f74095654d03c162e524bf`, Python `3.13.1` :

- 10 fonctions unitaires ciblées M4/scaling/`xtol`, forensic runner et audit M4 : `PASS` ;
- 6 fonctions unitaires du nouveau décodeur (cas paramétrés inclus) : `PASS` ;
- 13 fonctions unitaires R14/R16 exécutées sur le worktree historique C01 à `06fce7a47d41223955755c34e7238376b3c4a7b5` : `PASS` ;
- reproduction synthétique de l’ancien `.get()` : `AttributeError` ; décodage corrigé : mapping valide ;
- rejeu R14/R16 sur les résultats bruts : `NOT_RUN`, entrées hashées absentes ;
- campagne FEM, suite complète et CI protégée : `NOT_RUN`.

Les verdicts historiques, les seuils et les archives n’ont pas été modifiés. Prochaine action minimale : restaurer les fichiers bruts par les SHA du tableau depuis une sauvegarde vérifiée. À défaut, le rejeu R14/R16 nécessitera une nouvelle préparation contractuelle autorisée ; cette mission n’a lancé aucun calcul pour les remplacer.
