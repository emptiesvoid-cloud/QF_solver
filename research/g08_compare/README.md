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

Le criblage en précision double observe K0 positive dans les deux cas.
Il classe le candidat au rang numérique 1 et observe une inertie
numérique de 0 à 1 de part et d’autre des candidats. Aucun backend
d’inertie à erreur contrôlée n’est installé ; ces observations ne
certifient donc ni la positivité de K0 ni le rang du premier mode. Les
deux cas restent `FIRST_MODE_NOT_ESTABLISHED`. La comparaison modale
entre maillages n’a pas été effectuée, faute d’interpolation commune
définie et testée.

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

L’étude devra capturer ces objets en observant le chemin existant du
solveur, sans changer l’algorithme, puis certifier la positivité de
`K0` et compter l’inertie de `K0 + lambda Kg`. Les scopes de capture
n’étaient alors pas enregistrés et le document n’autorisait aucune
nouvelle exécution. La section précédente consigne les captures
autorisées ensuite ; les deux cas restent
`FIRST_MODE_NOT_ESTABLISHED`.
