# WP13-RBE — Rapport de qualification bornée RBE2/RBE3/MPC

Date : 2026-10-21
Branche : codex/wp13-rbe-vnv-20261021
HEAD de départ : d68554d8ca17fe4915fa8c761fb13051327a93ce
Dépôt : https://github.com/emptiesvoid-cloud/QF_solver.git
Rapport d’audit antérieur conservé : docs/elements/rbe2_rbe3_audit_vv.md, SHA-256 649c84dd94b05e0a107979131e9f2fcfd2f26b96bcefce1cc6c1bc92d17b0c74.

## Résultat exécutif

La campagne WP13 a exécuté les sept modules statiques ciblés : **100 PASS, 0 FAIL, 0 SKIP**, en 2,90 s rapportées par pytest (5,13 s pour la commande et son environnement). Les 89 cas du rapport précédent ont été rejoués et les 11 cas supplémentaires ont étendu les références RBE2, RBE3 et le contrôle MPC-aware à la limite de 180 DDL. Ces résultats ne changent aucun label de maturité public.

La recommandation pour décision du propriétaire est QUALIFIED_BOUNDED pour RBE2 linéaire statique et RBE3 rigid_body_projection dans le domaine étroit ci-dessous. La réduction MPC peut recevoir la même recommandation pour les systèmes linéaires statiques acycliques vérifiés. Le diagnostic de rang reste VERIFIED_BOUNDED seulement : son seuil absolu conservateur et son plafond de 180 DDL empêchent de le présenter comme une décision de rang universelle. Le mode RBE3 weighted demeure une interpolation algébrique limitée, sans garantie de conservation du moment.

La revue d’un second agent n’a relevé aucun P0/P1/P2 ouvert après la correction d’un finding P2. Cette revue était source-only; elle n’a pas exécuté les tests. La corrélation Code_Aster n’a pas pu être rejouée, car le moteur Docker local n’était pas disponible. Aucun label de production ou de qualification n’a été promu.

## Identité et périmètre Git

Le dépôt complet est le clone QF Solver situé sous solveur/tmp/wpc01-m4-kkt-full-capture; le dépôt parent SAFRAN/solveur est resté inchangé. Une branche WP13 dédiée a été créée depuis le HEAD de départ. Les changements de départ déjà présents ont été préservés; les modifications ajoutées pour cette campagne sont limitées à la vérification RBE/MPC et à sa documentation. Le rapport historique d’audit, non suivi au début de cette campagne, reste byte-for-byte inchangé.

Fichiers livrés :

- src/solveur/core/rbe.py
- src/solveur/core/constraints.py
- src/solveur/io/constraint_schema.py
- src/solveur/mesh/validation.py
- src/solveur/mesh/validation_rank.py
- tests/unit/test_rbe_links.py
- tests/unit/test_mpc_reduction.py
- tests/unit/test_mesh_validation_edge_contracts.py
- docs/elements/liaisons_mpc_rbe.md
- docs/elements/rbe2_rbe3_audit_vv.md — audit initial conservé
- qualification/0_2_12/wp13_rbe_vnv_qualification_report.md

Aucun changement n’a été fait à la résolution modale, harmonique, Newmark, non linéaire ou contact, ni à une qualification historique.

## Contrat mathématique vérifié

### RBE2

Pour r = x_s - x_m, les lignes MPC imposent

    u_s - u_m - theta_m × r = 0.

Les signes des blocs de rotation reproduisent donc u_s = u_m + theta_m × r. tie_rotations=True ajoute séparément theta_s=theta_m; ce n’est pas une conséquence du bras rigide translationnel. Les tests couvrent deux bras 3D non nuls, les six composantes, un mouvement rigide combiné et une résolution statique par ressorts. La référence statique est condensée indépendamment avec les matrices de bras et une raideur nodale diagonale définies dans le test. Les forces et moments externes ferment avec les réactions de ressort.

Les rotations auxiliaires d’un nœud solide peuvent être nécessaires au maître du RBE2 mais n’ont pas de raideur élémentaire du solide. Pour un esclave solide, tie_rotations ajoute des coordonnées sans raideur propre : cette égalité doit être mécaniquement intentionnelle. Le test d’activation de DDL ne qualifie pas toutes les associations de familles d’éléments.

### RBE3 rigid_body_projection

Pour les translations des nœuds indépendants, A_i=[I,-S(r_i)] et la projection pondérée est H=(AᵀWA)⁻¹AᵀW lorsque la géométrie porte les six mouvements rigides. Le code ne forme pas les équations normales : il centre le nuage au centroïde pondéré, met les colonnes rotationnelles à l’échelle, puis résout le problème pondéré par SVD. Il refuse si sigma_min/sigma_max ≤ 1e-12, les poids sont strictement positifs et le modèle possède les six DDL de référence.

L’oracle de test construit un autre opérateur géométrique à partir des produits vectoriels, puis appelle numpy.linalg.lstsq sur le problème pondéré. Les assertions contrôlent l’accord des coefficients, HA=I, la reproduction des six modes et le torseur obtenu par Hᵀp. Des configurations asymétriques et tétraédriques symétriques sont couvertes. Les poids communs sont testés de 1e-200 à 1e200; les coordonnées de 1e-8 à 1e8; une translation d’origine de l’ordre de 1e6 est aussi contrôlée.

Les diagnostics numériques indépendants consignés par la campagne précédente restent : erreur max de H contre la référence LS 7.77e-16, erreur max de HA-I 1.78e-15, erreur de résultante 7.55e-15, erreur de moment 1.15e-14, et écarts d’invariance de translation et de rotation respectivement 1.53e-15 et 2.59e-15. Les assertions ajoutées dans cette campagne confirment les cas de changement d’origine et le tétraèdre, mais n’impriment pas de nouveaux maxima; ces métriques ne sont donc pas présentées comme des mesures du run de 100 cas.

### RBE3 weighted

Le mode impose une relation pondérée par composante et normalise les poids par leur somme, sans ajouter de raideur aux nœuds indépendants. La normalisation est stable par échelle commune et une somme relativement annulée est refusée. Le mode autorise les poids signés si la somme normalisée est admissible, ce qui peut produire une extrapolation. Il n’exprime pas un bras rigide 3D et ne garantit pas la conservation du moment. Sa vérification ne justifie pas un usage comme distribution générale de charge structurelle.

### Réduction MPC et réactions

La voie nominale utilise u=u₀+Tz, K_r=TᵀKT et f_r=Tᵀ(f-Ku₀). La réduction conserve la symétrie pour K symétrique et construit les coefficients par substitution creuse. Les tests comparent la solution à multiplicateurs de Lagrange sur de petits systèmes, vérifient une valeur affine non nulle, l’invariance à une échelle commune des lignes, conservent des petits coefficients non nuls et refusent cycles et conflits. L’oracle Lagrange partage les équations MPC générées; il vérifie l’algèbre de réduction indépendamment mais ne remplace pas l’oracle cinématique RBE.

Après résolution, les multiplicateurs sont reconstruits au moindre carré avec la convention K u - f + Cᵀlambda = 0. Si les contraintes sont redondantes, les multiplicateurs peuvent ne pas être uniques, même lorsque la résultante physique est unique. LSMR fournit alors une représentation de norme minimale.

Le diagnostic de rang applique maintenant la réduction MPC avant le contrôle spectral pour les modèles d’au plus 180 DDL actifs. La vérification à 180 DDL utilise une raideur identité injectée par le test, ce qui isole le réducteur et le calcul de rang mais ne constitue pas un benchmark d’assemblage FEM à cette taille. Le cas 181 DDL conserve le refus précoce. Les supports heuristiques restent actifs si l’analyse réduite n’a pas abouti et un avertissement explicite est émis; ce point ferme le finding P2 du reviewer.

Limites du diagnostic : la matrice réduite est densifiée; le seuil est max(1e-10 * max(max(abs(eigenvalues)), 1), 1e-12). Son plancher absolu peut être conservateur pour des rigidités exprimées à une très petite échelle. Au-delà de 180 DDL ou en cas d’échec d’assemblage/réduction, le rang reste non vérifié et un avertissement explicite est requis.

## V&V exécutée

Commande exacte exécutée depuis la racine du clone complet :

    $env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:QF_SOLVER_RUN_EXTERNAL='0'; python -m pytest -q tests/unit/test_rbe_links.py tests/unit/test_mpc_reduction.py tests/unit/test_backend_edge_matrix_contracts.py tests/unit/test_mesh_validation.py tests/unit/test_mesh_validation_edge_contracts.py tests/unit/test_code_aster_rbe.py tests/unit/test_wp13_02_mixed_dynamic_validation.py

Sortie pytest observée :

    100 passed in 2.90s

Durée totale rapportée par le lanceur de commande : 5,13 s. La configuration a forcé OpenBLAS, MKL et OpenMP à un thread et QF_SOLVER_RUN_EXTERNAL=0. Il n’y a eu ni native FEM externe, ni résolution Code_Aster, ni test parallèle. Les modules couvrent notamment RBE2/RBE3, la réduction MPC, la validation de maillage et les refus dynamiques bornés. Ils ne couvrent pas toutes les combinaisons possibles de familles, cycles d’équations arbitraires ou grands modèles.

La campagne antérieure avait produit 89 PASS sur les mêmes modules. Les 11 cas ajoutés couvrent poids invalides, extrapolation weighted, invariance d’origine, RBE2 multi-bras et torseur avec référence condensée, projection RBE3 tétraédrique, robustesse d’échelle, rang MPC à 180 DDL et conservation des avertissements si le rang n’est pas disponible. Le résultat 100 PASS est le résultat actuel; 89 PASS reste l’évidence historique et n’est pas réécrit.

Les échecs intermédiaires conservés dans le rapport historique incluent des oracles RBE2 mal construits, un cas de rotation non couplée par le bras, une erreur d’indentation, puis un défaut réel où un poids brut négatif pouvait devenir positif après normalisation. Le défaut de code a été corrigé en validant la positivité avant normalisation. Pendant cette extension, un test de message d’avertissement a d’abord échoué parce que son oracle attendait “rank-check did not complete” alors que la formulation réelle disait “reduced-rank check did not complete”; seul le texte attendu a été corrigé. Une exécution ciblée ultérieure a passé 56 tests, puis le run final a passé 100 tests. Aucun seuil scientifique n’a été élargi pour obtenir un PASS.

Contrôles statiques effectués après les derniers changements : AST Python des huit fichiers Python modifiés (AST_OK 8), ruff check sans finding, et git diff --check sans erreur.

## Corrélation externe

La référence existante est Code_Aster 18.1.0 dans l’image épinglée simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435. Son cas historique est un bras de 2 m, six contraintes LIAISON_DDL, une force FX=20 N et une réponse UX=0.02 m; l’écart relatif historique documenté est 3.47e-18. Le résultat ne couvre qu’un cas RBE2 et ne vérifie pas indépendamment la réaction duale RBE.

La disponibilité du moteur Docker a été vérifiée par inspection de l’image épinglée. Docker Desktop ne pouvait joindre npipe:////./pipe/dockerDesktopLinuxEngine (named pipe absent). Le script de campagne n’a pas été lancé; il aurait démarré un processus externe. Résultat : **EXTERNAL_CORRELATION_NOT_RUN** dans cette campagne. Le chiffre historique reste identifié comme historique, pas comme résultat rejoué. Aucune référence externe RBE3 disponible n’a été trouvée dans cet environnement.

## Revue indépendante et constats

Un reviewer séparé a procédé à une revue source-only en deux lectures. La première a relevé un P2 : si le calcul du rang réduit échouait, les heuristiques de support pouvaient être supprimées sans avertissement équivalent. Le code conserve désormais les avertissements composants lorsque checked=False et ajoute une raison explicite. Le reviewer a relu cette correction et conclu qu’aucun finding P0/P1/P2 ne reste dans les changements examinés. Il a aussi vérifié les signes RBE2 et l’identité de projection tétraédrique. Le reviewer n’a pas exécuté les tests; cette conclusion n’est donc pas une revue numérique indépendante.

Findings résiduels connus (P2) :

- Le critère spectral de rang possède un plancher absolu et peut être conservateur à très petite échelle de raideur.
- Le coût/mémoire et le remplissage de la transformation T ne sont pas caractérisés au-delà des petits systèmes; le diagnostic dense s’arrête à 180 DDL.
- La détection actuelle refuse les cycles, DDL dépendants répétés et certains conflits, mais n’effectue pas une analyse générale de rang de toutes lignes MPC redondantes indépendamment du choix du DDL dépendant.
- La corrélation RBE3 externe, la convergence au raffinement et le transfert vers des structures déformables complexes ne sont pas établis.
- Les modes dynamiques, non linéaires et contact restent refusés ou hors scope.

Aucun P0 ou P1 ouvert n’a été retenu dans le domaine exécuté. Les anciens P1 de stabilité du rang RBE3 et P2 d’élagage absolu MPC / rang sans prise en compte des MPC ont reçu des corrections et des tests ciblés.

## Décisions de maturité proposées au propriétaire

| Candidat | Domaine exactement étayé | État de preuve | Recommandation |
|---|---|---|---|
| RBE2_LINEAR_STATIC | Bras 3D petit déplacement en statique linéaire; esclaves et rotations seulement selon DDL activés; tie_rotations uniquement si physiquement voulu; relations MPC acycliques vérifiables | Rigid-body cinématique, multi-bras, référence condensée ressort, réactions/torseur; corrélation Code_Aster historique d’un seul bras, non rejouée | **Recommander QUALIFIED_BOUNDED** après décision Owner, avec réserve explicite que la corrélation externe n’a pas été rejouée dans cette campagne |
| RBE3_RIGID_BODY_PROJECTION_LINEAR_STATIC | Tous les 6 DDL de référence; translations indépendantes; poids strictement positifs; géométrie 3D de rang six avec sigma_min/sigma_max > 1e-12; réduction MPC linéaire statique; rang diagnostiqué seulement jusqu’à 180 DDL | Oracle pondéré lstsq, six modes symétriques/asymétriques, échelles, origine, géométries dégénérées, wrench et statique limitée | **Recommander QUALIFIED_BOUNDED** après décision Owner; pas d’équivalence générale Nastran ni de corrélation externe RBE3 |
| RBE3_WEIGHTED_LIMITED | Interpolation/extrapolation algébrique pondérée par composante; somme normalisée non quasi nulle; aucun engagement de moment spatial | Normalisation stable, entrée JSON et coefficient pondéré vérifiés; pas un transfert spatial de charge général | **Rester VERIFIED_BOUNDED**, pas de qualification comme distributeur structurel 3D |
| MPC_REDUCTION | Linéaire statique; transformation affine; dépendances uniques et acycliques; petites références comparées à Lagrange; contraintes incompatibles/redondances simples refusées | 100 tests ciblés, oracle KKT petit, offsets affines, petits coefficients, cycles/conflits et RBE | **Recommander QUALIFIED_BOUNDED** après décision Owner pour ce domaine |
| MPC_RANK_DIAGNOSTIC | Diagnostic dense sur raideur réduite et au plus 180 DDL actifs; avertissement conservateur, non verdict universel | Réduction MPC dans le test RBE2 et cas isolé à 180 DDL; refus explicite au-delà et avertissement si non calculé | **VERIFIED_BOUNDED seulement** jusqu’à révision/validation du seuil spectral à différentes échelles de raideur |

Cette recommandation ne constitue pas un changement de maturité. La décision et la mise à jour du registre public demeurent réservées au propriétaire.

## Empreintes des livrables

Les empreintes SHA-256 ci-dessous correspondent aux octets examinés après le run de 100 tests et avant le commit documentaire :

| Fichier | SHA-256 |
|---|---|
| src/solveur/core/rbe.py | 3031c1c106c220e96c8b2e16dd0fe57a5efe028792891962867b8351ec95793c |
| src/solveur/core/constraints.py | 428f9d2bd907859e37a2dc8ea7e86102d804c1ec61c3473051cf85ab4fca9b41 |
| src/solveur/io/constraint_schema.py | 08735d9c518097053597967dabc9f2aa2630a5b836d9daa1931502332ea50a6a |
| src/solveur/mesh/validation.py | 2f80e5f2f17f5138ac875bc32d9e46ad416a9941b11ba13688188ec23b4642b6 |
| src/solveur/mesh/validation_rank.py | b286c05fa98dd0d1eb6c14e6b6e51fa567c25b01c61838c870874d6bdb71ee7b |
| tests/unit/test_rbe_links.py | d730601b7d7c284273537cb987d5518d76334b81324adf58451833344428d815 |
| tests/unit/test_mpc_reduction.py | c6d2c0c5685ed9d614c4ae696db4fffe322409904e7fa19e9abff859880ea009 |
| tests/unit/test_mesh_validation_edge_contracts.py | aef73bb9dbc1c1996bd81caedafbf070028c5c895b589f9f3b5f9a4807126557 |
| docs/elements/liaisons_mpc_rbe.md | f7b762875604149a4a9f37b6beee3c038030031b0cb8ce6788a6da37c2b722d1 |
| docs/elements/rbe2_rbe3_audit_vv.md | 649c84dd94b05e0a107979131e9f2fcfd2f26b96bcefce1cc6c1bc92d17b0c74 |

Le hash du présent rapport est calculé après sa création et reporté dans la réponse de campagne. Le SHA Git de l’arbre final est également communiqué après commit; il ne peut pas être incorporé de manière non circulaire dans ce fichier lui-même.

## Conclusion

La preuve couvre une enveloppe bornée de statique linéaire, pas la qualité générale de toutes les compositions RBE/MPC ni la fidélité complète à Nastran. Le résultat de 100 PASS, la comparaison LS indépendante de RBE3, la référence condensée RBE2 et la revue source indépendante justifient les recommandations de maturité ci-dessus. Ils ne remplacent pas la décision Owner, une corrélation externe rejouée, ni la qualification des autres modes de calcul.
