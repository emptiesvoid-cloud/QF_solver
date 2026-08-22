# Verification discret multi-DDL : candidat stable

| Champ | Valeur |
| --- | --- |
| Etude | `VNV-DISCRETE-MULTIDOF-ANALYTIC-001` |
| Domaine | Ressorts lineaires et masses concentrees, translations, petits deplacements |
| Statut technique | `PASS_TECHNICAL_VERIFICATION` |
| Maturite | candidat a l'extension du domaine, Owner Review encore requise |

## Objectif

Le cas Code_Aster existant est un systeme ressort-masse translationnel mono-DDL.
Cette campagne verifie une chaine assemblee de trois noeuds, avec deux ressorts
entre noeuds, un ressort au sol et deux masses concentrees. Les translations
`UX`, `UY` et `UZ` sont presentes, soit six DDL libres apres blocage du noeud 0.

Les resultats QF_solver sont compares a une reference matricielle independante
construite a partir des matrices assemblees `K` et `M`. La reference ne reutilise
pas les resultats de l'analyse QF_solver.

## Resultats

| Analyse | Ecart relatif | Limite | Verdict |
| --- | ---: | ---: | --- |
| Statique `K u = f` | `7,892e-15 %` | `1e-8 %` | PASS |
| Trois frequences propres | `2,004e-14 %` | `1e-8 %` | PASS |
| Historique Newmark | `1,986e-12 %` | `1e-8 %` | PASS |
| Reponse harmonique | `1,398e-14 %` | `1e-8 %` | PASS |
| Derive energetique Newmark | `0` | `1e-8` | PASS |

La campagne externe Code_Aster mono-DDL reste la preuve de correlation externe.
La presente etude ajoute une preuve de bonne gestion de l'assemblage, de la
masse, des matrices couplees et des methodes lineaires sur plusieurs DDL.

![Resultats multi-DDL](../../qualification/vnv/discrete_multidof_2026-08-21/discrete_multidof_results.png)

## Limites maintenues

Cette preuve ne couvre pas encore les inerties rotatoires excentrees, les
orientations locales, les liaisons MPC/RBE, les ressorts non lineaires ou les
assemblages comportant des elements flexibles. Elle ne signe aucune promotion
automatique vers `stable`.

## Artefacts

- [`summary.json`](../../qualification/vnv/discrete_multidof_2026-08-21/summary.json)
- [`report.md`](../../qualification/vnv/discrete_multidof_2026-08-21/report.md)
- [`discrete_multidof_results.png`](../../qualification/vnv/discrete_multidof_2026-08-21/discrete_multidof_results.png)
- [`vnv_manifest.json`](../../qualification/vnv/discrete_multidof_2026-08-21/vnv_manifest.json)

Commande de regeneration :

```powershell
python .\scripts\run_discrete_multidof_campaign.py
```
