# Clôture bornée du sous-dossier VV3D — QF Solver v0.2.12

**Disposition proposée :** `VV3D_CLOSED_BOUNDED_FOR_0_2_12`

**État :** `PROPOSED_PENDING_REVIEW_AND_OWNER_APPROVAL` — cette disposition ne devient effective qu’après intégration revue de cette modification et approbation Owner explicite.

**Périmètre :** sous-dossier VV3D seulement. `WP12-B`, `WP12` et `WP13` restent ouverts et inchangés.

## 1. Périmètre et méthode

La synthèse couvre les douze niveaux TET4, TET10, HEX8 standard et HEX20, L1 à L3, avec leurs scopes, sources, contrats et critères propres. Elle ne fusionne pas leurs ledgers. Les cas TET10, HEX8 et HEX20 proviennent de la campagne distincte `wp12_vv3d_family_remainder` (9/9 `CASE_GATE_PASS`). TET4 L1/L2 proviennent du scope R2; TET4-L3 a un timeout R2 historique, puis un diagnostic optimisé séparé. Les ordres TET4 ci-dessous sont une estimation descriptive inter-campagnes calculée à partir des observables conservés; ils ne transfèrent ni preuve ni verdict entre campagnes et ne valent pas `CONVERGENCE_PASS`.

Les nodeids sont les douze sélections `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-<FAMILLE>-L<N>]` enregistrées dans les contrats. Le scope R2 TET4 utilise la source HEAD `ba36860a156468dd7c54ee435a809222e227205a`, tree `2f8c0d3cef5a6b07eac9ad48d0dcb1a311af72e2`. Pour les neuf cas résiduels, les mesures lient le contrôleur de fingerprint `edf1ef48fdee1465b7889e6e894f56d440e9ba2863f4d6d3d39ed4cca4997e62` à la source de fingerprint `fdc76b49a21b9562dda517cecef7bf17c0a7a327f6fc1f1c6cfc7e9433c347bb` (HEAD `ac0f1855a88cc66e48e629eadc4f0e681d1d719d`, tree `39bf88bef3d72e6c970a3928d577239074f7b9fb`). TET4 conserve ses identités antérieures propres, détaillées à la section 5.

Le post-traitement optimisé `experiments/wp12_vv3d_adaptive/field_error_draft.py` est couvert dans la source figée par `tests/unit/test_wp12_vv3d_field_error_optimization.py`, dont les tests d’équivalence sont paramétrés pour TET10, HEX8 et HEX20 aux ordres 8 et 12, ainsi que pour des géométries cisaillées. Les formulations, quadratures, oracles et seuils gelés n’ont pas été modifiés dans ce dossier. Aucun FEM, benchmark ou test n’a été relancé pour préparer cette revue documentaire.

## 2. Résultats des douze niveaux

Les erreurs `e_u`, `e_E`, `e_s` et `e_σ` sont les erreurs relatives enregistrées : déplacement L2, norme d’erreur d’énergie `sqrt(J)`, énergie scalaire et contrainte L2 respectivement. Elles sont sans dimension. Le temps est le temps total mesuré par le contrôleur; RSS est le pic échantillonné arrondi au MiB. TET4-L3 utilise le diagnostic optimisé de 313,898 s; le timeout R2 après 1 200,161 s sans observables et le diagnostic précédent arrêté après 2 400,291 s restent dans l’inventaire des preuves.

| Famille | Niveau | État conservé | DDL | Temps (s) | RSS (MiB) | e_u | e_E | e_s | e_σ |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| TET4 | L1 | R2 `CASE_GATE_PASS` | 81 | 16,151 | 156,9 | 0,660636 | 0,791694 | 0,626780 | 0,788913 |
| TET4 | L2 | R2 `CASE_GATE_PASS` | 375 | 120,164 | 174,3 | 0,250935 | 0,470145 | 0,221036 | 0,465772 |
| TET4 | L3 | `DIAGNOSTIC_COMPLETED`; contrôles mécaniques `PASS`; seuil énergie scalaire `FAIL` | 2 187 | 313,898 | 317,6 | 0,074416 | 0,248065 | **0,061536** | 0,246878 |
| TET10 | L1 | `CASE_GATE_PASS` | 375 | 17,128 | 170,3 | 0,124004 | 0,293722 | 0,086272 | 0,288422 |
| TET10 | L2 | `CASE_GATE_PASS` | 2 187 | 73,595 | 279,8 | 0,016771 | 0,086922 | 0,007555 | 0,085713 |
| TET10 | L3 | `CASE_GATE_PASS` | 14 739 | 552,370 | 1 196,9 | 0,002052 | 0,023281 | 0,000542 | 0,023143 |
| HEX8 | L1 | `CASE_GATE_PASS` | 81 | 6,558 | 156,7 | 0,270078 | 0,461207 | 0,212712 | 0,461207 |
| HEX8 | L2 | `CASE_GATE_PASS` | 375 | 17,709 | 170,0 | 0,067633 | 0,226679 | 0,051383 | 0,226354 |
| HEX8 | L3 | `CASE_GATE_PASS` | 2 187 | 111,191 | 293,4 | 0,017116 | 0,113317 | 0,012841 | 0,113254 |
| HEX20 | L1 | `CASE_GATE_PASS` | 243 | 11,710 | 164,0 | 0,041403 | 0,124157 | 0,015415 | 0,123132 |
| HEX20 | L2 | `CASE_GATE_PASS` | 1 275 | 58,262 | 233,2 | 0,004935 | 0,024395 | 0,000595 | 0,024211 |
| HEX20 | L3 | `CASE_GATE_PASS` | 8 019 | 434,806 | 821,0 | 0,000609 | 0,005817 | 0,000034 | 0,005795 |

Pour les neuf cas du scope famille résiduelle, le temps cumulé est 1 283,330 s; le maximum est 552,370 s, 1 196,9 MiB et 14 739 DDL. Les plafonds approuvés de 1 200 s, 4 096 MiB et 30 000 DDL n’ont pas été dépassés. Les neuf cas ont chacun une seule tentative enregistrée et aucun retry.

## 3. Convergence et critères gelés

| Famille | Ordre déplacement L1→L2 / L2→L3 | Ordre énergie L1→L2 / L2→L3 | Décision sous le contrat |
|---|---:|---:|---|
| TET4 | 1,397 / 1,754 | 0,752 / 0,922 | Ordres observés sur preuves distinctes; descriptifs, pas `CONVERGENCE_PASS` |
| TET10 | 2,886 / 3,031 | 1,757 / 1,901 | `CONVERGENCE_PASS` dans le contrat famille résiduelle |
| HEX8 standard | 1,998 / 1,982 | 1,025 / 1,000 | `CONVERGENCE_PASS` dans le contrat famille résiduelle |
| HEX20 | 3,069 / 3,018 | 2,347 / 2,068 | `CONVERGENCE_PASS` dans le contrat famille résiduelle |

Les critères L3 et ordres des trois familles de la campagne dédiée sont :

| Famille | e_u L3 ≤ limite | Ordres e_u (limite) | e_E L3 ≤ limite | Ordres e_E (limite) | e_s L3 ≤ 0,05 | e_σ L3 ≤ limite | Bilan des critères |
|---|---:|---:|---:|---:|---:|---:|---|
| TET10 | 0,002052 ≤ 0,03 | 2,886 / 3,031 (≥2,1) | 0,023281 ≤ 0,15 | 1,757 / 1,901 (≥1,4) | 0,000542 | 0,023143 ≤ 0,15 | `PASS` |
| HEX8 | 0,017116 ≤ 0,10 | 1,998 / 1,982 (≥1,2) | 0,113317 ≤ 0,35 | 1,025 / 1,000 (≥0,7) | 0,012841 | 0,113254 ≤ 0,35 | `PASS` |
| HEX20 | 0,000609 ≤ 0,03 | 3,069 / 3,018 (≥2,1) | 0,005817 ≤ 0,15 | 2,347 / 2,068 (≥1,4) | 0,000034 | 0,005795 ≤ 0,15 | `PASS` |

L’assessment enregistré pour chaque famille résiduelle a `status=PASS` et aucune défaillance bloquante. Son champ de routage de campagne reste `decision=CONTINUE`; ce champ ne constitue pas une décision de clôture générale. Les ordres constatés décrivent uniquement ces familles, formulations, maillages, données et critères. Ils ne qualifient pas universellement les éléments.

Pour TET4-L3, le diagnostic optimisé rapporte `scientific_state=PASS` sur les contrôles mécaniques de son scope (jacobien positif, identité d’énergie, résidu libre, fermetures de force et de moment, quadrature des charges et post-traitement). Les observables d’erreur restent `DIAGNOSTIC_UNQUALIFIED`. Le contrôle d’énergie scalaire est distinct et reste `FAIL` :

| Contrôle mécanique TET4-L3 | Observation | Critère gelé | Résultat |
|---|---:|---:|---|
| Jacobien affine minimal | 0,001953125 m³ | > 0 | `PASS` |
| Identité d’énergie relative | 2,833×10⁻¹⁶ | ≤ 1×10⁻⁶ | `PASS` |
| Résidu libre relatif | 4,506×10⁻¹⁵ | ≤ 1×10⁻⁸ | `PASS` |
| Fermeture force relative | 1,180×10⁻¹⁵ | ≤ 1×10⁻⁸ | `PASS` |
| Fermeture moment relative | 1,008×10⁻¹⁵ | ≤ 1×10⁻⁸ | `PASS` |
| Différence quadrature charges Q8/Q12 | 1,369×10⁻¹⁴ | ≤ 1×10⁻⁶ | `PASS` |
| Différence quadrature post-traitement Q8/Q12 | 4,904×10⁻¹³ | ≤ 1×10⁻⁴ | `PASS` |

> `scalar_energy_relative_error = 0.06153606862707159 > 0.05` — `FAIL_THRESHOLD_NOT_MET`.

La convergence TET4 est observable à partir des erreurs relatives conservées, mais la précision exigée par le seuil d’énergie scalaire n’est pas acquise. Le seuil n’est pas modifié et ce FAIL n’est ni effacé ni converti en PASS.

## 4. Inventaire de provenance et intégrité

Les cinq ledgers sont conservés dans `E:\QFSolverAgents\evidence`. Leurs empreintes SHA-256 ont été recalculées en lecture seule et concordent avec les empreintes attendues. Le ledger de la campagne famille est aussi validé par son vérificateur de hash-chain et référence immuablement les quatre ledgers antérieurs.

| Campagne / scope | Contrat SHA-256 | Décision Owner (ID / SHA-256) | Contrôleur fingerprint | Source fingerprint | Ledger SHA-256; tentatives / résultat |
|---|---|---|---|---|---|
| R1 — `wp12_vv3d_adaptive` | `26617da1c0c430e1b5302aa9fd0bd9fb96d185e6303d25d74a309a1ee5669d08` | `vv3d-r1-initial-20261030-26617da1a` / `aaf33c4c8730328229cce047f14382906ea6f95fb1c7c715d265fcbac5d2e635` | `00f89f5dcf8540a1d257afe9f1e668b9b7bafc4a25d46436447f43a9c2cbef04` | `50b7bf6451a637de7967637b5a56a12ca9111d9d09609995dd94499526e120cf` | `2788619d097d148c74a3e71cef456ee52bc03642d680f9090360418b61d20bf8`; 2 — TET4-L1 `PASS`, TET4-L2 `INFRA_ERROR` |
| R2 — `wp12_vv3d_recovery_r2` | `62fcb9a63ef0f5d4b557f4e4a7ec6d076ca34bb4b4fcd4f139aa6a0f1c499e16` | `owner-vv3d-r2-20261030-154923-5e2e722` / `6950e12452d86a1b67a18f6c5cc395f07f1c5b3bd880b66824c3d6ffbd224fb5` | `851194718819999d483710435d0e119c799787e5962148b3e50672a99f6f387e` | `651bbacaf133106a6a8c8b2177e8741cf3fed9a9fdfc7f907d350484dfebd3ce` | `5e090e1351578803669af37f04d161a6c4608436763f87d71e03315978446bb5`; 3 — TET4-L1/L2 `PASS`, TET4-L3 timeout à 1 200,161 s / `INFRA_ERROR` |
| Diagnostic TET4-L3 précédent — `wp12_vv3d_tet4_l3_diagnostic` | `160b1a8f93a2aca25b80ba84ba5279c64a6f4df9a74705766b0c636b33e7dc39` | `owner-approved-20261030-tet4l3` / `998cc53842028e1e0c2369919371b195aad7106942a6b04ae4139f5079656bf4` | `c3d2d0946b9bf2063d4cb3bf4143877eaec0f93d2c4751178baad427d2e0c987` | `7500b3121983a05634c0cb5ddf5b58bca1bb3a85825066d589dda2d07a9e9a41` | `3dfab79fabd3ae5986b265ecdebf6a4ed1030f3806ab25ae12f0a9d4a1f5e6c4`; 1 — `DIAGNOSTIC_STOP` après timeout à 2 400,291 s |
| Diagnostic TET4-L3 optimisé — `wp12_vv3d_tet4_l3_optimized_diagnostic` | `5e76c4b656b95f0dc801631f38fd899c0184f2b849b10d89f594c3fc999ae0d0` | `owner-vv3d-tet4-l3-opt-20261030` / `126c1608981a7023596bfbf0a33d88f2d41b046b82b9c45a2d71453e49b5bc78` | `306903e538a0eb98c1805f6c443bd0c408ea836dd8b7e0cd508f09cddadcbbe8` | `d2ccee34ab5aba092bcacfa98e2d3332edc7fe02c9e1c7b39de092a59635d39b` | `43b3a680acf30493d057bb58079ad6a9b3c4834e371314c7ec5a935834e49732`; 1 — `DIAGNOSTIC_COMPLETED` en 313,898 s, `scientific_state=PASS` mécanique |
| Famille résiduelle — `wp12_vv3d_family_remainder` | `3b36aad892703d2a1131bff40ae0c4430ed04acf55c285e39142cb20e6049bd3` | `owner-vv3d-family-20261031-02` / `5b0e8db781aba502f0b97052a0ec2d2741ef06edbbf7f6d6b607c801ffc94592` | `edf1ef48fdee1465b7889e6e894f56d440e9ba2863f4d6d3d39ed4cca4997e62` | `fdc76b49a21b9562dda517cecef7bf17c0a7a327f6fc1f1c6cfc7e9433c347bb` | `e3343e83372760ed37d9165cc3a6b199d70c8aa958afcf842128c4fbffe752a4`; 9 — 9/9 `PASS` |

Les contrats et décisions sont sous les répertoires d’autorisation propres à chaque scope; manifests, `run.json`, observables, reçus et rapports restent dans leurs archives respectives. L’approbation family remainder lie explicitement les quatre ledgers prédécesseurs ci-dessus. Le vérificateur a confirmé 9 départs, 9 fins, aucune réservation ouverte et aucune erreur de hash-chain. Les événements et archives R1, R2 et des diagnostics n’ont pas été modifiés.

Aucun retry implicite n’apparaît dans ces scopes : chaque nodeid R1/R2/diagnostic concerné a au plus une réservation dans son ledger, et chaque nodeid famille résiduelle a exactement une tentative. Les tentatives après un `INFRA_ERROR` ou `DIAGNOSTIC_STOP` ont des scopes, contrats, décisions Owner, manifests et ledgers distincts; elles ne remplacent pas les événements antérieurs et ne sont pas agrégées en une campagne homogène.

## 5. Limites et vocabulaire de statut

- `CASE_GATE_PASS` : les portes de cas gelées sont satisfaites pour ce cas et cette identité. Cela ne signifie pas que la convergence de famille ou une qualification générale est acquise.
- `CONVERGENCE_PASS` : les critères inter-niveaux du contrat famille sont satisfaits pour TET10, HEX8 standard et HEX20 dans cette campagne précise.
- `DIAGNOSTIC_UNQUALIFIED` : observables diagnostiques conservées, sans qualification de ces erreurs pour le seuil scientifique de campagne. Cela couvre les erreurs observées pour TET4-L3.
- `DIAGNOSTIC_COMPLETED` / `scientific_state=PASS` : le diagnostic optimisé TET4-L3 a terminé et ses contrôles mécaniques ont passé; cela ne remplace pas le FAIL de précision d’énergie scalaire.
- `GENERAL_SCIENTIFIC_QUALIFICATION` reste `NOT_ACQUIRED`. Ces ordres ne généralisent pas les éléments aux autres géométries, matériaux, formulations, chargements ou routes. Les runs dédiés demeurent liés à leurs sources figées et ne sont pas des réexécutions du HEAD d’intégration ni une preuve de qualification du paquet. Le sous-dossier VV3D ne clôture pas WP12-B, WP12 ni WP13, et ne change aucun autre statut de capacité.

Les détails de conservation et les références des quatre lignes élémentaires concernées dans la matrice des 62 capacités figurent dans [l’audit WP12 des 62 capacités](vv_master_plan/WP12_62_CAPABILITY_AUDIT.md) et [son CSV](vv_master_plan/WP12_62_CAPABILITY_AUDIT.csv). La roadmap garde les statuts WP12/WP13 inchangés.

## 6. Recommandation de clôture bornée

Recommandation : approuver `VV3D_CLOSED_BOUNDED_FOR_0_2_12` uniquement pour le sous-dossier VV3D, avec les preuves, scopes, limites et le FAIL TET4-L3 ci-dessus. Cette recommandation administrative n’est pas une qualification universelle, ne promeut pas les autres capacités et n’altère aucun ledger historique. Elle est en attente de la revue/intégration de cette modification et de la décision Owner exacte suivante :

> **J’approuve le statut `VV3D_CLOSED_BOUNDED_FOR_0_2_12` pour le seul sous-dossier VV3D de QF Solver v0.2.12, selon le rapport intégré `qualification/0_2_12/vv3d_bounded_closeout_0_2_12.md`. Cette clôture conserve le FAIL TET4-L3 sur l’énergie scalaire et ne modifie ni les critères, ni les preuves historiques, ni les statuts WP12-B, WP12 et WP13.**
