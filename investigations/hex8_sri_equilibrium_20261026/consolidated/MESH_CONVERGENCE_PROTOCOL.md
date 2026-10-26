# Protocole de convergence spatiale

**État : `PREPARED_NOT_AUTHORIZED` — aucun cas de cette matrice n’a été exécuté.**

## Maillages appariés

Le plan croise HEX8 standard, SRI historique (contrôle négatif figé) et SRI corrigé avec `ν=.3,.45,.49,.499,.4999`, dimensions `20×1×1 m`, `E=1e6 Pa`, mêmes charges et même encastrement. Quatre raffinements de toutes les directions sont proposés :

| `nx×ny×nz` | HEX8 | Nœuds | DDL totaux | Bloqués | Libres | Une matrice K dense, plancher mémoire |
|---|---:|---:|---:|---:|---:|---:|
| `4×2×2` | 16 | 45 | 135 | 27 | 108 | 0,14 MiB |
| `8×4×4` | 128 | 225 | 675 | 75 | 600 | 3,47 MiB |
| `16×8×8` | 1 024 | 1 377 | 4 131 | 243 | 3 888 | 130 MiB |
| `32×16×16` | 8 192 | 9 537 | 28 611 | 867 | 27 744 | 6 250 MiB |

Le dernier cas impose un opérateur global creux avant l’exécution; les budgets de la matrice sont des enveloppes à valider sur l’environnement, pas des mesures. Le maillage 4×2×2 reprend le cas historique. Les raffinements all-axis changent les tailles relatives des éléments tout en conservant les mêmes proportions géométriques.

## Mesures et analyse

À chaque niveau, garder déplacement `UZ` signé moyen de la face chargée, déplacement en un point de référence, énergie, travail, résidus libres, réactions, fermeture force/moment, contraintes/déformations projetées, qualité Jacobienne, conditionnement si une estimation conforme au budget est raisonnable, temps et RSS. Conserver les champs et les preuves SHA. Comparer chaque formulation à une référence 3D indépendante vérifiée; la poutre Timoshenko sert au sens de grandeur et à une tendance seulement.

Aucun ordre n’est supposé. Avec un rapport de raffinement 2, si une erreur `e_h` mesurée contre une référence indépendante est disponible, rapporter `p_obs=log(e_h/e_{h/2})/log(2)` uniquement lorsque les erreurs sont positives et dans un régime cohérent. Rapporter aussi différences successives des quantités sans référence, les champs projetés et la tendance; ne pas baptiser cela une erreur absolue.

Seuils proposés à geler avant toute autorisation : résidu libre relatif `≤1e−7`, fermetures force et moment `≤1e−6`, identité énergie `|2U−W|/|W|≤1e−8`; entre les deux derniers niveaux, changement du déplacement moyen et de l’énergie `≤2 %`; au niveau fin, erreur du déplacement de référence 3D `≤5 %`. Les trois derniers sont des seuils de proposition, pas des critères passés/validés. Ils doivent être approuvés avec l’oracle et fixés avant l’accès aux résultats. Ils ne seront pas ajustés après résultat.

## Budget proposé

Les budgets par solve proposés dans `NEXT_CAMPAIGN_MATRIX.csv` sont 180/300/900/3600 s et RSS plafond prévisionnel 512/1024/4096/16384 MiB par maillage. Une tentative par configuration, séquentiellement, sans retry automatique. Les 60 cas correspondent à 15 couples (3 formulations × 5 `ν`) à chacun des quatre niveaux : enveloppe cumulée d’environ 20,75 h au temps maximal planifié, hors préparation et revue; enveloppe mémoire maximale séquentielle 16 GiB, avec mise en œuvre creuse nécessaire. Cette estimation est conservatrice et à revoir après un préflight non solveur. Aucun budget d’une autre campagne n’est prélevé.

Nodeid proposé : `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[<formulation>-nu_<nu>-<nx>x<ny>x<nz>]`. Les 60 chaînes proposées, les DDL, seuils, ressources et tentatives sont dans le CSV. Les cas de patch, distorsion et stabilité complémentaires sont spécifiés dans `SUPPLEMENTAL_VALIDATION_MATRIX.csv`. Ces tests ne sont ni implémentés, ni inscrits, ni autorisés.
