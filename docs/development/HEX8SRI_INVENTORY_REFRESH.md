# HEX8-SRI source inventory comparison

Historical science HEAD `8b61f5d37b9557e6d04cbcf8d787b4208af49486`, fingerprint `c93d539d6b67417f067a190066629d41f84c1a04f61a86b50034c3cfda917d04` (516 files).
Current science HEAD `f6402edc84af71d4d4be5b091b0ed323c1631529`, fingerprint `eb58f1ad1314debdc08f34f312eae17961fc4ebfaae8510632258b5eb51305a9` (517 files).

The historical inventory is validated against the pinned historical sidecar and its aggregate digest. Current raw bytes are checked against the pinned 517-file inventory.

| File | Historical SHA-256 | Current SHA-256 |
|---|---|---|
| `experiments/hex8_sri_equilibrium/convergence.py` | 4f05b1203956381b6729f768b3d30919e85642ce7be34a2c46a90ce821d0cf3e | 3558aa7e22cb8cd7e412dace910c559cbb52183aa92dc493eba22d3f44c565c3 |
| `experiments/hex8_sri_equilibrium/criteria_contract.py` | ADDED | ae46a29e23245d416892e88ce49fb46857403b0e67640f460adf9486df0771ee |
| `tests/verification/test_hex8_sri_convergence.py` | 7b8dbd9fe353145275825d0177f254617d505aa098261f30ef13d07f268e36f9 | d9f77834d62bab49e6eae3ab7177bbcb61813b675acb7096f259520af266d371 |

No files were removed. The registered source worktree was read without line-ending conversion. The full current per-file inventory is recorded in [hex8sri-source-byte-inventory-f6402ed.json](hex8sri-source-byte-inventory-f6402ed.json).

The registered case paths contain `{controller_head}`. The runner resolves it to its own clean Git HEAD inside the ignored `.codex/development-runs/hex8sri-manifests/registry-eb58-v3/` directory. Generate a fresh set into the directory named by that HEAD; creation refuses replacement. After merge, generate into the new canonical HEAD directory and renew the collect-only receipts. Older candidate manifests and receipts remain separate and cannot authorize the new controller identity.
