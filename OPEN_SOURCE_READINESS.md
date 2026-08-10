# Open Source Readiness

## Objective

The long-term objective is to publish QF_solver as an inspectable Python FEM
library with a stable public API, reproducible verification evidence and a
community-maintainable development process.

This file is a release gate, not a license. QF_solver uses Apache-2.0 for
source code and CC BY 4.0 for documentation and original examples.

## Publication Gates

- [x] Package name and public CLI are `qf-solver` and `qf-solver`.
- [x] Stable public imports are exposed through `solveur.api`.
- [x] Installation, test and documentation commands are documented.
- [x] CI covers supported Python versions on Windows and Linux.
- [x] Contribution, security, support and conduct documents exist.
- [x] Public issue and pull-request templates separate defects from V&V work.
- [x] External dependencies and optional extras are declared in `pyproject.toml`.
- [x] Public-release audit rejects workstation paths, private-environment
  markers, internal workflow terminology and obsolete branding.
- [x] Release readiness combines the source audit with version, license,
  changelog, clean-worktree and Git-tag gates.
- [x] Archive exclusions protect generated outputs, temporary folders and local
  evidence artifacts.
- [x] A release-archive audit inspects the paths exported by `git archive`;
  the final tag must be checked again with committed attributes.
- [x] A reachable-history path prefilter flags generated, private or working
  evidence paths before a public repository is created.
- [x] Public archives explicitly exclude internal instruction files and
  private runtime metadata in addition to generated results and working V&V
  trees.
- [x] The public-release policy states that archive exclusions are not access
  controls and that private material must never enter public Git history.
- [x] Owner selected Apache-2.0 for source code and CC BY 4.0 for original
  documentation and examples after checking third-party terms.
- [x] Root `LICENSE`, `LICENSE-DOCS`, `NOTICE` and third-party inventory are
  present and referenced by the package and documentation.
- [x] Generated evidence, private paths and large files were audited; the
  12.2 GB working V&V tree remains excluded from the source archive.
- [x] Tracked files and reachable history were audited, then exported into a
  new one-commit public repository with a GitHub `noreply` author identity.
- [x] Public documentation links were checked by the strict MkDocs build and
  the release audit rejects local file URLs and workstation paths.
- [x] The local `v0.2.0-alpha` tag, changelog section and immutable source
  archive are approved; no remote push is authorized by this checkbox.
- [x] The project owner triages issues and security reports under the
  best-effort policy documented in `SUPPORT.md` and `SECURITY.md`.

## License Decision

The owner selected the following split for the alpha release:

- source code: `Apache-2.0`;
- documentation and original examples: `CC BY 4.0`;
- third-party software, publications, meshes and solver outputs: their own
  licenses, recorded in `THIRD_PARTY_LICENSES.md` or next to the artifact.

This choice permits personal, academic and commercial use while preserving
copyright and attribution. It does not grant rights to the QF_solver name or
to third-party materials. It does not provide a warranty, numerical guarantee
or certification.

## Scope Communication

Public releases must retain the maturity labels `stable`,
`stable_after_reinforced_tests`, `experimental` and `research`. They must not
claim certification. Every release note must state that engineering review and
application-specific validation remain the user's responsibility.

## Separation Of Content

The public repository contains only information intended to be public. Private
working material is kept in a separate local or private repository. A public
site is documentation, not an access-control mechanism: content that must be
restricted must not be committed or deployed to it.

## Alpha Baseline - 10 August 2026

- Full Windows suite: `1091 passed`, `17 skipped`, no failure.
- Documentation: `711` generated artifacts and strict MkDocs build, PASS.
- Public-source audit: `992` files, `0` finding.
- Clean source archive: `1102` files, `0` finding.
- Clean public history: one root commit, `0` history finding, GitHub `noreply`
  author identity.
- Release readiness: every gate passes except the local version tag, which is
  created only after this baseline record is committed.
