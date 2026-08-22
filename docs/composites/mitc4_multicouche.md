---
doc_id: DOC-COMP-003
revision: 0.3
status: engineering_internal_validated_with_recommendations
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# MITC4 multicouche - statique bornee V1

## Sous-perimetre de promotion stable

La promotion vers `stable` est maintenant decoupee explicitement. Le
sous-perimetre `planar_regular_meshes` couvre la plaque plane symetrique
`[0/90/90/0]`, les chargements membrane, flexion et combine, trois niveaux de
maillage et les observables de contraintes par pli hors singularite. La
campagne dediee et sa decision Owner sont dans
`docs/verification/mitc4_laminate_static_planar_stable_owner_review.md`.

Les probes de maillage distordu et de coque courbe a orientation oblique ne
sont pas supprimes : ils restent des preuves experimentales hors du
sous-perimetre stable. Le probe oblique converge vers un plateau d'environ
`2,043 %`; il ne doit donc pas etre extrapole au domaine stable plan.

## Separation avec le MITC4 isotrope

Le type elementaire reste `MITC4`, mais le materiau `shell_laminate` suit un
chemin constitutif distinct. Le materiau historique `shell_isotropic` et ses
resultats valides ne sont pas modifies. La statique lineaire multicouche fait
partie de la V1 avec le statut
`engineering_internal_validated_with_recommendations`. Les criteres de rupture
La campagne dynamique interne modal/Newmark/harmonique est disponible dans
`VNV-MITC4-LAMINATE-DYNAMIC-001`, avec le statut `verified_development`; elle
ne ferme pas encore une correlation externe ni une Owner review. Le profil
`qualification` continue de refuser ce perimetre sans scope accepte.

## Rigidite elementaire

Avec les matrices de deformation MITC4 `Bm`, `Bb` et `Bs`, la contribution
stratifiee en un point de Gauss est :

\[
\mathbf K_e=\int_A\left(
\mathbf B_m^T\mathbf A\mathbf B_m
+\mathbf B_m^T\mathbf B\mathbf B_b
+\mathbf B_b^T\mathbf B^T\mathbf B_m
+\mathbf B_b^T\mathbf D\mathbf B_b
+\mathbf B_s^T\mathbf A_s\mathbf B_s
\right)dA+\mathbf K_d.
\]

Les deux termes croises sont indispensables pour un empilement non symetrique.
Ils sont assembles dans la composante `coupling` et leur somme est explicitement
symetrique. Pour un stratifie symetrique, `B=0` et cette composante est nulle.

## Cisaillement transverse

Chaque pli doit definir `G13` et `G23`. La rigidite de cisaillement tournee
dans les axes elementaires est integree sur l'epaisseur :

\[
\mathbf A_s=k_s\sum_k t_k\,
\mathbf R(\theta_k)
\begin{bmatrix}G_{13,k}&0\\0&G_{23,k}\end{bmatrix}
\mathbf R(\theta_k)^T.
\]

Le facteur `ks=5/6` est le defaut actuel. Il constitue une approximation
globale de Reissner-Mindlin et devra faire l'objet d'une sensibilite specifique
pour des empilements tres heterogenes.

Les points de tying MITC et l'integration `2x2` restent identiques au MITC4
isotrope. Le terme de drilling utilise une echelle faible construite a partir
de la moyenne geometrique `sqrt(E1 E2)` integree dans l'epaisseur.

## Resultantes et contraintes par pli

Au centre de chaque element :

\[
\mathbf N=\mathbf A\boldsymbol\varepsilon^0+
\mathbf B\boldsymbol\kappa,
\qquad
\mathbf M=\mathbf B^T\boldsymbol\varepsilon^0+
\mathbf D\boldsymbol\kappa,
\qquad
\mathbf Q=\mathbf A_s\boldsymbol\gamma.
\]

La sortie `ply_results` fournit, pour chaque pli et pour ses positions
`lower/middle/upper`, `z`, les deformations et contraintes dans les axes
elementaires et materiau, ainsi qu'un von Mises informatif. Ce von Mises ne
constitue pas un critere de rupture composite. Lorsque des allowables sont
definis, `failure_indices` fournit contrainte/deformation maximale, Tsai-Hill
et Tsai-Wu, et `failure_summary` identifie les positions critiques.

Les sorties `shell_faces` restent presentes pour la compatibilite : elles
correspondent a la face inferieure du premier pli et a la face superieure du
dernier pli.

La sortie `shell_sections` explicite les selecteurs d'epaisseur :
`shell_down` a $z=-t/2$, `shell_middle` a $z=0$ et `shell_up` a $z=+t/2$,
selon la normale locale $\mathbf e_3$. Si $z=0$ est une interface, les deux
limites de contrainte sont conservees, car une moyenne masquerait la
discontinuite inter-pli.

## Format JSON

```json
{
  "type": "shell_laminate",
  "shear_factor": 0.8333333333333334,
  "drilling_scale": 0.0001,
  "reference_direction": [1.0, 0.0, 0.0],
  "plies": [
    {
      "name": "ply-1",
      "E1": 135000000000.0,
      "E2": 10000000000.0,
      "nu12": 0.3,
      "G12": 5000000000.0,
      "G13": 4500000000.0,
      "G23": 3800000000.0,
      "density": 1600.0,
      "thickness": 0.000125,
      "angle_deg": 0.0
    }
  ]
}
```

`reference_direction` est optionnel. Lorsqu'il est defini, ce vecteur global
est normalise puis projete dans le plan de chaque facette. Si `e1/e2/e3`
designe le repere MITC4 local, l'angle de transport est :

\[
\alpha=\operatorname{atan2}
\left(\widehat{\mathbf d}_p\cdot\mathbf e_2,
\widehat{\mathbf d}_p\cdot\mathbf e_1\right),
\qquad
\mathbf d_p=\mathbf d-(\mathbf d\cdot\mathbf e_3)\mathbf e_3.
\]

L'angle constitutif utilise pour le pli `k` vaut alors
`alpha + angle_deg[k]`. La meme transformation est appliquee aux matrices
`A/B/D/As` et au post-traitement des contraintes. La sortie elementaire publie
`material_angle_offset_deg`, `material_reference_direction` et
`ply_directions_global`.

La projection est refusee lorsque le vecteur de reference est parallele a la
normale d'une facette. Pour une piece contenant une telle singularite
d'orientation, plusieurs regions materielles ou un champ directeur plus
general restent necessaires.

Un exemple executable complet est disponible dans
`examples/mitc4_laminate_static.json`.

## Verification actuelle

| Verification | Resultat | Verdict |
| --- | ---: | --- |
| Pli isotrope equivalent contre MITC4 isotrope | matrices egales a `2e-14` relatif | PASS |
| `[0/90]` non symetrique | composante `coupling` non nulle et symetrique | PASS |
| Rotation globale de `37 deg` | spectres de rigidite invariants | PASS |
| Coque facettisee a deux elements | assemblage, solution et 24 points de pli finis | PASS |
| Porte-a-faux UD, `t/L=1e-2` | deplacement/reference `0,997998` | PASS |
| Porte-a-faux UD, `t/L=1e-3` | deplacement/reference `0,997809` | PASS |
| API et CLI sur `[0/90]s` | solution, audit et JSON par pli | PASS |
| Panneau `[0/90]s` contre CalculiX 2.20 S8R | ecart fin de fleche `0,0310 %` | PASS |
| NAFEMS R0031/1 contre Code_Aster 18.1.0 DST | ecart fin QF/NAFEMS `0,458 %`, increment final `0,0967 %` | PASS |
| Contraintes par pli hors singularites | erreur L2 `0,00389 %` a `1,056 %` | PASS |
| Panneau cylindrique avec axe projete | erreur angulaire `1,4e-14 deg`, increment final `1,06 %` | PASS |
| Assemblage plie, 2 048 elements | increment final `0,875 %` | PASS |
| Facettes gauches perturbees de `10 %` | verdict de qualification `FAIL` attendu | PASS politique |

Les deux points minces ne montrent pas de shear locking, mais ne remplacent
pas une campagne parametrique complete en epaisseur, distorsion, orientation et
raffinement.

## Limites bloquantes

- statique lineaire seulement;
- masse composite dynamique et couplages inertiels hors scope;
- proprietes constantes dans chaque pli; direction globale projetee ou
  affectation par regions, sans champ nodal interpole;
- aucun effet thermique ou hygroscopique;
- aucun offset de coque;
- criteres disponibles comme indicateurs sans degradation; delaminage et
  endommagement absents;
- recuperation `S13` interlaminaire NAFEMS non implementee;
- comparaison `S11` NAFEMS encore informative car les localisations de sortie
  ne sont pas strictement identiques;
- aucune correlation externe sur coque composite courbe;
- aucune validation pour une decision industrielle.

Reference theorique : [REF-COMP-JONES](../reference/references.md#ref-comp-jones).
