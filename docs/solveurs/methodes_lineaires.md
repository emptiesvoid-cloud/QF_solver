---
doc_id: DOC-SOL-006
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Methodes lineaires : formulation et algorithmes

Cette page explicite les methodes selectionnables par `linear_method`. Elles
resolvent le systeme apres elimination des ddl bloques; aucune ne corrige un
maillage invalide, une rigidite singuliere ou un modele mecanique incoherent.

## Pages algorithmiques

- [Resolution directe creuse](lineaires/direct.md)
- [Gradient conjugue](lineaires/cg.md)
- [MINRES](lineaires/minres.md)
- [GMRES](lineaires/gmres.md)
- [BiCGSTAB](lineaires/bicgstab.md)

Chaque page contient formulation, algorithme, exemple executable, maillage,
chargement, conditions limites, resultats, figure, invariants, convergence,
limites et references. Elles attendent une Owner review documentaire et ne
modifient pas la maturite des solveurs.

## 1. Reduction par conditions de Dirichlet

En separant ddl libres $f$ et imposes $c$ :

$$
\begin{bmatrix}K_{ff}&K_{fc}\\K_{cf}&K_{cc}\end{bmatrix}
\begin{bmatrix}u_f\\u_c\end{bmatrix}=
\begin{bmatrix}F_f\\F_c\end{bmatrix},
\qquad K_{ff}u_f=F_f-K_{fc}u_c.
$$

Les reactions sont recalculees dans le systeme complet. Le residu publie est
$r=Ku-F$ et le controle normalise utilise

$$
\eta=\frac{\|r_f\|_2}{\max(\|F_f\|_2,\|K_{ff}u_f\|_2,1)}.
$$

## 2. Solveur direct creux

`direct`/`spsolve` applique une factorisation LU creuse. Il est robuste pour
les petits et moyens systemes mais son remplissage peut dominer memoire et
temps. Le solveur transforme les avertissements de rang, solutions non finies
et residus anormaux en `NumericalConvergenceError`.

`splu_reuse` factorise une fois une matrice constante puis resout plusieurs
seconds membres : c'est le chemin exploite par Newmark quand une factorisation
directe est demandee.

## 3. Preconditionnement

Les iterations portent sur $P^{-1}Kx=P^{-1}b$, avec $P$ inversible et peu
couteux. `jacobi` utilise l'inverse de la diagonale; `ilu` construit une LU
incomplete. Un preconditionneur modifie la vitesse de convergence, pas la
solution exacte visee. Il doit rester compatible avec la methode et les
proprietes de $K$.

## 4. CG, MINRES, GMRES et BiCGSTAB

Pour une matrice symetrique definie positive, CG initialise
$r_0=b-Kx_0$, $z_0=P^{-1}r_0$, $p_0=z_0$, puis itere

$$
\alpha_k=\frac{r_k^Tz_k}{p_k^TKp_k},\quad
x_{k+1}=x_k+\alpha_kp_k,\quad r_{k+1}=r_k-\alpha_kKp_k,
$$

$$
\beta_k=\frac{r_{k+1}^Tz_{k+1}}{r_k^Tz_k},\qquad
p_{k+1}=z_{k+1}+\beta_kp_k.
$$

MINRES minimise le residu sur une base de Lanczos et accepte les matrices
symetriques indefinies. GMRES construit une base d'Arnoldi
$KV_m=V_{m+1}\bar H_m$ puis minimise
$\|\beta e_1-\bar H_my\|_2$. BiCGSTAB est une methode bi-orthogonale
stabilisee pour les matrices non symetriques; elle est utile lorsque GMRES
serait trop couteux en memoire. Ces methodes ne doivent pas etre utilisees
aveuglement : une raideur elastique correctement contrainte est normalement
symetrique; CG est alors le choix iteratif naturel.

## 5. Politique explicable de selection

Le solveur conserve le choix fourni dans `analysis.method`: il ne bascule jamais
silencieusement de LU vers une methode iterative. Avant le calcul statique, il
produit toutefois `solver.selection` dans le resultat JSON et dans l'audit.
Newmark produit le meme bloc pour $K_{eff}$; l'harmonique publie un echantillon
par frequence de la rigidite dynamique complexe. Le bloc indique la symetrie
mesuree, le caractere reel ou complexe, le signe de la diagonale, le stockage
creux, une estimation conservative de la memoire LU et la methode recommandee.

Le bloc voisin `solver.execution` enregistre la methode demandee et utilisee,
le preconditionneur, les tolerances effectives, la limite d'iterations, le
residu controle, les temps d'assemblage et de resolution ainsi que l'estimation
de stockage. `fallback_used` vaut toujours `false` dans cette version: le
solveur refuse proprement une non-convergence au lieu de masquer un changement
d'algorithme.

| Contrat observe | Recommendation | Limite importante |
| --- | --- | --- |
| Reelle, symetrique, Cholesky dense verifiee ou hypothese `assume_spd` explicite | `cg` | l'hypothese utilisateur est tracee, elle ne constitue pas une preuve numerique |
| Symetrique sans preuve de positivite | `minres` | preconditionneur compatible a verifier |
| Non symetrique | `gmres` ou `bicgstab` | GMRES stocke une base qui augmente avec les iterations |
| Complexe harmonique | direct | le chemin standard ne propose pas de Krylov complexe |

Dans la route standard, une demande `CG` sans preuve de definitude positive est
refusee avant iteration. Pour les petites matrices, QF_solver effectue une
Cholesky dense bornee par `spd_dense_check_max_dofs` (256 par defaut). Pour une
matrice plus grande, `assume_spd: true` est une declaration explicite de
l'utilisateur fondee sur la derivee mecanique du systeme; elle est visible dans
l'audit et ne transforme jamais une diagonale positive en preuve. `CG` et `MINRES`
n'acceptent que `none` ou `jacobi`, car une ILU generale ne preserve pas le
contrat de symetrie. `GMRES` et `BiCGSTAB` restent disponibles pour les cas
non symetriques documentes; leur emploi sur une matrice apparemment symetrique
est trace comme avertissement, pas masque.

`direct_memory_budget_mb` fixe un budget de facteur LU estime avec
`direct_fill_factor_estimate` (10 par defaut). Avec
`enforce_direct_memory_budget: true`, un LU au-dessus du budget est refuse avant
la factorisation. Cette garde est appliquee en statique, a la matrice effective
Newmark et a chaque rigidite dynamique harmonique. L'estimation reste une garde
operationnelle et non une prediction exacte du remplissage: elle doit etre
calibree par les campagnes PETSc/MPI sur les grands modeles.

## 6. Criteres, diagnostics et demonstration

Les parametres `rtol`, `atol`, `maxiter`, `preconditioner` et le seuil de
residu final sont enregistres dans l'audit. Une limite d'iterations, une panne
numerique ou $\eta$ trop grand est un echec, non un resultat approximatif
silencieux. La [poutre TET4/TET10](../demonstrations/benchmarks/cantilever.md)
compare les voies iteratives au resultat direct et publie les residus.

La campagne `VNV-LINEAR-SOLVERS-001` complete ce cas EF symetrique par quatre
systemes algebriques controles : une paire SPD/non symetrique en `4` DDL et une
paire en `32` DDL de type chaine de rigidite scalaire et chaine non symetrique.
La famille SPD compare LU, CG, MINRES, GMRES et BiCGSTAB; la famille non
symetrique compare LU, GMRES et BiCGSTAB, tout en excluant explicitement CG et
MINRES. Chaque ligne publie le residu relatif, l'ecart a LU, le nombre
d'iterations, le temps indicatif, le nombre de coefficients non nuls et le
conditionnement 2-norme. Le conditionnement est calcule uniquement sur ces
petits systemes controles; il n'autorise jamais une conversion dense dans le
solveur de production. La campagne se regenere avec :

```powershell
python .\scripts\run_linear_solver_vnv.py --output .\results\VNV-LINEAR-SOLVERS-001
```

```python
from solveur.api import run_linear_solver_verification

report = run_linear_solver_verification("results/VNV-LINEAR-SOLVERS-001")
assert report["status"] == "PASS"
```

Le dossier contient aussi `vnv_manifest.json`. Les temps de calcul sont
informatifs et ne servent pas de seuil, car ils dependent de la machine. Le
critere d'acceptation reste algebrique : ecart de solution et residu relatif
inferieurs a `1e-10`, avec un benchmark EF separe pour confirmer l'accord sur
une matrice issue d'un assemblage mecanique.

| Methode | Hypothese principale | Memoire supplementaire | Usage |
| --- | --- | --- | --- |
| Direct LU | matrice generale | remplissage de facteurs | reference petits/moyens cas |
| CG | symetrique definie positive | quelques vecteurs | elasticite lineaire bien bloquee |
| MINRES | symetrique | quelques vecteurs | probleme symetrique indefini |
| GMRES | generale | base Arnoldi croissante | matrice non symetrique |
| BiCGSTAB | generale | quelques vecteurs | alternative memoire a GMRES |

## Tracabilite

| Methode | Code | Tests | References |
| --- | --- | --- | --- |
| Direct, residu et reutilisation | `solveur/core/linear_methods.py` | `tests/unit/test_solver.py` | [REF-FEM-BATHE](../reference/references.md#ref-fem-bathe) |
| CG | `linear_methods.py` | solveurs lineaires vs direct | [REF-CG-1952](../reference/references.md#ref-cg-1952) |
| MINRES | `linear_methods.py` | solveurs lineaires vs direct | [REF-MINRES-1975](../reference/references.md#ref-minres-1975) |
| GMRES / BiCGSTAB | `linear_methods.py` | solveurs lineaires vs direct | [REF-GMRES-1986](../reference/references.md#ref-gmres-1986), [REF-BICGSTAB-1992](../reference/references.md#ref-bicgstab-1992) |
| Politique de selection et garde LU | `solveur/core/linear_policy.py` | `tests/unit/test_linear_policy.py` | [REF-CG-1952](../reference/references.md#ref-cg-1952) |
| Comparaison SPD / non symetrique | `solveur/verification/linear_solver_comparison.py` | `tests/unit/test_linear_solver_comparison.py` | [REF-CG-1952](../reference/references.md#ref-cg-1952), [REF-GMRES-1986](../reference/references.md#ref-gmres-1986) |
