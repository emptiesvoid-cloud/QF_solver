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
- [x] Les liens de documentation Markdown/PDF sont controles par la generation
  d'artefacts et l'audit de release rejette les URL de fichiers locaux et les
  chemins de poste.
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

## Alpha V&V 0.2.1a0 - 22 August 2026

The next alpha is a V&V-process release built on the immutable `0.2.0a0`
baseline. The machine-readable release registry is
`qualification/release_vv_0_2_1.json`, and the local readiness command is:

```powershell
python .\qf_solver.py release-vv --output .\results\release_vv_0_2_1
```

The current preflight reports `FAIL` by design: 28 scopes are `PASS`, while
eight explicitly bounded or research scopes remain outside the stable release
target. The requested 13-case campaign, final Owner decision and clean Git
checkout are also still required. This is intentional: passing numerical
checks and being ready for a release are separate decisions.

## Scope Communication

Public releases must retain the maturity labels `stable`,
`accepted_for_bounded_engineering_use`, `experimental`, `research` and
`out_of_acceptance` where applicable. They must not claim certification. Every
release note must state that engineering review and application-specific
validation remain the user's responsibility.

## Separation Of Content

The public repository contains only information intended to be public. Private
working material is kept in a separate local or private repository. Public
documentation is not an access-control mechanism: content that must be
restricted must not be committed or deployed to it.

## Alpha Baseline - 13 August 2026

- Full Windows suite: `1117` tests collected, `1039 passed`, `78 skipped`,
  no failure.
- Mechanical verification: full MITC4 campaign and TET10 campaign, PASS.
- Documentation: generation Markdown/PDF controlee, PASS.
- Static analysis: Ruff, controlled mypy gate and `compileall`, PASS.
- Public-source audit: `1009` files inspected, `0` finding.
- PyPI distributions: wheel `917988` bytes and source archive `677398`
  bytes; Twine, content policy and isolated wheel smoke test, PASS.
- Public commits use the GitHub `noreply` author identity.
- The committed source archive and release-readiness gates are checked again
  after this baseline record is committed and before publication.
