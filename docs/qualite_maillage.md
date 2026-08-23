---
doc_id: DOC-MESH-001
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Qualite de maillage

La validation maillage retourne un rapport `PASS`, `WARNING` ou `FAIL`.
Les erreurs bloquantes interdisent la resolution. Les avertissements signalent
un calcul possible mais numeriquement fragile.

## Seuils par defaut

Les seuils sont centralises dans `solveur.mesh.quality.MeshQualityThresholds`.

| Famille | Metrique | Seuil | Effet |
| --- | --- | ---: | --- |
| TET4/TET10 | `signed_volume` | `> 1.0e-14` | `FAIL` si non respecte |
| TET4/TET10 | `quality` | `>= 5.0e-2` | `WARNING` si non respecte |
| TET4/TET10 | `radius_ratio` | `>= 5.0e-2` | `WARNING` si non respecte |
| TET4/TET10 | `aspect_ratio` | `<= 20.0` | `WARNING` si non respecte |
| TET4/TET10 | `relative_volume` | `>= 1.0e-4` | `WARNING` si non respecte |
| TET10 | `mid_edge_deviation_ratio_max` | `<= 5.0e-2` | `WARNING` si non respecte |
| TET10 | `sampled_jacobian_min` | `> 1.0e-14` | `FAIL` si non respecte |
| TET10 | `sampled_jacobian_ratio` | `>= 5.0e-2` | `WARNING` si non respecte |
| MITC4 | `aspect_ratio` | `<= 10.0` | `WARNING` si non respecte |
| MITC4 | `planarity_ratio` | `<= 1.0e-3` | `WARNING` si non respecte |
| MITC4 | `angle_min_degrees` | `>= 30.0` | `WARNING` si non respecte |
| MITC4 | `angle_max_degrees` | `<= 150.0` | `WARNING` si non respecte |
| MITC4 | `warpage_degrees` | `<= 5.0` | `WARNING` si non respecte |

Pour `TET10`, le controle combine le tetraedre des quatre coins, l'ecart des
six noeuds d'arete a leur milieu droit et le jacobien sur un reseau
barycentrique ferme de 35 points. Le jacobien est aussi controle aux points de
rigidite et aux 125 points de masse. Ce controle par echantillonnage ne constitue
pas une preuve analytique de positivite en tout point d'une geometrie courbe.

## Rapport JSON

`check-mesh --json-report mesh_report.json` expose:

- `details.quality_thresholds`: seuils utilises;
- `details.element_quality`: metriques par element;
- `quality_status`: `PASS`, `WARNING` ou `FAIL` au niveau elementaire;
- `quality_warnings`: avertissements locaux de qualite.

## Usage API avec seuils relaxes

```python
from qf_solver import MeshQualityThresholds, MeshValidator, load_model

model = load_model("examples/tet4_static.json")
thresholds = MeshQualityThresholds(tet_max_aspect_ratio=30.0)
report = MeshValidator(thresholds).validate(model)
```

Les seuils relaxes sont utiles en exploration. Pour une verification stricte,
il vaut mieux durcir les seuils et conserver `WARNING` comme signal de revue
ingenieur.
