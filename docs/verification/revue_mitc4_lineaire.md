---
doc_id: DOC-VV-MITC4-REVIEW-001
revision: 0.1
status: controlled
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Decision interne MITC4 statique lineaire

> Mise a jour : `VNV-MITC4-CONICAL-CUTOUT-STATIC-012` ajoute un panneau
> annulaire conique facettise avec ouverture centrale libre et pression normale.
> La correlation externe CalculiX 2.20 `S4` sur les memes trois maillages est
> cinematiquement `PASS` sous `VNV-MITC4-CONICAL-CUTOUT-CALCULIX-S4-013` :
> `0,0249 %` a la sonde fine et `0,629 %` sur le vecteur nodal. Sa sortie `RF`
> reste un diagnostic ambigu avec des `CLOAD` poses sur appuis. La correlation
> Code_Aster 18.1.0 `DKQ` `VNV-MITC4-CONICAL-CUTOUT-CODEASTER-DKQ-014` ferme
> ce point de resultante sur le meme maillage et vecteur de charge : au niveau
> fin, ecarts `0,3436 %` (sonde), `1,7565 %` (vecteur) et `2,26e-11 %`
> (resultante). C'est une evidence geometrique supplementaire, qui ne rouvre
> pas la decision `engineering_internal` existante ni la reserve Cook distincte.

## Decision

Quentin Farinazzo accepte le 14 juillet 2026 le MITC4 isotrope en statique
lineaire pour un usage engineering interne, avec reservations explicites.

| Champ | Valeur |
| --- | --- |
| Decision | `accepted_with_reservations` |
| Perimetre | `mitc4-linear-static` |
| Classe d'usage | `engineering_internal` |
| Mode de revue | `self_review` |
| Independence | `not_independent` |
| Visibilite a la decision | `private` |
| Revendication de certification | aucune |

Le registre machine-readable est
`qualification/reviews/mitc4_linear_static_2026-07-14.json`.

## Domaine accepte

La decision couvre les petits deplacements et rotations, un materiau de coque
isotrope lineaire et une epaisseur constante par element. Elle couvre les
deplacements, reactions, bilans globaux, resultantes de membrane/flexion/
cisaillement et contraintes aux faces superieure et inferieure.

Le maillage doit respecter: aspect ratio inferieur ou egal a 10, warpage
inferieur ou egal a 5 degres, angles entre 30 et 150 degres et planarity ratio
inferieur ou egal a `1e-3`.

## Preuves retenues

| Etude | Resultat | Decision |
| --- | ---: | --- |
| Patchs et objectivite | erreurs de l'ordre de `1e-16` | accepte |
| Shear locking, maillage fin | `2,07 %` | accepte |
| Shear locking, 30 % distorsion | `2,07 %` | accepte |
| Scordelis-Lo `32x32` | `0,314 %` | accepte |
| Cylindre pince `32x64` | `7,26 %` | accepte |
| Cylindre pince / Abaqus S4R publie | `4,87 %` | preuve externe partielle |
| Cook `64x64` | `4,52 %` | reservation |
| Cook `200x200` | `4,968 %`, residu `1,12e-8` | reservation |

## Reservations obligatoires

- La fleche Cook se stabilise vers `0,2515`, et non vers la reference actuelle
  `0,2396`: cette reference et les conditions aux limites doivent etre auditees
  avant toute acceptation complete de Cook.
- La correlation Abaqus du cylindre pince compare des maillages differents; un
  calcul S4R a maillage identique est requis pour relever le niveau de preuve.
- La presente decision ne couvre pas le modal, Newmark, l'harmonique, les
  grandes rotations, le flambement, les composites ni les epaisseurs variables.

Cette auto-revue constitue une decision engineering interne, non une
qualification externe independante ou une certification.
