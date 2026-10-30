# WP12-Q Owner policy decision record

**Decision scope:** adopt the principle of `QUALIFICATION_LOCAL_VV` for QF Solver v0.2.12.<br>
**Status:** `POLICY_PRINCIPLE_ADOPTED; CASE_EXECUTION_NOT_AUTHORIZED`<br>
**Numerical execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`<br>
**WP12:** `OPEN`

This record captures the Owner's explicit instruction in the WP12-Q request. It does not invent a signature, an Owner identity, a timestamp, or a cryptographic approval object.

## Adopted

- Ordinary local scientific verification on the Owner's Windows workstation is an accepted policy route when scoped to a frozen case and later separately approved.
- A dedicated Python environment, exact nodeids, fixed inputs, declared references, pre-run criteria, controlled numerical thread variables, unique outputs and preservation of errors are appropriate requirements.
- Local V&V is non-attested and is not a security sandbox, certificate, release gate or maturity promotion.
- Ed25519, SYSTEM broker, HKLM trust store, dedicated Windows runner account, VM, Docker, exact Windows build and cryptographic process attestation are not general preconditions for this local route.
- `AGENTS.md` may define this separate route while retaining `DEVELOPMENT_AUTONOMOUS`, `QUALIFICATION_RELEASE` and all WP12-A/B/C requirements unchanged.
- Prepare Q1–Q4, a separate independent 2-DOF oracle test, STAT-BEAM-001 and FEM-TET4-H-001 without running them.

## Not adopted or authorized by this decision

- No scientific test, benchmark, FEM solve, pytest invocation or campaign is authorized by the policy decision.
- No case-specific execution decision, attempt, result, numerical PASS, qualification, public claim, maturity change or WP12 closure is granted.
- No historical Owner decision is modified. WP11 remains `CLOSED` on its API/integration scope; WP12 and WP13 remain `OPEN`.
- No result is permitted to overwrite another attempt or a historical archive.

## Per-case decision required later

The future Owner decision must bind the final manifest SHA-256 and the precise selected case, test/source hashes, science and runner Git identities, Python/environment/import, thread variables, command/cwd, output path, attempt count, budgets, oracle and criteria. The structured decision JSON schema is a data contract only. The local runner checks its fields and bindings but cannot authenticate the author; Owner review must occur separately and be explicit.

The prior WP12-P [Owner plan decision](../vv_master_plan/OWNER_PLAN_DECISION.md) remains a historical snapshot with its original scope and status.
