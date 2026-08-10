---
doc_id: DOC-METH-BICGSTAB-001
revision: 0.2
status: owner_reviewed
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# BiCGSTAB

<span class="maturity reinforced">maturite inchangee : stable apres tests renforces</span>

## Geometrie, DDL et integration

BiCGSTAB traite le systeme reduit assemble. Les DDL, la quadrature, le
maillage, les charges et les blocages restent definis par le modele FEM.

## Formulation mathematique et algorithme

BiCGSTAB construit deux suites biorthogonales et applique un lissage de type
résidu minimal au polynome de BiCG. Il vise une matrice generale avec une
memoire courte. L'arret est fonde sur

$$
\eta_k=\frac{\lVert F-Ku_k\rVert_2}{\max(\lVert F\rVert_2,1)}.
$$

## Exemple executable

```powershell
python .\qf_solver.py solve --input .\examples\tet4_static.json `
  --output .\results\bicgstab.json --method bicgstab
```

Le maillage, le chargement et les conditions limites sont ceux du cas TET4
officiel.

## Resultats, figure, invariants et convergence

--8<-- "docs/generated/linear_solver_results.md"

![Historique des residus](../../assets/generated/linear_solver_residuals.png){ .result-figure }

Le tableau de resultats est regenere. La figure de deformee du cas est
disponible sur la [page TET4](../../elements/tet4.md).

Les controles portent sur le residu recalcule, la finitude, l'equilibre et
l'accord avec la solution directe. Une oscillation du residu ou une rupture
de recurrence doit etre publiee comme non-convergence.

## Limites et references

La methode peut etre moins reguliere que GMRES et reste sensible au
conditionnement. Voir
[van der Vorst](../../reference/references.md#ref-bicgstab-1992) et la
[page commune](../methodes_lineaires.md).

## Owner review

Page en attente d'Owner review; la demonstration ne change pas la maturite.
