---
doc_id: DOC-METH-MINRES-001
revision: 0.2
status: owner_reviewed
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# MINRES

<span class="maturity reinforced">maturite inchangee : stable apres tests renforces</span>

## Geometrie, DDL et integration

MINRES resout le systeme reduit sur les DDL libres. Il herite de la geometrie,
de l'integration, du chargement et des conditions limites du modele FEM.

## Formulation mathematique et algorithme

Pour une matrice reelle symetrique, eventuellement indefinie, MINRES cherche
dans $\mathcal K_k(K,r_0)$ la solution qui minimise

$$
\lVert F-Ku_k\rVert_2.
$$

La recurrence de Lanczos tridiagonalise implicitement $K$; des rotations
orthogonales mettent a jour le minimum du residu sans stocker toute la base.

## Exemple executable

```powershell
python .\qf_solver.py solve --input .\examples\tet4_static.json `
  --output .\results\minres.json --method minres
```

Le maillage TET4, la charge nodale et les blocages sont ceux de l'exemple.

## Resultats, figure, invariants et convergence

--8<-- "docs/generated/linear_solver_results.md"

![Historique des residus](../../assets/generated/linear_solver_residuals.png){ .result-figure }

Le tableau de resultats est regenere. La figure de deformee du cas est
disponible sur la [page TET4](../../elements/tet4.md).

Les controles couvrent la symetrie, le residu, la finitude, l'equilibre et
l'accord direct/iteratif. Une matrice indefinie peut signaler une formulation
mixte legitime ou une erreur mecanique : le diagnostic reste obligatoire.

## Limites et references

MINRES exige une matrice symetrique. Une singularite mecanique n'est pas
reparee par l'algorithme. Voir
[Paige et Saunders](../../reference/references.md#ref-minres-1975) et la
[page commune](../methodes_lineaires.md).

## Owner review

Page en attente d'Owner review; demonstration et qualification sont deux
decisions distinctes.
