---
doc_id: DOC-VNV-TET4-J2-CODEASTER-COMPLEX-001
revision: 0.1
status: verified_development_external_correlation
applicable_version: 0.2.1-alpha
owner_review: pending
reviewer: ""
approver: ""
---

# Correlation structurelle TET4 J2 avec Code_Aster

Cette campagne compare le comportement structurel monotone de QF_solver avec
Code_Aster 18.1.0 sur le meme maillage TET4/TETRA4. Elle complete la preuve
constitutive material-point et la campagne interne cyclique TET4 J2.

La campagne est une preuve externe de developpement. Elle ne constitue pas une
promotion automatique vers `stable` et ne couvre pas les grandes deformations,
le contact, le dommage ou la rupture.

## Modele et chargement

La geometrie est une equerre rentrante a volumes fusionnes. Le maillage commun
contient 104 noeuds et 244 elements TET4. Huit noeuds sont bloques et huit
noeuds charges. Les deux solveurs utilisent les memes forces combinees :

| Parametre | Valeur |
| --- | ---: |
| Force de base suivant X | `3.0e6 N` |
| Force de base suivant Y | `-6.0e6 N` |
| Facteurs de charge | `0.25, 0.50, 0.75, 1.00, 1.10` |
| Module d'Young | `210e9 Pa` |
| Coefficient de Poisson | `0.30` |
| Limite d'elasticite | `250e6 Pa` |
| Ecrouissage isotrope | `50e9 Pa` |

La relation Code_Aster est `VMIS_ISOT_LINE` avec l'option `PETIT`. Les
contraintes ponctuelles proches des re-entrants ne sont pas un observable
d'acceptation.

## Resultats compares

| Facteur | UX QF [m] | UX Code_Aster [m] | UY QF [m] | UY Code_Aster [m] | PEEQ QF | PEEQ Code_Aster |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.25 | -1.428563e-3 | -1.428563e-3 | -5.325139e-3 | -5.325139e-3 | 0.000000e+0 | 0.000000e+0 |
| 0.50 | -2.857125e-3 | -2.857125e-3 | -1.065028e-2 | -1.065028e-2 | 0.000000e+0 | 0.000000e+0 |
| 0.75 | -4.285688e-3 | -4.285688e-3 | -1.597542e-2 | -1.597542e-2 | 0.000000e+0 | 0.000000e+0 |
| 1.00 | -5.714250e-3 | -5.714250e-3 | -2.130055e-2 | -2.130055e-2 | 0.000000e+0 | 0.000000e+0 |
| 1.10 | -6.298769e-3 | -6.298769e-3 | -2.349823e-2 | -2.349823e-2 | 1.046898e-6 | 1.046898e-6 |

Les indicateurs sont ceux du `summary.json` archive. Les erreurs relatives
observees sont :

| Controle | Valeur | Limite | Statut |
| --- | ---: | ---: | --- |
| Ecart RMS chemin deplacement combine | `4.66e-14` | `1.0e-2` | PASS |
| Ecart deplacement final | `0.0` | `1.0e-2` | PASS |
| Ecart RMS chemin PEEQ | `2.89e-15` | `1.0e-2` | PASS |
| Ratio deplacement petits deplacements | `7.60e-3` | `1.0e-1` | PASS |
| Residu relatif maximal QF_solver | `1.36e-12` | `1.0e-7` | PASS |

![Comparaison des chemins QF_solver et Code_Aster](../../qualification/vnv/external/code_aster_tet4_j2_complex/reference/comparison.png)

![Deformee de l'equerre TET4](../../qualification/vnv/external/code_aster_tet4_j2_complex/reference/deformation.png)

## Interpretation et limites

Le meme maillage et les memes chargements produisent un accord numerique quasi
identique sur la branche monotone, y compris lorsque la PEEQ devient non nulle
au dernier facteur. Cette preuve reduit le risque de divergence entre
l'assemblage structurel TET4 et la loi J2 de reference.

Le perimetre reste limite a une geometrie rentrante, un materiau isotrope J2,
un ecrouissage isotrope lineaire, de petits deplacements et un chargement
monotone. Il manque encore une comparaison structurelle externe avec inversion,
decharge et rechargement avant de viser `stable`.

## Artefacts et reproductibilite

Les artefacts de reference sont conserves dans :

```text
qualification/vnv/external/code_aster_tet4_j2_complex/reference/
```

Ils comprennent le resume JSON, le rapport, le manifeste, la comparaison et la
deformee. La campagne peut etre relancee avec Docker :

```powershell
python .\scripts\run_code_aster_tet4_j2_complex_vnv.py `
  --output .\results\VNV-TET4-J2-CODEASTER-COMPLEX-027 `
  --mesh-size 0.50
```

La maturite reste `experimental` jusqu'a une decision Owner dediee et a la
fermeture des preuves cycliques structurelles. Les images et les chiffres de
ce document proviennent du resume archive, pas d'une recopie manuelle.
