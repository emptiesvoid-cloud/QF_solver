---
doc_id: DOC-BACKEND-022-002
revision: 0.1
status: draft
applicable_version: 0.2.2a0
reviewer: ""
approver: ""
---

# Plan V&V 0.2.2 alpha : assemblage, scaling et couverture

## Objet et statut

Ce document prépare la campagne de vérification et validation du backend
numérique de QF Solver. Il ne constitue ni une qualification, ni une décision
de maturité, ni une autorisation de publication. Aucun changement de
formulation d'élément n'est recherché dans ce lot.

Les objectifs sont les suivants :

1. mesurer séparément le coût de l'assemblage, de la réduction, de la
   résolution et du post-traitement ;
2. supprimer les copies sparse évitables sans changer les matrices produites ;
3. rendre le choix de méthode et de backend explicable et surchargeable ;
4. vérifier la non-régression des résultats statiques, modaux, transitoires et
   harmoniques ;
5. faire progresser la couverture branchée globale de `86 %` vers `90 %`
   par ajouts de tests utiles, et non par diminution des exigences. Ce gate
   est maintenant atteint à `90,195 %` après la campagne de contrats et la
   régression complète.

## Cartographie des chemins

| Analyse | Assemblage | Réduction/opérateur | Résolution | Mesures à conserver |
| --- | --- | --- | --- | --- |
| Statique linéaire | `GlobalAssembler` ou `ChunkedScipyAssembler` | contraintes/MPC puis système réduit | direct, CG, MINRES, GMRES | temps par phase, NNZ, résidus, réactions |
| Modal | `GlobalAssembler` K/M | réduction et condensation éventuelle | `eigsh`/`lobpcg`, SLEPc optionnel | fréquences, résidus propres, orthogonalité M |
| Newmark | K/M puis matrice effective | mêmes contraintes à chaque pas | factorisation réutilisée ou itératif | pas, énergie, résidus, coût factorisation |
| Harmonique | K, M, C et opérateur complexe | réduction par fréquence | résolution sparse complexe SciPy | fréquences, résidus, coût par fréquence |
| TET4 grand modèle | assembleur chunké ou PETSc AIJ/BAIJ | Dirichlet distribué | CG/KSP ou matrix-free | NNZ, chunks, RAM, temps MPI, convergence |

Les formulations d'éléments restent en dehors de la couche de sélection. Un
élément fournit ses matrices locales ; l'assemblage et la résolution ne
doivent pas connaître sa démonstration particulière.

## Architecture cible par couches

```text
Formulation élémentaire
        -> AssemblyPlan / kernel local
        -> SparseAssemblyAccumulator ou matrice native PETSc
        -> ConstraintReduction / opérateur sparse
        -> LinearSolverBackend ou EigenSolverBackend
        -> diagnostics de convergence et ressources
        -> résultat, audit et preuve V&V
```

### Couche d'assemblage

La première optimisation appliquée est l'accumulation CSR pairwise commune,
dans `solveur.core.sparse_accumulator`. Elle évite l'addition répétée d'un
nouveau chunk à une matrice globale déjà grande. Le chemin standard et le
chemin SciPy grand modèle utilisent maintenant cette même primitive.

La tranche realisee introduit `AssemblyPlan`, construit une fois par couple
`(model, dofs)`. Il conserve les éléments suivants :

- référence de la spécification d'élément ;
- connectivité et indices DDL globaux ;
- nombre d'entrées locales ;
- groupe de matériau et possibilité de cache ;
- nombre d'entrées locales, avec le temps de préparation du plan.

Le plan porte aussi une empreinte SHA-256 déterministe du modèle, des DDL et
du `chunk_size` effectif. Elle couvre notamment les coordonnées, éléments,
matériaux, blocages, ressorts, masses, MPC/RBE, contacts et paramètres du
modèle sérialisables. La vérification de réutilisation exige l'identité de
l'objet déjà préparé, l'égalité des dimensions et DDL, puis l'égalité de cette
empreinte et du découpage demandé. Une modification du modèle ou du chunk
invalide donc explicitement le plan ; aucune matrice locale n'est conservée
par cette empreinte.

La préparation réduit les appels répétés à `ElementRegistry`, aux conversions
de listes de DDL et aux recherches de coordonnées pour K/M. Elle ne met pas en
cache une matrice locale lorsque l'orientation, la géométrie ou l'état matériel
la rendent variable. Les analyses modal, Newmark et harmonique reutilisent
egalement ce plan dans une paire K/M. Dans chaque chunk, le motif temporaire de
DDL (`rows`, `cols`) est partage entre les deux matrices, alors que les valeurs
de K et M restent separees. Aucun motif global n'est conserve afin de ne pas
transformer la mutualisation en nouvelle pression memoire. Les diagnostics
`paired_assembly=true` et `shared_chunk_pattern=true` rendent cette propriete
verifiable. Le benchmark K/M confirme un gain de temps local, mais aucune
economie memoire n'est revendiquee : la paire conserve deux flux de valeurs et
son estimation temporaire reste plus conservative.

### Couche de résolution

`solveur.core.solver_backend` choisit le backend ;
`solveur.core.linear_policy` choisit la méthode ;
`solveur.core.linear_methods` exécute la méthode et produit les diagnostics.
La règle de base est :

- petit système : direct sparse si l'estimation mémoire l'autorise ;
- réel SPD démontré ou déclaré explicitement : CG ;
- réel symétrique sans preuve SPD : MINRES ;
- non symétrique : GMRES ;
- modal généralisé : `eigsh`/`lobpcg`, ou SLEPc si explicitement sélectionné
  et disponible ;
- backend `auto` : SciPy par défaut, PETSc seulement avec un signal de taille
  ou une préférence explicite et une trace de sélection.

Chaque exécution doit conserver le backend demandé, le backend utilisé, la
méthode, le nombre d'itérations, les résidus initial/final/relatif, la
tolérance et la raison de terminaison. Une non-convergence doit être une
erreur explicite ou un état `not_converged`, jamais un résultat silencieux.

## Diagnostic causal de l'assemblage

Les hypothèses à mesurer, dans cet ordre, sont :

1. **kernel local** : temps passé dans la formulation élémentaire ;
2. **construction du motif** : répétitions `repeat/tile`, conversion des DDL ;
3. **conversion sparse** : coût `COO -> CSR`, tri et fusion des doublons ;
4. **fusion des chunks** : nombre de fusions et mémoire temporaire ;
5. **discrètes et contraintes** : ajout des ressorts/masses puis réduction ;
6. **réutilisation** : matrice effective Newmark et factorisation constante.

Les métriques attendues sont `assembly_seconds`, les temps par phase, le
nombre de chunks, le pic d'entrées d'un chunk, `nnz` final, la mémoire sparse
estimée et, lorsque disponible, un pic RSS séparé du temps de résolution.
Le chemin standard accepte aussi `assembly_memory_budget_mb` et
`enforce_assembly_memory_budget=true` : l'estimation conservatrice du chunk
est faite avant allocation, puis l'exécution avertit ou refuse explicitement
selon la politique choisie. Ce garde-fou ne change pas la valeur par défaut.
Une optimisation ne sera acceptée que si elle conserve la matrice à une
tolérance numérique documentée et améliore au moins une mesure sans dégrader
les autres au-delà de la marge définie par la campagne.

## Idees d'architecture pour la suite

Les options suivantes sont compatibles entre elles et peuvent etre introduites
par petits lots :

1. conserver `AssemblyPlan` comme contrat immutable de connectivite et de DDL,
   puis ajouter un cache local de noyaux uniquement pour les elements dont la
   matrice locale est independante de l'etat et de l'orientation ;
2. exposer une interface `SparseOperator` commune aux matrices CSR et aux
   `LinearOperator`, afin que modal, Newmark et les grands modeles puissent
   eviter une materialisation dense sans dupliquer la politique de resolution ;
3. separer explicitement `AssemblyBackend`, `LinearSolverBackend` et
   `EigenSolverBackend`, avec un objet de diagnostics commun et un adaptateur
   PETSc/SLEPc optionnel ;
4. remplacer les copies repetitives de DDL par des index locaux compacts dans
   chaque chunk, tout en conservant des indices globaux int64 au point de
   fusion. Cette option doit etre mesuree sur la memoire et la vitesse avant
   d'etre activee ;
5. ajouter un plan de reutilisation de factorisation indexe par une empreinte
   des operateurs, de l'amortissement et du pas de temps. Une invalidation
   stricte doit interdire toute reutilisation apres changement de K, M, C ou
   des contraintes ;
6. produire un budget de ressources avant allocation, puis choisir entre
   direct, iteratif ou PETSc selon `nnz`, memoire estimee, symetrie et taille.
   La decision doit rester surchargeable par l'utilisateur.

## Campagne de non-régression

### Niveau A : identité d'assemblage

Pour chaque cas représentatif, comparer l'ancienne référence archivée et le
nouveau chemin sur :

- dimensions, symétrie et nombre de non-zéros ;
- norme de la différence `K_new - K_ref` et `M_new - M_ref` ;
- équilibre des charges et réactions ;
- patch test et énergie linéaire ;
- empreinte numérique lorsque le format est stable.

Le test ne doit pas comparer des arrondis textuels ; il doit comparer des
grandeurs numériques et accepter uniquement une tolérance explicitement
justifiée.

### Niveau B : analyses

La suite rapide doit couvrir au minimum un cas TET4, un TET10, un MITC3, un
MITC4, un BEAM2 et une entité discrète pour :

- statique linéaire ;
- modal et résidus propres ;
- Newmark avec et sans amortissement lorsque la branche est couverte ;
- harmonique sur un petit balayage fréquentiel.

Les campagnes V&V existantes restent séparées des tests rapides. Elles sont
relancées après une modification du chemin partagé, pas après un changement
isolé de documentation.

### Niveau C : scaling

Le script manuel `scripts/benchmark_sparse_scaling.py` mesure le backend de
résolution sur environ `1k`, `10k` et `100k` DDL. Le script
`scripts/benchmark_assembly_scaling.py` mesure en plus l'assemblage TET4
chunké aux mêmes ordres de grandeur. Le cas `1M` reste manuel et conditionné
par la mémoire disponible.

Le premier point de comparaison instrumenté d'assemblage est archivé dans
`qualification/benchmarks/qf_solver_0_2_2_assembly_scaling_reference.json`.
Le chemin SciPy grand modèle réutilise maintenant le cache matériau entre les
chunks et sépare dans `assembly_phase_seconds` le kernel élémentaire de la
conversion COO/CSR. Sur `107811` DDL, la médiane de trois répétitions donne
environ `0,860 s` de kernel, `0,714 s` de conversion COO/CSR, `0,093 s` de
fusion et `0,024 s` de finalisation. Le champ `chunk_build` reste la somme du
kernel local et de la conversion sparse, et ne doit pas être interprété comme
le seul coût de la formulation élémentaire.

Le runner manuel `scripts/benchmark_assembly_chunk_sweep.py` compare aussi les
tailles `1024`, `2048`, `4096`, `8192` et `16384` sur le même cas `100000` DDL.
La médiane locale est respectivement de `1,937 s`, `1,775 s`, `1,706 s`,
`1,689 s` et `1,673 s`. Le meilleur temps ne gagne qu'environ `2 %` par rapport
à `4096`, alors que le pic de triplets passe de `143055` à `448551`. La valeur
par défaut ne change donc pas : le sweep prouve un compromis temps/mémoire,
pas une justification suffisante pour augmenter globalement le chunk.
Cette preuve est archivée dans
`qualification/benchmarks/qf_solver_0_2_2_assembly_chunk_sweep_reference.json`.

Le candidat de construction CSR directe est comparé au baseline COO/CSR dans
`qualification/benchmarks/qf_solver_0_2_2_assembly_scaling_comparison.json`.
Les NNZ restent identiques aux trois tailles et la différence numérique est
nulle. Le changement de temps médian global reste toutefois dans le bruit de
la campagne (`+2,15 %` sur cet échantillon), donc le candidat ne constitue pas
encore une preuve de gain de performance ; il est conservé pour sa réduction
d'un objet intermédiaire, avec une nouvelle campagne nécessaire avant toute
promotion de performance.

Chaque ligne de benchmark doit contenir : DDL, éléments, NNZ, chunk size,
temps d'assemblage, temps de résolution, méthode, backend, itérations, résidu
final et estimations mémoire. Les benchmarks lourds ne doivent pas devenir
des tests CI obligatoires.

La comparaison dédiée du motif K/M est préparée par
`scripts/benchmark_standard_km_pair.py`. Elle rejoue le même modèle avec
l'assemblage séparé puis groupé, compare K et M par norme relative et conserve
les phases, NNZ, ratio de temps et estimations mémoire. Son résultat attendu
est archive dans
`qualification/benchmarks/qf_solver_0_2_2_standard_km_pair_reference.json`.

Le runner `scripts/compare_large_backends.py` exécute la même observable
statique sur SciPy, matrix-free et PETSc lorsqu'il est disponible. Sur le bloc
reproductible de `24` DDL, SciPy et matrix-free passent et donnent un écart de
déplacement de `5,82e-16`; l'exécution locale PETSc est enregistrée `SKIP` car
`petsc4py` n'est pas installé. Cette preuve locale ne ferme donc pas la
comparaison PETSc/BAIJ : une campagne HPC reste nécessaire.
La campagne locale apres compactage des indices a donne les ratios
groupe/separe de `0,916` a 1k DDL, `0,888` a 10k DDL et `0,890` a 100k DDL,
soit environ `8,4 %` a `11,2 %` de temps total economise sur cet environnement.
Les NNZ et les differences
relatives de K et M sont identiques a zero aux trois tailles. L'estimation de
memoire temporaire du chemin groupe est volontairement plus conservative ;
aucun gain memoire n'est revendique sur cette preuve.

## Leviers d'assemblage à tester dans l'ordre

Les mesures 100 k DDL imposent l'ordre suivant :

1. **Réduire le coût du kernel élémentaire.** Tester la vectorisation par
   famille d'éléments et matériau, puis une parallélisation contrôlée du
   kernel. La parallélisation ne doit pas modifier l'ordre des réductions sans
   tolérance numérique documentée.
2. **Réutiliser uniquement les motifs invariants.** Le motif DDL peut être
   réutilisé entre K et M et entre plusieurs résolutions d'un même modèle,
   mais les valeurs locales doivent rester recalculables pour une orientation,
   une géométrie ou un état matériau variable. Toute empreinte de cache doit
   inclure le modèle, les DDL, les contraintes et la configuration de chunk.
3. **Choisir le chunk par budget de ressources.** Un autotuning borné peut
   comparer quelques tailles de chunk à partir du NNZ et de la mémoire
   estimée. Le runner `scripts/benchmark_assembly_chunk_sweep.py` produit
   maintenant une recommandation advisory avec `--memory-budget-mb`, bloque
   si aucune taille mesurée ne respecte le budget et ne modifie pas la valeur
   par défaut de l'assembleur. Sur la référence 100k et un budget de
   `4 000 000` octets, la recommandation est `4096` avec une estimation de
   `3 433 320` octets. Il ne doit jamais allouer un second triplet global pour
   essayer une taille.
4. **Basculer vers matrix-free ou PETSc/BAIJ lorsque le modèle le justifie.**
   Cette voie doit être comparée au chemin SciPy sur la même observable
   mécanique ; elle ne peut pas devenir le défaut sans preuve de précision,
   de mémoire et de reproductibilité.

Le passage CSR direct a été mesuré mais ne montre pas encore de gain global
robuste. Le premier correctif de performance à privilégier est donc désormais
le kernel élémentaire, pas une augmentation aveugle du nombre de chunks. Le
critère de promotion sera un gain médian documenté, une mémoire maximale non
dégradée et une non-régression stricte des matrices, déplacements, réactions
et résidus.

Une seconde configuration est maintenant archivée avec la décomposition
centrée à douze TET4 par cellule et un matériau isotrope distinct. Elle sert de
contrôle de reproductibilité du kernel sur une topologie différente ; comme le
nombre d'éléments et de NNZ change, elle ne doit pas être transformée en ratio
avant/après avec le maillage historique. La comparaison directe des champs et
réactions avec le solveur standard est maintenant fermée sur `1 677` et
`18 357` DDL. Les déplacements, réactions fixées, déformations, contraintes et
von Mises restent finis, avec des écarts relatifs de l'ordre de `1e-13` pour un
seuil contractuel `1e-7`. L'artefact reproductible est
`qualification/benchmarks/qf_solver_0_2_2_large_standard_field_comparison.json`.
Cette preuve vérifie la cohérence mécanique entre chemins d'assemblage ; elle
ne mesure ni le gain de temps ni la capacité à exécuter plusieurs millions de
DDL.

La reutilisation de la matrice effective Newmark est mesuree dans
`qualification/benchmarks/qf_solver_0_2_2_newmark_factorization_reference.json`.
Sur `1 029` et `10 125` DDL, une factorisation est reutilisee pour huit
resolutions, avec des residus dynamiques maximum de `1,28e-11` et `2,21e-11`.
Le seuil de `100k` DDL reste une campagne manuelle, car le cout memoire d'une
LU directe doit etre mesure avant toute generalisation.

## Politique de couverture à 80 %

La couverture globale est un indicateur de garde, pas une preuve physique.
La régression pertinente du 23 août 2026 a produit `1336 passed`,
`107 deselected`, avec `88,67 %` de couverture branchée. Le gate CI retenu est
`80 %`; `90 %` n'est pas un objectif de release. La progression reste
découpée fonctionnellement pour suivre les zones qui doivent encore être
renforcées :

1. porter le backend commun, la politique et l'accumulateur à au moins `95 %`
   de couverture branchée ;
2. porter l'assemblage standard et le chemin grand modèle à au moins `90 %`
   avec cas d'erreur de mémoire, chunk vide, doublons, discrètes et contraintes ;
3. porter l'API publique, les résultats et les diagnostics à au moins `90 %` ;
4. traiter les branches réelles actuellement faibles dans modal, IO schema,
   lecture Gmsh, large solver et géométrie MITC4 ;
5. conserver le seuil global CI à `80 %` avec `--cov-branch` ; tout
   relèvement futur doit être une décision explicite de release ;
6. interdire les exclusions de couverture nouvelles sans justification dans
   le dossier V&V.

Pour les campagnes à partir de `2 000 000` DDL, le gate
`MULTI-MILLION-GATE` impose un backend scalable (`petsc` ou `matrix_free`) et
demande un budget mémoire explicite. Sans budget fourni, le rapport passe en
`WARNING` et interdit de considérer la campagne comme automatiquement prête.
Avec un budget inférieur à l'estimation PETSc indicative, le gate est en
`FAIL`. Ce contrôle est une readiness avant calcul : il ne lance pas le modèle
et reste hors CI rapide.

Les tests de performance ne doivent pas gonfler artificiellement le taux :
ils servent à mesurer, les tests unitaires servent à prouver les contrats et
les tests V&V servent à prouver les grandeurs mécaniques.

## Etat de fermeture au 2026-08-23

| Gate | Etat | Preuve ou limite |
| --- | --- | --- |
| Couverture globale branchee >= 80 % | `PASS` | `1336 passed`, `88,67 %`, `--cov-branch` |
| Non-regression statique/modal/Newmark/harmonique | `PASS` | campagne unit/integration : `1327 passed` |
| Matrices, reactions et champs | `PASS` | comparaisons sparse/large et tests de contrats archivees |
| Diagnostics de convergence et garde memoire | `PASS` | tests cibles et artefacts de readiness |
| Scaling 1k/10k/100k | `PASS` | benchmarks reproductibles et mesures assembleur archivees |
| PETSc multi-rang et multi-million statique TET4 | `PASS_BOUNDED` | quatre cas Docker réels `2M/4M x 2/4 rangs`, `CG+GAMG/BAIJ`, efficacité forte minimale `0,615` |
| SLEPc/modal et dynamique grand modèle | `PASS_BOUNDED` | modal SLEPc jusqu'à `107 811` DDL ; Newmark PETSc/GAMG à `2 044 416` DDL ; tentative modale 2M arrêtée par la limite de ressources |
| Partitionnement graphe | `PASS_BOUNDED` | PT-Scotch à 2M DDL, efficacité forte `0,621` |
| Seconde configuration matérielle | `OPEN_NON_BLOCKING` | la campagne reste limitée à une machine et à une image Docker épinglée |
| Audit documentaire/public | `PASS` | 42 tests documentation, 6 skips explicites, audits publics sans finding |

La tranche logicielle, la cible de couverture et le dossier backend borne sont
donc documentes. Le statut global du dossier reste `draft` : la preuve Docker
ne vaut pas validation generale d'un modal a plusieurs millions, d'une autre
machine ou d'une promotion de maturite.

## Gates de sortie de l'alpha backend

Le chantier restera `draft` tant que tous les points suivants ne sont pas
documentés :

- baseline reproductible avant/après ;
- non-régression statique, modale, Newmark et harmonique ;
- non-régression de la matrice assemblée et des réactions ;
- diagnostics de non-convergence testés ;
- benchmark 1k/10k/100k exécuté ;
- readiness multi-million vérifiée à partir de `2 000 000` DDL avec backend et
  budget mémoire tracés ;
- assemblage grand modèle comparé avec l'ancien chemin ;
- couverture globale mesurée et gate CI à 80 % respecté ;
- limites PETSc/SLEPc, SciPy, matrix-free et conversions denses documentées ;
- aucun chemin de publication, tag ou décision Owner déduit automatiquement.

## Décisions d'architecture proposées

La recommandation est d'avancer par petits lots :

1. accumulateur sparse commun et métriques, déjà appliqués ;
2. `AssemblyPlan` et cache de motif, avec test d'identité ;
3. réutilisation de motif K/M/matrice effective ;
4. opérateurs modaux sans inversion dense et réutilisation de factorisation ;
5. backend PETSc/SLEPc optionnel après benchmark, jamais par obligation ;
6. couverture ciblée et relèvement progressif du seuil ;
7. revue technique locale, puis seulement une revue Owner de release.

Cette séquence limite le risque : l'assemblage peut être accéléré sans
modifier la formulation, et chaque étape est réversible tant que les preuves
numériques ne sont pas comparées.
