---
doc_id: DOC-LRG-001
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Large models

The large-model route is a separate workflow for structured TET4 linear-static
models. It is designed to avoid building a monolithic result document and can
use HDF5, MPI-IO and PETSc when those optional dependencies are installed.

## Supported bounded workflow

- analysis: `linear_static`;
- element: `TET4`;
- material: isotropic 3D linear elasticity;
- degrees of freedom: `UX`, `UY`, `UZ`;
- input: supported HDF5 or NPZ large-model files;
- scalable backend: optional PETSc/MPI;
- comparison backend: chunked SciPy for small or intermediate models.

Modal, dynamic, harmonic, nonlinear and generalized mixed-mesh large-model
claims are outside this page.

## Recorded evidence

The 1M, 3M, 5M and bounded 10M results are tied to their exact workload,
hardware, container, MPI layout and solver options. They demonstrate recorded
capability, not universal scalability. The active evidence index and matrix are
available in [`0.2.7 verification`](../verification/0_2_7/README.md) and the
[capability matrix](../verification/0_2_7/0_2_7_capability_matrix.md).

## Optional installation

Install the large-model dependencies only when needed:

```powershell
python -m pip install "qf-solver[large]"
```

PETSc and MPI availability is environment-dependent. When unavailable, the
standard package remains importable and the large route must fail with an
explicit controlled diagnostic.
