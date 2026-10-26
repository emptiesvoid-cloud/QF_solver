# QF Solver — HEX8-SRI : premières conclusions indépendantes

**Date :** 26 octobre 2026

**Branche d’analyse :** `research/hex8-sri-equilibrium`

**Base :** branche `emptiesvoids-cloud/0.2.12`, commit `2aa994f34900f39bef8df9db5fb025157fb694bb`

**Worktree :** `E:\QFSolverAgents\hex8-sri-research`

## Décision provisoire

La revue trouve **un défaut de quadrature volumique démontré** dans la version historique de HEX8-SRI : la règle au centre n’appliquait pas le poids de Gauss `8` requis sur le cube de référence `[-1,1]^3`. Le correctif minimal est conservé sur cette branche. Le test analytique échoue sur le source parent avec l’énergie attendue divisée par huit, puis passe avec le correctif; il est désormais vérifié par le lanceur local de développement.

Ce défaut de poids ne suffit pas à expliquer les fermetures globales force/moment. Le post-traitement multiprécision permet maintenant de les relier à la non-annulation numérique, très faible mais non nulle, des modes rigides de la matrice assemblée archivée. Les résidus nodaux libres et l’identité énergie-travail, eux, disparaissent après résolution multiprécision des mêmes coefficients.

**Recommandation :** conserver HEX8-SRI au statut expérimental. Ne pas intégrer ce correctif ni promouvoir SRI dans v0.2.12 sur la seule base de cette revue. La release v0.2.12 peut rester indépendante si elle n’inclut aucune promotion de SRI. Reprendre l’investigation avant toute décision de maturité v0.3.0, après validation du correctif et comparaison appariée.

## Périmètre et intégrité

- Worktree indépendant créé depuis le HEAD de l’intégration. Les modifications locales présentes dans le worktree source n’ont pas été copiées.
- Les trois répertoires d’archives demandés ont été lus sans modification. Les SHA-256 des deux `numerical-state.npz` sont conformes aux manifestes : `85a4f5ca…57ccd775` (régulier) et `ab61364c…86ec3fdb` (mince/skew).
- Le manifeste d’exécution historique rattache les échecs au source `hex8_sri.py` SHA-256 `975e8dbb…01ad9869`, identique au code de base avant le correctif préparé ici.
- Aucun solveur global, assemblage multiélément FEM, maillage nouveau, calcul de contrainte, seuil, runner, politique ou preuve WP12/WP13 n’a été exécuté ou modifié. Les calculs ajoutés portent sur les matrices d’un seul élément affine et sur les vecteurs archivés.
- `git diff --check` et l’analyse syntaxique AST du source et du test préparé réussissent.

## 1. Audit des résidus et fermetures

Pour un système linéaire symétrique, notons `r = K u - F`. Les réactions archivées suivent la convention correcte `R_c = r_c` sur les DDL fixés et `R_f = 0` sur les DDL libres. Pour un mode rigide nodal `q` (translation, ou déplacement `ω × x`), la fermeture correspondante vérifie :

```text
qᵀ(F + R) = uᵀKᵀq − q_fᵀr_f
```

Si la matrice annule exactement le mode rigide (`Kq = 0`), la fermeture est donc la **projection** du résidu libre, `−q_fᵀr_f`. La norme du résidu nodal libre, les trois projections de force, les trois projections de moment et l’écart énergie-travail sont des observables distinctes : une petite projection ne borne pas la norme du résidu.

J’ai reconstruit les six modes avec les coordonnées archivées et évalué leurs projections sur les valeurs float64 exactes de `K`, puis sur les déplacements/réactions D110 archivés. Pour les deux cas, les fermetures multiprécision coïncident avec `u_HPᵀKq` à moins de `3,2×10⁻¹⁴` en valeur absolue. Les résidus relatifs `||Kq||₂/(||K||₂||q||₂)` calculés sur la matrice archivée restent tous sous `2,3×10⁻¹⁷` : c’est un défaut d’invariance au niveau de l’arrondi de la matrice, faible relativement à `K`, mais suffisant après projection par `u_HP` pour dépasser la porte gelée.

| Cas | Fermeture des forces avec `u_HP` (N), x/y/z | Fermeture des moments à l’origine avec `u_HP` (N·m), x/y/z |
|---|---|---|
| `ν=0,4999`, nx=16, régulier | `(-8,9955e-12, -2,7675e-10, -1,6565e-9)` | `(-8,2301e-10, 2,1938e-8, -3,8629e-9)` |
| `ν=0,495`, nx=4, mince/skew | `(3,5765e-12, -4,1751e-10, -1,0552e-8)` | `(-9,5939e-9, 1,8726e-7, -6,5615e-9)` |

Les normes de fermeture D110 rapportées sont `1,68e-9 N` et `2,23e-8 N·m` pour le cas régulier, puis `1,056e-8 N` et `1,876e-7 N·m` pour le cas mince. Les portes historiques normalisées restent au-dessus de `1e-10` : environ `1,68e-9` / `3,34e-9` (force/moment, régulier) et `1,06e-8` / `2,81e-8` (mince). La fermeture persistante réside donc dans le **K archivé et sa représentation float64**; cela ne prouve pas une erreur SRI. Le calcul précis localise le défaut au niveau de `Kq`, mais ne départage pas encore calcul de `B`, intégration, symétrisation et scatter global. Une matrice HEX8 standard appariée n’a pas été archivée dans ces deux campagnes.

Contrôles croisés des conditions aux limites et réactions : le masque fixé et les indices libres sont des complémentaires exacts; les 27 DDL fixés couvrent neuf nœuds complets `XYZ` à `x=0`; `R_f=0`; les réactions fixes égalent le résidu archivé; `Ku−F−R` est nul aux appuis et égale le résidu libre ailleurs. Le signe `R=Ku−F` est donc cohérent. La somme des charges vaut nominalement `−1 N` en z et leur moment à l’origine `(-0,5, 20, 0) N·m`. Le changement du point de référence modifie le défaut de moment selon `M_a = M_0 − a × (ΣF+ΣR)`; ce n’est pas une contradiction.

Les diagnostics antérieurs excluent aussi l’ordre de sommation global comme cause principale : Neumaier et `math.fsum` laissent les écarts de force/moment à des niveaux très inférieurs aux fermetures observées.

### Solveur et énergie

La résolution D110 des `Kff` archivés réduit les résidus libres de `1,10073e-8 N` à `6,50e-105 N` (régulier) et de `2,66925e-8 N` à `1,99e-104 N` (mince). L’écart énergie-travail D110 tombe respectivement à `4,33e-107 J` et `−1,39e-107 J`. Cela établit une contribution de la résolution float64 à l’échec nodal et énergétique sur le système stocké; cela ne certifie ni l’assemblage ni la solution physique. Les conditionnements `cond₂(Kff)=5,46e8` et `2,08e9` rendent le cas mince nettement plus sensible.

Les portes ne mesurent pas la même chose. L’identité énergie-travail est une projection scalaire du résidu (`0,5 uᵀ(Ku−F)`); le résidu libre est une norme vectorielle. Le cas régulier peut donc passer la porte d’énergie historique tout en échouant au résidu libre et aux fermetures.

## 2. Revue de HEX8-SRI

### Formulation correcte en théorie, poids erroné dans le source archivé

Le split isotrope en Voigt ingénieur est correct :

```text
Cvol = κ m mᵀ,   m=(1,1,1,0,0,0)ᵀ,   κ=E/[3(1−2ν)]
Cdev = C − Cvol
```

Le code source de matériau place `μ` sur les diagonales de cisaillement; la construction de `B` utilise les cisaillements ingénieur, ce qui rend la partition cohérente. La transformation de gradients suit `∇x N = ∇ξ N J⁻ᵀ` avec `J = (∂N/∂ξ)ᵀX`. Le terme déviatorique utilise bien les huit points `2×2×2`; le terme volumique n’utilise que le centre.

Sur `[-1,1]^3`, une quadrature de Gauss à un point a pour poids produit `2×2×2=8`. Le source pré-correctif calcule pourtant seulement `detJ₀ B₀ᵀ Cvol B₀`. Pour le cube physique unité, `detJ₀=1/8`; avec le champ affine `u=x`, l’énergie volumique du code est donc **un huitième** de `0,5 κ (tr ε)² V`. Le point central est correct, c’est son poids qui manque. Le correctif ajoute `volumetric_integration_weight = 8.0` et l’applique au terme central.

La formulation SRI reconnue sépare bien les énergies déviatorique et dilatationnelle, puis intègre le terme volumique au centre et le terme déviatorique sur `2×2×2`; voir le [manuel théorique Sierra/SD de Sandia, SAND2024-01791, §§5.3–5.4](https://www.sandia.gov/app/uploads/sites/315/2025/07/SD_Theory_5_18.pdf) et l’étude [Visintainer, Bittencourt & Braun (2021)](https://doi.org/10.1590/1679-78256441). Ces références ne justifient pas d’omettre le poids de la règle.

### Autres points contrôlés et risques

- Les deux géométries archivées ont des déterminants positifs au centre et aux huit points complets : `0,0390625 m³` par HEX8 pour le cas régulier et `0,00625 m³` pour le cas mince/skew. Le Jacobien ne révèle pas d’inversion dans ces preuves.
- La validation héritée de HEX8 n’échantillonne que les huit points complets. Le terme SRI évalue aussi le centre; les cas archivés sont positifs à ce point, mais un contrôle explicite du centre (et une couverture de distorsions plus forte) reste à inclure dans la suite.
- Chaque contribution `Bᵀ C B` est symétrisée. Avec `detJ>0` et des blocs constitutifs semi-définis positifs, le noyau est théoriquement symétrique et semi-positif; cette symétrisation ne prouve pas à elle seule la positivité. Les anciens essais WP10/WP13 indiquent six modes rigides et aucun mode nul supplémentaire sur leurs géométries gelées; ce résultat doit être rejoué après le poids corrigé.
- Il n’y a pas de stabilisation d’hourglass. Cette formulation n’est pas une intégration uniforme à un point : la partie déviatorique garde ses huit points. Les essais historiques bornés ne signalent pas de mode nul supplémentaire, sans couvrir toutes les distorsions.
- `Cdev` est calculé en soustrayant `Cvol` de la matrice élastique isotrope. À `ν=0,4999`, `κ/μ≈4999,7`; la soustraction peut perdre des chiffres significatifs. C’est une hypothèse numérique secondaire à tester contre la forme analytique directe de `Cdev`, pas un défaut démontré dans les fermetures archivées.
- La géométrie mince `L/h=500` et son oracle historique poutre non recalé à `h=0,04 m` rendent toute conclusion de précision physique prématurée.

La classe reste séparée de HEX8 standard, isotrope linéaire seulement et non enregistrée dans le registre public. Le correctif préparé n’altère donc ni le standard HEX8 ni une route de production dans ce worktree.

## 3. Hypothèses classées

| Rang | Hypothèse | État | Vérification discriminante |
|---:|---|---|---|
| 1 | Poids `8` absent au point volumique | **Démontrée analytiquement et par le test rouge/vert** | Le test donne `468,75` au lieu de `3 750` sur le source historique, puis passe avec la correction. |
| 2 | Erreur de résolution float64 sous mauvais conditionnement | **Confirmée pour le système archivé** | Résolution D110 : résidu libre et énergie-travail disparaissent. |
| 3 | Non-annulation float64 des modes rigides de `K` | **Confirmée pour les fermetures après résolution D110** | Les six projections de fermeture correspondent à `u_HPᵀKq`; `Kq/K` est de l’ordre de `1e-17`. Cause d’arrondi/assemblage, non attribution à SRI seul. |
| 4 | Amplification par géométrie mince/skew et conditionnement | **Plausible et cohérente avec les mesures** | `cond₂(Kff)` est environ 3,8 fois plus élevé; oracle non apparié à la section. |
| 5 | Signe, partition des DDL, réaction ou réduction globale erronés | **Peu plausible; indices contraires** | Masques, réactions et convention vérifiés; les sommes compensées conservent les fermetures. |
| 6 | Annulation numérique dans `C − Cvol` près de l’incompressibilité | **Plausible, non isolée** | Comparer `Cdev` actuel à `2μ` fois le projecteur déviatorique, puis réassembler. |
| 7 | Porte `1e-10` sous le plancher numérique des matrices archivées | **À examiner, sans retoucher le seuil** | Les fermetures fixes après D110 sont déjà `1e-9–1e-7` dans les unités normalisées historiques. Préserver les seuils et séparer les métriques. |

## 4. Matrice comparative élargie à envisager après la première gate

À autoriser séparément avant tout calcul global; tous les cas comparatifs devront garder même maillage, matériau, charges nodales, appuis, ordre des DDL, solveur et tolérances entre HEX8 et HEX8-SRI. Les données corrigées doivent recevoir un nouvel identifiant et ne pas remplacer WP12/WP13.

| Étape | Cas | Comparaison bornée | Mesures |
|---|---|---|---|
| A | Un cube unité et un cube modérément gauchi, `ν=0,30` puis `0,4999` | HEX8 standard vs SRI corrigé; champ affine analytique | Poids volumique, énergie, symétrie, six modes rigides, rang/valeurs propres, déterminants centre et Gauss. |
| B | Console régulière `20×1×1`, `nx=4,8,16`, `ny=nz=2`; `ν=0,30` et `0,4999` | HEX8 standard vs SRI corrigé, mêmes charges et appuis | Déplacement de pointe, énergie, résidu libre, fermetures forces/moments avec définitions séparées, convergence vs oracle Timoshenko. |
| C | Cas mince/skew `20×1×0,04`, skew `0,006(x/L)(y−0,5)`, `ν=0,495`, `nx=4,8` | HEX8 standard vs SRI corrigé; oracle 3D indépendant ou oracle poutre recalculé pour `h=0,04` | Même observables que B, déterminants, conditionnement, sensibilité au raffinement. |
| D | Distorsions gelées régulière, skew, stretched, warped, near-degenerate | SRI corrigé seulement, sur les formes déjà documentées | Patch affine, modes rigides, positivité/rang, énergie et orientation; la suite de validation ne promeut pas le candidat à elle seule. |

## 5. Vérifications et état du correctif

| Vérification | Résultat |
|---|---|
| Intégrité des NPZ archivés | SHA-256 conforme aux rapports; archives intactes. |
| Conditions aux limites et réactions | Masque, DDL libres, signe et reconstruction cohérents. |
| Modes rigides de `K` | Six projections évaluées; `||Kq||/(||K||||q||) < 2,3e-17` sur les deux matrices. |
| Résolution/énergie D110 des archives | Résultats reproduits et reliés aux projections rigides; aucun nouveau solveur appelé. |
| Test `test_center_volumetric_rule_integrates_constant_over_reference_hex` | **Rouge/vert confirmé** via `scripts/development_autonomous.py --scope unit`, nodeid exact. Essai 2 sur le source parent : `PYTEST_FAILED` à l’assertion, énergie `468,75` vs `3 750`. Essais 3 et 4 avec le correctif : `PASS`. Les essais 2–4 sont archivés sous `.codex/development-runs/standard/unit/dev-hex8-sri-quadrature/`. |
| Garde-fou E01 | L’empreinte initiale du checkout CRLF différait de l’empreinte brute LF épinglée; les octets logiques étaient identiques aux blobs Git. Les empreintes attendues n’ont pas été changées. Deux règles `-text` exactes dans `.gitattributes` préservent maintenant les octets des deux modules épinglés; les empreintes sur disque concordent et la collecte/test passe avec le garde actif. Voir §6. |
| Correctif poids 8 | Appliqué à `src/solveur/elements/solid/hex8_sri.py`, validé par le test rouge/vert et comparé au bloc volumique intégré sur 2×2×2. Voir §7 et `operator_comparison_results.json`. |
| Campagne HEX8 vs HEX8-SRI | Non lancée. Le worktree de recherche n’est pas une cible FEM enregistrée dans la politique actuelle. |

Le correctif est vérifié au niveau unitaire et des opérateurs d’un seul élément; cela ne constitue pas une validation FEM ni une qualification. Les artefacts historiques restent inchangés et gardent leurs statuts `PYTEST_FAILED` / `KEEP_EXPERIMENTAL` selon leurs contrats d’origine.

## Sources et code relus

- `src/solveur/elements/solid/hex8_sri.py` — split et quadrature SRI.
- `src/solveur/elements/solid/hex8.py` — fonctions de forme, `J`, `B`, contrôle du déterminant et intégration complète.
- `src/solveur/elements/solid/common.py` — convention de déformation de cisaillement.
- `src/solveur/materials/solid.py` — matrice isotrope.
- `src/solveur/core/solvers/static.py`, `src/solveur/core/audit.py` — résidu, réactions et bilans.
- Archives : rapports de fermeture, précision D110 et diagnostic r2 dans les trois répertoires WP12 cités par la mission.

## 6. Résolution documentée du garde-fou E01

Le garde-fou a été introduit dans `tests/unit/conftest.py` par le commit `a0846af0249ac3f3a37ec4e9c4900f1311c86238` (`Integrate bounded experimental WP-E01 Hencky scope`). L’historique du fichier E01M remonte à ce même commit; l’empreinte épinglée dans le garde-fou est celle des octets du blob Git introduit avec le test, et le blob E01Q est également identique à son empreinte épinglée. Les valeurs présentes dans le `conftest.py` courant n’étaient donc pas périmées.

| Module surveillé | SHA-256 attendu et blob Git | SHA-256 du checkout CRLF initial | SHA-256 courant après correction du checkout |
|---|---|---|---|
| `tests/unit/test_wp_e01m_hencky_material_point.py` | `cdd2651e9427c0e64284a75671d83d4f14cdd916a979759be0422f44dde84bfc` | `0d58ad2a499d13f84752f931c872c987577f8d3faae52cac06a8449ab2e2cec4` | `cdd2651e9427c0e64284a75671d83d4f14cdd916a979759be0422f44dde84bfc` |
| `tests/unit/test_wp_e01q_hencky_tangent.py` | `a99bcc6ea32bff3e2a669d2923380033f23e587aab95f612ab4047f98b7d7b50` | `9cc0260756b68b4da9397fe0c9fbe6d15abf0783ba25c6cbb400e613f14cbb37` | `a99bcc6ea32bff3e2a669d2923380033f23e587aab95f612ab4047f98b7d7b50` |

La différence initiale est uniquement de représentation des fins de ligne : les fichiers CRLF, après normalisation des fins de ligne, sont identiques aux blobs LF; aucun contenu, nom de test ou code E01 n’a divergé. `core.autocrlf=true` matérialisait CRLF, tandis que `pytest_collect_file` calcule `sha256(file_path.read_bytes())` directement sur les octets du disque. Le garde-fou lève une `pytest.UsageError` pendant la collecte si le digest diffère; en cas de correspondance, il marque ces tests `numerical_unit`. Son contrat borne ces fichiers à des vérifications numériques locales isolées, sans assemblage global ni solveur public/FEM.

La résolution conserve ce contrat et les deux SHA épinglés. `.gitattributes` porte maintenant deux règles `-text` spécifiques à ces modules hash-bound, conformément au traitement déjà utilisé pour les preuves hash-bound sous `qualification/**`. Les blobs Git demeurent inchangés et les octets du checkout correspondent maintenant aux deux SHA attendus. L’essai initial `attempt-0001` a bien été une erreur de collecte avant le corps du test; après la correction des fins de ligne et du checkout, les essais rouges/verts ont atteint le corps. Aucun test E01 lui-même n’a été exécuté dans cette investigation.

## 7. Preuve quadrature et mesures des matrices locales

En notation Voigt ingénieur, pour l’élasticité isotrope :

```text
m = (1, 1, 1, 0, 0, 0)ᵀ
Cvol = κ m mᵀ,    κ = λ + 2μ/3 = E/[3(1−2ν)]
Cdev = C − Cvol
Kdev = Σ(i=1..8) wi det(Ji) Biᵀ Cdev Bi,    wi = 1
Kvol = ∫[-1,1]³ Bᵀ Cvol B det(J) dξ dη dζ
```

La quadrature complète HEX8 est le produit tensoriel des points `±1/√3`; chaque poids 1D vaut 1, donc chacun des huit poids 3D vaut 1 et leur somme vaut 8. La règle réduite au centre doit appliquer son poids produit `2·2·2=8` : `Kvol,SRI = 8 det(J0) B0ᵀ Cvol B0`. Dans le source historique, le code calculait `det(J0) B0ᵀ Cvol B0`. `det(J)` ne contient que la transformation géométrique; `B` ne contient que la transformation des gradients. Le split constitutif n’ajoute pas de facteur et `stiffness()` additionne simplement les blocs déviatorique et volumique. Il n’existe donc aucun facteur 8 implicite ailleurs. Le correctif multiplie explicitement le bloc central par `volumetric_integration_weight = 8.0`.

Référence analytique indépendante, cube physique `[0,1]³`, `det(J0)=1/8`, volume `V=8 det(J0)=1` : le champ affine `u=x` donne `ε=I` et `Uvol=½κ(tr ε)²V=9κ/2`. Le source historique donne exactement `9κ/16`, soit `Uancien/Uexact=1/8`; le correctif donne `Ucorr/Uexact=1`. Avec `E=1000`, `ν=0,3`, ces énergies sont `468,75` et `3 750`; ce sont les valeurs observées dans les essais rouge/vert. Le script de matrices emploie `E=10⁶`, où ces valeurs sont `468 750` et `3 750 000`. Pour le champ affine sans trace `u=(x,−y,0)`, `Udev=2μV`; ce contrôle reste inchangé avant/après la correction.

Les normes ci-dessous sont les normes de Frobenius des matrices élémentaires, pour le cube unité et `E=10⁶` dans les unités du modèle. `Kvol HEX8` désigne la référence volumique à huit points; `Kdev` est commun aux deux SRI et au bloc déviatorique de HEX8 standard.

| `ν` | `κ/μ` | `||Kvol ancien||F` | `||Kvol corrigé||F` | `||Kvol HEX8||F` | `||Kdev||F` | `||Ktotal ancien||F` | `||Ktotal corrigé||F` | `||Ktotal HEX8||F` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0,3 | 2,1667 | 1,5625e5 | 1,2500e6 | 1,34179e6 | 9,86924e5 | 9,99216e5 | 1,59264e6 | 1,72403e6 |
| 0,4999 | 4 999,67 | 3,12500e8 | 2,50000e9 | 2,68359e9 | 8,55391e5 | 3,12501e8 | 2,50000e9 | 2,68365e9 |
| 0,49999 | 49 999,67 | 3,12500e9 | 2,50000e10 | 2,68359e10 | 8,55339e5 | 3,12500e9 | 2,50000e10 | 2,68359e10 |

Mesures directes des changements : `Kvol,corrigé = 8 Kvol,ancien` à l’égalité float64 sur ces matrices; `||ΔKvol||F = ||ΔKtotal||F`, et `ΔKdev=0`. La variation relative de `Ktotal` par rapport à l’ancien vaut respectivement `109,46 %`, `699,997 %` et `700,000 %`. La distance relative `||Ktotal,corrigé−Ktotal,HEX8||F / ||Ktotal,HEX8||F` vaut `28,29 %`, `36,35 %` et `36,35 %`. La matrice de SRI corrigée n’est donc pas identique à HEX8 pleinement intégré : la règle sélective volumique reste au centre, alors que HEX8 intègre le bloc volumique aux huit points. Leur énergie pour les champs affines de contrôle coïncide malgré cette différence matricielle.

Aux trois valeurs de `ν`, toutes les matrices totales ont six valeurs propres nulles selon le seuil `1e−10 λmax`, aucun mode supplémentaire détecté, et une plus petite valeur propre positive d’environ `64,10 k` (`ν=0,3`) ou `55,56 k` (`ν≥0,4999`). `Kdev` seul a sept valeurs propres nulles : les six modes rigides plus la dilatation uniforme, qui est bien dans le noyau déviatorique et est reprise par `Kvol`. Le résidu relatif maximal sur les six modes rigides est respectivement `7,3e−17`, `7,1e−17` et `7,3e−17`. La symétrie est exacte pour les matrices de production de l’élément; le bloc de référence non symétrisé à huit points n’a qu’un écart d’arrondi relatif de l’ordre de `1e−17`. Les minima propres légèrement négatifs des matrices totales restent eux aussi de l’ordre de `1e−17 λmax`, sans valeur négative au-delà du seuil numérique utilisé.

Quand `ν` approche `0,5`, `κ/μ` augmente d’environ `2,17` à `5,0e4`, le bloc `Kvol` croît avec `κ`, et `Kdev` reste à l’échelle de `μ`. Le champ dilatationnel retrouve donc l’énergie physique manquante; les six modes rigides sont conservés, sans mode nul local additionnel. Cela ne tranche pas le verrouillage volumique, la convergence ou la précision d’une structure globale. La comparaison directe de `Cdev=C−Cvol` à `2μPdev` montre une erreur relative de `1,7e−16`, `4,4e−13`, puis `3,5e−12`; le risque de perte de chiffres par soustraction s’accroît près de l’incompressibilité et doit rester dans l’audit.

Les calculs reproductibles et tous les résultats non arrondis sont dans `compare_element_operators.py` et `operator_comparison_results.json`. Ils ne font ni assemblage multiélément, ni résolution globale, ni modification de paramètres de qualification.

## 8. Protocole global limité proposé — en attente d’autorisation

Première campagne proposée : **six résolutions au total**, pas les 16 cas d’une grille complète. Utiliser un unique HEX8 régulier en porte-à-faux, dimensions `L×h×h = 20×1×1`, maillage `4×2×2` (16 éléments affines), encastrement complet de la face `x=0` et même charge nodale cohérente sur `x=L`. Croiser trois opérateurs (`HEX8` standard, SRI historique comme contrôle, SRI corrigé) avec `ν=0,3` et `ν=0,4999`; conserver le même `E`, le même ordonnancement des DDL, les mêmes appuis, charges, solveur direct et tolérances. Chaque formulation doit produire le même jeu d’observables : déplacement moyen `Uz` de la face chargée, énergie de déformation et travail extérieur, norme et résidu relatif des DDL libres, résultante des réactions et fermeture des forces et moments au même point de référence. Garder les fichiers et manifestes distincts des preuves historiques.

Avant toute exécution, il faudra un manifeste propre à cette campagne, une décision Owner explicite, et une méthode de harness qui appelle l’élément SRI interne sans l’enregistrer dans l’API publique. Ne pas étendre le maillage ni ajouter le cas skew dans cette première autorisation; les raffinement/distorsions pourront être décidés après revue des six résultats. Aucun calcul global n’a été lancé ici.

## 9. Recommandation

Conserver le correctif et les résultats dans `research/hex8-sri-equilibrium`. Le défaut de facteur 8 est démontré, le test analytique est rouge sur le parent et vert avec le correctif, et les contrôles locaux de symétrie, énergie et modes rigides sont cohérents. Garder HEX8-SRI au statut expérimental jusqu’à la première campagne globale limitée, sa revue Owner et une validation de distorsions. Pas de cherry-pick ni d’intégration à v0.2.12 dans ce travail.
