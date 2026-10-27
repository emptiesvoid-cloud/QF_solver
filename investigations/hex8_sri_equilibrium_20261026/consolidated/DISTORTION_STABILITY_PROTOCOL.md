# Protocole de distorsion, modes et stabilité

**État : `PREPARED_NOT_AUTHORIZED`.** Les seuls essais de ce document sont des propositions.

## Familles de géométrie

Préparer et comparer sur une grille régulière affine, skew modéré, cisaillement géométrique sévère, warp non affine, éléments étirés (rapport d’aspect ciblé 10/50/100), éléments aplatis quasi dégénérés à Jacobien strictement positif et perturbations internes avec graine publiée. Garder les faces physiques et le chargement cohérents lorsque cela est possible; pour les géométries qui changent le problème, les comparer à leur propre référence, pas à la poutre régulière.

Le module géométrique `experiments/hex8_sri_equilibrium/mesh_quality.py` fournit des maillages structurés reproductibles, les empreintes des coordonnées/connectivités, Jacobiennes au centre et aux 8 points, Jacobien mis à l’échelle `det(J)/∏||J_col||`, rapport des normes directionnelles et non-orthogonalité. Il précise `NOT_CERTIFIED_BETWEEN_SAMPLES`. Ce module ne connaît pas la rigidité ni le solveur.

### Écran géométrique purement cinématique — 2026-10-27

Les sept familles prévues ont été générées sur `4×2×2` et évaluées par le module de métriques seul. Cette opération ne construit aucune matrice `K`, ne fait aucun assemblage ni solve. Tous les cas ci-dessous sont `SAMPLED_POSITIVE` aux 9 points par élément, mais aucun n’est certifié positif entre les points. Les empreintes figent les coordonnées/connectivités; les grandeurs ne mesurent pas la stabilité mécanique.

| Famille | `min detJ` m³ | `min scaled J` | rapport directionnel max | cosinus non-orthogonalité max | SHA-256 géométrie |
|---|---:|---:|---:|---:|---|
| regular | 0.15625 | 1.000000 | 10.0000 | ≈0 | `2a258b9fca9edd610b3b21e039266770b2e9b021788eb1f23ec3ae7625d2bfc8` |
| moderate_skew | 0.154904307 | 0.981837 | 9.99982 | 0.187978 | `453dfca4cc3824c36d38c035319ed5f0eeff0ac4d6eceb695a4606f018b9732a` |
| severe_shear | 0.15625 | 0.250187 | 10.0000 | 0.965484 | `c0d9114328996330c4432f00372e6a94317ab5a4bc4e331bc5b6d02fae89e18e` |
| warped | 0.155589970 | 0.991151 | 9.99920 | 0.130980 | `8ca1e7d2c857e48b85387ac4523442410a7eb86c90a2d36f4c22e378905b80de` |
| seeded, seed `20261026` | 0.152876691 | 0.999445 | 10.1219 | 0.0232357 | `e87661a0c5fccaa60ef08b4af24b967ee9949cf8555192206782bd38b3dc78fb` |
| stretched, `20×1×0.1 m` | 0.015625 | 1.000000 | 100.000 | ≈0 | `82b9ac6ec2e5d1c14f90b6bfbbf784f918e6c8eefce29e395631f689a8612c36` |
| near-degenerate `z×0.05` | 0.0078125 | 1.000000 | 200.000 | ≈0 | `86acd1764ea3753b6d247d5d2f4eba416378fdd632aca48afd936b7346600ff4` |

Ces valeurs montrent une limite de la qualité normalisée : `scaled J=1` dans les deux cas orthogonaux très étirés, alors que le rapport directionnel monte à 100 et 200. Il faut donc garder simultanément `detJ`, Jacobien normalisé, rapport d’aspect et non-orthogonalité. Le cisaillement sévère reste positif aux points inspectés mais son Jacobien normalisé chute à `0.2502` et la non-orthogonalité atteint `0.9655`; aucune réponse mécanique ne peut être inférée sans calcul autorisé. L’inversion de contrôle est bien signalée `SAMPLED_INVALID` par les tests synthétiques.

## Règle d’exclusion

Exclure de tout calcul toute cellule ayant `detJ≤0` ou non fini aux points du centre, Gauss et à une grille de contrôle dense. La positivité aux points échantillonnés n’est pas une preuve continue. Pour les géométries sévères retenues, exiger en plus une borne inférieure certifiée par subdivision/Bernstein ou marquer la classe `POSITIVITY_NOT_CERTIFIED` et ne pas l’utiliser comme preuve robuste. Rapporter `qJ_min`, le rapport d’aspect, l’angle maximal, `detJ_min` et la méthode de certification sans mélanger leur portée.

## Patch test énergétique et objectivité infinitésimale

Cas élémentaires prévus : dilatation uniforme, compression hydrostatique, cisaillement pur, traction uniaxiale, champ affine général et rotation rigide infinitésimale. Pour chacun comparer `ε`, `σ=Cε`, `½ε:C:ε·V`, force nodale et somme des résultantes à une formule analytique. Sur cube affine, la dilatation distingue directement le poids volumique 1/8; l’énergie déviatorique contrôle `Kdev`. Le résidu de rotation infinitésimale doit rester nul à la tolérance pré-gelée. Une rotation finie n’est pas une propriété du modèle linéaire.

Nodeids proposés (pas encore implémentés/inscrits) : `tests/verification/test_hex8_sri_patch_energy.py::test_patch_case[<formulation>-<mode>-nu_<nu>-<geometry>]`. Fixer une tolérance relative `1e−10` pour les contrôles analytiques élémentaires après normalisation par l’échelle d’énergie/force; le seuil reste à valider avant exécution et ne sera pas recalé après résultat. Les cas et budgets sont listés dans `SUPPLEMENTAL_VALIDATION_MATRIX.csv`.

## Spectre et mécanismes

Après autorisation distincte, analyser la rigidité d’un élément libre pour HEX8, SRI historique et corrigé : six vecteurs de corps rigide, rang relatif à `||K||`, plus petite valeur singulière positive, modes supplémentaires, sensibilité aux seuils, et champs des petits modes. Utiliser des matrices mises à l’échelle sans dimension avant d’appliquer un seuil relatif. Distinguer mouvement rigide exact, petit mode physique, perte de précision par conditionnement et hourglass par visualisation/énergie nulle du mode. Le nodeid proposé est `tests/verification/test_hex8_sri_spectrum.py::test_element_spectrum[<formulation>-nu_<nu>-<geometry>]`; il est différé jusqu’à une autorisation d’eigensolve. Aucun résultat spectral nouveau n’est livré ici.

## Seuils, arrêt et priorité

Les cas affines et patch sont MUST pour toute nouvelle revue scientifique. Distorsions modérées/warp sont SHOULD; cisaillement extrême, graines multiples et seuils très aplatis sont DEFERRED jusqu’à la mise en place d’un certificat Jacobien et d’une référence. Un non-fini, un Jacobien non positif/non certifiable, un mode supplémentaire au seuil gelé, un échec d’équilibre ou un dépassement budgétaire arrête ce cas; aucun retry. Les seuils et catégories sont à geler par Owner avant exécution.
