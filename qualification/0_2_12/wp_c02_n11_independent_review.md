# WP-C02-N11 — Revue indépendante des preuves de front M2/M3

## Conclusion

**Avis favorable, issue A.** La revue indépendante confirme que les preuves M2/M3 récupérées du RUN AQ historique sont traçables et que le critère de front gelé N03 est satisfait sur M2–M5 pour ce benchmark : `ACTIVE_FRONT_M2_M5=PASS_BOUNDED`.

Findings : **P0 = 0, P1 = 0, P2 = 1**. Le finding P2 porte sur la terminologie du mot « bracket » : dans la fixture AJ gelée, `front_bracketed_by_observed_states` signifie qu’une rangée comprend des nœuds actifs et ouverts. Il ne signifie pas nécessairement que l’intervalle entre dernier actif et premier ouvert contient le front analytique. N11 explique cette distinction et donne les intervalles concernés. Le seuil indépendant de localisation `D_front,max/hx≤1` est contrôlé séparément.

## Vérifications indépendantes

- Manifeste d’intégrité de l’archive N11 : SHA-256 `864e108661eee3d4d9365d2d5798f85baa3f94048c8c039c771a1ca5bf442e80`; les huit entrées sont conformes.
- Manifeste d’intégrité N10 : SHA-256 `baa8822c7c078f89d1219445a034f579757eaf394ae4bde935b7a9bca7de74cc`; **539/539** fichiers conformes.
- Le stdout AQ archivé est byte-identique au stdout d’origine, SHA-256 `b10863968b43ebb228dd8d2423f5099a9418f27f2e781d2bf1c8404c25df5986`.
- Les identités AQ (commit, tree, branche, manifeste et campagne) concordent avec les reçus et la provenance archivée. **48/48** fichiers du reçu RUN et **55/55** fichiers du reçu COLLECT sont conformes.
- Le source AJ gelé correspond au hash `7b14816b6ed6f6bed8aaa8e3bbde568251cf94332aa6c7b12765f389d6ae226e`.
- La reconstruction indépendante à partir des trois diagnostics structurés du stdout retrouve les nombres de lignes, états actifs/ouverts, traces par rangée, transitions, faux positifs et distances M2/M3 présentés dans l’analyse N11.
- M2 : `D_front,max/hx=1`; M3 : `0.9999999999999998`. Les faux positifs sont à une cellule ou moins, les faux négatifs sont nuls et chaque rangée a une transition actif/ouvert.

## Portée et limites

Les données M2/M3 sont des sorties AQ historiques récupérées et post-traitées hors ligne, pas un nouveau calcul FEM natif. Les résultats N10 M4/M5 sont conservés tels qu’archivés. Les ratios de M2–M5 atteignent le seuil d’une cellule sans marge sous celui-ci. Le résultat est borné à la famille de maillages et à la définition nodale du front de ce benchmark; il ne démontre ni convergence asymptotique ni qualification générale du contact.

Les statuts N06/N08 `FAIL` et les verdicts Docker `FAIL_CLOSED` restent inchangés. Aucun fichier d’archive historique n’a été modifié. Aucun test, solveur, assemblage, FEM, Docker ou retry n’a été lancé par la revue indépendante.

## Tests préparatoires N11 (exécutés par l’agent principal)

Les tests de contrat non FEM des fichiers `test_wpc02_ar_native_manifest_contract.py` et `test_wpc02_ar_native_collection_reporting.py` ont donné **62 passed in 3.69s**. La revue indépendante n’a pas relancé ces tests.

## Verdict

Avis favorable pour le gate limité `ACTIVE_FRONT_M2_M5=PASS_BOUNDED` et pour l’issue A de N11. Aucun verdict de clôture globale WP-C02 ou de qualification générale n’est émis. Le maintien de `NOT_ACQUIRED` ou l’actualisation des statuts globaux relève de la décision et du contrat de qualification Owner; ce rapport n’effectue aucune promotion automatique.
