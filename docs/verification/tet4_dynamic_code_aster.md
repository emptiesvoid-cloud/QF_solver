---
doc_id: DOC-VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020
revision: 0.1
status: owner_accepted
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# Correlation dynamique TET4 et Code_Aster TETRA4

## Objet

`VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020` compare les chemins modal,
Newmark et harmonique de QF_solver avec Code_Aster `18.1.0`, mode
`3D/TETRA4`. Le porte-a-faux volumique droit isotrope comporte 135 TET4 et
62 noeuds. Les coordonnees, la connectivite, l'encastrement, la resultante
nodale en `UZ`, le pas de temps et les frequences sont identiques dans les
deux solveurs. L'observable est la moyenne de `UZ` sur la face chargee.

## Resultats externes

| Controle | Ecart QF_solver / Code_Aster | Seuil | Verdict |
| --- | ---: | ---: | --- |
| Six frequences propres | `1,34e-10 %` | 5 % | PASS |
| Historique Newmark | `3,38e-10 %` RMS normalise | 5 % | PASS |
| Reponse harmonique complexe | `1,02e-10 %` RMS normalise | 5 % | PASS |
| Increment modal du maillage final | `3,417 %` | 10 % | PASS |
| Raffinement Newmark `T1/40 -> T1/160` | `1,281 %` RMS | `5,115 %` RMS | PASS |

![Correlation dynamique TET4 et Code_Aster](../assets/generated/content_closure/tet4_dynamic_code_aster.png){ .result-figure }

## Diagnostic de fleche statique

La serie de maillage affiche aussi une variation de fleche de `42,01 %` entre
les deux derniers maillages. Ce nombre est **informatif, non bloquant** pour
la presente preuve dynamique : la charge de face est repartie egalement sur
les noeuds libres et sa distribution spatiale varie donc avec le remaillement.
Il ne s'agit ni d'un ecart QF_solver/Code_Aster ni d'un critere de convergence
TET4. La convergence statique TET4 reste tracee par ses campagnes de traction,
flexion et torsion dediees, avec chargements coherents.

## Reproduction

```powershell
python .\scripts\run_code_aster_tet4_dynamic_vnv.py `
  --output .\results\VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020
```

L'image Docker Code_Aster est epinglee par empreinte. Son indisponibilite est
une erreur d'infrastructure, jamais un verdict mecanique.

## Limites et Owner review

Cette preuve couvre le TET4 isotrope, lineaire, droit, charge nodalement et
sans amortissement. Elle ne couvre pas la dynamique sur geometrie courbe,
l'amortissement non proportionnel, les grandes deformations, la plasticite,
le contact, ni les contraintes harmoniques aux points de Gauss.

Les scopes `tet4-modal`, `tet4-transient-dynamic` et
`tet4-harmonic-response` ont ete acceptes par l'Owner le `2026-08-02` pour
le domaine borne de cette page. Cette decision ne couvre pas les exclusions
enumerees ci-dessus.
