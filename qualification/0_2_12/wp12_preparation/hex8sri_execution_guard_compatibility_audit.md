# HEX8-SRI execution-guard compatibility review

This is development work on the scientific guard. It authorizes no FEM run,
does not change the physical model or frozen criteria, and does not replace
the historical criteria-freeze record.

The registered controller emits an empty branch string for a detached HEAD.
The previous guard treated every empty value as missing; the revised guard
requires the branch environment variable to exist and match the recorded
string, then independently checks the controller worktree's Git root, actual
branch, HEAD, tree, cleanliness and runner/policy/plugin hashes. The empty
string therefore succeeds only when Git confirms a detached controller.

The official controller archives execution decisions under
`authorizations/<scope>/owner-decisions/execution/<decision-id>.json`. The
previous guard expected the decision directly under `owner-decisions`. The
new guard anchors the execution manifest, execution decision, criteria-freeze
record and preflight receipt to the controller's recorded run store and exact
scope, checks resolved-path containment, IDs and SHA-256 values, verifies the
execution decision type, time interval and manifest bindings, and independently
reads the separately archived freeze. A freeze-only decision cannot authorize
execution. The preflight checksum sidecar and science identity are also checked.

The pre-existing guard already checked the two execution-manifest aliases,
the science branch/HEAD/tree and raw source fingerprint, the case manifest's
registration digest and frozen criteria, the exact nodeid, collection report,
no-attempt state and solver import origin. The revised guard retains those
checks. It also ties the authorization ID to the manifest filename and the
six allowed nodeids to the decision. Resource limits are compared to the
decision and manifest; enforcement remains the controller's responsibility.
Resolved paths are constrained to their expected roots, but the local
workstation is not a filesystem sandbox and the JSON decision is not a
cryptographic signature.

The dedicated synthetic tests call `_authorized_case` only, for all six
first-mesh nodeids and negative provenance, decision, manifest and receipt
cases. Controller Git responses, source fingerprint and imported solver origin
are synthetic; they demonstrate the guard's contract logic, not a real
controller execution or a scientific result. The existing official controller
still validates the full approval schema and resource envelope independently.
An additional synthetic cross-contract test loads the reviewed merged
controller through `QF_HEX8SRI_CONTROLLER_PATH`, validates a complete
synthetic Owner decision and execution manifest with its official validator,
then passes them through the scientific guard. The test skips if that path is
not supplied; it was run against the reviewed controller for this change.

The older static guard test expected the v1 contract marker even though the
base scientific HEAD already used v2. Its expectation is updated to v2; the
marker and the scientific test's execution order remain unchanged.

Changing the scientific test changes the raw scientific fingerprint. Before a
future execution, the Owner must review and integrate the scientific change,
refresh the controller's source inventory and all 24 registrations and case
manifests, repeat the six preflights, archive a new criteria freeze for the
new identities, and separately approve execution. Historical manifests,
preflights and the old freeze remain historical records and must not be
rewritten or reused as current-identity evidence.
