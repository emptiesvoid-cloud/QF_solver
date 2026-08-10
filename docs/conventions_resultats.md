---
doc_id: DOC-REF-005
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Conventions de resultats

Ce document precise les conventions utilisees par les champs de
post-traitement.

## Solides TET4/TET10

Les contraintes et deformations 3D utilisent l'ordre de Voigt:

```text
[XX, YY, ZZ, XY, YZ, XZ]
```

Pour les deformations, les composantes de cisaillement sont les cisaillements
ingenieur `gamma_xy`, `gamma_yz`, `gamma_xz`.

Les invariants solides suivent ces conventions:

- `principal_stress`: valeurs propres du tenseur de contrainte 3D, triees par
  ordre croissant par NumPy;
- `principal_strain`: valeurs propres du tenseur de deformation 3D;
- `stress_trace`: trace du tenseur de contrainte;
- `strain_trace`: trace du tenseur de deformation;
- `hydrostatic_pressure`: opposee de la contrainte moyenne, donc
  `-(trace(stress) / 3)`;
- `deviatoric_stress`: tenseur deviateur remis en ordre Voigt;
- `von_mises`: contrainte equivalente 3D de von Mises.

`TET4` est un element a deformation constante: les valeurs au centre, au point
d'integration et les contributions nodales elementaires sont identiques.

`TET10` est evalue au centre pour le resultat elementaire principal et aux
quatre points d'integration de Hammer pour `integration_points`. En elasticite,
les resultats nodaux sont obtenus par extrapolation du champ lineaire ajuste
aux quatre points de Hammer. Pour un materiau chemin-dependant, les etats
internes restent moyennes et ne sont pas extrapoles.

## Elastoplasticite Von Mises

Le materiau `von_mises_elastoplastic_3d` utilise une loi J2 petites
deformations avec ecrouissage isotrope lineaire. Le retour radial est evalue
par point d'integration a partir de l'etat plastique committe au pas precedent.
La sortie `material_states` stocke l'etat final chemin-dependant par element et
point d'integration. L'historique complet de tous les pas de chargement n'est
pas encore exporte.

Les champs disponibles quand le materiau est actif sont:

- `material_state.model`;
- `material_state.elastic`;
- `equivalent_plastic_strain`;
- `plastic_multiplier`;
- `plastic_strain`;
- `yield_stress`;
- `yield_function`.

## Coques MITC4

Les resultantes MITC4 sont exprimees dans le repere local de la coque:

- `membrane_strain`: deformation membrane locale;
- `curvature`: courbure locale;
- `shear_strain`: cisaillement transverse local;
- `membrane_force`: resultante membrane;
- `bending_moment`: moment flechissant;
- `shear_force`: resultante de cisaillement transverse.

Les faces de coque utilisent la coordonnee locale `z`:

- `bottom` ou `shell_down`: $z=-t/2$;
- `shell_middle`: $z=0$;
- `top` ou `shell_up`: $z=+t/2$.

La contrainte de face est reconstruite par `membrane_strain + z * curvature`.
Le von Mises de face utilise la convention plane stress.

Pour un stratifie, `shell_sections.axis` vaut `local_e3`. Les positions
`shell_down` et `shell_up` sont les peaux exterieures. `shell_middle` est une
liste : elle contient une valeur si le plan moyen traverse l'interieur d'un
pli, et les deux limites materielles si $z=0$ coincide avec une interface. La
sortie ne moyenne jamais deux contraintes de plis differents a une interface.

## Resultats nodaux

Le champ global `nodal_results` est une moyenne des contributions elementaires
connectees a chaque noeud. Ce n'est pas encore une extrapolation superconvergente
ou une projection L2 globale. Il sert a obtenir un champ nodal stable pour
l'audit, les CSV et les exports VTU.

Chaque ligne contient:

- `node`;
- `contributing_element_count`;
- les grandeurs moyennables disponibles selon la famille d'element;
- `source = "element_nodal_average"`.
