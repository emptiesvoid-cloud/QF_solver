# V&V contact avec frottement : raffinement structurel TET4

- Etude : `VNV-CONTACT-FRICTION-TET4-STRUCTURAL-002`
- Verdict interne : `PASS_INTERNAL`
- Maturite : `experimental`

| Maillage | TET4 | Gap [m] | |t| [N] | mu p [N] | Strategie |
| --- | ---: | ---: | ---: | ---: | --- |
| 4x2x2 | 96 | 1.943e-16 | 1391.046399 | 1391.046399 | active_slip_root |
| 8x4x4 | 768 | 1.388e-17 | 1476.569597 | 1495.972123 | direct |
| 12x6x6 | 2592 | 2.498e-16 | 1481.929116 | 1530.828057 | direct |
| 16x8x8 | 6144 | 4.441e-16 | 1485.067146 | 1548.235597 | direct |

Le repli actif est trace lorsqu'un niveau atteint le glissement. Un maillage plus fin peut revenir en adherence si la reaction normale augmente et fait passer la borne mu p au-dessus de la charge tangentielle. Le resultat confirme la fermeture normale et le cone de Coulomb, mais ne constitue pas encore une correlation externe ni une qualification surface-a-surface.

![Raffinement contact frottant](friction_structural_convergence.png)
