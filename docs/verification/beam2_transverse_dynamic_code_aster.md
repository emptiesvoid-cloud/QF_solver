---
doc_id: DOC-VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019
revision: 0.1
status: owner_accepted
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# Correlation dynamique transverse BEAM2 et Code_Aster

## Objet

`VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019` compare les chemins
modal, Newmark et harmonique du `BEAM2` QF_solver a Code_Aster `18.1.0`,
element `POU_D_E`. Le porte-a-faux comporte deux noeuds, une section generale
identique, un encastrement complet et une force nodale `FY` en pointe.

Le `BEAM2` QF_solver est une poutre de Timoshenko alors que `POU_D_E` est une
poutre d'Euler-Bernoulli. La poutre est donc volontairement tres elancee : la
correction analytique de cisaillement vaut `2,808e-05`, soit `0,002808 %`. La
comparaison teste ainsi conventions locales, rigidite de flexion, masse,
reduction des blocages, Newmark et reponse complexe, sans masquer la
difference de modele.

## Resultats externes

| Controle | Ecart QF_solver / Code_Aster | Seuil | Verdict |
| --- | ---: | ---: | --- |
| Six frequences propres | `0,026486 %` | 1 % | PASS |
| Historique Newmark `UY` pointe | `0,017945 %` RMS normalise | 1 % | PASS |
| Reponse harmonique complexe `UY` pointe | `0,119821 %` RMS normalise | 1 % | PASS |
| Correction Timoshenko analytique | `0,002808 %` | 0,1 % | PASS |

![Correlation transverse BEAM2 et Code_Aster](../assets/generated/content_closure/beam2_transverse_dynamic_code_aster.png){ .result-figure }

## Parametres conserves

Les deux solveurs utilisent les memes noeuds, la meme section `A`, `Iy`, `Iz`,
`J`, le meme materiau, la meme densite, le meme clamp, le meme effort, le pas
Newmark `1e-4 s`, la grille temporelle et les quatre frequences harmoniques.
Les frequences sont sous la premiere resonance non amortie : une matrice
dynamique singuliere ne peut donc pas etre confondue avec une erreur du code.

## Reproduction

```powershell
python .\scripts\run_code_aster_beam2_transverse_dynamic_vnv.py `
  --output .\results\VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019
```

L'image Docker Code_Aster est epinglee. Son indisponibilite est une erreur
d'infrastructure, jamais un verdict mecanique.

## Limites et Owner review

Cette preuve est bornee a une flexion lineaire elancee et sans amortissement.
Elle ne qualifie ni poutre epaisse, ni amortissement, ni inertie repartie non
uniforme, ni assemblage multi-poutres, ni rotules, ni grandes rotations ou
contact. Le scope `beam2-linear-dynamics` a ete accepte par l'Owner le
`2026-08-02` pour ce domaine borne; cette decision ne couvre pas les
exclusions enumerees.
