# WP12-V — Revue des preuves numériques archivées U1–U3

**Statut :** revue de données archivée terminée; U3 conserve `FAIL`; WP12 reste `OPEN`
**Périmètre :** recalcul indépendant hors solveur à partir des archives WP12-U; aucune exécution FEM, aucun pytest, aucun appel à l’assembleur/solveur.
**Portée scientifique :** routes discrètes matrix-free et assemblée directe sur le seul modèle H1 TET4 archivé (36 DDL).

## 1. Résumé

- L’intégrité locale des manifestes, reçus, sorties U3 et copie du fixture est cohérente avec les identifiants prévus. U1 et U2 restent `PYTEST_PASS_ONLY`; U3 est `FAIL` avec un seul échec JUnit.
- U3 a émis le payload numérique avant les assertions. L’assertion qui échoue est l’exigence d’égalité exacte de la matrice assemblée globale à sa transposée. La matrice exacte de référence et la matrice scalaire sont symétriques; la matrice batch assemblée a un écart maximal de **7.62939453125e−6 N/m**, soit **1 ULP**, relatif Frobenius **1.74465e−17**. Ce constat quantifie l’échec sans le remplacer par une tolérance.
- Sur les données archivées, les deux routes ont des déplacements libres très proches (**écart maximal 3.14e−20 m**, écart L2 relatif **4.26e−12**), des produits opérateur proches, et des résidus libres petits. Ces diagnostics sont calculés avant l’assertion; les assertions pytest postérieures à l’assertion de symétrie sont `NOT_REACHED`.
- Ceci est une vérification de cohérence numérique du système discret H1. Cela ne valide ni la réponse 3D en flexion, ni la précision/convergence TET4, ni le solveur pour d’autres cas.

## 2. Provenance et intégrité

### 2.1 Identité de la campagne

Le manifeste local `qualification/0_2_12/vv_local/wp12_u/WP12_U_MANIFEST.json` a pour SHA-256 **3f10c7156c6f4e5eaf07f0bf66a92fe3f7cc6ef9031c200c1e41ca1087bf2a1c**, identique au hash présent dans les trois reçus. Les reçus U1, U2, U3 ont été recalculés et concordent respectivement avec les hashes attendus :

| Cas | Run | SHA-256 receipt | JUnit |
|---|---|---|---|
| U1 modal 2 DDL | `20261026T120140Z-49ca8fb4ee0d` | `409d8caf79621b9a94792080f49ad784523c3e5087d22018b1934ca25b6d729f` | sortie hash vérifiée; `PYTEST_PASS_ONLY` |
| U2 affine TET4 | `20261026T120231Z-ba477b0a779b` | `c5be56b7af3496ec6c34017bea42e452e5f1f44e2c984f48948bc0dc6aea2475` | sortie hash vérifiée; `PYTEST_PASS_ONLY` |
| U3 routes H1 | `20261026T120509Z-3a69e91f9b42` | `c47a566d97998746a58823ce3f88b5f4950b7cf597bf62129f72aa54c3956542` | JUnit hash `95f6fb8cade02efd3d712fcfe94231c5657c303d3bb130a23c10028369bd021c`; 1 test, 1 failure |

Pour chacun, le hash de `receipt.json`, le hash inscrit dans `receipt.sha256.json`, et les hashes d’outputs énumérés par le reçu concordent. Le hash JUnit U3 copié dans `WP12_U_EXECUTION_REPORT.md` correspond également à l’artefact primaire (64 caractères, identiques). Le manifeste est un snapshot pré-exécution (`result_status: NOT_RUN`); il est cité pour son identité/hash, pas comme statut post-exécution et n’est pas modifié. Les reçus d’archive portent les résultats effectués. Pour U3, `selection.json` et le JUnit sélectionnent un seul nodeid exact, `tests/unit/test_wp12_u_tet4_route_crosscheck.py::test_tet4_route_crosscheck_001`; l’import vérifié est `E:\QFSolverWP12B\science\src\solveur\__init__.py`. Le code de sortie est 1, stderr est vide, aucun timeout/interruption/output-limit n’est signalé.

Le reçu U3 donne, avant et après, les mêmes commits, arbres propres et inventaires de fichiers : science `00428adf38e9397340ac136f6f503a268eb671da`, runner `0bd8ebb5a886ac89a8216e65ff37d59fb510fb61`, tests `9c7df65403fc15dc6d12365534172eac87f2ee70`. L’environnement enregistré est Python 3.13.17, NumPy 2.2.6, SciPy 1.15.2, un thread OpenBLAS. Ce sont des assertions documentaires issues du reçu local, non une attestation cryptographique d’auteur ou d’immuabilité.

### 2.2 Modèle et charge U3

Le payload U3 identifie 12 nœuds, 12 TET4, 36 DDL (24 libres, 12 fixés), unités SI, matériau isotrope `E=70 GPa`, `ν=0.3`, `ρ=7800 kg/m³`, appuis aux nœuds 0–3 et quatre charges `Fz=−0.25 N` aux nœuds 8–11. La résultante appliquée est `(0, 0, −1) N`. Le SHA-256 du fixture archivé est **4807fea4cde876f57ef1e376f9b0791f5367526d182e236655b39e73e57baa7d**, et le fichier présent dans le checkout de tests a le même hash. Le reçu U3 vérifie également les hashes des sorties directes archivées `audit_large.json`, `displacements.h5` et `summary.json`.

La preuve matricielle comprend une matrice globale 36×36 de référence fractionnaire convertie en binary64, les matrices assemblées scalaire et batch, et la matrice libre 24×24 de référence conservée sous forme de chaînes `Fraction`. Les résidus complets sont conservés en fractions. La matrice libre exacte et les résidus permettent les recalculs rationnels décrits ci-dessous; la matrice globale de référence exposée dans le payload est binary64, pas un export rationnel 36×36.

## 3. Matrices, produits opérateur et condition

Les normes relatives ci-dessous utilisent `||A−B||F / ||K_exact||F`; la dissymétrie relative utilise `||K−Kᵀ||F / ||K||F`. Les écarts absolus sont en N/m. L’ULP est une distance d’encodage binary64 par entrée; elle complète les normes et n’est pas une mesure physique.

| Comparaison | max abs (N/m) | relatif Frobenius | max ULP |
|---|---:|---:|---:|
| Symétrie exacte, `K_exact−K_exactᵀ` | 0 | 0 | 0 |
| Symétrie scalaire | 0 | 0 | 0 |
| Symétrie batch | 7.62939453125e−6 | 1.74465e−17 | 1 |
| scalaire vs référence exacte | 3.0517578125e−5 | 9.63860e−17 | 2 |
| batch vs référence exacte | 1.52587890625e−5 | 9.05077e−17 | 3 |
| scalaire vs batch | 3.0517578125e−5 | 9.22988e−17 | 4 |

Pour la matrice batch, `||K−Kᵀ||F = 1.0789593218788873e−5 N/m` et `||K||F = 6.184394795572822e11 N/m`. La paire asymétrique signalée par l’audit, indices Python 0-based `(14,22)` et `(22,14)` (DDL Uz du nœud 4 / Uy du nœud 7), est :

| Entrée | Décimal (N/m) | `float.hex()` | bits binary64 (uint64, hex) |
|---|---:|---|---|
| `K[14,22]` | −44871794871.79487 | `-0x1.4e522816f96f9p+35` | `c224e522816f96f9` |
| `K[22,14]` | −44871794871.794876 | `-0x1.4e522816f96fap+35` | `c224e522816f96fa` |

Les bits diffèrent d’une unité et la différence signée `K[14,22]−K[22,14]` vaut `7.62939453125e−6 N/m`.

Pour situer l’ordre de grandeur arithmétique binary64, avec `u=2⁻⁵³`, `γ₃=3u/(1−3u)≈3.33066907387547e−16` et `γ₂=2u/(1−2u)≈2.220446049250314e−16`. Une borne d’arrondi de pire cas pour cette entrée ne peut pas être évaluée à partir des seuls tableaux globaux : elle requiert le `S` pertinent (somme des valeurs absolues des contributions/termes intermédiaires selon l’opération bornée). Ni le payload U3, ni les outputs archivés `summary.json`/`audit_large.json` ne conservent les contributions élémentaires ou ce `S`. Le calculer demanderait de reconstituer les contributions, ce qui n’est pas fait ici. Donc le seul constat est l’écart observé d’un ULP; l’hypothèse d’un arrondi compatible demeure plausible, mais n’est pas prouvée par une borne γ.

La plus grande entrée globale est d’environ `1.225897435897436e11 N/m`; la dissymétrie est ainsi de dernier bit relativement à l’échelle de `K`. Le test impose cependant l’égalité exacte par `array_equal`/symétrie booléenne. Cette assertion échoue; aucune réinterprétation par seuil n’est appliquée.

Pour le bloc libre fractionnaire de référence, une diagonalisation NumPy symétrisée en binary64 donne `λmin≈4.23345636e7 N/m`, `λmax≈3.37525591e11 N/m`, donc **κ₂≈7.9728e3**; la condition infinity norm observée est **κ∞≈1.2446e4**. C’est un post-traitement propre à cette matrice et à NumPy, non une preuve exacte des valeurs propres ni un indicateur universel de conditionnement TET4.

Les trois produits déterministes (24 DDL libres, sans générateur aléatoire) matrix-free / direct / référence donnent les écarts route relatifs archivés, avec dénominateur `||K_exact,free||F ||v||₂` :

| Vecteur | `\|\|A_mf v − A_direct v\|\|` max abs (N) | écart route relatif |
|---:|---:|---:|
| 1 | 2.28882e−5 | 2.08289e−17 |
| 2 | 6.48499e−5 | 4.89846e−17 |
| 3 | 1.52588e−5 | 2.83095e−17 |

Les valeurs absolues dépendent de l’échelle du vecteur et du `N/m`; les ratios utilisent le dénominateur ci-dessus. Elles ne prouvent pas l’identité exacte des implémentations ni une validation indépendante du matériau ou du maillage.

### 3.1 Borne rigoureuse de perturbation de l’opérateur libre H1

Cette borne compare uniquement les deux matrices directes `Ahat` (sous-matrices libres 24×24 extraites des matrices globales batch/scalar binary64 archivées) à `A0` (la matrice libre exacte archivée comme fractions). Pour chaque entrée, `E=Ahat−A0` a été calculé exactement comme `Fraction.from_float(Ahat[i,j])−A0[i,j]`; les normes `||E||∞` sont les sommes absolues de lignes rationnelles exactes.

Une matrice auxiliaire `B` a été construite en post-traitement seulement par `Bfloat = numpy.linalg.inv(float(A0))`, puis chaque binary64 de `Bfloat` a été interprété comme sa fraction exacte. Le résidu `R=I−A0B` et `q=||R||∞` ont ensuite été calculés exactement en `Fraction`, sans reprendre le booléen ou la borne `inverse_norm_upper_bound_exact` déjà émis par le test. Les valeurs exactes ci-dessous suffisent à vérifier `q<1`, donc `A0` est inversible et `||A0⁻¹||∞ ≤ U=||B||∞/(1−q)`.

| Quantité | Valeur exacte | Décimale indicative |
|---|---|---:|
| `\|\|B\|\|∞` (m/N) | `18489259885589737 / 604462909807314587353088` | `3.058791463562848e−8` |
| `q=\|\|I−A0B\|\|∞` | `571080211974063945637823480240560451069123329281643011913531 / 1378140710527139841807583696754621166059871378190192853711147089048633344` | `4.143845455052448e−13 < 1` |
| `U=\|\|B\|\|∞/(1−q)` (m/N) | `42154450409488536064484807026850435294421704177149766171420000256 / 1378140710526568761595609632808983342579630817739123730381865446036719813` | `3.058791463564116e−8` |
| `\|\|E_batch\|\|∞` (N/m) | `182383167527428994875425535366382622275407 / 4453012801242595038064201262340273961407873024` | `4.0957252015205465e−5` |
| `\|\|E_scalar\|\|∞` (N/m) | `309719830952474398085572855034373104797873 / 8906025602485190076128402524680547922815746048` | `3.477643617665419e−5` |

Donc `η=U||E||∞` et `η/(1−η)` sont, exactement :

| Route | `η` exacte | `η/(1−η)` exacte | Approximation de la borne relative `∞` |
|---|---|---|---:|
| Batch | `1726530448983903054952550050050639782168655081298445669355008 / 1378140710526568761595609632808983342579630817739123730381865446036719813` | `1726530448983903054952550050050639782168655081298445669355008 / 1378140710524842231146625729754030792529580177956955075300567000367364805` | `1.252796928353116e−12` |
| Scalaire | `1465981554227512185333637729263551083896734818285769786726656 / 1378140710526568761595609632808983342579630817739123730381865446036719813` | `1465981554227512185333637729263551083896734818285769786726656 / 1378140710525102780041382120623649704850367266655226995563579676249993157` | `1.063738661104454e−12` |

Dérivation : si `x=A0⁻¹f` et `x̂=(A0+E)⁻¹f`, alors `x̂−x=−(I+A0⁻¹E)⁻¹A0⁻¹E x`. Comme `||A0⁻¹E||∞≤η<1`, la série de Neumann donne `||x̂−x||∞/||x||∞≤η/(1−η)`. C’est une borne rigoureuse de la perturbation relative de solution pour **le même RHS**, à partir des matrices archivées et de fractions exactes; les approximations décimales sont indicatives, les fractions constituent les valeurs bornantes.

Cette borne directe exclut ici une erreur de route opérateur importante entre `A0` et chaque assemblage stocké, pour H1 seulement. Elle ne prouve ni la correction de l’assertion d’égalité exacte, ni l’équivalence de l’opérateur matrix-free complet à toutes les entrées de `Ahat`, ni une précision continuum/flexion, ni quoi que ce soit pour H2/H3. `B` est un inverse approché NumPy, mais la borne est certifiée par son résidu `q` recalculé exactement; aucun champ de borne pré-enregistré n’est pris comme preuve indépendante.

Extrait reproductible de la vérification (post-traitement des seules données archivées; aucun import QF Solver) :

```python
import json
from fractions import Fraction as Q
from pathlib import Path
import numpy as np

p = Path("E:/QFSolverWP12B/wp12-local-vv-evidence/WP12-U-TARGETED-001/"
         "TET4-ROUTE-CROSSCHECK-001/20261026T120509Z-3a69e91f9b42/receipt.json")
v = json.loads(p.read_text(encoding="utf-8"))["numeric_observables"]["payload"]["values"]
s = v["stiffness_reference"]
A = [[Q(x) for x in row] for row in s["full_free_matrix_exact_fractions"]]
n = len(A)
J = range(n)
Bf = np.linalg.inv(np.array([[float(x) for x in row] for row in A]))
B = [[Q.from_float(float(x)) for x in row] for row in Bf]
q = max(sum(abs(Q(int(i == j)) - sum(A[i][k] * B[k][j] for k in J))
            for j in J) for i in J)
assert q < 1
U = max(sum(abs(x) for x in row) for row in B) / (1 - q)
free = v["free_dofs"]
for key in ("batched_sparse_assembled", "scalar_element_assembled"):
    Kh = s[key]
    Enorm = max(sum(abs(Q.from_float(float(Kh[free[i]][free[j]])) - A[i][j])
                   for j in J) for i in J)
    eta = U * Enorm
    assert eta < 1
    print(key, "q=", q, "U=", U, "E_inf=", Enorm, "bound=", eta / (1 - eta))
```

Ces assertions vérifient une inégalité d'algèbre rationnelle sur les données, pas un nodeid scientifique QF Solver. Le choix de B approché peut varier selon NumPy/BLAS; la vérification rationnelle de q et les fractions imprimées constituent la justification pour l'inverse approché effectivement obtenu.

## 4. Déplacements et résidus

Les déplacements retournés sont des champs 36 DDL en mètres. Les DDL contraints valent exactement zéro dans les deux tableaux archivés. Sur les DDL libres, le recalcul binary64 donne : `max |u_mf−u_direct| = 3.13675e−20 m`, `||Δu||₂≈4.63599e−20 m`, `||Δu||₂/||u_direct||₂≈4.25961e−12`, et `max|Δu|/max|u_direct|≈6.06422e−12`. Un écart ULP maximal brut serait dominé par les composantes presque nulles; il n’est pas utilisé comme métrique de déplacement. Ces valeurs décrivent un seul vecteur de charge et une seule fixture.

Les résidus libres exacts ont été recalculés en fractions à partir de `K_free` fractionnaire, du déplacement binary64 exact-rationalisé et du vecteur de charge fractionnaire indépendant archivé. Les deux vecteurs reproduisent exactement les chaînes de résidus libres enregistrées. Les normes `L2` recalculées sont `4.0088340e−9 N` (matrix-free) et `1.1492670e−13 N` (direct). Pour matrix-free, le code divise par `max(||rhs||₂,tiny)`; `||rhs||₂=0.5 N`, donc `ρ_mf=8.0176681e−9 ≤ rtol=1e−8`. Pour direct, le dénominateur est exactement `max(||f_free||₂, ||K_free u_free||₂, 1.0)`: le recalcul des valeurs archivées donne respectivement `0.5 N`, `0.5000000000000282 N`, et **1.0**, donc `ρ_direct=1.1492670e−13 ≤ 1e−7`. Il n’est pas simplifié par hypothèse; le troisième argument fixe ici le maximum à 1. Les formules sont dans le test archivé `tests/unit/test_wp12_u_tet4_route_crosscheck.py` du checkout tests commit `9c7df65403fc15dc6d12365534172eac87f2ee70`, lignes 390–400 (`rho_mf`, `direct_product_exact`, `direct_residual_denominator`, `rho_direct`). La définition exacte du résidu est lignes 133–143. Le solveur matrix-free a enregistré 28 itérations CG et un résidu propre au solveur d’environ `4.0088e−9`; le direct a convergé en une résolution directe.



L’écart solution est par ailleurs comparé dans le payload à une borne d’inverse-résidu de `K_free` indépendante. Le booléen de borne est vrai et la valeur fractionnaire de la borne est archivée dans le reçu. Elle encadre ce couple de solutions selon la construction du cas, mais ne fournit pas de borne d’erreur continuum.

## 5. Réactions, forces et moments

Convention du test : `r=K_exact u−f`; réaction de support = `r` aux DDL contraints, force du support exercée sur le corps. Les coordonnées et charges sont exact-rationalisées depuis les tableaux d’entrée binary64 archivés. Les écarts route ci-dessous sont recalculés à partir du payload; les normes vectorielles évitent des ratios composante par composante instables près de zéro.

| Quantité | Matrix-free | Direct | Différence MF−direct | Normalisation de la différence |
|---|---|---|---|---|
| Réaction support (N) | `(9.40508e−11, −9.89336e−12, 0.9999999999905717)` | `(−2.55909e−14, 7.42738e−14, 1.000000000000065)` | `(9.40764e−11, −9.96763e−12, −9.49341e−12)`; norme `9.50781e−11 N` | `\|\|ΔR\|\|₂ / \|\|F_ext\|\|₂`, `\|\|F_ext\|\|₂=1 N`: `9.50781e−11` |
| Défaut force support + externe (N) | `(9.40508e−11, −9.89336e−12, −9.42834e−12)` | `(−2.55909e−14, 7.42738e−14, 6.50729e−14)` | différence vectorielle norme `9.50781e−11 N` | `9.50781e−11 / 1 N` |
| Moment support (N·m) | `(0.19999999999759668, −4.000000000001199, −1.60285e−12)` | `(0.19999999999995957, −4.000000000000251, 2.46921e−13)` | `(−2.36289e−12, −9.47686e−13, −1.84977e−12)`; norme `3.14690e−12 N·m` | `\|\|ΔM\|\|₂ / \|\|M_ext\|\|₂`, `\|\|M_ext\|\|₂=4.0049968789 N·m`: `7.85744e−13` |
| Défaut moment support + externe (N·m) | `(−2.40333e−12, −1.19861e−12, −1.60285e−12)` | `(−4.04273e−14, −2.51737e−13, 2.46921e−13)` | différence vectorielle norme `3.14666e−12 N·m` | `3.14666e−12 / 4.0049968789 N·m` = `7.85685e−13` |

Le moment externe est `(-0.2, 4.0, 0) N·m` autour de l’origine. Le code de réaction et des sommes se trouve dans le même test archivé, lignes 431–460; `_moment` est lignes 188–194. Les identités force par translation rigide et moment par rotation rigide sont vérifiées exactement en fractions par `_force_balance_identity` lignes 205–215 et `_moment_balance_identities` lignes 218–257. Les champs U3 enregistrent les identités de force exactes vraies pour les deux routes, ainsi que `exact_rigid_rotation_balance_identity=true` et `cauchy_bound_squared_holds=true` sur les trois axes pour les deux routes.

Ces identités ne sont pas une vérification externe indépendante : elles relient les réactions, les charges et les projections des résidus libres du même système discret. Les défauts bruts ci-dessus sont petits parce que les résidus libres le sont. Dans U3, les booléens de critères de force/moment sont calculés avant l’assertion échouée et restent des diagnostics du payload, non des assertions pytest atteintes.

## 6. Énergies, travaux et observables

`U=1/2 uᵀK_exact u` et `W=fᵀu`, tous deux en J. `Δ` signifie matrix-free moins direct. Les valeurs de différences relatives sont normalisées par la valeur absolue non nulle de la route directe; aucun ratio n’est donné pour `2U−W`, proche de zéro.

| Quantité | Matrix-free | Direct | Différence absolue | Différence relative / normalisation |
|---|---:|---:|---:|---:|
| Énergie de déformation `U` (J) | `2.5746365703056126e−9` | `2.574636570305104e−9` | `5.08716e−22 J` | `/\|U_direct\| = 1.97588e−13` |
| Travail externe `W` (J) | `5.14927314061041e−9` | `5.1492731406099025e−9` | `5.07889e−22 J` | `/\|W_direct\| = 9.86331e−14` |
| `2U−W = u_freeᵀr_free` (J) | `8.1403399433122385e−22` | `3.055245756732512e−22` | `5.08509e−22 J` | non rapportée, les deux valeurs sont proches de zéro |
| Uz moyen face terminale (m) | `−5.14927314061041e−9` | `−5.1492731406099025e−9` | `5.07889e−22 m` | `/\|Uz_direct\| = 9.86331e−14` |
| Uz centre face, interpolation (m) | `−5.149730628229096e−9` | `−5.1497306282291844e−9` | `8.85083e−23 m` | `/\|Uz_centre,direct\| = 1.71870e−14` |
| Uz centre − Uz moyen, même route (m) | `−4.574876186855719e−13` | `−4.574876192819692e−13` | `5.96397e−22 m` | division de chaque écart par `\|Uz_moyen\|`: `8.88451e−5` (MF), `8.88451e−5` (direct) |

Les fonctions et calculs sources sont dans le test archivé au commit tests ci-dessus : identité énergie discrète et évaluations `U`, `W`, `u_freeᵀr_free`, lignes 463–490; Uz moyen face terminale et déplacement conjugué lignes 493–512; interpolation centre par triangles de bord lignes 213–257; agrégation de l’output avant émission lignes 522–625. Le post-traitement indépendant de ce rapport utilisait `C:\Python313\python.exe`, CPython **3.13.1**, NumPy **2.2.6**, Windows 10.0.19045; les normes de vecteurs et diagonalisation signalées sont binary64/NumPy. Les opérations Fraction du recalcul sont rationnelles par rapport aux floats binary64 exact-rationalisés et aux fractions archivées.

L’identité énergétique est vérifiée exactement par le test en fractions pour les deux routes (`exact_energy_identity_holds=true`, et le champ combiné `energy_identity_criteria_met=true`). Elle vient de `K`, `u`, `f` et `r` du même système discret : c’est une identité algébrique, pas un oracle d’énergie indépendant ni une validation physique. Les identités de forces/moments sont aussi des contrôles d’équilibre algébrique, non des observations externes. La moyenne de face et le déplacement conjugué coïncident ici, car les quatre charges terminales sont égales et `Fz=−1 N`; cette égalité n’est pas générale. Aucune tolérance d’acceptation spécifique aux écarts route des observables n’est établie par cette revue; ils quantifient seulement l’accord de deux solutions sur H1.

## 7. Lecture du FAIL et assertions atteintes

Le JUnit contient un seul testcase et une seule failure : `assert (True and True and False)`, correspondant à `exact_stiffness_symmetric and scalar_stiffness_symmetric and assembled_stiffness_symmetric`. Le payload `QF_VV_NUMERIC_RESULT` apparaît dans stdout avant cette assertion, ce que confirme l’ordre des lignes du test.

Le premier contrôle scalaire/batch est atteint avant l’assertion de symétrie. Les assertions ensuite écrites pour `product_criteria_ok`, résidus, borne solution, identités force/moment/énergie et DDL fixés sont **`NOT_REACHED`**. Le payload contient des diagnostics correspondants calculés avant l’assertion de symétrie et examinés/recalculés ici; cela ne les transforme pas en assertions pytest réussies. Le statut U3 reste `FAIL` selon le critère d’égalité exacte.

## 8. Lien avec WP12-T et limites

WP12-T rapporte que la réponse fine TET4 en flexion diffère de **66.69%** du diagnostic poutre 1D, que les incréments de déplacement croissent entre les niveaux archivés et que le taux de convergence reste inconclusif. La formule poutre n’est pas un oracle exact 3D; la moyenne nodale terminale n’est pas universellement le déplacement conjugué de charge; le cause de l’écart n’a pas été déterminée. Le recalcul U3 ne change aucun de ces constats : il compare matrix-free et assemblage direct sur le modèle discret H1 de niveau 1, et ne quantifie pas l’erreur de discrétisation des niveaux H2/H3. Ne pas extrapoler U2 : son oracle concerne deux éléments TET4 isolés en champ affine, sans flexion assemblée ni étude de maillage.

Cette revue n’établit pas un correctif ou une cause de la dissymétrie, ne modifie aucun seuil et n’autorise aucun nouvel essai. Pas de nouveau solveur, assemblage ou calcul FEM; aucun pytest n’a été lancé. Les limites de la route locale restent celles de `QUALIFICATION_LOCAL_VV` : preuve locale non attestée et WP12 `OPEN`.

## 9. Méthode de recalcul et reproductibilité

Le recalcul a été effectué avec des scripts Python temporaires exécutés depuis PowerShell (`C:\Python313\python.exe`, CPython 3.13.1, NumPy 2.2.6, Windows 10.0.19045), sans écriture dans les checkouts science/runner/tests ni dans les archives. Les références de code ci-dessus pointent vers le checkout tests propre, commit `9c7df65403fc15dc6d12365534172eac87f2ee70`; aucun module ou fonction de ce checkout n’a été exécuté pour ce post-traitement. Les seules lectures numériques ont porté sur les `receipt.json`, `receipt.sha256.json`, `selection.json`, `junit.xml`, `stdout.log`, les fichiers d’outputs du reçu, le manifeste local et le fixture archivé.

Procédure reproductible :

1. Recalculer SHA-256 du manifeste et de chaque receipt; comparer les sorties présentes à tous les hashes `output_hashes` de chaque reçu. Confirmer les champs `manifest_sha256`, identités avant/après, inventaires avant/après, import exact et sélection JUnit.
2. Extraire la ligne `QF_VV_NUMERIC_RESULT=` de `stdout.log` U3. Charger les trois matrices 36×36 et `full_free_matrix_exact_fractions` 24×24. Calculer, avec NumPy binary64, `K−Kᵀ`, normes de Frobenius, maximum absolu et distances ULP d’encodage; comparer chaque paire de matrices. Diagonaliser `K_free` avec `eigvalsh` pour le diagnostic `κ₂`; calculer `cond(K_free,∞)`.
3. Calculer les trois produits route-à-route des vecteurs archivés; comparer les deux déplacements 36 DDL, en rapportant normes absolues/relatives sans utiliser un ratio composante à composante près de zéro.
4. Pour les résidus libres, parser les fractions de `K_free`, `f_free`, et les flottants de déplacement via `Fraction.from_float`. Recalculer `r_free=K_free u_free−f_free`, comparer exactement chaque fraction archivée, puis calculer les normes L2. Réutiliser les résidus complets fractionnaires archivés et les coordonnées exact-rationalisées pour sommer réactions d’appui et moments.
5. Calculer `U=1/2 u_freeᵀK_free u_free`, `W=f_freeᵀu_free` et `u_freeᵀr_free`; comparer l’identité fractionnaire exacte, puis rapporter observables et unités.
6. Pour la borne d’opérateur, inverser `float(A0)` avec NumPy, convertir chaque valeur de `B` en `Fraction.from_float`, calculer `q=||I−A0B||∞` exactement, puis `U=||B||∞/(1−q)`. Former `E` en convertissant exactement chaque entrée binaire de chaque matrice assemblée et calculer `||E||∞`, `η=U||E||∞`, puis `η/(1−η)` exactement en fractions.

Ces étapes reproduisent les métriques décrites à partir des preuves archivées. Les valeurs propres et opérations NumPy demeurent dépendantes du post-traitement binary64 local; les sommes/résidus/identités rationnels sont exacts par rapport aux nombres binary64 entrés et aux fractions conservées, pas par rapport à une géométrie ou un matériau physique idéalisé.
