# VNV-CONTACT-CODEASTER-G09-LOT3-010

Statut automatise : **PASS_EXTERNAL_CORRELATION**.

Dix niveaux de charge identiques sont compares entre QF_solver et Code_Aster 18.1.0. Les courbes couvrent l'ouverture, la fermeture progressive et l'etat final actif.

| Modele | Ecart courbe U | Ecart courbe gap | Gap final max |
| --- | ---: | ---: | ---: |
| dual_stop_corner | 4.16334e-14 % | 5.20417e-14 % | 0.000e+00 m |
| faceted_ramp_patch | 2.09476e-14 % | 2.50167e-14 % | 5.551e-17 m |
| deformable_tet4_two_slaves | 4.33998 % | 54.9912 % | 1.110e-16 m |

![Courbes QF_solver et Code_Aster](contact_code_aster_curves.png)

Cette campagne ne qualifie ni frottement, ni impact, ni grand glissement, ni contact surface-surface general.

Sur le bloc TET4 raffine, Code_Aster ferme un esclave plus tot au premier palier. L'ecart de courbe reste sous le seuil accepte de 5 %. QF_solver et CalculiX coincident avant contact, puis QF_solver et Code_Aster coincident sur la branche fermee.
