# WP08-R2 — Legacy and corrected-route compatibility

## Version boundary

R2 separates the existing behavior from the corrected force/state kernel using explicit identifiers:

| Concern | Legacy | Corrected R2 |
|---|---|---|
| Formulation ID | `legacy_corotational_j2/v1` | `corrected_corotational_biot_j2/v1` |
| Default selection | yes when no ID is supplied for existing corotational J2 | never implicit; explicit selection only |
| State semantics | historical transported state and historical force/output semantics | `corotational_j2_state/v2`, fixed material/reference frame |
| Force mapping | historical `P=R T_local` path | exact polar-adjoint Biot-conjugate mapping |
| Tangent | existing legacy finite-difference tangent | unavailable/not production-ready |
| Generic stress output | historical output contract | unavailable pending R3 semantics/aggregation |
| Checkpoint resume | existing legacy behavior | no migration; legacy/unknown corrected state rejected |

The default is still legacy. Old models without a formulation identifier resolve to legacy only. Unknown identifiers fail closed. Setting the corrected identifier in a model is rejected at nonlinear assembly/solver validation because R2 has no compatible validated global tangent. This prevents a corrected force from being combined silently with the legacy tangent.

## State compatibility

Corrected initial states are versioned and tied to a material-parameter hash. The corrected local validator refuses legacy states, unsupported schemas, mismatched material identity, malformed/nonfinite history, and inconsistent accumulated dissipation/hardening energy. It does not reinterpret or rewrite a historical checkpoint. R2 does not add corrected checkpoint serialization or resume, and the element-local material hash is not a substitute for the full physical/operator/execution identities required by the checkpoint contract.

The existing transaction mechanism is exercised for trial, rollback, and commit. No change is made to global checkpoint files, checkpoint migration records, historical results, qualification records, or old serialized data.

## Output compatibility

Corrected point-level diagnostic mappings identify `stress_measure`, `stress_frame`, formulation, semantic version, and availability. However, the public `integration_point_results` route deliberately reports the corrected output contract as unavailable by raising a clear not-ready error; no generic aggregate can mistake the new measure for historical `second_piola_stress`. Full result serialization, principal/von-Mises semantics, and historical result migration remain R3 responsibilities.

## Regression evidence and limitations

Focused tests verify the unchanged legacy default and explicit legacy force/tangent call, plus refusal of corrected global Newton through direct formulation validation, assembly-plan matching/building, and assembly. The targeted affected suite passed 196 tests. The full unit suite had 3,303 passes and 93 skips before the final small guards; it is not represented as an exact-final-tree rerun.

No numerical expectations for historical routes were loosened. The corrected/legacy force difference on a noncoaxial plastic fixture is recorded as an expected semantic difference, not used to alter legacy results. No existing historical status or maturity has been promoted or rewritten.
