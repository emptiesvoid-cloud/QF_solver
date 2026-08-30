# G08 High-order analytical Euler evidence

Status: **PARTIAL_ANALYTICAL_SCREEN**. Official G08 status remains **PASS_WITH_LIMITATIONS**.

Execution source SHA: `c58fcc7c9a17ed770ecc49bb45d1c965851ed23b`; dirty: `False`.

## Declared benchmark

The benchmark is a homogeneous isotropic fixed-free solid column with a conservative axial nodal dead load distributed over the loaded end face. Euler is used as an independent screening oracle under the declared slender-column assumptions; this is not a general 3D-solid validation oracle.

- `Pcr = pi^2 E I / (4 L^2)`; `E=1e+06`, `nu=0.3`, `L=4`, `b=0.5`, `h=0.5`, `I=0.00520833333333`.
- Euler reference: `803.190462328`; declared error tolerance: `10%`.
- Fixed-free conditions: all translations fixed at `x=0`; axial load distributed over all nodes at `x=L`.
- Mesh refinement changes only the lengthwise partition; one solid layer is retained through each transverse direction.

## Results

| Family | Cells | Elements | QF critical load | Euler error | Eigen residual | Mode norm | Route | Euler screen |
|---|---:|---:|---:|---:|---:|---:|---|---|
| TET10 | 1 | 5 | 21780.007 | 2611.686% | 9.510e-14 | 1 | PASS | FAIL |
| TET10 | 2 | 10 | 124743.12 | 15430.951% | 4.060e-14 | 1 | PASS | FAIL |
| TET10 | 3 | 15 | 499857.9 | 62134.044% | 9.099e-15 | 1 | PASS | FAIL |
| HEX8 | 1 | 1 | 5999.2201 | 646.924% | 5.300e-14 | 1 | PASS | FAIL |
| HEX8 | 2 | 2 | 21495.048 | 2576.208% | 6.106e-14 | 1 | PASS | FAIL |
| HEX8 | 3 | 3 | 65648.269 | 8073.437% | 4.249e-14 | 1 | PASS | FAIL |
| HEX20 | 1 | 1 | 20647.786 | 2470.721% | 1.380e-13 | 1 | PASS | FAIL |
| HEX20 | 2 | 2 | 212786.39 | 26392.644% | 9.157e-14 | 1 | PASS | FAIL |
| HEX20 | 3 | 3 | 1662126.9 | 206840.569% | 9.421e-16 | 1 | PASS | FAIL |

![QF versus Euler](euler_high_order_comparison.png)

![Euler error](euler_high_order_error.png)

## Interpretation

The Euler screen is evaluated independently for each family and level. A failed Euler screen is retained as a diagnostic result and is not repaired by changing the solver, eigensolver, mesh policy or tolerance. Mode norms and residuals are route checks; they do not establish physical mode-shape agreement by themselves.

No family is promoted automatically by this study. The result must be read together with the existing G08 mesh, external-correlation and first-mode evidence.
