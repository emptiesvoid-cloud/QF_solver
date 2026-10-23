# WP-C02-N13 — Décision Owner de clôture bornée AR

**Date : 2026-10-23**
**Décision : `APPROVED`**
**Statut du périmètre : `WP_C02_STATUS=CLOSED_BOUNDED` — WP-C02-AR seulement**

## Décision Owner

L’Owner a explicitement approuvé :

> Autoriser `WP_C02_STATUS=CLOSED_BOUNDED`, avec maintien explicite de `GENERAL_CONTACT_QUALIFICATION=NOT_ACQUIRED`, `DOCKER_EQUIVALENCE=NOT_ACQUIRED`, absence de revendication de convergence asymptotique et conservation des FAIL N06/N08 et Docker.

Cette approbation fait suite à la proposition N13 et à l’évaluation N12 `READY_FOR_OWNER_CLOSED_BOUNDED_DECISION`. Elle autorise l’enregistrement administratif **exclusivement pour le benchmark WP-C02-AR et ses critères prospectifs N03**. Elle ne constitue pas une autorisation de RUN, Docker, merge, release ou promotion générale.

## Périmètre scientifique exact

Le statut `CLOSED_BOUNDED` couvre uniquement le benchmark manufacturé décrit dans le plan AR SHA-256 `fa3806c842acefbe707499ffdec9f703bcedb5031962594df4c5293d0fbe6cfc`, le protocole AR SHA-256 `bf7535eb4028715071744a2b8cc119b828f0eae2129a8f6b05e588872fcbf58d` et l’approbation Owner N03 (`WP-C02-N03-OWNER-CRITERIA-20261023`, SHA-256 `e27403b8d98dfee9d98733c4b6c3faef022ac79fbfa0296dc746d5070fdd6c0a`). Le modèle est le contact normal, sans frottement, TET4, à face rigide plane figée, selon les matériaux, conditions aux limites, chargements, maillages M1–M5 et oracles gelés dans ces artefacts.

Preuves rattachées :

- **AQ M1–M3 historiques :** campagne `wp-c02-an-collect-20261022-03`; commit `847e93086b518e5d724f17ecb33e92d534212fcc`, tree `503348daa9dbfe882ea71b6bd2e3260282dacf6f`; manifeste SHA-256 `ba28108ece19c11277303167cc0197bb0f13a4b1ce8cc619a873075457b7b84e`; stdout original SHA-256 `b10863968b43ebb228dd8d2423f5099a9418f27f2e781d2bf1c8404c25df5986`. Reçu RUN 48/48 vérifié. Le stdout AQ d’origine, byte-identique à la copie N11, porte les diagnostics, réactions d’appui, références analytiques et erreurs M1–M3. Aucune mesure n’est inférée depuis le seul résumé AQ.
- **N10 M4/M5 natifs :** campagne `wpc02-ar-native-n10-m4m5-20261023-01`; commit scientifique `2ccd669cad8ba51baea475c4cb838b8c06426f4b`, tree `4b760fe0d263df5874f380d16693d6378d32c468`; manifeste externe `qualification/0_2_12/wp_c02_ar_native_n09_execution_manifest.json`, SHA-256 `c6573776cb9811800e1fa242f6d9ad8a1acc0901d43bc6f81e0fc416b9d26c0e`; agrégat des sources `94c87ffed4de192240aaba9e869c7085f18c6177bd3ad24cedc79131addce359`; archive SHA-256 `baa8822c7c078f89d1219445a034f579757eaf394ae4bde935b7a9bca7de74cc`, 539/539 fichiers vérifiés. M4 et M5 ont chacun un résultat pytest `1 passed` et une seule tentative.
- **N11 M2/M3 front :** reconstruction hors ligne, sans nouveau calcul FEM, depuis la sortie AQ d’origine. Commit N11 `244023a6b084597a333e39be20af9904b42b976f`, tree `284921ca598c520d6475f3ae6433261f9b0c8c64`; archive `wpc02_ar_front_n11_reconstruction_20261023_01`, manifeste d’intégrité SHA-256 `864e108661eee3d4d9365d2d5798f85baa3f94048c8c039c771a1ca5bf442e80`, 8/8 fichiers vérifiés. Revue N11 : 0 P0, 0 P1, 1 P2 ouvert, sémantique du bracket explicitée. N12 a fait examiner indépendamment la matrice et l’évaluation; les deux remarques P2 de traçabilité ont été corrigées et recontrôlées; findings ouverts finaux : 0 P0, 0 P1, 0 P2.

Les seuils restent inchangés : ratios d’erreur de déplacement et pression M5/M1 strictement inférieurs à 0,9; erreur énergétique M5 strictement inférieure à M1; front M2–M5 à `D_front,max/hx≤1`; classification, couvertures de rangées, KKT, stationnarité, équilibre, travail et cohérence énergétique selon N03/AJ. `ACTIVE_FRONT_M2_M5=PASS_BOUNDED`, `N10_M4=PASS`, `N10_M5=PASS`.

## Statuts et limites maintenus

| Statut | Valeur après décision |
|---|---|
| `WP_C02_STATUS` | `CLOSED_BOUNDED` — uniquement benchmark WP-C02-AR/N03 |
| `WP_C02_AR_BOUNDED_BENCHMARK` | `CLOSED_BOUNDED` |
| `ACTIVE_FRONT_M2_M5` | `PASS_BOUNDED` |
| `N10_M4` / `N10_M5` | `PASS` / `PASS` |
| `GENERAL_CONTACT_QUALIFICATION` | `NOT_ACQUIRED` |
| `DOCKER_EQUIVALENCE` | `NOT_ACQUIRED` |
| Convergence asymptotique | Non démontrée; aucune revendication |
| `N06_M4/N06_M5`, `N08_M4/N08_M5` | `FAIL` historiques préservés |
| Campagnes Docker historiques | `FAIL_CLOSED` préservés |
| Intégration autoritative / publication | `PENDING` / `NOT_AUTHORIZED` |

Le front atteint le seuil existant d’une cellule sans marge numérique sur M2 et M4; M3 et M5 sont à l’arrondi flottant de cette borne. Le terme contractuel « bracket » constate les états actif et ouvert, et ne garantit pas que chaque intervalle discret contienne le front analytique. Ces limites ne changent pas le critère N03 approuvé et restent visibles.

Cette clôture ne couvre pas les géométries mobiles ou non planes, frottement, glissement, contact multiple ou non convexe, robustesse générale, qualification du chemin public, intégration autoritative, corrélation externe, ni les autres lacunes d’historique du rapport unifié. Elle ne transforme aucun résultat Docker en PASS et ne déclare pas la campagne native équivalente à Docker.

## Enregistrement

## Revue administrative indépendante

La revue administrative a examiné cette décision, la mise à jour de la matrice N12 et l’addendum/statut du rapport consolidé C02 en lecture seule. Elle confirme que le `CLOSED_BOUNDED` est limité à AR/N03; les statuts généraux, les échecs historiques, l’absence de revendication asymptotique, les gaps §17 et l’intégration en attente sont maintenus. Une ambiguïté rédactionnelle initiale entre l’ancien statut ouvert et la clôture bornée a été corrigée en identifiant le statut ancien comme pré-N13 et en distinguant le périmètre général du périmètre AR. Conclusion finale : **P0=0, P1=0, P2 ouvert=0**. Aucun test, calcul, FEM ou Docker n’a été exécuté par le reviewer.

## Enregistrement

Les livrables N12, cette décision et les mises à jour administratives du rapport consolidé C02 sont gelés ensemble par le commit qui contient ce document. Le HEAD/tree de gel et l’état Git final sont rapportés par la clôture N13. Aucun merge vers main ni publication n’est autorisé par cette décision.
