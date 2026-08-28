---
doc_id: DOC-NL-025-013
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 risk register

Scale: probability (P), severity (S), detectability difficulty (D): 1 low to 5
high. Priority is `P*S*D`; values are planning estimates to review at G00.

| ID | Risk | P/S/D | Detection | Mitigation | Gate |
|---|---|---:|---|---|---|
| R1 | Rigid rotation generates spurious stress | 3/5/2 | objectivity and energy tests | exact kinematic contracts before global cases | G02 |
| R2 | Incorrect geometric tangent appears to converge | 3/5/4 | element/global FD and Newton-rate study | derive residual/tangent together; no tolerance relaxation | G02 |
| R3 | Arc-length follows wrong branch | 3/5/3 | known branch, direction and restart tests | one reviewed algorithm; explicit sign diagnostics | G04 |
| R4 | Contact depends excessively on penalty/enforcement | 4/4/3 | penalty/mesh/load-step sweeps | scale-aware controls; consider AL only with evidence | G05 |
| R5 | Failed Newton contaminates contact state | 3/5/4 | adversarial multi-iteration rollback | common transaction and state digests | G05/G09 |
| R6 | Friction frame update is non-objective | 3/5/4 | rotated-frame/cyclic sliding tests | postpone friction until normal core closes | G07 |
| R7 | Small-strain J2 is coupled inconsistently to finite kinematics | 4/5/4 | measure/work/energy review and external curves | Owner formulation decision before WP6 | G06 |
| R8 | Mono-element coupling passes but meshes are unstable | 4/5/3 | multi-element mesh/load-step studies | mandatory meshed benchmarks and limit recovery | G01/G06 |
| R9 | 0.2.4 small-strain/linear path regresses | 3/5/2 | frozen snapshots and full suite | incremental WPs; common code behind explicit paths | G00/G11 |
| R10 | HEX20 nonlinear cost explodes | 4/3/2 | component profile and scaling study | measure state/integration/copies; bounded scope | G08 |
| R11 | Contact tangent creates severe conditioning | 4/4/3 | condition/solver diagnostics and sensitivity | scaling, backend diagnostics, enforcement review | G05/G08 |
| R12 | Arc-length plus contact is unstable | 4/4/4 | coupled adversarial path | not in MUST pairwise scope; require separate Owner GO | G06/G09 |
| R13 | State deep copies cause memory growth | 4/3/3 | Gauss-point state memory scaling | profile before compact transaction design | G08 |
| R14 | External solvers use non-comparable formulations | 4/4/3 | deck/formulation audit | mark N/A; never hide mismatch in tolerance | G10 |
| R15 | Active-set nonsmoothness is misread as tangent failure | 3/3/4 | separate fixed-active and transition tests | distinguish smooth local rate from transition behavior | G05 |
| R16 | Buckling sign/preload convention yields plausible wrong factors | 3/5/4 | Euler and independent external modes | explicit formula/sign inventory and mode correlation | G03 |
| R17 | Tests never enter plastic/contact/nonlinear regimes | 3/5/3 | assert yield/active/large-rotation indicators | evidence preconditions in every benchmark | G01/G02/G05 |
| R18 | “Validated” is claimed from code correlation | 3/4/2 | documentation vocabulary audit | bounded verification/correlation terminology | G10/G12 |
| R19 | Scope breadth delays a coherent release | 4/4/2 | gate schedule and blocked dependency map | keep friction/high-order/triple coupling optional | all |
| R20 | Generated evidence points to stale SHA | 3/5/2 | digest/SHA consistency checker | regenerate only after candidate freeze | G12 |

## Highest-priority controls

R7 requires an Owner decision before any coupled J2/finite-kinematics code. R2,
R5 and R16 require adversarial/derivative evidence before global demonstration
plots are accepted. R19 is controlled by refusing to promote SHOULD/COULD work
without an explicit scope revision.
