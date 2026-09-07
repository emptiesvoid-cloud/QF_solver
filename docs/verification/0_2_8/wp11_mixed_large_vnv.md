---
doc_id: DOC-028-WP11-VNV-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP11 mixed large-scale evidence

WP11 records performance and reproducibility evidence for the already bounded
mixed `linear_static` workflow. It does not promote a numerical capability or
create a general scalability claim.

## Mandatory model

The measured model contains 9,091 repeated conforming chains. Each chain has
one TET4, one WEDGE6 and one HEX8, with shared triangular TET4/WEDGE6 and
quadrilateral WEDGE6/HEX8 interfaces. The aggregate has 100,001 nodes,
300,003 translational DOFs and 27,273 elements: 9,091 of each family. Each
component is fully constrained on its `x=0` nodes and receives a unit total Z
load on two free top nodes. Material is homogeneous isotropic linear elasticity
with `E=210e9`, `nu=0.3`, `rho=7800`, in SI units.

This repeated-chain construction is deliberately explicit scale evidence. It is
not an arbitrary connected industrial mesh and does not support a universal
large-model performance or accuracy claim.

## Results

The small two-chain baseline passed before the large run. Both mandatory replays
passed with the same physics digest. The CG/Jacobi SciPy solve used 12
iterations and produced a relative residual of `2.484933369237869e-9`.
Force and moment closure errors were respectively `2.0730893516296557e-12`
and `4.358628815121694e-12`; the linear energy identity error was `0.0`.
The reduced stiffness had `1,309,104` nonzeros.

Measured phase timings for replays 1/2 were:

| Phase | Replay 1 | Replay 2 |
| --- | ---: | ---: |
| Assembly | 46.1126 s | 46.0056 s |
| Linear solve | 0.0537 s | 0.0516 s |
| Total | 62.4159 s | 62.5280 s |

Peak RSS after each replay was `754,372,608` bytes. The environment pack records
Windows 10, AMD64, Python/NumPy/SciPy package metadata, backend, preconditioner,
MPI rank count and the exact input/replay digests.

The optional 999,999-DOF target and 2,999,997-DOF stretch target were not run;
both remain non-blockers and are not represented as measured results.

Machine-readable records:

- [frozen WP11 contract](../../../qualification/0_2_8/wp11_mixed_large_contract.json)
- [WP11 evidence](../../../qualification/0_2_8/wp11_mixed_large_vnv.json)
- [WP11 matrix](../../../qualification/0_2_8/wp11_mixed_large_matrix.json)
- [input manifest and replay pack](../../../qualification/0_2_8/wp11_mixed_large_evidence/)

## Bounded claim

The permitted claim is: “Recorded large-scale mixed TET4/WEDGE6/HEX8 evidence
for this specific linear-static route and environment.” No modal, dynamic,
nonlinear, PYRAMID5, HEX8-SRI, nonconforming-interface, accuracy, production or
universal performance claim is made. No 0.2.7 evidence was changed.
