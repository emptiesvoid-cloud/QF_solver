# WP-C02-N12 — Évaluation de qualification scientifique et recommandation

## Décision proposée

**A — `READY_FOR_OWNER_CLOSED_BOUNDED_DECISION`**, uniquement pour le benchmark manufacturé AR : contact sans frottement TET4, surface de contact plane figée, chargements et matériau du plan, familles de maillage M1–M5 et seuils N03/AJ inchangés. La décision de clôture reste à l’Owner. Ce rapport n’attribue pas `CLOSED_BOUNDED`, `VERIFIED_BOUNDED` au C02 global, une qualification générale, ni une équivalence Docker.

Les critères prospectifs approuvés sont tous démontrés : ratios M5/M1 déplacement et pression strictement sous 0,9; décroissance d’erreur énergétique; gate de front M2–M5 à `≤1hx`; classification partiellement active avec couverture de toutes les rangées; contrôles KKT, stationnarité, force/moment, travail et cohérence d’énergie. La preuve support manquante au résumé AQ a été retrouvée dans la sortie primaire AQ archivée : elle n’a pas été calculée ni inférée par N12.

## Tableau scientifique M1–M5

| Niveau | Origine des valeurs | `E_u` relative | `E_p` relative | `E_U` (√J) | Énergie FE (J) | Front max (`m`) | Front max / `hx` | Erreur support force (N) | Erreur support moment (N·m) | Statut du niveau / preuve |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| M1 | AQ, sortie historique | 0.0115305167 | 0.4638912089 | 0.06464430373 | 1.47758032285 | 0 (alias d’alignement) | 0 (diagnostic seulement) | 6.4384997429 | 7.8613874952 | AQ PASS; front non admissible comme ancre |
| M2 | AQ, sortie historique; front reconstruit hors ligne N11 | 0.0058533452 | 0.259359 | 0.04037444321 | 1.48466496920 | 0.25 | 1.0 | 0.6282485658 | 2.4672924465 | AQ PASS; front N11 PASS |
| M3 | AQ, sortie historique; front reconstruit hors ligne N11 | 0.0034192486 | 0.1560722560 | 0.02869720611 | 1.48544229380 | 0.1666666667 | 0.9999999999999998 | 0.2542069761 | 1.2402501535 | AQ PASS; front N11 PASS |
| M4 | N10, exécution native | 0.002251612 | 0.1060965 | 0.02213238493 | 1.48578711279 | 0.125 | 1.0 | 0.0762315739 | 0.6517179872 | N10 `1 passed`; critères M4 PASS |
| M5 | N10, exécution native | 0.001585991 | 0.07790737 | 0.01797265767 | 1.48594497175 | 0.1 | 0.9999999999999998 | 0.0017856317 | 0.3765226075 | N10 `1 passed`; critères M5 PASS |

L’énergie continue exacte est `1.486108265595 J`. Les comparaisons des réactions d’appui portent sur les résultantes et moments FE contre l’intégrale analytique de traction en tête; le protocole demande leur publication, mais ne fixe aucun seuil de discrétisation supplémentaire. Les valeurs d’appui M1–M3 viennent directement du stdout AQ original, et non d’une interpolation ou d’un calcul postérieur. Pour la provenance détaillée et les identités campagne par campagne, voir la [matrice des exigences](wp_c02_n12_closure_requirements_matrix.md) et l’archive N11.

## Verdicts par critère prospectif

| Critère N03 | Valeur observée | Règle | Verdict | Marge / commentaire |
|---|---:|---:|---|---|
| Déplacement M5/M1 | `0.13754746109833504` | `<0.9` | PASS | marge `0.7624525389` |
| Pression M5/M1 | `0.16794327502438183` | `<0.9` | PASS | marge `0.7320567250` |
| Erreur énergétique M5 vs M1 | `0.01797265767 < 0.06464430373 √J` | strictement décroissante endpoints | PASS | baisse `0.04667164606 √J` |
| Front M2 | `1.0hx` | `≤1hx` | PASS | seuil atteint, marge nulle |
| Front M3 | `0.9999999999999998hx` | `≤1hx` | PASS | représentation flottante du seuil |
| Front M4 | `1.0hx` | `≤1hx` | PASS | seuil atteint, marge nulle |
| Front M5 | `0.9999999999999998hx` | `≤1hx` | PASS | représentation flottante du seuil |
| État actif/ouvert et couverture | M2: 3/3 lignes; M3: 4/4; M4: 5/5; M5: 6/6 | chaque ligne interprétable, partiel, transition unique | PASS | FP/FN M2 `1/0`, M3 `3/0`, M4 `5/0`, M5 `6/0`, tous ≤hx |
| KKT et équilibre | AQ `3 PASS`; N10 M4/M5 toutes mesures sous seuil AJ | seuils AJ gelés | PASS | valeurs et identités consignées dans les preuves sources |
| Réactions supports | M1–M5 erreurs listées ci-dessus | rapports requis, pas de seuil d’erreur ajouté | PASS / reporté | réactions résiduelles et oracle analytique distinctement présentés dans diagnostics |

Les faux positifs des rangées N11 sont à une cellule du front. Pour certaines rangées M2/M3, l’intervalle du dernier actif au premier ouvert est translaté vers la droite et ne contient pas `x*=0.5 m`. Le contrat AJ/N03 appelle « bracket » la coexistence de nœuds actifs et ouverts; l’erreur du front nodal est un critère séparé. N11 a exposé cette nuance comme P2. Elle ne viole pas le critère gelé, mais le seuil de localisation n’a aucune marge.

## Revue et traçabilité

- N10 : campagnes natives M4/M5, une exécution chacune, `1 passed` chacune; archive et manifeste contrôlés sur 539 fichiers. Revue indépendante N10 sans finding P0/P1/P2.
- N11 : récupération hors ligne de M2/M3 depuis trois diagnostics de stdout AQ original; archive reconstruction vérifiée 8/8. Les tests non FEM de contrat/collecte ont donné 62 PASS en 3,69 s. Revue indépendante N11 favorable : P0=0, P1=0, P2=1 (sémantique du mot bracket, explicitée ci-dessus).
- AQ : 3 PASS historiques, reçu 48/48 vérifié; le hash du stdout archivé correspond au hash du reçu. La fixture AJ source confirme les champs du support et la construction de la référence KKT.
- Les artefacts N10 sont externes au commit N11 et sont rattachés par leur commit/tree, manifeste et manifeste d’intégrité propres. N12 ne modifie pas les campagnes AQ/N10/N11.

La revue indépendante N12 a examiné la matrice et cette recommandation en lecture seule. Elle a d’abord relevé deux P2 de traçabilité (hashes N11 renvoyés à tort au rapport d’évaluation et identifiants de campagnes non nommés dans l’en-tête); les deux ont été corrigés et recontrôlés par le reviewer. Résultat final de revue : **P0=0, P1=0, P2 ouvert=0**. Le détail est consigné dans [la revue indépendante N12](wp_c02_n12_independent_review.md).

## Limites et séparation des statuts

1. **Absence de preuve asymptotique :** limite explicitement prévue par AR §§7.2, 7.3 et 10; le protocole ne permet pas de qualifier une pente observée d’ordre asymptotique. Ce n’est pas un critère bloquant de la clôture *bornée* approuvée.
2. **Front à `1hx` :** la valeur `≤1hx` est exactement le seuil existant. Aucun seuil plus strict n’est ajouté après observation. Il n’y a pas de marge de robustesse, ce qui doit rester dans la décision Owner.
3. **Brackets :** la définition n’impose pas l’encadrement géométrique du front analytique dans l’intervalle discret. C’est une limite de l’oracle, divulguée; pas un échec au contrat N03 actuel.
4. **Réactions d’appui M1–M3 :** le baseline et le résumé AQ les étiquetaient non enregistrées; le stdout AQ conservé les contient. N12 s’appuie sur ces données primaires. La comparaison est une validation par oracle analytique et construction KKT indépendante à l’intérieur du benchmark, pas une validation externe du solveur.
5. **Équivalence Docker :** aucune n’est revendiquée. Le N03 autorise une campagne native bornée; l’absence d’équivalence est donc une limite de portée, non un critère qui bloque cette décision.
6. **N06/N08 FAIL :** restent `FAIL` dans leurs archives. Le N10 est un nouveau RUN distinct, autorisé sous une identité et un collecteur corrigés; ce résultat ne réécrit pas les échecs historiques.
7. **Qualification globale :** le rapport C02 unifié reste `OPEN_PENDING_OWNER_REVIEW`; qualification générale du contact `NOT_ACQUIRED`. Les branches AF/AQ/AR, les échecs Docker historiques, les limitations de robustesse et les autres gates ne sont pas promus par une décision bornée AR.

## Recommandation à l’Owner

La preuve permet de soumettre une **décision Owner de clôture scientifique bornée** pour le benchmark exact décrit ici. La décision doit nommer le périmètre TET4/face figée/manufacturé, ses critères, le caractère historique Docker de M1–M3, la campagne native M4/M5, l’absence de marge sous le seuil du front, et l’absence de claim asymptotique ou général. L’Owner peut accepter ou refuser cette portée; le rapport N12 n’actualise pas à lui seul `WP_C02_STATUS` et n’accorde ni `CLOSED_BOUNDED` ni `VERIFIED_BOUNDED`.
