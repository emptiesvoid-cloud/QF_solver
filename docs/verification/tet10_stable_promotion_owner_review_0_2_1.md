---

doc_id: OWNER-REVIEW-ST-02-A-TET10-001
revision: 0.1
status: owner_reviewed
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Owner review ST-02-A - TET10

Cette fiche concerne une promotion eventuelle de `owner_accepted` vers `stable`
pour TET10 isotrope en statique lineaire, modal, Newmark et harmonique.

## Resultats principaux

| Route | Reference | Ecart maximal | Niveaux de convergence | Verdict technique |
| --- | --- | ---: | ---: | --- |
| Statique | CalculiX C3D10 | `6.840e-05` sur le deplacement | 4 | PASS |
| Statique same-mesh | Code_Aster TETRA10 | `3.872e-09 %` sur UZ pointe | 1 | PASS |
| Modal | Code_Aster TETRA10 | `3.225e-11` | 3 spatiaux | PASS |
| Newmark | Code_Aster TETRA10 | `5.779e-12` | 4 temporels | PASS |
| Harmonique | Code_Aster TETRA10 | `6.190e-12` | 4 frequences | PASS |

Une seconde geometrie cylindrique TET10 est egalement PASS : ecarts
Code_Aster de `0,0701 %` modal, `0,0998 %` Newmark et `0,0611 %` harmonique,
avec quatre niveaux spatiaux et des increments finaux de `0,1388 %` et
`0,1929 %`.

Une variante amortie de cette geometrie est egalement PASS avec un
amortissement de Rayleigh massique cible de `2 %` sur le premier mode
(`alpha = 23,8485 s^-1`, `beta = 0`). Les ecarts Code_Aster sont de `0,0701 %`
sur les frequences, `0,0889 %` sur l'historique Newmark et `0,0610 %` sur la
reponse harmonique. Cette preuve couvre l'amortissement proportionnel declare,
mais pas l'amortissement non proportionnel ni un calage experimental.

Un chemin de charge non cantilever a ensuite ete ajoute avec un bloc unitaire,
face inferieure bloquee et charge repartie sur la face superieure. Sur `803`
noeuds et `386` TET10, les ecarts Code_Aster sont de `3,24e-10 %` modal,
`8,86e-13 %` Newmark et `1,14e-13 %` harmonique; les increments finaux sont
`0,1203 %` modal et `0,3207 %` statique.

Une sonde de contraintes interieures sur le bloc compare `35` elements avec une
marge de `20 %` vis-a-vis des faces de blocage et de chargement. Apres correction
explicite de l'ordre Voigt `XY/YZ/XZ`, l'ecart L2 sur les six composantes 3D
moyennes est de `2,1316e-13 %`, pour une limite de `10 %`.
La meme sonde sur un cantilever rectangulaire compare `13` elements et donne
`5,9227e-10 %`. Cette preuve est bornee a des champs interieurs moyens et ne
constitue pas une acceptation des pics aux singularites.

Sur le cylindre facettise, `30` elements interieurs donnent un ecart L2 de
`0,43619 %`. Les trois familles geometriques confirment la comparaison du
champ interieur, tandis que les pics ponctuels aux singularites restent exclus.

La regle d'acceptation est formalisee dans
`qualification/stress_observable_policy_0_2_1.json`. Elle impose une marge
interieure de `20 %`, au moins trois elements sondes et limite l'ecart de
reference a `10 %`. Les pics ponctuels aux faces de blocage, de chargement,
aux charges ponctuelles et aux angles rentrants restent informatifs seulement.

Le dossier complet est
`qualification/maturity_evidence_0_2_1/tet10_stable_batch_01/report.md`.

## Questions Owner

1. Les preuves TET10 statiques et dynamiques couvrent-elles le domaine isotrope revendique ? Réponse Owner : `OUI`.
2. Les correlations CalculiX statiques, Code_Aster TETRA10 statique et Code_Aster dynamiques sont-elles acceptables ? Réponse Owner : `OUI`.
3. Quatre niveaux spatiaux externes sur le cas cylindrique et quatre niveaux temporels sont-ils suffisants pour ce lot ? Réponse Owner : `OUI`.
4. Les limites avec amortissement de Rayleigh massique cible a 2 %, sans amortissement non proportionnel, sans non-linearite, sans contact et sans grandes transformations sont-elles suffisantes ? Réponse Owner : `OUI`.
5. La preuve amortie Code_Aster est-elle suffisante pour fermer le point amortissement proportionnel ? Réponse Owner : `OUI`.
6. La maturite `stable` est-elle acceptable avec trois chemins de charge dynamiques et des sondes de champ interieur sur trois geometries, en excluant explicitement les pics ponctuels aux singularites ? Réponse Owner : `OUI`.
7. Les sondes de contraintes interieures sur le bloc, le cantilever et le cylindre, avec des ecarts L2 de `2,1316e-13 %`, `5,9227e-10 %` et `0,43619 %`, sont-elles suffisantes comme preuve de contraintes hors singularites pour le domaine borne ? Réponse Owner : `OUI`.
8. Decision : `stable`, `accepted_with_recommendations` ou maintien `owner_accepted` ? Réponse Owner : `stable`.

## Decision

- Reponse Owner : `stable` avec recommandations non bloquantes
- Date : 2026-08-21
- Owner : Quentin Farinazzo (déclaration électronique)
- Domaine accepte : .......................................................
- Exclusions confirmees : .................................................
