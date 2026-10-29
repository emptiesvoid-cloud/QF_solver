# WP12-A — Matrice de disposition release après campagne P0

**État : WP12A_FINAL_RELEASE_DISPOSITION_READY — revue Owner requise.** Mise à jour prospective, sans modifier la matrice ou les statuts scientifiques historiques. La clôture bornée est une proposition, non une décision prise.

## Provenance et vocabulaire

- Référence release `emptiesvoids-cloud/0.2.12` : HEAD `098382938df641751271acb62b7c8e666cfa8e09` ; la documentation ici est proposée au-dessus de cette identité.
- Contrat du lot P0 `59052cf36486a68d7f91f78972d92be3830970bb5384bf59faa108ed60747f9f` ; rapport externe SHA-256 `28c1fbf527ad2c86c211f64070f0eea01c046d26b96e1a93831da5af934c73ee` ; ledger v2 final `8536e68403c12731b6f14562256bd749bda8bc781ba18c165ebe83164c77f09f`.
- P0-1 à P0-6 désignent dans l’ordre les reçus `case-01.json` à `case-06.json` sous `E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\batches\wp12a-p0-batch-20261029-r1\case-receipts`. Les nodeids exacts, SHA-256 et chemins du run, du préflight et des manifestes sont dans le rapport externe.
- H1 WP07 `dev-a3083df78b03`, H2 Newmark `dev-b81ed5a46142`, H3 harmonique réduit `dev-0dd64d435dd1`, H4 base complexe `dev-f5bae47755b8`. Voir [matrice des 31 artefacts et leurs SHA](../../docs/qualification/0_2_12/WP12A_EVIDENCE_MATRIX.md). Les 31 empreintes ont été recalculées sans divergence.
- P0 : six tests PASS, une tentative chacun ; les valeurs de résidus, erreurs, énergies et réponses sont `NOT_EXPOSED`, jamais inférées du PASS. Les résultats H2–H4 ont des sidecars détaillés ; H1 brut est `NOT_EXPOSED`.
- La matrice WP12-62 définit MUST comme **disposition bornée et traçable**, pas comme PASS général. Un résultat ciblé satisfait ses assertions pour son identité ; une disposition release devient applicable seulement après acceptation Owner des limites et des exclusions.

## Les 20 capacités

| Capacité / priorité | Preuves précises | Résultat ciblé et portée | Critère release : proposition, lacune et exclusion |
|---|---|---|---|
| `AN-MODAL` / MUST | P0-1 et P0-2 ; WP04 6/6 historique | PASS ciblé 2 DDL, invariance sous-espace dégénéré ; oracle SciPy/invariants | Disposer borné sous acceptation Owner ; modes et systèmes généraux exclus. |
| `AN-DIRECT-TRANSIENT` / MUST | P0-4 ; Newmark historique H2 | PASS SDOF libre, énergie initiale/finale et résidu ; oracle scalaire conditionnel | Disposer borné ; chargement général, multi-DDL et histoire analytique non démontrés. |
| `AN-DIRECT-HARMONIC` / MUST | P0-5 ; harmonique réduit H3 | PASS SDOF amplitude/phase et DC, plus cohérence base complète/directe | Disposer borné ; amortissements et fréquences générales non démontrés. |
| `AN-PREPARED` / MUST | P0-3 et P0-6 ; WP02 historique | PASS identité opérateurs/excitation et projection Rayleigh | Disposer borné ; mutations physiques et familles générales restent partielles. |
| `AN-EXCITATION` / MUST | H1 et H4 ; P0-6 | PASS harmonique/base complexe borné ; invariance opérateurs en changement excitation | Disposer borné ; multi-support, plusieurs axes et routes import/export non généralisés. |
| `AN-MODAL-BASIS` / MUST | P0-1, P0-2, P0-3 ; WP04 6/6 historique | PASS sur projection, orthogonalité, sous-espace dégénéré et Rayleigh | Disposer borné ; cinq contrôles de symétrie spécifiques et famille WP00 restent à rattacher à une identité pertinente ou limiter la revendication. |
| `AN-REDUCED-HARMONIC` / MUST | H3, sidecar 07493ac9… | PASS ciblé ; écart direct/base complète 2,27963e-16 ; base tronquée résidu physique 1 N | Disposer borné ; résidu modal nul ne garantit pas erreur physique ni borne de troncature. |
| `AN-MODAL-NEWMARK` / MUST | H2, sidecar 91b3ac5c… | PASS ciblé, 34 assertions ; ordres u 1,99724 et 1,99931 | Disposer borné ; cas libre non amorti, résidu modal, checkpoint et travail extérieur non établis ici. |
| `AN-BASE-ACCEL` / SHOULD | H1 et H4 ; sidecar 89174f40… | PASS borné un axe/un DDL, phases, repères et fréquence nulle | SHOULD : limiter à la fixture ; multi-support et cas non exposés exclus. |
| `AN-D01` / SHOULD | Matrice PR #71 ; rapport D01 | INCONCLUSIVE ; C4 NOT_ACQUIRED | SHOULD : préserver, exclure les revendications de qualification D01. |
| `AN-D02` / SHOULD | Matrice PR #71 ; disposition historique D02 | CLOSED_BOUNDED ; payload EXPERIMENTAL/NOT_ASSESSED | SHOULD : conserver domaine linéaire solide accepté ; pas de généralisation. |
| `CON-MPC` / SHOULD | Matrice PR #71 ; refus synthétiques 12 combinaisons à 20cb917f | PARTIAL statique et refus bornés ; support dynamique non démontré | SHOULD : exclure support dynamique non démontré, sans prétendre un refus universel. |
| `CON-RBE2` / SHOULD | Matrice PR #71 ; références de condensation historiques | PARTIAL transversal ; statut statique QUALIFIED_BOUNDED conservé | SHOULD : exclure support dynamique non démontré. |
| `CON-RBE3-RIGID` / SHOULD | Matrice PR #71 ; projection/torseur historiques | PARTIAL transversal ; VERIFIED_BOUNDED/QUALIFIED_BOUNDED statique | SHOULD : exclure dynamique et géométries hors rang contracté. |
| `CON-RBE3-WEIGHTED` / SHOULD | Matrice PR #71 ; extrapolation pondérée historique | PARTIAL ; poids signés ne garantissent pas la conservation générale des moments | SHOULD : limiter au contrat statique testé. |
| `ASM-STATIC` / MUST | P0-3 à P0-6 ; matrice historique et WP02 | PASS de fixtures dynamiques, assemblage partagé ; invariants de préparation | PARTIAL ; ne pas revendiquer contrôle exhaustif assemblage, réactions ou charges de face. Continuité HEX20 distincte. |
| `POST-STRESS` / SHOULD | Matrice PR #71 ; dossier D02 historique | PARTIAL / D02 borné ; aucun nouveau contrôle du champ par P0 | SHOULD : exclure familles et sorties non qualifiées. |
| `API-IO` / MUST | H1, H4 ; WP11 gate et DTO historiques | PASS borné de sérialisation et contrats ; WP07 brut NOT_EXPOSED | PARTIAL ; borner formats/routes, préserver la non-régression de WP11 sans généraliser. |
| `API-CLI` / MUST | WP11 gate et tests historiques cités dans matrice PR #71 | Preuves de contrat et dispatch historiques, aucune nouvelle exécution P0 | PARTIAL ; borner les routes annoncées ou fournir la preuve de continuité/dispatch pertinente. |
| `IO-HDF5` / DEFERRED | Matrice PR #71 ; contrat HDF5 expérimental | NOT_TESTED/DEFERRED pour le scope courant | DEFERRED : aucune revendication de robustesse, crash-safety ou compatibilité générale. |

## Identité et continuité

Les six résultats P0 sont liés au HEAD scientifique `7406e34efc28ed8f18c15440115595dfa3dd9ca5` et non au HEAD release. Les quatre résultats antérieurs utilisent respectivement `630d22b…`, `5f96dd6…`, `bf88803…`, `7406e34…`. Un diff Git de chacun vers la release ne montre qu’un fichier modifié sous `src/solveur` : `src/solveur/loads/integration.py`, concernant la quadrature des faces QUAD8/HEX20 ; cela n’établit pas à lui seul une équivalence complète de dépendances. Les fixtures ciblées sont petites BEAM2/TET4 ou matrices fixes ; ne pas transférer automatiquement leur identité au candidat release ni inférer un verdict HEX20. Les fichiers des six tests P0 et `tests/conftest.py`, `tests/unit/conftest.py` sont identiques entre `7406e34…` et la release examinée.

La définition WP12-0 demande des contrôles MUST sur une identité propre, un traitement explicite des lacunes, la non-régression des dépendances touchées et une revue Owner. La clôture de **WP12 global** conserve aussi son propre bilan de performance et ses autres gates. Aucun contrôle produit ici ne remplace ces exigences par un PASS automatique.

## Anomalies et dispositions conservées

- Newmark : un ancien échec scientifique `dev-a81c2f0d9e74` et le writer `dev-301ba3b31a43` en `PYTEST_FAILED`, tentative consommée et verdict mécanique non établi. Les PASS ultérieurs ne les effacent pas.
- WP07 : ancien échec round-trip préservé ; PASS ciblé ultérieur avec données brutes absentes.
- D01 `INCONCLUSIVE`, C4 `NOT_ACQUIRED` ; D02 `CLOSED_BOUNDED` ; C01 `CLOSED_NEGATIVE`, E01 `OPEN_WITH_BOUNDED_CERTIFICATES`. Les échecs HEX8-SRI `CLOSED_NEGATIVE` restent hors du chantier A.
- Aucun résultat A ne démontre une validation physique générale, des modèles grands ou non linéaires, ou une qualification FEM générale. La corrélation physique externe n’est pas un prérequis ajouté automatiquement à la release alpha.

## Décision proposée et contrôles réellement conditionnels

Une clôture **bornée** des 20 dispositions peut être soumise à l’Owner : accepter les 11 MUST dans les limites ci-dessus, y compris les statuts PARTIAL et l’identité des sources, et garder les huit SHOULD et le DEFERRED dans leurs statuts historiques. Cela ne vaut ni PASS général de ces capacités ni décision sur WP12/WP13 ou la publication. La décision complète figure dans [le projet de décision](WP12A_P0_RELEASE_DISPOSITION_DECISION.md).

Sans cette acceptation, la clôture globale WP12-A reste `PARTIALLY_CLOSED`. Si la release revendique une couverture plus large que les bornes proposées, les seuls contrôles indispensables sont ceux correspondant à la revendication : continuité de l’intégration des charges de face modifiées ; projection symétrique/refus et famille WP00 si revendiqués ; dispatch API/CLI et IO dynamiques si leurs routes sont revendiquées. Des preuves existantes valides peuvent suffire ; toute nouvelle exécution scientifique exige sa décision et son manifeste propres. Ne pas relancer les dix expériences pour augmenter le nombre de PASS.
