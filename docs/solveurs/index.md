---
doc_id: DOC-SOL-000
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Carte des methodes de resolution

Les labels de cette page sont des labels techniques historiques. Les claims
publics 0.2.7 doivent etre lus avec le registry v2 et les preuves bornees de
`docs/verification/0_2_7/`; la presence d'une route ne vaut pas qualification
generale.

| Analyse | Equation | Methodes disponibles | Maturite |
| --- | --- | --- | --- |
| Statique lineaire | $\mathbf Ku=\mathbf f$ | direct, CG, GMRES, BiCGSTAB, MINRES | stable sur TET4/MITC4 bornes |
| Modale | $\mathbf K\phi=\lambda\mathbf M\phi$ | `eigsh`, `lanczos`, `eigh` | renforcee |
| Dynamique | $\mathbf M\ddot u+\mathbf C\dot u+\mathbf Ku=f(t)$ | Newmark implicite | renforcee |
| Harmonique | $(\mathbf K-\omega^2\mathbf M+i\omega\mathbf C)\hat u=\hat f$ | direct par frequence | renforcee |
| Non-lineaire | $\mathbf r(\mathbf u,\lambda)=0$ | Newton, modifie, line-search, arc-length | experimentale |
| Grand modele | $\mathbf Ku=\mathbf f$ | SciPy chunked, PETSc, matrix-free structure | experimentale |

Le nom d'une methode n'est pas une garantie de convergence. Les proprietes de
la matrice, le conditionnement, la tolerance, le preconditionneur et les
residus finaux doivent etre examines ensemble.

La [formulation des methodes lineaires](methodes_lineaires.md) explique la
reduction par Dirichlet, le preconditionnement, CG, MINRES, GMRES et BiCGSTAB.

--8<-- "docs/generated/solver_matrix.md"
