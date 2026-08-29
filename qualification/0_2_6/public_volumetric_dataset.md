# Public Volumetric Geometry Dataset

## Purpose and boundary

This is a reproducible geometry and meshing corpus for QF Solver 0.2.6a0.
It is not a structural validation campaign and it does not promote any FEM
formulation. A generated QF case is a neutral linear-static smoke case only.

The source is the official [FreeCAD-library repository](https://github.com/FreeCAD/FreeCAD-library),
whose parts are distributed under **Creative Commons Attribution 3.0
Unported** according to its repository README. The pinned source commit and
per-record attribution fields are in the [machine-readable manifest](public_volumetric_dataset_manifest.json).
Raw STEP files and generated meshes remain in the ignored local cache
`datasets/public_volumetric/`; they are not silently treated as tracked proof.

## Corpus snapshot

| Metric | Result |
| --- | ---: |
| STEP candidates in pinned tree | 2,894 |
| Selected records | 100 |
| Downloaded records | 100 |
| Volumes with a valid Gmsh TET4 mesh | 78 |
| Records rejected or not meshed | 49 |
| TET4-ready records | 78 |
| TET10-ready records | 67 |
| HEX8-ready records | 0 |
| HEX20-ready records | 0 |

The 22 non-meshed selected records and 27 pre-selection rejections remain
visible in the manifest with their reasons. No HEX result is inferred from a
tetrahedral mesh and no recombination success is claimed where Gmsh did not
produce a coherent hexahedral mesh.

## QF execution

The generated TET4 cases were attempted independently with the standard QF
CLI and SciPy sparse direct route. The runner records command, return code,
duration, peak RSS when `psutil` is available, solver diagnostics and a digest
of each result before deleting the large runtime JSON.

| Metric | Result |
| --- | ---: |
| QF cases attempted | 78 |
| Numerical solve status PASS | 39 |
| PASS with `run_verdict=PASS` | 15 |
| PASS with `run_verdict=WARNING` | 24 |
| True QF FAIL | 38 |
| Timeout | 1 |
| Maximum completed-case DDL | 8,178 |
| Maximum observed RSS | about 1.79 GiB |

Warnings are not promoted to qualification: they principally report mesh
quality below the bounded TET4 audit threshold. The true failures are retained
as diagnostic evidence. They include audit-gate rejection for low-quality
meshes, abnormal direct residuals, repeated-node connectivity, one singular
matrix and one 120-second timeout. The campaign therefore demonstrates
pipeline diversity and fail-closed behavior, not universal solve success.

## Reproduction

With the optional pinned Gmsh dependency installed:

```text
python scripts/public_volumetric_dataset.py --limit 100
python scripts/run_public_volumetric_cases.py --timeout 120
```

The second command writes the compact report
`public_volumetric_qf_results.json` and removes per-case runtime results to
avoid turning a large displacement field into versioned evidence.

## Provenance and limitations

- The source tree commit, source blob SHA, pinned URLs, original SHA-256 and
  transformations are stored per record.
- The current source selection is filtered by explicit excluded-domain terms;
  license and domain review remain bounded by the source metadata and path
  audit.
- FreeCAD-library attribution is required by CC BY 3.0; the generic author
  field points to the pinned source history rather than inventing a contributor
  name.
- The generated structural setup fixes the minimum-x nodes, constrains two
  transverse DOFs at one maximum-x node and distributes 1,000 N across the
  maximum-x nodes. This is a reproducible smoke convention, not a physical
  load case for the represented object.
- TET10 availability is recorded as a mesh capability; the generated QF smoke
  case currently uses TET4. HEX8/HEX20 comparison is not available in this
  corpus snapshot.
- The corpus does not qualify stresses, convergence, element formulations or
  material behavior, and it is not a replacement for element-level V&V.
