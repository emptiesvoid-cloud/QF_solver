# VNV-MITC4-LAMINATE-DYNAMIC-001

## Objet

Cohérence interne modal, Newmark et harmonique pour un porte-a-faux MITC4 stratifié symétrique `[0/90/90/0]`. Cette campagne ne constitue pas une corrélation externe.

## Modal

Fréquence fondamentale : `14.002555` Hz. Résidu relatif : `3.100e-09`. Orthogonalités masse/raideur : `5.682e-16` / `3.919e-11`.

## Newmark

| Pas/période | Erreur RMS | Dérive énergie | Résidu dynamique | Max S11 face supérieure (Pa) |
| ---: | ---: | ---: | ---: | ---: |
| 20 | 4.162e-02 | 1.284e-11 | 4.762e-12 | 3.211e+03 |
| 40 | 1.048e-02 | 3.797e-12 | 4.558e-12 | 3.212e+03 |
| 80 | 2.623e-03 | 3.749e-12 | 3.874e-12 | 3.212e+03 |

## Harmonique

Erreur complexe maximale : `2.126e-08`. Limite statique à 0 Hz : `5.403e-12`. Post-traitement : `4` plis.

![Newmark](VNV-MITC4-LAMINATE-DYNAMIC-001-newmark.png)

![Harmonique](VNV-MITC4-LAMINATE-DYNAMIC-001-harmonic.png)

## Limites ouvertes

- The oracle is the first numerical laminate eigenmode; this is an algorithmic invariant, not an independent structural reference.
- No same-mesh Code_Aster, CalculiX, Abaqus or NAFEMS laminate-dynamics correlation is supplied.
- The layup is symmetric and planar. Curved laminates, eccentric shell offsets, nonlinear plies, damage and delamination are outside this evidence.
- Only mass-proportional Rayleigh damping is exercised because drilling directions are statically condensed.

Statut interne : **PASS_INTERNAL**. Maturité : `verified_development`.
