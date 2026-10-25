# Audit de la base de connaissances IA — QF Solver v0.2.12

**Date de revue :** 2026-10-25

**Périmètre :** documentation commune `docs/ai/`, capacités intégrées au candidat v0.2.12, sources, interfaces et preuves citées.

**Identité source examinée :** commit `4653abed9bd6d658fe68f29505377e2efdb75955`, tree `7f52585236f773751e235574bcb2d716772f867a`; la branche distante désignée pointait sur le même commit avant cette livraison documentaire.
**Nature :** revue statique/documentaire uniquement. Aucun solveur, test, calcul FEM, QEP, Campbell ou benchmark n’a été exécuté.

## Résumé

La base `docs/ai/` fournit maintenant une navigation courte vers une carte des capacités, les formulations, les dépendances, les tests et les enregistrements de qualification. La page de release distingue l’intégration v0.2.12 des capacités héritées de v0.2.11 et des décisions bornées. L’inventaire indépendant a mis au jour une collision importante : le WP13 RBE/MPC historique avait été présenté comme le WP13 opérationnel actuel. Les documents d’orientation le distinguent désormais du WP13 v0.2.12 de release engineering, packaging et publication. Les différences de numérotation WP05/WP06 entre v0.2.11 et v0.2.12 sont également explicites.

Des omissions susceptibles de sous-décrire le code ont été corrigées : familles acceptées par `MaterialFactory`, noyaux matériaux expérimentaux non raccordés à une route générale, critères de rupture première-ply, limites des backends PETSc/SLEPc et fonctions grandes tailles internes non exportées. La description de C02 a été resserrée pour ne pas suggérer qu’un certificat historique ou une archive de provenance équivaut à une campagne rejouée sur le candidat courant.

**Verdict : `KNOWLEDGE_BASE_VERIFIED_WITH_LIMITATIONS`.** Un assistant qui suit `INDEX.md`, puis la page spécialisée pertinente et ses liens peut présenter les capacités effectivement intégrées avec des limites et états de preuve sensiblement plus exacts. La base reste un index, pas une source normative : une réponse sur une combinaison précise, un oracle ou un statut doit encore remonter au code, au contrat, au rapport, au manifeste et à la décision applicable. Aucun résultat numérique courant n’est affirmé.

## Identité et méthode

Le HEAD local, son tree et la branche distante ont été contrôlés avant l’audit; commit et tree concordaient avec les identités d’audit ci-dessus. Depuis le commit `e711c553611144f2aa1f0f286a39acc3c985be6b` déclaré comme snapshot de l’inventaire de release, `git diff e711c553..HEAD` ne contient que des fichiers `docs/ai/`; la source scientifique n’a donc pas changé entre ces deux identités. Les documents déjà présents dans l’arbre de travail ont été comparés à ce HEAD; toutes les modifications préparées pour cette mission sont limitées à des fichiers Markdown sous `docs/ai/`.

L’inventaire a été construit depuis les sources d’interface et d’implémentation, et non en recopiant `CAPABILITIES.md` : `AnalysisSettings` et `AnalysisRouter`, les descripteurs de compatibilité et le registre d’éléments, les branches du `MaterialFactory`, la façade `qf_solver` / `solveur.api.public`, le parseur CLI, les modules de post-traitement/IO et les sous-packages grandes tailles. Ils ont été confrontés aux tests nommés, aux contrats WP00–WP10, aux rapports v0.2.11, aux décisions Owner et aux registres v0.2.12 cités dans les pages spécialisées.

Les liens, chemins, références et formulations ont fait l’objet d’une inspection statique. L’existence d’un test est notée comme disponibilité seulement, sauf lorsque le rapport ou manifeste d’origine porte un résultat. Aucun test n’a été lancé dans cette revue.

## Couverture indépendante vérifiée

| Domaine | Présence vérifiée dans le code/interface | Maturité et preuve à communiquer |
|---|---|---|
| Éléments | TET4, TET10, HEX8, HEX20, WEDGE6, BEAM2, MITC3, MITC4 et entités discrètes; un noyau PYRAMID5 est au registre interne sans descripteur de compatibilité correspondant. | La déclaration de route dépend de la combinaison analyse/matériau/charge. WEDGE6 dynamique est expérimental; PYRAMID5 ne constitue pas une route générale. Voir [CAPABILITIES](CAPABILITIES.md). |
| Analyses | Statique, modale, harmonique directe, Newmark direct, flambement linéarisé, routes non linéaires sélectionnées, réduction harmonique, Newmark modal, accélération uniforme de base, D01/D02, rotating modal et Campbell. | Les méthodes sont identifiées dans `settings.py` et dispatchées/refusées par `AnalysisRouter`; leurs preuves et limites diffèrent. D01 reste INCONCLUSIVE, D02 CLOSED_BOUNDED, méthodes dynamiques réduites EXPERIMENTAL. |
| Matériaux | Factory JSON/API : `beam_isotropic`, `isotropic_3d`, `orthotropic_3d`, `composite_orthotropic_3d`, `nonlinear_isotropic_3d`, `von_mises_elastoplastic_3d`, `shell_isotropic`, `orthotropic_lamina`, `shell_laminate`. | La factory n’est pas une matrice de compatibilité universelle. J2 corotationnel corrigé, StVK/Neo-Hookean point matériel, Hencky et indicateurs composites ont des périmètres distincts; `finite_kinematic_j2` n’est pas qualifié. |
| Non linéaire et états | Routes statiques non linéaires avec Newton, modified Newton, line search et arc-length selon les chemins; formulations total-Lagrangian/corotationnelles sélectionnées; état trial/accepted, checkpoints. | WP08–WP10 ont des décisions bornées; WP-E01 reste OPEN_WITH_BOUNDED_CERTIFICATES. Un test matériau ne qualifie pas le solveur FEM complet. FAIL et NOT_ACQUIRED restent visibles dans les rapports. |
| Contact | Composants normaux et frottants, recherche/évaluation, assemblage et état de reprise. | WP-C01 CLOSED_NEGATIVE avec remédiation ouverte; WP-C02 CLOSED_BOUNDED uniquement AR/N03. Aucun certificat ne justifie le contact général. |
| Contraintes et RBE | MPC linéaire, RBE2, deux modes RBE3 et diagnostic de rang dans des périmètres décrits par source et décision. | Les décisions bornées sont dans le flux historique distinct `WP13-RBE`; leur rapport d’intégration et ses 100 PASS sont historiques, pas une exécution sur ce HEAD. L’approbation finale d’intégration y reste en attente. |
| Rotordynamique | Assemblage gyro de disques, rotating modal avec QEP dense et modes complexes, Campbell à vitesses explicites et suivi MAC complexe. | Capacités héritées de v0.2.11, maturité EXPERIMENTAL. GYRO-01–06 sont des preuves historiques; l’ambiguïté à 100 rad/s est conservée. |
| API, CLI, IO et résultats | Façade Python et commandes CLI; JSON modèle/résultat, lecteur INP borné, import Gmsh MSH 4.1, exports choisis, bundles de preuve, sérialisation route-spécifique, HDF5 mixte limité. | WP11 CLOSED sur intégration/API uniquement. DTO hétérogènes; aucun chargeur universel de résultats n’est promis. `save_result` ne remplace pas par défaut. |
| Grandes tailles et backends | API grandes tailles surtout TET4 linéaire statique structuré/partitionné, stockage HDF5/NPZ, post-traitement chunké et outils de mesure; solveurs PETSc et chemin modal SLEPc sur certaines routes. | L’existence d’un backend ou d’un outil de benchmark n’établit ni prise en charge sur chaque analyse, ni performance générale, ni scalabilité MPI générale. Certaines fonctions TET4 modal/Newmark de `solveur.large.dynamic` sont internes et non exportées comme workflow public. |

Les noms exacts des fonctions publiques et les commandes sont liés à [la référence API](../reference/qf_solver_api.md), à [la façade](../../src/qf_solver/__init__.py), à [l’implémentation publique](../../src/solveur/api/public.py) et au [parseur CLI](../../src/solveur/cli/main.py), évitant de recopier ici un inventaire de signatures susceptible de devenir obsolète.

## Omissions et corrections apportées

1. **Collision WP13.** `wp13_rbe_*` désigne un flux historique d’intégration RBE/MPC. La roadmap et les documents Owner actuels définissent le WP13 opérationnel v0.2.12 comme release engineering, packaging et publication, statut OPEN. Une annexe prospective du 7 octobre réutilise encore WP13 pour Campbell. La table de correspondance indique les trois contextes sans renuméroter les archives.
2. **Collision WP05/WP06.** WP05/WP06 v0.2.11 désignent gyroscopie/rotating modal et Campbell; WP05/WP06 v0.2.12 désignent harmonique réduit et Newmark modal. Les références précisent maintenant le release.
3. **Noyaux matériaux omis ou confondus.** `CAPABILITIES.md` distingue les types réellement construits par la factory, les évaluations StVK/Neo-Hookean au point matériel, les helpers Hencky force-only TET4/HEX8, le chemin `finite_kinematic_j2` NOT_QUALIFIED et les critères maximum-stress/strain, Tsai-Hill et Tsai-Wu de première-ply. Aucun n’est transformé en route générale de plasticité ou dommage progressif.
4. **Backends et surface publique.** Les chemins PETSc/SLEPc, le refus du PETSc pour l’harmonique complexe directe, le QEP rotor dense et les helpers de grandes tailles non exportés sont distingués des API/CLI publiques.
5. **Contact C02.** La continuité historique AR/N03 reste bornée. La source/archive N10 est externe et non re-hashée dans la revue WP12-0; le helper AJ exact nécessaire à M4/M5 n’existe pas dans ce checkout; les dépendances de contact modifiées depuis n’ont pas été revalidées numériquement. Aucun PASS M4/M5 sur le HEAD courant n’est revendiqué.
6. **D02 et exports.** Les exports CSV/VTU sont qualifiés comme exports de résultats statiques sélectionnés. Les wrappers D02 sont décrits comme post-traitement de champs de contraintes, non comme solveurs ou assemblage de modèle.

## Audit des formulations

- La relation modale classique `K φ = ω² M φ` et les projections réelles `K_r = ΦᵀKΦ`, `M_r = ΦᵀMΦ` sont cohérentes avec les chemins et le contrat WP04; ce dernier porte les conventions de normalisation, les seuils et les critères d’acceptation.
- Le chemin harmonique direct construit `K + iωC − ω²M` et convertit la fréquence d’entrée en Hz en pulsation. La page mécanique renvoie au contrat pour les conventions de charge et de phase. La route harmonique réduite n’est pas assimilée à la route directe.
- La vérification ciblée de `modal_basis.py` et `modal_basis_numerics.py` confirme : K et M sont refusées si l’erreur relative de symétrie dépasse `1e-12`; K exactement symétrique aux valeurs stockées utilise le calcul bilinéaire structuré qui affecte les deux triangles par le même scalaire; une K dans la tolérance mais non exactement symétrique garde le produit historique `ΦᵀKΦ`. Aucune moyenne de la matrice complète ni correction de K n’a été observée. Ce comportement source est désormais explicitement décrit. Comme la modification de projection est postérieure à certaines preuves WP04, la non-régression numérique attend WP12.
- La rotordynamique documente `M q̈ + ΩG q̇ + Kq = 0` et son QEP `λ²M + λΩG + K`, en renvoyant aux contrats WP05/WP06 v0.2.11 pour axes et signes. Le modèle reste limité aux disques rigides centrés; les résultats Campbell ne sont pas une réponse forcée ni une décision de vitesse critique.
- Pour J2, corotation, contact, couches et recovery de contraintes, les pages d’orientation évitent les équations universelles non justifiées et renvoient aux contrats propres aux formulations. La revue documentaire n’a trouvé aucune contradiction dans les conventions résumées, mais elle ne constitue pas une revue complète de chaque équation ni une validation numérique indépendante.

## Dépendances et impact de changement

`DEPENDENCIES.md` sépare les appels directs des impacts potentiels. Les relations principales vérifiées dans les consommateurs sont : projection modale → `ModalBasis` → harmonique réduit/Newmark modal; système dynamique préparé → excitation/base → ces routes; matériaux/registre/préflight → construction JSON/API, assemblage et création d’état; ply axes → opérateurs MITC, récupération shell et indicateurs; DOF/constraints/RBE → réduction/reconstruction sur les routes concernées; gyro disque → rotating modal → QEP → Campbell; DTO/serialisation → API, CLI, post-traitement et fichiers de résultat.

Les liens d’import seuls ne sont pas présentés comme impact mécanique. Les impacts indirects exacts dépendent de la route, du type d’élément et du contrat; la page est une carte de revue, pas une fermeture exhaustive de graphe d’appels.

## Statuts et provenance

La revue préserve les états normatifs courants de la roadmap du 2026-10-25 : WP-C01 CLOSED_NEGATIVE/remédiation ouverte; WP-C02 CLOSED_BOUNDED AR/N03 seulement; WP-D01 INCONCLUSIVE; WP-D02 CLOSED_BOUNDED; WP-E01 OPEN_WITH_BOUNDED_CERTIFICATES; WP11 CLOSED pour l’intégration/API; WP12 et WP13 opérationnel OPEN. Le compte administratif 19/14/1/4 n’est pas présenté comme mesure de couverture scientifique.

La base sépare existence du code, route déclarée, test présent, résultat rapporté, exécution sur HEAD, vérification/validation et décision Owner. Les PASS historiques restent attachés à leur manifeste, source, modèle, environnement et périmètre. Aucun PASS historique C02, rotor, RBE ou WP02–WP10 n’est converti en PASS courant. L’état du runner WP12 est `RUNNER_READY_FOR_OWNER_SECURITY_REVIEW`; `EXECUTE` scientifique reste désactivé.

## Scénarios de navigation IA

| Question | Résultat de la navigation | Réserve à transmettre |
|---|---|---|
| A — « Quelles capacités v0.2.12 ? » | `INDEX.md` → `PROJECT_CONTEXT.md` donne le résumé; `CAPABILITIES.md` et `releases/v0.2.12.md` couvrent les familles, routes et capacités intégrées/héritées. | Vérifier une combinaison concrète dans descripteurs, preflight, contrat et source. La page de contexte seule n’est pas exhaustive. |
| B — Formulations non linéaires et limites | `MECHANICS.md` → nonlinear overview → contrats WP08–WP10/WP-E01; la release sépare J2 de StVK, Neo-Hookean et Hencky expérimentaux. | Le statut WP-E01 reste ouvert et un point matériel ne prouve pas un solveur FEM complet. |
| C — Impact d’une modification modale | `DEPENDENCIES.md` et `DEVELOPMENT.md` identifient projection, basis, harmonique réduit, Newmark modal et tests/contracts associés. | Le graphe est orientatif; suivre les appels et identités d’opérateurs du diff concret. |
| D — Qualifiées, expérimentales, inconclusives | `QUALIFICATION.md` et la page de release séparent statuts, preuves et identité historique. | L’état courant peut évoluer; consulter la roadmap normative et les décisions. |
| E — Campbell rotor | `CAPABILITIES.md`, `MECHANICS.md` et la section héritée v0.2.11 donnent route, suivi complexe, limitations et ambiguïté 100 rad/s. | Maturité EXPERIMENTAL; GYRO-01–06 sont historiques, pas des tests du HEAD. |
| F — RBE2 versus RBE3 | La table RBE dans `releases/v0.2.12.md` résume rigid-arm, projection et pondération, décisions bornées et exclusions. | Intégration finale en attente; consulter décision, source et tests pour conditions géométriques/algébriques exactes. |

Les scénarios réussissent comme navigation documentaire, avec ces réserves. Ils ne sont pas une évaluation empirique de plusieurs modèles ni une preuve que PROJECT_CONTEXT isolé contient tous les détails d’un audit.

## Limites et actions Owner

- Le paquet v0.2.12 demeure un candidat non publié; la métadonnée du package pointe encore vers 0.2.11. Il faut relire la roadmap pour tout statut vivant.
- Le WP13 RBE/MPC historique conserve une approbation d’intégration en attente; cette revue ne la remplace pas et ne modifie pas la décision Owner.
- Toute campagne WP12 nécessite les revues de sécurité et autorisations propres aux unités de campagne; le présent audit n’autorise pas leur exécution.
- Un rejeu des cas C02 dépend d’une décision Owner spécifique et d’un overlay AJ absent du checkout; aucun overlay n’a été matérialisé.
- Les preuves historiques et une revue statique ne permettent pas de conclure à la non-régression numérique sur ce HEAD.

Aucune décision Owner n’est requise pour corriger l’identité du WP13 opérationnel : les sources normatives v0.2.12 la définissent déjà. Les actions Owner mentionnées ci-dessus restent nécessaires pour leurs propres gates ultérieurs.

## Modifications de cette revue

Les documents ajustés sont `CAPABILITIES.md`, `DEPENDENCIES.md`, `INDEX.md`, `MECHANICS.md`, `PROJECT_CONTEXT.md`, `QUALIFICATION.md`, `TESTING.md`, `ARCHITECTURE.md` et `releases/v0.2.12.md`. Le présent rapport est ajouté sous `docs/ai/`. Aucun fichier `src/`, test scientifique, contrat, manifeste, rapport de preuve, décision Owner ou statut de work package n’a été modifié. Aucun test, calcul, campagne ou benchmark n’a été exécuté.
