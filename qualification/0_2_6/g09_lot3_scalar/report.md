# VNV-CONTACT-CODEASTER-LIAISON-UNIL-001

Statut automatise : **PASS_EXTERNAL_CORRELATION**.

## Perimetre compare

QF_solver utilise son contact normal noeud-triangle a normale initiale figee. Code_Aster 18.1.0 est execute dans le conteneur Docker epingle avec `DEFI_CONTACT(... FORMULATION='LIAISON_UNIL')`. Les deux problemes ont le meme ressort normal, le meme gap initial et les memes charges. Le plan est reduit a l'inegalite scalaire `z + UZ >= 0` pour isoler la loi unilaterale.

| Cas | Charge Z [N] | QF UZ [m] | Aster UZ [m] | Ecart | Gap Aster [m] |
| --- | ---: | ---: | ---: | ---: | ---: |
| compression | -200 | -0.1 | -0.1 | 0.000e+00 % | 0.000e+00 |
| separation | 20 | 0.02 | 0.02 | 0.000e+00 % | 1.200e-01 |

![Comparaison QF_solver et Code_Aster](code_aster_contact_comparison.png)

## Limites

Cette correlation externe ferme uniquement le comportement unidirectionnel ouverture/fermeture. Le contact avec frottement, les faces deformables, les normales actualisees, le grand glissement et les maillages non conformes restent hors preuve externe.
