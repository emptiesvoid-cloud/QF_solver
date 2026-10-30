# WP12-B HEX20 R2-CORE controller contract

R2 is a prospective development scope. Its only node is `tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual`; it is not authorized by registration. The scientific checkout is `research/wp12b-hex20-r2-prospective` at `9b998f42c1543f9d40b2f7a7ef88fd59153a65ee`, raw inventory fingerprint `8e6ac46ba6bc7ff3429c87077d795121a1d305f99b0006f80ab958b6ce90ca84`.

R2 carries a distinct mandate, evidence root, and one-attempt ledger. Before collection, manifest preparation and reservation, the runner checks the immutable R1 ledger at SHA-256 `ab5a8e4967ca204898f2eeec52b50f0c6b8e603d0328c3dff06926ff10669f53`. Reservation repeats the check under the ledger lock, verifies the ledger snapshot and refuses a second attempt. The prior attempt does not consume R2's separate prospective allowance. Both limits are procedural, not an OS sandbox.

The runner requires a checksummed, exact-node, skip-free collect-only preflight. It validates captured logs and attestation, source and controller provenance, the unchanged R1 and R2 ledgers, and the exact budgets. A prepared manifest remains PREPARED_NOT_AUTHORIZED; the later Owner decision must approve the final manifest and the proposed scientific criteria, including the R2 nodal load gate, before execution. An approved manifest binds the preflight, exact target, source, controller, 60 DOF and resources. Python output and sidecar provenance are reported separately. The scientific sidecar is written before assertions.

The maximum prospective envelope is one attempt, 300 s, monitored RSS 4096 MiB, 256 MiB archive, subject to the Owner decision. RSS is sampled, not a hard OS limit. An approved scope is not a qualification or release decision.

After review and authorized integration, designate a clean controller checkout by a reviewed canonical AGENTS.md change; existing launchers and manifests are not transferable. Only then issue the official collect-only preflight and prepared manifest. Present its complete hash and the exact R2 criteria for the separate Owner execution decision. No reservation or scientific execution is authorized by this document. Preserve the R1 ledger and all its evidence.

R2-EXTENDED remains separate, including additional face, pressure, local traction and distortion coverage. No previously designated MUST is waived by this contract; its disposition requires Owner review.

## Blocking criteria proposed for Owner approval

The prepared manifest binds these values and the exact source fingerprint. The existing R4 checks remain unchanged: displacement `rtol=1e-10`, `atol=1e-13 m`; stress `rtol=1e-10`, `atol=1e-4 Pa`; internal energy and final external work absolute error at most `1e-10 * exact_energy_J`; free residual `<=1e-10`; force and moment balance `<=1e-12`; energy identity `<=1e-10`. The R2 face nodal comparison is proposed as `rtol=1e-12`, `atol=1e-6 N` for each of the five loaded faces. Finiteness, 60 DOF, fixed indices, mesh and solve success are also asserted. These are proposed execution criteria, not an Owner approval or an achieved result. The diagnostic backward-error target remains observational.
