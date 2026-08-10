---
doc_id: DOC-VNV-CONTACT-CODEASTER-FOLDED-SEARCH-007
revision: 0.1
status: experimental
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Correlation Code_Aster : recherche autonome sur surface pliee

`VNV-CONTACT-CODEASTER-FOLDED-SEARCH-007` compare le patch QF_solver de trois
noeuds esclaves a un triangle esclave DKT Code_Aster, en regard de deux
triangles maitres plies. Code_Aster `18.1.0` est execute dans l'image Docker
epinglee avec `DEFI_CONTACT`, `CONTINUE`, sans frottement et
`REAC_GEOM="AUTOMATIQUE"`. Aucun etat actif ni facette finale n'est impose.

La moyenne des trois deplacements esclaves est l'observable comparee. Le seuil
est `1 %`; la campagne controle aussi que QF_solver a relocalise ses trois
noeuds vers la facette `1`.

```powershell
python .\scripts\run_code_aster_contact_folded_search_vnv.py `
  --output .\results\VNV-CONTACT-CODEASTER-FOLDED-SEARCH-007
```

## Limites

Les surfaces esclaves ne sont pas discretisees identiquement : QF_solver porte
trois noeuds a ressorts, Code_Aster un triangle DKT a ressorts. Cette
correlation est donc une preuve comportementale de recherche autonome sur un
pli, non une correspondance un-a-un des paires de contact. Le grand glissement
et une formulation generale surface-surface restent hors scope.
