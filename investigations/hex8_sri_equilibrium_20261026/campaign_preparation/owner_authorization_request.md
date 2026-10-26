# HEX8-SRI — Dossier de préparation et décision d’exécution

## État

Préparation technique complète. Aucun des six nodeids n’a été lancé; aucun assemblage, résolution FEM ou calcul global n’a été exécuté. Tous les manifestes finaux portent `execution_authorized=false` et `do_not_execute=true`. La politique `hex8sri` porte aussi `execution_authorized=false`.

Branche scientifique : `research/hex8-sri-equilibrium`  
Code expérimental figé : `b547cf0e1c8057ef7f58ba780967d1b19c891ac4`  
Commit des manifestes et inscriptions scientifiques : `528a87b18ca18196ee82f31339e9990d32044131`  
Fingerprint des sources : `e14217217a6044ca9cb7c64a0f187864121589463c00e1eaac53251696b60c29`

## Contrôleur canonique et inscription séparée

Avant toute modification, les blobs des trois fichiers du contrôleur de la branche scientifique ont été comparés à ceux de `emptiesvoids-cloud/0.2.12`. Ils étaient identiques : runner `cada122b620d7a48da41dc3358e20bfd76c0b426`, politique `a5e155385d1f10b387326d4a74fb051c5f7c87ec`, plugin `85f7a449350878ba7021017e7be6e5e37fcf76ab`.

Le contrôleur canonique ne permettait pas `hex8sri`: sa validation exigeait les clés exactes `d01/c01/e01`, et son seul préflight collect-only était D01-spécifique. L’extension minimale est donc isolée sur `codex/hex8sri-controller-registration`; aucun fichier contrôleur ou politique partagée n’a été modifié dans la branche scientifique. Le correctif conserve les contrôles et les inscriptions D01/C01/E01, n’active aucun override de skip, ajoute un préflight exact collect-only avec reçu lié aux manifestes et exige le préflight pour chaque run. La politique et chaque manifeste doivent tous deux autoriser l’exécution avant qu’un corps de test puisse démarrer.

Branche de configuration : `codex/hex8sri-controller-registration`  
HEAD de configuration : `616c9e2be7f020677bea5f67c92680bbe396aa3e`  
SHA-256 du runner : `9121059c172d3ab4e692042e283fe35e264503b35c736a86eb33bd4cf1837387`  
SHA-256 de la politique : `045dc5a01b472236de26a7ce6a8e3d3e0830c557dbd4796ff4d069ebf7ab8122`  
SHA-256 du plugin inchangé : `c1cf6238bba05fa24de5c455beac9ddd6844935999e8b4556d3b13e5f6e9ee16`

Contrôle statique du contrôleur : la politique charge, les six nodeids sont résolus exactement, les six manifestes correspondent aux SHA enregistrés, et la demande d’autorisation sur un manifeste de préparation est refusée comme attendu. Le test pytest du contrôleur n’a pas atteint sa collecte : le garde-fou E01 existant a refusé `tests/unit/test_wp_e01m_hencky_material_point.py`, dont l’empreinte actuelle (`0d58ad2a499d13f84752f931c872c987577f8d3faae52cac06a8449ab2e2cec4`) diffère de l’attendue (`cdd2651e9427c0e64284a75671d83d4f14cdd916a979759be0422f44dde84bfc`). Ce garde-fou, son empreinte et les archives n’ont pas été modifiés ni contournés.

## Problème commun et méthode

- Géométrie : porte-à-faux `20×1×1 m`, maillage régulier `4×2×2`, 16 HEX8, 45 nœuds.
- DDL : 135 translationnels UX/UY/UZ; face `x=0` fixée, indices globaux 0–26 (27 DDL); 108 DDL libres.
- Matériau : élasticité isotrope linéaire, `E=1,0e6 Pa`, `ν=0,3` ou `0,4999`.
- Charge : traction consistante `(0,0,−1) Pa` sur la face `x=20`, aire `1 m²`; résultante `(0,0,−1) N`, moment à l’origine `(−0,5,20,0) N·m`.
- Les trois opérateurs sont appelés directement depuis le harness de recherche. Aucun registre public ni solveur global de production n’est utilisé. La variante historique surcharge uniquement le bloc volumique central par l’expression du parent `2aa994f34900f39bef8df9db5fb025157fb694bb`, sans poids 8.
- Résolution préparée : assemblage local explicite et solveur SciPy direct. Le seuil relatif historique `1e−7` est conservé.

Le sidecar JSON et l’état NPZ sont écrits par création atomique sans remplacement avant les assertions. Ils lient les identités science/contrôleur/manifeste, les déplacements signés et normes, déformations de Gauss, énergies/travail, résidu libre, réactions, fermetures forces/moments, conditionnement, temps, RSS observé, états matriciels et verdicts. Fermetures et énergie sont rapportées sans nouveau seuil; la convergence spatiale reste non évaluée sur un maillage.

## Nodeids et SHA-256 des manifestes actifs

| Cas | Nodeid exact | SHA-256 |
|---|---|---|
| HEX8 standard, `ν=0,3` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[hex8_standard_nu_0p3]` | `7c9a77f69b6e59d3f2c143143e420ca801865b4208f4d35c6b2721661532bc14` |
| SRI historique, `ν=0,3` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[sri_historical_nu_0p3]` | `99e3b78d357586888adc66e0aaf4ddb48110d9952d21573c412f3c42da48900e` |
| SRI corrigé, `ν=0,3` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[sri_corrected_nu_0p3]` | `cd8815d4b49516dc93595ee14c300a8f8de3c1c21fbaea4f41fa0cb42dc44f41` |
| HEX8 standard, `ν=0,4999` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[hex8_standard_nu_0p4999]` | `9f1eaf63c79673e2b1a465ff6ed92ac467d4df02974441bb11bfe8a293eaf0e9` |
| SRI historique, `ν=0,4999` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[sri_historical_nu_0p4999]` | `4977e56ec132e70f2d55b459ae6998f75d151a125dacdee36e767aa88f0eee50` |
| SRI corrigé, `ν=0,4999` | `tests/verification/test_hex8_sri_structural_campaign.py::test_hex8_sri_cantilever_campaign[sri_corrected_nu_0p4999]` | `df4e052fccefd0b3cb62ed0a4603e2841d3a378f43388b98d08ad66f7c75933d` |

Ces SHA référencent les six manifestes de `final_candidates/b547cf0e1c8057ef7f58ba780967d1b19c891ac4_9121059c172d_protocol2/`. Les brouillons historiques préexistants restent inchangés. Trois jeux intermédiaires produits pendant la préparation sont conservés avec `candidate_status.json` les marquant `SUPERSEDED_NOT_REGISTERED_NOT_EXECUTION_AUTHORIZED`; ils ne sont pas inscrits dans la politique.

## Budgets inscrits

- 180 s par cas; une seule tentative par nodeid; maximum six tentatives pour cette campagne.
- RSS 1 024 MiB : observation souple échantillonnée.
- 8 processus : observation du contrôleur.
- stdout/stderr 8 MiB chacun, 16 MiB agrégés : limites de capture du contrôleur.
- Temporaires 64 MiB et archive 64 MiB : observations échantillonnées, pas quotas système.
- Espace disque libre minimal : 1 024 MiB.
- `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`.

## Vérifications réalisées

- `py_compile` : PASS pour harness, test campagne, écrivain, builder et runner de contrôleur.
- Test synthétique de l’écrivain : `2 passed`; vérifie l’écriture JSON, son SHA, le refus de remplacement et le nettoyage du temporaire; aucun FEM.
- Contrôle statique d’inscription : PASS pour les six nodeids, leurs six SHA, les manifestes exacts et le refus du gate d’exécution.
- Pytest ciblé du contrôleur : BLOCKED avant collecte par la divergence d’empreinte E01 indiquée ci-dessus.
- Collecte ou lancement des six nodeids : NOT_RUN, conformément à la décision Owner.
- Résolutions FEM : NOT_RUN.

## Décision Owner encore requise

La préparation et l’instrumentation sont complètes. Avant toute exécution, il faut une décision Owner distincte couvrant les six résolutions. À cette étape, le préflight exact collect-only sera produit pour chaque nodeid selon le contrôleur enregistré; les manifestes/politique devront recevoir l’autorisation correspondante et de nouveaux SHA seront calculés si leur contenu change. Aucun seuil ne sera retouché après résultats.
