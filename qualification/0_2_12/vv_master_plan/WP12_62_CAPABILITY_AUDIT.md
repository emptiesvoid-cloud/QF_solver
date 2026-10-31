# WP12 — Audit de couverture des 62 capacités

**Révision :** 2026-10-31
**État :** audit des 62 capacités conservé; WP12-B `WP12B_CLOSED_BOUNDED_FOR_0_2_12`; WP12=OPEN en attente de décision globale
**HEAD historique de l’audit statique (2026-10-26) :** cbdd54aadbb640a96c6b6b5b9726e1247da36012
**HEAD release examiné pour le closeout documentaire :** ee50684d3c146102b773f604e1625ba8c07348ca; aucune preuve scientifique n’est présentée comme un replay de ce HEAD.
**HEAD release après la confirmation Owner WP12-B :** 09f0810a39f9712044450c527d7613518d6bcea6 (PR #111, documentation seulement; aucun résultat scientifique exécuté sur ce HEAD).
**Exécution pour ce closeout :** aucune FEM, aucun solveur ni benchmark. Deux tests synthétiques du contrôleur R2 ont passé dans le worktree `wp12b-vv3d-bounded-closeout-20261031`; ils utilisent des fichiers temporaires et ne constituent pas une exécution scientifique ni une validation complète du parcours CLI R2.

Le fichier [WP12_62_CAPABILITY_AUDIT.csv](WP12_62_CAPABILITY_AUDIT.csv) reprend les 62 identifiants de [CAPABILITY_TEST_MATRIX.csv](CAPABILITY_TEST_MATRIX.csv), sans modifier cette matrice de planification. Il ajoute, par capacité, l’état observé sur le HEAD d’intégration, les résultats récents associés à d’autres identités de source, une lecture des oracles, un risque de régression, une priorité proposée et un chantier WP12 responsable.

## Méthode et portée

- Les 62 lignes sont reprises une à une depuis la matrice source. Les chemins de tests cités par cette matrice existent dans le checkout d’intégration. Les fonctions citées ont été vérifiées par lecture syntaxique de leurs sources; cette vérification n’a pas collecté ni exécuté pytest.
- La colonne audited_nodeids_exact contient des nodeids vérifiés par inspection statique ou explicitement issus d’un manifeste historique. Une fonction paramétrée exige son suffixe pytest exact. La colonne nodeid_static_audit_note distingue les sélecteurs statiques des sélecteurs historiques et signale les limites. Pour C02, les M4/M5 exacts restent liés à N10; l’helper AJ requis est absent du checkout propre et aucun essai n’est exécutable sans overlay approuvé. Les tests auxiliaires ne les remplacent pas.
- Le « dernier élément de preuve » reprend les rapports, contrats et identités cités dans la matrice source. Plusieurs lignes ne donnent qu’une identité par rapport ou par cas. L’audit n’invente donc ni un SHA manquant, ni le premier numéro de version d’introduction. La colonne origin_version_scope_audit indique ce qui est explicitement démontré et ce qui reste à vérifier dans le contrat d’origine.
- Les tags d’oracle A–E viennent du plan : A algébrique/invariant/refus; B analytique; C discrétisation/convergence; D comparaison avec un code indépendant; E robustesse/refus. La présence d’un tag, d’un test ou d’un rapport n’établit pas à elle seule que l’oracle a été acquis, est indépendant ou couvre toutes les routes.
- Aucune exécution récente décrite ci-dessous n’est une exécution sur le HEAD d’intégration cbdd54a. La colonne integration_head_execution le marque NOT_RUN_EVIDENCED pour les 62 lignes. Il s’agit de preuves de développement liées à d’autres identités, pas de preuves de non-régression du candidat intégré.
- Les comptes d’exécutions de campagnes qui couvrent plusieurs capacités ne sont pas additionnés par ligne et ne doivent pas être totalisés comme des tests indépendants.

## Priorités de release proposées

La priorité source de la matrice est traduite de manière déterministe : **17 MUST** (P0), **39 SHOULD** (P1), **6 DEFERRED** (P2). Ces choix ordonnent la couverture de release; ils ne créent ni seuil scientifique, ni autorisation, ni maturité. MUST signifie qu’une capacité centrale annoncée doit recevoir une disposition bornée et traçable. Un résultat FAIL, INCONCLUSIVE ou NOT_ACQUIRED conservé avec ses limites peut satisfaire la traçabilité attendue; il ne devient pas un PASS.

Chaque ligne donne également une justification appliquée à sa priorité source. La campagne assignée est un propriétaire de préparation : WP12-A méthodes partagées, dynamique, contraintes et interfaces; WP12-B éléments, matériaux linéaires compatibles, charges et maillages; WP12-C non-linéaire et contact; WP12-D rotordynamique, solveurs et performances; WP12-E corrélation externe; WP12-F outils de preuve et consolidation. Ces étiquettes A–F sont des chantiers internes de WP12, pas de nouveaux WP officiels.

## Résultats récents à préserver

### TET4, TET10 et HEX8 standard

Le rapport tet4/fem-cases-wp12-v1/analysis-20261026-v1/report.md (SHA-256 D06D8E8F4F2D7A5DFFEB850BCFB08DDC1353C4556FA096F1C728F5882646FBF0) enregistre six tentatives autorisées, chacune à un cas, toutes PASS sur la source 619fddd97d56936ca3333cbeca9e7ae46dbd6a8e. Il couvre quatre raffinements TET4, une comparaison TET10 et une comparaison HEX8 standard. Les nodeids exacts sont consignés dans la matrice et le rapport.

Pour TET4, les incréments relatifs successifs de la norme du déplacement moyen de face décroissent de 175,3 % à 90,8 % puis 31,7 %; la norme augmente encore entre chaque niveau et le niveau le plus fin reste à 11,75 % du diagnostic de poutre 1D non équivalent. Les contrôles de résidu, de réactions, de moments et d’énergie passent sur ces fixtures, mais aucun ordre asymptotique ni validation 3D n’est établi. TET10 et HEX8 n’ont chacun qu’un point de comparaison à facteur 4. Il s’agit de résultats de développement externes au HEAD intégré, sans conclusion générale par élément.

### Clôture bornée VV3D — disposition Owner approuvée, limitée à VV3D (2026-10-31)

Le rapport [VV3D bounded closeout v0.2.12](../vv3d_bounded_closeout_0_2_12.md) consolide les douze niveaux avec cinq ledgers distincts et leurs contrats, décisions et empreintes. Seules les lignes `EL-TET4`, `EL-TET10`, `EL-HEX8` et `EL-HEX20` de la matrice CSV référencent cette preuve. Les neuf cas TET10/HEX8/HEX20 sont `CASE_GATE_PASS`; leurs évaluations inter-niveaux sont `CONVERGENCE_PASS` sous le contrat famille exact. TET4-L1/L2 restent les `PASS` de R2; les ordres obtenus à partir des niveaux conservés sont descriptifs, car L3 provient d’un diagnostic séparé.

TET4-L3 demeure `DIAGNOSTIC_COMPLETED` avec contrôles mécaniques `PASS`, mais l’erreur relative d’énergie scalaire `0.0615360686 > 0.05` reste `FAIL`. La précision demandée n’est pas atteinte. Aucun ledger n’est réécrit ou combiné en campagne homogène. L’Owner a explicitement approuvé la disposition `VV3D_CLOSED_BOUNDED_FOR_0_2_12` le 2026-10-31; cette décision est intégrée par la PR #110 au HEAD release `ee50684`. Elle ne promeut pas d’autres capacités et ne change pas WP12-B, WP12 ou WP13.

### WP12-B — clôture bornée confirmée par l’Owner (2026-10-31)

L’Owner a confirmé `WP12B_CLOSED_BOUNDED_FOR_0_2_12` le 2026-10-31 après l’intégration documentaire de la PR #111 au commit `09f0810a39f9712044450c527d7613518d6bcea6`. La décision est archivée dans [WP12B_OWNER_BOUNDED_CLOSURE_DECISION_20261031.md](../WP12B_OWNER_BOUNDED_CLOSURE_DECISION_20261031.md). Elle accepte les dispositions bornées des six MUST, dont le FAIL énergétique TET4-L3 et les statuts HEX8-SRI/HEX20 `NOT_ACQUIRED` décrits dans le [dossier WP12-B](../wp12b_bounded_closeout_0_2_12.md).

Le rapport [WP12-B bounded closeout v0.2.12](../wp12b_bounded_closeout_0_2_12.md) porte les familles et chargements retenus, les six MUST, les résultats, les limites et les revendications autorisées. Il distingue les résultats liés à leurs sources des preuves sur le HEAD release actuel `09f0810` : aucune campagne scientifique n’est déclarée exécutée sur ce HEAD.

| MUST WP12-B | Disposition bornée retenue |
|---|---|
| `EL-TET4` | Résultats bornés conservés; pas de `CONVERGENCE_PASS`; FAIL énergétique TET4-L3 conservé. |
| `EL-TET10` | `CONVERGENCE_PASS` uniquement sous le contrat VV3D; pression R4 bornée distincte. |
| `MAT-ELASTIC` | Routes linéaires isotropes compatibles et déclarées seulement; pas de produit cartésien qualifié. |
| `AN-STATIC` | Cas statiques bornés; pas de certificat statique général. |
| `LOADS-REACTIONS` | Résultantes, moments et réactions documentés pour Beam2/TET10; HEX20 QUAD8 corrigé reste `NOT_ACQUIRED` en FEM. |
| `MESH-QUALITY` | Contrôles limités aux contrats et maillages identifiés; pas de garantie de précision de solution. |

La correction HEX8-SRI et la correction QUAD8 HEX20 sont intégrées, mais leur validation mécanique globale post-correction reste `NOT_ACQUIRED`. Les FAIL HEX8-SRI et HEX20 R4 sont conservés. Les certificats historiques MITC3/MITC4 et WEDGE6 restent dans leurs seuls scopes enregistrés; les extensions sont EXPERIMENTAL, DEFERRED ou NOT_ACQUIRED selon le registre. MPC/RBE demeure assigné à WP12-A.

WP12-B est clos dans le périmètre accepté. WP12 et WP13 restent ouverts; cette décision ne confère aucune qualification générale ni autorisation de publication. La consolidation WP12-F et la préparation de la décision globale sont référencées dans [WP12F_FINAL_VV_CONSOLIDATION_AND_GLOBAL_DECISION.md](../vv_local/WP12F_FINAL_VV_CONSOLIDATION_AND_GLOBAL_DECISION.md).

### HEX8-SRI

Les deux diagnostics test_wp12_hex8_sri_near_incompressible_nu04999_nx16 et test_wp12_hex8_sri_near_degenerate_nu0495_nx4 restent `PYTEST_FAILED / CLOSED_NEGATIVE`; ils ne sont ni remplacés ni attribués au seul défaut de poids volumique. Le correctif de formulation #91 est intégré au release par le commit `326b357fe752b33bb034c46ed546973abb1d2cb0`, ancêtre du HEAD actuel `09f0810`; ses huit tests d’élément sont rapportés PASS, sans assemblage ni résolution globale. La validation mécanique globale post-correction demeure `NOT_ACQUIRED`, HEX8-SRI reste `EXPERIMENTAL`, et la proposition 8×4×4 reste non gelée et non exécutée.

### Dynamique et harmonique

Le rapport DYNAMIC_HARMONIC_RESULTS_REPORT.md est disponible sur la branche scientifique codex/wp12-dynamic-harmonic-verification, chemin qualification/0_2_12/vv_local/wp12_dynamics/DYNAMIC_HARMONIC_RESULTS_REPORT.md, au HEAD 630d22b7667a0d84dd7b136b9f8c7d89ae00fc66. Son SHA-256 est FF3DC97B0F7FBF90695B8EEC9705BC309AE10B2CE3FC733AFF2B26228EC3FE3D; les trois calculs utilisent la source d9deddbd6b42467c5fdc9e278bd54e97605f5738. Le rapport n’est pas présent dans le checkout d’intégration audité. Tous trois sont des DEVELOPMENT_PASS_BOUNDED :

- **Newmark modal, un DDL axial BEAM2 SDOF :** les ordres observés avec trois pas de temps sont proches de 2 pour déplacement, vitesse et accélération. Les critères déjà présents sur déplacement, résidu et énergie passent. Les ordres vitesse/accélération sont descriptifs; ils n’ajoutent aucun critère accepté.
- **Harmonique réduit :** la base complète concorde avec la route directe à environ 2,28×10⁻¹⁶ d’erreur vectorielle relative sur six fréquences. Les deux routes partagent les opérateurs assemblés; cette comparaison établit une cohérence de route, pas un oracle physique indépendant. La troncature à deux modes donne une réponse nulle à la sonde sur cette fixture, soit 100 % d’erreur de réponse, sans établir de borne ROM générale.
- **Accélération uniforme de base :** les signes, phases, relations cinématiques, repères et le round-trip de sérialisation sont cohérents pour un axe et une coordonnée libre. À DC, les grandeurs absolues indisponibles restent null; le cas ne couvre ni les supports multiples ni une validation physique générale.

Ces trois tests n’ont pas été exécutés sur le HEAD intégré audité. Leur rapport conserve nodeids, SHA des manifestes, reçus et sidecars. Ils ne clôturent pas WP05, WP06, WP07 ou WP12.

## Décisions et manques saillants

- La matrice montre quels chemins sont intégrés, mais la compatibilité élément × matériau × analyse reste propre à chaque descripteur et route. Aucun produit cartésien de capacités n’est présumé.
- La chaîne dynamique partage des opérateurs, des projections et des contrats de résultats. Les trois nouveaux PASS bornés ne rejouent pas les tests de projection WP04 après changement de projection symétrique.
- Les preuves rotor v0.2.11 GYRO-01 à GYRO-06 restent historiques et EXPERIMENTAL, y compris l’ambiguïté Campbell à 100 rad/s. Aucun PASS rotor n’est revendiqué sur l’intégration actuelle.
- C01 reste négatif avec remédiation ouverte; C02 reste borné à AR/N03; D01 demeure INCONCLUSIVE; D02 reste CLOSED_BOUNDED; E01 reste OPEN_WITH_BOUNDED_CERTIFICATES. Aucun de ces statuts n’est modifié par le présent inventaire.
- Les corrélations Code_Aster/CalculiX doivent faire correspondre formulation, éléments, quadrature, charges, contraintes et observables. Elles ne remplacent pas une validation physique; le portefeuille indépendant plus large reste reportable à v0.3.0.

## Décision de gouvernance

L’audit statique du 2026-10-26 recommandait de garder WP12 OPEN. Le 2026-10-31, l’Owner a confirmé la clôture bornée de WP12-B après intégration du dossier; le sous-chantier WP12-B est désormais `WP12B_CLOSED_BOUNDED_FOR_0_2_12`. WP12 et WP13 restent OPEN dans l’attente de leurs décisions propres. WP12-F prépare la recommandation globale sans promouvoir de preuve ni rouvrir WP12-A, WP11, D01 ou E01. Toute campagne ultérieure exige ses propres manifestes, identités et décisions Owner. Les résultats anciens, les FAIL, les INCONCLUSIVE et les limites restent intacts.
