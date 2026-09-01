---
doc_id: DOC-027-002
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Gate Matrix

This matrix is a controlled status record. WP01 is `PASS` for release truth, WP02 is
`PASS` for the combination-level registry control, and WP03 is `PASS` for the
technical descriptor and fail-closed preflight control, and WP04 is `PASS` for
the additive V&V harness control. WP05 is `PASS` for the external deck
preflight only; it issues no WEDGE6 QF result or capability. WP06 is `PASS`
for the additive mesh-quality diagnostic contract; it introduces no new
numerical capability or universal quality cutoff. The WP07 row is technical
kernel evidence only: WEDGE6 remains `EXPERIMENTAL` and is not publicly
qualified. WP08 adds the bounded static vertical slice without changing that
maturity. WP12 records bounded large-scale readiness evidence for the existing
structured TET4 route; its Owner decision remains pending and its resource
limits are not success claims.

| Gate | Work package | Purpose | Dependencies | GO evidence | STOP conditions | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `027-G01` | WP01 | Release truth and provenance | None | exact baseline, clean-state and version records | SHA, tag or version mismatch | `PASS` |
| `027-G02` | WP02 | Element x analysis x material x route registry | G01 | schema, uniqueness and implementation cross-check | inferred maturity or orphan capability | `PASS` |
| `027-G03` | WP03 | Compatibility descriptors and preflight | G02 | deterministic accept/reject matrix | default-path or API behavior change | `PASS` |
| `027-G04` | WP04 | Declarative V&V harness | G01-G02 | additive runner contract and replay proof | numerical route refactor or hidden command execution | `PASS` |
| `027-G05` | WP05 | C3D6/PENTA6 oracle preflight | G01-G02 | comparable deck contract and availability record | non-comparable oracle presented as PASS | `PASS` |
| `027-G06` | WP06 | Mesh quality/distortion contract | G02-G03 | metrics, invalid cases, deterministic classification and preflight diagnostic | universal aspect-ratio cutoff | `PASS` |
| `027-G07` | WP07 | WEDGE6 kernel and elemental V&V | G03, G05, G06, T1-R | reviewed contracts, six-node kernel, stiffness/recovery checks, exact quality certificate and deterministic evidence | certified inversion not rejected; rank or rigid modes unexpected; affine patch or quadrature check fails; existing element formulation changed | `PASS` |
| `027-G08` | WP08 | WEDGE6 static vertical slice | G07 | 15-case Gmsh/import/load/assembly/equilibrium/post evidence with deterministic replay | missing face/load, silent unsupported path or unexpected failure | `PASS` |
| `027-G09` | WP09 | WEDGE6 robustness and external V&V | G08 | mesh/distortion/adversarial evidence with explicit external availability and comparability outcomes | unexplained divergence, weakened threshold or false external PASS | `PASS_WITH_LIMITATIONS` |
| `027-G10` | WP10 | WEDGE6 modal evidence | G08-G09 | mass, modes, residual, mesh and replay evidence | static evidence transferred without modal proof | `NOT_STARTED` |
| `027-G11` | WP11 | Existing maturity and J2 gaps | G01, G04, G06 | all-family J2/increment/tangent evidence | formulation change or relaxed acceptance | `NOT_STARTED` |
| `027-G12` | WP12 | Large-scale readiness | G02, G04, G06 | declared size/resource measurements, bounded backend/resource verdicts and deterministic replay | universal 1M claim or uncharacterized failure | `PASS_WITH_LIMITATIONS` |
| `027-G13` | WP13 | Research/stretch selection | relevant closed prerequisites | explicit Owner scope selection | scope creep or transitive promotion | `NOT_STARTED` |
| `027-G14` | WP14 | Release closeout | G01-G13 as applicable | docs, full regression, package and Owner review | stale claim, provenance gap or regression | `NOT_STARTED` |

`027-G07` required a design review before implementation. The external oracle
preflight and formulation review preceded the kernel, and the current PASS is
limited to the elemental technical route. The descriptor reports
`EXPERIMENTAL_ROUTE`; WP08 provides a bounded static user workflow, and WP09
adds controlled robustness evidence without creating a public qualification.
CalculiX C3D6 is explicitly non-formulation-compatible with the QF production
quadrature. WP09-R repairs the headless Code_Aster path and records one
bounded affine PENTA6 correlation through a derived image pinned to the base
image digest. WP10
modal evidence remains required for its separate claims. G13 may remain open
or deferred without blocking a bounded core release when research routes are
explicitly excluded.

`027-G12` is `PASS_WITH_LIMITATIONS` for the declared structured TET4
linear-static readiness scope. Matrix-free CG completed 100k through 750k
target levels (actual maximum 750141 DOF); 300k assembly-only evidence reached
311469 DOF; SciPy direct was resource-limited at 107811 DOF; higher SciPy
levels were rejected by the configured 200000-DOF guard; and the 1M
matrix-free attempt was time-limited after 600 seconds. These results are
hardware- and topology-specific and do not qualify a universal 1M solve.
The evidence is recorded in
`qualification/0_2_7/wp12_scaling_evidence.json`,
`qualification/0_2_7/wp12_assembly_probe_300k.json` and
`0_2_7_large_scale_readiness.md`; `027-OD-005` remains
`PROPOSED_OWNER_REVIEW`.
