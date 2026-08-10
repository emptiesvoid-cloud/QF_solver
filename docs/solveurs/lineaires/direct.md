---
doc_id: DOC-METH-DIRECT-001
revision: 0.2
status: owner_reviewed
applicable_version: 0.2.0
reviewer: ""
approver: ""
review_date: ""
---

# Resolution directe creuse

<span class="maturity stable">maturite inchangee : stable dans le perimetre borne</span>

## Geometrie, DDL et integration

La methode ne definit ni geometrie ni quadrature propre. Elle recoit le
systeme assemble sur les DDL libres; la geometrie, les DDL et l'integration
restent ceux des elements finis actifs. Apres elimination de Dirichlet :

$$
K_{ff}u_f=F_f-K_{fc}u_c.
$$

## Formulation mathematique et algorithme

QF_solver appelle la factorisation creuse de SciPy. Le pivotage et les
permutations sont geres par le backend. Les reactions sont ensuite
reconstruites dans le systeme complet avec $r=Ku-F$.

1. assembler $K$ et $F$;
2. appliquer les DDL imposes;
3. factoriser $K_{ff}$;
4. effectuer les substitutions;
5. reconstruire $u$, les reactions et les diagnostics.

## Exemple executable

```powershell
python .\qf_solver.py solve --input .\examples\tet4_static.json `
  --output .\results\direct.json --method direct
```

Le maillage est le TET4 de l'exemple; le chargement nodal et les blocages sont
decrits dans son JSON. La deformee et les conditions limites sont
presentees dans la [demonstration solide](../../demonstrations/solides.md).

## Resultats, invariants et convergence

--8<-- "docs/generated/linear_solver_results.md"

Le tableau de resultats inclus est regenere par la campagne documentaire.

![Comparaison des residus lineaires](../../assets/generated/linear_solver_residuals.png){ .result-figure }

Les invariants controles sont la finitude de $u$, l'equilibre global, le
residu libre normalise et, pour une elasticite conservative, l'identite entre
travail externe et deux fois l'energie de deformation. Une methode directe
n'a pas de convergence iterative; sa preuve porte sur le residu final et la
correlation avec les autres voies.

## Limites et references

La memoire de factorisation peut croitre beaucoup plus vite que le nombre de
coefficients de $K$. Une singularite, un avertissement de rang ou une solution
non finie interdit l'acceptation. Voir [Bathe](../../reference/references.md#ref-fem-bathe)
et la [page commune](../methodes_lineaires.md).

## Owner review

Cette page a ete incluse dans l'Owner review documentaire du 1er aout 2026,
avec decision `accepted_with_recommendations`. Cette decision ne modifie pas,
a elle seule, la maturite ni le statut de qualification.
