# Dossier de validation Owner — WP05-D HEX20

**Objet :** permettre la revue et la décision Owner sur la requalification formelle WP05-D.  
**Date des résultats :** 16 septembre 2026 (Europe/Paris).  
**Décision Owner reçue :** `ACCEPT 1/1 technique dans le périmètre établi`.  
**Date de décision :** 16 septembre 2026.  
**Identité Owner :** non renseignée dans le message de décision.

## Décision Owner enregistrée

Le candidat WP05-D satisfait les gates formels consignés ci-dessous. La décision reçue est enregistrée ici :

- [x] **ACCEPT** WP05-D à 1/1 technique, avec le périmètre et les limitations de ce dossier.
- [ ] **HOLD** — revue ou preuves complémentaires nécessaires.
- [ ] **REJECT** — indiquer les critères non acceptés dans les commentaires.

Nom Owner : ____________________  Date : ____________________

Commentaires / conditions :

______________________________________________________________________________

______________________________________________________________________________

Cette décision accepte techniquement WP05-D à 1/1 dans les limites documentées. Elle ne valide pas WP05-C/E. Les résultats bruts et le résumé formel restent inchangés. Le dossier est encore sur la branche isolée, avec `EVIDENCE_COMMIT_SHA = NOT_YET_COMMITTED`; le ledger governing, le merge et le push n’ont pas été modifiés ou effectués par l’enregistrement de cette décision.

## Résumé de la preuve

| Gate | Résultat constaté |
|---|---|
| Préflight et provenance | PASS |
| Production HEX20 H1/H2/H3 | PASS ; 12/12 incréments par cas ; 0 fallback |
| Recalcul indépendant de l’observable H1/H2/H3 | PASS ; post-traitement NumPy indépendant appliqué aux sorties brutes de production |
| Replay H1 | PASS ; statuts, facteurs de charge, observables, Newton et fallback comparés |
| Équilibre, enveloppe, charge et qualité maillage | PASS pour H1/H2/H3 |
| Convergence H2→H3 | PASS sur les cinq observables contractuels |
| Résultats historiques | L’ancien FAIL_CLOSED est préservé, non écrasé |

**Statut formel :** `PASS_CANDIDATE_OWNER_REVIEW_REQUIRED`  
**Candidat WP05-D :** 1/1  
**Décision Owner technique WP05-D :** ACCEPT 1/1 dans le périmètre établi  
**Ledger governing avant intégration de la décision :** WP05-D 0/1 ; total 58/100  
**Après enregistrement de cette acceptation dans le ledger governing :** WP05-D 1/1 ; WP05 3/5 ; total 59/100

## Périmètre exact de la qualification

Cette requalification concerne le benchmark cantilever HEX20 et la mesure de contrainte révisée, autorisée séparément par Owner. Elle ne modifie pas les mécaniques de production.

- Géométrie : (L=4.0, H=0.5, D=0.5), barre droite et éléments HEX20 affines.
- Matériau : (E=10^6, \nu=0.30).
- Encastrement : face (x=0).
- Résultante appliquée : `[0, -50, 0]`.
- Moment à l’origine : `[12.5, 0, -200]`.
- Charge : traction nodale cohérente ; intégration de la face Q8 en Gauss 2×2.
- Route : geometric nonlinear static, MINRES + Jacobi, canonical line search, floor-aware termination.
- 12 incréments de charge par exécution ; fallback direct désactivé et aucun fallback observé.
- Hiérarchie HEX20 : H1 `4×2×2`, H2 `8×4×4`, H3 `16×8×8` cellules parent.

### Observable de contrainte candidat

La fenêtre de référence physique est définie par :

- (x/L=[0.4,0.6]), soit (x=[1.6,2.4]) ;
- (y/H=[0.7,0.95]), soit (y=[0.35,0.475]) ;
- (z/D=[0.2,0.8]), soit (z=[0.1,0.4]) ;
- volume de référence attendu : `0.03` ; quadrature tensorielle Gauss 5 par axe.

La production utilise `EXACT_REFERENCE_WINDOW_CLIPPED_HEX20_TENSOR_GAUSS_5`. Le recalcul indépendant de l’observable reprend les coordonnées, connectivités et déplacements bruts produits par le solveur, puis recalcule la fenêtre et σxx avec sa propre implémentation NumPy (`INDEPENDENT_NUMPY_HEX20_CLIPPED_WINDOW_GAUSS_5`). Ce code n’importe ni `solveur` ni le module de post-traitement de production.

**Précision importante pour la décision Owner : il ne s’agit pas d’une résolution FEM indépendante.** Aucun second solveur n’a assemblé/résolu le problème mécanique. Cette preuve valide indépendamment le calcul de l’observable à partir des sorties de production ; elle ne constitue ni une seconde solution d’équilibre ni une corrélation indépendante du champ de déplacement.

**Limite de portée :** cette mesure candidate est approuvée ici uniquement pour des HEX20 droits/affines. Elle ne démontre pas une qualification de contrainte générale pour des maillages courbes/déformés ni pour TET10. La comparabilité de contrainte nécessaire à WP05-E doit être auditée avant toute fermeture inter-familles.

## Résultats de production par maillage

Les contraintes sont dans les unités du modèle. Les vecteurs sont `[x, y, z]`.

| Cas | Nœuds / éléments / DOFs | Temps mur | Newton total | Déplacement en bout | Réaction résultante | Moment de réaction | Énergie | σxx candidate | Équilibre force / moment | Fallbacks |
|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|
| H1 | 141 / 16 / 423 | 106.833 s | 152 | -0.1996119577533075 | `[7.063e-12, 50.0, 3.553e-14]` | `[-12.5, 2.203e-12, 199.69861013713208]` | 4.983671699041345 | 3114.8532844264123 | `1.4143e-13 / 1.4017e-14` | 0 |
| H2 | 785 / 128 / 2355 | 888.606 s | 156 | -0.203275972792037 | `[-1.059e-12, 50.0, 1.421e-14]` | `[-12.5, -5.862e-13, 199.689014902001]` | 5.07529880469701 | 3105.007421862718 | `2.1184e-14 / 5.7709e-15` | 0 |
| H3 | 5121 / 1024 / 15363 | 7340.838 s | 156 | -0.204429380246835 | `[4.210e-13, 50.0, 1.288e-13]` | `[-12.5, 1.439e-13, 199.68603435188]` | 5.10406978458417 | 3104.950355967558 | `8.8975e-15 / 1.2304e-15` | 0 |

Les trois cas ont le statut production `PASS`, 12 incréments acceptés sur 12 et les contrôles de charge et de maillage à `PASS`.

### Enveloppe de déformation

| Cas | min detF | Étirement principal min–max | max ‖E‖F | Enveloppe |
|---|---:|---:|---:|---|
| H1 | 0.994239810857063 | `[0.992772929780595, 1.00723113166533]` | 0.0078087035531238 | PASS |
| H2 | 0.993520058722856 | `[0.991434512779879, 1.00847765761582]` | 0.00928876478626652 | PASS |
| H3 | 0.992647220568447 | `[0.990391693415895, 1.00953847921681]` | 0.00984075991924316 | PASS |

## Gates de convergence H2→H3

Les valeurs ci-dessous sont des écarts relatifs exprimés en pourcentage. Les seuils sont gelés ; aucun n’a été modifié.

| Observable | Écart H2→H3 | Seuil | Résultat |
|---|---:|---:|---|
| Déplacement en bout | 0.5642082627 % | 2 % | PASS |
| Réaction résultante | 2.9683×10⁻¹² % | 2 % | PASS |
| Moment de réaction | 0.0014897023 % | 2 % | PASS |
| Énergie de déformation | 0.5636870400 % | 2 % | PASS |
| σxx représentative — mesure candidate | 0.0018379004 % | 8 % | PASS |

## Recalcul indépendant de l’observable et replay

| Maillage | σxx production candidate | σxx recalculée en NumPy | Volume de la fenêtre recalculé | Écart relatif σxx | Résultat |
|---|---:|---:|---:|---:|---|
| H1 | 3114.8532844264123 | 3114.8532844264123 | 0.030000000000000075 | 0 | PASS |
| H2 | 3105.007421862718 | 3105.007421862718 | 0.029999999999999732 | 0 | PASS |
| H3 | 3104.950355967558 | 3104.950355967558 | 0.029999999999998913 | 0 | PASS |

Le replay H1 est `PASS`. Les vérifications enregistrées couvrent le statut, les facteurs de charge acceptés, les observables, le nombre exact d’itérations de Newton et le nombre exact de fallbacks. Tolérances du replay : absolue `1e-14`, relative `1e-12`. Le replay a pris `108.275 s`, 152 itérations Newton et 0 fallback.

## Historique à préserver

L’ancien résultat WP05-D utilisant l’observable historique reste `FAIL_CLOSED` et fait partie de l’historique officiel. Il n’est ni supprimé ni remplacé par cette nouvelle méthode.

| Mesure historique | H2 | H3 | Écart H2→H3 | Seuil historique | Statut historique |
|---|---:|---:|---:|---:|---|
| σxx historique | 2914.8233075483017 | 3254.1440918472313 | 10.4273435571 % | 8 % | FAIL_CLOSED préservé |

La présente candidature est fondée sur l’observable de fenêtre de référence révisée, pas sur une modification de mécanique, de seuil, de charge ou de solveur. Les deux lignées de résultats doivent rester distinguées.

## Provenance et intégrité

| Champ | Valeur |
|---|---|
| ID d’autorisation | `VNV029-WP05-D-FORMAL-REQUALIFICATION-AUTH-001` |
| Branche d’exécution | `codex/wp05d-formal-requalification` |
| `AUTHORIZED_BASE_SHA` | `a670f106f4eef88a3cfe5ca65a09ed55cdcc19fe` |
| `REMEDIATION_SHA` | `817b5d098b280fbd0b7fa2938c3204d859f20b0c` |
| `EXECUTION_SHA` | `72282a6ca6e6574a32c6182eccb001d9816febbc` |
| `EVIDENCE_COMMIT_SHA` | `NOT_YET_COMMITTED` |
| `FINAL_SHA` | `NOT_YET_COMMITTED` |
| `REMOTE_HEAD` | `NOT_PUSHED` |
| Contrat candidat SHA-256 | `b5c05bc59d70ea53fdb0b480f4734c0dd53451b75c889e16e750c9fc6e7c12da` |
| Contrat historique SHA-256 | `e8ce5ed095bf3f142b64d5a5838682c638478a5a92c8330a10af88584f52d680` |
| Digest code policy gelée | `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac` |
| Digest de binding policy runtime | `895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5` |

Les deux digests de policy identifient des choses différentes et sont volontairement reportés séparément. Le préflight a vérifié les deux bindings attendus. Les hashes des NPZ bruts, résultats et références sont listés ci-dessous ; le JSON récapitulatif contient également les comparaisons et diagnostics détaillés par incrément.

### SHA-256 des preuves numériques

| Artefact | SHA-256 |
|---|---|
| H1 production `raw.npz` | `df0ecfcdcc39dc093ed7ae70779572e5ae936e82088549267400fd018ec6f48f` |
| H1 production `result.json` | `001f7a701fcd5adcaba61a8c7db7d90db27e37b353212ce8d54c008ab1b5def0` |
| H1 recalcul NumPy `result.json` | `7d5170e2998ae33e9769102585a1116e718523559a463ae5323131d785d4973b` |
| H2 production `raw.npz` | `055adadb7f3012ec295a6674a37e546a2f3d8c92a7ad29e531991598bff25348` |
| H2 production `result.json` | `6be156519d48134b4bf3d2a6097b656e717b654cab0a5b5637aca53407e23f51` |
| H2 recalcul NumPy `result.json` | `d45ecdb3b84857a85ca3000c2e1dcf6c7416f5be8cd0dced93fe9f1aec4b7897` |
| H3 production `raw.npz` | `1c51bd2e8df0a94dae6f10f70d435667e6f29478cd57d44c7448270afd808444` |
| H3 production `result.json` | `7b79c9b436e379eeca9bf2b7ae6d2d6eb4d685f76987c4d313f620b8cb93feec` |
| H3 recalcul NumPy `result.json` | `65c43206f37650da626ee0a6bc8361684316a710f09d4c1c6722eea72277317c` |
| Replay H1 `raw.npz` | `df0ecfcdcc39dc093ed7ae70779572e5ae936e82088549267400fd018ec6f48f` |
| Replay H1 `result.json` | `5c13a6e185e227a42de2a8f135c83e85c6789172e9c7415c8ceb1fe0be9d0915` |
| Résumé formel `formal_requalification_summary.json` | `1b72f1f3614b9ce536de0abc7e718a476f8ee328db4d13514c3d3d9b3d61b978` |

## Contrôles logiciels et règles de gouvernance

Contrôles ciblés enregistrés avant les calculs :

- tests ciblés : `29 passed` ;
- Ruff : PASS ;
- mypy : PASS, cinq fichiers source ;
- compileall : PASS ;
- validation JSON : PASS ;
- suite complète du dépôt : **non exécutée**.

**Gate avant merge final :** conformément à la revue Owner, la suite complète du dépôt reste à lancer avant tout merge final. Son absence ne remet pas en cause les résultats numériques ni l’acceptation technique WP05-D ci-dessus ; elle signifie que le paquet n’est pas encore prêt pour le merge final. Elle n’a pas été lancée dans le cadre de cet échange.

| Contrôle | Valeur |
|---|---|
| Changement de mécanique de production | NO |
| Changement de seuil | NO |
| Fallback | 0 sur H1/H2/H3 et replay |
| Ancien FAIL_CLOSED conservé | YES |
| WP05-E exécuté | NO |
| Points officiels modifiés automatiquement | NO |
| Suite complète du dépôt avant merge final | NOT RUN — à exécuter avant merge |

## Incidence sur WP05 et décision de score

| Partie WP05 | Points officiels actuels | État |
|---|---:|---|
| WP05-A/B | 2/2 | Clos |
| WP05-C — TET10 | 0/1 | Pas exécuté dans cette campagne |
| WP05-D — HEX20 | 0/1 inscrit au ledger governing ; 1/1 accepté techniquement | ACCEPT Owner enregistré ; intégration au ledger encore à effectuer |
| WP05-E — inter-familles | 0/1 | Non exécuté ; dépend de C/D et d’un audit de comparabilité des observables |
| **WP05 total actuel** | **2/5** | Score officiel inchangé |

L’acceptation technique Owner de WP05-D est maintenant explicite. La mise à jour correspondante est WP05 `3/5` et total global `59/100`, une fois portée au ledger governing. Dans le dépôt actuel, le ledger officiel demeure `2/5` et `58/100` jusqu’à cette intégration. WP05-C et WP05-E demeurent à zéro jusqu’à leurs propres preuves et décisions applicables. Aucun score n’est changé par ce document.

## Artefacts source à inspecter

Chemins relatifs à la racine du dépôt :

- Autorisation : `qualification/0_2_9/wp05d_formal_requalification_authorization.json`
- Contrat candidat : `qualification/0_2_9/wp05_cd_stress_window_remediation_candidate.json`
- Contrat structurel : `qualification/0_2_9/wp05_cd_structural_contract.json`
- Rapport produit par le runner : `qualification/0_2_9/wp05d_formal_requalification/formal_requalification_report.md`
- Résumé complet / diagnostics : `qualification/0_2_9/wp05d_formal_requalification/formal_requalification_summary.json`
- Production brutes : `qualification/0_2_9/wp05d_formal_requalification/production/HEX20/{H1,H2,H3}/`
- Sorties du recalcul NumPy indépendant de l’observable (nom de répertoire conservé tel quel par le runner) : `qualification/0_2_9/wp05d_formal_requalification/independent_reference/{H1,H2,H3}/`
- Replay : `qualification/0_2_9/wp05d_formal_requalification/replay/HEX20/H1/`
- Runner : `scripts/run_wp05d_stress_window_formal.py`
- Recalcul indépendant de l’observable (pas de solve FEM) : `scripts/wp05d_hex20_independent_reference.py`
- Test ciblé de requalification : `tests/verification/test_wp05d_formal_requalification.py`
- Autorisation détaillée : `docs/verification/0_2_9/wp05d-formal-requalification-authorization.md`

**État de publication :** les preuves formelles sont présentes localement, mais `EVIDENCE_COMMIT_SHA` et `FINAL_SHA` ne sont pas encore définis et aucun `REMOTE_HEAD` n’est déclaré poussé. Le paquet n’est donc pas intégré au ledger governing. Cette revue ne committe, ne pousse, ne merge ni ne modifie aucun score.
