# WP12-C — Protocole préparatoire d’objectivité corotationnelle J2

**Type :** protocole de recherche proposé, non exécuté.
**Base documentaire :** audit WP12-C `e8ace46aa64c98d7c3650b2b449ab3951f8e5d6d`.
**Périmètre :** préparation d’une investigation ciblée; aucun mandat d’exécution n’est créé par ce document.

## 1. Question et limites

L’investigation doit déterminer si, après une histoire plastique non coaxiale, une rotation spatiale rigide superposée laisse inchangés la réponse locale et l’état matériel et transforme correctement les mesures spatiales. Elle doit localiser un éventuel défaut entre (a) transport d’état, (b) mise à jour constitutive au point, (c) transformation du stress et force élémentaire, (d) assemblage/scatter. Elle ne cherche pas à qualifier la plasticité à grandes déformations, le Newton global ou des éléments au-delà des fixtures identifiées.

Les deux identités sont séparées et testées séparément : `legacy_corotational_j2/v1` (route historique par défaut) et `corrected_corotational_biot_j2/v1` (route explicitement expérimentale). Aucun résultat de l’une ne vaut preuve pour l’autre.

## 2. Preuves historiques pertinentes

| Source | Résultat à retenir | Limite / implication pour le protocole |
|---|---|---|
| `wp08_constitutive_feasibility_report.md` | Le diagnostic R0 rapporte, après précharge plastique, `F2=Qz(0.71)F1` avec `F1=diag(1.016,0.992,0.992)`. `U2-U1` est au bruit numérique, mais la route legacy change `alpha` de `0.0149067` à `0.0312165`, le stress local de 73,4 %, et manque `P2=Q P1` de 91,6 %. Le rapport distingue ce spin incrémental d’une rotation appliquée à tout l’historique, laquelle peut rester covariante. | Contre-exemple historique précis pour le transport legacy; à conserver comme tel et à reproduire sans le réétiqueter. Ce constat ne suffit pas à lui seul à séparer la contribution de l’état de celle du mapping de force. |
| `wp08_constitutive_feasibility_report.md` et `wp08_r2_objectivity_and_plasticity_report.md` | Le chemin legacy utilise `P=R T_local`, transporte les tenseurs stockés par `R_current.T @ R_old`; le diagnostic non coaxial rapporte également une contrainte de Cauchy non symétrique et un défaut de moment. R2 corrigé garde l’état dans le repère matériau et utilise l’adjoint polaire exact. | Deux mécanismes indépendants : transport d’état et mapping de force. Le défaut de force peut exister même avec état maintenu fixe; le test de spin seul n’est donc pas le test complet du mapping de force. |
| WP08-R2, `wp08_r2_objectivity_and_plasticity_report.md` | Sur les fixtures bornées, l’objectivité corrected, l’oracle radial-return local et un trajet non coaxial TET4 sont documentés comme PASS. Les skew Cauchy/PK2 corrigés observés sont de l’ordre de `1e-16`; le legacy demeure distinct. | Résultat borné historique, pas une qualification générale ni une raison de rerun sans hypothèse nouvelle. Un nouveau calcul doit avoir un différentiel explicite et préserver ces verdicts. |
| WP09, `wp09_plastic_branch_diagnostics.md`, `wp09_tangent_robustness_report.md`, `wp09_newton_robustness_report.md` | Le tangent corrected de production est une différence centrée avec état accepté fixé; WP09 classe les transitions comme `BRANCH_TRANSITION`, sans dérivée classique ni garantie semismooth. La vérification directionnelle PASS concerne des directions plastiques lisses bornées. | Première phase : ne pas utiliser Newton pour attribuer une anomalie d’objectivité. Toute tangente est examinée en second temps, loin d’une transition et avec branche gelée. |

Les historiques WP08 (`WP08_STATUS=BLOCKED`, G03 `FAIL_PRESERVED`, G04 `BLOCKED`, WP14 `HOLD_NOT_PROMOTED`) et les qualifications WP09 restent immuables. La route corrected demeure expérimentale; cette proposition ne promeut aucun statut.

## 3. Transformations attendues sous rotation spatiale superposée

Prendre `Q ∈ SO(3)` constant et `F* = Q F`. Avec la décomposition droite `F=R U`, on attend `R*=Q R` et `U*=U`. La rotation agit dans l’espace courant; les indices matériels/de référence restent inchangés.

| Quantité | Transformation attendue | Interprétation / comparaison |
|---|---|---|
| Stretch `U`, déformation locale `E_B=U-I` | `U*=U`, `E_B*=E_B` | Identiques pour une rotation après précharge qui laisse le même stretch. |
| Variables internes tensorielles corrected (déformation plastique additive, contraintes/strains historiques de state) | Identiques dans le repère matériel de référence; aucun incrément causé par `Q` seule. | Comparer les composantes du state versionné avant/après. En legacy, comparer d’abord la règle de transport réellement appliquée à l’invariant `alpha`; ne pas décréter que le transport legacy doit satisfaire le contrat corrected. |
| Scalaires internes `alpha`, dissipation, énergie d’écrouissage | Identiques si `E_B` et l’état accepté sont identiques; `Delta alpha=0` pour le seul spin. | Un changement signale état altéré, mauvaise branche/entrée locale ou défaut de transaction. |
| Contrainte conjuguée Biot locale `T_B` (corrected) | `T_B*=T_B` | Même matériau, même `E_B` et même state accepté impliquent exactement la même entrée locale et la même réponse. |
| PK2 `S=F⁻¹P` | `S*=S` | Mesure matérielle, invariance sous rotation spatiale. |
| Cauchy `sigma=J⁻¹ P Fᵀ` | `sigma*=Q sigma Qᵀ` | Mesure spatiale; comparer sans symétrisation postérieure. |
| First Piola `P` | `P*=Q P` | Mesure à deux points; les indices spatiaux tournent, les indices matériels restent fixes. |
| Force interne nodale d’un même maillage de référence | `f*_a=Q f_a` pour chaque nœud `a` | Vérifie le mapping élémentaire et, séparément, scatter/assemblage. |
| Tangent élémentaire/global en base nodale fixe | `K*=(I_n⊗Q) K (I_n⊗Q)ᵀ` pour le bloc translatoire considéré | Comparer uniquement sur branche lisse, mêmes DDL/contraintes et base cohérente. Aucun résultat Newton ne se déduit de cette covariance. |

Ces relations sont le contrat pour le chemin corrected dérivé de la formulation WP08-R1/R2. La conformité legacy est un objet de diagnostic par rapport à son propre comportement historique; un échec legacy reste un échec historique, et non un motif de modifier rétroactivement le contrat ou les archives.

## 3.1 Niveaux de preuve à ne pas confondre

| Niveau | Question propre à ce protocole | Observable / oracle | Ce qui ne suffit pas |
|---|---|---|---|
| 1. Matériau au point de Gauss | À `E_B` et state accepté identiques, le retour radial produit-il la même réponse et le même état selon l’oracle indépendant? | Variables internes, fonction de charge, multiplicateur, contraintes locales et résidu de l’oracle tensoriel. | Covariance de `P` ou succès d’un élément entier. |
| 2. Noyau élémentaire | Le point matériel, la transformation polaire et l’intégration donnent-ils les stress/forces nodaux attendus pour un TET4? | `P/S/sigma`, force par nœud, gradient indépendant du potentiel incrémental et identité angulaire. | Une somme de forces globales ou un solveur convergé. |
| 3. Assemblage global | Le scatter des forces élémentaires respecte-t-il les cartes DDL et les transformations des vecteurs/blocs? | Comparaison au scatter indépendant, nœud par nœud et DDL par DDL. | La justesse du noyau seul ou la convergence Newton. |
| 4. Solveur non linéaire | Un Newton avec cette tangente converge-t-il et respecte-t-il les transactions d’état? | Explicitement hors périmètre de la première campagne; nécessiterait une phase et une autorisation séparées, branche lisse et preuve préalable des niveaux 1–3. | Toute preuve matière, élémentaire ou d’assemblage isolée. |
| 5. Validation structurelle indépendante | La réponse intégrée satisfait-elle des contrôles mécaniques indépendants (invariance par rotation, équilibre/résultantes et moment sans couple parasite) ? | Bilan de force et moment comparé à un oracle indépendant; le gradient de potentiel vérifie la force élémentaire, mais n’est pas à lui seul une qualification structurelle générale. | Un test unitaire, un résidu Newton faible ou un résultat de post-traitement du solveur lui-même. |

Chaque rapport de résultat futur doit porter son niveau atteint et ses dépendances; aucun PASS ne se propage automatiquement au niveau suivant. La validation structurelle proposée ici reste une vérification bornée de fixture, pas une qualification générale ni une validation externe de conception.

## 4. Trajets à comparer

### 4.1 État de préchargement commun

Employer le TET4 unitaire et les paramètres matériau de la fixture historique exacte WP08 de précharge (`E`, `nu`, limite d’écoulement et écrouissage relevés de son artefact source, puis figés dans le manifeste). Ne pas substituer les paramètres de la fixture de test corrected simplement parce qu’ils sont disponibles.

Le trajet est imposé par gradients affines homogènes, sans solveur global :

1. `F0=I`, état initial vierge.
2. Précharge A, uniaxiale déviatorique, sur une valeur fixe `a` satisfaisant la preuve historique de plasticité et la borne locale `||U-I||F ≤ 0.05`.
3. Précharge B, incrément non coaxial (composante de cisaillement ou axe principal tourné), calculée à partir de la même histoire acceptée. L’invariant de commutation `||T U-U T||/(max(||T||·||U||,s0))` doit être strictement supérieur au seuil préenregistré de séparation coaxial/non coaxial.
4. Geler et hasher l’état accepté `S_pre`, `F_pre`, les paramètres, le maillage, la quadrature, les coordonnées et le vecteur des DDL.

Le choix final des amplitudes est arrêté avant le run par lecture/rejeu symbolique des données existantes ou par pré-calcul indépendant autorisé, pas par tâtonnement sur la production. Les invariants de prérequis sont : `alpha_pre>0`, deuxième incrément effectivement plastique si c’est la branche visée, `||U-I||F` sous la limite existante avec marge préenregistrée, et non-coaxialité mesurable. Si l’un manque, résultat `INVALID_PROTOCOL`, pas PASS/FAIL mécanique.

### 4.2 Référence et équivalent tourné

Depuis une copie immuable de `S_pre`, comparer :

- **R — référence maintenue :** évaluer `F_pre` et `S_pre` sans incrément physique additionnel;
- **Q — spin seul :** évaluer `F*=Q F_pre` avec `Q=Qz(0.71)` comme dans le contre-exemple WP08; repartir exactement du même `S_pre`, sans accepter une mutation de R;
- **Q-all — contrôle de rotation de l’historique entier :** appliquer la même `Q` à chaque `F` de la précharge A/B, avec état frais. C’est un contrôle de covariance de la trajectoire, distinct du spin seul, et non un substitut à Q;
- **Q-local-fixed-state — sonde de localisation :** pour le diagnostic legacy uniquement, fournir au calcul de réponse final une copie immuable de l’état juste avant le spin, en neutralisant le transport uniquement dans le harnais de mesure. Ne pas modifier le code/route. Cette sonde isole le transport d’état de la transformation de stress/force, mais ne constitue pas un résultat du solver legacy.

Chaque évaluation repart d’un snapshot indépendant, afin que l’ordre d’appel ne puisse pas faire du résultat Q le nouvel état accepté. La phase initiale se limite au point matériel et à la force d’un TET4 affine; elle exclut Newton et l’adaptation de pas.

## 5. Arbre d’attribution falsifiable

| Observation | Attribution soutenue | Contrôle de confirmation / exclusion |
|---|---|---|
| À `E_B*≈E_B`, le point matériel avec mêmes paramètres et même state diffère de l’oracle tensoriel radial-return indépendant. | Défaut de loi/implémentation constitutive locale, branche incohérente ou convention Voigt/tenseur incorrecte. | Comparer `E_B`, les six composantes converties, fonction de charge, `Delta gamma`, contraintes, `alpha`, dissipation et énergie à state initial identique; vérifier un cas élastique et un cas plastique lisse. |
| L’oracle local passe lorsque le state est figé, mais le chemin Q produit un changement de tenseurs internes/`alpha` non exigé par le contrat de la route examinée. | Erreur de transport d’état ou de transaction. | Comparer state pré-transporté à state figé; si seule la sonde Q-local-fixed-state rétablit `T_B`, l’attribution au transport est étayée. En corrected, toute différence de state sous spin seul est un défaut à expliquer. |
| Point local et state passent, mais `P`, `S`, `sigma` ne satisfont pas leurs transformations. | Défaut de mesure/repère ou de mapping polar contrainte-force. | Recalcul indépendant de `P` depuis le contrat; vérifier d’abord les mesures ponctuelles, sans assemblage. Utiliser l’identité de travail/adjoint et les skew invariants sans averaging. |
| Mesures ponctuelles passent, mais force nodale élémentaire ne tourne pas comme `Q f`. | Défaut du noyau force, gradients, quadrature ou convention d’indices. | Comparer la force au gradient indépendant du potentiel incrémental sur le même élément, paramètres et state; inspecter chaque contribution d’intégration. |
| Force élémentaire et points passent, mais somme/scatter global échoue. | Défaut d’assemblage global, de carte DDL ou de transformation des contraintes. | Comparer le vecteur assemblé au scatter indépendant des forces locales; comparer les DDL regroupés par nœud et les résidus avant toute résolution. |
| Force et assemblage passent, tangent seul échoue hors transition. | Défaut de tangent/dérivée, pas une preuve de défaut constitutif. | Différences directionnelles indépendantes à state accepté fixe; confirmer `SMOOTH_ELASTIC` ou `SMOOTH_PLASTIC`; comparer transformation tensorielle du tangent en base nodale tournée. |
| Les diagnostics montrent une branche traversée, des états mutés entre probes, des valeurs non finies ou une identité de source/fixture non conforme. | `INCONCLUSIVE` ou `INVALID_PROTOCOL`; attribution scientifique non permise. | Corriger uniquement le protocole/identité dans une nouvelle décision; ne pas retuner un seuil et ne pas interpréter comme PASS. |

## 6. Observables et critères préalables

Avant l’exécution, le manifeste Owner doit fixer les hashes, unités, valeurs exactes, ordre des increments, tolérances, oracle et résultat attendu. Le candidat minimal de métriques est :

1. **Cinématique :** résidu de polar/reconstruction, `||U_Q-U_R||`, `||E_Q-E_R||`, `det(Q)-1`, `||QᵀQ-I||`.
2. **Constitutif :** `alpha`, plastic strain tensor, contrainte locale, fonction de charge et multiplicateur plastique; résidus contre l’oracle tensoriel indépendant.
3. **Stress :** covariances PK2/Biot invariants, `P_Q-QP_R`, `sigma_Q-Q sigma_R Qᵀ`; skew non normalisé puis relatif, et identité angulaire sans symétrisation.
4. **Élément :** force par nœud, résultante, moment et gradient indépendant du potentiel incrémental.
5. **Assemblage, seulement après succès élémentaire :** vecteur de force après scatter comparé au scatter indépendant; matrice tangentielle transformée seulement sur branche lisse.

Réutiliser en priorité les seuils/mesures déjà préenregistrés et non révisés dans les artefacts WP08/WP09 correspondant à l’identité source retenue : transformation `≤1e-12 × max(||référence||F, 1 Pa)`, skew relatif corrigé `≤1e-10`, tolérances d’état du test pure-spin corrected (`5e-12` tensoriel, `5e-13` scalaire), covariance force/stress du test corrected (`5e-11` relatif avec ses tolérances absolues gelées), et erreur tangentielle seulement si la branche et le nœud WP09 sont les mêmes (`2e-5` historique). **Ces valeurs sont des références candidates, pas une autorisation de changer ni de réutiliser automatiquement des critères hors de leur contrat.** Les métriques du contre-exemple legacy sont évaluées contre les valeurs et méthodes archivées, pas contre un seuil rétrospectivement assoupli.

Décision après calcul :

- **PASS borné** seulement si tous les prérequis passent, l’oracle indépendant concorde, les invariants de la route considérée respectent les critères gelés, et l’identité de preuve est complète;
- **FAIL développement** si un critère préenregistré échoue avec entrée/source valides, en conservant l’archive et en attribuant seulement le niveau effectivement démontré;
- **INCONCLUSIVE / INVALID_PROTOCOL** en cas de mismatch d’identité, branche non maîtrisée, manque d’observable, oracle non indépendant, ou tolérance non gelée.

Aucun de ces résultats ne change automatiquement WP08/WP09, la maturité, un gate release, ou les verdicts historiques.

## 7. Nodeids candidats et autorisation

Une inspection statique des tests présents trouve notamment :

- `tests/unit/test_corotational_j2.py::test_corotational_j2_rigid_rotation_has_no_spurious_response` et `::test_corotational_j2_transports_committed_local_tensor_state` (contrôle legacy existant);
- `tests/unit/test_corotational_j2_corrected.py::test_corrected_pure_spin_preserves_accepted_material_state`, `::test_corrected_superposed_rotation_covariance_and_origin_invariance`, `::test_corrected_noncoaxial_history_changes_legacy_force_without_rewriting_legacy`, et `::test_polar_adjoint_satisfies_virtual_work_and_angular_identity` (contrôles corrected existants).

Ce sont des identifiants candidats déjà présents, pas des recommandations de relancer des nœuds qui pourraient dupliquer une preuve historique. Aucun nodeid d’objectivité WP12/J2 n’est enregistré dans la politique consultée pour le worktree courant. Un futur essai exige une décision Owner distincte, un worktree scientifique désigné et propre, sources et fixture gelées, oracle/critères identifiés, nodeid exact préenregistré dans la portée autorisée ou revue de politique applicable, manifeste à usage unique et archive neuve. Ne pas élargir un scope d’un autre worktree ni invoquer un nodeid générique. Aucun nodeid n’est lancé dans cette préparation.

## 8. Ressources et estimation

| Phase | Contenu | Effort ciblé |
|---|---|---:|
| A — Pré-enregistrement | Relever hashes et paramètres historiques; confirmer contrat de route, oracle indépendant, unités et tolérances; préparer manifeste/receipt. | 0,5–1 jour-personne |
| B — Point matériel / état | Précharge A/B; référence, spin seul, rotation complète et sonde state figé; contrôles radiaux indépendants. | 1–2 jours-personne |
| C — Noyau TET4 | Covariance des stress/forces, potentiel incrémental et moment; séparation explicite corrected/legacy. | 1–2 jours-personne |
| D — Assemblage | Scatter indépendant et tangent covariance, seulement si C passe et si inclus dans le mandat. | 1–2 jours-personne additionnels |

**Total préparatoire et exécution candidate : 3–7 jours-personne**, hors attente Owner, temps machine, revue indépendante et toute investigation Newton. Le coût de préparation documentaire déjà effectué n’est pas compté. Un résultat D01/contact, une étude de maillage, benchmark ou analyse de Newton n’est pas inclus.

## 9. Sources examinées

- [`wp08_constitutive_feasibility_report.md`](wp08_constitutive_feasibility_report.md) — contre-exemples historiques et séparation des défauts d’état/force.
- [`wp08_r2_objectivity_and_plasticity_report.md`](wp08_r2_objectivity_and_plasticity_report.md) — preuves bornées de la route corrected et limites.
- [`wp08_r2_legacy_compatibility.md`](wp08_r2_legacy_compatibility.md) — identité et compatibilité des routes.
- [`wp08_r1_corrected_formulation.md`](wp08_r1_corrected_formulation.md) — contrats de repères et transformations attendues.
- [`wp09_plastic_branch_diagnostics.md`](wp09_plastic_branch_diagnostics.md), [`wp09_tangent_robustness_report.md`](wp09_tangent_robustness_report.md), [`wp09_newton_robustness_report.md`](wp09_newton_robustness_report.md) — branche et limites tangent/Newton.
- Code et tests lus statiquement : `src/solveur/elements/solid/corotational_j2.py`, `tests/unit/test_corotational_j2.py`, `tests/unit/test_corotational_j2_corrected.py`.

**Statut :** `PREPARED_NOT_AUTHORIZED`. Aucune exécution, modification de source, d’oracle, de politique ou de worktree scientifique n’a été faite pour ce protocole.
