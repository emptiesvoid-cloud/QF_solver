---
doc_id: DOC-LEGACY-SHEAR-001
revision: 0.1
status: draft
applicable_version: 0.2.1-alpha
reviewer: ""
approver: ""
---

# Correlation avec la litterature du cisaillement

Ce document racine est conserve pour compatibilite. La formulation maintenue
de Reissner-Mindlin, les points de tying MITC4, le shear locking, les essais et
les references primaires sont dans :

- [`docs/elements/mitc4.md`](../../elements/mitc4.md) ;
- [`docs/demonstrations/coques.md`](../../demonstrations/coques.md) ;
- [`docs/reference/references.md`](../references.md).

Regenerer les artefacts documentaires locaux avec :

```powershell
python .\scripts\build_docs.py --profile engineering
python .\scripts\build_technical_latex.py
```
