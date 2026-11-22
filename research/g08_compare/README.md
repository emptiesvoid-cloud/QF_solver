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
