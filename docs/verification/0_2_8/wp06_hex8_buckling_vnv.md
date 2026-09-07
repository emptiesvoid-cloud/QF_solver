---
doc_id: DOC-028-WP06-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP06 HEX8 linear-buckling assessment

WP06 audits the sole `NOT_QUALIFIED` source combination,
`COMB-HEX8-linear_buckling`, from the WP01 maturity baseline. The campaign
does not alter the numerical source, the 0.2.7 registry or historical
evidence. Its machine-readable contract and output are
[`the frozen contract`](../../../qualification/0_2_8/wp06_hex8_buckling_contract.json)
and [`the campaign evidence`](../../../qualification/0_2_8/wp06_hex8_buckling_vnv.json).

## Frozen scope and gates

The candidate scope was first linearized tangent-instability factor and first
mode for homogeneous isotropic small-strain HEX8 rectangular columns under a
converged proportional nodal dead-compression preload. It covered two bounded
configurations (cantilever and pinned-pinned lateral), three structured mesh
levels, scale and preload perturbations, and explicit invalid/singular failure
paths. It excluded HEX8R/SRI/B-bar/hourglass formulations, post-buckling,
collapse, multi-mode, plates, mixed meshes and universal buckling claims.

The independent analytical oracle was Euler's column factor with the declared
weak-axis inertia and boundary coefficients. The frozen gates were 10% factor
error, 0.90 mode MAC, 1% final adjacent refinement change, 1e-7 relative
eigen residual, 1e-12 relative `Kg` symmetry, 1e-8 preload residual, 2% scale
and preload relations, and exact equality of the two complete replay digests.
No tolerance was changed after observing results.

## Technical result

The decision is **`NOT_QUALIFIED`**; no public promotion was applied.

The internal preload, `Kg` symmetry/sign and eigen-residual checks passed for
the valid rows, and the first-mode shape comparison passed. These sub-checks
do not close the qualification because the factor oracle and refinement gates
failed in both configurations:

| Configuration | Factors at `(2,2,2)`, `(4,4,4)`, `(6,6,6)` | Final adjacent change | Result |
| --- | --- | ---: | --- |
| Cantilever | 41.939686, 21.519986, 17.864878 | 0.204597 | `FAIL` |
| Pinned-pinned lateral | 112.004242, 49.246181, 28.216482 | 0.745298 | `FAIL` |

The Euler factor-relative-error gate also failed at every declared level. The
invalid-orientation input did not fail explicitly, so the robustness campaign
failed even though scale/preload proportionality passed and the singular
boundary case failed closed.

The current CalculiX C3D8 execution was not available because the Docker
daemon could not be reached. The historical 0.2.6 CalculiX record is retained
as an audited historical artifact only; it is not counted as current WP06
execution evidence. Code_Aster remains `NOT_COMPARABLE` unless an equivalent
solid eigen-buckling modelisation is demonstrated.

Two complete campaign replays were recorded. Their digests differed, so the
determinism gate failed. A separate fine-mesh spot check was numerically stable,
but it does not replace the required complete-campaign replay gate.

## Maturity and next gate

The 46-combination reconciliation remains:

- `32 QUALIFIED_BOUNDED`;
- `13 EXPERIMENTAL`;
- `1 NOT_QUALIFIED`, exactly `COMB-HEX8-linear_buckling`.

`WEDGE6 static` is distinct from this `NOT_QUALIFIED` status and is not
changed by WP06. A future closure attempt must keep the frozen tolerance
contract, close the factor/refinement and invalid-input gaps, obtain a
comparable current independent correlation, and make the full replay
deterministic before a separate Owner gate is requested.

The 0.2.7 evidence and source integrity checks are recorded as unchanged.
