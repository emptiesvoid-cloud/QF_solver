# WP12 R3.6 — préparation de corrélations sur topologies diverses

**Statut : `PREPARATION_ONLY_NOT_EXECUTED`**  
**Branche : `codex/wp12-expanded-correlation`**

## Objet

R3.5 a établi 144 corrélations candidates Code_Aster sur quatre familles
d’éléments, trois géométries prismatiques et quatre chargements. R3.6 prépare
une extension avec trois topologies géométriques nouvelles. Cette préparation
ne modifie ni la mécanique du solveur ni les résultats, contrats ou historiques
R3.5.

## Matrice proposée

| Géométrie | Définition | Fraction de volume | H1 / H2 / H3 |
|---|---|---:|---|
| `l_section_beam` | Poutre extrudée à section en L, bras d’un élément dans une section 3×3 | 5/9 | 1×3×3 / 2×3×3 / 4×3×3 |
| `perforated_prism` | Prisme avec trou carré traversant centré, une cellule retirée dans une section 3×3 | 8/9 | 1×3×3 / 2×3×3 / 4×3×3 |
| `stepped_cantilever` | Section complète jusqu’à mi-portée, puis section réduite au quart | 5/8 | 2×2×2 / 4×2×2 / 8×2×2 |

Les trois niveaux gardent la même géométrie physique au sein de chaque famille.
La subdivision varie uniquement selon l’axe longitudinal : il s’agit d’une
hiérarchie de maillages axiale, **pas** d’une étude de convergence isotrope ou
de convergence générale de maillage.

La matrice combinatoire comprend 4 familles (TET4, HEX8, TET10, HEX20),
3 géométries, 3 niveaux et 4 chargements (axial, transversal Y, transversal Z,
combiné), soit 144 cas proposés. Tous conservent la configuration linéaire
statique, le matériau, les résultantes et les conventions de charge R3.5.

## Taille maximale proposée, niveau H3

| Géométrie | Famille | Éléments | Nœuds | DDL |
|---|---|---:|---:|---:|
| L | TET4 | 120 | 60 | 180 |
| L | HEX8 | 20 | 60 | 180 |
| L | TET10 | 120 | 297 | 891 |
| L | HEX20 | 20 | 188 | 564 |
| Trou traversant | TET4 | 192 | 80 | 240 |
| Trou traversant | HEX8 | 32 | 80 | 240 |
| Trou traversant | TET10 | 192 | 432 | 1 296 |
| Trou traversant | HEX20 | 32 | 264 | 792 |
| Poutre étagée | TET4 | 120 | 61 | 183 |
| Poutre étagée | HEX8 | 20 | 61 | 183 |
| Poutre étagée | TET10 | 120 | 297 | 891 |
| Poutre étagée | HEX20 | 20 | 189 | 567 |

## Format Code_Aster

La documentation officielle ASTER limite les lignes du fichier de maillage à
80 caractères et impose que les mots/noms commencent par une lettre. Les longs
enregistrements HEX20 avec les labels décimaux `N<number>` dépassaient cette
limite. R3.6 utilise pour ses entrées des labels de nœuds bijectifs de deux
caractères, commençant par une lettre, avec `N` réservé aux anciens labels
`N1`, `N2`, etc. Le décodeur d’audit accepte les deux formats. Les fichiers et
labels des campagnes antérieures ne sont pas réécrits.

Références officielles : [syntaxe ASTER et limite de 80 caractères](https://code-aster.org/doc/v11/fr/man_u/u1/u1.03.00.pdf),
[lecture de maillage Code_Aster](https://code-aster.org/V2/doc/v12/en/man_u/u7/u7.01.21.pdf).

## Vérifications effectuées

- `tests/unit/test_wp12_diverse_models.py` : **8 passed**.
- Non-régression WP12 ciblée : **26 passed** (`test_wp12_expanded_models.py`,
  `test_wp12_expanded_correlation_io.py`, `test_wp12_code_aster_multifamily.py`).
- Ruff sur les fichiers concernés : PASS.
- Mypy ciblé sur modèle et auditeur : PASS.
- Compileall ciblé : PASS.
- Les tests vérifient volumes positifs et attendus, maillages HEX valides,
  absence de faces TET non-manifold, résultantes/moments de charge, résidus
  QF, limite de 80 colonnes et round-trip du maillage/chargement par l’auditeur
  indépendant.
- L’image Code_Aster épinglée est disponible localement ; aucun conteneur de
  calcul n’a été démarré pour R3.6.

## Limites et statut de preuve

Les 144 cas sont un catalogue déterministe et testé, pas 144 corrélations
exécutées. Aucun résultat Code_Aster, candidat, point officiel ou convergence
de maillage ne peut être revendiqué pour R3.6 à ce stade. Aucune mécanique de
production, aucun seuil et aucun ledger n’ont été modifiés. R3.5 et ses preuves
restent intacts.

**Prochaine étape :** geler un contrat prospectif R3.6 (catalogue exact,
provenance, gates et stockage), puis lancer la campagne séquentielle après
autorisation de cette exécution. Une éventuelle réussite sera une preuve
supplémentaire de corrélation linéaire bornée, sans attribution automatique de
points WP12.
