# Audit théorique de HEX8 et HEX8-SRI

## Cinématique et constitutive

Sur `Ω̂=[−1,1]³`, les huit fonctions trilinéaires HEX8 interpolent `u_e`. Les coordonnées physiques sont `x(ξ)=ΣₐNₐ(ξ)Xₐ`; le Jacobien implémenté est `J=(∂N/∂ξ)ᵀX`, et `dV=det(J)dξdηdζ`. Les gradients physiques utilisent `J⁻ᵀ`. La matrice `B` produit le vecteur Voigt ingénieur `(εxx,εyy,εzz,γxy,γyz,γzx)`.

Pour l’élasticité isotrope linéaire, `μ=E/[2(1+ν)]`, `λ=Eν/[(1+ν)(1−2ν)]`, et `κ=λ+2μ/3=E/[3(1−2ν)]`. Exactement,

```text
W(ε) = μ εdev:εdev + κ/2 (tr ε)²
εdev = ε − (tr ε / 3) I
Cvol = κ m mᵀ,  m = (1,1,1,0,0,0)ᵀ
Cdev = C − Cvol
```

avec la convention de cisaillement ingénieur du code.

## Intégration et trois opérateurs

La règle Gauss-Legendre 2 points en 1D emploie `ξ=±1/√3`, poids `1`. Son produit tensoriel donne huit points de poids `1`, donc somme des poids `8`. La règle centrale sur le cube de référence a le poids produit `2·2·2=8`.

```text
KHEX8 = Σ(q=1..8) det(Jq) Bqᵀ C Bq
      = Kdev,2x2x2 + Kvol,2x2x2
Kdev,SRI = Σ(q=1..8) det(Jq) Bqᵀ Cdev Bq
Kvol,SRI = 8 det(J0) B0ᵀ Cvol B0
KSRI = Kdev,SRI + Kvol,SRI
```

La version historique calcule `Kvol` sans `8`. Dans `hex8_sri.py`, le correctif applique explicitement `volumetric_integration_weight=8.0` dans `volumetric_stiffness()`. L’audit de source confirme qu’aucun autre facteur ne compense son absence historique : les poids de `Hex8Element.integration_data()` valent 1; `J` transforme mesure et gradients; `B` transforme les gradients; `Cvol` porte les modules; `stiffness()` additionne les deux matrices. Le facteur 8 n’est donc ni implicite dans `det(J)`, ni dans `B`, ni dans le split constitutif.

Le partage est visible dans [`hex8_sri.py`](../../../src/solveur/elements/solid/hex8_sri.py); la règle complète est dans [`hex8.py`](../../../src/solveur/elements/solid/hex8.py). Le terme historique des six calculs est une reproduction figée locale, sans changement de source corrigée.

## Démonstration analytique du facteur 8

Sur le cube physique `[0,1]³`, l’application affine `x=(ξ+1)/2` donne `det(J)=1/8`. Pour `u=x`, `ε=I`, `tr ε=3`, `V=1`; la référence exacte vaut

```text
Uvol,exact = ∫V κ/2 (tr ε)² dV = 9κ/2.
```

Le point central avec son poids donne `8·(1/8)·κ/2·9=9κ/2`. Sans le poids, il donne `1·(1/8)·κ/2·9=9κ/16`, soit exactement `Uhistorique/Uexact=1/8`. Avec `E=1000 Pa`, `ν=.3`, `κ=833⅓ Pa`, les énergies sont respectivement `468.75 J` et `3750 J`, retrouvées par le test rouge/vert archivé. Le champ trace nulle `u=(x,−y,0)` a une énergie entièrement déviatorique et reste inchangé.

Cette preuve est exacte pour cette géométrie affine et ce champ constant. Elle ne prouve pas qu’un point unique intègre exactement chaque intégrande non constant d’un HEX8 distordu.

## Mesures locales archivées de `Kdev`, `Kvol`, `Ktotal`

Normes de Frobenius pour le cube unité, `E=10⁶ Pa`, tirées de `operator_comparison_results.json` (pièce indexée avec son script).

| `ν` | `κ/μ` | `||Kvol,hist||F` | `||Kvol,corr||F` | `||Kvol,HEX8||F` | `||Kdev||F` | `||Ktotal,hist||F` | `||Ktotal,corr||F` | `||Ktotal,HEX8||F` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0,3 | 2,1667 | 1,5625e5 | 1,2500e6 | 1,34179e6 | 9,86924e5 | 9,99216e5 | 1,59264e6 | 1,72403e6 |
| 0,4999 | 4 999,67 | 3,12500e8 | 2,50000e9 | 2,68359e9 | 8,55391e5 | 3,12501e8 | 2,50000e9 | 2,68365e9 |

Sur les matrices float64 contrôlées, `Kvol,corr=8Kvol,hist`, `ΔKdev=0` et `||ΔKtotal||F=||ΔKvol||F`. La variation relative de norme de `Ktotal` entre corrigé et historique vaut 109,46 % à `ν=.3` et environ 700 % à `.4999`. Le corrigé reste distinct de HEX8 complet : `||Ktotal,corr−Ktotal,HEX8||F/||Ktotal,HEX8||F=28,29 %` et `36,35 %`.

## Symétrie, rigidité et modes

Les contributions `BᵀCB detJw` sont symétriques en arithmétique exacte pour `C=Cᵀ`; le code symétrise numériquement les matrices locales. Elles sont semi-définies positives pour `E>0`, `−1<ν<0.5`, `detJ>0`, mais la coercivité stricte modulo les six mouvements rigides n’est pas garantie pour toute distorsion. Aucun hourglass control n’est ajouté; le déviateur conserve l’intégration complète.

Un mouvement rigide infinitésimal a `ε=0`; ses forces internes sont nulles dans ce modèle. Une rotation finie relève d’une cinématique non linéaire et n’est pas couverte. L’étude locale archivée rapporte six modes rigides et pas de mode nul supplémentaire au seuil choisi pour des cubes affines; cela ne constitue pas une étude de modes sur maillages distordus. Aucun eigensolve nouveau n’a été lancé dans cette mission.

Le code vérifie les Jacobiennes aux huit points de Gauss et la campagne enregistre aussi le centre. Une positivité sur ces échantillons ne certifie pas `detJ>0` en tout point d’un élément distordu; un audit futur doit ajouter une borne géométrique/certificat ou classer le cas comme non certifié.

## Géométrie non affine et exactitude

Sur un élément affine, `J` et `detJ` sont constants; pour un champ de déplacement affine, `B u` est constant. Le poids central restaure alors exactement l’intégrale volumique de ce champ. Pour un mapping non affine, `J(ξ)`, `detJ(ξ)` et les gradients physiques varient. Le point unique pondéré n’intègre alors pas nécessairement `BᵀCvolB detJ` exactement. La correction répare le poids de mesure de la règle, pas son degré d’exactitude générale.

## Limite quasi incompressible et conditionnement

```text
κ/μ = 2(1+ν) / [3(1−2ν)] → ∞ quand ν → 0,5−.
```

Le bloc volumique croît avec `κ`, alors que le déviatorique reste à l’échelle de `μ`. L’HEX8 complet peut devenir trop rigide si son espace discret ne représente pas les contraintes quasi incompressibles (verrouillage). Le SRI réduit les contraintes volumétriques échantillonnées, mais peut perdre en stabilité ou ouvrir des mécanismes selon la géométrie. Les six cas ne justifient aucune amélioration universelle.

`Cdev` est calculé par soustraction `C−Cvol`, alors que sa représentation directe est `2μPdev`. Le rapport de comparaison antérieur entre ces deux expressions augmente d’environ `1,7e−16` à `ν=.3`, `4,3e−13` à `.4999`, et `3,5e−12` à `.49999`; la perte de chiffres par annulation doit être quantifiée avant de pousser `ν` plus près de 0,5.

## Références techniques

- [Sandia Sierra/SD Theory Manual, §5.3, selective integration](https://www.sandia.gov/app/uploads/sites/315/2025/07/SD_Theory_5_18.pdf).
- [Sandia Sierra/SM User Manual, formulation des éléments](https://www.sandia.gov/files/sierra/SM_Users_5_30/user_manual/elements/sections.html).
- T. J. R. Hughes, “Generalization of selective integration procedures to anisotropic and nonlinear media,” *International Journal for Numerical Methods in Engineering* (1980), [doi:10.1002/nme.1620150914](https://doi.org/10.1002/nme.1620150914).
- T. Belytschko and T. Bindeman, “Assumed strain stabilization of the eight node hexahedral element,” *Computer Methods in Applied Mechanics and Engineering* (1993), [doi:10.1016/0045-7825(93)90124-G](https://doi.org/10.1016/0045-7825(93)90124-G).

Ces références contextualisent les familles SRI et la stabilité HEX8; elles ne valident pas l’implémentation QF Solver.
