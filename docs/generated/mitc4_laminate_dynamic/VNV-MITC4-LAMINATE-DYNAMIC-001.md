# VNV-MITC4-LAMINATE-DYNAMIC-001

## Objet

Coherence interne modal, Newmark et harmonique pour un porte-a-faux MITC4 stratifie symetrique `[0/90/90/0]`. Cette campagne ne constitue pas une correlation externe.

## Modal

Frequence fondamentale : `14.002555` Hz. Residu relatif : `3.813e-09`. Orthogonalites masse/raideur : `9.712e-16` / `5.100e-11`.

## Newmark

| Pas/periode | Erreur RMS | Derive energie | Residu dynamique | Max S11 face superieure (Pa) |
| ---: | ---: | ---: | ---: | ---: |
| 20 | 4.162e-02 | 5.476e-12 | 4.381e-12 | 3.211e+03 |
| 40 | 1.048e-02 | 3.973e-12 | 4.580e-12 | 3.212e+03 |
| 80 | 2.623e-03 | 6.619e-12 | 4.350e-12 | 3.212e+03 |

## Harmonique

Erreur complexe maximale : `1.491e-08`. Limite statique a 0 Hz : `5.411e-12`. Post-traitement : `4` plis.

![Newmark](VNV-MITC4-LAMINATE-DYNAMIC-001-newmark.png)

![Harmonique](VNV-MITC4-LAMINATE-DYNAMIC-001-harmonic.png)

## Limites ouvertes

- The oracle is the first numerical laminate eigenmode; this is an algorithmic invariant, not an independent structural reference.
- No same-mesh Code_Aster, CalculiX, Abaqus or NAFEMS laminate-dynamics correlation is supplied.
- The layup is symmetric and planar. Curved laminates, eccentric shell offsets, nonlinear plies, damage and delamination are outside this evidence.
- Only mass-proportional Rayleigh damping is exercised because drilling directions are statically condensed.

Statut interne : **PASS_INTERNAL**. Maturite : `verified_development`.
