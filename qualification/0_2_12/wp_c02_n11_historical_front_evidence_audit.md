# WP-C02-N11 — Audit des preuves historiques du front

**Périmètre :** lecture seule des archives AQ et N10, vérification de provenance, reconstruction hors ligne M2/M3. Aucun solveur, assemblage, FEM, Docker ou test pytest n’a été lancé dans N11.

## Conclusion d’audit

Les résumés AQ publiés ne contenaient pas les traces nécessaires, mais le RUN AQ original a conservé les diagnostics structurés M1–M3 dans son `stdout.log`. Ce fichier se trouve encore dans l’archive locale du superviseur Docker, lié à son reçu et à son manifeste. Son SHA-256 est celui publié dans le rapport AQ. Les 48 fichiers référencés par le reçu sont présents et leurs hashes concordent. Le test AJ du commit d’exécution a le hash attendu.

Les tableaux bruts des contacts M2/M3 comprennent `gap_m`, `contact_pressures_pa`, les traces par rangée, les faux positifs/négatifs et les références de maillage. Les conventions figées du test AJ permettent de reconstruire indépendamment `λ=p·A_tributaire`, les états actif/ouvert et le front; les résultats reconstruits correspondent exactement aux traces et comptes enregistrés. Les données support de l’archive AQ restent néanmoins résumées dans les mêmes diagnostics et ne sont pas nécessaires au critère de front N03.

**Décision proposée : issue A — preuves M2/M3 récupérées.** Le gate prospectif de front M2–M5 est suffisamment documenté et satisfait son seuil d’une cellule. Cela propose `ACTIVE_FRONT_M2_M5=PASS_BOUNDED` pour le benchmark spécifié, après revue indépendante. Cela ne constitue pas une clôture automatique de WP-C02; l’état d’intégration global reste à actualiser selon les exigences restantes et une décision Owner documentée. Aucune preuve AQ historique n’a été remplacée ou modifiée.

## Provenance AQ vérifiée

- Campagne AQ : `wp-c02-an-collect-20261022-03`; statut de reçu `RUN_COMPLETE`; 3 PASS, 0 FAIL, 0 SKIP, 0 XFAIL, 0 XPASS.
- Commit d’exécution : `847e93086b518e5d724f17ecb33e92d534212fcc`; tree `503348daa9dbfe882ea71b6bd2e3260282dacf6f`.
- Arbre source SHA-256 : `26d82115b3e4a1628cdaa62bcd91a17873ae30a09d5604383029e10602aed883`.
- Manifeste AQ SHA-256 : `ba28108ece19c11277303167cc0197bb0f13a4b1ce8cc619a873075457b7b84e`; il correspond au SHA déclaré par le reçu.
- Reçu de RUN : `<local-data>\WP-C02-AK\wp-c02-an-collect-20261022-03\run-receipt.json`.
- `stdout.log` AQ original SHA-256 : `b10863968b43ebb228dd8d2423f5099a9418f27f2e781d2bf1c8404c25df5986`, identique à l’entrée `stdout.log` du reçu.
- Test exécuté `tests/unit/test_wpc02_aj_partial_active_contact.py` SHA-256 : `7b14816b6ed6f6bed8aaa8e3bbde568251cf94332aa6c7b12765f389d6ae226e`, recalculé depuis le blob du commit AQ.
- **48/48** artefacts du reçu contrôlés : fichiers présents, aucun hash divergent.
- Dans la sortie, trois lignes JSON `aj_partial_mesh_diagnostic` sont présentes. Elles viennent des appels du test AJ de raffinement M1, M2, M3; les corps ont été exécutés dans l’ancien RUN AQ. N11 ne fait que lire et recalculer à partir de ces nombres.

La mention antérieure `NOT_RECORDED_IN_AQ_SUMMARY` reste exacte pour le résumé AQ publié : les détails étaient dans le stdout original, pas dans ce résumé. Le nouveau paquet est classé **reconstruction hors ligne à partir d’une sortie numérique AQ archivée**, jamais comme nouvelle observation FEM.

## Conventions vérifiées

Le code source AJ du commit AQ fixe les nœuds de contact dans l’ordre `j` majeur puis `i`, les coordonnées `x=i/nx`, `y=j/ny`, et les aires tributaires comme somme des parts des triangles du bord inférieur. Le stdout archive les gaps et les pressions positives en Pa. On retrouve `λ_i=p_i A_i`, sans inversion de signe. Les seuils inchangés sont `λ>1e−7 N` pour actif et `g>1e−10 m` pour ouvert; les cas biactifs sont conservés séparément. Le front par rangée est le plus grand `x` actif; la référence continue est `x*=0,5 m` et `hx=1/nx`.

Ces conventions sont cohérentes avec N07/N09 : `λ` est la magnitude positive du multiplicateur compressif et `p=λ/A`; l’erreur de double négation de l’ancien collecteur n’est pas appliquée à ces champs AJ. Le source test AQ confirme explicitement `pressure=multipliers/areas`, la classification `multipliers > force_tolerance`, et la définition de front AR/AJ.

## Paquet de reconstruction hors ligne

Nouveau répertoire : `qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01`.

Il contient des copies byte-identiques du reçu, du reçu de collecte, du manifeste externe d’exécution, du stdout/stderr, du résultat worker et du source AJ du commit; ainsi que `m2_m3_front_reconstruction.json`. Les originaux AQ sous `AppData\Local\QFSolver` et les anciennes archives du dépôt n’ont pas été écrits. Les 8 fichiers du paquet correspondent à son manifeste d’intégrité; le SHA-256 de ce manifeste est `864e108661eee3d4d9365d2d5798f85baa3f94048c8c039c771a1ca5bf442e80`.

## Vérification N10

La campagne N10 demeure inchangée : M4 et M5 sont `PASS`, une tentative chacun. Le manifeste d’intégrité N10 a été recalculé sur **539/539** fichiers sans écart; SHA-256 `baa8822c7c078f89d1219445a034f579757eaf394ae4bde935b7a9bca7de74cc`. La revue indépendante N10 est favorable, sans finding P0/P1/P2. Les verdicts N06/N08 `FAIL` et Docker `FAIL_CLOSED` sont préservés.

Voir [l’analyse M2/M3](wp_c02_n11_m2m3_front_analysis.md) pour la reconstruction numérique, les lignes de front et l’évaluation N03.

## Contrôles préparatoires et revue N11

Les tests non FEM suivants ont été exécutés avec le manifeste N09 imposé par le contrat de collecte :

```text
python -m pytest -q -p no:rerunfailures -p no:cacheprovider \
  tests/unit/test_wpc02_ar_native_manifest_contract.py \
  tests/unit/test_wpc02_ar_native_collection_reporting.py
62 passed in 3.69s
```

Ils couvrent les contrats du manifeste, de la collecte et du rapport, y compris les fixtures unitaires de front, les classifications et la gestion des résultats incomplets. Aucun test appelant le solveur AJ ou le solveur FEM de production n’a été lancé.

La revue indépendante N11 est favorable : **P0=0, P1=0, P2=1**. Le P2 demande de préciser que le terme « bracket » désigne ici la présence d’états actif et ouvert, non la garantie que l’intervalle observé contienne le front analytique. Cette sémantique est celle de la fixture AJ et est explicitée dans l’analyse; le critère de distance `D_front,max/hx≤1` est vérifié séparément. Les faux positifs atteignent exactement le seuil d’une cellule, sans marge. Voir [la revue indépendante](wp_c02_n11_independent_review.md).

## État après revue

La preuve récupérée justifie le gate limité `ACTIVE_FRONT_M2_M5=PASS_BOUNDED` pour le benchmark N03. Cela ne ferme pas automatiquement WP-C02 et ne change ni les anciens verdicts Docker `FAIL_CLOSED`, ni N06/N08. Aucun FEM, Docker, merge ou release n’a été exécuté dans N11.
