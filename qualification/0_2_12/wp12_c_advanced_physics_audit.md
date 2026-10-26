# QF Solver WP12-C — Audit des capacités non linéaires et du contact

**Date :** 2026-10-26
**Branche :** `audit/wp12-advanced-physics`
**HEAD audité :** `cbdd54aadbb640a96c6b6b5b9726e1247da36012` (base `origin/emptiesvoids-cloud/0.2.12`)
**Nature :** audit documentaire et statique du code, des rapports et des preuves déjà archivées.

## Périmètre

Les preuves antérieures restent liées à leurs branches, commits, manifests et fixtures. Elles ne sont pas présentées comme des exécutions de ce HEAD. Le checkout principal avait des changements locaux et dossiers non suivis; ils n’ont pas été importés ni modifiés.

Aucun test, calcul FEM, calcul de contact, solveur, benchmark ou génération de maillage n’a été lancé pour cet audit. Aucun seuil, contrat, rapport d’exécution ou verdict historique n’a été modifié. Les cinq niveaux sont séparés : **(1)** matériau au point de Gauss, **(2)** noyau élémentaire, **(3)** assemblage global, **(4)** méthode Newton/résolution, **(5)** vérification structurelle indépendante. Une preuve à un niveau ne vaut pas automatiquement pour les suivants.

## Synthèse

- L’état normatif v0.2.12 classe WP08–WP10 `CLOSED_BOUNDED`, sans qualification non linéaire générale. La voie J2 corotationnelle corrigée est `EXPERIMENTAL` et opt-in; la voie legacy reste le défaut en l’absence de choix explicite.
- Le retour radial J2 petites déformations et sa tangente algorithmique existent au point de Gauss. Cela ne valide pas la tangente globale sur tous les DDL libres ni son comportement aux transitions de branche.
- La voie TL utilise `F`, Green–Lagrange `E`, PK2 `S`, puis `P=FS`. Cela ne constitue pas une plasticité J2 multiplicative à déformations finies. Les défauts de conjugaison/transport WP08 concernent l’ancienne voie corotationnelle; la formulation Biot corrigée est distincte.
- WP-C01 reste `CLOSED_NEGATIVE`, remédiation `OPEN`. Le rejeu hors FEM et la preuve B* bornée ne remplacent ni les échecs historiques ni les preuves manquantes de tangente de glissement, glissement fini et convergence spatiale.
- WP-C02 est `CLOSED_BOUNDED` uniquement pour AR/N03. C01 et C02 partagent les opérateurs/solveurs de `contact/`; leurs certificats ne se substituent pas l’un à l’autre.
- WP-E01 est `OPEN_WITH_BOUNDED_CERTIFICATES`. Hencky possède des preuves matériau, tangent, élément et assemblage bornées; son Newton isolé conserve 3 FAIL. La tangente globale J2 n’est pas acquise, le résultat global BA reste `FAIL` et l’équilibre maître-montage `NOT_VERIFIED`.
- WP-D01 reste `INCONCLUSIVE`. Le port de projection Rayleigh est prêt/intégré, mais C4 n’est pas acquis et la qualification FEM WP05 n’est pas évaluée.

## Registre des preuves

| ID | Sources | Preuve observée | Portée et limite |
|---|---|---|---|
| E-00 | [Roadmap d’intégration](ROADMAP.md) | WP08–WP10 `CLOSED_BOUNDED`; C01 `CLOSED_NEGATIVE`; C02 borné AR/N03; D01 inconclusif; E01 ouvert; WP12/WP13 ouverts. | État portefeuille, pas qualification générale ni résultat d’exécution unique. |
| E-08 | [Faisabilité WP08](wp08_constitutive_feasibility_report.md), [R2](wp08_r2_implementation_report.md), [force](wp08_r2_internal_force_vnv.md), [R3](wp08_r3_newton_convergence_report.md) | La route legacy a des défauts démontrés sur certains historiques plastiques non coaxiaux : `P=R T_local` n’est pas l’adjoint polaire exact; le transport d’état change l’histoire sous rotation pure. La route `corrected_corotational_biot_j2/v1` corrige force/sémantique sur ses cas bornés. | Les statuts `BLOCKED` du diagnostic restent historiques; ils ne condamnent pas tout J2. R3 valide des fixtures TET4 ciblées, non une convergence générale. |
| E-09/10 | [WP09 tangent](wp09_tangent_robustness_report.md), [Newton](wp09_newton_robustness_report.md), [convergence WP10](wp10_convergence_criteria_report.md), [états/checkpoints](wp10_nonlinear_state_checkpoint_report.md) | WP09 : 39 tests ciblés et robustesse bornée; WP10 : transactions, commit/rollback, checkpoints et vérité des statuts bornés. | Tangente corrigée par défaut : différence centrée, coût `2*n_dof+1`; à une transition de branche ce n’est pas une dérivée classique. Pas de garantie Newton générale. WP10 garde un critère avec plancher unitaire dépendant des unités. |
| E-GEO | [Contrat des contraintes](wp08_nonlinear_stress_measures_contract.json), [élément TL](../../src/solveur/elements/solid/total_lagrangian_j2.py), [assemblage géométrique](../../src/solveur/core/assembly/geometric.py) | Le code calcule `F=I+grad_X(u)`, `E=(F^TF-I)/2`, réponse J2, `S`, `P=FS`; le tangent comporte termes matériel et géométrique. | Le matériau reste J2 petites déformations, sans `F=FeFp`. TL, StVK, Hencky et Néo-Hookéen restent bornés/recherche selon le sous-module. |
| E-C01 | [R14](wp_c01_r14_bstar_slip_exploratory_report.md), [R17](wp_c01_r17_archive_replay.md), [R18](wp_c01_r18_independent_review.md), [registre R19](wp_c01_r19_status_register.json) | Le `B_STAR_SLIP_FAILED` initial et le FAIL FEM-smoke R16 sont conservés. R17/R18 vérifient hors FEM les archives, 106 événements et un bilan de moment indépendant. R19 garde B* `EXPERIMENTAL_BOUNDED`. | Une paire/triangle figés, petites rotations, opt-in; pas de seuil angulaire runtime. Tangente globale en slip, finite sliding et convergence spatiale `NOT_ACQUIRED`. Le rejeu ne remplace pas le RUN R16. |
| E-C02 | [Décision N13](wp_c02_n13_owner_bounded_closure_decision.md), [évaluation N12](wp_c02_n12_scientific_qualification_assessment.md), [rapport consolidé](wp_c02_unified_contact_vnv_report.md) | Clôture approuvée seulement pour AR/N03 : TET4, élasticité linéaire, contact normal frictionless, face plane figée, M1–M5. Référence indépendante de raideur/scatter, KKT et critères analytiques archivés. | Pas de convergence asymptotique; front à `1hx` sans marge; réactions de support issues du résidu, pas d’un oracle indépendant. N06/N08 et Docker FAIL préservés. |
| E-E01-M | [Audit BB](wp_e01_bb_global_scientific_audit_and_closure_readiness.md), [P3](wp_e01_p3_hencky_verification_2026-10-21.md), [S](wp_e01_s_hencky_tangent_verification_2026-10-21.md), [T](wp_e01_t_hencky_element_tangent_verification_2026-10-21.md) | Hencky matériau P3 41/41, tangente matériau S 35/35, tangente élément TET4/HEX8 T 34/34, chacun borné à ses cas. | Direct-import expérimental, non enregistré dans la fabrique publique. S ne démontre pas de plateau robuste; N historique 35/36 avec un FAIL reste préservé. |
| E-E01-U/V | [Rapport U/V/W](wp_e01_uvw_consolidated_report_2026-10-21.md) | Adaptateur isolé : assemblage U 31/31; Newton V 13 PASS / 3 FAIL. | Pas de dispatch public. Deux FAIL V concernent les identités exactes malgré déplacements sous tolérance; le cas d’équilibre initial applique une charge à facteur nul. Aucun rejet physique suivi d’une acceptation réduite. Le résumé `NOT_RUN` erroné est aussi conservé. |
| E-E01-J2/BA | [Faisabilité tangent global](wp_e01_j2_global_tangent_feasibility_2026-10-24.md), [audit BB](wp_e01_bb_global_scientific_audit_and_closure_readiness.md) | D4R : 65 PASS élémentaires historiques; F3 : 14/20 PASS, 6 FAIL; H : 16/20 PASS, 4 FAIL; K : 12/12 sur identité/translation. BA certifie seulement un sous-système esclave GF4/TET4. | Tangente assemblée `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; L préparé, non exécuté; directions faibles 6,74–11,03 % non résolues. BA global brut `FAIL`, maître-montage `NOT_VERIFIED`, qualification générale `NOT_ACQUIRED`. |
| E-D01 | [Récupération](wp_d01_capability_recovery_report.md), [projection stable](wp_d01_stable_projection_integration_report.md), [réconciliation](wp_d01_git_reconciliation_report.md) | `rayleigh_structured` opt-in pour `C=alpha*M+beta*K` vérifié; `legacy_direct` reste par défaut. Relecture des opérandes M3 et essais algébriques, sans FEM. | `WP_D01_STATUS=INCONCLUSIVE`, `C4=NOT_ACQUIRED`, `WP05_FEM_QUALIFICATION=NOT_EVALUATED`; preuves natives M1/M2/M3 sur identité finale manquantes. |

## Matrice par niveau

| Capacité | (1) Point matériel | (2) Noyau élémentaire | (3) Assemblage global | (4) Newton/résolution | (5) Vérification structurelle indépendante |
|---|---|---|---|---|---|
| J2, WP08–10 | Retour radial von Mises et tangente algorithmique locale; plasticité parfaite ou écrouissage isotrope linéaire. | TL et corotationnel sur familles nommées; corrigé borné, legacy garde ses défauts non coaxiaux. | Fixtures WP08-R3 ciblées; écarts d’action tangentielle E01 encore ouverts. | Full Newton, line-search, cutback et reprise réussis pour fixtures WP08-R3 seulement. | Potentiel/force et invariants sur cas bornés; pas de qualification générale; G03 historique FAIL. |
| Géométrie TL / finite strain | `E` est objectif; réponse J2 reste petites déformations, non multiplicative. | `P=FS`, termes matériel/géométrique présents. | Scatter/réduction présents; preuve indépendante complète non acquise. | Dépend du tangent existant; aucune garantie générale. | Études bornées; aucune validité sur déformations arbitraires établie. |
| WP-C01 B* | Élasticité linéaire de la fixture. | Transfert B*, une paire/triangle, petites rotations. | R16 intégré avec FAIL historique; R17/R18 hors FEM. | Active-set/racine bornés; tangent global en slip non acquis. | Bilan indépendant d’une fixture; pas de convergence spatiale générale. |
| WP-C02 AR/N03 | Élasticité linéaire. | Signorini normal, face rigide figée. | TET4 M1–M5, scatter indépendant; réactions dérivées du résidu. | Active-set/KKT; pas Newton non linéaire général. | Critères analytiques bornés; pas d’oracle réaction/asymptotique. |
| WP-E01 Hencky | P3/S point et action tangentielle bornés. | T tangent TET4/HEX8 borné. | U assemblage mémoire isolé. | V 13/16, échecs conservés; pas voie publique. | Références affines/bilans de fixtures, sans qualification générale. |
| WP-E01 J2/BA | Tangente point sur branche lisse; D5 indépendant bloqué. | D4R PASS historiques; directions E01-J ouvertes. | Tangente J2 non résolue; certificat BA esclave seulement. | Newton global non acquis; BA brut FAIL et maître NOT_VERIFIED. | Base libre complète, oracle maître/support et budget d’erreur manquants. |
| WP-D01 | Sans objet. | Sans objet. | M3 archivé relu, aucun assemblage nouveau. | Solveur harmonique réduit/direct, pas Newton non linéaire. | C4/WP05 FEM non évalués. |

## Anomalies, hypothèses et protocoles futurs

Ces protocoles sont des propositions non exécutées; ils demanderaient un mandat scientifique distinct.

### A1 — Route corotationnelle J2 legacy

**Constat :** WP08 rapporte qu’après préchargement plastique une rotation pure laisse `U` invariant mais modifie l’état transporté; `P=R T_local` omet l’adjoint polaire exact hors cas coaxiaux. Cette voie reste le défaut `legacy_corotational_j2/v1`; elle n’est pas la formulation corrigée.

**Hypothèse falsifiable :** à état accepté non nul, legacy ne conserve pas le scalaire plastique et ne respecte pas `P2=Q P1` pour `F2=QF1`, `U2=U1`.

**Protocole :** figer formulation, source et fixture TET4; plastifier, sauvegarder l’état, appliquer une rotation pure; comparer `U`, eqp, déformation plastique, `P`, `F^-1P`, skew Cauchy et moment à une dérivation polaire indépendante. Refaire séparément sur la voie Biot corrigée; garder les preuves distinctes.

### A2 — Tangente J2 globale et option polaire analytique

**Constat :** E01-J ne ferme pas l’action de tangent sur l’espace libre. Le code expose `j2_corotational_tangent="analytic_experimental"`, mais les documents normatifs gardent la tangente assemblée non résolue. Code ou test présent ne signifie pas test exécuté ou qualification.

**Hypothèse falsifiable :** sur branche plastique lisse à histoire fixée, l’action analytique suit la dérivée indépendante sur directions libres; près de la surface de charge, la transition interdit une affirmation de dérivée classique.

**Protocole :** lier source/tests à un HEAD exact; commencer sans solveur avec TET4 et la base libre complète, puis étendre aux familles prévues; vérifier état inchangé, force, branches et balayage de pas avec oracle indépendant; comparer l’assemblage à un scatter indépendant. Toute validation Newton/réaction/convergence de maillage est distincte.

### A3 — Certificat contact C02

**Constat :** N13 ferme AR/N03 au critère existant; front `1hx` sans marge, réactions issues du résidu et pas de convergence asymptotique.

**Hypothèse falsifiable :** le PASS borné du front n’implique pas la convergence de la force, ni un contact mobile/distribué.

**Protocole :** avec critères préapprouvés, comparer une famille géométrique cohérente à une réaction indépendante; publier front, résultantes, bilans, qualité maillage et tendance en `h`. Ne pas changer N03 ni reclasser l’archive.

### A4 — Newton Hencky isolé V

**Constat :** les 3 FAIL V restent conservés; deux portent sur les identités exactes malgré des déplacements sous tolérance, et le cas d’équilibre initial utilise un facteur de charge nul. Le RUN est effectif même si un résumé disait `NOT_RUN`.

**Hypothèse falsifiable :** les échecs sont principalement des critères/fixtures inadéquats, mais ne démontrent pas encore un rejet physique suivi d’un pas réduit accepté.

**Protocole :** sous nouvelle identité/autorisation, utiliser un oracle déplacement/résidu préétabli, une charge initiale non nulle et une trajectoire physique avec rejet puis pas réduit accepté; préserver le résultat 13/16 original.

### A5 — Dépendance partagée C01/C02

**Constat :** `contact/support.py`, `contact/solver.py`, `contact/entities.py` et `contact/evaluation.py` servent les chemins normal/frictionnel; C01 ajoute un transfert tangentiel opt-in, C02-AR exerce le normal sans frottement. Les certificats sont liés à des identités différentes.

**Hypothèse falsifiable :** une modification des opérateurs/dispatch communs pourrait affecter AR même sans B*.

**Protocole :** après tout changement de ces modules, comparer séparément les fixtures C01 B* et C02-AR : configuration, opérateurs, active set, déplacements, pressions, KKT, bilans et hashes. Ne pas promouvoir un cas par l’autre.

## Risques et priorités

| Priorité | Risque | Remédiation à considérer dans un mandat séparé |
|---|---|---|
| P1 | Route legacy corotationnelle encore défaut malgré anomalies WP08 sur certains historiques. | Documenter le domaine et décider de l’accessibilité pour plastique non coaxial; ne pas réinterpréter les résultats legacy. |
| P1 | Tangente J2 sur DDL libres non acquise; option analytique encore expérimentale. | Geler identité et obtenir l’oracle indépendant point/élément/assemblage avant tout claim Newton; ne pas réutiliser WP09 comme seuil général. |
| P1 | Certificat BA esclave confondu avec PASS global. | Garder ensemble : certificat esclave borné PASS, verdict brut global FAIL/WARNING, maître-montage NOT_VERIFIED. |
| P2 | C01 sans tangent slip, finite sliding ni convergence spatiale. | Conserver fermeture négative; qualifier les extensions séparément. |
| P2 | C02-AR sans marge au front ni réaction indépendante/asymptotique. | Conserver certificat borné; préparer extensions avec critères préenregistrés. |
| P2 | D01 prêt côté code, preuve native non acquise sur l’identité finale. | Garder inconclusif; rebind scope/ledger et obtenir une décision avant exécution. |
| P3 | Newton V et résumé superviseur ont des défauts de critères/compte-rendu. | Corriger sous nouvelle identité; conserver 13/16 FAIL et ne réexécuter que sous autorisation. |

## Capacités v0.2.12 et statuts recommandés

Les documents v0.2.12 demandent de conserver les routes existantes et leurs fermetures bornées avec statut explicite. Le roadmap Owner place E01 comme cible expérimentale; l’overlay d’intégration indique qu’E01 n’est pas une gate autonome de publication. WP12/WP13 restent ouverts.

| Capacité | Recommandation |
|---|---|
| J2 petites déformations au point de Gauss / retour radial | Conserver les preuves bornées matériau; séparer tangent local et affirmation globale. |
| WP08–WP10 | `CLOSED_BOUNDED` seulement pour critères/fixtures historiques. Route corrigée `EXPERIMENTAL`; legacy ne reçoit pas son verdict. |
| TL J2, StVK, Néo-Hookéen, Hencky, grandes déformations | `EXPERIMENTAL`/`RESEARCH`; J2 multiplicatif `F=FeFp` : `NOT_IMPLEMENTED` dans le périmètre consulté. |
| Tangente J2 globale / Newton général | E01-J `BLOCKED_PENDING_INDEPENDENT_EVIDENCE` / `NOT_ACQUIRED`; Newton WP08-R3 borné, pas de claim semi-smooth général. |
| Contact B* frictionnel | C01 `CLOSED_NEGATIVE`, remédiation `OPEN`; B* `EXPERIMENTAL_BOUNDED`. |
| Contact normal | C02 `CLOSED_BOUNDED` pour AR/N03 seulement; contact général `NOT_ACQUIRED`. |
| Hencky matériau/tangent/élément/assemblage | `VERIFIED_BOUNDED` pour P3/S/T/U; toujours expérimental et non public. |
| Newton Hencky isolé | `PARTIAL`, 13 PASS / 3 FAIL; aucune promotion au Newton public. |
| WP-E01 global | `OPEN_WITH_BOUNDED_CERTIFICATES`; qualification générale `NOT_ACQUIRED`. |
| WP-D01 | `INCONCLUSIVE`; C4 non acquis, WP05 FEM non évalué. |

## Références de code examinées

## Vérification des statuts historiques

Les constats ci-dessous sont une vérification documentaire du registre et des rapports référencés. Aucun archive, résumé de qualification ou statut source n’a été réécrit par cet audit.

| Dossier | Statuts historiques conservés | Portée de la conservation |
|---|---|---|
| WP08 / WP10 | G03 `FAIL`; WP14 `HOLD_NOT_PROMOTED`; diagnostic corotationnel legacy `BLOCKED`. | Les résultats bornés WP08-R3 et WP09 ne changent pas ces verdicts et ne se transfèrent pas à la route legacy. |
| WP-C01 | R14 `B_STAR_SLIP_FAILED`; R16 `FAIL`; R19 remédiation `OPEN`. | R17/R18 restent une relecture et un examen hors FEM; ils ne remplacent pas R16 ni ne ferment la remédiation. |
| WP-C02 | N06/N08 `FAIL`; essais Docker `FAIL`; clôture N13 `CLOSED_BOUNDED` seulement pour AR/N03. | Aucun échec n’est absorbé par la clôture bornée du cas normal. |
| WP-E01 Hencky / Newton | N historique 35/36 avec un `FAIL`; V 13/16 avec trois `FAIL`; résumé superviseur erroné `NOT_RUN` préservé comme anomalie. | Les preuves P3/S/T/U ne font pas passer Newton V. |
| WP-E01 J2 / BA | F3 14/20, H 16/20; tangente globale `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; BA global brut `FAIL`, maître-montage `NOT_VERIFIED`. | Le certificat esclave borné ne vaut pas validation globale. |
| WP-D01 | `INCONCLUSIVE`; C4 `NOT_ACQUIRED`; qualification FEM WP05 `NOT_EVALUATED`. | Aucun rejeu des archives ne devient une preuve de qualification FEM. |

## Criticité des lacunes pour v0.2.12

Cette classification porte sur le contenu de preuve nécessaire aux affirmations de capacité v0.2.12, pas sur une révision de la roadmap ni une autorisation de calcul.

| Classe | Lacune / disposition | Justification pour v0.2.12 |
|---|---|---|
| **MUST** | Maintenir les gates WP12/WP13 ouvertes et ne revendiquer que les domaines explicitement bornés; garder chaque FAIL et INCONCLUSIVE à son statut enregistré. | Nécessaire pour que la documentation de livraison n’étende pas les certificats. C’est une contrainte de revendication documentaire, pas une demande de nouvel essai. |
| **MUST** | Si la route corotationnelle J2 legacy reste accessible, présenter son domaine et ses limites connues sans lui attribuer les preuves de la route corrigée. | La route legacy est le défaut et les historiques non coaxiaux ont des anomalies documentées; la distinction est nécessaire pour une description fidèle de la capacité. |
| **SHOULD** | Acquérir une preuve indépendante de tangente J2 assemblée sur l’espace libre complet avant toute revendication de Newton global J2. | L’état est `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; la dérivée élémentaire ou le tangent du sous-système BA ne prouve ni l’assemblage ni le solveur global. Ce travail n’est pas une gate autonome E01 de publication selon le roadmap consulté. |
| **SHOULD** | Pour élargir le contact normal C02, ajouter un oracle indépendant de réactions et une étude de convergence spatiale; pour promouvoir C01, traiter séparément le tangent slip et les extensions de glissement. | Les certificats actuels sont strictement bornés et ne justifient pas les revendications élargies. |
| **DEFERRED** | J2 multiplicatif `F=FeFp`, Newton public général Hencky, frottement/glissement fini général, multi-contact général et validation FEM native D01. | Ces capacités dépassent les fermetures bornées et la portée v0.2.12 identifiées dans les documents consultés; elles relèvent de mandats scientifiques ultérieurs. D01 reste `INCONCLUSIVE` en attendant un mandat et les preuves requises. |

## Investigations scientifiques prioritaires proposées

Les estimations sont en jours-personne d’effort ciblé, hors attente de décision Owner et hors durée machine. Elles ne constituent ni un mandat ni une autorisation d’exécuter. Pour chacune, les critères doivent être gelés avant calcul; préserver les archives et les statuts actuels, quel que soit le résultat.

| Rang | Hypothèse falsifiable et protocole candidat | Prérequis avant tout calcul | Coût estimé |
|---|---|---|---|
| 1 — Objectivité corotationnelle J2 | Après un préchargement plastique non coaxial, une rotation spatiale rigide pure conserve les invariants matériels et fait tourner les contraintes/forces selon la covariance attendue; la route legacy pourrait violer ces relations, tandis que la route corrigée devrait les satisfaire sur le cas borné. Reproduire sur un cas minimal avec oracle polaire/potentiel indépendant et comparer les identités d’état. | Mandat scientifique Owner distinct; HEAD et sources/fixture exacts gelés; oracle indépendant défini; critère numérique et domaine fixés d’avance; autorisation explicite du node FEM borné correspondant. | 1–2 jours-personne |
| 2 — Tangente J2 sur espace libre complet | L’option analytique expérimentale peut correspondre à une dérivée indépendante sur branches lisses, mais doit signaler les transitions de branche et ne pas revendiquer une dérivée classique à la surface de charge. Comparer d’abord le point et TET4, puis scatter d’assemblage indépendant sur tous les DDL libres. | Mandat et critères Owner; HEAD, maillage, carte DDL et branches gelés; oracle différentiel indépendant; validation préalable matériau puis élément; autorisation distincte pour assemblage. Aucun essai Newton global avant ces portes. | 3–5 jours-personne |
| 3 — Portée de preuve contact | Le PASS C02 normal actuel ne prédit pas nécessairement une réaction de support indépendante ni une convergence du front; séparément, il ne résout pas le tangent slip C01. Choisir avant protocole une seule branche: (a) C02, oracle indépendant de réaction et convergence de maillage; ou (b) C01, tangent slip sur paire/triangle et petites rotations. Les deux ne forment pas un seul certificat. | Décision Owner sur C01 ou C02; identité exacte et critères préenregistrés; oracle indépendant (réaction pour C02, tangent pour C01); fixture et limites gelées; autorisation de calcul contact propre au périmètre choisi. | 4–7 jours-personne |

Ces trois propositions sont des priorités d’audit seulement. Elles ne changent ni la roadmap ni les verdicts et exigent un mandat scientifique séparé avant toute exécution.

## Références scientifiques consultées

- Felippa & Haugen, « A unified formulation of small-strain corotational finite elements: I. Theory » (2005), [article et résumé](https://www.sciencedirect.com/science/article/pii/S0045782504005353), DOI 10.1016/j.cma.2004.07.035. Référence de formulation et de cohérence variationnelle corotationnelle; elle ne vérifie pas l’implémentation QF Solver.
- SIMULIA, [Stress measures](https://abaqus.uclouvain.be/English/SIMACAETHERefMap/simathe-c-stressmeas.htm). Référence de convention sur mesures de contrainte et déformations conjuguées en travail; elle ne certifie pas les calculs du code audité.

- [`VonMisesElastoplasticMaterial`](../../src/solveur/materials/solid.py) — retour radial, état, tangente algorithmique.
- [`TotalLagrangianJ2Element`](../../src/solveur/elements/solid/total_lagrangian_j2.py) — F/E/S/P, force et tangent matériel/géométrique.
- [`corotational_j2.py`](../../src/solveur/elements/solid/corotational_j2.py) et [`assembly/nonlinear.py`](../../src/solveur/core/assembly/nonlinear.py) — routes legacy/corrected et stratégies de tangent.
- [`finite_strain_hencky.py`](../../src/solveur/materials/finite_strain_hencky.py), [`finite_strain_hencky_tangent.py`](../../src/solveur/materials/finite_strain_hencky_tangent.py) — matériau point et action tangentielle.
- [`contact/solver.py`](../../src/solveur/contact/solver.py), [`support.py`](../../src/solveur/contact/support.py), [`entities.py`](../../src/solveur/contact/entities.py), [`evaluation.py`](../../src/solveur/contact/evaluation.py) — opérateurs et contrats partagés.
- [`core/nonlinear/solver.py`](../../src/solveur/core/nonlinear/solver.py), [`iteration.py`](../../src/solveur/core/nonlinear/iteration.py) — intégration Newton et tangentes.

**Décision d’audit :** aucune promotion au-delà des périmètres nommés; conserver les verdicts historiques et étiquettes expérimentales. A1–A5 sont des protocoles futurs, pas des résultats.
