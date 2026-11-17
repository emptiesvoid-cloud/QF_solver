# J24B — torsion TET10, R1

La campagne sous le contrat `J24B-TET10-CIRCULAR-TORSION-STATIC-002` a terminé `PASS` pour les quatre maillages H1–H4. La première campagne, sous le contrat 001, reste `PYTEST_FAILED` / `INCONCLUSIVE` : son entrée H1 ne correspondait pas au SHA alors inscrit ; H2–H4 y avaient toutefois été calculés. Les deux contrats et leurs sorties historiques sont conservés dans `raw_results.zip`.

## Fichiers

- `raw_results.zip` — contrats, entrées, checkpoints par niveau, vecteurs, champs de contrainte aux points d’intégration et données de la tentative initiale. Le manifeste interne SHA-256 est vérifié par le script.
- `provenance.json` — sources, empreintes, identifiants, statuts, logiciels et ressources, avec chemins de dépôt relatifs.
- `site_data.json` et `mesh_results.csv` — résumé mécanique par niveau et critères.
- `torsion_deformed_mesh_h4.png` — maillage H4, appui, couple et déformée `×200 000`.
- `torsion_tip_section_twist_h4.png` — motifs de maillage initial/déformé de la section terminale à amplification identique.
- `torsion_mesh_convergence.png` — angle de torsion et erreurs selon les quatre maillages.
- `torsion_integration_point_stress_h4.png` — `√(Sxy²+Sxz²)` aux points d’intégration H4, avec position, unités et référence `Tr/J`.

Toutes les comparaisons de contrainte utilisent les valeurs aux points d’intégration TET10 à leurs coordonnées physiques ; aucune extrapolation nodale n’est utilisée. La norme L2 pondérée du tableau couvre tous les points d’intégration du maillage. La figure de section colore le sous-ensemble `|x−1,5| ≤ 0,05 m` ; le graphique radial affiche un point sur douze pour lisibilité.

Les statuts `WARNING` de l’audit général restent visibles, séparément du `PASS` limité aux critères gelés de cette campagne. Le PASS n’est ni une validation générale de TET10 ni une corrélation à un solveur externe.

## Reproduction des tables et figures

Depuis la racine du dépôt, avec QF Solver et son extra Gmsh, NumPy et Matplotlib disponibles :

```powershell
python research/j24b/tet10_torsion/build_site_assets.py
```

Cette commande lit l’archive et ne lance aucun calcul solveur. L’exécution FEM originale a été faite via le launcher autonome, sur le nodeid exact, le préflight et la source indiqués dans `provenance.json`. Les fichiers de sortie bruts du contrôleur demeurent dans son store local privé ; leurs empreintes sont dans le sidecar.

`provenance.json` et l’archive ne contiennent aucun chemin absolu du poste utilisateur. Les figures sont préparées pour revue ; aucune publication de site n’a eu lieu.
