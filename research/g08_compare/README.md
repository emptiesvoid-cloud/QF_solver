# G08 : comparaison contrôlée des maillages transverses

Le lot décrit trois tentatives de développement : l’essai avant initial
a échoué dans le harnais avant précharge et reste archivé tel quel ;
l’essai après a abouti ; un unique essai avant a ensuite été exécuté
sous un nouveau contrat, un nouveau scope et un nouveau ledger.
Les deux résultats exploitables permettent maintenant une comparaison
A/B pour les cas enregistrés. Ce n’est pas une qualification.

Le résumé avec les identités, les verdicts, les empreintes et les
mesures est dans
[controlled-ab-retry-2026-11-22.json](results/controlled-ab-retry-2026-11-22.json).
Les archives numériques, journaux et ledgers restent dans le store local
et ne sont pas versionnés dans ce port.

| Cas | Source | Maillage | Runner / précharge / spectre / archive |
|---|---|---|---|
| Avant, tentative initiale | `9f50ed064fa6a330a0c926d6c1a097b279966f69` | 117 nœuds, 40 TET10, 276 DDL libres | `PYTEST_FAILED` au passage d’un argument non accepté, avant précharge ; échec préservé. |
| Avant, nouvelle tentative | même source et mêmes entrées | 117 nœuds, 40 TET10, 276 DDL libres ; 48 faces internes ouvertes, 8 composantes, 12 alias | préflight officiel `PREFLIGHT_PASS`; runner `PASS`, pytest `PASSED`, précharge `CONVERGED`, spectre `COMPUTED`, archive `VALID`. |
| Après | `6dd15ea007439a37327298690232cf81bf4c7f69` | 125 nœuds, 48 TET10, 300 DDL libres ; aucune face interne ouverte, une composante, aucun alias | runner `PASS`, précharge `CONVERGED`, spectre `COMPUTED`, archive `VALID`. |

Le solide nominal (4 × 0,5 × 0,5), le matériau isotrope (E=1 000 000,
ν=0,3), les appuis sur la face x=0 et la charge UX résultante −1 sont
identiques. Les deux sources utilisent le même arbre solveur. Le nombre
de DDL libres passe de 276 à 300 : l’écart mesuré combine les
changements de connectivité et de discrétisation.

Le facteur avant vaut 866,2977536614513 et le facteur après
869,9805921314434. La différence avant moins après est −3,68283847,
soit −0,4233 % rapportée au facteur après. Les charges signées
correspondantes sont −866,29775366 et −869,98059213. Cette différence
est l’observation A/B des deux cas définis ; elle n’isole pas l’effet de
connectivité.

Les deux essais ont convergé en précharge, avec résidus relatifs finaux
de 5,96e−15 avant et 7,11e−15 après. Le solveur spectral a utilisé
`scipy.sparse.linalg.eigs` avec `generalized_eigs_shift_invert`.
Les résidus relatifs des paires propres sont 3,72e−11 avant et
5,08e−11 après. Ces résidus faibles ne déterminent pas le rang du mode.
Les deux résultats gardent le statut
`FIRST_MODE_NOT_ESTABLISHED`; aucune preuve distincte de positivité de
K0 et aucun comptage d’inertie avec contrôle d’erreur ne sont archivés.
Les modes ne sont pas comparés : les vecteurs ont des dimensions et des
maillages différents, et le premier mode n’est pas établi.

Les temps observés sont 16,13 s avant et 15,14 s après ; le RSS maximal
échantillonné est d’environ 166,0 MB avant et 167,1 MB après. Ce sont
deux observations ponctuelles sous surveillance logicielle, sans quota
OS dur et sans portée statistique. Le contrôle de criblage et l’écart
Euler ne valident pas la charge critique physique.

Le harnais appelle le solveur de flambement via son API supportée
`solve_model(model)`. Les tests synthétiques ciblés, le lint et les
contrôles du port ne remplacent pas la CI protégée ni une qualification
scientifique. Ces éléments ne déclarent pas la release prête.

## Capture matricielle et criblage spectral

Le contrat d’étude ci-dessus est conservé comme photographie de la
préparation antérieure aux captures. Deux captures séparées ont depuis
été exécutées sous le contrat
[`first-mode-capture-contract-2026-11-22.json`](first-mode-capture-contract-2026-11-22.json),
avec un scope, un préflight officiel et un ledger distinct par source.
Les deux préflights ont passé ; chaque ledger contient une tentative.
Les archives brutes restent dans le dépôt local de preuves et ne sont
pas versionnées ici.

Le résumé reproductible
[`first-mode-matrix-screen-2026-11-22.json`](results/first-mode-matrix-screen-2026-11-22.json)
lie les résultats aux empreintes des sources, entrées, vecteurs et
matrices, et aux verdicts A/B. Les deux runners ont réussi, les deux
précharges ont convergé et les deux archives de capture sont valides.
Les matrices réduites sont 276×276 avant et 300×300 après ; leurs
empreintes CSR canoniques et celles de `u_pre` figurent dans le résumé.

Le premier criblage en précision double observait K0 positive et classait
chaque candidat au rang numérique 1. Ces valeurs étaient des observations,
pas des certificats. Le statut historique des deux résultats reste
`FIRST_MODE_NOT_ESTABLISHED` ; la vérification séparée des matrices
stockées est consignée ci-dessous. La comparaison modale entre maillages
n’a pas été effectuée, faute d’interpolation commune définie et testée.

Les facteurs candidats diffèrent d’environ 0,425 %. Ce constat mêle la
connectivité et la discrétisation (276 contre 300 DDL libres) et ne
permet pas d’isoler l’effet de connectivité ni de qualifier la charge
critique physique. Aucun calcul FEM additionnel n’a été lancé après les
deux captures autorisées.

## Préparation initiale de l’étude du premier mode

Le contrat distinct
[first-mode-study-contract-2026-11-22.json](first-mode-study-contract-2026-11-22.json)
est un document de préparation antérieur aux captures. À sa date, les
archives A/B contenaient les vecteurs candidats `mode.npy` (351 et 375
composantes), les résidus et les comptes de non-zéros des tangentes ;
elles ne contenaient ni les valeurs de
`K0`/`Kg` ni le vecteur de déplacement de précharge `u_pre`.
Les résidus de précharge seuls ne permettent pas de reconstruire cet état.

À cette date, les captures n’étaient pas autorisées. Les captures
séparées décrites plus haut ont ensuite ajouté `K0`, `Kg` et `u_pre` sans
modifier l’algorithme du solveur. Les verdicts historiques restent
inchangés.

## Inertie vérifiée des matrices stockées

Le calcul reproductible et ses empreintes sont dans
[`verified-first-root-2026-11-22.json`](results/verified-first-root-2026-11-22.json).
L’empreinte SHA-256 du rapport est conservée dans
[`verified-first-root-2026-11-22.sha256`](results/verified-first-root-2026-11-22.sha256).
Les archives ont d’abord repassé le validateur contrôlé ; les empreintes
des fichiers bruts, matrices CSR canoniques, `u_pre`, mode et carte des
DDL y sont consignées. Les matrices binary64 stockées sont exactement
symétriques. Aucune symétrisation n’a été appliquée. La convention reste
`Q(lambda) = K0 + lambda * Kg`, avec facteur positif et charge signée
égale à son opposé. Les unités restent cohérentes, mais non étiquetées
physiquement dans la source.

La méthode construit une base propre approximative en binary64, puis
utilise Arb avec inclusion rigoureuse pour borner `V.T @ V` et
`V.T @ A @ V`. Elle certifie `V` inversible par
`||I - V.T @ V||∞ < 1`, puis certifie l’inertie de la diagonale
approximative par
`|| |D|^-1/2 (V.T @ A @ V - D) |D|^-1/2 ||∞ < 1`, où `D` est la
diagonale approximative et `|D|` prend la valeur absolue de chaque
entrée. Pour les matrices symétriques, cette erreur mise à l’échelle est
symétrique; sa norme spectrale est donc inférieure à 1. En posant
`J = sign(D)`, la matrice mise à l’échelle est `J + F`; l’homotopie
`J + tF`, `0 ≤ t ≤ 1`, ne rencontre pas zéro et conserve l’inertie.
Cette valeur absolue est nécessaire quand `D` contient des valeurs
négatives.
Un certificat indéterminé n’est jamais converti en compte flottant.
Le certificat par base propre ne repose pas sur une factorisation pivotée ;
les pivots 1×1/2×2 ne s’appliquent donc pas à cette preuve. Le rapport
consigne séparément un criblage Bunch–Kaufman `scipy.linalg.ldl` comme
comparaison numérique non certifiante.

Avec `python-flint==0.9.0`, 128 bits et Python 3.13.1 / NumPy 2.2.6 /
SciPy 1.15.2 :

| Cas | Inertie certifiée de K0 | Borne du premier facteur positif | Inertie aux bornes | Racine suivante |
|---|---:|---:|---:|---:|
| Avant, 276 DDL libres | (0 négative, 0 nulle, 276 positive) | [866,2977533340454 ; 866,2977542877197] | 0 puis 1 négative | [873 ; 873,03125], saut 1→2 |
| Après, 300 DDL libres | (0 négative, 0 nulle, 300 positive) | [869,9805917739868 ; 869,9805927276611] | 0 puis 1 négative | [872,96875 ; 873,03125], saut 1→2 |

Le criblage indépendant par `scipy.linalg.ldl` retrouve les mêmes comptes
pour K0, les quatre bornes du premier/deuxième facteur, avec un résidu de
reconstruction inférieur à 3,7e−16 en norme infinie relative. Ce contrôle
utilise des facteurs et opérations binary64 sans borne d’erreur ; il
corrobore les signes numériquement et n’entre pas dans le certificat Arb.

Les intervalles du premier facteur résultent de 16 bissections guidées
par des comptes d’inertie certifiés à chaque milieu. Le facteur candidat
archivé reste dans chaque intervalle raffiné. La différence après moins
avant est encadrée par [3,68283748626709 ; 3,6828393936157227].

`Kg` est indéfinie dans les deux cas, avec témoins de Rayleigh négatif
et positif certifiés. Cela ne casse pas le comptage : puisque `K0` est
positive définie, le crayon est congruent à `I + lambda B` pour une
matrice symétrique `B`; le nombre de valeurs propres négatives ne peut
que croître avec `lambda >= 0`. Le compte nul à la borne basse exclut
une racine positive antérieure. Un compte positif à la borne haute
place la première racine dans l’intervalle. La différence des comptes
aux bornes donne la multiplicité totale des croisements contenus dans
l’intervalle : 0→1 isole une racine simple, tandis qu’un saut plus grand
reste conservé comme multiplicité, sans prétendre distinguer une racine
multiple de plusieurs racines proches. Ici, le saut 0→1 certifie une
racine simple dans chaque premier intervalle. Le saut 1→2 encadre
également la valeur propre positive suivante.

Le rapport certifie donc un encadrement du **premier facteur propre
positif des matrices binary64 stockées**. Les résidus des vecteurs
candidats ont été recalculés avec Arb ; ils ne remplacent pas les résidus
archivés, qui suivent la définition du solveur. Le rapport conserve les
deux valeurs pour comparaison. Il ne valide ni l’assemblage
FEM, ni les erreurs de discrétisation ou de modèle, ni toute la route
non linéaire. Le vecteur candidat n’a pas reçu de certificat d’intervalle
propre ; ses résidus ont été recalculés avec une borne Arb séparée. Les
résultats d’origine conservent leur statut `FIRST_MODE_NOT_ESTABLISHED`.
La différence du premier facteur après moins avant est encadrée par
[3,68283748626709 ; 3,6828393936157227] ; elle mêle connectivité et
discrétisation et ne permet pas d’isoler l’effet de connectivité.

Les opérations d’inertie et les 16 raffinements ont pris 10,03 s avant
et 13,26 s après lors du rejeu du 23 novembre 2026. La mémoire n’a pas
été mesurée. Le budget de 120 s par certificat est vérifié après son calcul,
pas par interruption préemptive. Le backend de recherche est optionnel et épinglé dans
[`requirements-inertia.txt`](requirements-inertia.txt); il n’ajoute
aucune dépendance d’exécution au produit. Les tests synthétiques couvrent
les matrices définies positives, indéfinies, singulières, proches de
zéro et à valeurs multiples, les crayons à racines simples ou multiples,
les données invalides et l’indisponibilité du backend.

La revue croisée du certificat, son contrôle exact sur des matrices
synthétiques et la correction des conversions de dtype sont consignés dans
[`independent-review-2026-11-23.md`](independent-review-2026-11-23.md).
