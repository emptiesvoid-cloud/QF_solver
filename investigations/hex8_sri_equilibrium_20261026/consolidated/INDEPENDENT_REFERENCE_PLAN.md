# Plan de référence indépendante

## Référence de poutre : contrôle de grandeur seulement

Pour la poutre carrée `L=20 m`, `b=h=1 m`, `A=1 m²`, `I=1/12 m⁴`, force transverse `P=1 N`, théorie Timoshenko donne

```text
uz = P L³/(3 E I) + P L/(ks G A),  ks≈5/6,  G=E/[2(1+ν)].
```

Les valeurs analytiques sont environ `32,062 mm` à `ν=.3` et `32,072 mm` à `ν=.4999`. Cette référence est indépendante de l’opérateur HEX8. Elle sert à vérifier les unités, le signe, l’échelle et la tendance, mais le maillage 4×2×2, le chargement de face et les effets 3D d’encastrement ne sont pas équivalents à une poutre 1D exacte. Les déplacements archivés d’environ 3 mm montrent une erreur/discrétisation grossière importante; aucune tolérance de proximité serrée au Timoshenko ne doit donc servir à qualifier ce maillage.

## Référence 3D recommandée

Construire une solution mixte déplacement–pression d’ordre supérieur (p. ex. Q2/Q1) dans un code indépendant, avec pression incompressible stable et formulation documentée. Fixer même géométrie, traction distribuée, encastrement, loi isotrope, `E`, `ν`, et unités. Vérifier son propre patch test, équilibre, invariance au raffinement et convergence de pression/déplacement avant de l’utiliser comme oracle. Éviter de réutiliser les routines `Hex8Element`, `Hex8SRIElement`, le split ou les intégrateurs de QF Solver.

Une seconde voie est une solution manufacturée 3D avec déplacement exact choisi, force de volume/tractions dérivées analytiquement, et conditions compatibles; elle permet un taux d’erreur et un contrôle énergétique indépendant sur domaine non trivial. Cette voie mesure mieux le champ, mais ne représente pas le cas de poutre chargé en bout.

## Comparaison et seuils

L’oracle 3D doit être raffiné jusqu’à ce que son incertitude estimée sur le déplacement moyen et l’énergie soit inférieure à 0,5 %. Ensuite, le seuil proposé pour les HEX8/SRI les plus fins est erreur relative ≤5 % sur le déplacement moyen et ≤5 % sur l’énergie; utiliser les mêmes projections et références pour les trois formulations. Les seuils sont à faire accepter et geler avant les calculs; ils ne sont pas appliqués aux preuves actuelles. Si l’oracle ne converge pas ou n’est pas stable près de `ν=.5`, classer les comparaisons `INCONCLUSIVE`.

La poutre Timoshenko et le résultat mixte ne sont pas interchangeables : la première est une référence réduite avec hypothèses de poutre, la seconde est un calcul 3D dont l’indépendance et l’incertitude doivent être démontrées. Une comparaison inter-code seule n’est pas indépendante si les deux codes partagent même discrétisation, split constitutif ou source d’intégration.

Références de contexte : [Hughes (1980), selective integration](https://doi.org/10.1002/nme.1620150914); [Belytschko & Bindeman (1993), stabilization of eight-node hexahedra](https://doi.org/10.1016/0045-7825(93)90124-G); [Sandia Sierra/SD Theory Manual](https://www.sandia.gov/app/uploads/sites/315/2025/07/SD_Theory_5_18.pdf). Elles orientent le protocole et ne remplacent pas la référence numérique à construire.
