# WP12-A P0 tolerance descriptions and runtime versions

Three prospective case-manifest revisions describe tolerances that the
unchanged tests pass explicitly and those inherited from NumPy defaults.
They retain the previous case manifests and change no scientific assertion,
threshold, source identity, registration, resource budget or attempt limit.

| Case manifest revision | Raw SHA-256 |
| --- | --- |
| Coupled modal R3 | `6df1a28f6fc4a528c97d227ea59587099417a908e6d5b6093e86b9915b2fd79d` |
| Degenerate modal R2 | `9b05e92bcb0dedc501cddfdf787e7cb0528c57e287c53e6da7e7ea0c84ab3030` |
| Direct harmonic R2 | `fff77d9578fafc7e9a102d0e650f60e9e4733c1b0cbcad277b64edcf1eb3b8d9` |

With NumPy 2.2.6, the default relative tolerances are `1e-7` for
`numpy.testing.assert_allclose` and `1e-5` for `numpy.isclose`. The P0 batch
contract records NumPy and SciPy distribution versions and refuses a version
change before a case starts and again after its collect-only preflight, before
the controller can reserve that case. This version check is not a hash of the
installed distribution bytes or a guarantee of physical validation.

These prospective files do not authorize a scientific execution. The eventual
Owner decision must bind the newly prepared batch contract and its six exact
case-manifest hashes.
