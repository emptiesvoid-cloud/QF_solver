---
doc_id: DOC-METH-ARCLENGTH-001
revision: 0.2
status: owner_reviewed
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Continuation arc-length

<span class="maturity experimental">maturite inchangee : experimental</span>

## Geometrie, DDL et integration

La methode suit un chemin d'equilibre d'un modele non lineaire. Elle herite de
la geometrie, des DDL, de la quadrature, du maillage, des charges de reference
et des blocages de l'element actif.

## Formulation mathematique

Le residu et la contrainte d'arc sont

$$
r(u,\lambda)=\lambda F-f_{int}(u)=0,
$$

$$
\Delta u^T\Delta u+\alpha^2\Delta\lambda^2=\Delta s^2.
$$

Cette contrainte autorise le suivi de branches pour lesquelles le facteur de
charge n'est pas monotone.

## Algorithme et integration incrementale

1. calculer un predicteur tangent;
2. resoudre le systeme augmente;
3. corriger simultanement $u$ et $\lambda$;
4. controler residu et contrainte d'arc;
5. adapter le rayon ou refuser le pas.

L'integration constitutive est executee a chaque point de Gauss, puis les
etats ne sont committes qu'apres convergence.

## Exemple executable, maillage et chargement

```powershell
python .\qf_solver.py solve --input .\examples\tet4_nonlinear_static.json `
  --output .\results\arc_length.json
```

Le JSON porte la geometrie, le maillage, la charge proportionnelle, les
conditions limites et les parametres de continuation.

## Resultats, figure, invariants et convergence

--8<-- "docs/generated/nonlinear_results.md"

![Courbe de convergence non lineaire](../assets/generated/nonlinear_convergence.png){ .result-figure }

La figure de deformee du modele est publiee avec le benchmark non lineaire;
la courbe ci-dessus decrit le suivi algorithmique.

Le tableau publie increments, iterations et residus. Les invariants incluent
equilibre, finitude, coherence du chemin, etats committes et independance
raisonnable au rayon d'arc.

## Limites et references

La methode reste experimentale. La convergence numerique ne garantit ni
l'unicite de la branche ni sa stabilite physique. Voir
[Bathe](../reference/references.md#ref-fem-bathe) et la
[page non lineaire](non_lineaire.md).

## Owner review

Page en attente d'Owner review. Aucune evolution de maturite ne peut etre
deduite de la seule demonstration.
