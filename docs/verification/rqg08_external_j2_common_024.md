---
doc_id: DOC-RQ-G08-024-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.4a0
reviewer: ""
approver: ""
---

# RQ-G08 - Corrélation J2 externe commune

## Verdict

`PASS_EXTERNAL_CORRELATION_BOUNDED` pour le périmètre expérimental borné de
la 0.2.4a0. La campagne est exécutée avec Code_Aster 18.1.0 dans l'image
Docker épinglée :

`simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`

## Périmètre et résultats

Le même matériau J2 petites déformations avec écrouissage isotrope, le même
historique de déplacement affine `[0.0, 0.25, 0.5, 0.75, 1.0]` et les mêmes
observables sont comparés pour un élément TET4, TET10, HEX8 et HEX20.

| Élément | Contrôles | Écart relatif maximal | Limite | Verdict |
| --- | ---: | ---: | ---: | --- |
| TET4 | 20 | `2.6218e-15` | `5.0e-4` | PASS |
| TET10 | 20 | `2.0600e-15` | `5.0e-4` | PASS |
| HEX8 | 20 | `4.3368e-16` | `5.0e-4` | PASS |
| HEX20 | 20 | `1.8727e-15` | `5.0e-4` | PASS |
| **Total** | **80** | **`2.6218e-15`** | **`5.0e-4`** | **PASS** |

Les observables couvrent la force-déplacement, les réactions, la contrainte
de von Mises, la déformation plastique équivalente, l'apparition de la
plasticité et l'état final. Pour ce patch à déplacements entièrement
prescrits, le résultant de réaction est reconstruit à partir de la traction
uniforme `SIEF_ELGA` sur la face chargée.

## Limites de revendication

Cette preuve est une corrélation numérique externe bornée. Elle ne constitue
pas une validation physique et ne ferme pas les preuves multi-éléments, de
convergence en maillage, de chargement cyclique ou de grande échelle. Ces
extensions restent des travaux de promotion ultérieure (`RQ-NL-11` à
`RQ-NL-14`).

## Traçabilité

- Digest suivi : `qualification/external_reference_digests/rqg08_j2_common_024.json`.
- Archive brute de rejeu : `qualification/vnv/external/rqg08_j2_common_024/reference/`.
- Campagne : `VNV-RQ-G08-J2-COMMON-024`.
- Gate : `RQ-G08 = PASS_EXTERNAL_CORRELATION_BOUNDED`.
