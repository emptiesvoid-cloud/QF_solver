# Independent challenge of the WP12 V&V inventory

**Status:** PREPARATION_ONLY; static review only.
**Numerical execution:** NUMERICAL_EXECUTION_NOT_PERFORMED.
**WP12:** OPEN.

This is a critical read-only audit of the proposed inventory, including a challenge by the independent specialist agent `infra_inherited` on 2026-10-26 as part of WP12-P. Its scope was the source map, tests, runners, and inherited capabilities. The reviewer did not edit repository files, import the solver, collect pytest nodes, or run tests/benchmarks. No separate review report was stored in the repository; actionable findings and their disposition are summarized below. This audit does not certify scientific correctness.

## Challenge results

### Coverage checks

- Each registered element family is represented separately: TET4, TET10, HEX8, HEX8-SRI, HEX20, WEDGE6, PYRAMID5, BEAM2, MITC3, MITC4, discrete mass/spring, and rotating disk.
- Materials distinguish ordinary elastic/orthotropic/laminate, J2, corotational and total-Lagrangian routes, source-level finite-strain kernels, Hencky, finite-kinematic J2 identifier, and composite failure indicators.
- Analysis routes separately cover static, modal, buckling, direct transient/harmonic, WP02–WP07 methods, D01/D02, nonlinear state, contact, rotor/Campbell, IO/API/CLI, and optional backends/performance.
- Rows avoid claiming a universal element/material/analysis product. PYRAMID5 is identified as kernel-only without descriptor; WEDGE6 experimental route declarations are not promoted.

### Critical interpretation checks

1. **Test presence versus execution:** matrix entries mean only that source nodeids/files exist unless a report/manifest records a run. This plan reports no new test execution.
2. **Historical identity:** old reports are not transferred to science commit 00428ad without report-level identity verification. The current checkout also contains later runner and documentation commits.
    - Parameterized selection: a test function without its pytest parameter suffix is not an exact nodeid. The matrix marks such rows as requiring source-level discovery; no proposed command may use the bare function as a final approved selector.
3. **Projection dependency:** WP04 symmetric projection changed in 1f3148f and b5501e1. WP05 consumes projected operators directly; WP06 consumes the modal basis and shared Newmark core; WP07 composes with WP05/WP06. A small downstream sentinel set is required after the direct projection tests.
4. **C01/C02/E01:** preserve CLOSED_NEGATIVE, AR/N03-only CLOSED_BOUNDED, and OPEN_WITH_BOUNDED_CERTIFICATES. Do not interpret bounded evidence as general contact/material qualification.
5. **Rotor:** GYRO-01–06 are v0.2.11 historical, EXPERIMENTAL; GYRO-06 is internal mesh convergence and retains a 100 rad/s ambiguity. The full historic mesh/speed grid is not reproduced by narrower current unit tests.
6. **HPC:** PETSc/SLEPc adapters and MPI readiness guardrails do not prove installed-backend scaling or real multi-node behavior.
7. **Performance:** old timing is case/environment-bound. The dense QEP sample around 1000 physical DOF (~271 seconds and ~517 MB in its recorded environment) is not an extrapolation rule or an approved threshold.
8. **Convergence:** the TET4 unit node `test_timoshenko_reference_and_convergence_metrics` checks reference/metric logic and synthetic trends, not the multi-level FEM helper. A separate executable study must be chosen or a bounded test created.
9. **Circular or weak oracles:** direct/reduced response may share assembled operators; finite differences may share constitutive code; stress output may share recovery and constitutive transformations. Label these internal consistency/derivative checks and pair them with an independent oracle where feasible.
    - The coupled 2-DOF test uses SciPy `eigh` for expected eigenvalues, as does the production route. The plan now labels it same-backend consistency and proposes a separate scalar characteristic-polynomial oracle if an independent check is needed.
10. **Tests with broad side effects:** verification nodeids can run multiple mesh levels, write files, invoke external dependencies, or execute solve loops. Inspect the selected test body before approving a run; names and directory placement do not prove a test is cheap or non-numerical.

## Residual inventory limitations

- The CSV is a capability-level index, not a full enumeration of every test function or every test parameter instance in the repository. It lists exact representative nodes where confirmed and marks discovery where the parameterized node is unresolved.
- Historical commits/manifests are report-specific; a full provenance replay would require each archive and its native manifest. This plan does not rehash or reconstruct those external records.
- Some source directories and existing verification campaigns are represented by family-level paths; each future campaign must resolve exact source, test, fixture and output identities.
- The recommended first-campaign order is aligned across the master plan and Owner decision proposal: projection, spring-mass modal, coupled 2-DOF modal, SDOF modal Newmark, then BEAM2 and a bounded multi-mesh study. The first is algebraic; the next three invoke solver/analysis routes.
- The existence of external verification modules does not establish that the external executable is installed or that the formulation matches.
- Matrix status “no WP12 execution” means this planning task performed no such execution. It does not erase results recorded in earlier reports.

## Independent audit conclusion

The plan is suitable for Owner review as a scoped program, provided the Owner resolves the local-policy proposal and criteria before execution. No P0 production defect was demonstrated. The key gates are the current-source projection chain, an exact multi-mesh local FEM case, and separate disposition of existing bounded/negative workstreams. This conclusion is not a WP12 closure recommendation.
