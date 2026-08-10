---
doc_id: DOC-VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018
revision: 0.1
status: owner_accepted
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# Correlation dynamique TET10 et Code_Aster TETRA10

## Objet

`VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018` compare les chemins modaux,
Newmark et harmoniques de QF_solver avec Code_Aster `18.1.0`, modele
`3D/TETRA10`. Le cas est un porte-a-faux volumique droit isotrope, de
petites deformations, constitue de 135 TET10 et 318 noeuds. Il est
volontairement structurel : la masse, les modes, les chargements et les
reponses ne sont pas reduits a un seul element.

Les coordonnees, la connectivite quadratique, les 13 noeuds encastres, les
13 noeuds charges, la resultante `UZ`, le pas de temps et les frequences sont
strictement identiques. L’observable est la moyenne de `UZ` sur la face libre.

## Resultats externes

| Controle | Ecart QF_solver / Code_Aster | Seuil | Verdict |
| --- | ---: | ---: | --- |
| Six frequences propres | `7,60e-10 %` | 5 % | PASS |
| Historique Newmark | `3,43e-10 %` RMS normalise | 5 % | PASS |
| Reponse harmonique complexe | `3,72e-10 %` RMS normalise | 5 % | PASS |

![Correlation dynamique TET10 et Code_Aster](../assets/generated/content_closure/tet10_dynamic_code_aster.png){ .result-figure }

## Raffinement

Trois maillages TET10 sont resolus en modal et statique. L’increment final de
frequence vaut `0,2151 %`; celui de la fleche moyenne vaut `0,3509 %`. Newmark
compare `T1/20`, `T1/40` et `T1/80` au calcul `T1/160` : les erreurs RMS
normalisees diminuent de `3,6801 %` a `1,0304 %`, puis `0,2570 %`.

La reponse harmonique est evaluee sous la premiere resonance non amortie.
Cette precaution evite de convertir une singularite physique du probleme sans
amortissement en un faux ecart de solveur.

## Reproduction

```powershell
python .\scripts\run_code_aster_tet10_dynamic_vnv.py `
  --output .\results\VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018
```

L’image Code_Aster est epinglee par empreinte. Une indisponibilite Docker est
classee comme erreur d’infrastructure et ne produit jamais un verdict de
correlation.

## Limites et Owner review

La preuve est bornee au TET10 isotrope, lineaire, droit et charge
nodalement. Les geometres courbes dynamiques, amortissement non proportionnel,
non-linearite materielle ou geometrique, contact et contraintes harmoniques
aux points de Gauss ne sont pas fermes par cette etude.

Les scopes `tet10-modal`, `tet10-transient-dynamic` et
`tet10-harmonic-response` ont ete acceptes par l'Owner le `2026-08-02` pour
le domaine borne de cette page. Cette decision ne couvre pas les exclusions
enumerees ci-dessus.
