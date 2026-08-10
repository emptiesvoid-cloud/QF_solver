---
doc_id: DOC-START-003
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Creer un cas

Un modele JSON v1 contient au minimum `analysis`, `nodes`, `elements`,
`materials`, `fixed_dofs` et `loads`. Le systeme SI est impose pour un profil
de qualification.

```json
{
  "schema_version": 1,
  "units": {"system": "SI"},
  "analysis": {"type": "linear_static", "method": "direct"},
  "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
  "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
  "materials": {"steel": {"type": "isotropic_3d", "E": 2.1e11, "nu": 0.3}},
  "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ"]}],
  "loads": [{"node": 1, "dof": "UX", "value": 1000.0}]
}
```

Ce fragment illustre la syntaxe, pas un blocage mecaniquement suffisant. La
procedure complete et tous les champs sont decrits dans le
[schema JSON](../schema_json.md).

## Checklist de modelisation

- choisir une topologie compatible avec les champs attendus;
- orienter positivement les elements;
- definir materiau, densite et epaisseur lorsque necessaires;
- bloquer uniquement les modes rigides physiques;
- verifier les unites, signes et resultantes des charges;
- etudier la convergence avant d'interpreter une contrainte locale.
