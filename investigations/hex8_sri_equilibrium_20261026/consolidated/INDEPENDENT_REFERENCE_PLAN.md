# Plan de référence indépendante

## Vérification de l’observable et de la poutre Timoshenko

Le modèle 3D historique et le repère de poutre ont les mêmes résultantes globales : `L=20 m`, section carrée `1×1 m`, `E=1 MPa`, une traction uniforme `−1 Pa` sur `1 m²` à `x=L` (force résultante `−1 N` en `Z`) et une face entière encastrée à `x=0`. La traction nodale cohérente porte le résultant par le centre de la face, sans couple local autour du centre de section. L’observable QF est la moyenne surfacique de `UZ` calculée avec les poids cohérents de trace Q1; pour une cinématique de poutre plane et affine sur la section, cette intégrale est la translation centroidale. Dans le solide, le champ moyen de face inclut encore le gauchissement et les effets d’extrémité.

Pour la poutre carrée `L=20 m`, `b=h=1 m`, `A=1 m²`, `I_y=1/12 m⁴`, force transverse `P=1 N`, théorie Timoshenko donne

```text
uz = P L³/(3 E I_y) + P L/(k G A),  G=E/[2(1+ν)].
```

La flexion vaut `32,000 mm`. Avec `k=5/6`, les valeurs totales en valeur absolue sont `32,0624 mm` pour `ν=.3` et `32,0720 mm` pour `ν=.4999`. Le facteur de Cowper (section rectangulaire) `k=10(1+ν)/(12+11ν)` donne `32,0612 mm` et `32,0700 mm`. Le choix du facteur change ces valeurs de seulement `0,0012–0,0020 mm`, puisque la part du cisaillement est faible dans cette géométrie.

Le rapport `h/L=1/20` fait de Timoshenko un repère indépendant de signe, unités, échelle et tendance. Une guidance de poutres Timoshenko indique une utilisation pertinente pour les dimensions de section jusqu’à environ `1/8` des distances axiales typiques; `1/20` est plus élancé que ce rapport, mais cette guidance n’est pas une borne d’erreur universelle ([Abaqus, Choosing a beam element](https://abaqus.uclouvain.be/English/SIMACAEELMRefMap/simaelm-c-beamelem.htm)). Le maillage `4×2×2` reste trop grossier pour évaluer la qualité absolue, et l’encastrement 3D / la traction sur face ne reproduisent pas les champs locaux d’une poutre 1D. Les déplacements QF historiques autour de `3–3,4 mm` sont très éloignés des `32 mm`; cela révèle une réponse discrète à résoudre par convergence, sans privilégier d’avance le SRI parce qu’il est plus souple.

## Référence 3D indépendante recommandée

Construire une solution mixte indépendante déplacement–pression d’ordre supérieur, avec espaces satisfaisant une condition inf-sup appropriée (proposition à qualifier : DOLFINx/FEniCSx sur tétraèdres avec déplacement vectoriel P2 et pression P1 continue, Taylor–Hood). La formulation linéaire doit être documentée, par exemple `2μ ε_dev(u):ε_dev(v) + p div(v) + q div(u) − (1/κ)pq = l(v)` avec une convention de signe fixée. Le calcul doit utiliser la même géométrie, traction distribuée, encastrement, `E`, `ν`, unités et projection intégrale de `UZ` sur la face chargée. Ne pas réutiliser `Hex8Element`, `Hex8SRIElement`, le split ni les règles d’intégration QF. Le backend proposé n’est pas installé dans l’environnement actuel (`dolfinx`, `fenics`, `petsc4py`, `skfem` absents); son environnement, sa version et sa source doivent être acquis et empreintés avant de préparer son manifeste final.

La référence ne sera qualifiée qu’après ses patch tests analytiques, ses bilans, la stabilité du solveur mixte et un raffinement démontrant une incertitude `≤0,5 %` sur l’observable et l’énergie. Tant que ces contrôles n’existent pas, aucun seuil de précision contre le 3D ne peut être évalué.

Une seconde voie est une solution manufacturée 3D avec déplacement exact choisi, force de volume/tractions dérivées analytiquement, et conditions compatibles; elle permet un taux d’erreur et un contrôle énergétique indépendant sur domaine non trivial. Cette voie mesure mieux le champ, mais ne représente pas le cas de poutre chargé en bout.

## Comparaison et seuils

L’oracle 3D doit être raffiné jusqu’à ce que son incertitude estimée sur le déplacement moyen et l’énergie soit inférieure à 0,5 %. Le seuil proposé pour les maillages HEX8/SRI les plus fins est une erreur relative ≤5 % sur le déplacement moyen et ≤5 % sur l’énergie; les seuils sont à faire accepter et geler avant les calculs. Ils ne sont pas appliqués aux preuves historiques. Si l’oracle ne converge pas ou n’est pas stable près de `ν=.5`, classer les comparaisons `INCONCLUSIVE`.

La poutre Timoshenko et le résultat mixte ne sont pas interchangeables : la première est une référence réduite avec hypothèses de poutre, la seconde est un calcul 3D dont l’indépendance et l’incertitude doivent être démontrées. Une comparaison inter-code seule n’est pas indépendante si les deux codes partagent même discrétisation, split constitutif ou source d’intégration.

Références de contexte : Cowper (1966), [shear coefficient](https://doi.org/10.1115/1.3625046); [Hughes (1980), selective integration](https://doi.org/10.1002/nme.1620150914); [Belytschko & Bindeman (1993), stabilization of eight-node hexahedra](https://doi.org/10.1016/0045-7825(93)90124-G); [Sandia Sierra/SD Theory Manual](https://www.sandia.gov/app/uploads/sites/315/2025/07/SD_Theory_5_18.pdf). Elles cadrent le protocole; elles ne remplacent pas la référence numérique à construire.
