---
doc_id: DOC-OWNER-MITC3-LAMINATE-DYNAMIC-020
revision: 0.1
status: pending_owner_review
applicable_version: 0.2.1a0
promotion_target: stable
reviewer: ""
review_date: ""
---

# Owner review - MITC3 multicouche dynamique, raffinement strict

## Resultats

| Observable | Valeur fine | Limite stable | Verdict |
| --- | ---: | ---: | --- |
| Frequences modales | 1,778 % | 1,000 % | FAIL |
| Historique Newmark | 5,558 % | 1,000 % | FAIL |
| Reponse harmonique | 3,275 % | 1,000 % | FAIL |
| Residu modal | 1,082e-08 | 1e-7 | PASS |
| Residu dynamique | 6,849e-11 | 1e-7 | PASS |

La campagne compare le meme stratifié `[0/90/90/0]`, les memes blocages et les
memes protocoles a quatre niveaux `8x2`, `12x3`, `16x4` et `24x6`, avec
Code_Aster 18.1 DST/TRIA3. Le calcul externe est reproductible, mais la
promotion stable est bloquee par la regle d'erreur a 1 %.

## Questions Owner

1. Les quatre niveaux de maillage sont-ils acceptes comme preuve de tendance ?
2. La limite stricte de 1 % est-elle maintenue pour les trois observables ?
3. La decision est-elle `more_evidence_required` tant que les erreurs restent
   superieures a 1 % ?

## Reproductibilite

```powershell
python .\scripts\run_code_aster_mitc3_laminate_dynamic_refinement_vnv.py `
  --output .\results\VNV-MITC3-LAMINATE-DYNAMICS-REFINEMENT-CODEASTER-DST-020 `
  --levels 8x2 12x3 16x4 24x6
```
