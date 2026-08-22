---
doc_id: DOC-RELEASE-VV-021-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.1a0
owner_review: pending
reviewer: ""
approver: ""
---

# Pack V&V de QF_solver 0.2.1a0

## Objet

La version `0.2.1a0` est une alpha consacree a la verification et validation
reproductible. Elle ne remplace pas la baseline `0.2.0a0`, qui reste immuable,
et ne constitue pas une certification externe.

Le registre machine-readable est `qualification/release_vv_0_2_1.json` dans
la racine du depot; le runner le charge depuis ce chemin controle.
Le runner produit un dossier local avec un resume JSON, un rapport Markdown et
un manifeste SHA-256 :

```powershell
python .\qf_solver.py release-vv --output .\results\release_vv_0_2_1
```

Pour executer aussi la campagne officielle de 13 cas :

```powershell
python .\qf_solver.py release-vv `
  --output .\results\release_vv_0_2_1 `
  --execute-campaign
```

## Regles de verdict

`PASS` signifie que les liens de tracabilite et les preuves presentes dans le
checkout satisfont le scope. `WARNING` signifie qu'aucun echec numerique
bloquant n'est declare, mais qu'une preuve candidate, la campagne ou la revue
Owner reste ouverte. `FAIL` signifie qu'un element requis de la release est
invalide ou manquant et bloque le gel.

Seuls les scopes declares `stable` sont des bloqueurs du gate de release. Les
scopes `owner_accepted`, `owner_accepted_experimental_bounded_use`,
`experimental`, `research` et `out_of_acceptance` restent distribues avec
leurs limites explicites, mais ne peuvent pas etre presentes comme stables.
Les combinaisons `unsupported` sont hors perimetre. La presence d'un code,
d'un test ou d'une revue Owner ne transforme jamais a elle seule un statut
experimental en `stable`.

## Revue Owner attendue

Le champ `owner_review` du registre doit etre complete avant le gel final avec
une decision, une date et un commentaire. Cette revue confirme le perimetre
d'usage interne et les exclusions; elle ne doit pas etre formulee comme une
certification independante.

## Artefacts

Le fichier `release_vv_summary.json` est la source machine-readable du verdict.
`release_vv_summary.md` est la lecture Markdown. `release_vv_manifest.json`
empreinte les deux fichiers. Les chemins de travail absolus ne sont pas
publies dans le resume; seules les identites de revision et les empreintes sont
conservees.

La release controle egalement le paquet interne
`qualification/evidence/linear_dynamic_families_2026-08-14/`. Il contient les
resumes et rapports des cinq familles de verification lineaire dynamique. Ce
paquet prouve l'execution interne et son integrite; il ne remplace ni une
correlation Code_Aster ni une decision Owner.

Le resume expose aussi `blocker_summary` et classe les ouvertures entre
`maturity_not_stable`, `evidence_missing`, `external_reference_missing`,
`campaign_not_green`, `owner_review_pending` et `source_dirty`. La campagne
officielle indique séparément si un cas a échoué numériquement ou si ses
contrôles numériques passent mais restent bloqués par la politique de
qualification.

Les tests qui nécessitent le corpus V&V contrôlé sont marqués `evidence`. Ils
sont activés dans la CI documentaire avec `QF_SOLVER_RUN_EVIDENCE=1` ; les
lots locaux standard les ignorent lorsque les artefacts externes ne sont pas
installés, sans transformer leur absence en preuve mécanique.
