---
doc_id: DOC-REF-GMSH-001
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Import Gmsh MSH 4.1

## Perimetre

QF_solver lit MSH 4.1 ASCII et binaire par l'API Python officielle Gmsh. Une
importation contient une seule famille structurelle parmi `TET4`, `TET10` et
`MITC4`. Les entites et groupes physiques restent l'autorite pour affecter
materiaux, blocages et charges.

Installation optionnelle:

```powershell
python -m pip install -e ".[mesh]"
```

L'absence de Gmsh produit `InfrastructureError` et le code de sortie `5`.

## Fichier compagnon

Le MSH ne porte pas toute la physique. Un JSON strict associe les groupes:

```json
{
  "schema_version": 1,
  "mesh_scale_to_m": 0.001,
  "units": {"system": "SI"},
  "verification_profile": "engineering",
  "analysis": {"type": "linear_static", "method": "direct"},
  "materials": {
    "steel": {"type": "isotropic_3d", "E": 210000000000.0, "nu": 0.3, "density": 7800.0}
  },
  "groups": [
    {
      "name": "volume",
      "dimension": 3,
      "actions": [{"type": "elements", "element_type": "TET4", "material": "steel"}]
    },
    {
      "name": "encastrement",
      "dimension": 2,
      "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]
    },
    {
      "name": "pression",
      "dimension": 2,
      "actions": [{"type": "pressure", "value": 1000000.0}]
    }
  ]
}
```

`mesh_scale_to_m` est obligatoire. Il convertit uniquement les coordonnees;
les grandeurs mecaniques du setup doivent deja etre coherentes avec le systeme
declare.

## Actions physiques

| Action | Dimension habituelle | Donnees | Effet |
| --- | ---: | --- | --- |
| `elements` | 3 pour solides, 2 pour coque | type, materiau | affecte toutes les cellules structurelles |
| `fixed_dofs` | 0, 1 ou 2 | liste de ddl | bloque les noeuds du groupe |
| `nodal_load` | 0, 1 ou 2 | ddl, valeur | ajoute la valeur a chaque noeud du groupe |
| `pressure` | 2 | scalaire | pression compressive suivant la normale |
| `surface_traction` | 2 | vecteur | traction globale ou locale |
| `edge_traction` | 1 | vecteur | charge d'arete MITC4 |
| `gravity` | groupe d'elements | acceleration | force $\rho\mathbf g$ |
| `body_force` | groupe d'elements | densite de force | charge volumique imposee |

## Association topologique

Une surface solide doit correspondre exactement a une face d'un seul element
parent. Pour TET10, les six identifiants de la face sont verifies. Une courbe
MITC4 doit correspondre a une arete d'un seul quadrangle. Une frontiere sans
parent, partagee par plusieurs parents ou d'ordre incompatible est rejetee.

## Orientation

Par defaut, un tetraedre inverse est refuse. L'option
`--repair-tetra-orientation` autorise une permutation controlee TET4 ou TET10;
le rapport indique le nombre de reparations. Pour TET10, tous les noeuds
d'arete sont permutes avec les sommets. MITC4 n'est jamais reoriente
automatiquement.

## CLI

```powershell
qf-solver import-mesh `
  --mesh modele.msh `
  --setup modele.setup.json `
  --output modele.json `
  --report import_report.json
```

## API

```python
from qf_solver import import_gmsh_model, save_model

imported = import_gmsh_model("modele.msh", "modele.setup.json")
save_model(imported.model, "modele.json")
print(imported.report.to_dict())
```

## Rapport et refus

Le rapport contient version MSH/Gmsh, empreintes des deux entrees, format
binaire, groupes, comptages d'actions, famille, nombre de noeuds/elements,
reparations, avertissements et verdict du validateur de maillage.

Sont notamment refuses: groupe absent, cellule non supportee, element sans
materiau, conflit de materiaux, famille mixte, noeud manquant, frontiere non
conforme, element degenere ou orientation interdite.

Code: `solveur/mesh/gmsh_reader.py`, `solveur/mesh/gmsh_importer.py`.
Tests: `tests/unit/test_gmsh_importer.py`,
`tests/integration/test_gmsh_import_cli.py`. Exigences: `REQ-IO-001`,
`REQ-MESH-001`, `REQ-MESH-002`. Reference:
[REF-GMSH-41](references.md#ref-gmsh-41).
