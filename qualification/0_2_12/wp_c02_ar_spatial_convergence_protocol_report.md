# WP-C02-AR — Protocole de convergence spatiale du contact partiellement actif

## 1. Conclusion et limites de ce mandat

Ce rapport audite les mesures AQ déjà archivées, définit un protocole prospectif pour M4/M5 et expose le critère proposé pour la frontière active. **Aucun test scientifique, assemblage, solveur FEM, collecte ou RUN qualifiant n’a été lancé sous AR.** Les calculs M1–M3 ci-dessous sont les résultats historiques AQ. Les pentes apparentes sont des réductions hors ligne des nombres arrondis du rapport AQ, pas de nouvelles solutions numériques.

Les erreurs de déplacement, pression, énergie, résultante de contact et moment de contact diminuent entre M1 et M3. La frontière discrète, elle, se trouve à une cellule du front continu sur M2 et M3; le taux de discordance nodale pondéré par aire augmente entre ces niveaux. Cette évolution est compatible avec l’alignement du front biactif, la quantification des étiquettes par les nœuds et les maillages non emboîtés. Elle ne prouve pas un défaut de formulation ou de solveur. Les trois niveaux ne suffisent pas à déterminer l’ordre asymptotique.

M4 et M5 sont définis plus bas, sans changer le modèle. Leur exécution est **bloquée par le contrat de capacité du prototype gelé** : M4 et M5 demandent respectivement 675/1 188 DDL mécaniques et 45/66 contraintes, alors que le code refuse plus de 384 DDL ou 32 contraintes. Le présent mandat n’autorise pas à modifier ces limites ni à remplacer le solveur dense. Une nouvelle autorisation d’implémentation, de revue et de gel est nécessaire avant toute collecte ou exécution de ces niveaux.

Statut de campagne : `PROTOCOL_PREPARED_NOT_RUN`. La classification AQ du benchmark manufacturé reste strictement bornée à ce modèle; aucune promotion vers la convergence AH ni vers une qualification générale du contact n’est faite.

## 2. Identité et provenance

| Élément | Identité vérifiée / rapportée |
|---|---|
| Worktree AR | `<legacy-worktree>\.codex-worktrees\wp-c02-ar` |
| Branche AR | `codex/wp-c02-ar-spatial-convergence-20261023` |
| HEAD AR initial | `fe1586f59a83156f090a6976672f7c1645583df1` |
| Git tree AR initial | `808b498a96daaf4ffbcc0d5aa1a79d4cf3af38d2` |
| Dépôt / origin | `https://github.com/emptiesvoid-cloud/QF_solver.git` |
| État initial du worktree AR | propre |
| Rapport AQ | `qualification/0_2_12/wp_c02_aq_docker_fem_execution_report.md`, SHA-256 `ab1f9389c265174f20e1c8ef841513876cc1d635839e2bb2f30aadcf56104cab` |
| HEAD/tree d’exécution AQ | `847e93086b518e5d724f17ecb33e92d534212fcc` / `503348daa9dbfe882ea71b6bd2e3260282dacf6f` |
| Test AJ gelé | `tests/unit/test_wpc02_aj_partial_active_contact.py`, SHA-256 `7b14816b6ed6f6bed8aaa8e3bbde568251cf94332aa6c7b12765f389d6ae226e` |
| Manifeste AJ historique | SHA-256 `7bf71c3c0ce146f1bc01f5c6964d48f8bf642392d225514258d7f59829f606ca` |
| Manifeste AQ historique | SHA-256 `ba28108ece19c11277303167cc0197bb0f13a4b1ce8cc619a873075457b7b84e` |
| Source scientifique historique | SHA-256 de l’arbre `src/solveur`: `26d82115b3e4a1628cdaa62bcd91a17873ae30a09d5604383029e10602aed883` |
| Reçu COLLECT AQ | SHA-256 `47f7328f820ec376d01a076309ea59297be5944dbb12f73d90bcb3900be9b3a1` |
| Reçu RUN AQ | SHA-256 `172a70d86828018d36aafdd37cf9044fadf3b381a5bcb73549472d398281b499` |
| Image Docker AQ | `sha256:5502c6337d7eacbad450b40bf1f80837077d4a4fd3486e7041d9dec941dcb293` |
| Source contact inspectée dans AR | `src/solveur/contact/experimental_distributed_frozen.py`, SHA-256 `3f8ed76e57abe8cdf5ee2fc113eda667919aa649c0ba18f8d4902384a611844e` |
| Manifeste de conception AR | `qualification/0_2_12/wp_c02_ar_mesh_plan.json`, SHA-256 `fa3806c842acefbe707499ffdec9f703bcedb5031962594df4c5293d0fbe6cfc` |

Les rapports et preuves AQ/AJ/AH/AI/AG ont été lus sans les modifier. Aucun artefact d’exécution historique n’a été réécrit.

## 3. Modèle mécanique conservé

Le benchmark est celui du test AJ, sans changement : bloc élastique isotrope TET4 de domaine physique `[0,1] × [0,1] × [0.001,1.001] m`, `E=3 MPa`, `ν=0`, déplacement prescrit nul sur la face supérieure, face maître rigide et plane figée à `z=0`, normale de contact `+z`, contact sans frottement et une contrainte normale par nœud inférieur. Les charges volumiques et tractions non-contact restent celles obtenues à partir du même champ manufacturé.

Convention gelée : `g = 0.001 m + u_z`; `g≥0`, `λ≥0`, `gλ=0`; `λ` est la magnitude de la réaction normale compressive et la force exercée sur le solide est `+λ e_z`. La frontière analytique vaut `x=a=0.5 m`. La pression exacte est `p(x)=4000·max(0,a−x)^2 Pa`; la zone active est `0≤x<a`, la zone ouverte `a<x≤1`, et la ligne `x=a` est biactive dans le problème continu.

L’ordre Voigt reste `[εxx, εyy, εzz, γxy, γyz, γxz]`, avec cisaillements d’ingénieur et `μ` sur les diagonales de cisaillement. L’énergie de déformation est `U=½∫ εᵀDε dV`; la norme d’erreur énergétique est `sqrt(∫(ε_h−ε_exact)ᵀD(ε_h−ε_exact)dV)` en `sqrt(J)`.

Le maillage utilise la même subdivision locale en six TET4 par cellule que le test AJ, la même géométrie et les mêmes charges. La ligne `x=0.5 m` est une limite de cellule pour tous les niveaux proposés (tous `nx` sont pairs); cela doit être conservé comme caractéristique du benchmark et signalé comme source d’aliasing nodal, pas présenté comme un échantillonnage de frontière générique.

## 4. Résultats AQ M1–M3 audités

### 4.1 Maillage et erreurs de champ

Les erreurs de champ sont mesurées contre la solution analytique continue sur chaque maillage par la quadrature AJ; elles ne comparent pas les vecteurs nodaux de tailles différentes.

| Niveau `(nx,ny,nz)` | Nœuds / TET4 | DDL totaux / libres | Contraintes de contact | `hmax / hx` (m) | Erreur relative `u` L2 | Erreur relative pression L2 | Erreur relative énergie | `U_h` / `|U_h−U_exact|` (J) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 `(2,1,1)` | 12 / 12 | 36 / 18 | 6 | 1.5 / 0.5 | 0.0115305 | 0.463891 | 0.0374964 | 1.47758032 / 0.00852794 |
| M2 `(4,2,2)` | 45 / 96 | 135 / 90 | 15 | 0.75 / 0.25 | 0.00585335 | 0.259359 | 0.0234189 | 1.48466497 / 0.00144330 |
| M3 `(6,3,3)` | 112 / 324 | 336 / 252 | 28 | 0.5 / 0.166667 | 0.00341925 | 0.156072 | 0.0166456 | 1.48544229 / 0.000665972 |

`U_exact=1.486108265595 J`. Les erreurs absolues de norme énergétique sont `0.0646443`, `0.0403744`, `0.0286972 sqrt(J)`. La différence `½uᵀKu` contre l’intégrale discrète TET4 est respectivement `6.44e−15`, `1.82e−14`, `1.55e−15 J`.

### 4.2 Contact, équilibre et KKT

| Niveau | Force contact / erreur relative | Erreur de moment / erreur relative | Équilibre force / moment relatif | Pénétration / gap ouvert min (m) | λ actif min (N) | Stationnarité KKT inf (N) | Complémentarité inf (N·m) |
|---|---:|---:|---:|---:|---:|---:|---:|
| M1 | 173.105166 N / 0.0386310 | 7.86139 N·m / 0.0471683 | `6.75e−15 / 1.00e−14` | `0 / 2.25674e−5` | 17.1790 | `1.39e−12` | 0 à la précision enregistrée |
| M2 | 167.294915 N / 0.00376949 | 2.46729 N·m / 0.0148038 | `7.04e−16 / 3.31e−15` | `0 / 5.69367e−7` | 0.641219 | `8.31e−13` | 0 à la précision enregistrée |
| M3 | 166.920874 N / 0.00152524 | 1.24025 N·m / 0.00744150 | `2.16e−15 / 1.04e−14` | `0 / 2.46413e−7` | 0.243522 | `1.46e−12` | 0 à la précision enregistrée |

La référence continue est `F_contact=166.6666666666666 N`, `M_contact=[83.3333333333333, −20.8333333333333, 0] N·m`. L’oracle discret AJ utilise toutes les contraintes du bord inférieur et une résolution duale NNLS après assemblage indépendant de la matrice TET4. Les écarts production/oracle maximaux sont `2.88e−20`, `4.34e−19`, `6.51e−19 m` pour `u` et `4.26e−14`, `3.48e−13`, `1.19e−12 N` pour `λ`. Les gaps primaux, multiplicateurs duaux, complémentarité et bilans ont satisfait les seuils historiques reportés. Cela vérifie l’équilibre discret pour ces niveaux; ce n’est pas une corrélation externe.

Le rapport consolidé AQ ne publie pas les valeurs exactes des erreurs de résultante de réaction supérieure comparées à l’intégrale analytique : ces valeurs restent `NOT_RECORDED` dans l’artefact actuellement audité. Il publie les résidus globaux normalisés et les résultats du KKT. La prochaine campagne doit conserver séparément la réaction analytique de traction et la réaction discrète reconstruite.

### 4.3 Frontière active

Le rapport AQ définit le front discret comme, pour chaque rangée `y`, le plus grand `x` dont `λ` dépasse la tolérance de force gelée. Les points ouverts satisfont `g` au-dessus de la tolérance de gap; les points biactifs sont consignés séparément. La mesure est nodale et non une frontière interpolée.

| Niveau | Lignes `y` | Front max erreur physique | Front max erreur `/hx` | Faux positifs / faux négatifs | Fraction nodale tributaire discordante |
|---|---:|---:|---:|---:|---:|
| M1 | 2 | 0 m | 0 | 0 / 0 | 0 |
| M2 | 3 | 0.25 m | 1 | 1 / 0 | 0.0625 |
| M3 | 4 | 0.166667 m | 1 | 3 / 0 | 0.138889 |

Les faux positifs M2/M3 sont à un `hx` du front; aucun faux négatif éloigné n’a été observé. M1 tombe exactement sur le front et obtient une erreur nulle par alignement/biactivité; il ne constitue donc pas une référence fiable de taux de convergence. La fraction d’aire tributaire discrète est une mesure nodale lumpée, non une mesure de Hausdorff ni une intégrale exacte de l’aire active. Sa hausse ne signifie pas que le front physique s’éloigne : l’erreur physique M2→M3 diminue alors que le déplacement d’un seul nœud actif représente une fraction différente de la surface selon le maillage.

### 4.4 Pentes apparentes hors ligne

Formule utilisée uniquement pour les réductions des valeurs arrondies AQ : `p_ij=ln(E_i/E_j)/ln(h_i/h_j)`. Les champs globaux utilisent `hmax`; le front utilise `hx`. Ces valeurs décrivent des pentes entre deux points, pas un ordre asymptotique.

| Observable d’erreur | `p12` | `p23` | `p13` | Interprétation |
|---|---:|---:|---:|---|
| Déplacement L2 relatif | 0.978 | 1.326 | 1.106 | décroît sur M1–M3 |
| Pression L2 relative | 0.839 | 1.253 | 0.992 | décroît sur M1–M3 |
| Norme énergétique `sqrt(J)` | 0.679 | 0.842 | 0.739 | décroît sur M1–M3 |
| Erreur absolue d’énergie totale (J) | 2.563 | 1.908 | 2.321 | décroît; pente issue de valeurs arrondies |
| Erreur relative de résultante de contact | 3.357 | 2.231 | 2.942 | décroît sur M1–M3 |
| Erreur relative de moment de contact | 1.672 | 1.696 | 1.681 | décroît sur M1–M3 |
| Front physique | non défini (erreur M1 nulle par alignement) | ≈1.000 | non défini | M2→M3 seulement; pas d’ordre démontré |

La p1 de M1→M2 et p2 de M2→M3 diffèrent pour plusieurs observables; les niveaux sont non emboîtés et les ratios de `hmax` varient (`2`, `1.5`). Ne pas extrapoler ces valeurs comme ordre théorique ni comme erreur de solveur.

## 5. Explication de la non-monotonie du front

La frontière analytique est biactive : `g=0` et `λ=0` à `x=0.5 m`. Le test classe l’état avec tolérances absolues sur `g` et `λ`, tandis que le front nodal dépend de la position discrète des nœuds et de l’ordre actif/inactif retenu au voisinage de cette ligne. M1 place des nœuds exactement sur la frontière et obtient un front nodal nul; M2 et M3 présentent des faux positifs à une cellule du côté ouvert. La pression exacte s’annule quadratiquement près du front; une petite valeur discrète de multiplicateur peut ainsi déplacer le label sans représenter une erreur de même amplitude physique que le déplacement du front.

Les maillages ne sont emboîtés qu’au premier raffinement M1→M2; les rapports de discrétisation ultérieurs ne sont pas entiers. Les inconnues nodales ne doivent donc pas être comparées par index. La comparaison de champs contre la référence analytique intégrée sur chaque tétraèdre demeure comparable, mais l’évolution des labels actifs requiert une métrique géométrique en mètres.

| Hypothèse | Éléments favorables | Éléments contraires / limites | Conclusion AR |
|---|---|---|---|
| Défaut de formulation ou d’assemblage | Le front nodal change et les labels diffèrent de l’analytique. | Résidus KKT `~1e−12 N`, non-pénétration, complémentarité, bilans et accord avec QP complet sont bons; erreurs de champs/résultantes diminuent. | Non établi; à réexaminer seulement si M4/M5 montrent une anomalie hors bande ou un résidu. |
| Oracle analytique faux | AH avait un oracle de labels inadéquat et l’ordre `yz/xz` erroné dans l’oracle d’énergie; AJ a corrigé ces deux défauts. | Les références AJ sont dérivées de champs manufacturés; la corrélation reste algorithmique et non externe. | Les anciens oracles AH ne sont pas recevables; AQ a exécuté l’oracle AJ corrigé. Aucune preuve d’un nouveau défaut d’oracle dans les artefacts AQ. |
| Classification sensible à la frontière biactive | M1 est exactement aligné; faux positifs seulement à un `hx`; pression s’annule quadratiquement. | Les valeurs de `λ` et `g` au front pour chaque point ne sont pas toutes listées dans le résumé AQ. | Explication plausible, compatible avec données; non causalement isolée. Il faut publier les traces par rangée et les valeurs biactives M4/M5. |
| Projection ou post-traitement | Pression nodale reconstruite par `λ/aire tributaire`; cela peut influencer les labels/aire. | Face maître plane figée; les écarts de front sont localisés à la limite et la solution KKT complète concorde avec la production. | Pas d’indice actuel d’un défaut de projection; le post-traitement d’aire est une métrique secondaire, non un oracle géométrique. |
| Trois niveaux insuffisants | Un seul intervalle M2→M3 donne `p_front≈1`; aucune asymptotique. | Les métriques de champs/résultantes s’améliorent déjà sur trois niveaux. | Limitation confirmée; M4/M5 nécessaires pour une tendance de front, sans garantir l’asymptotique. |
| Maillages non emboîtés | Ils modifient les points d’échantillonnage et le nombre de rangées. | Le front reste aligné à une limite de cellule; les métriques de champs sont comparées à la même solution continue. | Contributeur plausible aux oscillations de labels, pas cause unique démontrée. |

## 6. Maillages proposés M4 et M5

La famille garde le modèle de test : `(nx,ny,nz)=(2k,k,k)`, six tétraèdres par cellule, même diagonale locale, mêmes coordonnées physiques et même ligne front `x=0.5`. `h_x=1/nx`; `h_max=3/nx` pour le plus long segment de la subdivision cubique adoptée. Comptages analytiques issus des formules de grille : nœuds `(nx+1)(ny+1)(nz+1)`, TET4 `6nx·ny·nz`, contact `(nx+1)(ny+1)`, DDL mécaniques `3N`, DDL libres `3N−3(nx+1)(ny+1)` (trois translations prescrites sur chaque nœud supérieur).

| Niveau | `(nx,ny,nz)` | Nœuds | TET4 | DDL totaux / libres | Lignes contact | KKT complet libre+contact | Actifs stricts / ouverts stricts / biactifs analytiques | `hx / hmax` (m) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| M1 historique | `(2,1,1)` | 12 | 12 | 36 / 18 | 6 | 24 | 2 / 2 / 2 | 0.5 / 1.5 |
| M2 historique | `(4,2,2)` | 45 | 96 | 135 / 90 | 15 | 105 | 6 / 6 / 3 | 0.25 / 0.75 |
| M3 historique | `(6,3,3)` | 112 | 324 | 336 / 252 | 28 | 280 | 12 / 12 / 4 | 0.166667 / 0.5 |
| M4 préparé | `(8,4,4)` | 225 | 768 | 675 / 540 | 45 | 585 | 20 / 20 / 5 | 0.125 / 0.375 |
| M5 préparé | `(10,5,5)` | 396 | 1 500 | 1 188 / 990 | 66 | 1 056 | 30 / 30 / 6 | 0.1 / 0.3 |

Toutes les charges, conditions limites, constantes matérielles, lois de contact, échelles et tolérances doivent être conservées. La ligne biactive reste sur un plan de cellule; M4/M5 ne testent donc pas l’alignement d’un front arbitraire. Le prochain travail doit présenter cette limite dans la portée du résultat.

### Blocage de capacité

`src/solveur/contact/experimental_distributed_frozen.py` fixe `MAX_DENSE_MECHANICAL_DOFS=384` et `MAX_CONTACT_CONSTRAINTS=32`; les validations de `DistributedTet4Case` et d’assemblage refusent les tailles supérieures. M4 dépasse les deux (`675`, `45`); M5 également (`1188`, `66`). Ces limites sont des refus scientifiques de portée et ne peuvent pas être contournées par le générateur de maillage.

Le cap dense implique aussi que l’extension doit être revue comme changement d’identité scientifique, pas uniquement comme augmentation de mémoire. Avant M4/M5 il faut une autorisation de modification de capacité, une revue du conditionnement/algorithme KKT et une enveloppe ressource appropriée. Le manifeste AJ source-dérivé contient en outre un compte M1 `reference_free_dofs=24` alors que la prescription de tous les trois DDL des six nœuds supérieurs donne 18; le rapport AQ et le test rapportent 18. Le KKT complet avec les six lignes de contact a donc une dimension `18+6=24`, pas `24+6=30` comme le compte dérivé du manifeste historique. Cette incohérence P1 de métadonnées est corrigée dans le présent plan prospectif (18 DDL libres); l’ancien manifeste et les résultats archivés restent immuables.

## 7. Critères de convergence proposés avant exécution

Les critères ci-dessous séparent les assertions effectivement gelées AJ des critères supplémentaires proposés pour AR. Aucun nouveau seuil n’est déjà approuvé ni un résultat AQ. Le module AJ demeure le contrat normatif de son exécution historique; les nouveaux niveaux et critères exigent une nouvelle identité et un accord Owner.

### 7.1 Assertions AJ effectivement gelées

Dans AJ, les gates ci-dessous ont été appliquées à chacun de M1–M3; les critères coarse/fine utilisaient M1 comme coarse et M3 comme fine. Elles doivent rester inchangées pour toute répétition de cette suite.

| Assertion AJ | Seuil exact | Unité / portée |
|---|---:|---|
| Solution partiellement active et présence d’un ouvert | `0 < active_count < contact_rows`; `open_count > 0` | chaque maillage |
| Pénétration maximum | `maximum_penetration ≤ 1e−10` | m, production |
| Reconstruction du gap | `max|g_reported−(0.001+u_z)| ≤ 1e−10` | m, production |
| Complémentarité production | `||g⊙λ||∞ ≤ 1e−10` | N·m |
| Gap sur les nœuds déclarés actifs | `strict_active_max_gap ≤ 1e−10` | m, production |
| Multiplicateur sur les nœuds déclarés ouverts | `strict_open_max_lambda ≤ 1e−7` | N, production |
| Stationnarité production | `||K_ff u−f_f−Gᵀλ||∞ ≤ 1e−6` | N |
| Faisabilité primale indépendante | `min(g_QP) ≥ −1e−10` | m, QP complet |
| Faisabilité duale indépendante | `min(λ_QP) ≥ −1e−7` | N, QP complet |
| Complémentarité indépendante | `||g_QP⊙λ_QP||∞ ≤1e−10` | N·m, QP complet |
| Stationnarité indépendante | `||r_KKT,QP||∞ ≤1e−6` | N, QP complet |
| Accord production / QP en déplacement | `max|u−u_QP| ≤1e−9` | m |
| Accord production / QP en multiplicateur | `max|λ−λ_QP| ≤1e−6` | N |
| Bilan force production et QP | `≤1e−9` après échelle gelée | sans dimension |
| Bilan moment production et QP | `≤1e−9` après échelle gelée | sans dimension |
| Identité de travail production et QP | `≤1e−9` | J |
| Énergie matrice / quadrature FE | `≤1e−10` | J |
| Erreur L2 déplacement, coarse/fine | `E_u(M3)/E_u(M1)<0.9` | sans dimension |
| Erreur L2 pression, coarse/fine | `E_p(M3)/E_p(M1)<0.9` | sans dimension |
| Norme d’erreur énergétique | `E_U(M3)<E_U(M1)` | sqrt(J) |
| Erreurs de résultante force/moment de contact | valeurs finies exigées, sans tolérance d’erreur de discrétisation | diagnostics AQ |
| Front | métriques finies exigées, sans seuil d’acceptation AJ | diagnostic descriptif |

La même table, y compris les gates active/ouvert séparés, doit rester normative à chaque niveau AR. Les tolérances de gap et de multiplicateur sont distinctes : un faible `λ` ne remplace pas le gate de gap sur un actif, ni inversement. La QP indépendante conserve toutes les inégalités inférieures; aucun ensemble actif provenant de la solution continue ne peut lui être imposé.

### 7.2 Extensions prospectives AR nécessitant approbation Owner

| Proposition AR | Critère prospectif | Pourquoi / statut |
|---|---:|---|
| Étendre le ratio d’erreur déplacement coarse/fine | `E_u(M5)/E_u(M1)<0.9` | même valeur numérique AJ, nouvel index fine; nouveau critère AR |
| Étendre le ratio d’erreur pression coarse/fine | `E_p(M5)/E_p(M1)<0.9` | même valeur numérique AJ, nouvel index fine; nouveau critère AR |
| Étendre la décroissance énergétique coarse/fine | `E_U(M5)<E_U(M1)` | même inégalité AJ, nouvel index fine; nouveau critère AR |
| Front actif | Gates de §7.3 | nouvel indicateur géométrique et nouveau seuil AR |

Ne pas présenter ces extensions comme critères déjà satisfaits ou automatiquement gelés par AJ. Il n’est pas proposé d’exiger une décroissance stricte à chaque intervalle M1→M5 : les maillages ne sont pas emboîtés et la monotonie de l’erreur Galerkin ne s’applique pas directement à cette succession.

Les équations KKT doivent inclure les 45/66 contraintes de contact dans les références M4/M5; aucun ensemble actif ne doit être imposé par le front analytique. La QP discrète et la référence continue demeurent séparées. La comparaison de `u`/pression sur M1/M5 reste faite contre le même champ exact par quadrature, pas par indexation de nœuds non correspondants.

### 7.2 Critère prospectif de frontière active

Mesure conservatrice adaptée au front rectiligne de ce benchmark : pour chaque rangée `y`, garder l’estimateur AJ `x_h(y)=max{x_i: λ_i>1e−7 N}` et enregistrer aussi le premier `x` ouvert (`g_i>1e−10 m`), le couple de valeurs `g_i,λ_i` des points voisins, les points biactifs et l’intervalle de bracket. Comparer à `x*=0.5 m` en distance physique et `hx` normalisée. L’union des rangées forme la polyligne discrète; pour la ligne analytique de y complet, son erreur de Hausdorff en x est le maximum des erreurs par rangée.

Critères candidats, uniquement pour M2–M5 (M1 reste diagnostique, car son erreur nulle est un artefact d’alignement) :

1. Toutes les rangées doivent contenir des états actifs et ouverts et fournir un front/bracket interprétable; les lignes non encadrées sont un résultat incomplet, pas des lignes à exclure silencieusement.
2. `D_front,max/hx ≤1` à chaque niveau, où `D_front,max=max_y |x_h(y)−0.5|`. Cela signifie localisation à une cellule pour cette famille régulière; le plafond en mètres décroît avec `hx` (`0.25`, `1/6`, `0.125`, `0.1 m` aux M2–M5). C’est un seuil prospectif empirique lié à la résolution observée, pas une borne théorique générale.
3. Chaque faux positif (`λ` significatif du côté continu ouvert) ou faux négatif (`g` significatif du côté continu actif) doit se trouver à distance `≤hx` du front. Les points sur `x=0.5` sont biactifs analytiques et leurs étiquettes ne sont pas imposées; leurs `g` et `λ` sont néanmoins soumis aux tolérances KKT gelées.
4. Toute alternance active/ouvert hors de la bande d’une cellule, tout front multiple ou toute ligne sans voisinage ouvert/actif doit être rapporté et bloque la conclusion bornée jusqu’à explication.
5. La fraction d’aire active discordante est un diagnostic seulement; aucune monotonie n’est exigée, car l’estimateur par aires tributaires lumpées dépend de la grille.

La condition `D_front,max≤hx` à chaque niveau exige une erreur géométrique physique qui reste dans l’enveloppe de résolution. Elle ne prouve pas un ordre asymptotique et ne prétend pas une convergence de labels individuels. L’absence d’exigence de décroissance adjacente stricte est volontaire : les maillages M2–M5 sont non emboîtés et la monotonie discrète n’est pas un théorème. La frontière reste une métrique distincte des résidus KKT.

### 7.3 Indicateurs à rapporter sans seuil inventé

Pour chacun des cinq niveaux, publier : `E_u`, `E_p`, `E_U`, `U_h`, `|U_h−U_exact|`, pression nodale `λ/A_trib`, résultante et moment de contact contre l’intégrale analytique, réactions d’appui contre l’intégrale de traction supérieure, maximum/RMS du front physique et normalisé, largeur des brackets, faux positifs/négatifs, `||gλ||∞`, minimum de gap, minimum de λ, stationnarité, résidu NNLS et conditionnement du QP.

Les erreurs absolues de résultante, moment, énergie totale et support seront publiées en unités physiques. Les tests AQ n’imposent pas de tolérance d’erreur de discrétisation pour ces écarts continus : on ne leur invente pas de seuil. Les gates d’équilibre restent les tolérances normalisées gelées. Calculer les pentes apparentes par intervalles pour `hmax` (champs/énergie) ou `hx` (front) lorsque les deux erreurs sont positives; rapporter également les rapports, la non-monotonie et l’intervalle utilisé. Une pente ne sera dite asymptotique que si une étude ultérieure démontre un régime stable; cinq niveaux non emboîtés ne l’établissent pas à eux seuls.

## 8. Indépendance des références et limites

Les références analytiques — déplacement, pression, tractions, énergie et résultantes — dérivent du champ manufacturé et sont indépendantes des routines d’assemblage/contact de production. La référence discrète construit une matrice TET4 et un système dual QP séparément, et traite toutes les inégalités nodales sans active set continuum imposé. Elle partage néanmoins les mêmes géométries, matériau et chargements manufacturés que le test. C’est une indépendance algorithmique bornée, pas un autre solveur ou un autre modèle de charge.

Les réactions d’appui analytiques sont intégrées depuis la traction de surface du champ manufacturé; la reconstruction discrète depuis le résidu utilise la matrice indépendante. Les deux voies doivent être affichées séparément. Un équilibre global proche de zéro seul ne valide pas l’oracle si la réaction provient du même résidu; le résultat doit aussi comparer la réaction reconstruite à la référence de traction analytique, tout en conservant le contrôle KKT.

AG conserve son résultat historique de convergence sur un benchmark entièrement actif, sans frontière mobile; il s’agit d’une preuve de méthode distincte, pas d’une validation de front partiellement actif. AF reste `PASS_BOUNDED`. AH demeure `2 PASS / 1 FAIL`; AQ exécuté sur le gel AJ corrigé est `3 PASS`, sans réécriture de l’historique AH.

## 9. Revue indépendante

Revue en lecture seule par `<reviewer-workspace>`; aucune collecte, test, assemblage ni résolution n’a été effectuée par le reviewer. La revue a identifié :

* **P1 — métadonnée du manifeste AJ incohérente sur les DDL libres M1** : 24 inscrit contre 18 dans le test et AQ. `wp_c02_ar_mesh_plan.json` utilise 18 pour les futures préparations. Le manifeste historique reste immuable; tout nouveau manifeste doit porter 18 et les dimensions correspondantes.
* **P1 — les niveaux M4/M5 dépassent les caps source** 384 DDL / 32 lignes de contact. Il faut une autorisation explicite et un nouveau gel/contrat de ressources avant leur RUN.
* **P1 initial — gate de décroissance à chaque niveau** : retirée de la proposition après revue; elle est marquée **résolue/supersédée**. AR ne demande pas la monotonie adjacente pour des maillages non emboîtés.
* **P1 initial — provenance des critères fine/coarse et assertions AJ omises** : corrigée dans les §§7.1–7.2 et dans le manifeste de conception. Les gates AJ sur M1/M3 sont séparées des extensions proposées M1/M5; les assertions de gap sur actifs et de multiplicateur sur ouverts sont énumérées explicitement.
* **P2 — la borne d’une cellule pour le front est interprétable, mais empirique**, non un contrat existant ni un théorème. Elle doit être explicitement acceptée par l’Owner avant exécution; l’alignement de M1 reste exclu du trend.
* **P2 — AG ne couvre pas le front mobile.**

La revue est une revue indépendante du protocole/source. Elle ne constitue pas un calcul numérique indépendant. Aucun P0 n’a été signalé. Le problème de monotonie adjacente et les omissions documentaires sont résolus dans cette version; le dépassement réel des caps reste le P1 qui bloque un gel de RUN qualifiant. La métadonnée M1 du manifeste AJ historique est corrigée pour les futurs artefacts seulement.

## 10. Préparation d’exécution et conditions d’un futur `PASS_BOUNDED`

Le fichier `wp_c02_ar_mesh_plan.json` est un artefact de conception et ne constitue pas un manifeste exécutable, une allowlist ou une autorisation. Il corrige le compte M1 libre dans la prospective sans altérer le manifeste AJ historique et documente les cinq niveaux, le seuil candidat de front et les gates AJ.

Avant toute future campagne, il faut :

1. Obtenir l’approbation Owner des critères prospectifs, en particulier de la borne de front `≤1 hx` et du maintien des critères coarse/fine AJ sur M1/M5.
2. Obtenir l’autorisation d’augmenter/reconcevoir le prototype pour 1 188 DDL et 66 contraintes. Le changement devra conserver les refus géométriques/KKT et être évalué sous le même algorithme ou un algorithme distinct validé; ne pas simplement relever deux constantes.
3. Revoir l’enveloppe de calcul, les limites mémoire/CPU/temps et le conditionnement sur le nouveau dimensionnement. Aucun élargissement automatique du profil Docker/Windows.
4. Corriger le prochain manifeste pour `M1 free DOF=18`, puis geler HEAD/tree, code, tests, manifeste, runner, image, liste de nœuds et reçus. Les preuves AQ/AJ/AH/AI/AG restent immuables.
5. Effectuer une revue indépendante de ce nouveau gel et du graphe de dépendances. COLLECT et RUN demanderont les GO distincts prescrits par le manifeste et l’Owner. Aucun commit/changement entre un COLLECT accepté et son RUN lié.
6. Exécuter une unique campagne autorisée. Chaque maillage doit écrire ses diagnostics avant assertion afin qu’un échec M4/M5 ne supprime pas les niveaux précédents.

Un `PASS_BOUNDED` pour ce benchmark ne sera recommandable que si tous les tests exécutés passent, chaque gate KKT/équilibre AJ est respecté sur M1–M5, les ratios coarse/fine et l’erreur énergétique restent dans les gates gelées, le front est bracketé sur toutes les rangées et respecte l’enveloppe `≤1 hx` sur M2–M5, aucune erreur d’état n’existe hors de la bande d’une cellule, et la revue indépendante ne laisse aucun finding P0/P1. Une non-monotonie locale des erreurs intégrées n’est pas un échec automatique; les rapports, pentes et explications doivent être présentés, sans revendiquer l’asymptotique.

## 11. Classifications conservées

| Élément | État après AR |
|---|---|
| Exécution AQ sur M1–M3 | `3 PASS` historique, non rerun |
| Contact partiellement actif manufacturé | preuve AQ bornée au cas/test exact; aucun élargissement automatique |
| Convergence active-front AH/AQ | `NOT_ACQUIRED` avant M4/M5; reste `NOT_ACQUIRED` |
| M4/M5 | géométrie et comptages préparés; non assemblés, non collectés, non exécutés |
| Contact partiellement actif AQ | `VERIFIED_BOUNDED` pour le benchmark manufacturé frozen-face exécuté exact; aucun élargissement de portée |
| WP-C02-AG | `VERIFIED_BOUNDED` pour benchmark nonaffine entièrement actif uniquement |
| WP-C02-AH spatial | `NOT_ACQUIRED`; le front actif reste la métrique à vérifier avec M4/M5 |
| WP-C02-AF | `PASS_BOUNDED` historique, inchangé |
| Qualification générale du contact | `NOT_ACQUIRED` |
| WP-C01 | `CLOSED_NEGATIVE`, inchangé |
| Intégration autoritative | `PENDING` |
| Publication | `NOT_AUTHORIZED` |

## 12. Artefacts et contrôles AR

| Fichier | Rôle |
|---|---|
| `qualification/0_2_12/wp_c02_ar_spatial_convergence_protocol_report.md` | audit, seuils candidats, risques et conditions de décision |
| `qualification/0_2_12/wp_c02_ar_mesh_plan.json` | inventaire source-indépendant de M1–M5; conception uniquement |

Aucun fichier de production, test scientifique, seuil AJ, manifeste historique ou preuve AQ n’a été modifié. Aucun calcul qualifiant n’a été exécuté.

