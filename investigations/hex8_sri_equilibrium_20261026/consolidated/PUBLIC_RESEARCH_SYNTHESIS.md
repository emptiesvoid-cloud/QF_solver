# Synthèse publique — recherche HEX8-SRI

La formulation HEX8-SRI sépare les composantes déviatorique et volumique de la rigidité d’un solide isotrope : la première est intégrée sur huit points de Gauss, la seconde au centre de l’élément. Une revue a trouvé que l’expression historique au centre omettait le poids de Gauss `8` associé au domaine de référence `[-1,1]³`. Sur un cube affine et un champ de déformation constante, une référence analytique montre que l’omission divise l’énergie volumique par huit; le correctif rétablit exactement cette intégrale.

Une campagne bornée de six calculs a comparé HEX8 standard, SRI historique et SRI corrigé sur une poutre régulière et un seul maillage grossier, pour deux coefficients de Poisson. Les résultats montrent que les formulations donnent des déplacements différents, particulièrement près de l’incompressibilité, et que le conditionnement du SRI corrigé devient élevé dans ce cas. Ces observations sont propres à cette configuration.

La campagne ne démontre pas une convergence spatiale, une robustesse générale aux maillages distordus, ni une précision supérieure sur une référence 3D indépendante. La formulation reste expérimentale et n’est pas proposée comme capacité de production. Les travaux futurs doivent combiner raffinement spatial, essais énergétiques, géométries certifiées et référence numérique indépendante.

Pour le contexte mathématique sur l’intégration sélective et la stabilité HEX8, voir le [manuel théorique Sierra/SD de Sandia](https://www.sandia.gov/app/uploads/sites/315/2025/07/SD_Theory_5_18.pdf), Hughes (1980, [DOI](https://doi.org/10.1002/nme.1620150914)) et Belytschko & Bindeman (1993, [DOI](https://doi.org/10.1016/0045-7825(93)90124-G)). Ces travaux ne qualifient pas l’implémentation QF Solver.
