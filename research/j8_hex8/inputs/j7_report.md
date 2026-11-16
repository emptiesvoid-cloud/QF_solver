# QF Solver 0.3.0 — Jalon J7 : résultats

Date : 2026-11-16
Statut : diagnostic de développement borné, non qualification.

## Synthèse

J7 a exécuté les deux reprises HEX8-SRI post-correction et un calcul R4 HEX20/QUAD8 selon des nodeids individuels enregistrés. Les trois tests se sont terminés dans leur budget, mais les critères scientifiques HEX8 restent FAIL. Le calcul R4 reproduit le résidu historique FAIL et satisfait un budget d’erreur prospectif propre à ce seul patch. L’audit TET4 réutilise les résultats J6 et ne relance aucun calcul FEM.

Aucune modification du solveur ni des seuils historiques n’a été faite. Les données brutes et traces expurgées sont archivées sous `research/j7_static_debt/results/2026-11-16/`.

## Baseline et portée

| Élément | Référence vérifiée |
|---|---|
| `origin/main` relevé pour J7 | `be455745f4a1c2cf81cb9448830223107dc39b66` |
| Ancêtre J6 | `873d681cb0a993183e827896902bd321b11810c2` |
| Branche isolée | `work/0.3.0-j7` |
| HEAD source des calculs | `7b60400eeb34239e1cf639dc7e92f94118ca57bc` |
| Worktree | `qf_solver_030_j7`, propre au lancement des calculs |

`origin/main` est ancêtre de la branche. Le checkout utilisateur `qf_solver` n’a pas été modifié. Le commit `7b60400` a enregistré le runner, les contrats, les entrées et les trois nodeids avant tout lancement FEM. Les exécutions ont ensuite conservé ce même HEAD, cette même empreinte de source (`e82803a2d39f48d51f5e18d153c6b82df0f2e22271ca3a659b2a57e4c52b37f1`) et un arbre de travail propre.

La procédure Owner J7 répond à l’autorisation de développement : les trois cas ont chacun un nodeid exact, une limite d’une tentative, un contrat et une entrée hachée. Le fichier local `development_autonomous_policy.json` est ignoré par Git et contient les racines absolues nécessaires au runner; il n’est pas livré. Le scope versionné et les contrats sont dans `research/j7_static_debt/`.

## HEX8-SRI post-correction

Les deux reprises utilisent le cas global historique, l’assemblage dense puis `numpy.linalg.solve`; elles ne démontrent pas à elles seules la route complète du solveur de production. Le fichier source SRI corrigé est celui dont le SHA canonique est `e014652e9efc3912046891348d9dfa76adaa1f8ff084db58e84a9b3d151cf9e4`. La charge totale appliquée est −1 N suivant Z.

| Cas | Maillage | `nu` | Charge résultante relative | Erreur énergie | Résidu DOF | Fermeture force | Fermeture moment | Statut scientifique |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Régulier | 16×2×2, 64 éléments, 153 nœuds | 0,4999 | 2,22e−16 PASS | 3,227e−10 FAIL | 1,093e−7 FAIL | 5,353e−8 FAIL | 1,165e−7 FAIL | **FAIL** |
| Quasi dégénéré valide | 4×2×2, 16 éléments, 45 nœuds | 0,495 | 2,22e−16 PASS | 5,610e−10 FAIL | 2,581e−7 FAIL | 1,217e−7 FAIL | 2,224e−7 FAIL | **FAIL** |

Tous les critères scientifiques ci-dessus ont un seuil gelé de 1e−10, à l’exception du contrôle de résultante (1e−14). Dans les deux cas, les matrices sont symétriques, les champs finis et les jacobiens de Gauss strictement positifs (minimum 0,0390625 m³ et 0,00625 m³). Cela écarte une inversion d’élément pour ces entrées, sans établir la cause des défauts d’équilibre et d’énergie.

Les états bruts montrent des matrices libres très mal conditionnées : estimation `κ₂(Kff)` = 4,359e9 pour le cas régulier et 1,511e10 pour le quasi dégénéré. Les résidus libres relatifs à la norme de charge valent respectivement 3,279e−7 et 7,742e−7; `κ₂ ε` vaut environ 4,84e−7 et 1,68e−6. Cette proximité rend l’arrondi et le conditionnement compatibles avec une contribution importante, mais ne prouve pas qu’ils soient la cause unique : assemblage, calcul de résidu, réactions et cohérence énergétique restent à isoler.

### Comparaison historique pré-correction

Le manifeste WP13-12 reste inchangé (`KEEP_EXPERIMENTAL`, avec les échecs de campagne conservés). Pour le cas régulier `nu=0,4999`, `nx=16`, il archive avant correction : énergie 2,035e−11, résidu libre 1,127e−8, fermeture de force 2,085e−9 et de moment 4,924e−9. Les valeurs J7 sont supérieures sur ces quatre métriques. Pour le cas quasi dégénéré historique `nu=0,495`, `nx=4`, l’énergie s’améliore de 1,028e−9 à 5,610e−10, tandis que les fermetures force et moment augmentent de 7,258e−9 à 1,217e−7 et de 1,715e−8 à 2,224e−7.

Les définitions des métriques de résidu, force, moment et énergie sont les mêmes dans les deux routes; le code historique et le code J7 ne sont toutefois pas la même source. Cette comparaison montre un résultat post-correction mitigé, pas une attribution causale à la correction. Aucune référence indépendante de déplacement n’est établie pour ces configurations globales.

**Point de méthode à ouvrir :** le champ historique `energy_identity_relative` est calculé comme `|U−W| / max(|W|, 1.0)` en SI. Comme `W` est inférieur à 1 J dans ces essais, le dénominateur vaut numériquement 1 et le critère se comporte comme une limite absolue en joules. Le seuil gelé n’a pas été changé; il ne faut pas l’interpréter comme une erreur relative indépendante des unités sans revoir sa définition prospective.

## Moment HEX20 / QUAD8 R4

Contrat `J7-HEX20-QUAD8-R4-MOMENT-BUDGET-001`, entrée `hex20_r4_equivalent.json`, 20 nœuds, 1 HEX20, 60 degrés de liberté, cinq faces QUAD8 chargées et une face fixée. Le test reconstruit les forces nodales et compare une intégration QUAD8 indépendante, des sommes ordinaires, inversées et compensées, le transport d’origine et des identités de corps rigide.

| Mesure | Résultat |
|---|---:|
| Erreur relative du vecteur de charge QUAD8 indépendant | 1,746e−16 PASS |
| Patch affine de déplacement / contrainte | PASS / PASS |
| Résidu de moment historique à l’origine | 5,853561e−9 N·m, au-dessus de 1e−12 : **FAIL conservé** |
| Reproduction du résidu J6 archivé | delta 0 N·m |
| Invariance de `eta` avec changement d’unité | 0, limite 1e−15 : PASS |
| Résidu compensé au centroïde | 8,170345e−9 N·m |
| Budget prospectif de ce cas | 2,314210e−7 N·m : `WITHIN_CASE_BUDGET` |

Le budget additionne des bornes binary64 de soustraction d’origine, produits vectoriels, sommation, résidu d’équilibre libre et invariance de rotation rigide. Le résidu est inférieur au budget d’environ 28 fois. C’est un diagnostic d’arrondi pour cet état affine représenté en binary64, pas un PASS générique pour HEX20/QUAD8, ni un remplacement du FAIL historique J2B/R4. La nouvelle tentative n’a pas rendu ce verdict historique caduc.

## Série TET4 à source commune

`audit_tet4_family.py` a retraité les observables et résumés J6 disponibles; aucune donnée de champ brute n’a été rechargée et aucun FEM n’a été lancé. L1–L3 partagent le même arbre `src/solveur` (`2e2f4974805099c36179133775e529082454086e`), le générateur de maillage, l’assemblage de charge et l’oracle. Le HEAD complet de L3 diffère de L1/L2 par six fichiers de harnais, post-traitement et performance; aucun changement n’est sous `src/solveur`. L4 J2F est exclu, car son arbre source (`908ef5684ec92854451325bbc3696218864eb9e7`) diffère.

| Niveau | Éléments | Nœuds | Erreur déplacement | Erreur énergie norme | Erreur énergie scalaire | Erreur déformation | Erreur contrainte |
|---|---:|---:|---:|---:|---:|---:|---:|
| L1 | 48 | 27 | 0,6606 | 0,7917 | 0,6268 | 0,7939 | 0,7889 |
| L2 | 384 | 125 | 0,2509 | 0,4701 | 0,2210 | 0,4736 | 0,4658 |
| L3 | 3 072 | 729 | 0,07442 | 0,2481 | 0,06154 | 0,2490 | 0,2469 |

Les différences Q8/Q12 maximales sont de 2,84e−14, 2,39e−13 et 4,90e−13. Les erreurs diminuent aux deux intervalles observés. Les ordres descriptifs déplacement sont 1,397 puis 1,754; énergie norme 0,752 puis 0,922; énergie scalaire 1,504 puis 1,845. Trois niveaux et deux intervalles ne suffisent pas à démontrer un régime asymptotique. Les statuts restent `COMPLETED_UNASSESSED` pour L1/L2 et **FAIL_PRESERVED** pour L3 (erreur scalaire 0,061536 > seuil historique 0,05). Le PASS diagnostique L4 J2F reste distinct.

Un premier appel de validation de l’audit J7 s’est arrêté sur une clé de contrat absente avant de lire les niveaux. Après correction du lecteur de contrat, l’audit de retraitement s’est terminé en 2,814 s. Cette erreur de prévalidation n’a ni touché aux données ni lancé de FEM.

## Contrôles, budgets et ressources

Les trois exécutions FEM ont respecté le contrat de 300 s, 512 MiB RSS souple, quatre processus, 8 MiB de sortie capturée, 128 MiB temporaires et 64 MiB d’archive. Les bibliothèques numériques étaient limitées à un thread. Le RSS et le nombre de processus sont des observations du runner, pas des quotas OS.

| Exécution | État du runner | Durée | Pic RSS | Pic processus | Résultat scientifique |
|---|---|---:|---:|---:|---|
| HEX8 régulier | PASS | 5,684 s | 86 990 848 octets | 1 | FAIL |
| HEX8 quasi dégénéré | PASS | 2,993 s | 86 183 936 octets | 1 | FAIL |
| HEX20 R4 | PASS | 8,457 s | 131 424 256 octets | 3 | critères de calcul atteints; FAIL historique conservé |

Contrôles logiciels exécutés :

- huit tests unitaires J7 de préparation, modèle, géométrie et bornes : 8 PASS avant FEM;
- trois tests ciblés du post-traitement de conditionnement (sous-matrice libre, matrice non définie positive, vecteurs de taille invalide) : 3 PASS;
- compilation `py_compile` des scripts, plugins, contrats Python et tests J7 : PASS;
- validation du policy local et résolution des trois nodeids exacts : PASS;
- les trois nodeids FEM terminent avec `1 passed` chacun; leurs verdicts scientifiques demeurent ceux du tableau ci-dessus;
- l’audit TET4 : 2,814 s, RSS non échantillonné, zéro calcul FEM;
- le contrôle final de diff, chemins publics et empreintes est effectué avant le commit de clôture.

## Fichiers, Git et diffusion

Les contrats, entrées, script d’analyse, états NPZ, résultats JSON, traces de runner expurgées et manifestes SHA sont versionnés sous `research/j7_static_debt/`; la synthèse est ce document. Les traces brutes du runner et le policy contenant les racines locales restent dans `.codex`/le fichier ignoré local. Aucun algorithme du solveur, seuil ou verdict historique n’a été modifié.

La branche reste cumulative depuis J6 et contient les livrables J6 hérités; un PR étroit ne peut donc pas être ouvert directement depuis cette branche sans isoler les commits et dépendances. Après vérification des chemins publics, aucun push ni PR brouillon n’est effectué pour J7. Une extraction dédiée des changements J7 depuis un main contrôlé sera préférable à une publication du cumul J6/J7.

Le contrôle de confidentialité sur tout le diff `origin/main...HEAD` n’a trouvé aucun chemin absolu local ni motif de secret. `git diff --cached --check` a passé pour le commit J7. Le contrôle du diff cumulé signale uniquement des espaces finaux et une ligne vide en fin de `docs/planning/0.3.0-j6-contrats-execution.md`, fichier hérité de J6; il a été laissé intact.

## Décision et limites

**Faits vérifiés :** deux cas globaux HEX8-SRI post-correction ne satisfont pas les critères gelés; R4 reproduit le résidu historique et se place dans un budget numérique propre au cas; la tendance TET4 L1–L3 est descriptive sur une source de solveur commune.

**Hypothèse soutenue mais non démontrée :** le conditionnement binary64 élevé contribue aux résidus HEX8. Les données ne permettent pas d’écarter une contribution de l’assemblage, de l’audit des réactions ou de la définition historique de l’énergie.

**Recommandation :** lancer J8 sur l’isolation HEX8-SRI uniquement. Recalculer indépendamment `Kff u−f`, les réactions et les deux côtés de l’identité énergétique depuis les états bruts; vérifier l’échelle/unité du critère énergétique; puis concevoir au plus une paire de variantes contrôlées pour distinguer le solveur dense, la formulation SRI et la géométrie. Tout nouveau FEM doit recevoir un nodeid, une hypothèse et une tentative nouvelle et séparée. Garder le budget R4 cantonné à ce patch jusqu’à disposer d’autres cas d’amplitude, d’origine et de géométrie.

Les verdicts historiques restent inchangés : WP13-12 `KEEP_EXPERIMENTAL`, le FAIL énergie HEX8 correspondant, R4/J2B `FAIL`, TET4 L3 `FAIL`, et les statuts L4 J2F distincts. J7 ne qualifie ni le solveur dans son ensemble ni les familles HEX8-SRI, HEX20/QUAD8 ou TET4.
