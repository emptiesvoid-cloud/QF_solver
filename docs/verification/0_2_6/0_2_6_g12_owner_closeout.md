---
doc_id: DOC-VNV-026-G12-OWNER-001
revision: 0.1
status: owner_closeout
applicable_version: 0.2.6a0
gate: 026-G12
closeout_base_sha: c883f47f83ba18dc4a4294e84b2744962eca614d
execution_source_sha: 81443c20b3f1ec9b742292bc5f880cc10e112a96
---

# 026-G12 — Owner closeout

## Décision

L’Owner clôt `026-G12` comme **PASS_WITH_LIMITATIONS**. Le requirement
`REQ-026-007` est satisfait dans le périmètre déclaré : mesures répétables,
profils de scaling, manifests de benchmark et métadonnées matérielles sont
présents et cohérents.

La décision ne revendique pas une loi universelle de scaling, une qualification
HPC générale, ni une promotion de route ou de formulation.

| Contrôle | Résultat |
| --- | --- |
| Matrice finale | 9 lignes, 2 répétitions, 18/18 PASS |
| Routes | linear_static, modal, linear_buckling, nonlinear_static, geometric_nonlinear_static, contact borné |
| Métriques | finies sur les 18 exécutions |
| Replay | déterministe sur chaque ligne |
| Full solve scaling | 3 000 à 107 811 DOF réels, PASS |
| Probe 300k | PASS assembly-only, 311 469 DOF réels |
| Probe 1M | RESOURCE_LIMITED après 300 s, sans solve |
| Changement fonctionnel dans le closeout | NON |
| Statut officiel | PASS_WITH_LIMITATIONS |

La preuve machine-readable est
[`g12_owner_closeout.json`](../../../qualification/0_2_6/g12_owner_closeout.json).

## Requirement Owner

| Requirement | Décision | Évidence |
| --- | --- | --- |
| `REQ-026-007` — mesures répétables et métadonnées matérielles | `OWNER_APPROVED_FULL` | campagne finale, scaling optimisé, probes et triage de régression |

`FULL` est ici relatif au requirement et au domaine mesuré déclaré. Il ne
signifie pas que chaque route, famille, topologie ou matériel est caractérisé.

## Neutralité numérique et régression

La comparaison optimisée conserve le nombre d’entrées sparse, le checksum de
solution et le résidu ; les résidus restent finis. La formulation, la politique
du solveur et les seuils ne changent pas dans le closeout.

La commande complète unique exécutée pour cette revue était `python -m pytest -q`.
Elle a produit **1849 passed, 184 skipped, 18 failed**. Les 18 échecs sont dans
les familles historiques documentées par
`g12_optimization_regression_triage.json` : version CLI, disponibilité du
sous-processus `git` dans l’audit du registre, audits release/document et
vocabulaire contrôlé G08. Aucun échec spécifique au correctif G12 n’a été
observé ; `NEW_FIX_ONLY_FAILURES = 0` et `REGRESSION_NEUTRAL = YES`.

Les deux probes larges restent honnêtement bornées : 300k mesure uniquement
l’assemblage, tandis que 1M est `RESOURCE_LIMITED` et ne constitue pas un
succès.

## Limites explicites

- la matrice multi-route est une caractérisation compacte et bornée ;
- les temps de solve modal ne sont pas exposés comme phase publique séparée ;
- les lignes J2, TL et contact ne modifient ni ne promeuvent leurs gates ;
- le speedup concerne le chemin mesuré `linear_static`/TET4 de charges et
  d’assemblage, pas le solveur global ;
- les 18 blockers de régression historiques restent des blockers de release
  hors G12.

## Gouvernance

Le contrat G12 reste inchangé. Aucun autre gate n’est modifié par ce closeout.
La maturité reste bornée et toute extension de périmètre exige une nouvelle
preuve et une nouvelle revue Owner.
