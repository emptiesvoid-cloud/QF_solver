# VNV-J2-NONLINEAR-PERFORMANCE-006

Statut : **PASS_INTERNAL**

Cette campagne est une caracterisation bornee; elle ne constitue pas une preuve de scalabilite HPC.

| Element | DDL | Etats Gauss | Temps [s] | Iterations Newton | Residu final | Memoire Python [octets] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `TET4` | 204 | 140 | 8.837795 | 33 | 4.061177e-09 | 5945507 |
| `TET10` | 1023 | 560 | 35.614007 | 33 | 3.088015e-09 | 12967703 |

The measurements characterize total solve cost and state storage on small J2 bars. They do not qualify large-scale, parallel or multi-million-DOF performance.
