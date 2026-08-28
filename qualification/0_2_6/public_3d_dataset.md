# Public 3D Geometry Corpus

## Purpose

This corpus provides a reproducible, license-audited set of public 3D geometries for future QF Solver verification, meshing, robustness, and scaling work. It is a geometry corpus, not a claim that every object is already a valid structural-analysis case.

## Source and License

The source is the public Gazebo Fuel **Scanned Objects** collection queried through its official API:

- API: <https://fuel.gazebosim.org/1.0/models?page=1&per_page=100&q=collections%3AScanned%20Objects>
- Dataset description: <https://research.google/blog/scanned-objects-by-google-research-a-dataset-of-3d-scanned-common-household-items/?hl=en_GB&version=v1>
- Accepted license: **Creative Commons Attribution 4.0 International**

Every accepted record stores its source URL, source owner, license URL, original archive SHA-256, original mesh SHA-256, and original format in [the machine-readable manifest](public_3d_dataset_manifest.json).

## Current Corpus Snapshot

The reproducible selection contains 120 candidate records from a catalog of 1,046 entries:

| Result | Count |
| --- | ---: |
| Gmsh mesh accepted | 114 |
| Selected records without a usable OBJ | 5 |
| Mesh quality review required | 1 |
| Pre-selection exclusions | 13 |
| Accepted mesh category | 114 `SHELL` / `TRI3_SURFACE` |
| Accepted `SOLID_TET` | 0 |
| Accepted `SOLID_HEX` | 0 |

The accepted scans are surface geometries. No volume mesh is claimed where Gmsh did not produce one. In particular, no HEX capability is inferred from a surface mesh, and no neutral QF solid case is generated without a valid volume discretization and a physically meaningful setup.

## Reproduction

From the repository root, with the pinned optional Gmsh dependency available:

```text
python scripts/public_3d_dataset.py --limit 120 --mesh
```

Raw archives and generated meshes are kept in the ignored local cache `datasets/public_3d/`. The tracked manifest is the portable corpus index and records the exact URLs, hashes, transformations, mesh classifications, quality values, and rejection reasons. Gmsh attempts are isolated per object; a timeout is recorded instead of stopping the whole campaign.

The pipeline attempts a volume route only for closed topologies with at most 500 triangles. This is a bounded resource policy, not a quality threshold for structural qualification. Larger or otherwise unsuitable scans remain surface candidates until a separate volume-meshing study is justified.

## Scope and Limitations

- The corpus is intended for geometry and meshing experiments; it does not qualify a FEM formulation.
- Surface acceptance means that a Gmsh first-order triangular surface mesh was generated with positive reported quality values.
- The corpus deliberately excludes aerospace, aircraft, engines, turbines, compressors, casings, and related terms.
- Entries with missing geometry, non-accepted licensing metadata, or mesh-quality concerns remain visible as rejected/review records.
- Any later structural QF case must add an explicit modeling convention, units, material, loads, boundary conditions, and an independent verification record.
