---
doc_id: DOC-LEGACY-MANUAL-001
revision: 2.0
status: superseded
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Manuel theorique des elements finis

!!! warning "Document remplace"
    Le manuel monolithique a ete migre vers le site technique modulaire afin
    d'eviter deux formulations concurrentes. Cette page ne contient plus de
    resultats ni de demonstrations maintenus.

Les formulations applicables sont maintenant reparties entre :

- [fondements FEM](fondements/travaux_virtuels.md) ;
- [conventions et reperes](fondements/conventions.md) ;
- [element TET4](elements/tet4.md) ;
- [element TET10](elements/tet10.md) ;
- [element MITC4](elements/mitc4.md) ;
- [solveurs disponibles](solveurs/index.md) ;
- [demonstrations reproductibles](demonstrations/index.md) ;
- [verification et preuves](verification/index.md).

Construire et servir le site avec :

```powershell
python .\scripts\build_docs.py --profile engineering
python .\scripts\serve_docs.py
```
