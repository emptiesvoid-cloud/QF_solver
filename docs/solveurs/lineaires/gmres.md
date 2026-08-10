---
doc_id: DOC-METH-GMRES-001
revision: 0.2
status: owner_reviewed
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# GMRES

<span class="maturity reinforced">maturite inchangee : stable apres tests renforces</span>

## Geometrie, DDL et integration

GMRES agit sur le systeme assemble des DDL libres. Il ne modifie ni maillage,
ni quadrature, ni chargement, ni conditions limites.

## Formulation mathematique et algorithme

Pour une matrice generale, GMRES construit une base orthonormale de
$\mathcal K_k(K,r_0)$ par Arnoldi et minimise

$$
\lVert F-Ku_k\rVert_2.
$$

QF_solver utilise un redemarrage pour borner la memoire. Chaque cycle applique
Arnoldi, resout le petit probleme de moindres carres, met a jour $u$, puis
controle le residu reel.

## Exemple executable

```powershell
python .\qf_solver.py solve --input .\examples\tet4_static.json `
  --output .\results\gmres.json --method gmres
```

Le cas officiel fournit le maillage TET4, la charge et les blocages.

## Resultats, figure, invariants et convergence

--8<-- "docs/generated/linear_solver_results.md"

![Historique des residus](../../assets/generated/linear_solver_residuals.png){ .result-figure }

Le tableau de resultats est regenere. La figure de deformee du cas est
disponible sur la [page TET4](../../elements/tet4.md).

Les invariants sont la finitude, le residu libre, l'equilibre et la
correlation avec la voie directe. Le redemarrage peut ralentir ou bloquer la
convergence; l'historique doit donc etre conserve.

## Limites et references

Sans redemarrage, le stockage de la base croit avec le nombre d'iterations.
Avec redemarrage, la robustesse peut diminuer. Voir
[Saad et Schultz](../../reference/references.md#ref-gmres-1986) et la
[page commune](../methodes_lineaires.md).

## Owner review

Page en attente d'Owner review; aucune revendication de qualification n'en
decoule automatiquement.
