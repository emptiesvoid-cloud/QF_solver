---
doc_id: DOC-OWNER-PROMOTION-PROTOCOL-001
revision: 0.1
status: controlled
applicable_version: 0.2.1a0
decision: pending
certification_claim: none
---

# Protocole de promotion Owner

Une Owner review distingue désormais deux informations :

1. `decision` décrit l'acceptation d'usage du périmètre (`accepted_with_recommendations`,
   `accepted_for_bounded_engineering_use` ou `more_evidence_required`).
2. `promotion_target` décrit la maturité visée (`stable`, `owner_accepted`,
   `experimental` ou `research`).

Dans le paquet de revue, la colonne « Cible Owner » reste `PENDING` tant que
le fichier signé n'a pas été contrôlé. Elle ne doit pas être déduite de la
colonne « Cible technique ».

Exemple pour une promotion vers `stable` :

```json
{
  "scope": "tet4-linear-static",
  "decision": "accepted_with_recommendations",
  "promotion_target": "stable",
  "signature": {
    "name": "Nom du Owner",
    "date": "YYYY-MM-DD"
  }
}
```

La commande de contrôle est :

```powershell
python .\qf_solver.py owner-review-check `
  --input .\qualification\reviews\review.json `
  --scope tet4-linear-static `
  --require-decision `
  --target-maturity stable
```

Cette commande vérifie la structure, la signature et la cohérence de la cible.
Elle ne modifie jamais `qualification/element_analysis_matrix.json`. La
promotion effective doit rester une action de release explicite après audit des
critères techniques et conservation de la preuve signée.
