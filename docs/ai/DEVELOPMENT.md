# Source-first development navigation

**Purpose:** answer “where should I inspect before changing this feature?”
**Revision:** 2026-10-25. This guide does not authorize test or campaign execution.

| Intended change | Inspect first | Follow-on review |
|---|---|---|
| Add an element family | [elements](../../src/solveur/elements/) and [compatibility preflight](../../src/solveur/compatibility/) | Assembly, DOFs, supported analysis matrix, element unit tests, analytic/convergence contract |
| Add or change a material law | [materials](../../src/solveur/materials/) and nonlinear state | Tangent/residual consumers, state transaction and checkpoint tests, material and global contracts |
| Change element matrices | Element implementation and its local formulation contract | Shared assembly, mass/stiffness/damping users, element tests plus route-level oracle |
| Change global assembly | [assembly](../../src/solveur/core/assembly/assembler.py) and assembly plan | DOF/constraint transformations, static/modal/dynamic/nonlinear/contact consumers |
| Change MPC or RBE | [constraints](../../src/solveur/core/constraints.py), [RBE](../../src/solveur/core/rbe.py), [DOFs](../../src/solveur/core/dofs.py) | Reduction/reconstruction, reactions and result recovery; RBE and route integration tests |
| Add a dynamic analysis | [analysis modules](../../src/solveur/core/analyses/), [router](../../src/solveur/core/router.py), settings and route preflight | Prepared system identity, excitation, damping, results, checkpoints, energy/residual and time-convergence evidence |
| Change modal bases | [modal_basis.py](../../src/solveur/core/analyses/modal_basis.py), [modal_basis_numerics.py](../../src/solveur/core/analyses/modal_basis_numerics.py) | Reduced harmonic and modal Newmark consumers; WP04/WP05/WP06 contracts and tests |
| Change contact | [contact package](../../src/solveur/contact/), contact assembly/search and WPC01/WPC02 contracts | Gap/force balance, search/sliding behavior, mesh sensitivity, negative and bounded historical evidence |
| Change rotordynamics | [gyro assembly](../../src/solveur/core/assembly/rotating_disk_gyro.py), [rotating modal](../../src/solveur/core/analyses/rotating_modal.py), [QEP](../../src/solveur/core/analyses/qep.py), [Campbell](../../src/solveur/core/analyses/campbell.py), [tracking](../../src/solveur/core/analyses/modal_tracking.py) | Frozen v0.2.11 contracts, complex-mode normalization, refusal behavior and planned WP12 regression |
| Change Python API or CLI | [qf_solver facade](../../src/qf_solver/__init__.py), [API](../../src/solveur/api/), [CLI](../../src/solveur/cli/), [pyproject.toml](../../pyproject.toml) | API stability, route dispatch, output compatibility and explicit refusal tests |
| Change post-processing/results | [post-processing](../../src/solveur/post/), [result models](../../src/solveur/core/results.py) | Result contracts, serialization round trips, units/frames and export integration tests |
| Change IO | [IO package](../../src/solveur/io/) and API IO facade | Input validation, schema/version compatibility, path safety and overwrite semantics |
| Change qualification machinery | [scripts](../../scripts/), [verification code](../../src/solveur/verification/), [qualification records](../../qualification/) | AGENTS.md, manifest/runner requirements, Owner authorization, immutable evidence policy |
| Change performance-sensitive code | Hot path plus caller and backend policy | Existing workload identity, profiler/benchmark protocol, memory and scaling evidence; do not generalize one benchmark |

## Before editing

1. Read [INDEX.md](INDEX.md), then the relevant domain page and normative contract.
2. Confirm the current branch, source identity, worktree state, and task-specific limits.
3. Trace direct callers and indirect shared dependencies using [DEPENDENCIES.md](DEPENDENCIES.md).
4. Inspect exact tests, fixtures, markers, runners, and whether execution would produce scientific evidence.
5. Keep code change, test result, and qualification claim distinct.

The repository’s [AGENTS.md](../../AGENTS.md) policy controls execution. Neither this page nor a test’s existence grants authority to run qualification, alter manifests, or write evidence.
