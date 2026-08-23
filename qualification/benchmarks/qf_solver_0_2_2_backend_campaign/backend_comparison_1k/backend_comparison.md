# Comparaison des backends grands modeles

Statut : **PASS**

Le statut `PARTIAL` indique qu'un backend optionnel n'etait pas disponible ; il ne vaut pas qualification complete.

| Backend | Statut | DDL | Audit | Motif |
| --- | --- | ---: | --- | --- |
| scipy | PASS | 1029 | PASS |  |
| matrix_free | PASS | 1029 | PASS |  |
| petsc | PASS | 1029 | PASS |  |

| Reference | Candidat | Ecart deplacement | Seuil | Statut |
| --- | --- | ---: | ---: | --- |
| scipy | matrix_free | 1.087040e-13 | 1.000000e-07 | PASS |
| scipy | petsc | 1.417246e-13 | 1.000000e-07 | PASS |

All requested backends completed and matched.
