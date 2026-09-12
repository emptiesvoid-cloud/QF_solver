---
doc_id: DOC-029-037
revision: 0.1
status: evidence
applicable_version: 0.2.9-development
---

# WP04-C1 — TET4 mesh-convergence diagnosis

WP04-C1 is diagnostic work only. The frozen WP04-C qualification campaign is
preserved unchanged in commit `a5c3031f6b28b00476e328daff4845a741a5c161`.
Its original M1/M2/M3 G04-10 result remains **FAIL**: M3 versus M2 changes are
16.40618103457515% (tip displacement), 16.379509145773455% (strain energy),
and 24.310580151133324% (representative stress), above the frozen 2%/2%/10%
limits. This record does not reclassify that result or start WP04-D.

## Reproduction and extension

The exact frozen cantilever, distributed total load, boundary conditions,
TET4 six-tetrahedron subdivision, material, Newton tolerance, and 12 accepted
load intervals were rerun. M1/M2/M3 reproduced the stored observables exactly
(relative delta `0.0` for tip displacement, energy, and stress). The linear
diagnostic used the zero-state Total-Lagrangian tangent on the same meshes,
loads, and constraints. Extended levels were M4 = 32x16x16 (49,152 elements,
28,611 DOFs) and M5 = 48x24x24 (165,888 elements, 91,875 DOFs). M5 was run for
the linear diagnostic; M1–M4 were run through the nonlinear public route.
M6 was not attempted.

| Quantity | Linear M1 → M5 | Nonlinear M1 → M4 |
| --- | --- | --- |
| Tip displacement | -0.0877586, -0.1522625, -0.1773190, -0.1883826, -0.1973398 | -0.0876838, -0.1520161, -0.1769561, -0.1879571 |
| Strain energy | 2.1939654, 3.8065633, 4.4329762, 4.7095646, 4.9334950 | 2.1913031, 3.7974457, 4.4194487, 4.6936693 |
| Representative σxx | 1883.0054, 3983.3219, 5159.7189, 5547.1940, 5972.3997 | 1291.1114, 2224.4287, 2765.2002, 2837.8439 |

For the original M2→M3 comparison, the ratios of linear to nonlinear relative
change are 1.0030 (tip), 1.0047 (energy), and 1.2148 (stress). The matching
linear/nonlinear tip and energy trends show that the failure already exists in
the linear TET4 discretization, rather than being introduced by the small
finite deformation (`min det(F) = 0.9938` in the original M3 run).

M3→M4 nonlinear changes remain 6.2168% (tip), 6.2049% (energy), and 2.6271%
(stress). Thus the trend is monotone but has not entered a regime that could
support the frozen 2% qualification condition. The apparent-order fits in the
raw record are diagnostic only; they are explicitly not treated as asymptotic
qualification evidence.

## Load, mesh, subdivision, and sampling audit

Every level preserves the 1.0 domain volume to at most `8.88e-16`, has zero
negative-orientation elements, and retains identical shape-quality extrema
(minimum `0.2721258946`, median `0.3463420477`). The applied resultant remains
`[0, -50, 0]` to floating-point summation, and its force-weighted centroid is
`[4, 0.25, 0.25]`; the face area and resultant moment are invariant.

An alternate, self-similar body-diagonal linear M2/M3 audit changes tip and
energy by only about `1.2e-10` relative. A directional subdivision bias was
therefore **not detected** for this benchmark at the audited levels.

The original centroid-selected stress region remains physically interior, but
its discrete contributing volume varies with refinement (M1 0.0208333, M2
0.0130208, M3 0.0162037, M4 0.0136719, M5 0.0159144). This is potential
stress-sampling aliasing and may contribute to the stress metric, but it cannot
explain the independently failing tip-displacement and energy metrics.

## Diagnosis and boundary

Primary diagnosis: **SLOW_TET4_DISCRETIZATION_CONVERGENCE** (medium
confidence), with the original M1/M2/M3 range also pre-asymptotic for the
frozen cantilever observable. The evidence is consistent with low-order TET4
bending stiffness/convergence; it does not demonstrate locking or a
Total-Lagrangian formulation defect. The WP04-B objectivity, affine patch,
energy-gradient, tangent, and accepted-path work identities remain covered by
their focused regression.

Recommended Owner action: **C2_REQUALIFY_WITH_FINER_PREDECLARED_MESHES** only
after review and only with a new frozen campaign. It must retain WP04-C's
failed result and must not alter the existing thresholds, benchmark, physical
load, or public maturity. If a practical bounded campaign cannot demonstrate
the required asymptotic behaviour, the alternative is
**G04_10_NO_GO_FOR_TET4_CURRENT_SCOPE**. WP04-D remains unauthorized.

Raw arrays and machine-readable diagnostics are in
`qualification/0_2_9/wp04_c1_tet4_mesh_diagnosis_raw.npz` and
`qualification/0_2_9/wp04_c1_tet4_mesh_diagnosis.json`.
