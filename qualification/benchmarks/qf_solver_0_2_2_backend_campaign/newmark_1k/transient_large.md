# Grande campagne Newmark TET4

Statut technique : **PASS**. Le périmètre reste **development** jusqu'à la revue Owner.

- DDL : `1029`
- Éléments : `1296`
- Backend : `petsc`
- MPI : `1` rang(s)
- Assemblage : `0.019` s
- Résolution : `0.009` s
- Pas de temps : `1.000e-04` s
- Pas Newmark : `6`
- Résidu final : `1.507e-05`
- Résidu maximal : `1.507e-05`
- Résidu relatif maximal : `1.055e-07`
- Matrice effective réutilisée : `K + 1/(beta*dt^2)*M`.

## Limites

Cette preuve couvre le modèle TET4 généré, le backend PETSc/SLEPc disponible dans l'image d'exécution et la configuration MPI indiquée. Elle ne constitue pas une qualification universelle des grands modèles ni des autres éléments.
