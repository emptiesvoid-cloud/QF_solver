---
doc_id: DOC-METH-CG-001
revision: 0.2
status: owner_reviewed
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Gradient conjugue

<span class="maturity stable">maturite inchangee : stable dans le perimetre SPD</span>

## Geometrie, DDL et integration

CG agit sur les DDL libres du systeme element fini assemble. Il n'ajoute
aucune integration : maillage, quadrature, chargement et blocages proviennent
des elements et du modele d'entree.

## Formulation mathematique et algorithme

Pour $K=K^T>0$, CG minimise l'energie quadratique

$$
\Pi(u)=\tfrac12u^TKu-u^TF
$$

sur les espaces de Krylov. Avec $r_0=F-Ku_0$ et $p_0=r_0$, il construit des
directions $K$-conjuguees jusqu'a satisfaction du residu.

1. initialiser $u_0$, $r_0$ et le preconditionneur;
2. calculer le pas dans la direction $p_k$;
3. mettre a jour $u_k$ et $r_k$;
4. construire la direction conjuguee suivante;
5. arreter sur tolerance ou declarer la non-convergence.

## Exemple executable, maillage et conditions limites

```powershell
python .\qf_solver.py solve --input .\examples\tet4_static.json `
  --output .\results\cg.json --method cg
```

Le cas utilise le maillage, la charge et les blocages du TET4 officiel.

## Tableau, figure, invariants et convergence

--8<-- "docs/generated/linear_solver_results.md"

![Historique des residus](../../assets/generated/linear_solver_residuals.png){ .result-figure }

Le tableau de resultats est regenere. La figure de deformee du cas est
disponible sur la [page TET4](../../elements/tet4.md).

Sont controles : symetrie, positivite attendue, finitude, residu relatif,
equilibre et accord avec la solution directe. La courbe de residu est la
preuve de convergence algorithmique; elle ne prouve pas la convergence en
maillage.

## Limites et references

CG ne doit pas etre employe pour une matrice non symetrique ou indefinie. Le
conditionnement et le preconditionneur gouvernent le nombre d'iterations.
Voir [Hestenes et Stiefel](../../reference/references.md#ref-cg-1952) et la
[page commune](../methodes_lineaires.md).

## Owner review

Cette page a ete incluse dans l'Owner review documentaire du 1er aout 2026,
avec decision `accepted_with_recommendations`. Aucune maturite mecanique n'est
changee par sa seule publication.
