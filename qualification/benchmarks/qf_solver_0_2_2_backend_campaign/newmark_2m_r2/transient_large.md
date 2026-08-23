# Grande campagne Newmark TET4

Statut technique : **PASS**. Le périmètre reste **development** jusqu'à la revue Owner.

- DDL : `2044416`
- Éléments : `3951018`
- Backend : `petsc`
- MPI : `2` rang(s)
- Assemblage : `19.079` s
- Résolution : `90.939` s
- Pas de temps : `1.000e-04` s
- Pas Newmark : `10`
- Résidu final : `1.915e-05`
- Résidu maximal : `1.915e-05`
- Résidu relatif maximal : `1.968e-06`
- Matrice effective réutilisée : `K + 1/(beta*dt^2)*M`.

## Limites

Cette preuve couvre le modèle TET4 généré, le backend PETSc/SLEPc disponible dans l'image d'exécution et la configuration MPI indiquée. Elle ne constitue pas une qualification universelle des grands modèles ni des autres éléments.
