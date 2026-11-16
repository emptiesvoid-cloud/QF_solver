# J11 — résultats et reproductibilité

Les données de ce dossier sont des éléments de développement exploratoire. Elles ne constituent ni une qualification générale de QF Solver, ni une preuve de convergence universelle. Aucun résultat historique J7 à J10 n’a été réécrit.

## Transitoire TET10 indépendant

`transient_v3/result.json` consigne le contrat, la solution continue indépendante, les contrôles, les indicateurs temporels et spatiaux et les limites. `transient_v3/checkpoints/tet10_axial_bar_states.npz` contient 41 états complets de déplacement nodal du calcul Newmark `nx=16`, de 0 à 8 ms. Les checkpoints atomiques intermédiaires sont conservés dans `transient_v3/checkpoints/`.

L’animation GIF a 41 images tirées de ces états, espacées de 0,2 ms. Elle représente les déplacements Newmark enregistrés; le facteur d’amplification visuelle est `1e8`. Le rendu affiche les nœuds de l’axe central. Le GIF boucle pour présentation et ne représente pas le temps d’affichage physique. Les figures sont dans `transient_v3/figures/`.

Les images `tet10_axial_bar_mesh.png`, `tet10_axial_bar_history.png` et `tet10_axial_bar_time_refinement.png` accompagnent la série. La table temporelle et la table spatiale récapitulatives sont dans `transient_v3/result.json`; les historiques sont aussi disponibles en CSV.

Les deux premières tentatives TET10 restent respectivement `PYTEST_FAILED` : v1 s’est arrêtée dans l’oracle au temps initial; v2 a terminé les calculs mais son harnais a comparé deux grilles temporelles de tailles différentes avant la sérialisation finale. Les checkpoints partiels v2 sont conservés. La reprise v3 a terminé `COMPLETED_EXPLORATORY` en une tentative.

## HEX8-SRI

`hex8/raw/` contient les sorties brutes du diagnostic global J11; `hex8/hex8_global_reconstruction_states_key_normalized.npz` est une copie dérivée dont les clés alpha=0 ont été normalisées après vérification byte-à-byte des tableaux. Le fichier brut n’est pas altéré. La correction répare une indexation d’archive et ne recalcule aucun résultat.

Le calcul v2 est un assemblage de diagnostic via le noyau de recherche `Hex8SRIElement`, pas la route globale publique du solveur. NumPy, SciPy, mise à l’échelle diagonale et mpmath résolvent le même système QF; ils ne sont pas des références mécaniques indépendantes. Les échecs globaux HEX8-SRI historiques de J7 restent des FAIL.

## Sensibilité spatiale des résultats J10

`j10_mesh_postprocess_v3.json` compare les historiques de l’oracle semi-discret QF J10 pour trois changements successifs d’une seule direction de maillage. Les quatre maillages conservent le même point de charge physique, la même force ponctuelle de 1 N, le même point physique de mesure et les mêmes 192 instants. La comparaison utilise une échelle commune issue de l’archive.

Il s’agit de différences entre systèmes semi-discrets QF construits sur des maillages différents, pas d’erreurs par rapport au continuum. Les deux échecs de procédure précédents sont consignés dans `j10_mesh_postprocess_v1_failure.json` et `j10_mesh_postprocess_v2_failure.json`; ils n’ont modifié aucune entrée J10.

## Reproduction et empreintes

Les contrats et scripts sont dans `research/j11_transient/` et `research/j11_hex8/`; le bilan complet est `docs/planning/0.3.0-j11-resultats.md`. Les fichiers ici sont décrits dans `artifact_manifest.json`, avec taille et SHA-256. Les exécutions FEM ont été faites via `scripts/development_autonomous.py`, sur un seul nodeid exact par tentative.
