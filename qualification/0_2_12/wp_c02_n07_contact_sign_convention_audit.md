# WP-C02-N07 — Audit des conventions de signe et préparation native

## Portée et statut

Le candidat est isolé dans `wp-c02-n07-remediation`, créé depuis le commit N05 autorisé `a0e0359f6cd4423e966a64ffde82bbad4dd20831` (branche N07). Les fichiers N05/N06, archives et rapports historiques sont restés dans leur worktree; les données N06 n’ont été lues qu’en mode hors ligne.

Statuts conservés : `N06_M4=FAIL`, `N06_M5=FAIL`, `WP_C02_SPATIAL_CONVERGENCE=NOT_ACQUIRED`, `GENERAL_CONTACT_QUALIFICATION=NOT_ACQUIRED`. Les campagnes Docker restent `FAIL_CLOSED`.

N07 interdit le RUN FEM, toute modification du solveur de production, des équations ou des critères AR. Aucun solveur, assemblage, calcul modal ou résolution de contact n’a été déclenché.

## A. Conventions mécaniques établies

Le contrat a été vérifié dans le solveur (`support.py`, matrice selle et export de `pressure`), les réactions d’appui de `static.py`/`audit.py`, les définitions du test AJ et les identités de travail/équilibre.

| Grandeur | Convention de production | Convention WP-C02-AR et formule de collecte |
|---|---|---|
| Gap `g` | `g = g0 + C u`; `C` mesure le déplacement relatif dans la normale, côté esclave positif et côté maître négatif. Unité m. | Plan rigide horizontal : `n=+ez`, `g=0,001+uz`, `g≥0`. |
| Multiplicateur selle brut `μ` | Le système `[[K,Cᵀ],[C,0]] [u,μ] = [f,−g0]` donne un multiplicateur algébrique de signe opposé à la compression physique. Unité N. | Il ne faut pas l’utiliser directement comme force physique de compression. |
| Pression/force de ligne `p` | `p=−μ`; `_pressures` exporte la valeur déjà positive en compression dans `contact.pressure`. Ce champ est une force nodale en N malgré son nom. | `λ_AR = p = row["pressure"]` (sans signe supplémentaire); `p≥0`; `g p=0`. |
| Pression surfacique | Le champ de ligne est une force N; aucune aire n’intervient dans l’équation KKT. | `q_i=p_i/A_i` en Pa, avec l’aire tributaire AR gelée. L’oracle exact AJ est comparé à cette densité. |
| Force sur l’esclave | La force physique est `+p n`; le solveur considère la contribution selle `Cᵀ μ`, équivalente à `−Cᵀp` dans l’équilibre interne. | Dans AR, `Fcontact_i=p_i ez`; sa résultante attendue est positive z. |
| Force sur le maître rigide | Action/réaction `−p n`, distribuée selon les poids de projection du contact; le maître est géométriquement fixe dans cette campagne. | Pas de vecteur maître distinct dans l’archive N06; l’action opposée est imposée par le contrat mécanique, non mesurée séparément. |
| Réaction d’appui | Le solveur exporte le résidu `K u−f` aux DDL prescrits : réaction exercée par l’appui sur le corps, en N. | Elle s’ajoute à `Fext` et `Fcontact` pour fermer le bilan du corps. Elle ne reçoit pas de signe ajouté au collecteur. |
| Moments | Moments globaux calculés par `Σ r×F` autour de l’origine globale, unités N·m. | La même opération s’applique aux charges, réactions et forces de contact; aucun changement d’origine n’est requis dans cet oracle. |
| Complémentarité et travail | `g≥0`, `p≥0`, `gp=0`. | Sur une rangée active au plan fixe, `uz=−0,001 m` et `p uz=−0,001p J`; identité de travail du test AJ conservée. |

Le finding N06 est donc circonscrit : le collecteur utilisait `-row["pressure"]` alors que le solveur avait déjà effectué `p=−μ`. Les vecteurs dérivés M4/M5, leurs pressions, leurs forces, les classifications et le front étaient inversés. Les données N06 restent FAIL telles qu’archivées; les valeurs réinterprétées figurent uniquement dans le rapport `OFFLINE_DIAGNOSTIC_ONLY`.

## B. Correctif du collecteur

Le correctif expérimental ajoute un décodeur strict des lignes de contact : valeurs finies, champs requis, normales unitaires et identiques à la normale gelée `+Z`, aires positives, IDs cohérents. Il interprète `row["pressure"]` comme la force de compression physique en N et calcule `Pa=N/m²` seulement en divisant par l’aire tributaire. Les forces nodales sont montées par `p n`; la normale AR est contrôlée avant calcul.

Le test scientifique ne nie plus la pression de ligne. Il emploie la force physique positive pour la classification, la stationnarité, la complémentarité, les bilans, le travail, la pression surfacique et la trace de front. Les valeurs de min/max sur un ensemble actif vide deviennent `null`, sans produire `Infinity`/`-Infinity`. Les unités et formules des seuils ne changent pas.

Le diff ne modifie aucun fichier du noyau FEM. Le plan de maillage, le modèle AJ, les chargements, les matériaux, les conditions aux limites et les seuils AR sont inchangés.

## C. Priorité des statuts et diagnostics manquants

Le rapporteur lit maintenant `run_ledger.json`. Un état pytest `SCIENTIFIC_CRITERION_FAILURE` reste prioritaire même si un fichier diagnostic est mal sérialisé, incomplet ou contient des mesures dérivées manquantes. Les métriques absentes sont notées `NOT_EVALUATED`; une archive invalide sans échec scientifique explicite reste `ERROR_COLLECTION`. Timeout et interruption d’infrastructure restent `NOT_EVALUATED`. Une archive portant une identité de campagne (`archive_integrity_manifest.json` ou manifeste d’exécution) sans `run_ledger.json` est une erreur de collecte et ne peut pas être évaluée PASS.

Le collecteur refuse aussi une force de contact négative au-delà de la tolérance AR `force_tolerance_n=1e-7 N`, une force compressive au-dessus de cette tolérance avec un drapeau inactif, ou une force de traction au-delà de la tolérance avec un drapeau actif. Les cas biactifs proches de zéro restent permis.

N06 reste classé FAIL par son ledger, et non ERROR_COLLECTION. La limitation secondaire `strict_active_max_gap_m=null` est exposée comme donnée non évaluée; elle n’efface pas l’échec direct du critère d’activité partielle.

## D. Analyse hors ligne des archives N06

Les vecteurs bruts enregistrés sont suffisants pour corriger uniquement la transformation de signe et recalculer les pressions, KKT de contact, résultantes, moments, bilans, erreurs de pression et fronts. Pour cette analyse, `p_corrigé = −multipliers_N06`, parce que N06 avait stocké `multipliers_N06 = −row.pressure`. Aucun octet de l’archive source n’a été modifié. Les fichiers de sortie séparés se trouvent dans `qualification/0_2_12/wpc02_n07_offline_diagnostics/`.

| Mesure hors ligne | M4 | M5 | Critère prospectif / lecture |
|---|---:|---:|---|
| Lignes actives / ouvertes | 30 / 15 | 42 / 24 | Contact partiellement actif, compatible avec les drapeaux du solveur |
| Force de contact min…max N | 0…17,8572 | 0…12,9099 | `p≥0`, PASS sur les champs transformés |
| Erreur L2 pression vs AJ | 0,106097 | 0,0779074 | M5/M1 historique = 0,167943 `<0,9`, PASS hors ligne |
| Erreur relative déplacement (inchangée) | 0,00225161 | 0,00158599 | M5/M1 = 0,137547 `<0,9`, PASS sur cette mesure |
| Norme d’erreur énergétique (inchangée) | 0,0221324 | 0,0179727 | M5 < M1 historique 0,0646443, PASS sur endpoint |
| Résultante de contact z N | 166,742898 | 166,668452 | Exact AJ = 166,666667; erreurs relatives 4,5739e−4 / 1,0718e−5 |
| Bilan relatif de force, corps | 5,54e−14 | 2,55e−14 | Seuil `≤1e−9`, PASS dans le recalcul hors ligne |
| Bilan relatif de moment, corps | 1,22e−14 | 2,94e−14 | Seuil `≤1e−9`, PASS dans le recalcul hors ligne |
| Erreur de complémentarité | 1,98e−13 N·m | 2,28e−12 N·m | Seuil `≤1e−10`, PASS dans le recalcul hors ligne |
| Écart max de multiplicateur à l’oracle QP archivé | 2,54e−8 N | 4,15e−7 N | Seuil `≤1e−6`, PASS; comparaison dépend des champs N06 transformés |
| Rangées avec bracket de front | 5/5 | 6/6 | Couverture locale M4/M5 PASS |
| Erreur max de front / hx | 1,0 | 1,0 | Seuil `≤1`, à la limite |
| Faux positifs / faux négatifs | 5 / 0 | 6 / 0 | Les faux positifs sont à une cellule ou moins; aucun front multiple observé |
| Stationnarité production | NOT_EVALUATED | NOT_EVALUATED | Le vecteur production `internal_force` n’est pas archivé; ne pas l’inférer depuis l’oracle QP |

Ces opérations sont une transformation de champs provenant des mêmes exécutions N06; elles ne constituent ni une seconde exécution, ni une preuve indépendante du solveur. Les mesures de déplacement/énergie sont réutilisées depuis N06 et signalées comme telles. Les résidus d’équilibre QP archivés proviennent de l’oracle indépendant, mais ne remplacent pas le contrôle production. Le déplacement système de l’oracle est proche; l’archive ne contient pas le vecteur de force interne de production nécessaire au recalcul indépendant de sa stationnarité.

**Interprétation :** les données disponibles montrent que le signe inversé du post-traitement explique les anomalies de classification, pression, résultante, moment et comparaison de multiplicateurs. Elles ne démontrent pas un défaut du noyau; elles ne suffisent pas non plus à certifier la stationnarité réelle de production sans les champs internes manquants. Aucun finding de solveur n’est démontré à ce stade.

Ces mesures restent `OFFLINE_DIAGNOSTIC_ONLY`. Elles ne transforment pas `N06_M4=FAIL` ou `N06_M5=FAIL` en PASS.

## E. Traces historiques AQ M2/M3

Les traces par rangée ne peuvent pas être reconstruites à partir des archives retrouvées. Le rapport AQ fournit des agrégats arrondis, erreurs maximales, comptes de faux positifs/négatifs et distances maximales; il n’archive pas, pour chaque nœud, les IDs/coordonnées, gap, pression/multiplicateur, état actif/ouvert/biactif ni les voisins qui encadrent le front. Plusieurs distributions par rangée satisfont les mêmes agrégats : l’inversion n’est pas unique. Le baseline historique marque explicitement les traces comme `NOT_RECORDED_IN_AQ_SUMMARY`; aucun autre export AQ brut n’a été localisé dans les worktrees C02 examinés.

Le gate complet M2–M5 reste donc `NOT_ACQUIRED`. Une collecte/reconstruction par nouveau calcul nécessite une autorisation Owner séparée; ce mandat n’autorise pas ce calcul.

## F. Vérifications préparatoires

- `python -m pytest -q tests/unit/test_wpc02_ar_native_collection_reporting.py` : **46 PASS**, tests purement unitaires/non-FEM. Couverture ajoutée : compression positive, contact ouvert et partiellement actif, action/réaction, force/moment, KKT, pression/unités, front, normales, signes/drapeaux incohérents, données non finies, ledger obligatoire pour archive identifiée, gestion des statuts/archives partielles.
- `git diff --check` : PASS.
- `python -m py_compile` des 5 fichiers Python modifiés (`scripts/freeze_wpc02_ar_native_manifest.py` inclus) : PASS.
- `python -m pytest -q tests/unit/test_wpc02_ar_native_collection_reporting.py tests/unit/test_wpc02_ar_native_manifest_contract.py` : 51 PASS, 5 échecs explicables car le manifeste préparatoire attendu n’existe pas encore dans le candidat; ces tests tentent de lire `wp_c02_ar_native_execution_manifest.json`. Le nouveau manifeste est conditionné à une revue favorable et un commit. Aucun calcul FEM n’a été déclenché par ces tests.
- Vérification du rapporteur en mémoire sur archive N06 : verdict global FAIL, M4 FAIL, M5 FAIL; fichier source archive non modifié.
- `git diff --check` : PASS.
- Les contrôles de contrat de manifeste seront relancés après génération du manifeste externe, laquelle suit commit et revue favorable. Aucun test FEM n’a été lancé.
- Revue indépendante du correctif initial : favorable, 0 P0/P1; elle avait signalé les contrôles force/drapeau, ledger absent et reproductibilité offline comme P2. Les deux premiers sont corrigés et retestés; l’absence d’un script de rejeu versionné reste une limite P2 à signaler.
- Revue indépendante du delta final après durcissements : favorable, 0 P0/P1, gel du code candidat recommandé. Les findings P2 sont consignés dans `wp_c02_n07_independent_review.md` : pas de script versionné de rejeu offline et pas de test dédié au paramétrage du générateur de manifeste.

## G. Gel et étapes suivantes

Le script `freeze_wpc02_ar_native_manifest.py` accepte maintenant les champs `campaign`, `campaign_id` et `archive_relative_path` en arguments, tout en conservant les valeurs N03 historiques par défaut. Aucun gel N03 n’est modifié. Après revue favorable, les corrections et rapports seront commités, HEAD/tree recalculés, puis un manifeste externe N07 distinct sera généré et vérifié. Il restera à relancer les tests de contrat avec ce manifeste et les contrôles statiques avant de présenter l’identité pour une future autorisation Owner. Le script de gel n’a pas de test dédié à ses nouveaux arguments (P2). La procédure de recalcul offline est documentée par les formules et hashes d’entrée/sortie, mais n’a pas encore de script de rejeu versionné (P2).

Même après le gel N07, `GO-RUN-FEM-NATIF` reste non accordé. Il faudra aussi décider comment acquérir les traces historiques manquantes M2/M3 avant de pouvoir satisfaire le critère complet M2–M5. Aucune fusion, publication, équivalence Docker ou promotion de qualification n’est autorisée.
