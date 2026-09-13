---
doc_id: DOC-029-028
revision: 0.1
status: controlled-audit
applicable_version: 0.2.9-development
---

# WP04-E — G04-12 TET4/HEX8 cross-family closure

This is an evidence-only cross-family audit. It uses the already approved
TET4 C2R6 M3 and HEX8 H3 records; it does not launch a structural solve or
alter production source, mechanics, thresholds, maturity, or WP04 points.

## Audit identity and governing evidence

- Branch: `0.2.9-unified-nonlinear`
- Audit start SHA: `a4f8937919f5a008abbc15d0d404c47f09816459`
- TET4 execution source SHA: `2c52bf8196a7d47d14ce1784290580160de26590`
- HEX8 WP04-E source checkout SHA: `a4f8937919f5a008abbc15d0d404c47f09816459`
- HEX8 campaign execution SHA: `e01e292a36dc4f2e6bfe1cbe8a64a6b563707edf`

TET4 is taken from
`qualification/0_2_9/c2r6/frozen_threshold_audit.json`, approved for the
C2R6 M3 case (`64x32x32`, 393,216 TET4, 212,355 DOFs). Its campaign and case
records are `qualification/0_2_9/c2r6/campaign_result.json` and
`qualification/0_2_9/c2r6/m3_result.json`.

HEX8 is taken from the approved WP04-D H3 record (`32x16x16`, 8,192 HEX8,
28,611 DOFs). Its contract, audit, campaign and case records are
`qualification/0_2_9/wp04d/hex8_contract.json`,
`qualification/0_2_9/wp04d/g04_11_audit.json`,
`qualification/0_2_9/wp04d/hex8_campaign_result.json` and
`qualification/0_2_9/wp04d/h3_result.json`.

The machine-readable audit, including SHA-256 hashes for these records, is
`qualification/0_2_9/wp04e/g04_12_cross_family_audit.json`.

## Frozen physical-comparability check

Both records use the bounded WP04 problem:

| Definition | TET4 | HEX8 | Result |
| --- | --- | --- | --- |
| Geometry | `L=4.0`, `H=0.5`, `D=0.5` | `L=4.0`, `H=0.5`, `D=0.5` | PASS |
| Material | homogeneous isotropic 3-D StVK, `E=1e6`, `nu=0.30` | same | PASS |
| Boundary condition | all translations fixed on `x=0` | same | PASS |
| Physical load resultant | `[0,-50,0]` | `[0,-50,0]` | PASS |
| Reference first moment | `[12.5,0,-200]` | `[12.5,0,-200]` | PASS |
| Tip displacement | loaded-face average `u_y` at `x=L` | mean `u_y` on `x=L` | PASS |
| Reaction comparison | reaction resultant norm | same sign convention and norm | PASS |
| Strain energy | accepted-state TL-StVK total energy | accepted-state TL-StVK integrated energy | PASS |
| Stress region | `0.40<=X/L<=0.60`, `0.75<=Y/H<=0.90`, `0.25<=Z/D<=0.75` | same | PASS |
| Stress weighting | reference-volume weighted `sigma_xx` | same | PASS |

The family-specific discrete boundary-load representations are disclosed:
the frozen TET4 C2R6 contract uses equal sharing over loaded-face nodes,
whereas the HEX8 WP04-D contract integrates constant traction on Q4 boundary
faces. The governing cross-family physical checks are the frozen resultant
and reference first moment; both match. This representation distinction is
not hidden or silently reinterpreted as identical nodal vectors.

For TET4, the recorded M3 total load and centroid independently give a
reference moment of
`[12.499999999999831, 0.0, -199.99999999999375]`, with norm error
`6.255052878983532e-12` from `[12.5,0,-200]`. HEX8 records the reference
moment directly as `[12.5,0,-200]`.

## Frozen comparison

The exact frozen metric is:

```text
delta(a,b) = abs(a-b) / max(abs(a), abs(b), 1e-12)
```

Reaction is compared using resultant norms. The G04-12 thresholds are
displacement `0.03`, reaction `0.03`, strain energy `0.03` and representative
`sigma_xx` `0.12`.

| Observable | TET4 C2R6 M3 | HEX8 H3 | Delta | Limit | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Tip displacement | `-0.2002482511318092` | `-0.19933380039473436` | `0.004566585385421973` | `0.03` | PASS |
| Reaction resultant norm | `49.99999999999998` | `49.99999999999994` | `7.105427357601005e-16` | `0.03` | PASS |
| Strain energy | `4.999939075668591` | `4.977170539703795` | `0.004553762679948579` | `0.03` | PASS |
| Representative `sigma_xx` | `3068.972048649666` | `2910.498904645881` | `0.05163720669059609` | `0.12` | PASS |

All four deltas are independently recomputed by
`tests/verification/test_wp04_e_cross_family.py` from the governing source
records, rather than copied from a prior cross-family result.

Both fine cases reached accepted load factor `1.0` with 12 accepted load
steps and zero direct fallback. The approved deformation/equilibrium context
is retained, not recomputed here:

- TET4 M3: force equilibrium `2.5505039661180956e-14`, moment equilibrium
  `7.63053276664867e-16`, minimum `det(F)` `0.9909797199809931`, principal
  stretches `[0.9893216428558, 1.0104538037144282]`, maximum
  `||E||_F` `0.01111056564916684`.
- HEX8 H3: force equilibrium `2.7493855285792547e-14`, moment equilibrium
  `3.257786891417962e-15`, minimum `det(F)` `0.9924435183210853`, principal
  stretches `[0.9907111439153957, 1.0092228247131967]`, maximum
  `||E||_F` `0.0095824348944902`.

All recorded values are finite and inside the frozen WP04 deformation
envelope (`det(F)>=0.20`, principal stretches `[0.75,1.30]`, and
`||E||_F<=0.30`).

## Carried limitation

The explicit HEX8 H1 small-load support limitation remains unchanged:
at multiplier `0.001`, displacement error is
`2.5607163831358572e-05` (within `1e-4`), while reaction error is
`2.7738177407149553e-04` (above `1e-4`). It is recorded as
`HEX8_SMALL_LOAD_REACTION_SUPPORT = LIMITATION_CARRIED_TO_WP04_F` and does
not change the approved G04-11 decision or this cross-family delta decision.
The independent WP04-F audit must judge its significance for combined WP04
closure.

## Decision and governance

The physical definitions and provenance checks pass, and all four frozen
cross-family observables pass. Therefore the derived result is:

```text
G04-10 = OWNER_APPROVED_PASS
G04-11 = OWNER_APPROVED_PASS
G04-12 = PASS_PENDING_OWNER_REVIEW
```

This is not final WP04 closure. WP04 remains `0/12` and the validated total
remains `29/100`; neither TET4 nor HEX8 maturity is promoted. The next step
is the independent WP04-F combined G04-01…G04-12 closure audit.
