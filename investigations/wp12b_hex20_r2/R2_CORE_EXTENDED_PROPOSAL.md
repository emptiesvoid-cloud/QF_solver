# HEX20 R2 — proposition CORE / EXTENDED

Statut : proposition scientifique, **aucune catégorie n'est une décision Owner**, aucune nouvelle tentative n'est autorisée. La matrice des 14 candidats est dans `R2_NODEID_MATRIX_PRELIMINARY_NOT_REGISTERED.json`. Les 13 cas préparés ne sont pas reclassés comme PASS et aucune priorité MUST préexistante n'est supposée levée.

## CORE proposé

1. Les cinq tests purement mathématiques `tests/unit/test_wp12b_hex20_quadrature_math.py` vérifient les moments Gauss QUAD4/QUAD8 et les intégrales nodales de référence; ils ne font ni assemblage, ni solve FEM. Ils ont déjà passé sur le correctif.
2. Une seule tentative instrumentée du nodeid exact `tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual`, scope R2, 60 DDL (24 fixés), budget proposé 300 s, RSS surveillée 4096 MiB, une tentative. Elle conserve les assertions historiques R4 et archive K, F, réactions, contraintes, énergie et les cinq charges de face avant assertions. Ces cinq faces exercent les directions ±Y, ±Z et +X sur le cube R1 et sont comparées à l'oracle QUAD8 géométrique indépendant.

La source prospective `research/wp12b-hex20-r2-prospective` ajoute pour R2 seulement, **après l'écriture de la preuve**, une assertion par face sur les 60 composantes : `rtol=1e-12`, `atol=1e-6 N`, valeurs antérieurement proposées dans le sidecar R1. Cette nouvelle assertion et son statut de critère bloquant sont proposés pour décision Owner avant exécution. Le chemin R1 et les seuils historiques ne sont pas assouplis. Le résidu affine et la comparaison `K u_affine` restent des mesures descriptives.

## EXTENDED à examiner avec l'Owner

Les 13 cas préparés comprennent six tractions planes, six pressions planes et un contrôle QUAD4/TRI3. Ils demeurent `PREPARED_NOT_AUTHORIZED`, non inscrits et marqués skip. La face 5 en traction de production, la pression, la traction en repère local et les géométries courbes ne sont pas démontrées par le CORE. Aucun test local ou courbe n'est actuellement préparé. Leur priorité et leur éventuel statut MUST exigent une disposition Owner fondée sur la politique applicable; la présente proposition ne les supprime ni ne les déclare réussis.

## Préconditions non satisfaites

Le contrôleur doit encore inscrire le nodeid CORE dans un mandat R2 distinct, vérifier le ledger R1 immuable, assurer préflight collect-only, manifeste, décision, sidecar et réservation atomique. Le validateur de prédécesseur préparé dans cette branche n'est pas encore raccordé au runner. Après intégration revue et désignation du contrôleur, recalculer les fingerprints et obtenir les SHA définitifs des pièces non autorisées avant la revue Owner unique. Aucun préflight officiel ni manifeste R2 n'existe à ce stade.
