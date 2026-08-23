# Comparaison des backends grands modeles

Statut : **PARTIAL**

Le statut `PARTIAL` indique qu'un backend optionnel n'etait pas disponible ; il ne vaut pas qualification complete.

| Backend | Statut | DDL | Audit | Motif |
| --- | --- | ---: | --- | --- |
| scipy | PASS | 24 | PASS |  |
| matrix_free | PASS | 24 | PASS |  |
| petsc | SKIP |  |  | PETSc backend requires optional dependency petsc4py. |

| Reference | Candidat | Ecart deplacement | Seuil | Statut |
| --- | --- | ---: | ---: | --- |
| scipy | matrix_free | 5.816018e-16 | 1.000000e-07 | PASS |

Some optional backends were unavailable; this is not a complete backend qualification.
