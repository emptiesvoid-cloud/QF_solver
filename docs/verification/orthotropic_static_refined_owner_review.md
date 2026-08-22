---
doc_id: DOC-OWNER-ORTHO-STATIC-REFINED-004
revision: 0.1
status: pending_owner_review
applicable_version: 0.2.1a0
promotion_target: stable
reviewer: ""
review_date: ""
---

# Owner review - raffinement statique orthotrope TET4/TET10

## Objet

Cette fiche examine la campagne `VNV-ORTHOTROPIC-SOLID-CONVERGENCE-004`, qui
ajoute trois niveaux TET4 au cas de porte-a-faux orthotrope hors axes. Elle ne
modifie aucun resultat numerique et ne propose pas de promotion automatique.

## Resultats

| Observable | Valeur finale | Limite stable | Verdict |
| --- | ---: | ---: | --- |
| Erreur de fleche TET4 | 2,828 % | 1,000 % | FAIL |
| Erreur d'energie TET4 | 2,856 % | 1,000 % | FAIL |
| Increment de fleche dernier niveau | 1,717 % | 1,000 % | FAIL |
| Residu libre maximal | 2,109e-11 | 1e-8 | PASS |
| Erreur de fleche TET10 | 0,292 % | 1,000 % | PASS |

Les niveaux TET4 sont `215`, `440`, `1 187`, `2 607`, `4 951`, `9 820`,
`23 434`, `53 224` et `112 076` elements. L'erreur diminue monotoniquement,
mais le critere de promotion `stable` n'est pas atteint.

## Decision a renseigner par le Owner

1. Les trois niveaux supplementaires et la tendance de convergence sont-ils
   acceptes comme preuve de progression ?
2. La limite de `1 %` est-elle maintenue sans exception pour ce scope ?
3. La decision est-elle `more_evidence_required` tant que TET4 reste au-dessus
   de `1 %`, ou une justification mecanique formelle est-elle demandee ?

## Reproductibilite

```powershell
python -m pytest tests\verification\test_stable_refinement_evidence.py -q
```

Les preuves compactes sont dans
`qualification/vnv/orthotropic_solid_convergence_refined/reference/`.
Les niveaux fins utilisent des fichiers `summary.json` afin d'eviter une
serialisation nodale monolithique.
