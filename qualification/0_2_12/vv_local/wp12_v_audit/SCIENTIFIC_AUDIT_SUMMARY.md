# WP12-V — Synthèse de l'audit scientifique

**Date :** 2026-10-26.
**Verdict global :** WP12_V_SCIENTIFIC_AUDIT_COMPLETED.
**Classification principale de l'échec :** FLOATING_POINT_ASSERTION_DEFECT.
**Mécanisme précis du bit produit par l'assemblage :** ASSEMBLY_ORDER_ROUNDOFF plausible; non démontré par une trace des contributions.
**Statuts préservés :** U1/U2 PYTEST_PASS_ONLY; U3 FAIL; WP11 CLOSED; WP12 OPEN; WP13 OPEN.

L'audit est terminé au sens du mandat : les archives et sources ont été confrontées, les métriques ont été recalculées, les limites de causalité identifiées et un protocole prospectif proposé. Il ne prétend pas avoir identifié l'ordre runtime des trois contributions manquantes, ni validé le continuum 3D.

## A — Origine de l'échec U3

Le test U3, au commit tests `9c7df65403fc15dc6d12365534172eac87f2ee70`, calcule les diagnostics avant d'échouer à `tests/unit/test_wp12_u_tet4_route_crosscheck.py:637`. L'assertion exige simultanément la symétrie exacte des matrices rationnelle, scalaire et batch; seuls les deux premiers booléens sont vrais. Le résultat conservé est un échec de cette assertion, avec un seul testcase sélectionné, code de sortie 1 et aucun incident d'infrastructure signalé.

`np.array_equal` vérifie une égalité exacte des valeurs, pas universellement l'identité des mots binaires (notamment +0/−0). Pour cette paire finie non nulle, l'exigence revient bien à demander le même binary64 dans les deux positions.

| Observation archivée/recalculée | Valeur |
|---|---:|
| Indices globaux zéro-based | (14,22) et (22,14), soit Uz nœud 4 / Uy nœud 7; DDL libres |
| K[14,22] | −44871794871.79487 N/m; `-0x1.4e522816f96f9p+35` |
| K[22,14] | −44871794871.794876 N/m; `-0x1.4e522816f96fap+35` |
| Écart | 2^−17 = 7.62939453125e−6 N/m = 1 ULP |
| Paires transposées différentes | 1 sur 630 paires hors diagonale |
| Norme Frobenius de K−Kᵀ | 1.0789593218788873e−5 N/m |
| Norme Frobenius de K | 6.184394795572822e11 N/m |
| Rapport des normes | 1.7446481952466456e−17 |

La conclusion ne repose pas sur la seule petitesse de cet écart :

1. Les kernels scalar et batch construisent explicitement les valeurs locales miroirs par symétrisation. Leurs conventions B/D donnent la même forme élastique V Bᵀ D B; U2 a vérifié deux éléments isolés par oracle rationnel indépendant.
2. L'assemblage SciPy coalesce ensuite séparément les contributions de chaque coordonnée globale. Le code ne réaffecte pas une valeur unique aux deux positions globales. Le profil SciPy 1.15.2 trie et additionne les doublons; il ne fournit pas de garantie de symétrie exacte du stockage global. Une telle propriété n'est donc pas justifiée comme invariant universel de ce chemin.
3. La référence rationnelle et le scalaire sont exactement symétriques; l'écart apparaît dans le résultat global de la route batch sparse, avant réduction des contraintes. Il ne provient pas d'une paire simplement écartée par les conditions aux limites.
4. Les éléments contributeurs sont 0, 8 et 9. L'archive U2 fournit la contribution du premier : −8974358974.358974 N/m dans les deux orientations. Les valeurs locales runtime des éléments 8 et 9 et leur ordre après tri ne sont pas conservés. Leur somme exacte de contributions flottantes n'a pas été réinventée par un nouvel appel FEM.

**Démontré, confiance élevée :** le critère exact n'est pas couvert par une garantie de l'assembleur et provoque le FAIL. **Démontré :** localisation au résultat global batch et différence d'un ULP. **Hypothèse soutenue par la source, confiance modérée :** différence normale de réduction des doublons. **Indéterminé :** attribution de ce bit à une permutation précise, à une opération native particulière ou reproduction interplateforme. L'audit ne classe donc pas ASSEMBLY_ORDER_ROUNDOFF comme cause runtime prouvée.

L'Owner avait approuvé le critère exact pour U3; son échec demeure donc valide selon ce protocole. Le classement FLOATING_POINT_ASSERTION_DEFECT concerne son usage comme oracle de symétrie mécanique/équivalence de cette route, qui ne promet pas ce stockage exact. Si l'Owner veut une nouvelle exigence de stockage exactement symétrique, il s'agit d'une exigence de conception à décider prospectivement, pas d'un motif de réécrire U3.

Le diagnostic ne démontre ni ELEMENT_SYMMETRY_DEFECT, ni GLOBAL_ASSEMBLY_DEFECT mécanique, ni SOLVER_ROUTE_DEFECT. Cette absence de défaut démontré n'est pas une qualification générale. Voir [le détail causal](U3_FAILURE_ROOT_CAUSE.md) et [l'audit de symétrie](MATRIX_SYMMETRY_FLOATING_POINT_AUDIT.md).

## B — Équivalence matrix-free/direct

Le modèle H1, les propriétés isotropes, la connectivité, les DDL, le second membre et les appuis sont identiques dans les deux routes. Le direct utilise la matrice batch SciPy et une résolution explicitement directe; le matrix-free applique les templates scalaires et accumule leurs produits avant CG avec Jacobi par blocs nodaux. Ce sont deux algorithmes de calcul, pas deux oracles physiques indépendants.

L'archive contient la matrice globale assemblée complète, sa référence et les champs complets des deux solutions. Les recalculs hors solveur ont vérifié :

| Grandeur | Observation et portée |
|---|---|
| Matrice batch vs référence rationnelle arrondie | erreur relative Frobenius 9.050773047627961e−17 sur les 36×36 entrées; pas seulement trois vecteurs |
| Matrice scalaire vs référence | erreur relative Frobenius 9.63860460493275e−17 |
| Produits matrix-free/direct | trois vecteurs libres déterministes; ratios route de 2.08e−17 à 4.90e−17 selon la normalisation de U3 |
| Deux champs pour la charge H1 | écart L2 relatif 4.259605142953099e−12; écart maximal 3.1367464309835078e−20 m |
| Résidu libre sur la matrice fractionnaire indépendante | matrix-free 8.01766808946804e−9 relatif à 0.5 N; direct 1.1492670024590035e−13 avec dénominateur de U3 égal à 1 N |
| Équilibre / énergie | résidus libres reproduits exactement en Fraction; réactions et identités force, moment et 2U−W = u_freeᵀr_free cohérentes |

Les sorties ont une provenance exploitable malgré le FAIL : elles sont émises avant l'assertion, incluses dans stdout, sélection/JUnit/reçu et liées à leurs empreintes. Les assertions des lignes 638–642 demeurent NOT_REACHED; le recalcul de l'audit est une analyse nouvelle des données enregistrées, pas leur réussite rétrospective dans pytest.

Ces résultats établissent un accord étroit pour le problème discret et le chargement H1 observés. Ils ne démontrent pas l'identité complète de l'opérateur matrix-free : ses 24 colonnes libres ne sont pas archivées. Une solution et trois produits ne suffisent pas à prouver cette identité. Les réactions/énergies sont construites sur le même opérateur rationnel; leurs identités renforcent la cohérence algébrique et ne constituent pas des mesures indépendantes.

La matrice libre présente κ₂ ≈ 7.97e3 (diagnostic de post-traitement, non valeur propre certifiée). Le [rapport quantitatif](MATRIX_FREE_DIRECT_EVIDENCE_REVIEW.md) donne les normes, les valeurs par route, les écarts absolus et normalisés, leurs unités, les dénominateurs et les limites.

Une vérification plus forte a été ajoutée pour éviter de conclure de la seule petitesse des normes : un inverse approché B de la matrice fractionnaire libre A0 a été calculé hors solveur, puis `q=||I−A0 B||∞` vérifié exactement en Fraction. Avec q ≈ 4.14385e−13 < 1, la borne exacte `||A0⁻¹||∞ ≤ ||B||∞/(1−q)` est établie. Les écarts d'opérateur archivés donnent une borne relative ∞ de perturbation de solution, pour un même second membre et des résolutions mathématiques exactes, d'environ **1.2528e−12 pour le batch** et **1.0637e−12 pour le scalaire**. La preuve rationnelle et ses fractions sont à la section 3.1 du rapport quantitatif. Elle borne l'effet de toute différence entre ces assemblages stockés H1 et A0, au-delà du seul terme antisymétrique. Elle ne comprend pas les erreurs supplémentaires d'une résolution flottante, examinées séparément par les résidus, et ne prouve pas l'opérateur matrix-free complet.

## C — Statut mécanique TET4 et écart initial de 66,69 %

U2 contribue à vérifier l'élément linéaire à déformation constante : deux géométries, convention de cisaillement ingénieur, gradients, B/D, rigidités, forces internes, énergies et six modes rigides sont confrontés aux oracles du test. Cette preuve ne porte pas sur la flexion d'un maillage assemblé ni sur un continuum 3D général.

U3 réduit fortement l'hypothèse d'un désaccord significatif entre les deux routes pour H1 et ce chargement : les solutions sont très proches et leurs résidus sont petits sur l'opérateur indépendant du cas. Le FAIL exact de stockage ne remet pas ces valeurs à NOT_EXPOSED, mais il empêche de déclarer le test U3 réussi.

Le déficit de 66,69 % provient du niveau fin H3 comparé à un diagnostic poutre 1D. U3 concerne H1 (niveau grossier, dont le déficit au même diagnostic est environ 96,42 %). Aucun transfert automatique de la concordance H1 à H2/H3 n'est justifié. Les questions d'approximation P1 en flexion, de charge/observable et de référence 3D restent celles de WP12-T. Aucune part du déficit fin n'est attribuée quantitativement par cet audit à un mécanisme unique; la validation physique et la convergence asymptotique demeurent non acquises.

## D — Correctif recommandé

**Aucune correction immédiate de production.** Aucun changement du solveur, de l'assemblage ou de la formulation n'est soutenu par une erreur mécanique démontrée dans cette archive. U3 et ses assertions historiques restent inchangés.

Pour un nouveau test, remplacer le présupposé d'égalité globale exacte par une borne prospective validée : pour les contributions a et b des deux orientations, la dissymétrie admissible est bornée par L + γ_p S_a + γ_q S_b. Les kernels miroirs donnent L=0 sous leurs hypothèses; ici trois contributions permettent p=q=2 pour une réduction ordinaire. Il manque cependant S pour évaluer cette borne sur l'archive U3. La valeur observée n'est donc pas déclarée conforme à une borne gamma a posteriori non calculée. La borne de perturbation vérifiée ci-dessus est une autre forme de preuve : elle borne l'effet de l'opérateur stocké, pas la cause arithmétique des trois contributions.

L'ordre exact n'est pas nécessaire à cette borne worst-case; il reste nécessaire pour reproduire le bit précis. Une égalité exacte peut rester un invariant local où une même valeur est reproduite par affectation miroir. Une moyenne globale (K+Kᵀ)/2 peut cacher une erreur d'indexation et changer l'opérateur; un ordre déterministe ne prouve pas l'exactitude. La [proposition de critère](NUMERICAL_CRITERION_PROPOSAL.md) compare les options A–D, leurs coûts, leurs risques et leurs contrôles négatifs.

## E — Prochaine action

Les archives suffisent pour le diagnostic de critère et pour les conclusions bornées ci-dessus. Une expérience V2 n'est utile que pour fermer les limites de traçabilité de réduction et/ou d'équivalence complète du bloc matrix-free. Le [plan minimal proposé](PROSPECTIVE_V2_TEST_PLAN.md) conserve la fixture H1, capture les contributions et toutes les colonnes libres, et réemploie les solutions archivées lorsque leur re-résolution n'est pas nécessaire. Il n'inclut pas de raffinement ni de campagne globale.

Ce plan reste PROPOSED_NOT_AUTHORIZED. Il nécessite un nouveau test, un nouveau manifeste figé et une décision Owner distincte avant tout calcul. Aucune autorisation U n'est réutilisée.

## Revue et intégrité

Le modèle courant du responsable de consolidation est GPT-6.1 Sol, selon le contexte runtime du tour. Trois tâches Luna-executor ont couvert la chaîne d'assemblage, les métriques archivées et le critère prospectif; l'effort demandé était high. Le modèle est fixé par le rôle; aucune métadonnée de lancement supplémentaire ne permet de certifier ici l'effort effectif. La consolidation a corrigé les limites d'une première formulation de la borne (ordre d'arbre contre majorant m−1), les liens et les normalisations. Cette organisation n'est pas une certification externe ni trois validations physiques indépendantes.

Le [registre de provenance](README.md) identifie les octets WP12-U locaux non committés, les commits gelés, les reçus et les contrôles d'intégrité. Aucun fichier scientifique, test historique, manifeste U ou archive n'a été modifié; seuls les sept rapports de ce dossier sont destinés au commit documentaire.

Les contrôles documentaires couvrent les sept fichiers attendus, les 26 références locales et les tableaux Markdown. La comparaison SHA-256 des 40 fichiers d'entrée/preuves/documents U avant et après audit ne détecte aucune modification ni ajout dans ces ensembles. Les trois checkouts gelés restent propres aux identités annoncées. Les trois workers de cette mission sont terminés; aucun n'est encore actif. L'interface expose leur statut terminé mais pas d'opération distincte de fermeture. Aucun budget de nouvelle tentative scientifique n'a été consommé; les compteurs de tokens/temps des travaux de lecture n'ont pas été instrumentés comme métriques de campagne.
