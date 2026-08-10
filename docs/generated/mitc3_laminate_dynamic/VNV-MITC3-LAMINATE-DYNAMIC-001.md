# VNV-MITC3-LAMINATE-DYNAMIC-001

## Objet

Verification interne MITC3+ multicouche plane symetrique `[0/90/90/0]`. La campagne combine un patch membranaire analytique et des invariants modaux/dynamiques. Elle ne constitue pas une correlation externe.

## Statique

| Elements | Erreur relative deplacement | Plis post-traites |
| ---: | ---: | ---: |
| 2 | 1.626e-15 | 4 |
| 4 | 9.246e-15 | 4 |
| 16 | 7.562e-14 | 4 |
| 64 | 8.477e-13 | 4 |

## Modal

Frequence fondamentale : `13.934772` Hz. Residu relatif : `2.400e-09`. Orthogonalites masse/raideur : `5.242e-16` / `9.906e-12`.

## Newmark

| Pas/periode | Erreur RMS | Derive energie | Residu | Plis finaux |
| ---: | ---: | ---: | ---: | ---: |
| 20 | 4.162e-02 | 1.026e-12 | 1.322e-12 | 4 |
| 40 | 1.048e-02 | 1.636e-12 | 1.332e-12 | 4 |
| 80 | 2.623e-03 | 1.610e-12 | 1.433e-12 | 4 |

## Harmonique

Erreur complexe maximale : `9.150e-09`. Limite statique a 0 Hz : `7.812e-14`. Post-traitement : `4` plis.

![Newmark](VNV-MITC3-LAMINATE-DYNAMIC-001-newmark.png)

![Harmonique](VNV-MITC3-LAMINATE-DYNAMIC-001-harmonic.png)

## Limites ouvertes

- The static oracle is an affine membrane field and the dynamic oracle is the first computed mode; neither is an external structural comparison.
- No same-mesh Code_Aster, CalculiX, Abaqus or published ply-level dynamic correlation is supplied.
- The layup is planar and symmetric. Curved laminates, non-zero B coupling, offsets, damage, delamination, large rotations and nonlinear dynamics are outside this evidence.
- Nodal dynamic shell-stress histories are intentionally not requested for MITC3+ across non-aligned local frames; element and ply results remain available at each stored state.

Statut interne : **PASS_INTERNAL**. Maturite : `verified_development`.
