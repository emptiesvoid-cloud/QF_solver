# WP-E01-J2-GLOBAL — preuve de faisabilité et périmètre restant

Date : 2026-10-24  
Branche inspectée : `codex/v0.2.12-integration`  
HEAD : `00a9b133d0f9768f0d7ab5ff11a7858d51814d14`  
Tree : `fd5638dd783203c4d62bdff024c0e50c241cbed5`

## Verdict

**`J2_GLOBAL_PROOF_INCONCLUSIVE`**

La dérivation locale du retour radial et la linéarisation discrète total-Lagrangienne sont établissables analytiquement sur une branche lisse, à histoire entrante fixée. Elles ne suffisent pas à certifier que l’implémentation globale réalise cette dérivée sur les DDL libres. La route corotationnelle emploie une différence centrée à pas fini pour construire `K`; aucune borne d’erreur acceptée ne permet de transformer cette approximation en certificat de dérivée. Les identités globales, les bornes d’erreur et les critères de décision restent non acquis.

Statuts préservés :

```text
C03_BRANCH_STABILITY=CERTIFIED_BOUNDED
GLOBAL_J2_TANGENT_QUALIFICATION=NOT_ACQUIRED
CRITERIA_GLOBAL=NOT_APPROVED
BA_GLOBAL_VERDICT=FAIL
WP_E01_STATUS=OPEN_WITH_BOUNDED_CERTIFICATES
```

## 1. Cartographie des chemins exécutés

| Chemin | Force `F` | Tangente `K` | Portée de la dérivation |
|---|---|---|---|
| J2 constitutif | `VonMisesElastoplasticMaterial.stress_tangent_state` calcule le trial puis le retour radial dans [`solid.py`](../../src/solveur/materials/solid.py:137). | Branche élastique : `C`; branche plastique : `_algorithmic_tangent` dans le même fichier, lignes 216–247. | Dérivée locale à histoire fixée; séparément lisse sur chaque branche. |
| TET4/HEX8 total-Lagrangien | [`total_lagrangian_j2.py`](../../src/solveur/elements/solid/total_lagrangian_j2.py:99) calcule `F=I+uᵀ∇N`, `E=(FᵀF−I)/2`, `S`, `P=FS`, puis intègre `P∇N` sur la géométrie de référence. | `_tangent` assemble le terme matériel et le terme géométrique (lignes 187–210); TET4 utilise 1 point et HEX8 8 points (lignes 213–241). | La formule est la dérivée exacte de la force discrète en arithmétique réelle si le tangent constitutif fourni est exact et si la branche ne change pas. Le code symétrise ensuite la matrice. |
| Corotationnel legacy/corrected | [`corotational_j2.py`](../../src/solveur/elements/solid/corotational_j2.py:741) calcule la force à partir de la décomposition polaire, de la déformation locale, du transport d’état et de la transformation de contrainte. | Les deux routes forment `K` par différences centrées; la route legacy symétrise le résultat (lignes 997–1012), la route corrected renvoie la matrice brute et non symétrisée (lignes 945–995). | `K` est un estimateur à pas fini, non une identité exacte avec `D F`. Le corrected détecte les changements de branche, mais son diagnostic indique que la qualité de dérivée n’est pas estimée par appel (lignes 966–990). |
| Assemblage global | [`nonlinear.py`](../../../../src/solveur/core/assembly/nonlinear.py:277) mappe connectivité, coordonnées et DOFs locaux, appelle l’élément et disperse les forces (lignes 308–389). | Le même chemin disperse la matrice élémentaire en triplets et CSR (lignes 358–404). Le solveur réduit aux indices libres dans [`solver.py`](../../../../src/solveur/core/nonlinear/solver.py:65). | La réduction mathématique est `F_f=Q_fᵀF`, `K_ff=Q_fᵀKQ_f`. Le code doit encore être comparé à un oracle global indépendant sur les actions de la base libre. |

Les sources sélectionnent TL ou corotationnel à partir de la cinématique dans `core/assembly/nonlinear.py`. Les preuves TL ci-dessous ne se transfèrent pas à la formulation corotationnelle.

## 2. Démonstrations analytiques établies par lecture des sources

À histoire entrante fixe `(εᵖ_n, α_n)`, le code constitutif définit

\[
\sigma_{tr}=C:(\varepsilon-\varepsilon^p_n),\quad
s_{tr}=\operatorname{dev}\sigma_{tr},\quad
q_{tr}=\sqrt{\tfrac32s_{tr}:s_{tr}},\quad
f=q_{tr}-(\sigma_{y0}+H\alpha_n).
\]

Si `f≤0`, `σ=σtr` et `dσ=C:dε`. Si `f>0`, avec `D=3μ+H`,

\[
\Delta\gamma=f/D,\quad q=q_{tr}-3\mu\Delta\gamma,
\quad \sigma=\operatorname{tr}(\sigma_{tr})I/3+(q/q_{tr})s_{tr}.
\]

Pour une variation `dε`, poser `dσtr=C:dε`, `ds=dev(dσtr)`, `dq=(3/2)(s_tr:ds)/qtr`, `a=q/qtr`. Alors

\[
d\sigma=\operatorname{tr}(d\sigma_{tr})I/3+a\,ds
-3\mu\left[\frac{1}{q_{tr}D}-\frac{\Delta\gamma}{q_{tr}^2}\right]dq\,s_{tr},
\]

ce qui correspond à la construction de `_algorithmic_tangent`. `H=0` donne `q=σy0`, `a=σy0/qtr`; `H>0` donne `dq/dqtr=H/(3μ+H)`. Cette dérivation ne valide pas numériquement les conversions Voigt ni les valeurs calculées par l’implémentation.

Pour la formulation TL, `δE=sym(FᵀδF)`, `δS=C_alg:δE`, `δP=δF S+FδS`. En différentiant `f_a=∫P∇N_a dV₀`, on obtient la somme du bloc matériel et du bloc géométrique `((∇N_a)ᵀS∇N_b)I`, les deux termes présents dans `_tangent`. TET4 et HEX8 partagent cette formule d’élément; leurs gradients, mesures de quadrature et assemblages restent à vérifier indépendamment en exécution.

À `f=0`, la contrainte retournée est continue, mais la tangente n’est généralement pas unique : le code choisit `C` avec la convention `f≤0`, alors que la limite plastique donne le tangent radial réduit. Une différence centrée traversant cette surface n’est donc pas une preuve d’une dérivée classique; les deux dérivées unilatérales doivent être caractérisées séparément.

## 3. C03 et éléments C04–C06 disponibles

Le certificat [`C03`](wp_e01_l_c03_metadata_fix/c03_certificate_promotion_record.json) a été intégré par le commit `b9b233f3f82feb564c2c295c9856df588836c80f`. Il établit la stabilité de branche sur 8 actions TET4/HEX8, `H=0` et `H=1.5 GPa`, deux directions par histoire entrante, et segments `±1e-4 m`, avec 304 contrôles point × action. Il ne prouve ni `K v=D F[v]`, ni la génération des histoires, ni les autres directions.

Les archives C04–C06 ne sont pas présentes sous ces identifiants dans l’arbre intégré. Les résultats historiques WP-E01-J consultés sont conservés comme observations, pas comme nouvelles exécutions : six diagnostics dérivés à histoire fixe ont passé leurs contrôles de branche; les deux directions mixtes TET4 ont montré la décroissance centrée `O(h²)` jusqu’au plancher de comparaison avec `K` binaire64. Quatre directions faibles, proches d’une translation inadmissible dans le sous-espace libre, ont gardé une erreur locale de 6,74–11,03 %; les quatre contrôles de translation exacte se sont arrêtés sur un défaut d’identité plan/`DofManager` avant la comparaison physique. Ces chiffres ne sont ni des bornes globales ni des seuils approuvés. Source : rapport historique WP-E01-J du dossier E01-A, daté du 21 octobre 2026.

Une concordance Decimal/binary64 ne borne pas à elle seule l’erreur du noyau, de la matrice assemblée ou de l’accumulation. Le balayage de pas et Richardson démontrent un comportement empirique sur les cas mesurés; ils ne fournissent pas une borne rigoureuse sans dérivées d’ordre supérieur encadrées et budget d’arrondi de toutes les évaluations.

## 4. Faisabilité, erreurs et couverture

| Objet | Ce qui est démontré maintenant | Ce qui manque pour une qualification |
|---|---|---|
| Retour radial J2, branches lisses | Dérivation symbolique de `C_alg` compatible avec les équations du source; valable à état entrant fixe pour `qtr>0`. | Oracle ponctuel indépendant exécuté contre les 6 composantes et 36 entrées tangentes, pour `H=0` et `H>0`, branches élastique/plastique, avec conversion Voigt vérifiée. |
| Passage élastique/plastique | Continuité du stress; deux dérivées unilatérales distinctes à `f=0`. | Contrat de classification à la surface et tests directionnels unilatéraux, sans exiger une dérivée unique. |
| TET4/HEX8 TL | Dérivation de la formule discrète matérielle + géométrique; règles de quadrature visibles au code. | Comparaison force/action sur toute la base des DDL libres de petits modèles, matrices de permutation/connectivité, BC/réactions, plusieurs états et histoires; borne d’erreur d’implémentation et d’arrondi. |
| TET4/HEX8 corotationnel | Chemin de force tracé; la matrice utilisée est produite par différence centrée à pas fini. | Tangente analytique/AD, ou tolérance Owner et majoration du biais de troncature + arrondi propre à chaque action, sur domaines polaires admissibles et branches stables. La symétrisation legacy doit aussi être justifiée. |
| Assemblage et réduction libre | Scatter-add puis restriction libre identifiés par inspection. | Référence indépendante connectivité→force/matrice, base complète `Q_f`, invariance aux permutations, réactions et contrôles du signe du résidu Newton. |
| Arrondi et erreur | C03 borne la stabilité mathématique de branche sur ses segments; archives haute précision donnent des comparaisons observées. | Enclosures de `F`, `K v`, produit matrice-vecteur, quadrature/assemblage, erreur Decimal, troncature des différences et conditionnement/cancellation par action. Aucun budget d’acceptation global n’est approuvé. |

La couverture existante comprend des tests unitaires TL, corotationnels, multiéléments et V&V J2 dans `tests/unit` et `tests/verification`; leur présence ne prouve pas leur exécution pour cette identité. Le test WP-E01-L reduced-space historique n’a pas été exécuté dans cette mission et ne couvre que huit directions, pas une base libre complète.

## 5. Garde d’exécution et décision de périmètre

À la date de ce rapport de faisabilité, la politique active autorisait E01 en mode `math_non_fem` pour 15 nodeids Hencky matériau-point seulement. Cette section précède l’autorisation et l’exécution des tests ciblés de phase 2 : la politique a depuis ajouté une allowlist J2 distincte pour des tests constitutifs et assemblages mémoire sans solveur. Aucun budget J2 FEM solver n’a été ajouté; aucun nodeid de solveur n’est autorisé par cette extension.

Un verdict positif global exige donc encore : (1) décision Owner sur les exigences d’erreur/tolérance, (2) allowlist exacte pour les tests mathématiques constitutifs J2 indépendants, (3) autorisation dédiée et garde vérifiée pour la comparaison élémentaire/globale TET4/HEX8, (4) oracle indépendant à haute précision et base complète des DDL libres, (5) budget rigoureux de troncature/arrondi et analyse des transitions, puis (6) revue indépendante des preuves archivées.

## 6. Revue critique et prochaines preuves

Revue interne indépendante en lecture seule : les dérivations matériau et TL sont cohérentes avec les formules codées sous les hypothèses indiquées; elle confirme que C03 est une preuve de branche bornée, que les résultats de différence finie restent directionnels/empiriques, et que les échecs de translation historiques n’ont pas mesuré l’invariance physique. Cette revue n’est pas une seconde exécution et ne remplace pas une revue scientifique externe au travail d’implémentation.

L’itération suivante minimale, avant toute expérience FEM, est un paquet de preuves **non exécuté contre le noyau** : (a) oracle symbolique indépendante de la convention Voigt et tables de dérivées J2, (b) tests algébriques de la formule TL sur tenseurs rationnels/perturbations symboliques, (c) registre des branches et des cas de non-différentiabilité, (d) exigences Owner pour l’erreur globale et directionnelle. Ensuite seulement, demander l’autorisation d’ajouter les nodeids J2 mathématiques au mandat actif. Les tests d’élément/assemblage et toute comparaison de base libre resteront séparés et nécessiteront le périmètre d’exécution adéquat.

Aucun solveur, résultat historique, seuil, certificat ou statut n’a été modifié ou promu.
