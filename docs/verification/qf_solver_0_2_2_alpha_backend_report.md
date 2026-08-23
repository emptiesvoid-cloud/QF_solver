---
doc_id: DOC-BACKEND-022-001
revision: 0.1
status: draft
applicable_version: 0.2.2a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.2 alpha : chantier backend numerique

## Objet

La version 0.2.2 alpha est consacree au renforcement du backend numerique de
QF Solver. Elle ne revendique pas de nouvelle physique majeure : elle vise la
scalabilite, la memoire, la robustesse des solveurs et la tracabilite des
diagnostics, sans modifier les formulations d'elements deja couvertes.

## Architecture avant

Le chemin standard est `analysis -> assembler -> reduction -> solveur ->
resultat`. Le solveur lineaire commun existait deja dans
`solveur.core.linear_methods`, tandis que la politique de choix etait dans
`linear_policy`. Les chemins Newmark et harmonique reutilisaient toutefois
partiellement cette logique, et le modal possedait une chaine specifique
`eigsh/eigh`.

## Architecture introduite

La selection de backend est maintenant centralisee dans
`solveur.core.solver_backend` : SciPy est toujours disponible, PETSc et SLEPc
sont importes uniquement a la demande. La politique accepte `backend=auto`,
`backend=scipy` et `backend=petsc`. Une demande PETSc explicite sans
`petsc4py` produit une erreur explicite ; elle ne bascule jamais silencieusement
vers un autre backend.

L'adaptateur KSP transmet maintenant explicitement les preconditionneurs PETSc
`jacobi`, `gamg`/`amg`, `hypre`, `ilu`, `sor`, `asm` et `bjacobi`. Les alias et
les noms non supportes sont testes sans importer PETSc ; un nom invalide est
rejete avant toute allocation de matrice. Les tests de ce contrat ne constituent
pas une execution HPC et ne ferment donc pas le gate multi-rang.

Le chemin statique accepte `method=auto`. Pour un petit systeme, il choisit un
solveur direct sparse ; pour un systeme plus grand, il utilise les preuves de
symetrie/SPD disponibles pour recommander CG, MINRES ou GMRES. Le choix reste
visible dans le resultat et peut toujours etre surcharge par une methode
explicite.

Les diagnostics lineaires enregistrent desormais le backend, le residu initial,
le residu final, le residu relatif, la tolerance et la raison de terminaison.
L'estimation de memoire distingue le stockage sparse, une factorisation directe
et une representation dense potentielle.

Pour l'assemblage, `solveur.core.sparse_accumulator` est partage par le chemin
standard et le chemin SciPy grand modele. Les chunks sont fusionnes pairwise,
et les resultats grands modeles conservent le nombre de chunks, le pic de NNZ
par chunk, les niveaux d'accumulation et le NNZ final. Le chemin grand modele
ventile maintenant le temps de construction des chunks, de fusion et de
finalisation CSR. Le chemin standard expose en plus les phases du kernel local,
de conversion COO/CSR, de fusion et de reduction des discretes ; la campagne
avant/apres les utilise maintenant pour distinguer le gain de la paire K/M du
cout propre du kernel elementaire.

La chaine modale peut utiliser SLEPc lorsqu'il est disponible et demande, avec
fallback trace vers SciPy pour `backend=auto`. Le chemin dense reste borne par
`dense_modal_max_dofs` et n'est jamais choisi implicitement pour un grand
systeme.

## Tests et non-regression

Le baseline ciblé du chantier a produit `35 passed`. Apres la premiere tranche,
les tests lineaires, modaux, dynamiques et de comparaison ont produit `63
passed`, puis les nouveaux tests de backend et de benchmark ont ete ajoutes.
La regression pertinente de reference a produit `1327 passed, 107 deselected`
avec une couverture branchee de `90,195 %` pour un seuil de `80 %`. Les lots
incrementaux ajoutes ensuite couvrent les helpers d'assemblage sparse, les
controles multi-million, les metriques de scaling MPI simulees et les sorties
file-backed ; la mesure cumulee locale atteint donc la cible de `90 %` dans
les artefacts `coverage.json`/`coverage.xml`. Cette verification locale ne
remplace pas la campagne V&V complete et ne constitue pas une decision Owner.
Les branches PETSc/MPI multi-rangs restent explicitement dependantes d'un
runtime HPC ; elles ne sont pas simulees lorsque les dependances ne sont pas
installees sur l'hote. Une campagne reelle est toutefois archivee dans le
runtime Docker epingle decrite plus bas. Les contrats documentaires locaux
ont produit `42 passed, 6 skipped` et le controle public a conserve le statut
PASS.
Les tests ajoutés aux branches de partitionnement et de comparaison des
préconditionneurs portent ces modules à `92 %` et `91 %`. Les contrats CLI
grand modèle et le contrat KSP mono-rang sont maintenant couverts dans
`tests/unit/test_large_cli_commands.py` et
`tests/unit/test_large_petsc_contract.py`; ils vérifient le câblage et les
métriques sans être comptés comme une preuve HPC. Le déficit global reste
principalement concentré dans les chemins PETSc/MPI multi-rangs et certaines
interfaces natives qui nécessitent leurs dépendances réelles.

## Benchmark de scaling

Le script reproductible suivant est separe de la CI longue :

```powershell
python scripts/benchmark_sparse_scaling.py --output results/scaling_0_2_2/summary.json
```

Il couvre par defaut environ 1k, 10k et 100k DDL et enregistre le nombre de
non-zero, les temps d'assemblage et de resolution, les iterations, les
residus, le backend et les estimations de memoire. Un cas 1M DDL peut etre
lance manuellement avec `--sizes 1000000` si la machine le permet.

Un echantillon numerique reproductible est archive dans
`qualification/benchmarks/qf_solver_0_2_2_sparse_scaling_reference.json`.
Sur cet echantillon, la resolution reste sous `0,04 s` a 100k DDL, le residu
relatif reste sous `4,0e-9`, le stockage sparse est d'environ `4,0 MB` et une
representation dense equivalente est estimee a `80 GB`. Ces chiffres sont un
point de comparaison local, pas une garantie de performance universelle.

Le benchmark d'assemblage TET4 est separe dans
`qualification/benchmarks/qf_solver_0_2_2_assembly_scaling_reference.json`.
Avec un chunk de `4096` et trois répétitions, la médiane instrumentée donne
environ `0,013 s` pour `1029` DDL, `0,138 s` pour `10125` DDL et `1,731 s`
pour `107811` DDL. Le cas `100k` contient `196608` éléments et `3813789`
non-zero finaux. Sur ce dernier cas, le kernel élémentaire représente environ
`0,860 s`, la conversion COO/CSR `0,714 s`, la fusion pairwise `0,093 s` et la
finalisation CSR `0,024 s`. Le temps `chunk_build` est la somme du kernel et
de la conversion sparse. Le cache matériau est réutilisé entre les chunks,
et `AssemblyPlan` sépare la carte DDL du kernel élémentaire. Le plan porte une
empreinte SHA-256 déterministe du modèle, des DDL, des contraintes et du
`chunk_size`; toute modification détectée invalide la réutilisation sans
conserver de matrice locale variable. Les analyses
modal/dynamiques mutualisent le motif temporaire K/M par chunk. Aucun motif
global ni matrice locale variable n'est conservé. La conversion COO/CSR et le
kernel élémentaire restent les deux leviers prioritaires. La comparaison K/M
archivée ci-dessous quantifie le gain réel de la paire sans le confondre avec
un gain mémoire.

Un sweep de taille de chunk sur le même cas `100000` DDL est archivé dans
`qualification/benchmarks/qf_solver_0_2_2_assembly_chunk_sweep_reference.json`.
Les médianes locales vont de `1,937 s` avec `1024` à `1,673 s` avec `16384`,
mais le pic de triplets augmente de `37323` à `448551`. Le gain d'environ `2 %`
ne justifie donc pas de modifier la valeur par défaut. Le runner produit
désormais une recommandation advisory bornée par budget : sur la référence
100k et `4 000 000` octets, il retient `4096` avec un pic estimé de
`3 433 320` octets ; aucune politique automatique globale n'est activée.

La conversion directe `csr_matrix((data, (rows, cols)))` a été essayée comme
remplacement local du passage COO intermédiaire. La comparaison archivée dans
`qualification/benchmarks/qf_solver_0_2_2_assembly_scaling_comparison.json`
confirme l'identité des NNZ et des valeurs, mais ne montre pas encore de gain
de temps global robuste ; elle ne doit donc pas être présentée comme une
accélération validée.

Le kernel géométrique TET4 a ensuite remplacé l'inverse batched de la matrice
`4 x 4` d'interpolation par les gradients barycentriques construits à partir
des produits vectoriels des trois arêtes et du déterminant orienté. Le contrat
de volume signé, la somme nulle des quatre gradients et l'identité avec
l'élément TET4 de référence sont testés. La campagne archivée dans
`qualification/benchmarks/qf_solver_0_2_2_assembly_scaling_geometry_comparison.json`
confirme l'identité numérique, les mêmes NNZ et une variation médiane du temps
total d'environ `-3,4 %` ; le kernel élémentaire diminue d'environ `7,6 %` à
`100k` DDL. Ce résultat est conservé comme amélioration locale à confirmer sur
une seconde configuration, pas comme garantie universelle de performance.

Cette confirmation a été exécutée avec la décomposition centrée à douze
TET4 par cellule et un matériau isotrope `E=70 GPa`, `nu=0,27`,
`rho=2700 kg/m3`. Le résultat est archivé dans
`qualification/benchmarks/qf_solver_0_2_2_assembly_scaling_centered_reference.json`.
À la taille cible, il produit `206115` DDL, `393216` éléments et `7715381`
NNZ, avec un kernel de `1,588 s` et une conversion sparse de `1,553 s` sur la
machine de mesure. Cette campagne confirme la stabilité du calcul sur une
seconde topologie et un second matériau ; ses temps ne sont pas comparés au
maillage historique, car le nombre d'éléments et de NNZ est différent.

Cette quantification est archivee dans
`qualification/benchmarks/qf_solver_0_2_2_standard_km_pair_reference.json`.
Sur 1k, 10k et 100k DDL, le ratio temps paire/separe mesure apres le compactage
des indices est respectivement `0,916`, `0,888` et `0,890`. Les matrices K et
M ont les memes dimensions, NNZ et differences numeriques nulles dans les
trois cas. Le resultat montre un gain de temps local d'environ `8,4 %` a
`11,2 %`, mais pas de gain memoire
revendique : l'estimation temporaire de la paire reste plus conservative.

La reutilisation de la matrice effective Newmark est mesuree separement dans
`qualification/benchmarks/qf_solver_0_2_2_newmark_factorization_reference.json`.
Le runner est `scripts/benchmark_newmark_factorization.py`. Sur environ `1029`
DDL et `10125` DDL, avec `8` pas, le chemin direct utilise une seule
factorisation (`factorization_count=1`) pour `8` resolutions (`solve_count=8`),
soit un ratio de reutilisation de `8`. Les residus dynamiques relatifs maximum
mesures sont respectivement `1,28e-11` et `2,21e-11`. Les temps de factorisation
mesures sont d'environ `0,006 s` et `0,572 s`, contre `0,002 s` et `0,063 s`
pour l'ensemble des huit resolutions. Le temps d'assemblage mesure est
respectivement `0,180 s` et `2,258 s`. Cela confirme le contrat de reutilisation
de la matrice effective ; cela ne constitue pas encore une comparaison
avant/apres avec une ancienne implementation qui refactoriserait a chaque pas.

## Limites restantes

Le chemin harmonique complexe conserve pour l'instant sa resolution sparse
SciPy dediee par frequence. Le backend PETSc n'est pas obligatoire et son
benefice doit etre mesure sur une configuration MPI tracee avant de modifier
la politique par defaut. La factorisation re-utilisee de Newmark reste le
chemin prefere pour les matrices effectives constantes ; les solveurs
iteratifs sont disponibles lorsque la memoire ou la taille le justifie.
Le benchmark Newmark est limite a `10k` DDL dans cette tranche ; une campagne
directe a `100k` DDL reste manuelle car la factorisation LU peut devenir le
goulot d'etranglement memoire.

La promotion de la release reste reservee a l'Owner apres execution de la
regression complete, des benchmarks de scaling et de la revue des ecarts
numeriques.

Le runner `scripts/compare_large_backends.py` a été ajouté pour comparer une
observable mécanique identique entre SciPy, matrix-free et PETSc. La campagne
Docker archivée sur `1 029` DDL termine avec les trois backends et des écarts
relatifs de déplacement de `1,087e-13` (matrix-free) et `1,417e-13` (PETSc)
par rapport à SciPy. Cette comparaison reste une preuve de cohérence sur un
petit cas, pas une qualification HPC universelle.

## Gate multi-million de DDL

La readiness distingue désormais les campagnes à partir de `2 000 000` DDL
avec le contrôle `MULTI-MILLION-GATE`. Ce contrôle exige `petsc` ou
`matrix_free` et accepte un budget mémoire explicite en octets, transmis par
l'API ou par `large-readiness --memory-budget-mb`. Sans budget, le statut est
`WARNING`; avec un budget inférieur à l'estimation PETSc indicative, il est
`FAIL`. Le gate ne lance pas le solveur : il protège la campagne contre une
allocation prématurée et laisse la qualification multi-million hors CI rapide.

Une tranche Docker réelle a été exécutée avec l'image épinglée
`qf-solver-large:0.2.0@sha256:f2a7931d0543ee142ce67847bb91bf59350a947d5d4874bfe7be43b6848a49c8`.
Les quatre cas `2M/4M DDL x 2/4 rangs` passent l'audit, la convergence CG,
le résidu relatif `1e-8`, la sortie file-backed et le budget RSS de `32 GiB`.
Les efficacités fortes observées sont `0,651` à 2M et `0,615` à 4M. Cette
preuve est **bornée au statique linéaire TET4, à une machine, à une image et au
partitionnement contigu** ; elle ne ferme ni le modal/dynamique multi-million,
ni SLEPc, ni le partitionnement graphe.

## Campagne backend agregee 0.2.2 alpha

Le dossier
`qualification/benchmarks/qf_solver_0_2_2_backend_campaign/campaign.json`
est genere par `scripts/build_backend_campaign_report.py`. Son statut
`PASS_BOUNDED_BACKEND_CAMPAIGN` ferme le gate technique dans le perimetre
suivant, sans promotion de maturite :

| Chemin | Preuve | Resultat |
| --- | --- | --- |
| PETSc statique contigu | 2M/4M DDL, 2/4 rangs | efficacites fortes `0,651` et `0,615` |
| PETSc graphe/PT-Scotch | 2M DDL, 2/4 rangs | efficacite forte `0,621` |
| matrix-free | `107 811` DDL | residu relatif `1,104e-12` |
| comparaison backends | SciPy/matrix-free/PETSc, `1 029` DDL | ecarts `< 1,5e-13` |
| modal SLEPc | `107 811` DDL, 3 modes | residu modal maximal `2,789e-12` |
| Newmark PETSc/GAMG | `2 044 416` DDL, 10 pas | residu relatif maximal `1,968e-6` |

Les sept manifestes d'evidence de cette campagne sont verifies `PASS`. Les
sorties modales et Newmark utilisent une masse TET4 coherente et ne forment
pas `inv(M) @ K`.

La tentative modale SLEPc a `2 044 416` DDL n'a pas ete declaree PASS : le
shift-invert direct a ete tue par la limite de ressources du conteneur apres
environ `33,5 GiB` observes. Cette limite est archivee dans
`qualification/benchmarks/qf_solver_0_2_2_backend_campaign/modal_2m_resource_limit/`.
La modalisation a plusieurs millions, une seconde configuration materielle et
la revue Owner restent donc hors de ce gate technique borne.
