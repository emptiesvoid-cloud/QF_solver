# WP12-A P0 prospective oracle descriptions

The two `-r2.json` case manifests clarify the assertions in the unchanged
scientific source at HEAD `7406e34efc28ed8f18c15440115595dfa3dd9ca5`.
The earlier proposed manifests and batch proposal remain available unchanged.

| Case | Correction | R2 raw SHA-256 |
| --- | --- | --- |
| Coupled modal | The eigenvalue reference is SciPy `eigh`; eigenvectors are checked through orthogonality, projected operators and reconstruction. The test does not assert a closed-form eigenvector reference. | `578a11406166fc72467f66c1b8c49b4a01524c3a41aa21c0de1e11daa0e46299` |
| Direct transient | The test compares initial and final energies with analytical initial strain energy, and checks energy drift and residual. It does not compare the displacement history with a closed-form motion. | `fd7609b421cb33e9d8932b53ad573aef052d6cfbcefa8e721bd36881cf320a1b` |

The nodeids, source identity and fingerprints, acceptance text, source-module
hashes, selected degrees of freedom, timeout, attempt limit and stop rules are
unchanged. These case manifests do not authorize execution. A runtime batch
contract must bind the R2 files and all six exact case-manifest hashes before
an Owner execution decision.
