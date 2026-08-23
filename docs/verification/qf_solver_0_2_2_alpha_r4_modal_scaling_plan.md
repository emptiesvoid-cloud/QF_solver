---
doc_id: DOC-VNV-R4-MODAL-SCALE-001
revision: 0.1
status: draft technique
applicable_version: 0.2.2a0
reviewer: ""
approver: ""
---

# R4 - Protection modale SLEPc et passage a l'echelle

## Objet

Le scope modal SLEPc est actuellement demontre jusqu'a `107811` DDL. Une
tentative a `2044416` DDL a ete arretee par la limite de ressources pendant
la factorisation shift-invert, avec environ `33,5 GiB` observes. Ce document
separe la protection immediate du travail de recherche necessaire pour
augmenter la capacite. Il ne constitue pas une preuve de support a `2M` DDL.

## Phase 1 - protection immediate implementee

Le garde-fou est centralise dans `src/solveur/core/modal_options.py` et est
appele avant l'assemblage de `K` et `M` dans les deux chemins SLEPc :

| Chemin | Declencheur | Protection |
| --- | --- | --- |
| Solveur modal standard | `use_slepc_modal: true` ou `backend: petsc` | oui |
| `solve_large_modal` TET4 | le runner est intrinsiquement SLEPc | oui |

Lorsque le nombre global de DDL est strictement superieur a `500000`, le
solveur leve `InputValidationError` avant toute allocation de matrice globale
et avant l'extraction des valeurs propres. Le message rappelle :

- la derniere campagne SLEPc archivee : `107811` DDL ;
- la limite de protection : `500000` DDL ;
- le fait que `500000` est un plafond de protection R&D, pas une capacite
  validee ;
- l'interdiction d'extrapoler ce scope a `2M` DDL.

Le choix est volontairement conservatif : le test porte sur le nombre global
de DDL, et non seulement sur les DDL libres apres blocage. Les matrices ne
sont donc pas assemblees pour un calcul que la release ne sait pas qualifier.

## Phase 2 - architecture R&D shift-invert

### Contrat numerique

Le probleme reste

\[
  K\,\phi = \lambda M\,\phi .
\]

Le chemin cible conserve `K` et `M` sous forme creuse. Il ne doit jamais
former `inv(M) @ K`, `inv(K)` ou une matrice dense equivalente. Le shift-invert
doit etre vu comme un operateur d'application :

\[
  (K-\sigma M)^{-1} M\,\phi,
\]

dans lequel chaque inverse est realise par une resolution lineaire. SLEPc
documente explicitement cette semantique pour `STSINVERT` et gere les
resolutions via le `KSP` associe au `ST`.

### Configuration PETSc/SLEPc de reference

Le squelette suivant est une configuration de recherche. Il ne doit pas etre
active par defaut ni utiliser le verdict de la campagne comme preuve de
qualification :

```python
from petsc4py import PETSc
from slepc4py import SLEPc

eps = SLEPc.EPS().create(comm=PETSc.COMM_WORLD)
eps.setOperators(K_aij, M_aij)  # matrices PETSc AIJ, jamais dense
eps.setProblemType(SLEPc.EPS.ProblemType.GHEP)
eps.setType("krylovschur")
eps.setDimensions(nev=mode_count, ncv=max(2 * mode_count + 4, 20))
eps.setTarget(sigma)
eps.setWhichEigenpairs(SLEPc.EPS.Which.TARGET_MAGNITUDE)

st = eps.getST()
st.setType("sinvert")
st.setShift(sigma)
ksp = st.getKSP()
ksp.setType("preonly")
pc = ksp.getPC()
pc.setType("lu")
pc.setFactorSolverType("mumps")

eps.setTolerances(tol=1.0e-8, max_it=10000)
eps.setFromOptions()
eps.solve()
```

Le nom exact de certaines constantes peut varier avec la version de
`petsc4py`; la voie par options PETSc est la reference de reproductibilite :

```text
-eps_type krylovschur
-eps_target 0.0
-eps_which target_magnitude
-st_type sinvert
-st_shift 0.0
-st_ksp_type preonly
-st_pc_type lu
-st_pc_factor_mat_solver_type mumps
```

Le package standard ne doit pas dependre de cette configuration. Elle est
reservee a une image HPC explicitement tracee, avec MUMPS effectivement
compile dans PETSc.

### Variante SciPy pour les campagnes de comparaison

SciPy peut recevoir explicitement `OPinv`. Cela evite a `eigsh` de recreer un
chemin implicite different, tout en laissant la factorisation SuperLU sous
forme creuse :

```python
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import LinearOperator, eigsh, splu

K_csc = csc_matrix(K_csr, copy=False)
M_csc = csc_matrix(M_csr, copy=False)
shifted = (K_csc - sigma * M_csc).tocsc()
shifted.sum_duplicates()
lu = splu(shifted, permc_spec="COLAMD")
op_inv = LinearOperator(
    shape=shifted.shape,
    dtype=shifted.dtype,
    matvec=lu.solve,
)
eigenvalues, modes = eigsh(
    K_csc,
    M=M_csc,
    k=mode_count,
    sigma=sigma,
    which="LM",
    OPinv=op_inv,
)
```

`copy=False` est une intention d'eviter une copie, pas une garantie si le
format, l'indexation ou le type numerique ne conviennent pas. Surtout, la
factorisation `splu` peut consommer beaucoup plus que `K` et `M` a cause du
remplissage. Ce chemin est utile pour comparer les resultats, mais il ne
resout pas le probleme OOM a lui seul.

### Out-of-core

La piste prioritaire est PETSc + MUMPS. MUMPS expose une factorisation
out-of-core configurable par les options PETSc suivantes :

```text
-st_pc_type lu
-st_pc_factor_mat_solver_type mumps
-mat_mumps_icntl_22 1
-mat_mumps_ooc_tmpdir /scratch/qf_solver/mumps
-mat_mumps_icntl_23 4096
```

`ICNTL(22)=1` active le mode out-of-core, le repertoire temporaire doit etre
rapide et suffisamment grand, et `ICNTL(23)` borne la memoire de travail par
processeur en Mo. La factorisation peut toutefois conserver des structures
en memoire, subir un cout I/O tres eleve et echouer si le disque ou le
quota est insuffisant. L'out-of-core n'est donc pas une promesse de succes a
`2M` DDL.

SuperLU_DIST peut rester une comparaison de factorisation distribuee, mais
MUMPS est la premiere piste a instrumenter pour l'out-of-core PETSc. Il faut
archiver la memoire RSS, la memoire PETSc, le volume de remplissage, les temps
de factorisation/solve et la capacite disque avant tout verdict.

## Plan de validation R4

1. **Contract tests** : verifier le refus pre-assemblage a `500001` DDL et le
   passage a `500000` DDL.
2. **Baseline** : rejouer `1k`, `107811` et le cas modal qualifie, avec les
   frequences, residus, orthogonalite masse et temps.
3. **Sparse audit** : verifier le format de `K`, `M`, `K-sigma*M`, le nombre de
   non-zero et l'absence de conversion dense.
4. **Factorization ladder** : comparer SuperLU, MUMPS in-core et MUMPS
   out-of-core sur une machine dediee, d'abord a `100k`, puis a `500k`.
5. **Scale trial** : ne tenter `1M` puis `2M` qu'avec timeout, telemetry,
   quota disque et arret propre. Un timeout ou une limite de ressources reste
   `BLOCKED`, jamais `PASS`.
6. **Qualification** : ne relever la limite que si les invariants physiques
   et numeriques sont passes sur plusieurs tailles et si le profil de
   ressources est archive.

## R1, R2, R3 et priorisation

| Gate | Etat de la revue 0.2.2a0 | Action de suivi |
| --- | --- | --- |
| R1 | fermee par le profil runtime (`slepc4py`, CPU/RAM, image) | maintenir le profil dans chaque campagne HPC |
| R2 | fermee pour le gate borne avec seuil Newmark `1e-5` | calibrer le seuil par domaine avant une revendication production |
| R3 | executee mais `BLOCKED_TIMEOUT` sur matrix-free 1M | conserver timeout et telemetry, optimiser en v0.3.0 |
| R4 phase 1 | implementee : refus SLEPc > `500k` avant assemblage | proteger la release et ajouter le test de contrat |
| R4 phase 2 | recherche non qualifiee | MUMPS, out-of-core, factorisation et campagne de scaling |

La priorite recommandee est :

1. fusionner la protection R4 phase 1 avec la regression rapide ;
2. maintenir R1 et R2 comme controles de tracabilite, sans les melanger au
   developpement de la factorisation ;
3. instrumenter R3 et R4 avec le meme schema de telemetry ;
4. construire la matrice de comparaison PETSc/SLEPc avant toute modification
   de formulation FEM ;
5. traiter l'out-of-core et le modal 2M comme un chantier de recherche
   independant, sans modifier le statut des scopes deja valides.

## References techniques

- [SLEPc ST et shift-invert](https://slepc.upv.es/release/documentation/manual/st.html)
- [SLEPc configuration du KSP interne](https://slepc.upv.es/release/documentation/hands-on/hands-on2.html)
- [SciPy `eigsh` et `OPinv`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html)
- [PETSc/MUMPS out-of-core](https://petsc.org/release/src/mat/impls/aij/mpi/mumps/impl/imumps.c.html)

Owner review requise avant toute promotion de la limite ou toute
qualification du modal au-dela de `107811` DDL.
