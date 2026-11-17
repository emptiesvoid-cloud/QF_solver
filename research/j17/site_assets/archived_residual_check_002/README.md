# J17 — diagnostic du résidu archivé

**Statut :** données de diagnostic reproductibles, non publiées et sans promotion des verdicts QF.

Cette figure compare, pour 15 combinaisons de cinq fréquences (2,300 à 2,450 Hz) et trois vecteurs archivés, le résidu relatif évalué exactement sur les valeurs binaires stockées et la borne relative recalculée par le garde courant. Les matrices archivées sont complexes de taille 175 × 175. La ligne horizontale est le seuil inchangé de 1e−7.

Les 15 évaluations exactes satisfont le seuil pour les systèmes représentés. Les 15 réévaluations du garde restent rejetées, car leur borne conservative dépasse le seuil. Ces statuts portent sur les matrices, seconds membres et solutions stockés; ils ne vérifient ni l’assemblage, ni la réponse physique, ni l’erreur avant de la solution. Les verdicts J15/J16 restent `QF_GUARD_REJECTED`.

`exact_residual_points.csv` donne les fréquences, méthodes, résidus et bornes. `exact_residual_summary.json` conserve les fractions exactes, les contrôles mpmath, les conditionnements estimés, les empreintes et les ressources observées. La figure a été réimprimée depuis le CSV par `research/j17/prepare_gallery_assets.py`.

### Rectification de libellé

Le fichier brut de post-traitement J17 et son image portent par erreur le libellé « 8x8 ». Les NPZ vérifiés et le contrat montrent des matrices de taille **175 × 175**. Les artefacts bruts sont conservés à l’identique; la figure présente ici le libellé corrigé.

### Reproduction

Depuis la racine du dépôt, avec les dépendances Python du projet et Matplotlib :

```powershell
python research/j17/prepare_gallery_assets.py
```

Le script ne lance aucun assemblage ni solveur FEM. Les empreintes des sources et de chaque fichier préparé sont dans `artifact_manifest.json`.
