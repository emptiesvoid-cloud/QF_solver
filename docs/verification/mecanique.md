---
doc_id: DOC-VV-001
revision: 0.1
status: draft controle
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Verification mecanique

## Hierarchie des preuves

| Niveau | Exemple | Ce qu'il detecte |
| --- | --- | --- |
| Identite mathematique | Symetrie, partition de l'unite | Erreur de formulation locale |
| Mode rigide | Six modes 3D | Couplage ou signe parasite |
| Patch test | Champ constant/affine | Interpolation, assemblage et transformation |
| Solution analytique | Traction, oscillateur | Erreur quantitative independante |
| Benchmark publie | Scordelis-Lo | Comportement combine et convergence |
| Correlation experimentale | Essai structure/materiau | Adequation au reel dans un domaine borne |

## Etude de convergence

Definir une grandeur $Q_h$ et au moins trois tailles caracteristiques $h$.
Examiner l'erreur par rapport a une reference ou la difference entre niveaux:

$$
e_h=\frac{|Q_h-Q_{ref}|}{\max(|Q_{ref}|,Q_0)}.
$$

Le raffinement doit conserver geometrie, charges resultantement equivalentes
et conditions limites. Pour une contrainte singuliere, suivre une resultante,
une energie ou une contrainte a distance fixee plutot que le maximum nodal.

## Independence

Une valeur de non-regression protegee par snapshot n'est pas une reference
independante. Le registre classe explicitement `analytic`,
`equilibrium_closed_form`, `third_party`, `experimental` et
`non_regression`. Un cas candidat remplacement exige au moins une reference
independante.
