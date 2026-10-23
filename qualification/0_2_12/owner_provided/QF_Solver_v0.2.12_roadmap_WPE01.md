# QF Solver v0.2.12 — Roadmap active et suivi d’avancement

<!-- QFSOLVER_0212_OPERATIONAL_STATUS_SNAPSHOT_2026-10-18 -->

**Dernière mise à jour du suivi : 18 octobre 2026.**  
**Statut de la release : `IN_PROGRESS / NOT_RELEASED`.** Version publique du logiciel au moment du suivi : **v0.2.11**.  
**Nature des preuves :** clôtures et résultats **rapportés dans les échanges Owner/Codex** ; le tableau ci-dessous n'est pas un audit GitHub indépendant du dernier checkout expérimental. Les preuves primaires sont les commits, rapports, archives et décisions Owner cités ci-dessous.  
**Instruction de reprise : lire cette section d'abord.** Le découpage opérationnel WP00–WP13 diffère de la nomenclature **prospective** de l’étude datée du 7 octobre, conservée intégralement dans l'annexe. Ne jamais additionner les deux nomenclatures ou remettre à zéro les clôtures en lisant cette ancienne étude.

## 1. État officiel de travail à reprendre

| Périmètre | Positivement clôturés | Clôture négative | Ouverts | Total | Ratio des clôtures positives |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Avant WP-E01** — suivi opérationnel historique | **11** | **1** | **5** | **17** | **64,7 %** |
| **Après ajout de WP-E01** — 18 octobre 2026 | **11** | **1** | **6** | **18** | **61,1 %** |

**Lecture obligatoire :** les 11 clôtures positives concernent **WP00 à WP10**. `WP-C01 = CLOSED_NEGATIVE` est la clôture négative distincte. Les cinq WP historiquement ouverts sont **WP11, WP12, WP13, WP-D01 et WP-D02**. Le sixième WP ouvert après la décision du 18 octobre est **WP-E01**. **WP-C03 = CLOSED_INCONCLUSIVE** est suivi séparément et n'est pas dans le dénominateur 17/18. Les ratios ci-dessus comptent des WP ; ils ne quantifient ni le temps ni la charge restante.

### Matrice d'avancement opérationnelle — 18 WP

| Identifiant | Fonction dans le suivi opérationnel | État au 18/10/2026 | Précision / suite |
| --- | --- | --- | --- |
| **WP00** | Baseline, périmètre, provenance et décisions Owner | `CLOSED` | Clôture positive historiquement rapportée ; ne pas rouvrir par confusion de nomenclature |
| **WP01** | Contrats, interfaces et invariants | `CLOSED` | Clôture positive historiquement rapportée |
| **WP02** | Système dynamique préparé K/M | `CLOSED` | Clôture positive historiquement rapportée |
| **WP03** | Excitations multiples et phasors | `CLOSED` | Clôture positive historiquement rapportée |
| **WP04** | Base modale et amortissement réduit | `CLOSED` | Clôture positive historiquement rapportée |
| **WP05** | Réponse harmonique réduite | `CLOSED` | Clôture positive historiquement rapportée |
| **WP06** | Newmark modal | `CLOSED` | Clôture positive historiquement rapportée |
| **WP07** | Excitation uniforme de base | `CLOSED` | Clôture positive historiquement rapportée |
| **WP08** | Consolidation J2, contraintes/résultats non linéaires | `CLOSED_BOUNDED` | Acceptation limitée au périmètre borné ; ne vaut pas qualification NL générale |
| **WP09** | Tangentes corotationnelles / robustesse NL | `CLOSED_BOUNDED` | Acceptation limitée ; contrôle des formulations et tangentes sur d'autres périmètres non acquis |
| **WP10** | États internes, checkpoints et convergence NL | `CLOSED_BOUNDED` | Clôture bornée ; ne signifie pas robustesse générale de Newton ni des couplages |
| **WP-C01** | Contact FEM, frottement et convergence spatiale | **`CLOSED_NEGATIVE`** | M2-PLANE : `NUMERICAL_PASS`, stabilité native `NOT_EVALUABLE`, preuve spectrale indépendante positive ; pas de promotion globale ; investigations M3/M4 et contact ouvertes scientifiquement |
| **WP-D01** | Flexibilité résiduelle dynamique | `OPEN` | Clôture non documentée ; distinguer du WP03 *prospectif* de l’étude du 7 octobre |
| **WP-D02** | Contraintes dynamiques | `OPEN` | Clôture non documentée ; distinguer du WP14 *prospectif* |
| **WP11** | Intégration, résultats, API et sérialisation | `OPEN` | Gate d'intégration complet à démontrer |
| **WP12** | Vérification/validation globale et performances | `OPEN` | Campagne ciblée et preuves de non-régression à clôturer |
| **WP13** | Release engineering, packaging et publication | `OPEN` | Aucune publication v0.2.12 autorisée / démontrée |
| **WP-E01** | **Fondations du calcul non linéaire — ajout Owner du 18/10** | **`OPEN — EXPERIMENTAL_TARGET`** | Sous-packages A–E détaillés §3 ; n'est pas une capacité qualifiée |

**Note sur la précision des états :** les 11 clôtures positives et leur ordre WP00–WP10 sont établis par le suivi rapporté. Les libellés ci-dessus sont les domaines de travail mémorisés, et non une reproduction certifiée des intitulés/actes de clôture de chaque commit. Pour un audit formel, retrouver les 11 décisions source et leurs critères avant toute déclaration publique de maturité.

## 2. Dernière avancée scientifique — WP-C01 (18 octobre 2026)

Le WP est **historiquement `CLOSED_NEGATIVE`**, et reste tel quel. Une étude complémentaire sur **`SPATIAL-M2-PLANE`**, maillage M2 de 96 TET4, domaine `EXTENDED_PLANE`, a néanmoins produit **un calcul FEM natif réel, une archive scellée et un audit indépendant des matrices archivées**.

| Observation | Valeur / verdict | Portée exacte |
| --- | --- | --- |
| Solveur natif | `NUMERICAL_PASS` | **Une** tentative native, zéro retry ; pas une qualification globale |
| Résultante normale esclave | `+1000.0000000000033 N` | Référence : 1000 N, erreur relative `3,30e-15` |
| Énergie de déformation | `2.000000000000007 J` | Référence : 2 J, erreur relative `3,55e-15` |
| Contact | `9/9 ACTIVE` | Multiplicateurs strictement positifs, frictionless |
| Équilibre | Erreur relative force `3,41e-15` ; moment `5,24e-15` | Réaction du support rigide **inférée**, non mesurée directement |
| Audit de stabilité **natif** | `NOT_EVALUABLE` | Certificat conservateur creux inconclusif ; ne prouve pas l'instabilité |
| Audit spectral **post-FEM indépendant** | `CERTIFIED_POSITIVE` **pour les matrices archivées** | Noyau de `J` orthonormal, `Kc=ZᵀKffZ`, `Kc` 123×123, `λ_min=599.0513826555 N/m`, `λ_max=4 833 214.2641 N/m`, seuil `4.8332e-6 N/m` |
| Acceptation globale native | `GLOBAL_ACCEPTANCE_NOT_ACQUIRED` | Un `WARNING` de provenance de réaction inférée empêche l'agrégation des gates d'équilibre |
| Exécution | 27,073 s de bout en bout ; 4,1547546 s worker | Une tentative consommée, aucun nouveau lancement autorisé par ces preuves |
| Archive scellée | `PASS_BOUNDED` par reconstruction indépendante | Archive inchangée ; 16 fichiers inventoriés |
| Correctif post-run | Lecteur d'événements `type` corrigé | 55 tests ciblés PASS, sans nouveau FEM |

**Provenance M2 :** HEAD du FEM natif `553da25ec278424dc49b5c3e182e3534dbd3b41c` ; HEAD propre après audit/correctif `17e4d4e8237213e00c86311276e645e1c09501ab` ; archive seal SHA-256 `988a242c91b37439e92b94248bf769838ee555df6ee963f8370e36a1afa1b1b5` ; Kff SHA-256 `8d8434db81c8ebba58b455e490e14236f1e60740d1ab714306e50b7f234e7072` ; J SHA-256 `6dd47b176375194a5d3474afb6dc9752a4ebf3fe011e6b0ccdf7a196d5d0a691`. Rapport local de post-traitement : `qualification/0_2_12/wpc01_m2_postfem_stability_audit.md` ; spectre complet : `qualification/0_2_12/wpc01_m2_constrained_spectrum.json` (dans le checkout expérimental ; non vérifiés directement ici).

**Conséquence :** M2 permet une conclusion **numérique bornée et positive** sur ce cas, sans requalifier rétroactivement l'audit natif ni faire disparaître les défauts historiques de convergence/frottement. **M3 et M4 ne sont pas autorisés** par le rapport M2 ; la convergence multi-maillages reste non démontrée sous un même gel.

**WP-C03 :** suivi hors compteur principal, état `CLOSED_INCONCLUSIVE` ; ne pas en faire un PASS de WP-C01.

## 3. WP-E01 — Nouveau chantier expérimental (décision Owner du 18 octobre)

**Statut : `OPEN — EXPERIMENTAL_TARGET`.** Ajout explicite à la release *comme objectif d'ingénierie*, **sans** acquisition automatique de qualification ou inclusion rétroactive dans le budget MUST du 7 octobre.

| Sous-package | Objectif | État |
| --- | --- | --- |
| **WP-E01-A** | Socle Newton–Raphson incrémental, contrôles de convergence, gestion des incréments et états | `OPEN` — réutiliser l'existant |
| **WP-E01-B** | Plasticité **J2 petites déformations**, retour radial, plasticité parfaite, écrouissage isotrope linéaire, chargement–déchargement | `OPEN` — réutiliser le noyau J2 existant |
| **WP-E01-C** | **Grandes déformations élastiques** : TL, F/E, mesures Piola, tangentes, StVK puis néo-Hookéen | `OPEN` — consolider la voie TL existante |
| **WP-E01-D** | Tests V&V non linéaires indépendants, objectivité, tangentes, convergence et échecs contrôlés | `OPEN` |
| **WP-E01-E** | Intégration FEM TET4/HEX8, API, résultats et limites documentées | `OPEN` |

**Hors périmètre initial :** plasticité J2 **multiplicative à déformations finies** (`F=FeFp`), contact frottant couplé aux grandes déformations plastiques, dynamique plastique générale et post-flambement général. Les routes J2/TL existantes ont une maturité **bornée/expérimentale**, non un `PASS` industriel global. Pour les critères complets de WP-E01, voir §F de l'étude de conception conservée dans la Partie II ci-dessous.

## 4. Plan des étapes restantes — sans réouvrir les 11 clôtures

| Ordre de travail | Chantier | Condition de sortie |
| --- | --- | --- |
| 1 | **WP-C01**, investigation complémentaire | Clarifier la politique du `WARNING` de réaction inférée, exploiter le spectre M2 ; décider séparément toute campagne native M3/M4, sans auto-promotion |
| 2 | **WP-D01 / WP-D02** | Flexibilité résiduelle et contraintes dynamiques : preuves spécifiques + non-régression |
| 3 | **WP-E01 A–E** | J2, grandes déformations élastiques, tangentes, V&V TET4/HEX8 ; `EXPERIMENTAL` seulement |
| 4 | **WP11** | Intégration, API, sortie et contrats de sérialisation des nouvelles fonctionnalités |
| 5 | **WP12** | V&V intégrée, performances et périmètre de support borné |
| 6 | **WP13** | Gates, packaging, docs et décision Owner de publication v0.2.12 |

**Règles de lecture pour les futurs échanges :**

1. **Ne jamais remettre l'avancement à zéro en réinterprétant l'étude du 7 octobre.** Le suivi opérationnel a déjà **11 WP clôturés positivement sur 17**, devenus **11 sur 18** après WP-E01.
2. **Ne pas considérer WP-C01 comme un WP positivement terminé** : la clôture est `CLOSED_NEGATIVE`, même si M2 a produit de nouvelles preuves positives.
3. **Ne pas assimiler `CLOSED_BOUNDED` à une qualification générale** du non-linéaire, du contact ou des dynamiques.
4. **WP-E01 réutilise WP08–WP10, J2 et TL déjà implémentés** : le chantier ajoute des preuves, corrections ciblées et capacités expérimentales ; il ne recrée pas un solveur de zéro.
5. L'étude prospective de la Partie II reste utile pour **architecture, formules, risques et gates**, mais **ses noms/indices WP ne sont pas le suivi des clôtures exécutées**. La matrice opérationnelle ci-dessus prime pour l'avancement.
6. Pour toute décision de qualification/publication, consulter les **preuves primaires** et le HEAD effectif ; les messages et ce document sont un **suivi de décisions**, non une vérification indépendante du checkout local.

---

# Partie II — Étude d'architecture du 7 octobre 2026 (archive prospective)

> Cette section est conservée comme référence technique historique. Ses WP00–WP17, son ordre et ses statuts **représentent la proposition initiale**, pas l'état opérationnel actuel. Référer au tableau **§1** pour les vrais 11/18 et à **§3** pour le WP-E01 décidé le 18 octobre.

# QF Solver v0.2.12 — étude d’architecture et proposition de release

**Date : 7 octobre 2026. Statut : proposition d’ingénierie, sans implémentation. Révision : ajout du volet non linéaire demandé.**

> **Mise à jour de roadmap — décision Owner du 18 octobre 2026 :** ajout de **WP-E01 — Fondations du calcul non linéaire**. Cet ajout est une cible de développement expérimental pour v0.2.12 ; il ne modifie pas les constats datés du 7 octobre, les statuts historiques de WP09/WP-C01 ni les preuves de qualification.

**Recommandation actualisée : dynamique structurale réduite, excitations enrichies et mise à niveau nécessaire du non linéaire existant.** Réutiliser une base modale pour calculer des réponses harmoniques et transitoires, introduire les charges harmoniques déphasées et l’accélération uniforme de base, et expliciter l’erreur de troncature. Cette proposition développe une chaîne mécanique cohérente : **modèle → opérateurs → base → excitation → réponse → observables**. Elle réserve aussi un bloc obligatoire aux contrats de contraintes, à la fiabilité des tangentes et aux états/convergences des routes non linéaires existantes. Ce bloc représente **+30–45 unités**, soit environ **23–31 % du MUST révisé**, sur la base de coût initiale de 100 unités. Ces chiffres sont des estimations de planification.

Le scénario rotordynamique constitue une alternative sérieuse, surtout si un besoin utilisateur immédiat porte sur les réponses au balourd. Il n’est cependant pas le meilleur choix général sur le code actuel : il cumulerait une nouvelle formulation gyroscopique de poutre, l’amortissement/paliers, une réponse forcée et un traitement spectral plus scalable. La dynamique non linéaire est encore plus coûteuse et risquée.

La recommandation n’est pas une conclusion universelle sur les besoins du projet. Elle maximise ici la couverture des usages mécaniques, la réutilisation du code et la maîtrise du périmètre. Un engagement prioritaire envers un utilisateur de rotordynamique pourrait inverser ce choix.

## Méthode, identité et limites de l’audit

### Snapshot réellement examiné

| Objet | Identité vérifiée |
| --- | --- |
| Repository | `emptiesvoid-cloud/QF_solver` |
| `main` lors de la collecte | `e367fe58b2b9ebb4aef321424ca775e80e82d9ca` |
| Commit cible du tag annoté `v0.2.11` | `afd2efa469a18e66581720ff4801f50de7d29eb4` |
| Commit cible de `v0.2.10` | `e535ff63464ddd7d76c2898df25470350b5154f1` |
| Commit cible de `v0.2.9` | `3e016a11ebff054c6aabb22ec76c2b0a1e247035` |
| Commit cible de `v0.2.8` | `c8f202d504fd26f66e12fbbc9a754a273ffbde07` |

Le code de `src/solveur/` et `src/qf_solver/` est identique entre le tag v0.2.11 et ce `main`. Les changements postérieurs au tag concernent notamment la gouvernance de publication, les métadonnées, leurs tests et la documentation. La release GitHub v0.2.11 est publiée, non brouillon et non préversion ; l’API GitHub donne le 7 octobre 2026 à 13:58:55 UTC comme date de publication.

Le fichier `publication_verification_0_2_11.json` enregistre aussi des contrôles PyPI/Zenodo et le DOI `10.5281/zenodo.23214487`. **Ces contrôles externes sont ici lus dans le dossier, pas réexécutés.** La publication GitHub et les références Git ont été vérifiées directement. [S01, S02]

L’étude repose sur une copie de lecture séparée, l’historique Git, les noyaux numériques, les validations d’entrée, les tests et les décisions de qualification. Aucun code du repository n’a été modifié. Aucune branche de développement, aucun commit, issue, PR ou tag n’a été créé ; aucune implémentation n’a été commencée.

### Niveau de preuve utilisé

- **Fait vérifié** : observé dans le code, une référence Git, ou une exécution locale décrite ci-dessous.
- **Preuve historique** : résultat enregistré dans le repository, avec son environnement et son scope ; elle n’est pas présentée comme un nouveau résultat d’exécution.
- **Calcul** : déduit d’une formule ou des dimensions des objets.
- **Estimation** : score de décision ou charge relative ; ce n’est ni une mesure de productivité ni une probabilité statistique.
- **Proposition** : API, module, seuil ou comportement à concevoir. Aucune API proposée ci-dessous n’existe du seul fait qu’elle est nommée dans ce rapport.

### Exécutions de contrôle

**118 tests ciblés passent, sans échec** : 66 sur disques, préflight rotatif, Campbell, suivi modal, contrôles/conditions initiales/checkpoints Newmark et API rotative ; 52 sur plans d’assemblage, matériaux, TL TET4/HEX8, J2 corotationnel, contrats géométriques, transactions d’état et post-traitement harmonique de coques. Environnement : Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, BLAS limité à un thread. Ce n’est pas l’environnement historique de qualification. Les deux lots prennent respectivement 5,48 s et 7,33 s selon pytest.

Deux diagnostics supplémentaires ont été exécutés sans changer les sources :

1. Sur la fixture transitoire TET4 existante, ajouter une masse concentrée de **100 kg** ne change pas la signature de checkpoint ; pourtant `||ΔM||F = 173,205`. Ajouter un ressort de **100 N/m** ne change pas cette signature non plus ; `||ΔK||F = 100`. C’est une omission confirmée dans l’identité physique, pas une hypothèse de lecture.
2. Instrumenter l’assemblage existant sur un Campbell à **3 vitesses** donne **6 appels** à `assemble_stiffness_and_mass`, avec `numerical_status=PASS`.

La suite complète, Code_Aster, CalculiX, PETSc/MPI, les grandes campagnes de maillage et les assets publics wheel/sdist n’ont pas été réexécutés. L’audit couvre les chemins centraux et leurs preuves pertinentes ; il ne constitue pas une revue ligne par ligne de tout le repository ni une qualification du solver. **On ne peut pas conclure avec les informations disponibles à une exactitude générale, à une performance industrielle ou à une équivalence Abaqus.**

## A. État actuel de QF Solver

### A1. Architecture et frontières effectives

Le routeur expose **9 familles** : `linear_static`, `modal`, `nonlinear_static`, `geometric_nonlinear_static`, `linear_buckling`, `transient_dynamic`, `harmonic_response`, `rotating_modal`, `campbell`. La façade recommandée est `qf_solver`; l’implémentation est principalement sous `solveur`. Les anciens modules tels que `core/dynamic.py` ou `core/solver.py` sont des aliases de compatibilité : leur présence ne prouve pas une duplication de noyaux. [S03–S05]

L’organisation est déjà exploitable : analyses, assemblage, solveurs, éléments, matériaux, charges, contact, IO, post-traitement et voie `large` sont séparés. Les couches historiques de vérification restent nombreuses. Inventaire de fichiers réguliers du snapshot : **484** sous `src/solveur`, **656** sous `tests`, **2 873** sous `qualification`, **1 241** sous `docs`. Ce comptage inclut les ressources, pas seulement les fichiers Python ; il ne mesure pas la qualité.

**Force :** la séparation API/CLI/noyaux existe ; une nouvelle capacité peut être ajoutée sans déplacer tout le code. **Faiblesse :** plusieurs analyses réassemblent leur propre système et reconstruisent leurs contrôles. Une abstraction ciblée de système dynamique préparé peut servir plusieurs calculs. Une refonte globale serait disproportionnée.

La télémétrie du routeur n’instrumente explicitement que statique linéaire et modal dans sa phase 1. L’étendre aux nouvelles routes est utile ; en faire un chantier global de télémétrie ne définit pas une grosse release mécanique. [S03]

### A2. Matrice de capacités observées

| Domaine | Ce qui existe effectivement | Limite structurante pour la suite |
| --- | --- | --- |
| Éléments | BEAM2 Timoshenko 3D ; MITC3/MITC4 ; TET4/TET10/HEX8/HEX20 ; WEDGE6 ; PYRAMID5 interne/recherche | Disponibilité de l’élément ≠ qualification de chaque analyse ; WEDGE15 absent ; HEX8-SRI distinct et expérimental |
| Statique linéaire | Assemblage sparse, charges distribuées, entités discrètes, contraintes et solveurs directs/itératifs | Scope qualification défini par combinaison ; HPC générique non démontré |
| Modal classique | Problème généralisé symétrique réel ; dense borné, eigsh/Lanczos/LOBPCG et intégrations optionnelles | Difficultés historiques sur certains grands cas MITC4 ; pas de modal sur état précontraint public général |
| Transitoire | Newmark linéaire, masse cohérente, Rayleigh, histories multiples, sondes, mode summary, reprise et factorisation réutilisée | Pas de transitoire non linéaire ni d’explicite public ; condensation drilling avec `rayleigh_beta>0` rejetée ; signature de reprise incomplète |
| Harmonique | Résolution sparse complexe directe par fréquence ; Rayleigh ; post-traitement de contraintes de coques | La force assemblée est un vecteur réel unique ; pas de canal public de phases indépendantes ; pas de superposition modale exposée |
| Géométrie non linéaire | TL/StVK et tangentes, campagnes TET4/HEX8, noyaux high-order | Route publique homogène en famille/matériau ; charges nodales mortes ; pas de follower général ni de promotion automatique |
| Constitutif | Élasticité isotrope/orthotrope, stratifiés, élasticité non linéaire cubique, J2 isotrope avec retour radial | J2 petites déformations ; J2 corotationnel à petites déformations locales ; pas de plasticité multiplicative générale |
| Non-linéaire global | Newton, line search, pas adaptatifs, transactions, checkpoint, continuation/arc-length spécialisé | Couplages limités ; interface commune ≠ toutes physiques composables ; arc-length n’établit pas un suivi général de bifurcation |
| Contact | Node-to-triangle, patches expansés en contributions nodales ; pénalité sans frottement ; route active-set et stick/slip spécialisée | Sensibilité maillage ; requalification actuelle frottante non établie ; pas de mortar ; updated search/finite sliding implémentés sur des chemins bornés, sans qualification générale |
| Rotating modal | Disques rigides axisymétriques, G antisymétrique, QEP conservatif dense, résultats complexes | Gyro d’arbre distribué absent ; pas d’amortissement, précontrainte, balourd ou backend sparse ; scope BEAM2 rectiligne |
| Campbell | MAC complexe, assignment global, sous-espaces dégénérés, lineage et ambiguïtés explicites | Réassemblages et stockage coûteux ; grille explicite 2–101 vitesses ; ambiguïté 100 rad/s préservée |
| IO | JSON, Gmsh, subset `.inp`, NPZ checkpoints, HDF5 mixte optionnel | `.inp` mappe C3D4/C3D6/C3D8, pas tout Abaqus ; HDF5 mixte scope TET4/WEDGE6/HEX8 ; pas de format universel de tous résultats |
| Résultats/post | Classes statique/modal/transitoire/harmonique/rotatives ; sérialisation complexe explicite ; VTU, CSV, récupération mécanique | Contrats et statuts hétérogènes ; VTU orienté état statique ; historique sondé déjà présent en transitoire, responses complets stockés en harmonique |
| Performance | Assemblage K/M pairé en chunks, accumulator CSR pairwise, plans, telemetry temps/mémoire ; voie TET4 grande taille | LU/historiques/base modale/QEP ont des coûts différents ; succès TET4 historique non transférable aux autres voies |

Sources : code des analyses, registre éléments, lois, validation des charges et limites actuelles. [S06–S18, S25–S29]

### A3. Points techniques à ne pas mal interpréter

**La dynamique n’est pas vide.** `DynamicDofReducer` réalise une condensation de coordonnées de drilling sans masse ; ce n’est pas une réduction modale. Newmark réutilise déjà la LU effective quand la voie directe SciPy le permet. Les charges multiples et le Rayleigh ajusté sur deux cibles existent. Les ajouter à la roadmap comme nouveautés serait faux. [S08, S09, S17]

**La non-linéarité est substantielle, mais bornée.** L’acceptation formelle WP09 R3 concerne HEX8 corotationnel J2, petites déformations locales. Des extensions HEX20/TET10 sont acceptées avec limitations, sans score supplémentaire et sans solveur FEM/Newton indépendant global. Une mise à jour de l’observable à partir du résultat QF n’est pas une résolution indépendante du problème. Le TL/StVK garde une classification de recherche et des décisions bornées ; le code géométrique renvoie lui-même `maturity='research'`. [S10–S12, S21, S22]

**Le noyau corotationnel a un coût précis et une convention spécifique.** Il calcule F=RU par SVD, utilise la déformation locale U−I, transporte l’état accepté entre repères, puis forme P=Rσlocal. Sa tangente élémentaire est calculée par différences centrales, à état accepté fixé, puis symétrisée. Pour d DDL locaux, un appel force+tangente appelle le noyau complet de force **1+2d fois** : **49 pour HEX8**, **121 pour HEX20**. Ce comptage n’est pas un facteur de ralentissement mesuré, mais il identifie un coût structurel avant d’étendre cette cinématique au transitoire. WP16 traite désormais la fiabilité de cette tangente numérique ; son remplacement complet par une tangente analytique reste un chantier ultérieur. [S31]

Une autre limite de réutilisation apparaît dans les résultats de ce noyau : le champ `second_piola_stress` recopie σlocal. Avec F=RU et P=Rσlocal, la transformation exacte donnerait S=F⁻¹P=U⁻¹σlocal. Le champ stocké ne représente donc pas exactement cette mesure à étirement fini ; l’écart s’annule pour U=I et reste lié à l’approximation de petites déformations locales. **Ne pas réutiliser ce libellé comme preuve d’une formulation finite-strain ni comme entrée générale de précontrainte.** Cette observation de code et d’algèbre ne chiffre pas son effet sur les cas acceptés ; elle justifie désormais le contrat de mesures de contraintes obligatoire de WP15 dans cette proposition révisée de v0.2.12. [S31]

**Le contact n’est pas absent ni général.** Les patches sont transformés en contributions node-to-surface, non en mortar. Les modes `updated`/`finite_sliding` existent dans la pénalité sans frottement, alors que la route frottante rejette la recherche actualisée. Les capacités implémentées doivent être distinguées des frontières qualifiées. La fiche historique WP01 de v0.2.11 cite des deltas de glissement de **24,883 % et 24,541 %** entre maillages et une requalification formelle actuelle non établie. Ces nombres sont des preuves historiques lues, non de nouveaux calculs. [S13, S23]

**Le QEP conservatif ne devient pas amorti en ajoutant C.** Le solveur actuel impose M/K définies positives, G antisymétrique, contrôle des parties réelles quasi nulles et appariement spectral conservatif. Ajouter l’amortissement exige une nouvelle définition des contrôles et des modes sélectionnés ; supprimer un gate existant pour faire passer le modèle serait incorrect. [S14]

**Une intersection Campbell 1× n’est pas une amplitude ni une dangerosité.** Le problème forcé nécessite charges, amortissement et observables. Le post-traitement actuel conserve les trous ambigus ; la v0.2.12 doit conserver cette propriété si elle modifie cette voie. [S15, S16, S24]

### A4. Releases précédentes : apports et lecture de l’ambition

| Cycle | Apport établi | Travail entamé ou limite laissée ouverte |
| --- | --- | --- |
| v0.2.8 | Workflows mixtes TET4/WEDGE6/HEX8 statique/modal/MPC translation/multimatériau ; Newmark/harmonique mixtes expérimentaux ; subset INP, HDF5 mixte, contact et SRI bornés | Mixte distribué NOT_VALIDATED ; dynamique mixte expérimentale ; PYRAMID5 interne ; pas de généralisation des coques et contacts |
| v0.2.9 | Tag de source du grand cycle Newton/états/continuation, géométrie, J2 corotationnel, contact/friction, extensions et diagnostics | **Pas une release publique intermédiaire** ; gates/qualifications incomplets et échecs préservés |
| v0.2.10 | Publication et présentation des travaux depuis la dernière release publique v0.2.8 ; API et limites clarifiées ; artefacts sélectionnés audités | Beaucoup du code vient du cycle 0.2.9 ; G03 archive FAIL_PRESERVED et WP14 HOLD_NOT_PROMOTED ; pas de dynamique NL générale |
| v0.2.11 | Rotating modal et Campbell expérimentaux ; provenance et reprise V&V prospective ; surfaces de publication consolidées | Disques seulement ; QEP dense ; gyro arbre, balourd, amortissement absents ; ambiguïté haute fréquence 100 rad/s |

Diffs Git **limités à `src/solveur` et `tests`**, tous fichiers inclus : 0.2.7→0.2.8 : 86 fichiers, +8 456/−68 lignes ; 0.2.8→0.2.9 : 192, +37 288/−1 154 ; 0.2.9→0.2.10 : 14, +412/−48 ; 0.2.10→0.2.11 : 47, +4 691/−88. **Ces volumes ne mesurent ni la valeur mécanique ni le coût.** Ils montrent surtout pourquoi comparer littéralement 0.2.12 au delta 0.2.9→0.2.10 serait trompeur. [S01]

Le bon objectif est une profondeur comparable de workflow utilisateur, pas un nombre de lignes ou de WPs. La proposition recommandée ouvre deux nouveaux modes de résolution et deux catégories d’excitation sur une même chaîne ; elle dépasse une release corrective.

## B. Opportunités v0.2.12

### Échelle et tableau comparatif

Notes **1–5**. V = valeur utilisateur, S = valeur scientifique pour la mécanique/numérique, D = différenciation, C = coût d’implémentation, A = risque architectural, N = risque numérique, T = coût de validation ciblée. Une note élevée est favorable pour V/S/D, défavorable pour C/A/N/T. La valeur scientifique ne signifie pas nouveauté de recherche. Les notes sont des **estimations argumentées**, pas des métriques vérifiées.

| Axe concret | V | S | D | C | A | N | T | Dépendances et justification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Superposition modale harmonique/transitoire | 5 | 3 | 3 | 3 | 3 | 3 | 3 | K/M, base normalisée, projections, reconstruction ; bénéficie à plusieurs familles existantes |
| Excitation uniforme de base | 4 | 3 | 3 | 2 | 2 | 3 | 2 | Masse complète et repère relatif/absolu explicite ; manque fonctionnel utile |
| Forces harmoniques complexes/multientrées | 4 | 2 | 2 | 2 | 2 | 2 | 2 | IO strict des phasors et charge spatiale existante ; l’harmonique actuel n’expose pas les phases indépendantes |
| Flexibilité résiduelle harmonique | 4 | 4 | 3 | 3 | 2 | 4 | 3 | Base et K inversible dans scope ; corrige le résidu statique sans prétendre résoudre tous les modes omis |
| Generalized-alpha linéaire | 3 | 4 | 3 | 3 | 3 | 3 | 3 | Convention d’interpolation des forces et état/reprise ; dissipation numérique contrôlable |
| Transitoire implicite J2 petites déformations | 5 | 5 | 4 | 5 | 4 | 5 | 5 | M, Newton dynamique, commit/rollback, énergie et reprise ; plus qu’un appel du Newton statique à chaque pas |
| Plasticité multiplicative finite-strain | 3 | 5 | 4 | 5 | 5 | 5 | 5 | Nouvelle loi objective, tangente et état ; peut être une release dédiée |
| Contact surface/updated search généralisé | 4 | 5 | 4 | 5 | 5 | 5 | 5 | Recherche, normales, tangentes, transitions et frottement ; dette actuelle importante |
| Explicite central differences | 4 | 4 | 3 | 5 | 4 | 5 | 4 | Masse diagonale admissible, pas critique, stabilité/énergie ; masse lumped actuellement rejetée |
| Gyro d’arbre BEAM2 distribué | 4 | 5 | 4 | 4 | 3 | 5 | 4 | Interpolation rotative cohérente avec la masse de poutre actuelle ; oracle indépendant indispensable |
| Réponse rotor amortie au balourd | 4 | 4 | 4 | 4 | 4 | 4 | 4 | C/paliers, force centrifuge déphasée, opérateurs rotor ; scope disques possible mais incomplet pour arbres lourds |
| QEP sparse ciblé | 3 | 4 | 3 | 4 | 4 | 4 | 4 | Shift-invert, extraction partielle, résidus polynomial et tracking ; change le contrat de spectre complet |
| Modal autour d’un état précontraint | 4 | 5 | 4 | 4 | 4 | 4 | 4 | Équilibre accepté et tangente physique ; fondations TL/buckling existent mais restent étroites |
| WEDGE15/nouvelles familles d’éléments | 3 | 3 | 2 | 4 | 3 | 4 | 4 | Géométrie/charges/masses/post/IO à étendre ensemble ; pas le meilleur effet de levier aujourd’hui |
| Système dynamique préparé et réutilisation | 4 | 2 | 2 | 3 | 3 | 2 | 2 | Identité physique forte et scope ; indispensable à une base modale réutilisable |
| Optimisation globale MPI/GPU/assemblage | 3 | 4 | 3 | 5 | 5 | 4 | 5 | Workloads concrets absents pour généraliser les gains ; ne pas confondre voies `large` et standard |
| Résultats sondés et contrats d’observables | 4 | 2 | 3 | 2 | 2 | 2 | 2 | Historique sondé déjà existant ; gain additionnel surtout en harmonique/reconstruction réduite |
| Nouvelle bibliothèque globale de V&V | 3 | 4 | 2 | 5 | 3 | 2 | 5 | Très pertinente pour 0.3.0 ; contraire au thème demandé pour 0.2.12 |

Les opportunités les plus rationnelles combinent **base modale + réponses + excitations + observables**. Le système préparé est une dépendance de ce thème, pas une justification autonome d’une release « nettoyage ».

## C. Quatre scénarios cohérents

**Base de coût conservée pour comparer les scénarios initiaux : le MUST dynamique du scénario A = 100 unités relatives.** Le scénario retenu après ajout demandé est **A+NL = 130–145 unités** ; les comparaisons initiales ci-dessous restent celles des scénarios avant cet ajout. Les plages des autres scénarios expriment une estimation de travail total, tests directement nécessaires inclus. Elles ne proviennent pas de chronométrages d’implémentation. Aucun délai calendrier crédible ne peut être déduit sans cadence, disponibilité et budget de calcul.

| Scénario | Périmètre définissant la release | Bénéfices / impact | Coût relatif estimé | Risque / complexité | Cohérence |
| --- | --- | --- | --- | --- | --- |
| **A — Dynamique réduite et excitations** | Système préparé ; base modale ; harmonic/transient par projection ; amortissement modal/Rayleigh ; correction statique harmonique ; phases multiples ; base uniforme | Rend plusieurs analyses existantes réutilisables pour sweeps et charges ; portée structures solides et poutres ; apporte amplitudes/temps, pas seulement fréquences | **100**, plage de sensibilité 80–150 | Moyen ; complexité 3/5 ; troncature, identités, reconstruction | **5/5** ; une chaîne mécanique, une base partagée |
| **B — Rotor linéaire forcé** | Gyro distribué BEAM2 ; paliers linéaires passifs ; réponse harmonique/balourd ; système rotor préparé ; optimisation Campbell | Extension physique naturelle de 0.2.11 ; intéressante pour arbres dont l’inertie distribuée compte et études au balourd | **130–190** | Élevé ; 4/5 ; formulation de poutre rotative et références ; QEP dense reste un plafond | **5/5** ; très ciblée, moins large en utilisateurs |
| **C — Dynamique non linéaire implicite** | Newmark NL petites déformations J2 sur TET4/HEX8 ; Newton avec K effective ; états/reprise ; adaptation du pas ; bilan énergétique | Capacité mécanique forte, extension du travail 0.2.10 ; réponse plastique transitoire | **170–250** | Élevé ; 5/5 ; histoire constitutive, temporalité, convergence et dissipation | **5/5**, si contact, géométrie finite-strain et explicite sont exclus |
| **D — État préchargé et analyses incrémentales** | État d’équilibre TL élastique accepté ; export/reprise de cet état ; tangente ; modal précontraint ; cohérence buckling/preload | Chaîne statique→modal physiquement utile ; pont vers stabilité et machines | **115–175** | Moyen à élevé ; 4/5 ; tangente matérielle/géométrique, configuration de M et scope StVK | **4/5** ; forte, mais états historiques étroits |

### Périmètres à conserver propres

**B :** ne pas ajouter automatiquement QEP sparse, modal amorti général et rigidification centrifuge. Une réponse forcée passive peut être ajoutée avec C sans changer immédiatement le QEP conservatif ; elle doit alors garder un domaine distinct du Campbell non amorti. Coefficients de paliers constants, symétriques et passifs seulement ; pas de roulements hydrodynamiques cross-coupled ni d’instabilité générale. Un noyau gyro BEAM2 ne peut pas être copié sans justification d’interpolation : la masse actuelle combine Hermite transverse et rotations indépendantes. [S07, S14]

**C :** commencer par une seule cinématique, masse constante et charges mortes. Le résidu doit contenir `M a + C v + f_int(u,state) - f_ext`; la tangente effective et la transaction d’état doivent correspondre au même instant. Exclure contact/impact au départ. Mélanger immédiatement J2, grandes rotations et contact ferait sortir le scénario de sa plage de charge.

**D :** ne pas présenter une interpolation `K0 + αKg` de buckling comme la tangente complète de tout équilibre fini. Le code de flambement dispose d’une décomposition d’initial stress bornée ; la réutilisation dans le modal nécessite une définition propre de la configuration et des états. [S18]

### Sensibilité du choix

- Besoin principal : nombreuses excitations sur une structure linéaire et plusieurs familles → **A**.
- Livrable prioritaire déjà engagé : rotor/balourd à court terme → **B** peut devenir premier.
- Problème prioritaire : transitoire plastique irréductible à un modèle linéaire → **C**, en acceptant une charge nettement supérieure.
- Besoin prioritaire : variation de fréquences sous charge statique → **D**.

Sans cette contrainte d’usage spécifique, **A** offre le meilleur rapport portée/coût/risque. La seule nouveauté récente de la rotordynamique ne suffit pas à imposer B.

## D. Architecture recommandée

### D1. Définition de la release

**v0.2.12 = réponses dynamiques linéaires réduites, excitations enrichies, réutilisation sûre des opérateurs et de la base, et fiabilisation bornée du non linéaire statique existant.**

La release comporte deux livrables mécaniques explicites. Le premier ajoute des réponses linéaires réutilisables. Le second corrige les contrats et traite les faiblesses numériques identifiées du non linéaire avant de construire de nouveaux couplages dessus. La base modale linéaire n’est pas utilisée pour approximer une réponse plastique ou une tangente évolutive.

Le **bloc dynamique du MUST** supporte, dans des combinaisons explicitement testées, les éléments solides **TET4/TET10/HEX8/HEX20** et **BEAM2**, les matériaux élastiques isotropes, les conditions fixes homogènes et les ressorts/masses concentrées sans excentricité sur DDL déjà présents. Exclure contacts, MPC/RBE, rotors, follower loads, états précontraints et directions sans masse. Un cas simple par famille exerce la nouvelle intégration ; il ne requalifie pas la famille entière.

Les coques, stratifiés, matériaux orthotropes et modèles mixtes peuvent continuer à utiliser leurs routes existantes. Leur accès aux **nouvelles** méthodes reste rejeté tant que le WP optionnel correspondant n’est pas clos. Cette frontière évite d’intégrer par accident les problèmes de condensation drilling dans le MUST.

### D2. Objets et responsabilités proposés

| Objet proposé, interne sauf mention | Responsabilité | Ne doit pas faire |
| --- | --- | --- |
| `PreparedDynamicSystem` | Snapshot de modèle, DDL libres, K/M sparse, règle d’amortissement, reconstruction, empreinte structurale | Garder une référence mutable au modèle ou une LU globale non bornée |
| `ModalBasis` | Φ, valeurs propres, métriques M-orthogonalité, identités et domaine | Confondre modes propres et autorisation de toutes analyses |
| `ExcitationChannels` | B spatial, amplitudes réelles temporelles ou complexes fréquentielles, unités et repères | Supposer que toutes les forces sont en phase ou changer silencieusement les index historiques |
| `ReducedResponseOperators` | Mr/Kr/Cr et projections des forces ; solveurs de coordonnées modales | Inventer des termes gyroscopiques ou oublier les couplages d’amortissement |
| `ResponseObservation` | Déplacement/vitesse/accélération, relative/absolue si base, observables signées et sélection des sorties | Promouvoir la maturité ou masquer une troncature derrière numerical PASS |

Proposition de modules sous `core/analyses/` : `prepared_dynamic_system.py`, `modal_basis.py`, `modal_response.py`, `dynamic_excitation.py`, `residual_flexibility.py`. Les noms exacts peuvent évoluer au design. Réutiliser `assembly/assembler.py`, `analyses/modal.py`, `dynamic_controls.py`, les solveurs et les sérialisateurs. Ne pas créer un framework général de plugins mécaniques.

### D3. Formulation et erreurs à distinguer

Dans le scope à coordonnées inertielles retenues :

\[
M\ddot u+C\dot u+Ku=Bf(t),\qquad u\approx\Phi q.
\]

\[
M_r=\Phi^T M\Phi,\quad K_r=\Phi^T K\Phi,\quad C_r=\Phi^T C\Phi,
\quad B_r=\Phi^T B.
\]

Avec modes mass-normalisés, Mr≈I et Kr≈diag(ω²). **N’imposer la diagonalisation de C que si le contrat le permet.** Pour Rayleigh, `Cr=αMr+βKr`; pour un amortissement modal prescrit, il définit le modèle réduit `diag(2ζjωj)` et ne prétend pas identifier une matrice physique complète C. Dans un sous-espace dégénéré, des ζ différents dépendraient du choix arbitraire de base : exiger un même ζ par cluster ou une loi invariantement définie.

Harmonique, convention explicite `Re(U exp(iωt))` :

\[
(-\omega^2M_r+i\omega C_r+K_r)Q=\Phi^T F(\omega),\qquad U=\Phi Q.
\]

Correction statique harmonique, K inversible dans le scope :

\[
R_s B=K^{-1}B-\Phi K_r^{-1}\Phi^T B,\qquad
U(\omega)\approx\Phi Q(\omega)+R_sF(\omega).
\]

Calculer les vecteurs de correction par RHS, jamais K⁻¹ dense. Ce terme restitue la contribution statique des modes omis ; il ne restitue pas leur résonance. **Ne pas appliquer automatiquement cette correction au transitoire** : ses dérivées affecteraient vitesse/accélération, surtout sous impulsion ou histoire non lisse.

Séparer obligatoirement : résidu de l’eigensolve, erreur de projection/troncature, erreur temporelle, erreur de reconstruction/post et erreur du modèle mécanique. Une masse participante élevée ne garantit pas les contraintes locales ni la bonne réponse à une charge locale. Une norme de résidu complète peut rester non nulle pour une approximation modale correcte et doit être interprétée avec l’erreur de troncature, pas avec un gate de résolution directe copié tel quel.

### D4. MUST / SHOULD / COULD

| Priorité | Contenu |
| --- | --- |
| **MUST HAVE** | Identité physique complète et reprise sûre ; système préparé ; base modale réutilisable ; Rayleigh ou amortissement modal explicite ; harmonic modal et correction statique optionnelle ; transient modal Newmark à pas constant ; phasors multientrées ; accélération uniforme de base ; sorties/provenance/erreur de troncature ; non-régression et publication sélectionnée ; **WP15–WP17 : mesures de contraintes NL, tangentes corotationnelles et contrats d’états/convergence/scope** |
| **SHOULD HAVE** | Generalized-alpha linéaire ; extension des nouvelles méthodes aux coques avec condensation justifiée ; post contraintes solides sur fréquences/instants sélectionnés ; optimisation Campbell par système invariant préparé si elle reste séparée |
| **COULD HAVE** | Auto-suggestion du nombre de modes sur deux troncatures et coût borné ; export compact versionné de base ; enrichissement par vecteurs de Ritz pour une charge ciblée après étude séparée |

Le MUST révisé inclut les deux blocs : les corrections NL nécessaires ne sont pas un SHOULD retirable. Le SHOULD est retirable en blocs ; le COULD n’est jamais un gate. Avec cet ajout, limiter les options à **+15–20 unités** sur la base initiale de 100, et choisir au maximum une extension après clôture des deux blocs. Les nouveaux développements NL larges ne sont pas ajoutés à ce budget.

### D5. Volet obligatoire — mise à niveau du non linéaire

**Objectif : rendre les capacités existantes plus sûres et plus explicites avant de les étendre.** La présence de Newton, line search, cutbacks et états trial/commit/rollback est déjà vérifiée ; les réintroduire sous de nouveaux noms ne serait pas une amélioration. Le travail porte sur les lacunes précises suivantes. [S10–S12, S21–S22, S31]

| Constat dans le snapshot | Nature du constat | Mise à niveau 0.2.12 |
| --- | --- | --- |
| Le noyau corotationnel stocke σlocal sous `second_piola_stress`, alors que ses propres F et P donnent S=F⁻¹P | Incohérence de mesure/libellé vérifiée ; effet sur cas acceptés non quantifié | Mesures et repères explicites ; transformation cohérente ; évolution de sérialisation versionnée ; WP15 |
| Tangente corotationnelle par différences centrales puis symétrisation | Algorithme vérifié ; une mauvaise convergence n’est pas démontrée par cette seule lecture | Vérification directionnelle indépendante du pas de production ; comparer dérivée brute et tangente retournée ; corriger les écarts observés ; WP16 |
| Pas de différences finies dépendant de `max(abs(coords))` | Dépendance à l’origine du repère vérifiée ; impact numérique à mesurer | Échelle fondée sur géométrie relative et unités ; contrôles de translation du maillage et de variation de pas ; WP16 |
| Une tangente mobilise 49 évaluations de force HEX8 et 121 HEX20 | Comptage algorithmique, pas facteur de temps mesuré | Compteurs/coûts séparés ; garder l’optimisation analytique pour un bloc ultérieur si nécessaire ; WP16 |
| États transactionnels, reprise et garde de cinématique déjà présents | Fondations existantes ; absence de sûreté globale non démontrée | Renforcer les cas limite : essai rejeté, reprise, inversion, limite locale et échec contrôlé ; WP17 |
| Corotation J2 à petites déformations locales ; TL/StVK et extensions high-order bornées | Limites de formulation et de qualification vérifiées | Matrice de scope commune aux entrées, résultats et docs ; pas de claim de plasticité multiplicative ; WP17 |

**Scope retenu :** non linéaire statique solide déjà disponible, avec priorité HEX8 corotationnel J2 et petites déformations J2. Lorsqu’un noyau partagé est modifié, couvrir ses familles consommatrices existantes par des cas ciblés TET4/TET10/HEX8/HEX20 selon la voie réellement supportée. Les tests TL/StVK nécessaires protègent les chemins partagés sans promouvoir la route géométrique. Contacts et arc-length gardent leurs domaines historiques ; toute modification de code commun impose leur non-régression pertinente, sans nouvelle capacité contact ou postbuckling.

**Livrable visible :** contraintes dont la mesure est identifiable, tangentes contrôlées, résultat convergé relié à un état accepté, diagnostics d’échec exploitables et limites mécaniques lisibles. Les champs futurs de diagnostic sont proposés, pas des API déjà présentes.

**Frontière :** pas de transitoire non linéaire implicite, explicite, plasticité multiplicative, follower loads, contact général ni modal précontraint dans ce bloc. La levée de la restriction aux charges nodales mortes et une tangente analytique complète pourront constituer des extensions ultérieures, après fermeture des corrections. Elles ne sont pas promises pour cette release.

## E. Feature matrix

Les noms de méthodes/API ci-dessous sont **proposés**. Leur stabilité sera PROVISIONAL ; leur maturité runtime reste EXPERIMENTAL, sauf décision ultérieure explicitement justifiée.

| FEATURE | CURRENT_STATE | TARGET_0_2_12 | MATURITY_TARGET | WP | PRIORITY |
| --- | --- | --- | --- | --- | --- |
| Identité checkpoint Newmark | Omet masses/ressorts dans payload physique | Hash complet ; version explicite ; rejet des reprises incompatibles | Contrat logiciel vérifié, aucune promotion mécanique | WP01 | MUST |
| Système dynamique réutilisable | Assemblage par solve ; plans déjà présents | K/M et DDL préparés, reuse en mémoire avec garde mutation | PROVISIONAL / EXPERIMENTAL | WP01 | MUST |
| Base modale pour réponse | Modes présents ; pas de contrat de réponse réutilisé | Base liée à empreinte, projection et M-orthogonalité | EXPERIMENTAL ; preuves bornées | WP02 | MUST |
| Damping modal par mode | Cibles de Rayleigh déjà existantes | ζj explicites ; contrôle dégénérescences ; distinction modèle réduit/physique | EXPERIMENTAL | WP02 | MUST |
| Flexibilité résiduelle | Non exposée dans harmonic | Vecteurs statiques ciblés, option explicite | EXPERIMENTAL | WP03 | MUST |
| Harmonique modal | Direct_frequency seulement | `harmonic_response/modal_superposition` | EXPERIMENTAL | WP04 | MUST |
| Transitoire modal | Newmark dans espace physique | `transient_dynamic/modal_newmark`, pas constant | EXPERIMENTAL | WP05 | MUST |
| Forces harmoniques déphasées | Somme des forces réelles assemblées | Phasors par canal ; même force en direct et réduit | EXPERIMENTAL | WP06 | MUST |
| Historique multicharge | Déjà disponible en Newmark | Adaptateur conservant la sémantique ; pas de faux ajout | Scope existant inchangé ; extension réduite EXPERIMENTAL | WP06 | MUST |
| Uniform base acceleration | Pas de contrat public dédié identifié | Charge inertielle cohérente et accélération absolue observée | EXPERIMENTAL | WP07 | MUST |
| Résultats réduits/sondes | Histories sondées en transient ; harmonic conserve U complet | Métadonnées base/troncature ; choix sondes/full explicite | Schémas nouveaux PROVISIONAL | WP08 | MUST |
| Generalized-alpha | Absent des méthodes exposées | Méthode linéaire distincte avec ρ∞ et reprise | EXPERIMENTAL | WP11 | SHOULD |
| Shell modal response | Condensation actuelle ; beta-Rayleigh interdit en Newmark condensé | Scope coques borné, après traitement DAE/reconstruction | EXPERIMENTAL | WP12 | SHOULD |
| Campbell préparé | 2 assemblages K/M par vitesse mesurés | Assemblage invariant unique, identité et ambiguïté conservées | EXPERIMENTAL inchangé | WP13 | SHOULD |
| Solid stress snapshots dynamiques | Pas de chaîne complète générale harmonique solide | Réutiliser la récupération sur quelques snapshots explicites | EXPERIMENTAL | WP14 | SHOULD |
| Mesures de contraintes NL | Ambiguïté `second_piola_stress` corotationnel vérifiée | Mesures/repères cohérents et sortie versionnée | Maturités historiques préservées ; correction documentée | WP15 | MUST |
| Tangente corotationnelle | Différences centrales, pas dépendant de l’origine, symétrisation | Pas robuste, diagnostic directionnel et corrections justifiées | Preuves numériques bornées, sans promotion globale | WP16 | MUST |
| États/convergence/scope NL | Transactions et reprise déjà présentes | Cas limite contrôlés, état accepté explicite, matrice de scope cohérente | Contrats renforcés ; maturités historiques préservées | WP17 | MUST |
| Gyro arbre / balourd / contact NL | Absent ou hors scope général | Aucun ajout dans scénario A | Maturités historiques préservées | — | DEFER |

## F. Work Packages

> **Attention — numérotation prospective datée du 7 octobre.** Les WP de cette section ne constituent **pas** la liste opérationnelle des clôtures. Pour la situation effective et les 11 WP déjà clôturés, revenir à la **Partie I, §1**.

Chaque WP forme une PR cohérente future. L’étude présente la découpe ; elle n’autorise ni ne crée ces PR. Les dépendances déterminent l’ordre d’intégration. Les migrations des modules communs restent localisées ; interfaces minimales gelées à WP01 permettent de développer les consommateurs séparément.

### WP00 — Freeze et baseline

- **Objectif :** rattacher le plan au `main` examiné et au code du tag v0.2.11 ; figer le périmètre MUST.
- **Modules :** manifests/plans futurs sous `qualification/0_2_12`, contrat API et inventaire des chemins modifiés.
- **API :** aucune API nouvelle.
- **Numérique :** aucune modification ; préserver les baselines et échecs historiques.
- **Dépendances :** aucune.
- **Tests :** réutiliser la CI existante et sélectionner les cas de non-régression concernés ; pas de nouvelle bibliothèque d’anciens modèles.
- **Acceptation :** identités sources enregistrées, matrice scope/priorités/limites claire ; statut G03/WP14 intact.
- **Risques :** confondre les tags de source et publications, ou un ancien verdict avec le code actuel.
- **Hors scope :** requalifier tous éléments, nettoyer archives ou changer les tolérances historiques.

### WP01 — Système préparé, identité physique et reprise

- **Objectif :** préparer K/M/DDL une fois et rendre leur reuse sûr ; corriger l’omission prouvée de signature Newmark.
- **Modules :** `assembly/plan.py`, nouveau `prepared_dynamic_system.py`, `dynamic.py`, `dynamic_checkpoint.py`, `io/dynamic_checkpoint.py`, `model_writer.py`.
- **API :** objet interne préparé ; façade optionnelle proposée `prepare_dynamics(model)` PROVISIONAL, sans changer la signature ni le comportement de `solve_model` existant.
- **Numérique :** matrices identiques à l’assemblage actuel ; copie/snapshot immuable et empreinte structurelle. Séparer empreinte d’opérateurs, identité d’excitation et identité d’exécution.
- **Dépendances :** WP00.
- **Tests :** équivalence préparé/non préparé ; invalidation après coordonnées, matériau, masses, ressorts, BC ou DDL ; répétition de loads autorisée seulement si identité d’excitation séparée ; reprise après mutation rejetée.
- **Acceptation :** un seul assemblage K/M par préparation ; égalité numérique sur fixtures ; aucune mutation du modèle utilisateur ; correction confirmée par les diagnostics 100 kg/100 N/m.
- **Risques :** caches obsolètes, copies mémoire excessives, ancienne empreinte qui inclut trop ou trop peu.
- **Hors scope :** cache global/persistant, assemblage distribué, refonte des plans non linéaires. Pour les anciens checkpoints incomplets, permettre lecture/inspection, mais refuser par défaut une reprise non prouvée ; ne pas inventer la physique manquante.

### WP02 — Base modale et amortissement réduit

- **Objectif :** construire une base de réponse, avec sa qualité et son identité.
- **Modules :** `modal.py`, nouveau `modal_basis.py`, `modal_options.py`, `dynamic_controls.py`, validators/preflight.
- **API :** proposition `build_modal_basis(prepared, modes, ...)` PROVISIONAL ; paramètres `reduction.modes`, `damping.kind`, ζj ; modes existants conservés.
- **Numérique :** réutiliser les eigensolvers existants ; vérifier ΦᵀMΦ et ΦᵀKΦ ; projection Mr/Kr ; Rayleigh ou ζj. Si des clusters sont dégénérés, loi d’amortissement invariante obligatoire.
- **Dépendances :** WP01.
- **Tests :** système 2–3 DDL analytique ; base complète ; permutation/phase/sous-espace ; un modèle simple par famille nouvelle autorisée ; rejet de base d’un autre système.
- **Acceptation :** résidu modal relatif ≤10⁻⁸ et défaut M-orthogonalité ≤10⁻⁸ sur fixtures bien conditionnées ; seuils à figer avant campagne ; indices de modes et dimensions explicites.
- **Risques :** mêmes fréquences avec bases différentes ; loss of orthogonality ; choix incomplet des modes.
- **Hors scope :** QEP rotatif, modes rigides/free-free, enrichissement automatique général, nouveau eigensolver. Base sous forme N×r, jamais N×N pour une demande tronquée.

### WP03 — Correction statique et diagnostics de troncature

- **Objectif :** éviter qu’une réponse harmonique réduite reproduise mal la composante quasi statique d’une charge locale.
- **Modules :** nouveau `residual_flexibility.py`, `solvers/linear.py`, `modal_basis.py`.
- **API :** `residual_correction='none'|'static'`; résultat indiquant méthode, RHS et coût ; vecteurs de correction internes.
- **Numérique :** résoudre KB pour les canaux pertinents avec LU réutilisée ; soustraire la contribution statique modale ; ne pas former l’inverse.
- **Dépendances :** WP01–WP02 ; interface des canaux WP06 définie, implémentation testable avec B fourni.
- **Tests :** à ω=0, retour exact à la solution statique dans le scope ; à base complète, correction nulle à l’arrondi ; charge locale et deux troncatures.
- **Acceptation :** erreur relative à ω=0 ≤10⁻⁸ sur fixtures ; défaut de projection explicite ; exemple démontrant une amélioration sur une observable définie, sans prétention de monotonie universelle.
- **Risques :** double comptage, K singulière, amélioration du déplacement masquant mauvaise accélération/contrainte.
- **Hors scope :** correction transitoire automatique, rigid body, approximation des résonances des modes omis, garanties à haute fréquence.

### WP04 — Harmonique par superposition modale

- **Objectif :** ajouter la réponse complexe réduite avec choix explicite direct/réduit.
- **Modules :** `harmonic.py`, nouveau `modal_response.py`, `settings.py`, `schema_analysis.py`, `router.py`.
- **API :** nouvelle méthode proposée `modal_superposition`; paramètres base, damping et correction ; `direct_frequency` reste défaut.
- **Numérique :** résoudre l’impédance réduite ; cas diagonal spécialisé seulement lorsque démontré ; reconstruction U et observables. Convention exp(+iωt) unique.
- **Dépendances :** WP01–WP03 ; B/phasors de WP06 intégrés ensuite.
- **Tests :** oscillateur amorti ; 2–3 DDL ; full basis versus direct ; troncature contrôlée ; fréquences proches de résonance et entrée nulle.
- **Acceptation :** base complète, réponse relative ≤10⁻⁸ versus direct hors singularité ; référence analytique d’amplitude et phase ; au voisinage d’une résonance, contrôler condition/résidu plutôt que promettre une tolérance arbitraire universelle.
- **Risques :** erreurs de signe complexes, impédance quasi singulière, mauvaise interprétation du résidu complet.
- **Hors scope :** harmonique NL, PETSc complexe, rotor forcé, changement de défaut implicite selon taille.

### WP05 — Newmark dans la base modale

- **Objectif :** utiliser les mêmes base et canaux en réponse temporelle linéaire.
- **Modules :** `dynamic.py`, nouveau noyau de réponse modale, `dynamic_history.py`, checkpoints dédiés/versionnés.
- **API :** méthode proposée `modal_newmark`; même pas constant et mêmes fonctions de charge historiques ; état modal explicite dans le nouveau checkpoint.
- **Numérique :** Newmark dans Mr/Cr/Kr ; initialisation cohérente de u/v/a et projection ; reconstruction finale ou sondée ; énergie calculée dans le modèle réduit et correctement étiquetée.
- **Dépendances :** WP01–WP02 ; contrats WP06 et WP08.
- **Tests :** oscillation libre/damping ; force sinus et pulse ; base complète versus Newmark direct ; dt/dt/2/dt/4 ; reprise au milieu du calcul.
- **Acceptation :** équivalence full basis à pas identique ≤10⁻⁸ sur fixtures ; ordre temporel observé proche de 2 pour charges lisses ; reprise cohérente ; rapport de projection des conditions initiales et d’énergie abandonnée.
- **Risques :** vitesse/accélération reconstruites à un autre instant que u ; oubli de modes initialement excités ; métadonnées de reprise obsolètes.
- **Hors scope :** NL, variable dt, explicite, correction statique instantanée. Ne pas migrer le résultat Newmark existant sans besoin fonctionnel.

### WP06 — Canaux d’excitation et phasors

- **Objectif :** calculer des charges indépendantes et déphasées, identiques entre direct et réduit.
- **Modules :** `loads/entities.py`, `load_schema.py`, nouveau `dynamic_excitation.py`, assemble_load_vectors, JSON/model writer, harmonic.
- **API :** `excitation_channels` proposé ; chaque canal référence une charge spatiale par identité stable et définit une amplitude réelle temporelle ou un phasor `{real, imag}` par fréquence. Anciennes listes et `load_factors_by_load` gardées via adaptateur.
- **Numérique :** F(ω)=B f̂(ω), F(t)=B f(t). Les charges spatiales distribuées existantes restent intégrées par les noyaux actuels.
- **Dépendances :** WP01 ; interfaces indépendantes des solveurs WP04/WP05.
- **Tests :** superposition complexe ; 90°/180° ; annulation de canaux ; mismatch des fréquences et valeurs non finies rejetés ; compatibilité des indices historiques.
- **Acceptation :** égalité direct/réduit des vecteurs de force, conservation des amplitudes/units/phase ; priorité des entrées non ambiguë ; entrées nouvelle+ancienne incompatibles explicitement rejetées.
- **Risques :** double application des amplitudes, confusion Hz/rad/s ou degrés/radians, index de charge mouvant.
- **Hors scope :** champ de phase spatial arbitraire, signal aléatoire/PSD, spectres de réponse, balourd automatique.

### WP07 — Accélération uniforme de base

- **Objectif :** apporter une excitation inertielle exploitable dans le transitoire et l’harmonique.
- **Modules :** dynamic_excitation, préparation de M, dynamic/harmonic, history/results, schemas.
- **API :** `base_acceleration` avec direction globale normalisée et amplitude en m/s² ; un mouvement de translation rigide commun à la base, coordonnées relatives ; résultat d’accélération absolue explicitement distinct.
- **Numérique :** Fbase=−M r ag ; Γ=ΦᵀM r. r possède les translations rigides correspondantes et rotations nulles ; utiliser la masse cohérente complète, y compris couplages, avant projection. Ne pas remplacer par des forces diagonales m_i ag sans justification.
- **Dépendances :** WP01–WP02, WP04–WP06.
- **Tests :** SDOF à accélération de base analytique ; équivalence avec forces nodales cohérentes ; deux axes ; ag=0 ; conventions accélération relative/absolue.
- **Acceptation :** mêmes résultats direct/réduit full basis ; accélération absolue a_rel+r ag ; masses participantes rapportées avec dénominateur et scope ; énergie d’un système forcé distinguée de la conservation libre.
- **Risques :** signes, repère mobile implicite, confusion BC de déplacement imposé et pseudo-force, masse participante surinterprétée.
- **Hors scope :** déplacements imposés multisupports, rotation de base, mouvement différentiel, gyros et excentricités ; seul déplacement relatif est garanti si l’utilisateur ne fournit pas la position absolue de la base.

### WP08 — Résultats, sorties et compatibilité de politique

- **Objectif :** rendre les nouvelles réponses inspectables sans gonfler inutilement la mémoire ou sur-promouvoir la maturité.
- **Modules :** `results.py`, `result_serialization.py`, `qualification.py`, compatibility/preflight, JSON/CSV, dynamic_history, API/CLI.
- **API :** champs additifs `reduction`, `excitation`, `response_frame`, `output_availability`; schéma des nouveaux résultats versionné ; sélection explicite probes/full. `save_result` et `solve_model` restent utilisables.
- **Numérique :** sondes évaluées via les lignes de Φ ; calculs complets reconstruits seulement si demandés. Pour les réactions physiques, utiliser le système complet et déclarer l’erreur de troncature ; ne pas assimiler réactions réduites à un équilibre exact.
- **Dépendances :** interfaces WP01–WP07 ; sérialisation développable séparément après gel des objets.
- **Tests :** round-trip real/imag, noms/units, absence de champs non calculés, API/CLI en installation propre, strict/qualification ne requalifient pas la nouvelle méthode.
- **Acceptation :** numerical status distinct d’evidence/maturity ; aucune fausse collection complète vide ; old JSON/API/exit codes préservés ; test d’une méthode modale nouvelle sur un élément historiquement qualifié restant EXPERIMENTAL.
- **Risques :** classification runtime héritée de l’analyse classique, schéma incompatible, mélange amplitude/von Mises de phasors.
- **Hors scope :** format universel de tous résultats, restart HDF5, viewer/dashboard, modification des anciens enregistrements.

### WP09 — Vérification ciblée et caractérisation de coût

- **Objectif :** fermer les preuves nécessaires aux nouvelles formulations et contrôler le coût réellement gagné.
- **Modules :** tests des nouvelles méthodes, petit runner utilisant V&V v2 existant, manifests neufs `0_2_12`.
- **API :** pas de nouvelle infrastructure globale ; cas/mesures exprimés dans les structures existantes.
- **Numérique :** aucuns seuils ajustés après résultats ; comparer solveur réduit, direct et références indépendantes selon la section H.
- **Dépendances :** WP02–WP08.
- **Tests :** bibliothèque ciblée de la section H ; suite de non-régression existante adaptée aux fichiers modifiés ; petit workload de performance full/probes/direct/reduced.
- **Acceptation :** mêmes entrées, tolérances figées, erreurs et versions enregistrées ; reprise V&V refuse changements d’oracle/tolérances ; temps préparation/solve/post distincts, RSS et tailles base/output.
- **Risques :** considérer QF direct comme oracle physique indépendant ; sélectionner seulement des charges favorables ; coût base masqué.
- **Hors scope :** cent modèles historiques, campagnes inter-solveurs globales, 10M DDL, nouvelle qualification de toute une famille.

### WP10 — Release engineering

- **Objectif :** publier le scope complet MUST vérifié, avec les exclusions clairement visibles.
- **Modules :** changelog, metadata/version/citation, docs capacités/API, packagers et contrats existants.
- **API :** nouvelles méthodes listées, exemples minimaux ; namespace et CLI conservés.
- **Numérique :** aucune promotion implicite et aucun dernier changement de formulation pendant le packaging.
- **Dépendances :** WP00–WP09 **et WP15–WP17** ; SHOULD seulement si accepté comme bloc complet.
- **Tests :** CI requise, docs, wheel/sdist, import propre, API/CLI, un harmonic, un transient reduced et un cas statique NL installés ; contrats de sortie de contraintes ; hashes du candidat.
- **Acceptation :** scope source/assets exact, 0.2.12 cohérente partout, anciennes interfaces et limites intactes ; autorité existante de publication respectée lors de la future exécution.
- **Risques :** embarquer anciennes archives sensibles/non cleared, publier preuve d’un autre SHA, promouvoir routes voisines.
- **Hors scope :** « réparation » de G03 historique ; effacement WP14 ; nouvelle chaîne de publication parallèle.

### WPs MUST du volet non linéaire

Les numéros WP15–WP17 sont ajoutés pour préserver les références WP00–WP14 de la proposition initiale. Ils s’intègrent avant WP09/WP10, même si leur numéro est supérieur.

### WP15 — Mesures de contraintes et contrat de résultats NL

- **Objectif :** éliminer l’ambiguïté entre contrainte locale corotée, premier Piola, second Piola et Cauchy.
- **Modules :** `elements/solid/corotational_j2.py`, récupération solide, résultats/sérialisation et docs ; vérifier les consommateurs du champ concerné avant migration.
- **API proposée :** mesure, repère et version de sémantique explicites ; schéma versionné pour le champ corrigé. Conserver les lecteurs historiques et permettre l’identification d’anciens résultats ; ne pas conserver une valeur incorrectement étiquetée dans les nouvelles sorties pour simuler une compatibilité parfaite.
- **Numérique :** cohérence avec le modèle actuel : P=Rσlocal, σ=PFᵀ/J, S=F⁻¹P. Ne pas imposer une symétrie supplémentaire à S sans justification, ni convertir ce modèle en plasticité multiplicative par changement de vocabulaire. Cohérence des transformations et validité physique de la formulation sont deux questions distinctes.
- **Dépendances :** WP00 ; coordination du schéma avec WP08 ; constitue le contrat préalable à WP16/WP17.
- **Tests :** déformation affine, étirement fini borné, rotation rigide superposée, unités/repères, export puis relecture ; références tensorielles calculées sans appeler le récupérateur de production.
- **Acceptation :** identités de transformation satisfaites sur les cas définis ; anciens fichiers identifiés sans réinterprétation silencieuse ; correction et changement de sens documentés. Les décisions historiques restent attachées à leur ancien code/résultat, sans être réécrites.
- **Risques / hors scope :** dépendances aval au champ historique ; pas d’usage général de précontrainte ni de nouvelle qualification finite-strain.

### WP16 — Fiabilité et coût des tangentes corotationnelles

- **Objectif :** vérifier la dérivée utilisée par Newton et corriger la dépendance du pas numérique à l’origine du repère.
- **Modules :** noyau corotationnel partagé, assemblage NL et instrumentation locale ; pas de refonte générale du solveur.
- **API proposée :** diagnostics internes de méthode/pas, évaluations de force et erreur directionnelle ; exposer seulement les informations utiles à interpréter un échec. Aucune nouvelle option publique n’est nécessaire si le choix peut rester interne et déterministe.
- **Numérique :** confronter Kv à une dérivée directionnelle de f interne à état committed figé ; explorer plusieurs pas indépendants du pas de production. Comparer la tangente brute et la tangente symétrisée. Si la symétrisation altère matériellement la dérivée sur le scope, corriger formulation ou politique de tangente/solveur et documenter la compatibilité ; ne pas simplement relâcher le seuil.
- **Dépendances :** WP00/WP15 ; consomme les contrats d’état existants ; WP17 utilise ensuite la tangente corrigée.
- **Tests :** translation de l’origine du maillage sans changement physique, changement cohérent d’unités, rotations rigides et chargement plastique lisse ; HEX8 et un high-order consommateur au minimum, puis non-régressions des autres consommateurs touchés. Près d’un changement de branche constitutive, utiliser une analyse unilatérale ou un critère adapté à la non-lissité, pas une fausse exigence d’ordre deux.
- **Acceptation :** plateau de convergence de la dérivée sur les cas lisses, écart tangente/force borné par seuils figés avant exécution, absence de dérive due au seul choix d’origine à tolérance documentée ; itérations Newton et évaluations de force enregistrées. Une tangente numérique fiable reste acceptable : une tangente analytique complète n’est pas un gate.
- **Risques / hors scope :** la correction peut révéler une incohérence plus profonde. Si elle exige une nouvelle formulation constitutive, rendre le cas concerné explicitement indisponible et replanifier ; ne pas étendre son domaine. Aucun gain ×49/×121 promis à partir du seul nombre d’appels.

### WP17 — États acceptés, convergence et frontières de formulation

- **Objectif :** consolider les capacités existantes afin qu’un résultat publié corresponde à un état accepté et à un scope effectivement supporté.
- **Modules :** `core/nonlinear/solver.py`, `contracts.py`, `checkpoint.py`, moteur Newton et transactions existants, garde d’assemblage NL, validation d’entrée et docs.
- **API proposée :** enrichissement additif des diagnostics de convergence : motif d’arrêt, résidu normalisé avec référence/plancher explicites, itérations, essais rejetés, facteur de charge accepté et histoire partielle après reprise. Réutiliser les champs déjà existants.
- **Numérique :** garder les historiques constitutifs committed inchangés après échec/line search/cutback ; vérifier la reprise à partir d’un état accepté et l’identité des ingrédients pertinents. Le défaut confirmé du checkpoint Newmark ne prouve pas un défaut du checkpoint NL : auditer ce dernier et corriger seulement les lacunes effectivement observées. Ne pas uniformiser aveuglément les critères de Newton et d’arc-length.
- **Dépendances :** WP00/WP15/WP16 ; coordination WP01 uniquement pour conventions d’identité, WP08 pour les résultats.
- **Tests :** charge–décharge–recharge J2, essai volontairement rejeté suivi d’une résolution, reprise interrompue comparée à la résolution continue, mutation/corruption de checkpoint, limite locale corotationnelle, J≤0 et demandes non supportées. Réutiliser les tests transactionnels existants en ajoutant les chemins effectivement modifiés.
- **Acceptation :** états matériels et déplacements acceptés concordants ; aucun essai rejeté conservé comme état final ; échec contrôlé sans faux `converged`; reprise et diagnostics cohérents ; documentation/runtime d’accord sur cinématique, famille, loi et charge. Aucune promotion automatique HEX20/TET10, contact ou TL/StVK.
- **Risques / hors scope :** interactions avec adaptation, line search et reprises anciennes ; pas de nouveaux couplages de méthodes, dynamique NL ou extension générale contact.

### WP-E01 — Fondations du calcul non linéaire

**Décision Owner : 18 octobre 2026.** **Statut : `OPEN — EXPERIMENTAL_TARGET`.**
Work package ajouté à la roadmap v0.2.12, séparément des WPs historiques.
Objectif : consolider et étendre les bases vérifiables de la **plasticité J2 en petites déformations** et des **grandes déformations élastiques**, en s'appuyant sur les noyaux Newton, J2 et Total Lagrangian existants. L'implémentation et la qualification de ce nouveau périmètre ne sont pas acquises par sa seule inscription à la roadmap.

| Sous-package | Contenu visé | Livrable / preuve minimale |
| --- | --- | --- |
| **WP-E01-A — Socle Newton** | Newton–Raphson incrémental, contrôle des résidus, pas de charge, line search/cutback, tangente cohérente, transactions d'états | Chemins de convergence et d'échec contrôlé, états rejetés non validés, instrumentation des itérations et critères |
| **WP-E01-B — Plasticité J2** | Petites déformations, critère von Mises, retour radial, plasticité parfaite et écrouissage isotrope linéaire | Tests matériau uniaxiaux/multiaxiaux, chargement–déchargement–rechargement, dissipation et tangente algorithmique comparée à une dérivée indépendante |
| **WP-E01-C — Grandes déformations élastiques** | Cinématique Total Lagrangian, gradient `F`, déformation de Green–Lagrange `E`, mesures de contrainte et tangentes matérielle/géométrique ; Saint-Venant–Kirchhoff et néo-Hookéen sur périmètre explicitement supporté | Rotation rigide superposée, traction/cisaillement, vérification de l'objectivité, de `det(F) > 0` et des réponses de référence |
| **WP-E01-D — V&V non linéaire** | Campagne constitutive, élémentaire et multi-incréments ; indépendance des références, comparaison des tangentes, sensibilité au pas et au maillage | Tests positifs/négatifs, marges de tolérances préenregistrées, limitations documentées, aucune promotion sur la seule base de tests unitaires |
| **WP-E01-E — Intégration FEM** | Première cible TET4/HEX8, raccordement API, états internes et résultats, diagnostics et documentation | Cas FEM élémentaires et maillages bornés, sorties physiques cohérentes, non-régression des routes existantes, statut expérimental explicite |

**Critères de clôture du périmètre expérimental :**

1. Formulations, conventions tensorielles, unités, hypothèses cinématiques et domaines de validité documentés.
2. Retour radial J2, écrouissage et transferts d'états vérifiés sur histoires de chargement, avec conservation des états acceptés et traitement correct des essais rejetés.
3. Tangentes constitutives et tangente globale vérifiées sur des états lisses par références indépendantes ; gestion explicite des points non différentiables.
4. Objectivité sous rotations rigides et cohérence des contraintes et déformations de la voie Total Lagrangian vérifiées.
5. Tests FEM TET4 et HEX8 sélectionnés, échecs contrôlés, limites de convergence et résultats reproductibles archivés.
6. API, diagnostics, V&V et documentation conformes au périmètre **`EXPERIMENTAL`** ; aucune qualification industrielle générale implicite.

**Dépendances et coordination :** réutiliser les capacités pertinentes de WP09 et les contrats WP15 (mesures de contraintes), WP16 (tangentes) et WP17 (états/convergence). WP-E01 complète ces chantiers sans remplacer leurs critères historiques. Maintenir WP-C01 et les routes de contact en qualification séparée. Aucun changement rétroactif du statut de WP09, WP-C01, WP-C03 ou de la version publiée.

**Hors périmètre initial :** plasticité J2 multiplicative à déformations finies (`F = Fe Fp`), contact frottant couplé à la plasticité finie, grands glissements couplés, flambement/post-flambement général, dynamique non linéaire et extension automatique aux éléments high-order. Une future décision Owner sera nécessaire pour élargir ces frontières.

**Place dans la release :** cible expérimentale ajoutée le 18 octobre 2026, distincte des preuves MUST/SHOULD et estimations de charge établies dans l'étude du 7 octobre. Réévaluer explicitement le budget et les gates de release avant de déclarer WP-E01 obligatoire pour la publication.

### WPs SHOULD séparables

| WP | Objectif, modules et API | Numérique et dépendances | Tests / acceptation | Risque et hors scope |
| --- | --- | --- | --- | --- |
| **WP11 — Generalized-alpha** | dynamic integration dédié ; `method='generalized_alpha'`, ρ∞ explicite et checkpoint versionné | Linéaire seulement ; conventions d’évaluation M/C/K/F documentées ; dépend WP01/WP05 | Oscillateur, ordre 2, limite de dissipation, récupération du comportement non dissipatif, reprise ; tolérances gelées | Risque moyen ; pas de J2/contact ou dt adaptatif |
| **WP12 — Coques et réduction dynamique** | dynamic_reduction, modal_basis, reconstruction et stress shell ; méthodes nouvelles autorisées sur scopes nommés | Traiter les coordonnées algébriques et l’effet de β-Rayleigh ; dépend WP01–WP05/WP08 | Plaque simple + shell courbe ciblée ; full basis/direct ; massless drilling, orientation et rejet des cas non supportés | Risque élevé ; ne pas lever l’interdit β-Rayleigh de Newmark condensé sans formulation DAE adéquate ; pas de requalification globale MITC4 |
| **WP13 — Campbell invariant préparé** | campbell/rotating_modal ; objet rotor préparé interne ; API de sweep inchangée | Assembler K/M/G une fois, vérifier modèle immutable au lieu de réassembler ; dépend WP01 ; préserver QEP et tracking policy | Compteur d’assemblage=1 ; spectres/sous-espaces/branch lineage identiques aux fixtures ; ambiguïté 100 rad/s conservée ; nouveau execution key attendu | Risque moyen ; pas de gyro arbre, damping, balourd ou sparse QEP |
| **WP14 — Contraintes solides sur snapshots** | solid recovery/stress, harmonic/modal response ; liste explicite fréquences/instants/éléments | Reconstruction puis noyaux existants ; dépend WP04/WP05/WP08 | Champ affine et un cas flexion ; base complète/direct ; erreur de troncature des contraintes rapportée | Risque moyen ; pas de garantie locale déduite de masse participante ; phasor de von Mises jamais assimilé sans définition à un maximum temporel |

### Ordre d’intégration proposé

WP00 → WP01 → WP02. WP03 et WP06 peuvent ensuite être conçus séparément sur les contrats gelés ; WP04 dépend de WP03, WP05 de la base, WP07 des réponses et canaux, WP08 des objets résultats. Après WP00, WP15 fixe les mesures NL, WP16 vérifie/corrige les tangentes, puis WP17 consolide les états et limites. Les deux blocs se rejoignent dans WP08/WP09 ; WP09 consolide leurs preuves puis WP10 prépare la publication. Les tests unitaires appartiennent à chaque WP ; WP09 ne repousse pas tous les tests à la fin.

WP12 est le SHOULD présentant le plus grand risque de dépassement. Si la condensation nécessite une nouvelle formulation large, le retirer de 0.2.12 plutôt que diminuer silencieusement les garde-fous.

## G. Gates proportionnés

**Sept gates suffisent.** Statuts futurs : PASS, FAIL ou BLOCKED ; un gate requis BLOCKED interdit la publication du MUST. Un SHOULD retiré est REMOVED_FROM_SCOPE, avec docs/tests/API cohérents, et non « PASS » fictif. Un propriétaire de décision peut être enregistré sans inventer une approbation déjà donnée.

| Gate | Porte principalement sur | Preuve minimale et condition de fermeture |
| --- | --- | --- |
| **QF0212_G01 — Baseline et scope** | Identité, frontières et compatibilité | Commit/tag/source ; MUST gelé ; exclusions ; anciennes maturités/échecs préservés ; aucune confusion avec G03 historique |
| **QF0212_G02 — Architecture/identités** | Système préparé, caches et checkpoints | Invalidation physique exhaustive dans scope ; K/M prepared équivalents ; pas de mutation ; nouvelles reprises vérifiées ; G03 reste FAIL_PRESERVED |
| **QF0212_G03 — Formulations** | Projection/damping/base et mesures/tangentes NL | Identités et références de H ; conventions ; full basis recovery ; transformations de contraintes et dérivée directionnelle NL vérifiées |
| **QF0212_G04 — Comportement numérique** | Troncature, temps, singularités et coût | Convergence r et dt séparées ; domaines de tolérance explicités ; near resonance contrôlée ; reprise déterministe bornée ; mémoire/compteurs mesurés ; indépendance à l’origine du repère, cas lisses/non lisses distingués et essais NL rejetés correctement restaurés |
| **QF0212_G05 — Non-régression et interfaces** | Code ancien partagé, API/CLI/JSON | CI existante obligatoire ; cas impactés ; règles de maturité par nouvelle méthode ; old inputs/lecteurs/exit codes conservés ; correction de sémantique des contraintes NL versionnée et documentée ; options invalides rejetées |
| **QF0212_G06 — Candidat installé et docs** | Artefacts sélectionnés | Wheel/sdist candidat installable, hashes, exemples réduits installés, docs strictes, metadata/citation ; exclusions d’archives identiques à la politique existante |
| **QF0212_G07 — Publication et vérification** | Distribution exacte | Au futur moment de publication : autorisation selon contrat existant, tag/artefacts/source liés, version et hashes publics vérifiés ; aucune promotion générale |

Ces gates n’exigent pas une nouvelle corrélation externe de tous éléments. Les cas historiques non touchés sont protégés par les checks existants ; on n’invente pas une campagne 0.3.0 à leur place.

## H. Tests minimaux directement nécessaires

### H1. Petit corpus, plusieurs propriétés

**Proposition : 7 fixtures/cas physiques pour le bloc dynamique**, complétées par les quatre groupes NL de H4, plus tests logiciels et paramétrisations. Ce nombre ne correspond pas au nombre d’exécutions : dt et nombre de modes nécessitent quelques variantes. Il n’y a pas une nouvelle galerie de tous les anciens benchmarks.

| ID proposé | Cas / référence | Capacités et propriétés | Critère prospectif |
| --- | --- | --- | --- |
| **DYN12-01** | SDOF amorti force et base ; formules fermées | Amplitude/phase, transient, accélération absolue, dissipation | Harmonique ≤10⁻⁸ relatif loin des zeros/singularités ; transient ordre 2 sur intervalle lisse |
| **DYN12-02** | Système 2–3 DDL, M/K non diagonales ; décomposition dense indépendante | Projection complète, Cr, phasors, superposition et invariance des bases | Full basis équivalent direct à 10⁻⁸ ; propriétés Mr/Kr ; force nulle et null cancellation |
| **DYN12-03** | Petite structure TET4 existante adaptée à charge locale | Correction statique, troncatures r/2r/full | Exactitude statique ≤10⁻⁸ ; erreurs par observable, sans monotonie universelle imposée |
| **DYN12-04** | Petite structure TET10 élastique | Intégration de la nouvelle réponse/base/IO sur famille high-order | Full basis/direct et propriétés de projection, pas nouvelle qualification complète de TET10 |
| **DYN12-05** | Petite structure HEX8 élastique | Transient/harmonic reduced, restart, masse/ressort | Full basis ; restart et mutation physique ; propriétés énergétiques |
| **DYN12-06** | Petite structure HEX20 élastique | Intégration high-order, mémoire de base, projection | Full basis/direct ; pas de balayage global de qualité de maillage |
| **DYN12-07** | Cantilever BEAM2 droit non rotatif ; formule analytique fondamentale et référence dense assemblée séparément | Domaine poutre, force locale, masses/ressorts, réponse modale | Frequence première sur maillage borné ; full basis/direct ; petits raffinements uniquement si un noyau de poutre est modifié |

Une référence « assemblée séparément » doit effectivement reconstruire les petites matrices à partir des formules, sans appeler les noyaux QF de production. Pour les cas FEM 03–06, **QF direct est une référence d’équivalence logicielle**, pas un oracle indépendant de formulation élémentaire. Les éléments n’étant pas changés dans le bloc dynamique du MUST, c’est une limitation acceptable et explicite ; SDOF et matrices analytiques établissent les nouvelles formulations de réponse.

### H2. Tests transverses nécessaires

- **Base :** orthogonalité M, residual eigenproblem, invariance aux signes/rotations d’un cluster ; damping cluster constant.
- **Projection :** force conservée dans le sous-espace ; full basis récupération ; conditions initiales hors base signalées.
- **Énergie :** libre non amorti à pas constant, dérive bornée ; amorti libre, décroissance ; forcé, bilan travail/énergie cohérent. Ne pas appliquer un gate de conservation libre à un système forcé.
- **Convergence temporelle :** dt, dt/2, dt/4 sur signal lisse ; ratio d’erreurs vers 4, par exemple intervalle prospectif 3–5 loin du roundoff. Les fronts/discontinuités ne satisfont pas forcément cet ordre.
- **Troncature :** r, 2r, full sur mêmes matrices ; deux observables dont une sensible à une charge locale. Viser ≤1 % sur cette démonstration bornée, sans en faire une garantie de toute base.
- **Reprise/identité :** même résultat à tolérance fixée ; mutation d’un ingrédient physique ou base/canal refusée ; corruption détectée.
- **API/maturité :** le nom d’une ancienne analyse ne suffit pas à qualifier la nouvelle méthode. L’option probes ne doit pas être interprétée comme un champ complet.
- **Performance :** une préparation, une base, sweeps de 10/100/500 fréquences et transitoire borné ; compteurs et profils seulement, pas campagne HPC.

Les seuils ci-dessus sont **proposés**, à figer avant les futures exécutions. Ajouter un plancher absolu dimensionné aux observables proches de zéro ; sinon une erreur relative devient indéfinie ou trompeuse. Ne pas relaxer un seuil parce que la première exécution échoue.

### H3. Maturité visée

Toutes nouvelles routes : **EXPERIMENTAL** à la première publication. Les identités analytiques et équivalences peuvent constituer des preuves **VERIFIED_BOUNDED** décrites dans les fiches du nouveau scope ; cette expression ne doit pas être ajoutée comme enum runtime sans adaptation explicite du contrat existant. **QUALIFIED_BOUNDED** n’est pas une cible automatique du MUST.

Ne pas promouvoir le modal classique, le contact, la voie distribué, BEAM2 entier ou un élément high-order parce que sa nouvelle réponse passe un cas simple.

### H4. Corpus ciblé du volet non linéaire

| ID proposé | Cas / référence | Propriétés et fermeture |
| --- | --- | --- |
| **NL12-01** | Élément affine corotationnel, rotation superposée et étirement local borné ; identités tensorielles indépendantes | P/S/σ et repères cohérents, version de sortie/relecture ; pas de preuve globale de validité constitutive déduite de ces identités |
| **NL12-02** | HEX8 et consommateur high-order du noyau partagé ; dérivées directionnelles avec pas distincts | Effet de symétrisation quantifié, invariance à la translation de coordonnées, cohérence d’unités, plateau sur branche lisse ; compteurs et temps séparés |
| **NL12-03** | J2 charge–décharge–recharge ; retour radial de référence calculé séparément sur le cas homogène | État matériel, seuil plastique et durcissement cohérents ; essai rejeté puis reprise depuis l’état accepté ; convergence globale bornée |
| **NL12-04** | Résolution continue/interrompue et entrées à la frontière du scope | Reprise à tolérance, identité/corruption contrôlées, histoire partielle identifiée ; refus de J≤0, limite locale dépassée et combinaison non supportée |

Ces quatre lignes sont des groupes de propriétés, pas quatre exécutions uniques ni une campagne externe exhaustive. Les fixtures existantes peuvent être réutilisées ; ajouter seulement les cas manquants. Les seuils tangente, contraintes, état et résidu doivent être dimensionnés et figés avant les futures exécutions. Les cas smooth et changements de branche constitutive ont des critères distincts. Les **118 tests passés de l’audit initial ne démontrent pas la fermeture de WP15–WP17** ; aucune nouvelle implémentation ni campagne de tests NL n’a été exécutée pour cette révision du rapport.

## I. Dette technique et travail différé

### I1. Dette rationnelle dans 0.2.12

| Classe | Dette précise | Pourquoi la traiter / limiter |
| --- | --- | --- |
| **BLOCKING** | Signature checkpoint Newmark sans masses/ressorts ; autres données physiques doivent être inventoriées | Bug de garde confirmé ; incompatible avec base/cache/reprise sûrs ; WP01 |
| **BLOCKING** | Maturité actuellement surtout attachée au type d’analyse ; nouvelles méthodes risquent d’hériter « stable » | Nouvelle méthode modale ne doit pas emprunter le statut de `transient_dynamic` ; WP08, fixtures dédiées |
| **BLOCKING** | Identité d’une base et d’un opérateur distincte de l’excitation | Réutilisation sinon soit dangereuse, soit invalidée inutilement par chaque force ; WP01–WP02 |
| **HIGH_VALUE** | Réassemblages et duplication de préparation pour analyses multiples | Justification fonctionnelle directe par reuse ; extraction limitée, pas refonte totale |
| **HIGH_VALUE** | Harmonique stocke tous vecteurs et phases indépendantes absentes | Sondes et canaux pour sweeps ; WP06/WP08 |
| **HIGH_VALUE** | Erreur de résolution confondable avec troncature | Contrat des nouveaux résultats ; WP02/WP04/WP05 |
| **OPPORTUNISTIC** | Compteurs/temps nouveaux non alignés avec telemetry | Ajouter seulement événements nécessaires aux nouvelles routes |
| **OPPORTUNISTIC** | Campbell assemble deux fois par vitesse | WP13 optionnel ; optimisation démontrable mais pas defining feature |
| **OPPORTUNISTIC** | Docstrings géométriques encore « TET4 » alors que plusieurs noyaux sont admis | Corriger seulement si module touché ; coût faible, pas WP autonome |
| **DEFER_TO_0_3_0** | Inventaire global des preuves, visibilité/availability de toutes références | Domaine de consolidation 0.3.0 ; réutiliser v2 aujourd’hui pour nouveaux cas |
| **DEFER_TO_0_3_0** | Analyse systématique de toutes limites contact/postbuckling/HPC | Campagnes globales de modèles et preuves ; ne pas effacer échecs existants |
| **DEFER / chantier dédié** | Extraction exhaustive des gros modules slip_root/robustness | Leur taille n’est pas seule une raison de refactor ; pas de consommateur nouveau dans scénario A |
| **BLOCKING dans le volet NL** | Mesures de contraintes ambiguës, pas dépendant de l’origine, vérification de tangente/symétrisation | WP15–WP16 obligatoires ; coûts 49/121 appels documentés ; optimisation analytique non obligatoire |
| **HIGH_VALUE / MUST NL** | Consolidation des contrats d’état accepté, reprise et scope | WP17 ; renforcer l’existant, sans prétendre que les transactions ou checkpoints sont absents |

### I2. À réserver à v0.3.0

1. Grande bibliothèque couvrant tous éléments, familles d’analyse et combinaisons.
2. Corrélations inter-solveurs systématiques, sur maillage identique et indépendant, avec niveaux d’oracles explicites.
3. Convergence spatiale/temps/troncature systématique sur cas simples et complexes.
4. Réévaluation globale des maturités et rapprochement registry/runtime/décisions.
5. Grandes campagnes de stress, contact, postbuckling et refinement sur les routes historiques.
6. Scaling HPC général, répartition MPI et études de mémoire de workloads représentatifs.
7. Dashboards, observatoires, rapports automatiques transverses et normalisation globale des preuves.
8. Migration prévue des façades legacy, selon décision de compatibilité spécifique.

### I3. À exclure de 0.2.12 sans les promettre automatiquement pour 0.3.0

Plasticité multiplicative, mortar/contact finite sliding général, impact, explicite, GPU, nouveaux éléments majeurs, arbres rotatifs solides, roulements hydrodynamiques, rotor nonlinear/rubbing, centrifugation générale et QEP distribué sont des **chantiers de capacité distincts**. Une v0.3.0 principalement de validation ne doit pas devenir implicitement leur implémentation. Ils relèvent de releases ultérieures ou d’un autre scénario explicitement choisi.

**G03 archive et WP14 :** préserver leurs statuts et la politique des artefacts sélectionnés. Les rouvrir seulement sur un scope dédié explicitement décidé ; ne pas supposer que 0.3.0 « effacera » un échec de diffusion. Le contenu public du rapport n’extrait pas les données historiques à l’origine des constats d’archive.

### I4. Fondations utiles à la future validation, déjà proportionnées

Introduire uniquement les identités nécessaires aux nouveaux opérateurs/bases/canaux et aux états NL touchés ; les métriques signées avec unités/repère ; la séparation solve/truncation/evidence/maturity ; les petits manifests du scope 0.2.12. Réutiliser `verification/v2/execution_identity.py`, `resume.py`, runners et projections existants. [S30]

Pour 0.3.0, ces choix permettront de remplacer l’oracle sans modifier les noyaux, comparer un nombre de modes ou un maillage différent, et produire des rapports sur les mêmes observables. Pas de nouveau framework de campagne, database ou dashboard en 0.2.12.

## J. Performance et risques

### J1. Limitations de performance observées

**Mesure historique QEP, pas nouveau benchmark :** le fichier `wp05_dense_characterization.json` donne, sur matrices synthétiques SPD/skew et Windows/BLAS 1 thread, trois répétitions par taille :

| DDL physiques n | Dimension du pencil | Temps médian historique | Pic RSS historique maximal |
| ---: | ---: | ---: | ---: |
| 50 | 100 | 0,0457 s | 74,5 MB |
| 100 | 200 | 0,151 s | 78,5 MB |
| 250 | 500 | 2,18 s | 102,9 MB |
| 500 | 1 000 | 25,3 s | 186,4 MB |
| 1 000 | 2 000 | 271,2 s | 516,8 MB |

MB décimaux ; RSS de processus, pas seule taille des matrices. Ces données caractérisent un solveur dense sur une fixture numérique, **pas la physique d’un rotor réel**. [S19]

**Calcul :** 101 vitesses à 271,2 s/solve représenteraient environ **7,61 h**, avant assemblage/tracking/export. C’est une multiplication hypothétique, pas un sweep mesuré. Les coûts dépendent du spectre et de l’environnement ; ne pas extrapoler un plafond validé au-delà de n=1 000.

Le pencil dense 2n et ses vecteurs coûtent au moins O(n²) mémoire ; les étapes d’eigensolve sont lourdes. Les temps complets ci-dessus incluent aussi les diagnostics : ne pas en déduire une loi empirique universelle O(n³). Retenir tous les raw modes à chaque vitesse coûte O(Sn²) ; l’orchestration current Campbell et la sérialisation peuvent devenir significatives.

**Conséquence :** si B est choisi, une caractérisation et un plafond de taille explicite deviennent structurants. QEP sparse ou QEP projeté sont des sous-projets, avec contrat d’extraction partielle ou erreur de projection propre. L’optimisation des assemblages seuls ne résout pas le plafond dense.

### J2. Gains plausibles du scénario A, avec hypothèses

Direct harmonique : assemblage + S factorisations d’impédances différentes + S résolutions. Réduit : préparation + extraction r modes + projection + S résolutions r×r ou diagonales + reconstruction demandée. **La même LU ne peut pas être réutilisée telle quelle entre deux fréquences différentes.** À une même fréquence, elle peut servir plusieurs RHS, après support complexe explicite ; `ReusableSparseFactorization` actuel caste en float et ne doit pas être recyclé aveuglément. [S08, S17]

Pour Newmark direct à pas constant, la factorisation effective est déjà réutilisée. Le gain réduit porte donc sur résolutions, projections/reconstructions et réutilisation des modes entre excitations, pas sur la suppression d’une factorisation par pas qui n’existe pas dans le chemin actuel.

| Objet | Calcul d’ordre de grandeur | Implication |
| --- | --- | --- |
| Base Φ float64 | 8Nr octets | N=100 000, r=100 → 80 MB ; N=1 000 000, r=200 → 1,6 GB, hors matrices/copies |
| Harmonique complet complex128 | 16NS octets | N=100 000, S=500 → 800 MB pour U seul, hors JSON/objets |
| Sorties p sondes | O(pr) stockage du mapping, O(pS) sorties | Pertinent quand p≪N ; ne dispense pas de stocker Φ pour réutilisation générale |
| Réponses modales diagonales | O(Sr) après projections | Valable Rayleigh/ζj et base propre ; pas pour C réduit plein |
| Projection / base | Coût initial non négligeable, taille dépendante | Peut annuler le gain sur petit S ou petit N ; aucun speedup universel chiffré sans mesure |

Le point mort est `C_initial_reduit / (C_par_cas_direct − C_par_cas_reduit)` lorsque le dénominateur est positif. Le rapport futur doit publier ces trois coûts séparément. Objectif de démonstration : **au moins ×3 en phase réponse** sur un sweep représentatif choisi avant mesure, erreur bornée sur les observables. Cet objectif n’est pas une promesse et ne doit pas entraîner une troncature moins fidèle pour « passer » ; un gain plus faible peut conduire à réduire le claim performance sans invalider la capacité mécanique.

Pas de chantier HPC/GPU recommandé. La valeur de 0.2.12 vient de réutiliser et résoudre un problème de plus petite dimension correctement, pas d’ajouter un backend sans workload.

### J3. Registre des risques

| Niveau | Risque | Traitement et arrêt explicite |
| --- | --- | --- |
| **HIGH** | Cache/base/restart associés à une physique différente | Empreinte et mutation guard avant reuse ; ne pas accepter une reprise legacy non prouvée |
| **HIGH** | Réponse « PASS » mais modes tronqués insuffisants | Différencier résidu et erreur de troncature ; comparaison r/2r ; limitations visibles |
| **HIGH** | Maturité inherited de méthode classique | Classification method-specific ; aucune promotion sur test mécanique isolé |
| **HIGH** | SHOULD coques élargissant le scope vers DAE général | Retrait WP12 si formulation/reconstruction dépasse budget |
| **HIGH** | Tangente symétrisée différente de la dérivée ou sensible à l’origine | WP16 : mesure directionnelle, pas fondé sur géométrie relative, correction justifiée ; restriction explicite du cas si formulation hors budget |
| **HIGH** | Contrat de contrainte NL ambigu dans anciennes sorties | WP15 : mesure/repère/version, lecteurs historiques, migration documentée ; pas de changement silencieux |
| **HIGH** | Double bloc consommant les options et dégradant la clôture | Réserver +30–45 unités au NL ; couper SHOULD avant corrections nécessaires ; replanifier si défaut majeur |
| **MEDIUM** | Repère/signe de base et phase harmonic | Convention unique, SDOF et équivalence de forces cohérentes |
| **MEDIUM** | ζ différents pour modes dégénérés | Loi invariante par cluster ; rejeter options non invariantes |
| **MEDIUM** | Correction statique hors validité ou appliquée au temps | Option harmonic-only ; fréquence et observable de confiance explicites |
| **MEDIUM** | Mémoire Φ ou export supérieur au budget | Estimation préalable ; allocation bornée ; probes/full explicit ; aucune conversion N×N |
| **MEDIUM** | Compatibilité checkoints durcie | Ancienne lecture possible ; reprises incomplètes refusées avec motif versionné ; changement documenté |
| **LOW** | Noms API provisoires/documentation | Contrat figé avant code consommateurs ; legacy conservé |
| **LOW** | Packaging et metadata | Réutiliser checks existants et source/hash du nouveau candidat |

Les niveaux sont qualitatifs et prospectifs. Aucune fréquence d’incident disponible ne permet de calculer des probabilités crédibles.

## K. Charge relative et politique de coupe

Tailles : SMALL = tâche locale et faible dépendance ; MEDIUM = plusieurs modules/contrats ; LARGE = chaîne numérique et essais ciblés ; VERY_LARGE = formulation/couplage substantiel avec forte incertitude. Elles ne sont pas des durées.

| WP du bloc dynamique MUST | Taille | Part du bloc dynamique / unités sur base 100 | Principal déterminant |
| --- | --- | ---: | --- |
| WP00 | SMALL | 3 % | Freeze et sélection des non-régressions |
| WP01 | LARGE | 12 % | Identités physiques, immutable snapshot, checkpoint |
| WP02 | LARGE | 14 % | Base, damping, compatibilité eigensolver |
| WP03 | MEDIUM/LARGE | 10 % | Correction statique et troncature |
| WP04 | LARGE | 12 % | Réponse complexe/projection |
| WP05 | LARGE | 14 % | Temporalité, état, reprise |
| WP06 | MEDIUM | 9 % | Schema et charges multi-input |
| WP07 | MEDIUM/LARGE | 10 % | Masse et repère excitation de base |
| WP08 | MEDIUM | 7 % | Résultats/probes/politique de maturité |
| WP09 | MEDIUM | 5 % | Campagne ciblée finale et performance |
| WP10 | SMALL/MEDIUM | 4 % | Publication et preuves installées |
| **Sous-total dynamique MUST** | **Grand projet cohérent** | **100 unités / 100 % du bloc initial** | **Aucune garantie de calendrier** |

Les tests unitaires, analytiques et d’intégration de chaque WP sont inclus dans sa charge. Les 5 % de WP09 concernent la consolidation finale ; **ce n’est pas la totalité du travail de vérification**. Estimation transversale : environ **20–30 %** du MUST sera consacré aux tests ciblés et diagnostics, déjà inclus dans les 100 unités du bloc dynamique. Les coûts NL ci-dessous incluent eux aussi leurs tests directs.

| WP NL MUST ajouté | Taille | Unités sur la base initiale de 100 | Principal déterminant |
| --- | --- | ---: | --- |
| WP15 — Mesures/contrat résultats | MEDIUM | +8–12 | Transformations, consommateurs et compatibilité de sortie |
| WP16 — Tangentes numériques | LARGE | +14–21 | Vérification indépendante, robustesse du pas et corrections observées |
| WP17 — États/convergence/scope | MEDIUM/LARGE | +8–12 | Chemins de rejet/reprise et matrice de limites |
| **Sous-total NL MUST** | **Bloc réservé** | **+30–45** | **Environ 23–31 % du total révisé** |
| **Total MUST A+NL** | **Deux blocs obligatoires** | **130–145** | **Estimation, sans délai garanti** |

La part NL vaut 30/130≈23 % à la borne basse et 45/145≈31 % à la borne haute. Réserver environ un quart à un tiers de l’effort obligatoire. Cette réserve couvre une correction bornée ; si la vérification de tangente impose de remplacer la formulation, le chiffrage doit être révisé.

| WP optionnel | Taille | Surcoût estimé sur la base initiale de 100 |
| --- | --- | ---: |
| WP11 generalized-alpha | LARGE | +12–20 unités |
| WP12 coques | LARGE / risque VERY_LARGE | +18–35 unités |
| WP13 Campbell préparé | MEDIUM | +5–10 unités |
| WP14 solid stress snapshots | MEDIUM | +8–15 unités |

Tous les SHOULD réunis ajouteraient toujours **43–80 unités**, au-delà du MUST révisé : total **173–225 unités**. Avec le volet NL obligatoire, limiter les options à **+15–20 unités** et une extension choisie, soit **145–165 unités** pour une release utilisant cette enveloppe optionnelle. Ne pas imputer les corrections NL au budget des options.

**Sensibilité :** si WP01–WP02 coûtent ×1,5 et WP05/WP07 ×2, le MUST passe de 100 à **137 unités**, les autres WPs inchangés. Si seulement WP01–WP02 doublent, total **126**. Ajouter le bloc NL estimé +30–45 donne respectivement **167–182** ou **156–171 unités** pour le MUST révisé. Ces calculs rendent visible où l’estimation est fragile. Pas d’intervalle probabiliste prétendument précis.

Ordre de coupe : COULD, puis WP12, puis WP11/WP14 selon usage ; WP13 seulement si il perturbe les contrats. Ne pas couper les gardes d’identité, conventions, équivalences full basis, corrections de mesures/tangentes NL ou détection des erreurs pour tenir un budget. Si le MUST lui-même dépasse durablement le budget, replanifier le calendrier/scope explicitement plutôt que publier une moitié de chaîne.

## L. Release score et décision

### L1. Scores initiaux et effet du volet NL ajouté

Notes sur **5**, estimations de décision. Le tableau ci-dessous décrit A avant ajout NL ; le score révisé A+NL est donné ensuite. Pour risques et charge de validation, 5 signifie plus lourd.

| Critère demandé | Note | Interprétation |
| --- | ---: | --- |
| Scientific value | **3/5** | Formulations établies ; valeur dans cohérence, troncature et propriétés, peu de nouveauté scientifique intrinsèque |
| User value | **5/5** | Réponses réutilisables et excitations concrètes sur plusieurs familles |
| Differentiation | **3/5** | Transparence/identités/limites intéressantes ; techniques déjà présentes chez des solveurs établis |
| Architecture quality | **4/5** | Extraction ciblée, reuse et identité ; architecture universelle volontairement évitée |
| Implementation risk | **3/5** | Moyen ; phases, repère, cache et troncature demandent une vraie conception |
| Validation burden | **3/5** | Modérée, ciblée ; 7 fixtures plus variations/tests, sans campagne générale |
| Release coherence | **5/5** | Base/opérateurs/excitations/réponses/observables forment un seul workflow |

Ne pas moyenner directement bénéfices et risques sans inverser le sens. À titre d’aide à décision : pondérer user 25 %, science 15 %, differentiation 10 %, architecture 15 %, coherence 15 %, faible risque 10 %, faible charge de validation 10 %. Convertir les deux derniers en `6−note` donne **3,95/5** pour A. Ce résultat dépend des poids, pas d’une preuve d’optimalité.

| Scénario | V / S / D / Architecture / Cohérence | Risque / charge validation | Score pondéré indicatif |
| --- | --- | --- | ---: |
| A | 5 / 3 / 3 / 4 / 5 | 3 / 3 | **3,95** |
| B | 4 / 5 / 4 / 4 / 5 | 5 / 4 | **3,80** |
| C | 5 / 5 / 4 / 3 / 5 | 5 / 5 | **3,80** |
| D | 4 / 5 / 4 / 4 / 4 | 4 / 4 | **3,75** |

**Scénario retenu révisé A+NL :** garder les notes valeur utilisateur/science/différenciation/architecture à 5/3/3/4, ramener la cohérence à 4 et augmenter risque/charge de validation à 4/4. Avec les mêmes poids, le score indicatif devient **3,60/5**, contre 3,95 pour A seul. Deux workflows et des corrections de tangente augmentent la charge ; il serait trompeur de garder le score initial inchangé. Cet ajout répond à une priorité explicite de remise à niveau du non linéaire, que le score générique initial ne représentait pas. Il ne devient pas le scénario C : aucun intégrateur temporel NL n’est ajouté.

L’écart faible des scores initiaux montre que **la recommandation n’est pas robuste à n’importe quel besoin utilisateur**. La charge relative et le nombre de formulations nouvelles départagent A lorsque le besoin reste général. Valoriser davantage science/rotor et disposer d’un oracle externe prêt peut rendre B préférable. Une science notée 5 n’équivaut pas à un choix plus rentable.

### L2. Compatibilité explicite

| Surface | Décision recommandée |
| --- | --- |
| Backward compatibility | Toutes méthodes/defaults existants conservés ; nouvelles méthodes opt-in ; aucun auto-switch réduit selon taille |
| Python | `qf_solver` conservé ; `solve_model`, `load_model`, `save_result` inchangés ; helpers nouveaux PROVISIONAL |
| CLI | Commandes et exit codes actuels ; options/documentation additives ; nouvelles routes refusent scopes non supportés |
| Formats modèles | JSON v1 ancien toujours accepté ; nouveaux champs explicites validés ; subset INP inchangé |
| Serialized results | Schéma nouveau versionné pour modal-response/probes ; real/imag explicites ; mesures de contraintes NL corrigées avec version de sémantique et migration explicite, lecteurs historiques préservés |
| Checkpoints | Nouvelle identité/version ; lecture historique préservée si possible ; reprise legacy incomplete fail-closed et documentée |
| Deterministic results | Comparer valeurs/observables/sous-espaces à tolérance ; ne pas exiger bitwise equality entre versions BLAS ; snapshot et execution key fixés |
| Qualification contracts | Enregistrements historiques immuables ; nouveaux scopes séparés ; G03/WP14 et ambiguïté 100 rad/s préservés |

### L3. Réponse à la question finale

**La proposition révisée de v0.2.12 combine réponses dynamiques réduites, excitations enrichies et mise à niveau nécessaire du non linéaire statique existant.** Elle exploite K/M, modal, Newmark, harmonic, charges et résultats existants, tout en ajoutant des usages réellement nouveaux : résoudre dans une base réutilisable, imposer des déphasages, répondre à une accélération uniforme de base et maîtriser le résidu statique harmonique.

WP15–WP17 ajoutent un second livrable obligatoire : mesures de contraintes cohérentes, tangentes numériques contrôlées et états/convergences/scopes fiables. Réserver +30–45 unités au NL, pour un MUST total de 130–145 ; réduire les options en conséquence. Ce périmètre ne prétend pas livrer le transitoire NL ni supprimer toutes les limitations contact/finite-strain.

Les points certains sont les capacités/limites du snapshot, les 118 tests ciblés passants, l’omission confirmée de signature Newmark et les doubles assemblages Campbell. Les coûts, scores et gains futurs restent des estimations. Le ratio valeur/coût exact dépendra des cas d’usage et du coût de la base. **Aucune promotion globale de maturité et aucune campagne générale de validation ne sont nécessaires pour définir ce périmètre.** Les grandes bibliothèques, comparaisons inter-solveurs et consolidations de preuves restent à v0.3.0.

## Sources et traçabilité

Tous les liens de code/documents ci-dessous sont figés au commit audité `e367fe58…`, pas à un `main` mouvant. Le changelog et les décisions plus récentes priment sur un ancien fichier de planning ; notamment `docs/verification/0_2_9/known-limitations.md` est un document de planification 0.2.9, pas une photographie actuelle autonome.

| ID | Sources réellement utilisées |
| --- | --- |
| S01 | [CHANGELOG](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/CHANGELOG.md) ; tags/diffs Git de 0.2.8 à 0.2.11 ; [releases](https://github.com/emptiesvoid-cloud/QF_solver/releases) |
| S02 | [Publication verification 0.2.11](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/qualification/0_2_11/publication_verification_0_2_11.json) |
| S03 | [Router](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/router.py) ; [settings](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/settings.py) |
| S04 | [API public](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/api/public.py) ; [exports](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/api/__init__.py) ; façade `src/qf_solver/__init__.py` |
| S05 | [Architecture](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/docs/architecture.md) ; [API stability](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/docs/reference/api_stability.md) |
| S06 | [Element registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/elements/registry.py) |
| S07 | [BEAM2 formulation](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/elements/beam/beam2.py) ; [discrete entities](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/elements/discrete.py) |
| S08 | [Newmark solver](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/dynamic.py) ; `_checkpoint_signature_payload`, `_validated_newmark_parameters` |
| S09 | [Dynamic reduction](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/dynamic_reduction.py) ; [controls](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/dynamic_controls.py) ; `dynamic_history.py` |
| S10 | [Nonlinear solver](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/nonlinear/solver.py) ; [constitutive contracts](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/nonlinear/contracts.py) |
| S11 | [Nonlinear assembly](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/assembly/nonlinear.py) ; [geometric route](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/geometric_nonlinear.py) |
| S12 | [Solid constitutive materials](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/materials/solid.py) ; [nonlinear overview](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/docs/mechanics/nonlinear-overview.md) |
| S13 | [Contact entities](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/contact/entities.py) ; [contact solver](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/contact/solver.py) |
| S14 | [QEP formulation](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/qep.py) |
| S15 | [Rotating modal](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/rotating_modal.py) ; [validator](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/rotating_input_validator.py) ; [disk gyro assembly](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/assembly/rotating_disk_gyro.py) |
| S16 | [Campbell solver](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/campbell.py) ; [tracking tests](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/tests/unit/test_modal_tracking.py) |
| S17 | [Harmonic solver](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/harmonic.py) ; [linear solver/reusable LU](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/solvers/linear.py) |
| S18 | [Buckling route](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/buckling.py) ; [modal route](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/analyses/modal.py) |
| S19 | [Dense QEP characterization](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/qualification/0_2_11/wp05_dense_characterization.json) |
| S20 | [WP01 capability matrix](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/qualification/0_2_11/wp01_capability_matrix.json) ; fiche de baseline, non un remplacement des ajouts gyro ultérieurs |
| S21 | [HEX8 corotational owner acceptance](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/qualification/0_2_9/wp09_owner_acceptance_r3.json) |
| S22 | [HEX20/TET10 extension acceptance](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/qualification/0_2_9/wp09_hex20_tet10_owner_acceptance.json) |
| S23 | [Historical open items](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/qualification/0_2_11/wp01_historical_open_items.md) ; [current limitations](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/docs/etat/limites.md) |
| S24 | [Campbell post](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/post/campbell.py) ; [rotating mechanics scope](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/docs/mechanics/rotating-modal.md) |
| S25 | [Paired assembler](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/assembly/assembler.py) ; [plan and fingerprint](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/assembly/plan.py) ; `assembly/sparse.py` |
| S26 | [Load entities](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/loads/entities.py) ; [load schema](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/io/load_schema.py) |
| S27 | [Results](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/results.py) ; [qualification policy](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/core/qualification.py) ; `core/result_serialization.py` |
| S28 | [INP importer](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/io/inp_reader.py) ; `io/mixed_results_hdf5.py`, `io/vtu_writer.py`, `io/schema_analysis.py` |
| S29 | [Packaging](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/pyproject.toml) ; `large/multifamily.py`, `large/memory.py` ; inventaire voie `large` |
| S30 | [Prospective V&V identity](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/verification/v2/execution_identity.py) ; [safe resume](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/verification/v2/resume.py) |
| S31 | [Corotational J2 kernel](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/elements/solid/corotational_j2.py) ; [Total-Lagrangian J2 kernel](https://github.com/emptiesvoid-cloud/QF_solver/blob/e367fe58b2b9ebb4aef321424ca775e80e82d9ca/src/solveur/elements/solid/total_lagrangian_j2.py) |

**Périmètre exact des tests exécutés :** `test_rotating_disk_gyro`, `test_rotating_modal_preflight`, `test_campbell`, `test_modal_tracking`, `test_dynamic_controls`, `test_dynamic_initial_conditions`, `test_dynamic_checkpoint`, `test_rotating_modal_public_api`, `test_assembly_plan`, `test_nonlinear_assembly_plan`, `test_solid_material`, `test_total_lagrangian_tet4`, `test_total_lagrangian_hex8`, `test_corotational_j2`, `test_geometric_nonlinear_contracts`, `test_nonlinear_state_transaction_contract`, `test_harmonic_shell_post`. Le seul `test_rotating_modal_public_api` est sous integration ; les autres fichiers listés sont sous unit. Les fixtures utilisées dans les deux diagnostics sont celles de `test_dynamic_controls.py` et `test_campbell.py`.
