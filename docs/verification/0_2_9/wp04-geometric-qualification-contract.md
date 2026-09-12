---
doc_id: DOC-029-WP04-001
revision: 0.1
status: prospective-contract
applicable_version: 0.2.9-development
---

# WP04-A — geometric nonlinear qualification contract and baseline

WP04 is a **two-family all-or-nothing** qualification package: TET4 and HEX8
may become `QUALIFIED_BOUNDED` only after every frozen G04 gate, an independent
closure audit and Owner approval. This WP04-A record awards **0/12** and leaves
both current public maturities at `RESEARCH_ONLY`.

## Bounded target

The target covers homogeneous `isotropic_3d` Total-Lagrangian
Saint-Venant-Kirchhoff solids under static nodal dead loads and fixed
displacement boundary conditions, in serial execution. The prospective
envelope is `0 <= nu < 0.45`, positive quality-controlled reference elements,
`det(F) >= 0.20`, principal stretches in `[0.75, 1.30]`, and
`||E||_F <= 0.30`. These are qualification boundaries, not universal
large-strain material claims.

TET10, HEX20, contact, friction, J2+geometry, arc-length/postbuckling,
follower loads, updated/corotational formulations, nonlinear dynamics and
distributed nonlinear execution are expressly excluded.

## Implemented mechanics audit

The audited kernels implement

\[
F=I+\operatorname{Grad}_X u,\quad C=F^T F,\quad
E=\tfrac12(C-I),\quad S=\lambda\operatorname{tr}(E)I+2\mu E,
\quad P=FS.
\]

They assemble \(f_{\rm int}=\int_{V_0}B_P^T P\,dV_0\), the material and
initial-stress geometric tangent terms, and
\(\psi=\frac12\lambda\operatorname{tr}(E)^2+\mu E:E\). Cauchy stress is
\(\sigma=J^{-1}FSF^T\). TET4 uses constant reference gradients and volume
integration; HEX8 uses 2×2×2 Gauss integration. The source map is in
`qualification/0_2_9/wp04_formulation_map.json`.

## Historical debt and corrected future method

The frozen 0.2.8 WP13-11 discovery run passed its tangent, residual, balance,
small-limit, determinant, replay and failure checks, but its energy/work test
reported `1.3963468382007748e-05` against a prospective `1e-07` threshold. It
used a coarse 24-interval trapezoidal work path and did not have a public,
authoritative accepted-state trajectory. That evidence remains unchanged and
does not establish a formulation defect.

WP02/WP03 now expose an authoritative accepted-state callback seam. WP04-B
must record detached snapshots only after global acceptance and compare
\(\Delta U\) against progressively refined dead-load work paths (12/24/48/96).
It must also retain the stronger local identities
\(f_{\rm int}=\partial U/\partial u\) and
\(K_T=\partial f_{\rm int}/\partial u\).

## Frozen gates and baseline

G04-01 through G04-12 are fixed in
`qualification/0_2_9/wp04_gate_matrix.json`; no threshold can be tuned after
WP04-B observations. The targeted current baseline is green: 14 kernel/V&V,
27 geometric-route and 29 path/failure tests. It also records the missing
two-family affine, mesh, cross-family and accepted-path work campaigns.

The next permitted action is **Owner review before WP04-B**. WP05 has not
started.
