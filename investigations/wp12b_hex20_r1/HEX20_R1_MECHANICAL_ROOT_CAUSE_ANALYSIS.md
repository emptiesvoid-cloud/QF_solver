# HEX20 R1 — analyse mécanique sur archives

Statuts : **déplacement CONFIRMED**, **écart QUAD8 CONFIRMED** pour le cas affine R1. Le verdict R1 reste `PYTEST_FAILED / PROVENANCE_MISMATCH`. Cette analyse ne valide ni les géométries courbes ni une correction structurelle par un nouveau calcul.

## Provenance et limites

Les SHA-256 vérifiés sont : manifeste autorisé `b901a3970ef4d59d28a9d031264d8817336bfdeb4756f4f2e96164f6ef041ab3`, sidecar `dee3c6976929954b7f4c5a678d474b3a151f7821db9c334f0f01d22320d2133e`, rapport R1 `e1d8577c48bf54c25ed3105db5b9a8eb8cec1943ac9ee46adcf127bcd4e82a7f`, ledger `ab5a8e4967ca204898f2eeec52b50f0c6b8e603d0328c3dff06926ff10669f53`. Le script [analyze_archive.py](analyze_archive.py) refuse un sidecar dont le hash diffère; [R1_DERIVED_MATRIX_COMPARISON.json](R1_DERIVED_MATRIX_COMPARISON.json) conserve ses résultats détaillés. Il lit K, F, u et les vecteurs d'oracle archivés, sans assembler ni résoudre un système.

## Champ, appuis et géométrie

Le champ attendu est `u=(1e-4 x,0,0)` sur le cube de 1 m. Les huit nœuds de la face `x=0` sont contraints sur les trois composantes; `u_affine,c=0` sur les 24 DDL contraints, compatible avec ces appuis. Les 36 autres DDL sont libres. Pour les six faces, les milieux d'arêtes coïncident avec la moyenne des coins, les normales calculées à partir des boucles coïncident avec les normales géométriques et le jacobien surfacique affine vaut `0,25 m²` sur le carré de référence. Les fonctions QUAD8 codées sont les polynômes sérendipité usuels. Ces constats portent sur le cube R1.

## Démonstration du défaut de chargement

La branche QUAD8 de `src/solveur/loads/integration.py` utilisait `±1/√3, 0` avec les poids `5/9, 8/9, 5/9`. Or la règle de Gauss à trois points utilise `±√(3/5), 0`. Le second moment de la règle historique vaut `10/27` au lieu de `2/3`. Avec le jacobien `A/4`, les intégrales nodales historiques valent `−17A/108` aux coins et `11A/27` aux milieux; l'intégrale exacte vaut respectivement `−A/12` et `A/3`. Les écarts prédits sont `−2A t/27` et `+2A t/27`, exactement ceux observés pour les cinq faces chargées. Voir [comparaison par face et par nœud](HEX20_R1_LOAD_VECTOR_COMPARISON.md).

En posant `Fq` la somme des cinq vecteurs indépendants QUAD8, `Fp` la charge de production et `δu=u_num−u_affine`, les opérations **matricielles sur les données R1** donnent :

| Relation sur les DDL libres | Norme infinie |
|---|---:|
| `r_aff=Kff u_aff,f − (Fp,f−Kfc u_aff,c)` | `2 094 017,094 N` |
| `r_num=Kff u_num,f − (Fp,f−Kfc u_num,c)` | `9,347e-9 N` |
| `r_aff + (Fp−Fq)f` | `9,779e-9 N` |
| `Kff δu_f − (Fp−Fq)f` | `9,347e-9 N` |
| `r_aff + Kff δu_f − r_num` | `6,752e-9 N` |

En outre `||K u_aff−Fq,six faces||∞=9,779e-9 N`. La charge d'oracle de la face encastrée n'a aucun DDL libre; elle est donc nulle après restriction aux DDL libres. Ces identités établissent, à l'arrondi près, que l'écart de charge nodale archivé explique l'écart de déplacement R1 pour la matrice et les appuis archivés. Elles ne supposent pas une nouvelle résolution.

## Énergie et équilibre

`½u_numᵀKu_num=1540,116723 J` contre `½u_affᵀKu_aff=1413,461538 J`, soit `+126,655185 J` (`8,9606 %`). La décomposition `u_affᵀKδu + ½δuᵀKδu` vaut `−2,0e-12 + 126,655185 J`, reliant l'écart énergétique au même `δu`. L'identité de travail de la solution numérique reste correcte (`1,48e-16`): elle vérifie l'équilibre pour la charge erronée.

Le moment d'imbalance absolu vaut `8,533e-9 N·m`. Le code de l'audit divise par `max(||M_ext||,||M_reaction||,1 N·m)`, ici `1 N·m` car les moments résultants sont proches de zéro. Le ratio est donc numériquement `8,533e-9`; une échelle descriptive force×1 m donnerait `3,019e-16`. Les moments des cinq faces et leurs résultantes coïncident avec l'oracle par symétrie. L'ordre de grandeur de l'imbalance absolue est compatible avec l'arrondi sur des contributions de plusieurs MN·m, sans démontrer la séquence exacte des arrondis. L'origine et la normalisation peuvent affecter un ratio de moment proche de zéro. Le seuil historique `1e-12` n'est ni modifié ni déclaré PASS; cette assertion n'a pas été atteinte après l'échec de déplacement.

## Correction et limites

Le correctif prospectif emploie la règle `±√(3/5),0`, poids `5/9,8/9,5/9` pour QUAD8; QUAD4 conserve `±1/√3` et poids 1. Les faces triangulaires restent sur leur branche existante. Cela concerne les charges de traction, pression et repère local passant par la face à huit nœuds. Les tests de moments polynomiaux et d'intégrales QUAD8 sont purement mathématiques. Les tests d'intégration de face et de pression préparés restent `PREPARED_NOT_AUTHORIZED`, non exécutés. Aucun calcul R2 ne peut être déduit de ce contrôle analytique.
