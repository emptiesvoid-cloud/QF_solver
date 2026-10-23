# WP-C02-N11 — Analyse hors ligne du front actif M2/M3

## Nature des preuves

Les valeurs qui suivent sont reconstruites hors ligne à partir de `gap_m`, `contact_pressures_pa`, paramètres de maillage et traces JSON archivés dans le stdout du RUN AQ original. Elles ne sont pas un nouveau RUN. Les conventions et hashes de provenance figurent dans [l’audit des preuves](wp_c02_n11_historical_front_evidence_audit.md); les champs détaillés et chaque point sont dans `wpc02_ar_front_n11_reconstruction_20261023_01/m2_m3_front_reconstruction.json`.

Le recalcul a reconstruit les coordonnées de lignes de contact selon le générateur AJ gelé, réparti les aires de triangles exactement selon le code source hashé, puis calculé `λ=p·A`. Les classements sont `actif iff λ>1e−7 N`, `ouvert iff g>1e−10 m`; la ligne analytique `x=0,5 m` n’est pas forcée dans une catégorie. Les reconstructions retrouvent exactement les `last_active_x`, `first_open_x`, faux positifs et faux négatifs des diagnostics JSON AQ.

## Traces par rangée

| Niveau | y (m) | x actifs (m) | x ouverts (m) | Dernier x actif | Premier x ouvert | Intervalle observé / hx | Erreur du front / hx | Bracket présent |
|---|---:|---|---|---:|---:|---:|---:|---|
| M2 | 0 | 0; 0,25; 0,50 | 0,75; 1 | 0,50 | 0,75 | 1,0 | 0 | oui |
| M2 | 0,50 | 0; 0,25; 0,50 | 0,75; 1 | 0,50 | 0,75 | 1,0 | 0 | oui |
| M2 | 1 | 0; 0,25; 0,50; 0,75 | 1 | 0,75 | 1 | 1,0 | 1,0 | oui |
| M3 | 0 | 0; 1/6; 1/3; 0,50 | 2/3; 5/6; 1 | 0,50 | 2/3 | 1,0 | 0 | oui |
| M3 | 1/3 | 0; 1/6; 1/3; 0,50; 2/3 | 5/6; 1 | 2/3 | 5/6 | 1,0 | 1,0 | oui |
| M3 | 2/3 | 0; 1/6; 1/3; 0,50; 2/3 | 5/6; 1 | 2/3 | 5/6 | 1,0 | 1,0 | oui |
| M3 | 1 | 0; 1/6; 1/3; 0,50; 2/3 | 5/6; 1 | 2/3 | 5/6 | 1,0 | 1,0 | oui |

L’intervalle observé est celui qui relie le dernier nœud actif au premier nœud ouvert; sa largeur vaut `hx` dans chaque rangée. Pour les rangées ayant un faux positif, l’intervalle discret actif/ouvert est translaté à droite de la ligne analytique; le rapport le signale au lieu de prétendre que `x*=0,5` est contenu dans chaque intervalle. La localisation de l’estimateur `x_h` est contrôlée séparément par `|x_h−x*|/hx≤1`, comme défini par N03.

## Synthèse de classification M2/M3

| Critère prospectif N03 | M2 | M3 | Seuil | Verdict |
|---|---:|---:|---:|---|
| Contact rows | 15 | 28 | plan gelé | information |
| Actifs / ouverts | 10 / 5 | 19 / 9 | `0<actifs<lignes`, ouverts > 0 | PASS |
| Cas biactifs | 0 | 0 | conserver sans étiquette forcée | PASS |
| Rangées avec actif et ouvert / toutes | 3/3 | 4/4 | toutes | PASS |
| Transitions actif/ouvert par rangée | 1 maximum | 1 maximum | aucune multiplicité | PASS |
| `D_front,max` (m) | 0,25 | 0,1666666667 | rapporter | information |
| `D_front,max/hx` | 1,0 | 0,9999999999999998 | ≤ 1 | PASS |
| Faux positifs / faux négatifs | 1 / 0 | 3 / 0 | tous à ≤ hx | PASS |

Détail des classifications erronées côté ouvert :

| Niveau / indice AQ | Coordonnée (x,y) m | Gap archivé m | Pression archivée Pa | Multiplicateur reconstruit N | Distance au front / hx |
|---|---|---:|---:|---:|---:|
| M2 / 13 | (0,75; 1) | 0 | 10,25950502 | 0,6412190638 | 1,0 |
| M3 / 11 | (2/3; 1/3) | 0 | 4,383394951 | 0,2435219417 | 0,9999999999999998 |
| M3 / 18 | (2/3; 2/3) | 0 | 12,56831983 | 0,6982399906 | 0,9999999999999998 |
| M3 / 25 | (2/3; 1) | 0 | 9,255265332 | 0,2570907037 | 0,9999999999999998 |

Aucun faux négatif n’est observé. Aucune ligne n’a plus d’une transition active/ouvert. Tous les états et tous les nœuds de contact sont présents dans le JSON de reconstruction. Les gaps/multiplicateurs restent des données issues de l’ancien calcul AQ; seule leur conversion en états et mesures par rangée est recalculée hors ligne.

## Comparaison front M2–M5

| Niveau | hx (m) | Erreur front max (m) | Erreur / hx | Rangées bracketées | Erreurs FP/FN | Source | Verdict du gate front |
|---|---:|---:|---:|---:|---|---|---|
| M2 | 0,25 | 0,25 | 1,0 | 3/3 | 1 / 0, toutes ≤ hx | AQ, reconstruit hors ligne | PASS |
| M3 | 1/6 | 1/6 | 0,9999999999999998 | 4/4 | 3 / 0, toutes ≤ hx | AQ, reconstruit hors ligne | PASS |
| M4 | 0,125 | 0,125 | 1,0 | 5/5 | 5 / 0, toutes ≤ hx | N10, diagnostiqué directement | PASS |
| M5 | 0,1 | 0,1 | 0,9999999999999998 | 6/6 | 6 / 0, toutes ≤ hx | N10, diagnostiqué directement | PASS |

La localisation physique maximale diminue de 0,25 à 0,1 m avec le raffinement. Le ratio reste à une cellule, exactement au seuil gelé; il n’existe donc pas de marge sous ce seuil. Ces quatre niveaux satisfont le critère empirique `D_front,max/hx≤1`, mais ne démontrent pas un ordre asymptotique ni une convergence théorique du front.

## Verdict proposé et limites

**Issue N11 A : données M2/M3 récupérées; le critère de localisation du front actif M2–M5 est `PASS_BOUNDED` pour cette famille régulière TET4 et la définition nodale gelée.** Les erreurs de classification sont à une cellule ou moins et chaque rangée possède un front observé unique avec états actifs et ouverts.

Les données AQ proviennent d’une campagne Docker historique; la reconstruction est une analyse hors ligne des sorties déjà archivées. Cela ne convertit pas les mesures en RUN natif, ne modifie pas AQ, et n’établit pas d’équivalence entre qualifications. M4/M5 restent les seuls cas de la campagne N10 native et conservent leur statut local PASS. Les échecs N06/N08 et les verdicts Docker FAIL_CLOSED restent inchangés.

Cette conclusion est limitée à ce benchmark, à ses maillages, à la définition `x_h=max{x:λ>1e−7 N}` et au seuil prospectif `≤1 hx`. Les intervalles observés du dernier actif au premier ouvert ont largeur `hx`; sur les rangées de faux positifs, cet intervalle est à droite de `x*=0,5 m`, bien que l’estimateur actif reste à exactement une cellule de la référence. Le seuil est donc satisfait à sa limite, sans marge. Le critère de front peut être proposé PASS_BOUNDED après revue indépendante, mais WP-C02 ne doit pas être automatiquement marqué `CLOSED_BOUNDED`; les autres exigences de clôture et les statuts de qualification doivent être examinés séparément.

## Revue indépendante et contrôles

La revue N11 a recalculé la reconstruction directement à partir des trois diagnostics JSON du stdout AQ original. Elle confirme les comptes, traces par rangée, coordonnées des faux positifs et ratios M2/M3; elle n’a lancé aucun test ni calcul. Finding P0=0, P1=0 et P2=1, ce dernier portant sur la clarté du mot « bracket ». La fixture gelée définit ce booléen comme la coexistence d’au moins un état actif et d’un état ouvert; l’inclusion géométrique du front analytique n’est pas une condition du contrat actuel. Les tables ci-dessus signalent explicitement cette limite.

Les tests préparatoires non FEM `test_wpc02_ar_native_manifest_contract.py` et `test_wpc02_ar_native_collection_reporting.py` ont réussi (**62 passed, 3.69 s**). Aucun solveur, assemblage, calcul FEM, Docker ou retry n’a été exécuté dans N11. La revue indépendante détaillée figure dans [wp_c02_n11_independent_review.md](wp_c02_n11_independent_review.md).

Après revue, le verdict du gate de front est `ACTIVE_FRONT_M2_M5=PASS_BOUNDED`, limité au benchmark et au seuil gelé. Il ne démontre pas de convergence asymptotique, ne confère pas de qualification générale et n’autorise pas à clôturer automatiquement WP-C02. Les statuts historiques `FAIL_CLOSED` sont préservés.
