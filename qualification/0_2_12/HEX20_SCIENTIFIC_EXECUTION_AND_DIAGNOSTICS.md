# HEX20 — exécution scientifique et diagnostic

Statut : `NOT_RUN`. Aucun nouveau calcul FEM, assemblage, solveur, réservation ou retry n'a été lancé dans cette mission. Aucune nouvelle valeur numérique ni preuve de PASS scientifique n'est disponible.

La source scientifique est `8f2b02b053af70cbaa23378adbd783dd99669b1b`, fingerprint enregistré `efe44ae1505eb130e15e8ce8c4ae5311b639353b674c94b393d75387655227fb`. Le cas déclaré est un HEX20 à 60 DDL, avec 24 contraintes et 36 DDL libres, limité à une tentative de 300 s et 4096 MiB RSS surveillée. Le ledger diagnostique est absent.

L'inspection statique confirme la capture sidecar avant les assertions : K de production, F, contributions de faces, référence QUAD8 géométrique indépendante, champ affine, K·u, résidus libres/contraints, réactions, énergie, contraintes récupérées et métadonnées. K n'est pas une référence indépendante. Les assertions historiques R4 portent sur déplacement, contraintes récupérées, énergie/travail, résidus, forces et moments, qualité et convergence. Les seuils proposés pour η∞ et les écarts de charges restent observationnels et non approuvés.

L'historique R4 demeure `PYTEST_FAILED / ROOT_CAUSE_INCONCLUSIVE`. Une future exécution diagnostique, sous un nouveau manifeste et une décision Owner valide, doit conserver les observations même en cas d'échec. Un PASS ultérieur n'effacerait pas l'échec historique et ne qualifierait pas le solveur dans son ensemble.
