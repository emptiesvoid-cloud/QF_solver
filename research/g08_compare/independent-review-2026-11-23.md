# Revue croisée du certificat spectral G08 — 2026-11-23

## Résultat et périmètre

La reconstitution du raisonnement ne révèle pas d’erreur dans le certificat
d’inertie appliqué aux deux jeux de matrices binary64. Le rejeu dans ce
worktree confirme les inerties et intervalles archivés. Une lacune séparée
de validation des entrées a été reproduite et corrigée localement : des
entrées complexes ou de dtype non conforme pouvaient être converties en
`float64` avant validation, en perdant des données.

Cette relecture croisée inclut un second lecteur en lecture seule et une
dérivation séparée des arguments. Elle n’est ni une revue externe ni une
qualification. Le worktree `review/0.3.0-g08-independent-audit-20261123`
part de `origin/0.3.0` à `bb0fa9cb51e4db365a61a3853081cd6b5f79b04d`. Les
commits examinés sont `5601342e` (capture), `f7b55234` (inertie vérifiée) et
`bb0fa9cb` (corrections de formulation et multiplicité). Aucune campagne FEM
n’a été lancée.

## Raisonnement contrôlé

Pour une matrice symétrique `A`, l’outil choisit en binary64 une base propre
approximative `V` et une diagonale non singulière `D`. Les entrées de `V` et
`D` sont ensuite traitées comme des valeurs binary64 exactes et les produits
sont encadrés par Arb.

1. Les bornes Arb sur `G = VᵀV` donnent `||G−I||∞ < 1`. Comme `G−I` est
   symétrique, `||G−I||₂ ≤ ||G−I||∞ < 1`; `G` est donc définie positive et
   `V` est inversible.
2. Pour `H = VᵀAV`, `E = H−D`, `R = |D|⁻¹ᐟ²` et `F = RER`, la borne stricte
   sur chaque somme de ligne donne `||F||₂ ≤ ||F||∞ < 1`. `F` est
   symétrique. L’homotopie `sign(D)+tF`, pour `0≤t≤1`, reste inversible car
   sa perturbation a une norme inférieure à la valeur singulière minimale 1
   de `sign(D)`. Elle conserve donc l’inertie de `D`. Les congruences par
   `R` et `V` conservent l’inertie et établissent celle de `A`.
3. Dans le crayon `Q(λ)=K0+λKg`, la définition positive certifiée de `K0`
   permet la congruence `K0⁻¹ᐟ² Q K0⁻¹ᐟ² = I+λB`, avec `B` symétrique.
   Ses valeurs propres sont `1+λμᵢ`; pour `λ≥0`, chacune franchit zéro au
   plus une fois. Le compte négatif est donc monotone, même si `Kg` est
   indéfinie. Un compte nul à la borne basse exclut une racine positive
   antérieure ; un compte positif à la borne haute place la première racine
   dans l’intervalle. Le saut du compte est la multiplicité totale dans cet
   intervalle. Un endpoint singulier reste indéterminé et n’est pas déclaré
   certifié.

La relecture séparée confirme ces étapes et n’a trouvé aucun contre-exemple.
La preuve suppose la symétrie exacte des matrices binary64, vérifiée sans
symétrisation, et l’inclusion correcte des opérations Arb. Les bornes sont
des inégalités strictes ; si elles ne sont pas résolues, le code retourne un
état indéterminé. La preuve ne dépend pas de l’exactitude de l’eigensolveur
SciPy utilisé pour construire `V` : ses erreurs sont incluses dans les
bornes Arb.

## Défaut d’entrée corrigé

Avant correction, `np.asarray(..., dtype=float64)` supprimait la partie
imaginaire d’une matrice complexe. Le cas `[[1+1j]]` pouvait ainsi produire
un certificat positif pour `[[1]]`. Le lecteur NPZ faisait la même
normalisation silencieuse pour `k0_data`, `kg_data` et `u_pre`, puis
validait les tableaux déjà convertis. Le chemin de résidu convertissait
aussi le vecteur candidat.

Le correctif local :

- refuse les matrices et vecteurs complexes et les conversions numériques
  qui perdraient une précision détectable ;
- vérifie les dtypes bruts avant de reconstruire les CSR : données `float64`,
  indices, pointeurs, formes et cartes de DDL `int64` ;
- lit `mode.npy` comme vecteur fini `float64` et vérifie sa dimension avant
  validation de l’archive.

Ce défaut d’interface ne modifie pas les deux certificats examinés : les
archives d’origine ont les types attendus (`<f8` pour `K0`, `Kg`, `u_pre`
et mode ; `<i8` pour les indices), et leurs empreintes correspondent aux
enregistrements contrôlés. Les verdicts historiques restent
`FIRST_MODE_NOT_ESTABLISHED`.

## Provenance et rejeu

Les deux captures utilisables restent `runner PASS`, `preload CONVERGED`,
`spectral COMPUTED` et `archive VALID`. L’échec historique initial du cas
avant et les verdicts A/B antérieurs n’ont pas été réécrits. Le contrat de
capture partagé a pour SHA-256
`1114517e4522053c9419d2c7b7a7afb54c9b6d7a2f6dcb9377777f458b6ea2f5`. Les
SHA des fichiers d’archives, préflights, ledgers et exécutions ont été
recalculés. Les deux préflights exacts sont `PREFLIGHT_PASS`; chaque ledger
contient une tentative. Les commits et arbres sources concordent avec le
rapport. Les lecteurs corrigés ont revalidé les types bruts.

| Empreinte | Avant, source `9f50ed064fa6a330a0c926d6c1a097b279966f69` | Après, source `6dd15ea007439a37327298690232cf81bf4c7f69` |
|---|---|---|
| Entrées | `cada40b87ac8cfadfb1e60f6a3398772fd9385cbf96b0b1abeec3fc894768a53` | `1b0f448d8910c4b1f9bb3282a5fb97a3b014cfcef4b97b3a048cb8d493f062ff` |
| `capture.json` / `matrices.npz` / `result.json` | `957ec4ee53b4b380a1b75f806bbab0deb990926befa5fb6ea67f55dafde56840` / `a8e3f50dd02174c83ca886d5f0225f369dd8eaa83386f8eb99022f8aeab5dd7f` / `b8a43e3582963103e548b7a22c5abd29d44ed2995c60af22c274c1a5184accf7` | `105766de775f540eed7439dd0d7320d5bcc2f6d2d7b57c40b52b2a2eaf069c0f` / `e263f58cca91d7f845e14f2e8d4b7552e3d2904ff2c61fc5c0cf9f164a56bc67` / `e366ce7289ec61120a56a8f567a59e9313aad9de519b4dce70cf8918f9d822b8` |
| `K0` / `Kg` CSR canonique | `7500bf21f2a3f25cbcd200ebb6b338aa5de18aac0161f96e320612315f5485b5` / `90e175c8c573794a8c49eb78e6acf8d70d0d42bb2fc0421ebd12bfeb1ecc3172` | `17d5ca19a3b35b8cdde3575e9d9b43769efe80cd583d6f9c3a4589625bc84476` / `749d42ae487f41bd456fd8e261eb829c6d131c02e2e27c95f65327308cdfca6d` |
| `u_pre` / mode | `6c072a73927e94b358714e89f9a407e181c127ed356b8e99523c09664a11443d` / `73a5a05605ece9436735d667b07b652caf501c606d6b799745194b3e5926b6b3` | `6c1dbd73e67e7cd0958b9b26dedaddad8976bb31d3d9fd2259fbc62c433fe3b0` / `6990c6a4293ca9610fc4cfea092bc7a7bde1a1b3331aca851e8f28b18f48a6b6` |
| Préflight / ledger | `pf-efbf9d01dffa` / `102bb2e756e28f81c598f6b6f6c90c184040ebdb121f535603a71919c53a2c7b`; ledger `a51380160ca8ea566fd328b03da34758fcff2edba0628aba749d017addcc5051` | `pf-87e141ae8f88` / `89529a663bcf537877c5b37c84de61a7fc9729de1c130c1922c7194fcbb099b5`; ledger `47086f71fab2c830cc72d7424b3b2328e211870e8d44df405f6c4e90f7f976bf` |

Les rejeux à 128 bits reproduisent :

| Cas | DDL libres | Inertie de `K0` | Inertie aux bornes du premier facteur | Intervalle du premier facteur | Intervalle suivant |
|---|---:|---:|---:|---:|---:|
| Avant | 276 | `(0, 0, 276)` | `0 → 1` négative | `[866,2977533340454 ; 866,2977542877197]` | `[873 ; 873,03125]` |
| Après | 300 | `(0, 0, 300)` | `0 → 1` négative | `[869,9805917739868 ; 869,9805927276611]` | `[872,96875 ; 873,03125]` |

Les candidats archivés sont dans les intervalles certifiés. Le facteur
après moins avant est encadré par
`[3,68283748626709 ; 3,6828393936157227]`. L’A/B mêle changement de
connectivité et de discrétisation (`276` contre `300` DDL). Le maillage
avant présente 48 faces internes ouvertes, 8 composantes et 12 alias ; le
certificat de son crayon ne valide pas sa représentation mécanique.

La durée du rejeu est de 10,03 s avant et 13,26 s après (Python 3.13.1,
NumPy 2.2.6, SciPy 1.15.2, `python-flint` 0.9.0). La mémoire de l’analyse
spectrale n’a pas été mesurée. Le criblage G08 par `scipy.linalg.ldl` reste
un contrôle flottant sans borne d’erreur.

## Contrôle exact indépendant et tests

Un éliminateur rationnel séparé utilise `Fraction.from_float`, des pivots
symétriques `1×1` ou `2×2` et des compléments de Schur exacts. Il retrouve
les inerties attendues sur cinq cas synthétiques : définie positive à
valeurs répétées, bloc indéfini `[[0,1],[1,0]]`, singulière, dyadiques
proches de zéro et transformation par congruence avec noyau. Trois cas
nonsinguliers sont aussi comparés aux résultats Arb. Le test reproductible
est `tests/research/test_g08_independent_audit.py`.

Aucune élimination exacte complète des matrices 276×276 et 300×300 n’a été
tentée. Elle n’est pas nécessaire pour la preuve Arb et son coût rationnel
avec remplissage n’a pas été benchmarké ici ; aucun résultat exact complet
n’est revendiqué.

Contrôles exécutés sur cette révision : 14 tests du certificat, 5 tests de
revue exacte/entrées, et 22 cas ciblés des validateurs et de
l’instrumentation synthétique d’archives ; tous passent. Ruff, `py_compile`,
`git diff --check` et l’intégrité SHA du rapport passent également. Suite
complète, CI protégée, factorisation exacte G08, correspondance modale et
calcul FEM : non exécutés.

## Portée mécanique et suite recommandée

Le certificat établit un premier zéro positif du crayon **des matrices
binary64 stockées** et une racine simple dans chaque intervalle. Il ne
certifie pas le vecteur propre lui-même, n’établit pas une correspondance
modale entre maillages et ne borne aucune erreur d’assemblage FEM, de
discrétisation ou de modèle. Les statuts historiques restent ouverts.

Prochain chantier recommandé : **réconciliation des preuves contact R10/R16**,
en commençant par une revue des traces archivées, sans campagne par défaut.
R1.10 conserve un échec M4 slip au pas 7 (`1,5038e−7` contre un seuil
`1e−9`) et une aire active M3 slip de 87,5 % ; les six cas M1/M2/M3 restent
des succès de diagnostic uniquement. Le dossier R16 documente un échec de
parsing pytest préservé et des rejeux offline R17/R18, mais cette route reste
expérimentale, limitée aux petites rotations et sans tangent global slip
qualifiée. Ces éléments donnent un défaut et des archives concrets à
réconcilier avant toute nouvelle exécution. Voir
[`résultats R1.10`](../../docs/verification/0_2_9/wp08-area-supported-contact-r1-10-m4-results.md)
et [`transfert R16`](../../docs/contact_small_rotation_work_conjugate_transfer.md).

Le garde non linéaire reste décrit par un contrat prospectif de phase
architecture, sans implémentation WP01 autorisée dans ce dossier. La preuve
HEX8-SRI existante conserve `KEEP_EXPERIMENTAL` avec échecs d’équilibre et
d’énergie ; aucun dossier nommé J7/J14 n’a été trouvé dans cette branche.
Le chantier contact a donc la piste de diagnostic la plus concrète ici.
