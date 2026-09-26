# M4 slip forensic R2 — result

## Verdict

`DIAGNOSTIC_CAPTURED_NUMERICAL_FAILURE` — the frozen M4 slip case reproduced
its step-7 failure. The added runner captured the full nested error evidence.
This is not a formal WP08 qualification and awards no points.

## Frozen execution

- Branch: `codex/wp08-area-contact-r1-10-candidate`
- Execution/source SHA: `50b3d35809b49457a5c7cebac017d63daf17b06e`
- Runner SHA-256: `ba8ba38292027d4d7a21c2c04a1984b84947bdc693d74cb5d5ca4e6ef14569bc`
- Contract SHA-256: `190910ae3d9c8ca8afdd1e4742a97b57984fd54e9bac5a79db45bc4ddb533583`
- Canonical execution-binding SHA-256: `583bf26a4cebaf8ffcdb0b5a2f141c5a72c32f6240e134c7d6df3289bdcd87be`
- Execution-binding file SHA-256: `f176fc4a8530004a0efe81dca20a164abe6ae7cf741394df91ca464c6380a1ee`
- One fresh `M4/slip_target` process; PID `31436`; exit code `1`; elapsed `68.569 s`.
- The previous M4 failure and parent M1/M2/M3 evidence were hash-verified and reused read-only.
- No M1/M2/M3, stick, reference, or replay was run. No production source, threshold,
  mesh, load, material, friction/stiffness input, iteration limit, or fallback changed.
- No process remains active.

## Numerical evidence

The slip solve failed at step 7 after six accepted steps. The attempted step was
rejected and rolled back.

| Route | Captured result | Meaning |
|---|---|---|
| Direct normal/friction active set | `ACTIVE_SET_MAX_ITERATIONS`, 25-iteration limit; 10 visited sets; 81 contacts, 80 classified slip and 1 stick at failure | The outer set iteration did not reach its fixed point. |
| Active-slip root | 45 closed slip contacts / 90 unknowns; maximum scaled per-contact residual `1.051909715e-8` vs frozen `1e-9`; physical residual norm `1.503786832e-7` | 37 of 45 contact residuals exceeded the gate. Worst was contact 65: residual `5.495876941e-8 N`, friction limit `5.224666015 N`. |
| Least-squares globalization | `success=true`, termination by `xtol`, only 3 function evaluations | Optimizer termination is not proof that the physical contact residual passed; the solver correctly rejected it. |
| Semismooth refinement | Line search could not reduce residual; 0 successful evaluations, 28 remaining iterations | No accepted correction was found from that seed. |
| Coupled projection | Deterministic 45-contact seed also rejected; 81 operators exceed the frozen exhaustive-search cap of 8 | The fail-closed combinatorial guard worked as designed; its cap was not raised. |

## Cause assessment

Established: this is a repeatable **solver robustness** failure, not an
infrastructure failure or a missing execution. The normal set cycles/exhausts
its allowance; the nonlinear slip root remains about 10.5 times above the
per-contact acceptance tolerance; and the coupled fallback safely stops at its
frozen enumeration guard.

The data narrows, but does not isolate, why the root stalls. Early `xtol`
termination is visible; whether it is dominant over Jacobian conditioning,
inner linear-solve accuracy, or nonsmooth active-set interaction is not proven.
Therefore this report does not claim a confirmed single-line mechanical bug.

## Recommended next action

Keep the physical `1e-9` residual gate and the enumeration cap unchanged. In a
new source revision, separate optimizer step/cost stopping tolerances from the
physical acceptance gate, add optimizer optimality/cost/gradient diagnostics,
and add focused regressions. Any next M4 attempt requires a new prospective
contract and binding; this one-attempt contract is spent. M1/M2/M3 results and
the historical M4 failure remain unchanged.

Full machine-readable evidence and artifact hashes are in
[`forensic_review.json`](forensic_review.json). The complete exception and raw
telemetry are retained beside this report.
