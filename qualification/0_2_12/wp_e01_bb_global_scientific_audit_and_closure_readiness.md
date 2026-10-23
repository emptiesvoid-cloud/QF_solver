# QF Solver v0.2.12 — WP-E01-BB
## Audit scientifique global, décision de clôture et préparation de l’intégration

Date de l’audit : 2026-10-23
Périmètre : preuves WP-E01 disponibles au gel BA et état local de la branche d’intégration vérifiée
Disposition : rapport d’audit documentaire et scientifique; aucune modification de formulation ni nouvelle exécution FEM

## 1. Décision proposée

**Recommandation : B — OPEN_WITH_BOUNDED_CERTIFICATES.**

Plusieurs résultats sont suffisamment étayés pour porter des certificats strictement bornés, en particulier le certificat prospectif **PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED**. Les éléments disponibles ne satisfont toutefois pas l’ensemble des critères de clôture A–E approuvés pour WP-E01. En conséquence, la décision de statut dans la roadmap reste à l’Owner; ce rapport ne clôt pas le WP et ne change pas **WP_E01_STATUS=OPEN / EXPERIMENTAL_TARGET**.

L’option A, CLOSED_BOUNDED, serait prématurée : la cohérence globale de la tangente J2 n’est pas établie, la voie incrémentale Hencky garde trois échecs historiques, et l’intégration API/V&V/release reste ouverte. L’option C, OPEN / EXPERIMENTAL seule, sous-décrirait les résultats bornés déjà obtenus, notamment le cas Newton–Armijo physique BA. La recommandation B conserve les deux faits.

**Le WP-E01 n’est pas, selon la roadmap Owner actuellement approuvée, un nouveau gate obligatoire autonome de publication v0.2.12.** Il a été ajouté comme objectif d’ingénierie expérimental sans qualification automatique ni inclusion rétroactive dans le budget MUST du 7 octobre. La roadmap demande une décision explicite avant de le rendre obligatoire pour la publication. La release globale n’est cependant pas démontrée prête : les gates et travaux v0.2.12 hors E01 doivent encore être décidés et clôturés par leurs propriétaires, notamment WP11, WP12 et WP13, dont le ledger les donne ouverts. Cette conclusion ne retire aucun gate global existant.

## 2. Identité et méthode

### 2.1 Dépôt faisant foi

| Élément | Valeur vérifiée |
|---|---|
| Worktree d’audit | C:\wpc01-frictionless-public-integration-wt\wp-e01-ag |
| Branche | emptiesvoids-cloud/wp-e01-ba-slave-bounded |
| HEAD initial | d9c36088c272100763b18700448a82ef418f6045 |
| Tree initial | 5bfe5099c31381f363e91fe72aa89557da559426 |
| Origin | https://github.com/emptiesvoid-cloud/QF_solver.git |
| État initial | Propre |

Le rapport BA et les autres rapports de qualification ont été lus comme preuves archivées; leurs résultats ne sont pas présentés comme nouvellement exécutés dans BB. Deux modules ciblés, déjà enregistrés comme tests synthétiques/contractuels, ont été exécutés : `python -m pytest -q tests/unit/test_wp_e01ag_worker_state_capture.py tests/unit/test_contact_aware_equilibrium_audit.py`, résultat observé `49 passed in 1.45s`. Aucun solveur, Docker, collect ou calcul FEM n’a été lancé. Aucun fichier de l’intégration n’a été modifié.

La mission autorisait des tests ciblés non qualifiants. Aucun nouveau test de code n’a été nécessaire : ce travail n’apporte aucun changement de code à régresser et les RUN historiques ne devaient pas être répétés. Le contrôle documentaire et l’intégrité des références ont été vérifiés localement; git diff --check est exécuté avant le commit de ce rapport.

### 2.2 Sources primaires et identité des rapports

Les SHA-256 ci-dessous ont été calculés sur les octets présents dans le worktree E01-AF/AG. Ils permettent de rattacher les constats aux rapports cités; ils ne remplacent pas les manifestes d’exécution propres aux campagnes.

| Source | SHA-256 |
|---|---|
| Module ciblé exécuté — contrats d’état, verdicts et agrégation worker, tests/unit/test_wp_e01ag_worker_state_capture.py | 06af29d5688bf528552cbfd350bf53963fffa180e55e66c122407b27d612d855 |
| Module ciblé exécuté — audit synthétique contact/équilibre, tests/unit/test_contact_aware_equilibrium_audit.py | e4b6dd60fcb70dff696cb8c142d03b84ebff3817da0ed4f3904acc22e2b40894 |
| Roadmap Owner préservée, owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md | c5140d75444905cb79e54fe995a0dce7ef060fdc6473979aaca15136285c22f1 |
| Ledger actif, ROADMAP.md | 48021a7773895c354806446ab89e317b968cfee5f2618790f4487fbf11195a6d |
| WP-E01-AA | 505fea6393e34edb9cb651ce672b5e022247340e1c3aa6b6eea3a46b851f87d7 |
| WP-E01-AB | ffbd7095b7889939b238d82a0e8c410b1d831a2d4c4c7046ebc7a38e5f9e91f8 |
| WP-E01-E — plan d’assemblage | b0a629bf80306a6cb6dba639e99d44adf4da05743dcc89084215e2dca9559d6d |
| WP-E01-F3 | 05b0cfe0934ddcc14f25b556ccca6035c212aad455ac1a680c86093b8ec44381 |
| WP-E01-AL | 044340ab275823237b24f304c960ec081d7fe082046d03c96c023e263920d8ef |
| WP-E01-AM | 446dd84bb7f799adc513a820ef794fae45600b0d2bd297af517b8fe0d13e27ec |
| WP-E01-AV | 2a4eb2b36d9f9fc9ad373d44e7a17583591f195d19293cc0a9a820ff0d910c4b |
| WP-E01-AW | 5db359fa2169048beeda8191ed0ff4f0ac05e30dbc10444951233a3eb99bef8a |
| WP-E01-AX | 694f91932336461c8a19a33fcf60c22e010cac2a94652dab4fb3d3620752f6f1 |
| WP-E01-AY | a7fba121b90b2f5fad47518262da77515d4f607b5a88103c9fb853d03239bf99 |
| WP-E01-AZ | 25603b9304fcff1d82e87a5a262f9280ea7b7c35a7655b266e73e6b31c5d6eb0 |
| WP09 — robustesse tangente corotationnelle | 660ec1e95c8652fcb469d527c1f137f8e65074814ae58a3c0395b1cdd6ad97e0 |
| WP09 — matrice de régression | 42742af2193e20898b2ba5d475e98d3ab0e01c24c5dde1b5c7480f24c0eb7a7d |
| WP08 — faisabilité constitutive | 8027f50f5e8776d3fcb5430ee55cae334716350ee3e647b8eb154c1c658883ba |
| WP-E01-C1 — matériaux StVK/Neo-Hookean | c341e06bbdc440012908364a73482c992b497a4ed3d7472a8a88d7bb9867ce19 |
| WP-E01-DE — intégration FEM | ff38e474c3937c47bc4aa4d618c3e9b8c4f2a4279193259d58c19133bc419fe0 |
| WP-E01-D4R | c8224ac6ccd120e5de17e91ec931ac536379ec6d4416a620a7a5d6569cda0eeb |
| WP-E01-H | 741947c130df21042da8e0465732634465e25371cdb79baa400cdf123dbe8e5b |
| WP-E01-J | b325524051c7b5dc679ef71703e51e70a273ef5d25101edf5b813488568f5c27 |
| WP-E01-K | c9628d955436395136b327e79e163d765881034d119b92eb17aebab7a4e0d1c8 |
| WP-E01-L | 7426427de2e250b9868acd90fe0f066f14ccc98de15de1871e9d255a25e2f08d8 |
| WP-E01-U/V/W consolidé | dc254d1228796023a04e98c690b45434c29c18bff35297550a0de7ab59fac9ff |
| WP-E01-M — conception matériau Hencky | 48a7f5d6eb52389963b82a0c0d780afc058b6f08837e90f31c00af04fae989f0 |
| WP-E01-P3 — matériau Hencky | 333c7d471780694a4c5c095ad18666c825ecca8f5406090940e332dc2f0c0584 |
| WP-E01-S — tangente matériau Hencky | 92096692a7918cb1369e91fad42f5ea3477da7ca04dcc8d364f8452d6dfb1eaa |
| WP-E01-T — tangente élément Hencky | 4b81ad1f3a1c7ffd517508f5962356117411a2b60bda37a3aba56fd805248c86 |
| WP-E01-U — assemblage global Hencky | 6ba7a838025e37fcff0abfdea16bc286e1b300df2065d2baa9965f6542a7a97b8 |
| WP-E01-BA — certificat GF4 borné esclave | 7eace9f62649bd452b058ad318a2489682d22fe0eb1a9aec739c9b05df1f1fca |

Le rapport BA indique que ses manifestes PREFLIGHT, COLLECT et RUN épinglaient et vérifiaient **534 fichiers** du gel, sans fichier absent ni divergence. Certains messages antérieurs ont abrégé ce total en 533 empreintes. Pour la campagne BA, ce rapport et ses manifestes finaux font foi; le décompte opérationnel documenté est 534. Ce décalage de comptage ne change pas les résultats numériques et n’est pas interprété ici comme une divergence de contenu.
Autre limite de transfert de preuve : le rapport DE cite le module C1 de 17 cas sous son identité historique SHA-256 F64A3F9B2E296A2366A977A782C27635AB2E6868F2C44D55A84560D9A59399F9. Le fichier test correspondant présent dans le worktree d’audit a SHA-256 0AFDCA4CFE35D6E45D987E9353B63CBFC4DE8670CF8692E146CB4035BDFCB63F. BB n’a pas vérifié l’équivalence de ces identités et ne transfère donc pas le 17/17 au fichier courant; le résultat C1 est cité uniquement comme preuve de son identité historique enregistrée.

## 3. Roadmap E01 et critères de clôture initiaux

WP-E01 a été ajouté le 18 octobre comme objectif d’ingénierie expérimental. Le périmètre original comprend :

| Sous-package | Objectif Owner initial |
|---|---|
| E01-A | Newton incrémental, contrôles de convergence, incréments, line search/cutback, tangentes et transactions d’état |
| E01-B | J2 petites déformations, retour radial, plasticité parfaite et écrouissage isotrope, chargement/déchargement |
| E01-C | Élasticité grandes déformations Total Lagrangian, mesures F/E/Piola et tangentes; StVK puis néo-Hookéen sur domaine déclaré |
| E01-D | V&V indépendante constitutive, élémentaire et multi-incréments; objectivité, tangentes, sensibilité au pas et au maillage, échecs contrôlés |
| E01-E | Intégration FEM TET4/HEX8, API, états, résultats, diagnostics et limites documentées |

Les six critères expérimentaux de clôture conservés dans l’étude Owner sont évalués ci-dessous :

1. Formulations, conventions tensorielles, unités, hypothèses cinématiques et domaines documentés : **largement atteint pour les modules expérimentaux audités**, mais le contrat API/résultats et les limites publiques relèvent encore de WP11.
2. Retour J2, durcissement et transfert d’état vérifiés sur des histoires acceptées et rejetées : **partiel**. Les points matériau, validations d’état et helpers transactionnels ont des preuves bornées; aucune trajectoire globale multi-segment complète avec chargement, déchargement/rechargement et rollback d’incrément n’est établie.
3. Tangentes constitutives et globales vérifiées avec références indépendantes sur états lisses : **non satisfait pour l’ensemble E01**. La preuve directe J2 est bornée, mais la cohérence de la tangente J2 globale reste bloquée; les gates scientifiques correspondants ne sont pas approuvés. Pour Hencky, les essais matériaux/éléments existent, mais le plateau de convergence n’est pas établi par le critère de minimum d’erreur et la voie Newton conserve des échecs.
4. Objectivité TL et cohérence contraintes/déformations : **vérifié de façon bornée pour les cas StVK et Hencky exécutés**, sans généralisation au-delà des configurations testées.
5. Cas FEM TET4/HEX8 sélectionnés, échecs contrôlés, limites de convergence et reproductibilité archivés : **partiel**. Il existe des V&V directes, assemblées et un cas physique TET4 BA, mais pas une matrice complète de chemins/formulations; V conserve 3 FAIL et les essais J2 globaux conservent des échecs.
6. API, diagnostics, V&V et documentation limités explicitement à EXPERIMENTAL : **partiel**. Le statut expérimental et les exclusions sont documentés; l’intégration et le contrat de résultats complet n’ont pas été clôturés par WP11–WP13.

Ces critères portent sur la clôture E01, pas sur un nouveau gate de publication automatiquement ajouté. La roadmap Owner dit explicitement de réévaluer le budget et les gates avant de rendre E01 obligatoire pour la publication.

## 4. Matrice de maturité des capacités

Les statuts décrivent le périmètre des preuves disponibles. « Oracle indépendant » distingue une référence analytique ou une reconstruction séparée d’une comparaison entre deux appels du même noyau. « FEM natif » désigne ici le scénario exécuté dans le chemin de production; les assemblages isolés et les calculs synthétiques sont indiqués séparément.

| Capacité | Implémentée | Tests unitaires / éléments | Oracle indépendant | FEM natif | Équilibre | Statut justifié | Manque principal |
|---|---|---|---|---|---|---|---|
| Newton incrémental synthétique A | Oui, voies expérimentales ciblées | AA : 16/16 PASS sur petits modèles TET4/HEX8 en mémoire | Références algébriques pour les fixtures | Non : cas synthétiques | Résidus de fixtures; pas une qualification physique générale | VERIFIED_BOUNDED pour les fixtures AA | Une trajectoire Newton physique ne se déduit pas des fixtures; aucun checkpoint durable/production certificate général |
| Newton–Armijo physique GF4 TET4 | Oui, chemin de production invoqué par BA | Scénario ciblé; assertions de contrat et preuves de RUN | Résidu libre et bilan du sous-système esclave; la force de contact est issue des sorties de quadrature de production | Oui, un scénario/maillage/chemin; deux replays dans une invocation RUN | Force et moment esclave PASS; maître/montage non vérifié | PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED | Un seul cas borné; absence d’oracle indépendant calculant la force de contact depuis la loi, l’aire et les poids; aucune preuve maître |
| Verdict global du RUN BA | Le worker émet des verdicts distincts, agrégation corrigée | Replays individuels et agrégat conservés | Revue des reçus et signatures | Même RUN physique BA | Verdict brut global FAIL; MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED | Certificat esclave borné PASS; portée globale FAIL/WARNING | Ne pas assimiler le certificat nommé à un certificat global |
| J2 point matériau et état | Oui, petites déformations; plusieurs lois/configurations existantes | Direct V&V incluse dans D4R; validations d’état et négatives | Diagnostics Decimal à portée fixe-histoire et références matériau bornées | Pas de trajectoire globale J2 qualifiante établie | Sans objet à l’échelle du point | VERIFIED_BOUNDED sur les cas directs D4R | Histoire complète multi-segment intégrée non exécutée |
| J2 tangente élément TET4/HEX8 | Oui, opérateurs directs | D4R : 65 PASS pour le module direct historique, périmètre documenté | Différences et directions admissibles définies par les tests; seuil J2 reste candidat | Pas une qualification globale de solveur | N/A au point/élément isolé | VERIFIED_BOUNDED au niveau direct testé; J2_TANGENT_SCIENTIFIC_FREEZE=NOT_APPROVED | Gate scientifique non gelé; résultats globaux directionnels encore incomplets |
| J2 assemblage global et tangente réduite | Assemblage expérimental présent; diagnostic réduit L préparé | F3 : 20 collectés, 14 PASS/6 FAIL; H : 20 collectés, 16 PASS/4 FAIL; K : 12/12 PASS sur identité de plan et contrôles translation | J : 6 diagnostics Decimal et 2 comparaisons Richardson PASS; ne règle pas toutes les directions assemblées | Non pour une trajectoire Newton J2 complète | Incomplet | GLOBAL_ASSEMBLY_VNV=PARTIAL; J2_ASSEMBLED_TANGENT_CONSISTENCY=BLOCKED_PENDING_INDEPENDENT_EVIDENCE | L est PREPARED_NOT_RUN; directions faibles historiques à 6,74–11,03 % non résolues; gate non approuvé |
| J2 corotationnel corrigé | Oui, formulation Biot J2 corrigée versionnée, opt-in EXPERIMENTAL; l’ancienne route corotationnelle reste distincte | WP09 : 39 tests de route corrigée PASS, régressions sélectionnées et robustesse bornée documentées | Dérivées directionnelles et références WP08/WP09 bornées aux cas et branches rapportés | Modèle global corrigé limité exécuté dans WP09; ce n’est pas une preuve E01-A Armijo générale | Convergence/réponse pour fixtures citées seulement | Héritage WP09 CLOSED_BOUNDED; maturité de la route corrigée reste EXPERIMENTAL | La route legacy conserve les findings sémantiques WP08; ne pas fusionner legacy, route corrigée et petites déformations; ne vaut pas J2 finite-strain multiplicatif |
| J2 Total Lagrangian additif | Oui, route séparée utilisant Green–Lagrange et retour J2 | Tests TL J2 dédiés et régressions WP08/WP09 documentés | Tangente/mesures vérifiées selon les tests dédiés; les résultats et limites de stress WP08 restent à respecter | Cas et intégration limités; aucun chemin plastique global multi-segment qualifiant n’est établi ici | Borné aux fixtures héritées | Route implémentée avec preuves bornées; pas une qualification générale de plasticité finite-strain | Ce modèle additif dans E_G n’est pas F=FeFp; la tangente globale E01 et la trajectoire complète restent à démontrer |
| TL StVK TET4/HEX8 | Oui | D4R direct; cas globaux bornés documentés avec force/tangente/objectivité | Références affines et dérivatives bornées propres aux fixtures | Pas de campagne globale de convergence générale | Équilibre limité aux cas assemblés testés | VERIFIED_BOUNDED pour les cas élémentaires/assemblés décrits | Aucun droit de généraliser aux grandes déformations arbitraires ou à toutes les mailles |
| TL Neo-Hookean isochore/volumique | Oui, noyau matériau-point expérimental isolé | C1 rapporte 17/17 PASS pour son identité historique; le module test courant a un hash différent et BB ne transfère pas ce PASS | Formules analytiques et contrôles énergétiques/tangent ponctuels du rapport; dérivées à une échelle, sans plateau multistep établi | Aucun élément ni assemblage Neo-Hookean; aucun chemin solveur/public | N/A, matériau-point seulement | Résultat matériau-point borné pour le candidat implémenté et l’identité historique testée; formulation et domaine J admissible pas gelés | Le choix d’énergie et J_min doivent être approuvés avant intégration; aucune équivalence à la forme log-J n’est présumée |
| Hencky matériau point | Oui, opt-in expérimental, non enregistré dans la fabrique publique | P3 : 41/41 PASS; ancien N 35 PASS/1 FAIL préservé | Références analytiques et mesures d’objectivité selon les fixtures | Non | N/A | VERIFIED_BOUNDED pour tests matériau-point exécutés | Pas de tangent ni intégration publique par ce seul résultat |
| Hencky tangente matériau | Oui, action analytique directionnelle expérimentale | S : 35/35 PASS; 6 sweeps ont montré un régime O(h²) selon le rapport | Références Decimal diagonales et contrôles énergétiques; certaines comparaisons restent de cohérence différentielle | Non | N/A | VERIFIED_BOUNDED sur configurations testées | Le gate accepte le minimum d’erreur; TANGENT_CONVERGENCE_PLATEAU=NOT_ESTABLISHED; ne pas prétendre au plateau global |
| Hencky tangente élémentaire TET4/HEX8 | Oui, adaptateur isolé | T : 34/34 PASS | Références élémentaires/analyses directionnelles du rapport, périmètre borné | Local élément uniquement | Sans certification globale | HENCKY_ELEMENT_TANGENT=VERIFIED_BOUNDED | Pas d’intégration au Newton public; pas de convergence maillage |
| Hencky assemblage global isolé | Oui, adaptateur expérimental | U : 31/31 PASS pour les nœuds listés | Références algébriques et cas de forces/assemblage décrits | Assemblage en mémoire, pas une route publique | Réactions/équilibre bornés des fixtures | HENCKY_GLOBAL_ASSEMBLY=VERIFIED_BOUNDED pour ce jeu de cas | Aucun dispatch public; ne prouve ni robustesse globale ni matériau J2 finite-strain |
| Hencky Newton incrémental isolé | Oui, expérimental | V : 16 collectés, 13 PASS/3 FAIL | Trajectoires affines bornées; quelques contrôles synthétiques de line search | Newton isolé TET4/HEX8, pas production publique | Résidu des cas réussis seulement | PARTIAL / FAIL_PRESERVED | Deux assertions d’identité d’état accepté échouent; cas initial à charge nulle ne teste pas la charge non nulle voulue; aucun rejet physique suivi d’une acceptation réduite |
| Intégration API, résultats, sérialisation et support E01 | Présence partielle, voies expérimentales | Tests locaux par module; matrice globale non clôturée | Aucun audit transversal complet établi ici | Pas de contrat public E01 complet | Pas de matrice complète | INCOMPLETE | WP11/WP12/WP13 et limites de support/publication restent ouverts |
| J2 multiplicatif grandes déformations | Non implémentée | Aucun | Aucun | Non | N/A | NOT_IMPLEMENTED et hors périmètre initial | Capacité future séparée : F=FeFp, état, tangente et validation |

### 4.1 Portée de D4R

Les 65 PASS de D4R constituent une preuve historique directe sur le module élémentaire autorisé et son identité exacte. Ils ne sont pas une rerun par BB, ne prouvent pas l’assemblage global J2, ni la convergence Newton, ni une intégration publique. Le rapport D4R conserve le contexte et la portée exacte.

### 4.2 Portée de la preuve J2

Les quatre échecs directionnels globaux rapportés par H ne doivent être ni effacés ni convertis en défaut de production démontré. Les directions faibles comportent des composantes sur des DDL prescrits et ne sont donc pas des directions Newton réduites admissibles. J confirme un comportement O(h²) pour le cas TET4 libre-centre-mixte et deux comparaisons Richardson bornées. K corrige l’identité DofManager/plan et valide les contrôles de translation, mais les écarts faibles historiques demeurent non résolus. Le test réduit proposé par L n’a pas été exécuté. Il manque donc encore une comparaison indépendante de Jv sur une direction strictement libre, résoluble et à branche fixée.
## 5. Newton–Armijo et contact GF4 : verdicts qui coexistent

Le résultat BA établit pour le cas exact gelé :

- le pas complet α=1 et le pas α=0,5 sont rejetés;
- α=0,25 satisfait le test Armijo et est accepté;
- trois pas complets α=1 supplémentaires sont acceptés;
- quatre corrections Newton et quatre résolutions linéaires sont enregistrées;
- la norme finale du résidu libre est 2.182020284783493e-12 N, sous la tolérance relative gelée 1e-9;
- le facteur de charge final est 1 et un seul commit accepté est effectué;
- les deux replays ont la même signature scientifique c086f9c59bcd6dea6d1855163c23f77e9bcc2a092a40cc17773e233571cdf3ce;
- le bilan du sous-système esclave donne une erreur relative force 2.0375137808189935e-12 et moment 1.337698787036916e-12, sous les limites contractuelles 1e-10.

Les six contrôles du certificat borné nommé sont PASS. Cela justifie uniquement :

**PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED**

Le rapport BA conserve en même temps le verdict brut global FAIL et le run_verdict=WARNING, car la provenance de la réaction du montage rigide n’a pas été mesurée indépendamment. L’équilibre maître + montage demeure MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED; le certificat global reste PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED et GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED.

Le bilan esclave ajoute une fois la force de contact issue des sorties de quadrature GF4. Ce n’est pas une reconstruction indépendante de la pression multipliée par l’aire et les poids; aucun tangent de contact indépendant n’est inclus. L’exclusion du maître est explicite et scientifiquement acceptable pour le certificat prospectif borné BA, mais n’est pas une preuve d’équilibre du système complet.

Les anciens bilans contact-blind E+R (force relative 0.6657242842315055, moment relative 0.507475126989006) restent des diagnostics historiques et ne doivent pas être présentés comme le bilan contact-aware BA. Ils sont conservés dans le rapport d’origine.

## 6. Résultats négatifs et historique à préserver

Les résultats suivants restent dans le registre des preuves; les résultats ultérieurs ne les réécrivent pas :

| Campagne | Résultat à conserver | Interprétation bornée |
|---|---|---|
| D4R | 65 PASS | V&V élémentaire directe pour son identité gelée |
| F3 | 20 collectés, 14 PASS / 6 FAIL | Deux références élastiques de précision insuffisante et quatre échecs de tangente J2 globale; preuves diagnostiques, pas qualification |
| H | 20 collectés, 16 PASS / 4 FAIL | Direction TET4 fenêtre globale et directions faibles locales J2 en échec sous le gate proposé |
| J | 6 diagnostics Decimal PASS; 2 comparaisons Richardson PASS | Résultats fixes-histoire bornés; l’observation O(h²) ne rend pas valide une direction contrainte |
| K | 12/12 PASS | Répare l’identité de fixture et démontre les translations rigides testées; ne résout pas la tangente J2 globale |
| AB | 16 PASS / 1 FAIL | Le garde test/no-FEM a correctement refusé le chemin physique; ce n’est pas une exécution FEM |
| AL | RUN ERROR après lecture du champ privé _last_load_step_state absent; diagnostic numérique initial NOT_RECORDED | Trace et verdict ERROR préservés; la correction AV traite l’instrumentation du worker |
| AW | Deux replays ont atteint des décisions de line search, puis ERROR_CONFIGURATION car qualification/requirements.json manquait dans l’image | Pas de résultat final qualifiant; aucune reclassification en PASS |
| AX | Deux replays ont convergé, mais les bilans contact-blind ont FAIL (force 0.6657, moment 0.5075); l’ancien agrégat worker PASS était incohérent | FAIL détaillé conservé; AY corrige l’agrégation; AZ/BA introduisent le bilan contact-aware borné |
| AY / AZ | P1 d’agrégation identifié puis audit de contact corrigé | L’agrégation fail-closed préserve FAIL/ERROR; l’ajout de la contribution contact est justifié dans le nouveau périmètre |
| BA | Certificat esclave PASS; verdict brut global FAIL/WARNING | Deux faits distincts; tous deux restent actifs |
| P3 | 41 PASS | Matériau Hencky point et ses cas autorisés, historique N 35/1 préservé |
| S | 35 PASS | Tangente Hencky au matériau, mais plateau du gate non établi |
| T | 34 PASS | Tangente d’élément Hencky isolée |
| U | 31 PASS | Assemblage global Hencky en mémoire borné |
| V | 13 PASS / 3 FAIL | Newton Hencky isolé partiel; aucun rejet physique suivi d’une acceptation réduite |

Une entrée PASS d’une campagne ultérieure ne supprime pas l’échec historique d’une identité ou d’un contrat antérieur. Les campagnes sont comparées seulement après vérification des hashes et des conditions de test.

## 7. Revue indépendante

Une revue distincte, en lecture seule, a vérifié le périmètre BA, les reçus, signatures, chiffres Newton–Armijo et bilans du sous-système esclave. Le reviewer n’a lancé aucun test, Docker ou calcul. Il confirme que le certificat nommé est cohérent avec ses six critères PASS, tout en maintenant le verdict global FAIL, le statut maître NOT_VERIFIED et la qualification générale NOT_ACQUIRED.

Pour l’audit BB, le reviewer recommande également l’option B. Il ne relève pas de P0. Il retient :

- **P1 pour clôture générale E01 :** cohérence de tangente J2 globale non démontrée et gate non approuvé;
- **P1 d’intégration conditionnel à l’inclusion d’E01 :** E01 n’est pas dans la branche d’intégration vérifiée et les contrats WP11–WP13 ne sont pas clôturés; si E01 est exclu de la release, ce constat n’ajoute pas un gate E01 autonome.
- **P2 scientifique BA :** force de contact du bilan esclave lue depuis la production, sans recalcul indépendant depuis la loi et les poids;
- **P2 de maturité Hencky :** V conserve 13 PASS/3 FAIL et le rapport U/V/W signalait une incohérence de reporting du superviseur; S ne prouve pas le plateau demandé par son gate malgré des régions O(h²) observées.

Ces constats ne bloquent pas le certificat BA tant qu’il conserve son périmètre exact. Ils bloquent ou limitent une clôture globale plus large. Aucun désaccord important entre l’audit principal et la revue indépendante n’est relevé.

Limite d’indépendance : la revue porte sur les sources et preuves archivées; elle n’est pas une nouvelle vérification numérique indépendante.

## 8. Travaux restants et effet publication

Les estimations ci-dessous sont des tailles relatives de planification, pas des durées mesurées.

### Groupe 1 — Obligatoire avant publication v0.2.12 selon les contrats déjà applicables

| Travail | Lacune et gravité | Effort / risque | Preuve minimale | WP | Effet publication |
|---|---|---|---|---|---|
| Fermer le contrat d’intégration API/résultats/sérialisation pour les capacités effectivement retenues | WP11 est OPEN. Ce rapport ne prétend pas avoir audité toutes ses exigences détaillées. | Moyen / risque de rupture de compatibilité si une voie est exposée sans contrat | Matrice des fonctions retenues, schémas et métadonnées versionnés, refus des usages non supportés, tests API et de sérialisation sur le candidat intégré | WP11 | Gate global à traiter; l’API E01 peut être exclue si l’Owner ne la met pas dans le scope |
| Fermer la V&V globale et les performances exigées pour le candidat | WP12 est OPEN; les preuves locales E01 ne remplacent pas les tests du candidat combiné | Moyen à grand / risque de régression ou de périmètre trop large | Exécuter les campagnes précises du contrat WP12 sur le HEAD intégré gelé, inclure les non-régressions et documenter les limites; les critères précis restent sous la gouvernance WP12 | WP12 | Gate global à traiter; ne transforme pas les tests E01 historiques en preuves sur l’arbre intégré |
| Fermer packaging, conformité documentaire et décision Owner de publication | WP13 est OPEN; roadmap : IN_PROGRESS / NOT_RELEASED | Moyen / risque de packaging, de claims et de traçabilité | Dossier release identifié, artefacts reproductibles, statuts/échecs préservés, liste d’exclusions et décision de publication explicitement enregistrée | WP13 | Bloque la déclaration de publication prête selon le ledger actuel |
| Décider si E01 est inclus dans le scope publié | Le roadmap d’octobre le décrit comme objectif expérimental, non comme MUST ajouté rétroactivement | Faible à moyen / risque de communiquer une capacité plus large que la preuve | Décision Owner de scope; si retenu, documentation EXPERIMENTAL/opt-in et claims bornés; si exclu, aucune clôture E01 ne doit être inventée | Owner avec WP11/WP13 | E01 lui-même n’est pas un gate obligatoire selon le texte approuvé; l’inclusion d’une capacité E01 exige le traitement cohérent de son API et de ses limites |
| Examiner les autres WPs ouverts selon leur propre contrat et le scope final | D01/D02 et d’autres WPs sont indiqués ouverts dans le ledger; le dépôt BB ne peut pas décider leurs gates | Variable / risque et effort propres à chaque WP | Chaque propriétaire doit fournir son statut et ses preuves pour les éléments effectivement inclus; une intégration de commit D02 ne constitue pas une clôture | Propriétaires respectifs, avec WP13 | Ne pas inférer leur caractère obligatoire ou facultatif à partir de l’audit E01 |

Le document Owner ne rend pas la clôture de l’ensemble WP-E01 obligatoire pour v0.2.12. La publication doit néanmoins satisfaire les gates v0.2.12 réellement approuvés et ne pas dépasser les claims supportés. La roadmap marque WP11, WP12 et WP13 ouverts; la décision précise concernant D01/D02 et les autres packages reste à leurs propriétaires dans le scope final de release.
### Groupe 2 — Souhaitable, non bloquant pour la publication si E01 reste expérimental

| Travail | Gravité / dépendances | Effort / risque | Preuve minimale utile | WP | Effet publication |
|---|---|---|---|---|---|
| Terminer le diagnostic J2 réduit | P1 pour clôturer A/B comme prévu; dépend de l’oracle fixe-histoire indépendant et de directions libres | Moyen / risque scientifique élevé si l’oracle n’est pas suffisamment indépendant | Exécuter sous nouveau GO le test L sur TET4 et HEX8, directions uniquement libres, historique accepté fixé, branche stable, erreurs absolues/relatives et sweep d’étapes; revue du critère avant tout gel | E01-B/D | N’ajoute pas de gate de release selon la roadmap actuelle; indispensable à une clôture scientifique plus large |
| Démontrer une histoire J2 globale multi-segment | Chargement, déchargement/rechargement, rollback rejeté et commit accepté globaux non réunis dans une seule campagne | Grand / dépend de L et des contrats A/B | Cas TET4/HEX8 borné, états acceptés et provisoires, équilibre indépendant à chaque étape, restart si inclus, preuves sans mutation après rejet | E01-A/B/D | Non bloquant si le support reste experimentalement exclu; nécessaire pour prétendre satisfaire le critère initial de fermeture J2 |
| Résoudre les 3 échecs Hencky-V et le cas initial à charge nulle | P2 de la voie Hencky Newton; dépend du correctif d’identité d’état et d’un vrai nonzero load initial | Petit à moyen / risque d’acceptation fausse si l’identité est relâchée | Diagnostic ciblé des deux assertions et nouvelle fixture chargée; garder l’ancienne preuve 13/16 et ne pas confondre équivalence d’état avec identité d’objet | Extension Hencky / E01-D | Non bloquant si Hencky reste opt-in expérimental et si ses limitations sont publiées |
| Améliorer le gate de convergence tangente Hencky | Les campagnes montrent des régions O(h²), mais le critère minimum-error ne certifie pas un plateau | Moyen / risque de seuil surajusté | Sweep multi-étape gelé, plateau résolu par rapport au plancher roundoff, comparaison analytique indépendante et état NOT_EVALUABLE explicite | Extension Hencky / E01-D | Non bloquant pour un statut borné historique; requis pour toute revendication plus forte |
| Recalcul indépendant de la force contact GF4 | Le bilan BA utilise la contribution de contact issue des points de production | Moyen / dépend de la géométrie/quadrature et du contrat de surface | Reconstituer force et moment depuis pression, positions, aires et poids indépendants; comparer sans appeler l’assembleur testé | E01-E / WP-C02 à coordonner | Non bloquant pour le certificat esclave actuel; requis pour renforcer l’indépendance du bilan |
| Contrat public API/résultats/états E01 | Modules expérimentaux pas intégrés au contrat général WP11 | Moyen / risque d’incompatibilité de résultat ou reprise | Cas d’API, sérialisation, métadonnées et refus; tests de compatibilité contre base WP08–WP10 | WP11/WP12 | Requis seulement pour les fonctionnalités E01 effectivement exposées dans la release; reste à traiter par les gates globaux WP11–WP13 |

### Groupe 3 — Reportable ou hors périmètre de la release actuelle

| Travail | Pourquoi reportable / condition de reclassification | Effort / risque | Preuve minimale si repris | WP | Effet publication |
|---|---|---|---|---|---|
| J2 finite-strain multiplicatif F=FeFp | Explicitement hors périmètre E01 initial et non implémenté | Très grand / très élevé | Formulation, variables internes, tangente cohérente et campagne dédiée | Nouveau WP / future release | Aucun effet si déclaré non supporté |
| Contact frottant couplé à plasticité finite-strain, dynamique plastique générale, post-flambement général | Exclusions explicites du roadmap E01 | Très grand / très élevé | Contrat et V&V propres, Owner scope séparé | WP futur / release future | Aucun effet si exclus explicitement |
| Équilibre du maître rigide et du montage pour le scénario BA | Hors du certificat slave BA, non mesuré indépendamment | Moyen / dépend des réactions et de l’interface de support | Instrumenter ou reconstruire les réactions maître/montage et fermer le bilan complet avec un oracle admissible | E01-E / WP-C02 à coordonner | Aucun effet au certificat slave nommé; obligatoire avant tout claim d’équilibre du système complet |
| Élargir l’échantillonnage du domaine Hencky/TET4/HEX8 | Au-delà des configurations bornées exécutées | Grand / dépend d’une stratégie de domaine | Matrice de déformations, maillages et convergence déclarée | Future extension E01 | Aucun effet si domaine supporté reste restreint/documenté |

Ces groupes ne constituent pas une nouvelle spécification normative. Les seules exigences obligatoires restent celles des contrats Owner approuvés et de la définition de release; une reclassification de l’extension E01 demande une décision Owner.
## 9. État de la branche d’intégration et plan proposé

### 9.1 État observé en lecture seule

| Élément | Résultat |
|---|---|
| Branche | codex/v0.2.12-integration |
| HEAD | 6b17ad538e90b5f63b61a66110a57ba6d479a63d |
| Tree | 4d74385d6171ff139f07cbada7d4bf4a13b36b88 |
| État | Propre au moment de l’inspection |
| WP08/WP09/WP10 | Présents dans l’historique de la branche; WP10 est ancêtre |
| WP-D02 | Le commit D02 est ancêtre de ce HEAD |
| WP-E01 | Le commit scientifique BA 524c15a0355a3033d92f7a723b27e1ca5752d3bd n’est pas ancêtre; les chemins E01 examinés sont absents |
| WP-C02 | Son tip n’est pas ancêtre à ce HEAD |

Le ledger d’intégration local est en retard sur D02 : il indique encore l’absence de D02 alors que son commit est ancêtre du HEAD observé. Le hash de tree 4d74385… est celui de l’HEAD courant; une valeur cccf897… issue d’un parent RBE antérieur a été corrigée par la revue indépendante. Ne pas utiliser le ledger obsolète pour prétendre que D02 manque au HEAD actuel.

La branche E01 cumulative ne doit pas être fusionnée en bloc. Depuis le point commun WP10, elle transporte de nombreux changements historiques multi-WP. BA et C02 ont environ 30 chemins src/solveur modifiés en commun, notamment contact/*, core/assembly/nonlinear.py, core/analyses/geometric_nonlinear.py et les contrôles/solveur nonlinear. Ce constat prouve un chevauchement de chemins et un risque concret de réconciliation; il ne prouve pas à lui seul un conflit textuel dans chacun de ces fichiers.

Un ancien lot de commits nommé WP13 dans cette lignée correspond au travail historique RBE; le WP13 opérationnel actuel est release engineering. Cette homonymie ne doit pas être utilisée pour inférer la clôture du WP13 actuel.

### 9.2 Séquence d’intégration limitée proposée

1. Obtenir le GO Owner d’intégration distinct; ne pas merger depuis BB.
2. Partir de l’HEAD d’intégration réel 6b17ad53…, refaire un inventaire de source path, de commit et de dépendances avec D02/C02/WP08–WP10.
3. Décomposer E01 en sélections minimales et opt-in. Ne pas importer les campagnes, outils, tests ou changements d’autres WPs par la seule présence dans la branche accumulée.
4. Faire la réconciliation trois-voies des quelque 30 chemins partagés BA/C02 contre le vrai HEAD et les branches source; traiter contact GF4/C02 explicitement.
5. Garder les extensions Hencky et les adaptateurs globaux derrière une API expérimentale nommée; ne pas les enregistrer implicitement dans les routes publiques.
6. Laisser WP11 valider l’API, les objets résultat, les états et sérialisation; WP12 fournir les tests intégrés et de non-régression sur l’arbre combiné; WP13 décider du packaging, des claims et des gates de publication.
7. Réexécuter seulement les suites ciblées autorisées sur l’identité intégrée finale. Toute preuve antérieure reste attachée à son ancien hash et ne se transfère pas automatiquement.

Cette proposition n’est ni un plan de merge autorisé ni une garantie de compatibilité. L’inspection BB n’a modifié ni la branche d’intégration, ni C02, ni D02.

## 10. Synthèse opérationnelle compatible roadmap

| WP / capacité | Statut existant ou constat BB | Lecture de maturité |
|---|---|---|
| WP08 | CLOSED_BOUNDED dans la roadmap | Limité au contrat clôturé; ne ferme pas les gaps J2 globaux E01 |
| WP09 | CLOSED_BOUNDED dans la roadmap | Preuves bornées historiques; pas de qualification non linéaire générale |
| WP10 | CLOSED_BOUNDED dans la roadmap | État/checkpoint borné; n’établit pas les transactions E01 supplémentaires |
| WP-D01 | OPEN dans le ledger | Hors décision de clôture E01; garder le statut de son propriétaire |
| WP-D02 | OPEN au ledger de référence, mais code D02 présent au HEAD local d’intégration | Une intégration de commit ne vaut pas clôture; ledger à synchroniser par son Owner |
| WP11 | OPEN | API, résultats, sérialisation et intégration restent un gate à fermer selon son contrat |
| WP12 | OPEN | V&V intégrée/performance à fermer selon son contrat |
| WP13 | OPEN | Release engineering et décision de publication non terminés |
| WP-C02 | Non ancêtre dans l’intégration inspectée | Coordonner avant modification de chemins contact partagés; ne pas inférer son statut Owner |
| WP-E01 original A–E | OPEN / EXPERIMENTAL_TARGET | Recommandation BB : OPEN_WITH_BOUNDED_CERTIFICATES |
| Certificat BA | PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED | Cas GF4 TET4 et équilibre du sous-système esclave uniquement |
| Équilibre maître + montage BA | NOT_VERIFIED | Hors périmètre et preuve manquante |
| Qualification scientifique générale | NOT_ACQUIRED | Aucun changement de statut |
| Release v0.2.12 | IN_PROGRESS / NOT_RELEASED | E01 n’est pas automatiquement un MUST; les gates globaux ouverts demeurent applicables |

## 11. Statuts finaux de l’audit BB

| Domaine | Statut retenu |
|---|---|
| WP-E01 global | OPEN / EXPERIMENTAL_TARGET |
| Recommandation de clôture | B — OPEN_WITH_BOUNDED_CERTIFICATES |
| Certificat GF4 esclave | PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED |
| Certificat Armijo général | NOT_VERIFIED |
| Verdict brut global BA | FAIL préservé |
| Équilibre maître + montage | NOT_VERIFIED |
| J2 assemblé / tangente réduite | BLOCKED_PENDING_INDEPENDENT_EVIDENCE |
| Hencky Newton incrémental | PARTIAL, 13 PASS / 3 FAIL préservés |
| Qualification scientifique générale | NOT_ACQUIRED |
| P0 relevé par la revue indépendante | Aucun |
| Tests ciblés exécutés dans BB | 49 PASS, 0 FAIL; contrats synthétiques/worker uniquement |
| RUN scientifique / Docker / COLLECT | Aucun |
| Merge, tag ou publication | Aucun |

## 12. Décision Owner demandée

Décision requise :

1. Confirmer ou rejeter la recommandation **B — OPEN_WITH_BOUNDED_CERTIFICATES**, en gardant le statut roadmap OPEN / EXPERIMENTAL_TARGET jusqu’à mise à jour explicite.
2. Confirmer si une capacité E01 sera exposée dans v0.2.12 comme cible expérimentale ou exclue du périmètre publié; ne pas traiter le certificat BA borné comme autorisation d’intégration.
3. Si l’intégration est souhaitée, ouvrir un GO distinct pour une sélection minimale depuis E01 vers l’HEAD réel d’intégration, avec réconciliation préalable des chemins partagés C02 et revue par WP11/WP12/WP13.
4. Garder tout futur GO de test ou RUN limité à des identités et scénarios précis; aucune répétition ou promotion automatique des preuves BB.

**Conclusion :** E01 a désormais un résultat physique Newton–Armijo reproductible et utile dans un périmètre étroit, mais il n’a pas satisfait les critères initiaux de clôture complète. La voie correcte est de conserver explicitement le certificat borné, de préserver les FAIL et preuves partielles, puis de laisser l’Owner décider du statut E01 et du périmètre de release.

## Références primaires

- [Roadmap Owner préservée](owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md)
- [Ledger opérationnel](ROADMAP.md)
- [WP-E01-AA — Newton incrémental synthétique](wp_e01_aa_bounded_pipeline_report.md)
- [WP-E01-AB — garde no-FEM](wp_e01_ab_armijo_physical_backtracking_report.md)
- [WP-E01-AL — premier RUN physique](wp_e01_al_run_report.md)
- [WP-E01-AM — diagnostic du worker](wp_e01_am_attribute_error_diagnostic.md)
- [WP-E01-AV — correction instrumentation contact](wp_e01_av_newton_armijo_worker_diagnostic.md)
- [WP-E01-AW — erreur de packaging image](wp_e01_aw_docker_native_fem_vnv_report.md)
- [WP-E01-AX — verdict contact-blind historique](wp_e01_ax_docker_native_fem_vnv_report.md)
- [WP-E01-AY — agrégation fail-closed](wp_e01_ay_balance_aggregation_audit.md)
- [WP-E01-AZ — correction contact-aware](wp_e01_az_contact_balance_correction.md)
- [WP08 — faisabilité constitutive J2](wp08_constitutive_feasibility_report.md)
- [WP09 — robustesse tangente corotationnelle](wp09_tangent_robustness_report.md)
- [WP09 — matrice de régression](wp09_regression_matrix.json)
- [WP-E01-C1 — V&V matériau StVK/Neo-Hookean](wp_e01_c1_finite_strain_and_residual_jacobian_review_2026-10-20.md)
- [WP-E01-DE — revue d’intégration FEM](wp_e01_de_fem_integration_review_2026-10-20.md)
- [WP-E01-D4R — V&V élémentaire directe](wp_e01_d4r_campaign_2026-10-21.md)
- [WP-E01-H — assemblage global et diagnostics](wp_e01_h_supervised_global_assembly_diagnostics_2026-10-21.md)
- [WP-E01-J — diagnostic Decimal et directions faibles](wp_e01_j_j2_high_precision_diagnostics_2026-10-21.md)
- [WP-E01-K — translation rigide](wp_e01_k_j2_translation_verification_2026-10-21.md)
- [WP-E01-L — diagnostic réduit préparé](wp_e01_l_reduced_space_tangent_diagnostic_2026-10-21.md)
- [WP-E01-U/V/W — assemblage Hencky et Newton](wp_e01_uvw_consolidated_report_2026-10-21.md)
- [WP-E01-M — conception Hencky](wp_e01_m_hencky_material_point_design_2026-10-21.md)
- [WP-E01-P3 — vérification matériau Hencky](wp_e01_p3_hencky_verification_2026-10-21.md)
- [WP-E01-S — vérification tangente Hencky](wp_e01_s_hencky_tangent_verification_2026-10-21.md)
- [WP-E01-T — tangente élémentaire Hencky](wp_e01_t_hencky_element_tangent_verification_2026-10-21.md)
- [WP-E01-BA — certificat GF4 borné esclave](wp_e01_ba_bounded_slave_certificate_report.md)
- [WP-E01-A/B — décisions et contrat numérique](wp_e01_owner_decision_d1_d4_2026-10-20.md), [revue numérique](wp_e01_final_numerical_contract_review_2026-10-20.md), [décisions encore ouvertes](wp_e01_final_open_decisions_2026-10-20.md)
