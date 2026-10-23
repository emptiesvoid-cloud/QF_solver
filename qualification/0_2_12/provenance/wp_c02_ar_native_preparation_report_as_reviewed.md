# WP-C02-AR — préparation de campagne FEM native M4/M5

## Conclusion préparatoire

**État scientifique : `NOT_ACQUIRED`.** Aucun scénario FEM M4 ou M5 n'a été exécuté. Le verdict de convergence M1–M5 reste donc `NOT_ACQUIRED` jusqu'à la décision explicite de l'Owner et à l'obtention de mesures nouvelles.

Le test dédié, le runner one-shot, le rapporteur, le manifeste d'exécution et le préflight non-FEM sont préparés. Le préflight a validé les modèles M4/M5; il n'a effectué aucun assemblage de rigidité ni appel au solveur. L'exécution est bloquée jusqu'au GO Owner sur l'identité ci-dessous.

## Gel d'exécution

| Identité | Valeur |
|---|---|
| Worktree / branche | `C:\Users\fari\Documents\projet\SAFRAN\.codex-worktrees\wp-c02-ar` / `codex/wp-c02-ar-spatial-convergence-20261023` |
| HEAD de base | `cd02eef59d3345643d617035be96190811d370bb` |
| Arbre Git de base | `4d24fbebcc4c08f63d17f41c693394a01d040bd5` |
| Empreinte du jeu source (525 fichiers) | `c0a29b1244d9d4d308769528a8a03e3b703ab123fce595ece069cc15199bd3c5` |
| Manifeste d'exécution SHA-256 | `dd17e77d6b9776508e26642a33636df2920a612542caff93cae2134cf02bc105` |
| Plan AR SHA-256 | `fa3806c842acefbe707499ffdec9f703bcedb5031962594df4c5293d0fbe6cfc` |
| Protocole AR SHA-256 | `bf7535eb4028715071744a2b8cc119b828f0eae2129a8f6b05e588872fcbf58d` |
| Fixture AJ gelée SHA-256 | `7b14816b6ed6f6bed8aaa8e3bbde568251cf94332aa6c7b12765f389d6ae226e` |
| Test natif SHA-256 | `d04f3c4d315adcc7d0d3f9d176b8afdbc4942d1cd8f9069bf513fe8b34e54451` |
| Runner one-shot SHA-256 | `c528b489839add5ee48b5e90bbce292c251486719868595e4868ceee6075b60d` |
| Générateur de rapport SHA-256 | `5d6683a1f1268c05f1a9fb9883b1e59e1967a9b15afb0df22d12fe2baa2b7916` |

Le HEAD et l'arbre Git identifient la base versionnée. Le jeu source SHA-256 fixe aussi les nouveaux fichiers préparatoires, encore non commités; le runner vérifie tous les hashes listés avant de lancer un scénario et en archive une copie contrôlée.

## Modèle, solveur et nombres gelés

Le modèle est construit avec les helpers gelés `_mesh` et `_load` d'AJ, puis résolu par le solveur FEM de production : `LinearStaticSolver` → `GlobalAssembler` → `FrictionlessActiveSetSolver`. Les résultats ne proviendront ni de l'adaptateur expérimental borné ni d'un substitut synthétique. L'adaptateur AJ n'est importé que pour ses helpers exacts de géométrie, charges, métriques et oracle QP indépendant; le test ne fait appel à aucun de ses solveurs.

Les constantes du modèle sont celles d'AR : TET4 structurés avec la subdivision AJ, domaine `[0,1]×[0,1]×[0.001,1.001] m`, `E=3 MPa`, `ν=0`, déplacement nul sur les trois composantes de tous les nœuds de face supérieure. Le plan rigide z=0 est représenté par un triangle explicite orienté +z dont les trois nœuds géométriques sont fixes. Cette représentation ajoute 9 DDL fixes au modèle du solveur; les comptes des DDL mécaniques du corps et de la référence KKT restent ceux du plan AR.

Chaque nœud inférieur porte une contrainte séparée, frictionless, de gap `g=0.001+u_z`, avec `g≥0`, `λ≥0`, `gλ=0`, `gap_tolerance=1e−10 m`. La politique dimensionnelle donne `force_reference=1000 N`, `relative_force_tolerance=1e−10` et `force_tolerance=0`; avec une contrainte singleton par ligne, elle produit `1e−7 N` par ligne. La projection est `accepted_rigid_plane_v1`, la recherche est initiale et la limite d'itérations active-set de production est 128. Aucune équation ou tolérance scientifique n'est changée.

M4 utilise `(nx,ny,nz)=(8,4,4)`, 225 nœuds corps, 768 TET4, 675 DDL mécaniques, 540 DDL libres et 45 lignes de contact. M5 utilise `(10,5,5)`, 396 nœuds corps, 1500 TET4, 1188 DDL mécaniques, 990 DDL libres et 66 lignes. Le préflight confirme ces comptes, la face de support, la loi et la géométrie/contact normaux. Il appelle `MeshValidator` et calcule les géométries nodales; il n'assemble pas `K` et n'appelle pas `LinearStaticSolver`.

## Dépendances et limites de ressources

Environnement gelé : Python `3.13.1`, NumPy `2.2.6`, SciPy `1.15.2`, pytest `8.4.1`, psutil `7.2.2`, threadpoolctl `3.6.0`, Windows 10 x64. Les imports des dépendances du solveur et des outils d'exécution ont réussi. `pip check` signale des conflits entre paquets globaux non utilisés par cette campagne (`kokoro`/`misaki`, contrainte NumPy de `kokoro`, `langchain-core`/`packaging`); le runner contrôle les versions exactes des cinq paquets ci-dessus.

Chaque scénario aura une limite de 900 secondes et un plafond RSS de 4 GiB pour le processus pytest et ses descendants, surveillé toutes les 0,5 s par psutil. Au dépassement, le runner termine l'arbre de processus. Les bibliothèques numériques sont limitées à un thread; aucune limite CPU matérielle portable n'est configurée. Le léger dépassement mémoire entre deux échantillons est possible et sera documenté dans le reçu. Le runner crée un ledger avant chaque lancement, refuse tout réemploi du dossier d'archive, marque `attempt_count=1` et n'active aucun plugin de retry. Après un échec scientifique enregistré, l'autre niveau distinct est tenté une seule fois; un timeout, dépassement mémoire ou arrêt d'infrastructure sans diagnostic arrête la campagne.

Le dossier d'archive réservé est `qualification/0_2_12/wpc02_ar_native_campaign_20261023_01`. Il n'existe pas avant GO et sera créé une seule fois. Le runner archivera le manifeste, un snapshot de toutes les sources hashées, le ledger, les logs, les vecteurs/scalaires de chaque scénario, le rapport et l'inventaire SHA-256 final.

## Données historiques M1–M3

Les valeurs suivantes sont la synthèse publiée d'AQ, réutilisée sans relancer ces scénarios. Les valeurs détaillées d'AQ ne sont pas remplacées. Les réactions exactes de support et les traces de front par rangée ne sont pas enregistrées dans le résumé disponible.

| Niveau | Erreur déplacement L2 relative | Erreur pression L2 relative | Erreur énergie relative | Énergie FE (J) | Norme erreur énergie (√J) | Force contact (N) | Erreur force relative | Erreur moment contact (N·m) | Front max (m / hx) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 | 0.0115305 | 0.463891 | 0.0374964 | 1.47758032 | 0.0646443 | 173.105166 | 0.0386310 | 7.86139 | 0 / 0 |
| M2 | 0.00585335 | 0.259359 | 0.0234189 | 1.48466497 | 0.0403744 | 167.294915 | 0.00376949 | 2.46729 | 0.25 / 1 |
| M3 | 0.00341925 | 0.156072 | 0.0166456 | 1.48544229 | 0.0286972 | 166.920874 | 0.00152524 | 1.24025 | 0.166667 / 1 |

Ces valeurs historiques ont déjà satisfait les gates AQ/AJ consignées; le ratio historique M1→M3 vaut `<0.9` pour déplacement et pression, avec décroissance de la norme d'erreur énergie. La référence exacte publiée est `U=1.486108265595 J`, `F_contact=166.6666666666666 N`, `M_contact=[83.3333333333333,−20.8333333333333,0] N·m`. Les faux positifs de front M2/M3 sont publiés à une cellule du front et les faux négatifs sont nuls; les rangées détaillées, les brackets, les comptes par rangée et les valeurs biactives ne sont pas archivés dans le résumé.

## Critères scientifiques

Le test lit les gates historiques et prospectives du JSON AR gelé. Les seuils restent inchangés :

- À chaque niveau exécuté : contact partiel et nœuds ouverts; pénétration et reconstruction de gap `≤1e−10 m`; complémentarité `≤1e−10 N·m`; gap actif `≤1e−10 m`; multiplicateur ouvert `≤1e−7 N`.
- KKT production : stationnarité `≤1e−6 N`; oracle QP sur toutes les lignes : gap primal `≥−1e−10 m`, multiplicateur dual `≥−1e−7 N`, complémentarité `≤1e−10 N·m`, stationnarité `≤1e−6 N`.
- Production/QP : erreur maximale déplacement `≤1e−9 m`, multiplicateur `≤1e−6 N`; bilans normalisés force et moment `≤1e−9`; identité de travail `≤1e−9 J`.
- FE : différence énergie matrice/quadrature `≤1e−10 J`; erreurs de résultante et moment de contact doivent être finies, sans seuil de discrétisation ajouté.
- Gate historique M1→M3 : erreurs relatives de déplacement et pression ratio `<0.9`, norme d'erreur d'énergie strictement décroissante.
- Extension AR M1→M5 : mêmes inégalités numériques `<0.9`, `<0.9`, décroissance d'énergie, appliquées à M5. Il n'y a pas de gate de monotonie adjacente.
- Front M2–M5 : `D_front,max/hx≤1`, bracket actif/ouvert ordonné dans chaque rangée, toutes les classifications erronées à distance `≤hx`, aucun front multiple. M1 n'ancre pas cette tendance car il est aligné au front biactif.

Le rapport final séparera les gates AJ historiques, les critères prospectifs AR et l'état de qualification. Les données AQ conservées ne suffisent pas à revérifier la couverture de chaque rangée M2/M3. Si M4/M5 satisfont leurs critères mais que cette preuve historique demeure absente, le gate de front M2–M5 et la conclusion complète resteront `NOT_ACQUIRED`; cette lacune ne sera pas masquée en relançant M1–M3.

## Tests préparatoires et revue indépendante

- `python -m py_compile` sur le test, le runner et le rapporteur : réussi.
- `python -m pytest -q tests/verification/test_wpc02_ar_native_contact_convergence.py::test_wpc02_ar_native_model_preflight_m4_m5` : `1 passed`.
- `python -m pytest -q tests/verification/test_wpc02_ar_native_contact_convergence.py` : `1 passed, 2 skipped`; M4/M5 ont été ignorés par la porte GO, aucun solveur FEM n'a été appelé.
- Une première tentative de préflight a révélé que `FiniteElementModel.from_raw` attend des dictionnaires pour les contacts; le constructeur a été corrigé, puis le préflight final a passé. Cette erreur de préparation n'a déclenché aucun calcul scientifique et ne constitue pas un retry M4/M5.
- Le runner final désactive l'auto-chargement de plugins pytest externes et fixe `--confcutdir=tests/verification`; le test dédié ne dépend donc pas de `tests/conftest.py` ni d'autres hooks du dépôt. Il refuse aussi l'apparition d'un `tests/verification/conftest.py` non gelé.
- Revue indépendante du gel préparatoire : **en attente**. Aucune campagne FEM n'est autorisée avant son résultat et le GO Owner.

À la vérification de l'état du worktree, six changements suivis hors du jeu source natif sont présents dans les fichiers WP-C02-AT `test_wpc02_at_worker_contract.py`, `wpc02_at_bounded_capture.cs`, `wpc02_at_build.ps1`, `wpc02_at_docker_worker.py`, `wpc02_at_freeze_manifest.ps1` et `wpc02_at_guarded_docker.ps1`. Le premier relevé du worktree était propre; d'autres changements sont apparus pendant cette préparation et leur origine n'est pas connue. Ils touchent le chemin WP-C02-AT/Docker, n'ont pas été faits par cette préparation, ne sont pas inclus dans le manifeste source natif, et ont été laissés intacts. Aucun Docker ni fichier de résultat historique n'a été modifié par cette campagne. L'Owner doit en tenir compte avant de donner le GO.

Les résultats natifs, lorsqu'ils seront autorisés, resteront des preuves de calcul local. Ils ne seront pas déclarés équivalents à la qualification Docker et ne recevront pas `VERIFIED_BOUNDED` sans approbation explicite d'un protocole de remplacement et satisfaction du contrat de qualification.

## Décision Owner requise

Après la revue indépendante, l'autorisation à fournir est : **`GO-RUN-FEM-NATIF` pour le manifeste SHA-256 `dd17e77d6b9776508e26642a33636df2920a612542caff93cae2134cf02bc105`**. Le runner contrôlera ce hash exact, puis exécutera M4 et M5 une fois chacun dans l'ordre indiqué. À ce stade, cette autorisation n'est pas encore donnée.
