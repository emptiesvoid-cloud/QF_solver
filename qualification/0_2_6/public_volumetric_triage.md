# Public Volumetric Campaign Triage

This report classifies every non-PASS execution in the recorded campaign. It is a diagnostic corpus report, not a FEM qualification claim.

- QF source SHA: `e7a10d552cfaaf4ecc1150f44aed4d1528697bd2`
- Runner worktree dirty: `False`
- Non-PASS cases classified: `39`
- Categories: `{'B': 21, 'D': 2, 'C': 15, 'G': 1}`

## Category key

| Category | Meaning |
| --- | --- |
| A | Source model invalid or outside the intended volumetric use |
| B | Bad or insufficient mesh quality |
| C | Automatic BC/load pattern unsuitable for disconnected or multi-volume geometry |
| D | Import/connectivity/element IDs invalid |
| E | Plausible QF bug |
| F | Numerical robustness or convergence issue requiring a reproducer |
| G | Performance, memory or timeout issue |
| H | Unknown |

## Case matrix

| Case | Category | Mesh | Components | Qmin | Proof | Action |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| FCL-0004 | B | 1243 TET4 | 1 | 0.00752062 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0006 | B | 2097 TET4 | 1 | 0.00349987 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0009 | B | 2180 TET4 | 1 | 0.000497756 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0010 | B | 538 TET4 | 1 | 0.0423281 | The Gmsh quality minimum is 0.0423281, below the bounded audit target. | Remesh or retain only as an explicitly low-quality robustness case. |
| FCL-0011 | D | 8180 TET4 | 7 | 4.94769e-16 | Invalid, repeated or zero-volume tetrahedral connectivity is present. | Reject this mesh from the neutral QF case and retain the source as a mesh diagnostic. |
| FCL-0014 | B | 2439 TET4 | 1 | 0.00405822 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0015 | B | 4049 TET4 | 1 | 0.00737211 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0017 | C | 3873 TET4 | 2 | 0.00231713 | The mesh contains 2 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0023 | B | 1150 TET4 | 1 | 0.00850392 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0025 | C | 10898 TET4 | 11 | 0.000679885 | The mesh contains 11 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0026 | C | 1388 TET4 | 3 | 0.0452995 | The mesh contains 3 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0028 | C | 1328 TET4 | 4 | 0.00341264 | The mesh contains 4 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0029 | C | 1520 TET4 | 3 | 1.21888e-06 | The mesh contains 3 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0032 | C | 1867 TET4 | 7 | 0.129923 | The mesh contains 7 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0036 | B | 523 TET4 | 1 | 0.00548536 | The Gmsh quality minimum is 0.00548536, below the bounded audit target. | Remesh or retain only as an explicitly low-quality robustness case. |
| FCL-0038 | C | 1426 TET4 | 5 | 0.285337 | The mesh contains 5 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0040 | B | 2101 TET4 | 1 | 0.0658222 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0041 | C | 3942 TET4 | 6 | 0.0144538 | The mesh contains 6 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0042 | C | 1354 TET4 | 4 | 0.106669 | The mesh contains 4 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0044 | C | 2559 TET4 | 6 | 0.0141876 | The mesh contains 6 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0045 | C | 2075 TET4 | 6 | 0.0120905 | The mesh contains 6 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0046 | C | 747 TET4 | 4 | 0.0648042 | The mesh contains 4 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0047 | B | 7555 TET4 | 1 | 0.00148721 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0050 | B | 7027 TET4 | 1 | 3.12673e-05 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0051 | B | 1161 TET4 | 1 | 0.00294669 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0055 | B | 2278 TET4 | 1 | 0.00747009 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0056 | C | 65627 TET4 | 16 | 0.00376797 | The mesh contains 16 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0057 | B | 1078 TET4 | 1 | 0.00737025 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0060 | G | 126286 TET4 | 1 | 0.0133437 | The QF process exceeded the 120 second limit. | Measure separately with a resource budget and a larger timeout. |
| FCL-0062 | D | 924 TET4 | 1 | 3.2182e-16 | Invalid, repeated or zero-volume tetrahedral connectivity is present. | Reject this mesh from the neutral QF case and retain the source as a mesh diagnostic. |
| FCL-0065 | B | 1647 TET4 | 1 | 0.0178973 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0070 | C | 1771 TET4 | 31 | 0.12473 | The mesh contains 31 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0071 | B | 1166 TET4 | 1 | 4.85005e-06 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0076 | B | 1198 TET4 | 1 | 0.0181732 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0078 | C | 3191 TET4 | 5 | 0.00552746 | The mesh contains 5 disconnected components; one global support pattern cannot constrain them all. | Do not run the neutral case; reject it or define per-component physical boundary conditions. |
| FCL-0085 | B | 2021 TET4 | 1 | 0.00258075 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0090 | B | 1361 TET4 | 1 | 0.00531877 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0095 | B | 1179 TET4 | 1 | 0.0313812 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |
| FCL-0096 | B | 1264 TET4 | 1 | 0.0464973 | QF solved numerically but the engineering audit rejected low-quality element checks. | Keep as a mesh-quality robustness diagnostic; do not promote it as a successful case. |

## Boundary/load audit

The generator applies the minimum-x nodes as a full support, constrains two transverse DOFs at one maximum-x node, and distributes 1,000 N over maximum-x nodes. The recorded cases have non-zero loads and valid node references. The decisive defect is not a zero-load setup: disconnected meshes receive a single global support pattern and can therefore remain mechanically under-constrained. Those cases must not be used to infer a QF solver defect.

## Decision

No QF numerical defect is demonstrated by this campaign. The actionable fixes are to reject degenerate connectivity from neutral cases, exclude disconnected assemblies from the single-domain BC convention, and characterize the large timeout separately. The remaining low-quality single-component cases stay visible as mesh robustness diagnostics.
