# Campagne TET4 de convergence structuree en flexion

| Champ | Valeur |
| --- | --- |
| Identifiant | `VNV-TET4-STRUCTURED-FLEXION-001` |
| Element | TET4 isotrope lineaire |
| Analyse | Statique lineaire, petits deplacements |
| Reference de diagnostic | Euler-Bernoulli + correction de cisaillement Timoshenko |
| Cible | Erreur de fleche inferieure a `1 %` |
| Statut | `stable_candidate`, promotion non automatique |

## But de la campagne

Cette campagne remplace les successions de maillages Gmsh non imbriques par une
sequence structuree reproductible. Chaque cellule hexaedrique est decoupee en
six TET4 positifs. Les niveaux par facteurs `1, 2, 4, 8` partagent les noeuds
des niveaux precedents ; l'ordre de convergence peut donc etre estime sans
confondre le raffinement avec une variation de geometrie ou de connectivite.

Le modele est un porte-a-faux prismatique. La face `x=0` est totalement
bloquee et une force transverse `Fz` est distribuee sur la face `x=L` avec des
poids de surface tributaires. La somme des forces nodales est exactement la
force imposee.

## Execution legere

```powershell
python .\scripts\run_tet4_structured_convergence.py `
  --output .\tmp\tet4_structured_flexion `
  --factors 1 2
```

Pour la sequence complete de verification, utiliser les facteurs `1 2 4 8`.
Le dernier niveau est volontairement hors execution automatique de la CI : il
peut atteindre plusieurs centaines de milliers d'elements et doit etre lance
avec le backend matrix-free ou PETSc/MPI selon la memoire disponible.

## Interface librairie

```python
from solveur.api import generate_large_tet4_cantilever
from solveur.verification.tet4_structured_convergence import (
    StructuredTet4ConvergencePlan,
    run_structured_tet4_study,
)

plan = StructuredTet4ConvergencePlan(refinement_factors=(1, 2, 4))
summary = run_structured_tet4_study("results/tet4_structured", plan=plan)
```

## Campagne de correction de maillage

Le motif historique à six TET4 par cellule reste la référence de
non-régression. Pour isoler l'effet de la discrétisation sur la flexion, le
runner accepte aussi un motif centré à douze TET4 par cellule et un chargement
de face cohérent avec les triangles de bord :

```powershell
python .\scripts\run_tet4_structured_convergence.py `
  --output .\results\tet4_centered `
  --base-nx 4 --base-ny 1 --base-nz 1 `
  --factors 1 2 4 8 16 `
  --decomposition centered `
  --load-distribution surface_consistent
```

Cette variante est un outil de diagnostic, pas une nouvelle formulation
TET4. Le chargement `surface_consistent` est intégré avec les fonctions de
forme bilinéaires du quadrangle de face : chaque sous-face rectangulaire
reçoit un quart de sa résultante sur chacun de ses quatre noeuds, sans
privilégier une diagonale. La campagne PETSc du 21 août 2026 donne environ
11,71 %, puis 3,79 %, sur 24 576 et 196 608 éléments. Le niveau suivant à
1 572 864 éléments atteint 1,5073 %. Le niveau 80 franchit ensuite le seuil
de 1 % avec 0,8183 % sur 24 576 000 éléments.

Le modele genere est un format grand modele HDF5, avec les tableaux de noeuds,
connectivite, blocages et charges. Le backend matrix-free n'alloue pas la
matrice globale creuse ; le resume conserve les iterations, le residu et le
temps de resolution.

## Resultat grand modele PETSc

Une execution PETSc/GAMG reproductible a ete realisee avec le motif centre,
le chargement de face coherent et le runtime large epingle. L'ecart est
calcule sur le deplacement de pointe par rapport a la reference de poutre de
Timoshenko :

| Elements | DDL | Ecart de fleche | Iterations | Residu |
| ---: | ---: | ---: | ---: | ---: |
| 24 576 | 8 019 | 11.711981 % | 161 | 2.00e-17 |
| 196 608 | 56 355 | 3.791534 % | 193 | 3.40e-17 |
| 1 572 864 | 814 659 | **1.507279 %** | 212 | 6.47e-17 |
| 3 072 000 | 1 579 923 | **1.217644 %** | 219 | 1.37e-16 |
| 24 576 000 | 12 462 243 | **0.818328 %** | 252 | 2.09e-16 |

Le seuil `1 %` est atteint sur la référence de flexion de Timoshenko. La preuve
reste mono-rang et utilise une référence analytique 1D ; elle est donc lue avec
la corrélation indépendante TET4/TETRA4 sur maillage identique. Le TET10/TETRA10
reste un diagnostic d'ordre d'interpolation, et non l'oracle primaire du TET4.

Le niveau supplementaire est archive sous
`qualification/vnv/tet4_structured_petsc_refined_003/`. La sequence initiale
est archivee sous
`qualification/vnv/tet4_structured_petsc_corrected_002/reference/`. Le
manifeste conserve la commande, les versions et les empreintes des fichiers
de preuve. Les anciennes valeurs inferieures a 1 % qui ne disposent pas dans
l'arbre courant d'un modele d'entree et d'un manifeste correspondant ne sont
pas utilisees pour la promotion.

Le niveau 80 est archive sous
`qualification/vnv/tet4_structured_petsc_refined_004_docker/`. Il a été exécuté
dans l'image PETSc/GAMG `qf-solver-large:vnv-20260821`, avec `12 462 243` DDL,
`252` itérations, `830,82 s` de résolution et environ `986 MiB` d'opérateur.

## Reference 3D TET10

La campagne `VNV-TET4-TET10-3D-REFERENCE-001` convertit chaque niveau
structure TET4 en TET10 conforme, puis compare les deux interpolations a la
reference poutre. Sur la sequence `8x2x2`, `16x4x4`, `32x8x8`, le niveau final
contient `12 288` TET4, `18 785` noeuds TET10 et `56 355` DDL TET10 :

| Facteur | Erreur TET4 / poutre | Erreur TET10 / poutre | Ecart TET4 / TET10 |
| ---: | ---: | ---: | ---: |
| 1 | 71,2666 % | 2,1132 % | 70,6463 % |
| 2 | 39,6337 % | 1,1367 % | 38,9396 % |
| 4 | 14,9327 % | **0,8277 %** | 14,2228 % |

Cette preuve confirme que l'ecart TET4 est principalement une erreur de
representation de la flexion et non une divergence entre noyaux. Elle fournit
une reference 3D interne convergee sous `1 %`, mais pas encore un oracle
independant : la corrélation primaire Code_Aster `TETRA4` sur maillage
identique est suivie séparément ; `TETRA10` reste un diagnostic d'ordre.
Les artefacts sont archives dans
`qualification/vnv/tet4_tet10_3d_reference_001/` avec manifeste SHA-256.

## Criteres de promotion

Le seuil physique de `1 %` est accepte uniquement si le dernier niveau passe
simultanement :

1. erreur de fleche `<= 1 %` par rapport a une reference 3D convergee ;
2. residu libre sous le seuil du profil de verification ;
3. ordre h positif et tendance monotone sur au moins trois niveaux ;
4. accord TET4 QF_solver / TETRA4 Code_Aster sur le meme maillage ;
5. absence de dependance a une conversion dense ou a une liste globale de
   coefficients Python.

La formule de poutre reste un diagnostic de tendance et le seuil de `1 %` est
maintenant vérifié par le niveau 80. La comparaison TET4/TETRA4 ferme la
vérification de l'opérateur sur maillage identique ; la comparaison TET10 ou
TETRA10 reste informative pour mesurer la différence d'ordre, mais n'est pas
un critère de rejet du TET4 sur ce cas de flexion.

## Artefacts attendus

- `summary.json` : valeurs, erreurs, ordres et checks ;
- `report.md` : tableau lisible pour la revue ;
- `level_<facteur>/model.h5` : modele grand format de chaque niveau ;
- `displacements.h5` ou `displacements.npz` : a produire lors d'une execution
  de resolution avec sortie ;
- manifeste de preuve : a ajouter lorsque la campagne externe Code_Aster est
  executee sur les memes niveaux.

Cette campagne est une etape de V&V vers la maturite stable ; elle ne change
pas la maturite du TET4 par simple generation de maillage.
