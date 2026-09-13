---
doc_id: DOC-029-021
revision: 0.1
status: controlled-evidence
applicable_version: 0.2.9-development
---

# WP04-C2R5 — residual precision and near-floor termination forensics

**Start SHA:** `571b7f64450ec556e1f9a59ecc65826cf49675d5`
**Scope:** C2-M2 only; canonical existing line search; no M3, M4, PETSc,
PyAMG, threshold change, convergence-policy implementation or mechanics change.

This record is diagnostic evidence. It does not close G04-10 or promote TET4
maturity. The machine-readable record is
`qualification/0_2_9/c2r5/residual_precision_audit.json`.

## Frozen route and protocol

The rerun used the canonical C2 route:

| control | value |
| --- | --- |
| mesh | `48 x 24 x 24`, 165,888 TET4, 91,875 full DOFs |
| linear solver | MINRES |
| preconditioner | Jacobi |
| MINRES `rtol` / `atol` / `maxiter` | `1e-11` / `1e-14` / `10000` |
| direct fallback | OFF |
| Newton tolerance | `1e-10` |
| load increments | 12 fixed target factors |
| line search | existing/enabled |

The original C2 and R2B routes use the existing enabled line search. R2B M1
direct and MINRES use the same setting. C2R3 explicitly set
`line_search=off`, which C2R4 classified as `PROTOCOL_DRIFT`. C2R5 therefore
matches the canonical protocol rather than C2R3.

## Residual definition

The nonlinear driver forms

```text
target = lambda * F_ext
residual = target - F_int(u)
relative_residual = ||residual[free]||_2 /
                    max(||target[free]||_2, force_scale, 1.0)
```

The C2 call does not provide an additional `force_scale`, so the denominator is
`max(||target[free]||_2, 1.0)`. At the captured step-4 target the free target
norm is `0.6666666666666664`, hence the effective denominator is `1.0`. The
numerator has force units; the reported residual is dimensionless. The
initial residuals are O(`1e-1`) because the prior accepted state is an
equilibrium for the preceding load factor, not for the next target factor.

## Canonical M2 reproduction

The run reproduced the canonical outcome: load steps 1–3 were accepted and
step 4 terminated with `LINE_SEARCH_FAILURE` at Newton iteration 26. There
were 67 iteration events, three accepted-step events and one terminal failure;
the run did not enter M3.

| item | value |
| --- | ---: |
| accepted steps | 3 |
| accepted factors | `1/12`, `2/12`, `3/12` |
| failure step / iteration | 4 / 26 |
| failure residual | `1.0411047989090212e-10` |
| line-search iterations reported | 106 cumulative in the failing step diagnostics |
| wall / CPU time | `1678.3279889000114 s` / `1741.671875 s` |
| process peak RSS / private-or-USS | `1897238528` / `1891807232` bytes |
| telemetry sample peak RSS / private-or-USS | `760750080` / `735080448` bytes |

The process peak is from an independent sampling thread over the nonlinear
run; the telemetry peak is sampled at emitted events. They are intentionally
reported as different measurements and neither is a durability guarantee.

## Captured state

The one failing step-4 reduced system was captured outside Git:

```text
path: C:\Users\fari\AppData\Local\Temp\qf_solver_029_c2r5_forensics\c2_m2_canonical_step4_failure.npz
shape: 90000 x 90000
nnz: 3835710
size: 27394683 bytes
SHA-256: f94e13d6a92c7ed6203a85f9be23d7fb7d23bf7552b8081393574472cb6b1b01
```

The captured state is the step-4 target at `lambda=1/3`; the accepted state
before that step has `lambda=1/4`, displacement norm
`4.254463589033866`, composite digest
`5e7ed9762d80b6dd87a9d9b55651e70f0e4b44067b5ecd6c99465fab76efe706` and the
component digests recorded in the JSON record. The captured trial displacement
norm is `5.672080202650529`.

## Force cancellation and equilibrium

All cancellation norms below are on free DOFs, with the target external force
`lambda*F_ext`.

| quantity | 2-norm | infinity norm |
| --- | ---: | ---: |
| target external force | `0.6666666666666664` | `0.026666666666666665` |
| internal force | `0.6666666666666998` | `0.026666666668667273` |
| imbalance | `1.0411047989090212e-10` | `3.7411558226341235e-12` |
| cancellation indicator | `12806907957.1103` | `14255843879.227219` |

The accepted state before step 4 has force/moment relative errors
`1.324838322760566e-14` and `4.172828174723821e-15` when evaluated against
its `lambda=1/4` target. The captured trial has force/moment relative errors
`2.4672319589855068e-14` and `2.4472628640241725e-15` against its `lambda=1/3`
target. Thus the trial is not mislabeled as an accepted equilibrium state;
the equilibrium evidence is independently near machine scale.

## Accumulation-precision diagnostics

Local kinematics and constitutive values were evaluated in float64 in every
method. Only the global sum of already-computed float64 local internal-force
contributions was varied.

| accumulation | normalized residual |
| --- | ---: |
| normal float64 `np.add.at` | `1.0411047989090212e-10` |
| sorted per-DOF pairwise float64 | `1.0411048963249379e-10` |
| compensated/Kahan float64 | `1.0411048278985379e-10` |
| `np.longdouble` accumulation | `1.0411048047789044e-10` |

On this Windows environment `np.longdouble` reports dtype `float64` and
itemsize 8, so it is not an extended-precision accumulator here. The pairwise,
compensated and platform-longdouble values are small perturbations of the
normal result, not a material reduction below `1e-10`. Their internal-force
differences from the normal sum have norms `1.0828288342138365e-14`,
`8.705357908075808e-15` and `9.963777015254368e-15`, respectively.

Five repeated normal reassemblies of the untouched captured trial were
bitwise-identical. Their normalized residual statistics were:

```text
min  = 1.0411047989090212e-10
max  = 1.0411047989090212e-10
mean = 1.0411047989090212e-10
spread = 0.0
```

The per-DOF accumulation diagnostic had 1,990,656 local scalar contributions,
between 2 and 24 contributions per DOF, maximum local magnitude
`0.533518308741781` and free-DOF sum-of-absolute-contributions norm
`192.14695002494148`.

## Rounding-bound diagnostic

Using the prospective per-DOF model
`gamma_n * sum(abs(local_contributions))`, with float64 machine epsilon
`2.220446049250313e-16` and maximum `n=24`, gives an estimated normalized
accumulation floor of `9.926818702066467e-13`. The observed-to-estimated ratio
is `104.87799063886342`. This bound is only for summing float64 local
contributions; it does not bound every constitutive, kinematic, vectorized
einsum or norm operation. It therefore does not prove that global accumulation
alone causes the observed floor.

## Same-state linear correction forensics

The exact captured tangent and RHS were solved independently with direct
SuperLU and MINRES/Jacobi. Each correction was applied to a detached copy of
the same trial state, followed by normal and alternate residual assembly.

| solver | correction norm | relative correction | raw linear residual | eta-infinity | solution delta vs direct | nonlinear residual after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| direct | `8.108503804890719e-16` | `1.4295467474352116e-16` | `2.4590020864264226e-15` | `1.148509118958703e-15` | — | `1.1786672101386367e-10` |
| MINRES `rtol=1e-11` | `8.10850383404193e-16` | `1.4295467525746333e-16` | `4.8764970402010876e-12` | `5.232341881338818e-13` | `2.768139786132888e-08` | `1.1786672101386367e-10` |
| MINRES `rtol=1e-12` | `8.108503805815807e-16` | `1.4295467475983066e-16` | `3.3207339399833917e-12` | `4.999305581031921e-13` | `2.972290615437137e-10` | `1.1786672101386367e-10` |

The alternate accumulation residuals after each correction are also identical
to the same displayed order (`1.1786672101386367e-10` normal; the companion
JSON retains all method values). No correction materially reduces the
physical imbalance; the direct correction is machine-scale and the two
MINRES corrections are indistinguishable at the state scale.

## Line-search forensics

At the failing Newton state the strict existing line search tested all of the
following alphas:

| alpha | merit | merit - initial |
| ---: | ---: | ---: |
| 1 | `1.1786672101386367e-10` | `1.3756241122961543e-11` |
| 1/2 | `1.087998092674283e-10` | `4.689329376526171e-12` |
| 1/4 | `1.0816636703227027e-10` | `4.0558871413681465e-12` |
| 1/8 | `1.0687095189798257e-10` | `2.760472007080446e-12` |
| 1/16 | `1.0608807344801181e-10` | `1.9775935571096863e-12` |
| 1/32 | `1.0537365372983584e-10` | `1.2631738389337184e-12` |
| 1/64 | `1.0495728321429686e-10` | `8.468033233947376e-13` |
| 1/128 | `1.0435852481068462e-10` | `2.480449197824943e-13` |
| 1/256 | `1.0430259234360327e-10` | `1.9211245270114322e-13` |
| 1/512 | `1.0429477685691295e-10` | `1.8429696601082412e-13` |
| 1/1024 | `1.041523504194613e-10` | `4.1870528559171174e-14` |
| 1/2048 | `1.0416104471125124e-10` | `5.056482034911369e-14` |
| 1/4096 | `1.0413191293026293e-10` | `2.1433039360804965e-14` |
| 1/8192 | `1.0412069200871767e-10` | `1.0212117815542812e-14` |
| 1/16384 | `1.0411521045606017e-10` | `4.7305651580512374e-15` |

The initial merit was `1.0411047989090212e-10`; every tested trial merit was
strictly larger. The smallest difference was `4.7305651580512374e-15`, with
relative difference `4.543793442320523e-05`, which is numerically resolved in
the scalar float64 merit even though the overall state is near its residual
floor. The recorded classification is therefore
`LINE_SEARCH_TRUE_REJECTION`, not a claim that the merit is physically exact
below all assembly error.

## Termination-policy analysis

No mixed termination criterion was implemented or numerically frozen. A future
floor-aware policy is plausible only as a scale-aware conjunction of the
primary residual, machine-scale relative correction, deterministic repeated
reassembly, independently measured force/moment balance, linear backward
error and finite-state checks. It must not be implemented as an arbitrary
`1.1x`, `1.5x` or `2x` relaxation of the residual threshold.

Because no acceptance threshold was proposed, the R2B M1 telemetry was not
retroactively reclassified and no retrospective policy-acceptance claim is
made (`NOT_APPLICABLE_NO_POLICY_THRESHOLD_PROPOSED`). Ordinary M1 convergence
remains governed by the existing `1e-10` criterion.

## Decision and governance

The evidence classifies the issue as:

```text
ROOT_CAUSE_CLASSIFICATION = NONLINEAR_RESIDUAL_NUMERICAL_FLOOR
MECHANISM = FORCE_CANCELLATION_AND_FLOAT64_PRECISION_LIMIT
RECOMMENDED_NEXT_REMEDIATION = R6_FLOOR_AWARE_TERMINATION_POLICY
```

`R6_ACCUMULATION_PRECISION_REMEDIATION` is not supported by this bounded
diagnostic because alternate global summation did not materially lower the
residual. The rounding estimate is informative but not a proof of the whole
error budget. The line-search rejection is a true strict-merit rejection at
the captured state, while the accepted-state equilibrium and the correction
scale show why a policy decision is needed rather than another linear-solver
tuning pass.

No threshold, convergence policy, mechanics formulation, element formulation
or maturity status changed. M3, M4, PETSc and PyAMG were not run. WP04
remains `HOLD`, G04-10 remains `UNRESOLVED`, WP04 points remain `0/12` and the
validated total remains `29/100`.

## Reproducibility and tooling

- Main runner: `scripts/run_wp04_c2r5_residual_precision_audit.py`.
- Offline repeat: `scripts/run_wp04_c2r5_offline_checks.py`.
- Canonical JSONL telemetry is flushed at every event and contains no matrices
  or full vectors.
- Production source was not changed in C2R5; the diagnostic backend-label fix
  predates this phase and is included in the start SHA.
- No full repository suite was run. Targeted groups passed: C2R5-adjacent
  sparse/contract checks `5 passed`, unified nonlinear/checkpoint/restart/
  robustness checks `241 passed`, and WP04-B mechanics checks `43 passed`.
  The separate legacy failure-campaign test remains an inherited fixture
  failure: it monkeypatches the removed private `iteration.spsolve` seam,
  while the approved adapter dispatches through `LinearSystemSolver`; its
  typed case report is otherwise correct. The heavier mixed failure/C1
  structural command was stopped before completion and is not counted.
- Ruff PASS, mypy on both new diagnostic scripts PASS with no issues,
  compileall PASS, qualification JSON validation PASS and MkDocs strict PASS.
