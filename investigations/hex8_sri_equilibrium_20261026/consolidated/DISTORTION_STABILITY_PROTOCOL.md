# Protocole de distorsion, modes et stabilité

**État : `PREPARED_NOT_AUTHORIZED`.** Les seuls essais de ce document sont des propositions.

## Familles de géométrie

Préparer et comparer sur une grille régulière affine, skew modéré, cisaillement géométrique sévère, warp non affine, éléments étirés (rapport d’aspect ciblé 10/50/100), éléments aplatis quasi dégénérés à Jacobien strictement positif et perturbations internes avec graine publiée. Garder les faces physiques et le chargement cohérents lorsque cela est possible; pour les géométries qui changent le problème, les comparer à leur propre référence, pas à la poutre régulière.

Le module géométrique `experiments/hex8_sri_equilibrium/mesh_quality.py` fournit des maillages structurés reproductibles, les empreintes des coordonnées/connectivités, Jacobiennes au centre et aux 8 points, Jacobien mis à l’échelle `det(J)/∏||J_col||`, rapport des normes directionnelles et non-orthogonalité. Il précise `NOT_CERTIFIED_BETWEEN_SAMPLES`. Ce module ne connaît pas la rigidité ni le solveur.

## Règle d’exclusion

Exclure de tout calcul toute cellule ayant `detJ≤0` ou non fini aux points du centre, Gauss et à une grille de contrôle dense. La positivité aux points échantillonnés n’est pas une preuve continue. Pour les géométries sévères retenues, exiger en plus une borne inférieure certifiée par subdivision/Bernstein ou marquer la classe `POSITIVITY_NOT_CERTIFIED` et ne pas l’utiliser comme preuve robuste. Rapporter `qJ_min`, le rapport d’aspect, l’angle maximal, `detJ_min` et la méthode de certification sans mélanger leur portée.

## Patch test énergétique et objectivité infinitésimale

Cas élémentaires prévus : dilatation uniforme, compression hydrostatique, cisaillement pur, traction uniaxiale, champ affine général et rotation rigide infinitésimale. Pour chacun comparer `ε`, `σ=Cε`, `½ε:C:ε·V`, force nodale et somme des résultantes à une formule analytique. Sur cube affine, la dilatation distingue directement le poids volumique 1/8; l’énergie déviatorique contrôle `Kdev`. Le résidu de rotation infinitésimale doit rester nul à la tolérance pré-gelée. Une rotation finie n’est pas une propriété du modèle linéaire.

Nodeids proposés (pas encore implémentés/inscrits) : `tests/verification/test_hex8_sri_patch_energy.py::test_patch_case[<formulation>-<mode>-nu_<nu>-<geometry>]`. Fixer une tolérance relative `1e−10` pour les contrôles analytiques élémentaires après normalisation par l’échelle d’énergie/force; le seuil reste à valider avant exécution et ne sera pas recalé après résultat. Les cas et budgets sont listés dans `SUPPLEMENTAL_VALIDATION_MATRIX.csv`.

## Spectre et mécanismes

Après autorisation distincte, analyser la rigidité d’un élément libre pour HEX8, SRI historique et corrigé : six vecteurs de corps rigide, rang relatif à `||K||`, plus petite valeur singulière positive, modes supplémentaires, sensibilité aux seuils, et champs des petits modes. Utiliser des matrices mises à l’échelle sans dimension avant d’appliquer un seuil relatif. Distinguer mouvement rigide exact, petit mode physique, perte de précision par conditionnement et hourglass par visualisation/énergie nulle du mode. Le nodeid proposé est `tests/verification/test_hex8_sri_spectrum.py::test_element_spectrum[<formulation>-nu_<nu>-<geometry>]`; il est différé jusqu’à une autorisation d’eigensolve. Aucun résultat spectral nouveau n’est livré ici.

## Seuils, arrêt et priorité

Les cas affines et patch sont MUST pour toute nouvelle revue scientifique. Distorsions modérées/warp sont SHOULD; cisaillement extrême, graines multiples et seuils très aplatis sont DEFERRED jusqu’à la mise en place d’un certificat Jacobien et d’une référence. Un non-fini, un Jacobien non positif/non certifiable, un mode supplémentaire au seuil gelé, un échec d’équilibre ou un dépassement budgétaire arrête ce cas; aucun retry. Les seuils et catégories sont à geler par Owner avant exécution.
