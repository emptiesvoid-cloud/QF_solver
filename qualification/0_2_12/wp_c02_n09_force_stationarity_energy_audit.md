# WP-C02-N09 — Audit forces, stationnarité et énergie

## Résumé et statut

Le finding N08 est confirmé comme une erreur de post-traitement, et non comme un défaut démontré du noyau FEM. Le solveur exporte `internal_force = K u + Cᵀ μ = K u − P`, où `P` est la force physique de compression appliquée au corps. Le collecteur N08 lui retranchait encore la charge extérieure **et** une seconde contribution `P`. Il calculait aussi `½ uᵀ internal_force` puis le comparait à l’énergie élastique quadraturée, alors que le vecteur contient le terme de contact.

Le collecteur N09 est corrigé sans modification des équations ou du solveur. Les tests analytiques indépendants ciblés passent. Les valeurs physiques de stationnarité M4/M5 ne sont pas recalculables depuis N08, car les vecteurs bruts de production ne sont pas archivés. L’acceptation effective des critères sur M4/M5 exige une nouvelle acquisition sous autorisation N10.

Statuts conservés : `N06_M4=FAIL`, `N06_M5=FAIL`, `N08_M4=FAIL`, `N08_M5=FAIL`, `WP_C02_SPATIAL_CONVERGENCE=NOT_ACQUIRED`. Aucun RUN FEM n’a été lancé dans N09.

## Identités et périmètre

- Base : N07 commit `d517ddc53a871e3032ac82d2712076693e45220b`, tree `daece63b182e733ea19183febbfb4a61827140bc`.
- Candidat isolé : worktree `wp-c02-n09-remediation`, branche `emptiesvoids-cloud/wp-c02-n09-remediation`.
- Archive source N08 : `wp-c02-ar-native-n07-m4m5-20261023-01`, 539 fichiers, inventaire et hashes validés par rejeu hors ligne. Manifeste N07 SHA-256 `1618fe6f3cd29cd9f1a3005a45f92df7937c26cdd6ce94bf785261d65149309a`.
- Seuil stationnarité de production : `1e-6 N`; cohérence énergie matrice/quadrature : `1e-10 J`, sans changement.
- Sources approuvées inchangées : plan AR SHA-256 `fa3806c842acefbe707499ffdec9f703bcedb5031962594df4c5293d0fbe6cfc`; protocole AR SHA-256 `bf7535eb4028715071744a2b8cc119b828f0eae2129a8f6b05e588872fcbf58d`; approbation N03 `wp_c02_n03_ar_prospective_criteria_approval.json`.

## Provenance mécanique des vecteurs

| Grandeur | Définition de production | Usage correct |
|---|---|---|
| Force élastique | `K u`, assemblée à partir de la rigidité TET4 | Contribue à l’énergie élastique `U=½uᵀKu`. |
| Multiplicateur selle brut | `μ`, issu de `[K Cᵀ; C 0][u;μ]=[f;−g0]` | Signe algébrique opposé à la compression physique. |
| Contact physique sur l’esclave | `P=Cᵀp`, avec `p=−μ≥0`, normale AR `+Z` | Force de compression `+p n`; l’action opposée est portée par le maître fixe. |
| `internal_force` exportée | `K u + Cᵀμ = K u−P` | Force interne totale, contact déjà inclus. |
| Charge extérieure | `f` | Reste séparée de `internal_force`. |
| Résidu | `r=internal_force−f` | Stationnarité testée sur les seuls DDL libres. |
| Réaction d’appui | `r` aux DDL prescrits | Réaction de l’appui sur le corps; elle n’est pas incluse dans le test libre. |
| Oracle QP indépendant | `K_ind u−f−Gᵀp` | Équation KKT distincte, calculée séparément; ne pas soustraire `Gᵀp` une seconde fois au vecteur total production. |

Les sources confirment ces définitions : `src/solveur/contact/solver.py` construit le vecteur frictionless par `stiffness @ displacement + contact_force`; `src/solveur/contact/support.py` convertit la pression physique en `p=−μ`; `src/solveur/core/solvers/static.py` forme `residual=internal−loads`; `src/solveur/core/audit.py` décrit le même signe et exporte les réactions sur les DDL fixes.

## Correctif prospectif

Le calcul de stationnarité production est maintenant `|| (internal_force−external_force)[free] ||∞`, à partir du vecteur d’audit production. Il ne retranche aucune pression ou force de contact supplémentaire. Le calcul QP indépendant garde sa propre formule et ses propres multiplicateurs. Les résultantes, moments, réactions et KKT restent séparés; aucune compensation entre métriques n’est introduite. Les prochains records conservent `internal_force` et le résidu production dès l’état `SOLVER_COMPLETED_RAW_FIELDS`, avant l’oracle QP et les intégrations quadraturées, de sorte qu’un échec ultérieur ne supprime pas ces preuves.

Pour l’énergie :

`internal_force = K u−P`, `C_contact=uᵀP`, et `U_old=½uᵀinternal_force = U_el−½C_contact`.

Le calcul N09 reconstruit donc `K u=internal_force+P`, puis `U_el=½uᵀ(internal_force+P)`. `P` est assemblé avec la force physique positive `p n` déjà utilisée pour les bilans. La comparaison porte sur la même énergie de déformation que l’intégration quadraturée TET4. Le facteur `½` reste inchangé. Les seuils AR restent inchangés. L’identité `U_el=U_old+½C_contact` est une réécriture algébrique de `½uᵀKu`; elle n’affirme aucun travail de trajet par le contact.

### Définitions énergétiques distinctes

- Énergie de déformation élastique : `U_el=½uᵀKu`, également évaluée par `½∫εᵀDε dV` en quadrature TET4.
- Travail des charges extérieures à l’état final : `W_ext=fᵀu` pour des charges mortes. Le travail cumulé sur un trajet quasi-statique est `W_trajet=∫₀¹ f(α)ᵀ(du/dα)dα`. Il se réduit à `½fᵀu` seulement si `f(α)=αf` et `u(α)=αu`, avec contraintes homogènes et sans changement de régime. Ici le jeu initial est non nul et le contact actif peut évoluer; aucun travail de trajet n’est évalué depuis le seul état final.
- Produit forces de contact finales–déplacement depuis la référence : `C_contact=uᵀP`, ici `Σ p_i u_{z,i}`. Il est négatif pour la compression AR (+Z normal, déplacement comprimant vers −Z). C’est le diagnostic d’identité d’extrémité nommé `contact_work`; aucun travail physique intégré sur le trajet `∫P(α)ᵀdu` n’est inféré. Ce produit n’est pas une énergie élastique stockée.
- Potentiel total pour charges mortes : `Π=U_el−fᵀu`, minimisé sous `g=g0+Cu≥0`. Le Lagrangien de la contrainte unilatérale est `L=Π−pᵀg`, avec `p≥0`; il donne `Ku−f−Cᵀp=0`, équivalent à la stationnarité de production `internal_force−f=Ku−P−f=0`. À l’équilibre complémentaire `pᵀg=0`, le terme du Lagrangien est nul sur les contraintes satisfaites. Il ne faut ni ajouter `½uᵀP` à `U_el`, ni comparer un potentiel ou un travail extérieur à une énergie de déformation.
- L’énergie de matrice et l’énergie quadraturée comparées par le gate AR sont toutes deux `U_el`; le travail de contact et le travail extérieur restent des diagnostics distincts.

## Tests analytiques indépendants

`tests/unit/test_wpc02_ar_native_collection_reporting.py` ajoute des cas avec une matrice SPD et un déplacement spécifiés indépendamment du collecteur. La référence élastique est calculée explicitement par `K@u`; les données couvrent compression active, nœud ouvert, mélange actif/ouvert et DDL contraint. Les tests vérifient :

- stationnarité totale sur les DDL libres et masquage des réactions prescrites;
- échec explicite du double comptage et de l’inversion de signe;
- récupération indépendante de `K u` et énergie `½uᵀKu`;
- échec de l’énergie historique qui omet la compensation de contact;
- limite sans contact, formes incompatibles et valeurs NaN/Inf;
- action/réaction, résultantes, moments et conventions de pression via les tests existants.

Le jeu ciblé a donné **49 PASS**. Une fixture analytique de barre compare aussi l’énergie récupérée à une intégration de Gauss indépendante de deux points; la variante qui omet le travail de contact échoue. `py_compile` des sources touchées a réussi. Aucun test FEM, assemblage ou solveur n’a été déclenché.

## Vérification historique N08

Les fichiers sources de l’archive ne sont pas modifiés. Les anciennes mesures N08 restent FAIL et ne sont pas réinterprétées comme des PASS. Le détail reproductible est dans `wp_c02_n09_offline_diagnostic.md` et dans `wpc02_n09_offline_diagnostic.json`. Les anciens nombres de stationnarité (17,8572 N M4; 12,9099 N M5) sont issus de la soustraction contact en double et ne sont pas des mesures valides de la formule production correcte. En l’absence du vecteur production brut, la mesure correcte demeure `NOT_EVALUATED` hors ligne.

## Critères et conclusions N09

Tous les critères prospectifs N03 (erreurs déplacement/pression, énergie, front par rangée M2–M5, classification, KKT, équilibre, travail et tolérances numériques) sont conservés. Les fichiers approuvés et leurs empreintes n’ont pas changé. Les traces de front AQ M2/M3 sont marquées `NOT_RECORDED_IN_AQ_SUMMARY`; les archives examinées ne permettent pas de les reconstruire sans ambiguïté. Leur gate reste `NOT_ACQUIRED`.

Findings avant revue indépendante :

- **P0 :** aucun identifié.
- **P1 :** défaut de formule N08 traité dans le collecteur; confirmation numérique sur une nouvelle sortie de production reportée à N10.
- **P2 :** les données brutes de force/résidu et les traces de front M2/M3 manquent des archives historiques. L’archive N08 ne permet donc ni stationnarité production hors ligne, ni validation complète M2–M5. Le nouveau collecteur conserve ces vecteurs au prochain RUN autorisé; le présent N09 ne génère aucune nouvelle mesure FEM.

La campagne N09 ne qualifie pas le solveur, n’établit pas la convergence spatiale, et n’autorise pas N10. Aucun manifeste exécutable N09 ne doit être généré avant revue indépendante favorable et contrôles finaux du gel. Le RUN FEM natif, Docker, merge, release et promotion restent non autorisés.
