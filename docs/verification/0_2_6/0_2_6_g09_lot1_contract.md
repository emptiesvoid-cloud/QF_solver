# 026-G09 Lot 1 Contact Contract

## Status

Lot 1 is a controlled qualification increment. It does **not** close
`026-G09`; the official gate remains `NOT_STARTED` until the complete contact
contract is reviewed and all required lots are closed.

## Bounded scope

This lot exercises the existing nonlinear common-driver contribution named
`frictionless_penalty`. Its current contact geometry is a bounded slave-node to
triangular-master representation. The cases use a TET4 deformable body and
the nonlinear static route with the common Newton residual and tangent
assembly. The study covers signed gap, opening/closure/recontact, controlled
penalty sensitivity, finite outputs and a structured excessive-penetration
failure.

The linear exact active-set route is historical context only and is not mixed
with this Lot 1 penalty evidence. Friction, general surface-to-surface contact,
finite-sliding qualification, self-contact, external correlation and broader
element-family qualification remain outside this lot.

## Predeclared policy

Penalty values are `[1e2, 1e3, 1e4, 1e5, 1e6]`. The evidence records the
penetration, signed gap, iterations, relative residual and contact tangent
sparsity for every value. The expected internal trend is non-increasing
penetration as penalty increases. No universal production penalty range or
conditioning cutoff is approved here; that remains an Owner decision.

The controlled failure sets a maximum penetration below the imposed state.
It must produce a structured contact failure and must not be counted as a
converged case. The runner treats the structured failure result as authoritative
for this expected-failure case.

## Case mapping

The machine-readable requirements and case registry are:

- `qualification/0_2_6/g09_requirements.json`
- `qualification/0_2_6/g09_case_registry.json`

`READY` cases are executed by `scripts/run_g09_lot1.py`. The registry keeps
`NOT_SUPPORTED` explicit; it is not converted to a pass.

## Evidence and limitations

The Lot 1 report and manifest record the source SHA, dirty state, runtime,
configuration, predeclared policy and artifact digests. A successful Lot 1
result is internal research evidence only. It does not claim qualification of
finite sliding, general surface contact, friction or contact for other element
families.
