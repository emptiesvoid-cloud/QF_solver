# Comparaison structurelle — six cas, un maillage

Toutes les valeurs viennent des sidecars vérifiés ou d’opérations algébriques sur leurs NPZ. Les unités sont indiquées dans `SIX_CASES_RESULTS.csv`.

## Déplacement signé moyen de la face chargée

| `ν` | HEX8 standard | SRI historique | SRI corrigé | Historique vs standard | Corrigé vs standard | Corrigé vs historique |
|---:|---:|---:|---:|---:|---:|---:|
| 0,3 | −2,991477 mm | −3,161814 mm | −3,036130 mm | +5,69 % | +1,49 % | −3,98 % |
| 0,4999 | −0,474211 mm | −3,411156 mm | −3,410621 mm | +619,33 % | +619,22 % | −0,0157 % |

Le signe négatif correspond au chargement `−Z`. Sur ce seul cantilever très grossier, l’HEX8 standard devient environ 7,2 fois moins déformable que le SRI corrigé à `ν=0.4999`. C’est compatible avec un verrouillage volumétrique de l’HEX8 complet sur ce cas, mais cette observation n’est pas une preuve générale. Le résultat SRI à environ 3,41 mm reste très éloigné de l’ordre de grandeur Timoshenko d’environ 32 mm pour cette poutre; les trois modèles sont donc fortement affectés par la discrétisation/coarse bending response sur 4×2×2.

À `ν=0.3`, le correctif ramène le déplacement vers l’HEX8 standard par rapport à l’opérateur historique sous-raidi volumétriquement. À `ν=0.4999`, historique et corrigé donnent des déplacements presque égaux, alors que leur énergie volumique et leurs matrices diffèrent fortement. Cette faible variation d’un observable structurel ne rend donc pas l’opérateur historique correct.

## Énergie et équilibre archivés

| `ν` / formulation | Énergie interne (mJ) | Travail des charges (mJ) | `|2U-W|/|W|` recalculé | Résidu libre relatif | Fermeture force relative | Fermeture moment relative |
|---|---:|---:|---:|---:|---:|---:|
| 0,3 / standard | 1,495738 | 2,991477 | 2,05e−12 | 7,85e−12 | 1,22e−11 | 1,03e−11 |
| 0,3 / historique | 1,580907 | 3,161814 | 1,31e−12 | 3,18e−12 | 4,64e−12 | 3,76e−12 |
| 0,3 / corrigé | 1,518065 | 3,036130 | 1,09e−12 | 3,87e−12 | 5,16e−12 | 3,57e−12 |
| 0,4999 / standard | 0,237105 | 0,474211 | 2,88e−10 | 1,06e−9 | 5,34e−10 | 5,14e−10 |
| 0,4999 / historique | 1,705578 | 3,411156 | 4,04e−12 | 7,55e−10 | 2,87e−10 | 1,94e−10 |
| 0,4999 / corrigé | 1,705311 | 3,410621 | 3,13e−9 | 4,65e−9 | 1,75e−8 | 1,24e−8 |

Les résultantes de réactions en `Z` sont respectivement proches de `+1 N` et la fermeture globale est faible. La campagne n’avait pas de seuil gelé sur énergie/équilibre; ces chiffres ne sont donc pas présentés comme des gates PASS ajoutés après coup. Le résidu direct `≤1e−7` était le seul critère numérique d’équilibre explicitement enregistré.

## Matrices globales présentes dans les archives

Les différences de Frobenius de `K` assemblées et stockées, calculées sans nouvel assemblage, sont dans `FORMULATION_PAIRWISE_DIFFERENCES.csv`. Pour `ν=0.3`, `||Kcorr−Kstd||F/||Kstd||F=0,2340`; pour `ν=0.4999`, le ratio vaut `0,3934`. Entre historique et corrigé à `ν=0.4999`, la différence vaut `6,988` fois la norme de `K` historique parce que la composante volumique historique était sous-pondérée. Ces normes globales incluent tous les DDL et ne se substituent pas à la comparaison élémentaire séparée de `Kdev`, `Kvol` et `Ktotal` donnée par `THEORY_AND_FORMULATION_AUDIT.md` et `operator_comparison_results.json`.

La comparaison élémentaire antérieure trouve `Kvol,corrigé = 8 Kvol,historique`, `ΔKdev=0`, et donc `||ΔKtotal||F=||ΔKvol||F` sur l’élément affine contrôlé. Ce résultat exact porte sur cet opérateur et cette géométrie; il ne prédit pas, à lui seul, les déplacements globaux.

## Conditionnement et ressources

`cond₂(Kff)` :

| `ν` | HEX8 standard | SRI historique | SRI corrigé |
|---:|---:|---:|---:|
| 0,3 | 6,33e5 | 3,11e5 | 6,01e5 |
| 0,4999 | 1,15e8 | 1,08e8 | 8,59e8 |

Le conditionnement du SRI corrigé est le plus élevé à `ν=0.4999`. Les résultats existent en float64 et restent finis, mais une grande condition amplifie l’effet des erreurs d’arrondi et interdit de déduire une marge numérique large du seul résidu. Les durées totales des six exécutions sont 3,40–3,83 s, RSS maximale observée 106 209 280 octets (environ 101,3 MiB); ce sont des mesures de ce petit cas, pas des projections pour les futurs maillages.

## Interprétation

La campagne démontre que l’opérateur corrigé est exécutable et équilibré selon les observables enregistrées sur un maillage, et que le défaut historique modifie les matrices. Elle ne démontre ni précision absolue, ni stabilité générale, ni convergence, ni robustesse à la distorsion. La comparaison scientifique déterminante reste à faire contre un champ de référence indépendant et sur des raffinements appariés.
