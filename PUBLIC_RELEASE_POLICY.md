# Public Release Policy

## Public Scope

A public QF_solver release may contain the solver source, examples, technical
documentation, controlled requirements and reproducible mechanical evidence.
It must not contain personal workstation paths, cached results, temporary
files, private environment metadata or internal working instructions.

The technical documentation remains public. Internal development workflows are
kept out of the public archive. Owner review decisions may identify Quentin
Farinazzo where authorship or accountability is required; they must not include
contact details beyond the public repository profile.

## Release Metadata

The latest published release is QF Solver `0.2.10`, tagged `v0.2.10` and
bound to package source `e535ff63464ddd7d76c2898df25470350b5154f1`. Its version
DOI is [`10.5281/zenodo.23106744`](https://doi.org/10.5281/zenodo.23106744).
The published `0.2.8` version DOI is
[`10.5281/zenodo.22697898`](https://doi.org/10.5281/zenodo.22697898), while
[`10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897) is the
concept DOI for the evolving project. These identifiers do not change any
capability maturity or V&V result. A prepublication candidate must not claim
a version DOI or release date that has not actually been issued.

## Content Classification

The public release may include reviewed, controlled V&V contracts, selected qualification records,
Owner/delivery decisions and evidence manifests when
they are needed to substantiate a public claim. Inclusion requires review of
scope, provenance, licensing and confidentiality. Large raw arrays, temporary
runtime outputs, private models, local environment fingerprints and internal
execution logs remain excluded unless a separate review explicitly selects a
safe, reproducible artifact.

Ephemeral files, caches, debug traces, private or confidential material,
credentials and secrets are never release content. An archive exclusion is not
permission to commit such material, and it is not an access-control mechanism.

## Repository Boundary

A public Git repository exposes every committed file and its reachable history.
`export-ignore` only filters a source archive; it does not make a committed
file private. Therefore private working material, machine-specific data and
internal operating notes must remain outside the public repository from the
start. The ignored working trees are convenience safeguards, not access
controls.

The first public release must be made from a reviewed public repository or a
reviewed clean branch. If the development history ever contained material that
must not be published, create a new public history after a dedicated review;
do not rely on deleting a file in a later commit.

## Release Gate

Before promoting a full repository source archive or GitHub Release, run:

```powershell
python .\scripts\audit_public_release.py --output .\public_release_audit.json
python .\scripts\audit_release_archive.py --ref HEAD --output .\release_archive_audit.json
python .\scripts\audit_git_history.py --output .\git_history_audit.json
python .\scripts\release_readiness.py --output .\release_readiness.json
git archive --format=zip --output qf-solver-source.zip HEAD
```

The source audit must report `PASS` with zero findings. The readiness report
must report `READY`: it additionally checks the chosen license, changelog
version, clean Git worktree and version tag. The archive must be inspected
before upload. `.gitattributes` excludes local outputs and generated runtime
artifacts from `git archive`. The complete `qualification/vnv/` working tree
is also excluded: only selected, reviewed V&V packages may be copied into a
future public release deliberately. These rules are safeguards, not substitutes
for review.

A source tag used solely to identify a separately audited PyPI candidate does
not pass this whole-repository gate by implication. GitHub may still offer an
automatic source archive for the tag; it must not be described or uploaded as
a cleared distribution while this gate fails. The separate PyPI decision and
its frozen selected-content checks are specified below.

`audit_release_archive.py` uses worktree attributes by default to verify the
next prospective archive. Immediately before tagging, run it again with
`--committed-attributes` on the reviewed commit: this confirms that the actual
tagged archive, not only the local working tree, carries the exclusions.

The release owner must also inspect the list of tracked files and the staged
change set before publication:

```powershell
git ls-files
git diff --cached --name-only
git log --all --name-only
```

`audit_git_history.py` is a path-index prefilter for this review. A `WARNING`
requires a deliberate history review or a new clean public history; a `PASS`
does not prove that historical file contents are suitable for publication.

## Prohibited Content

- Absolute home or workstation paths.
- Cached outputs, temporary directories and local runtime fingerprints.
- Credentials, tokens, private email addresses and private customer models.
- References to internal assistance workflows or proprietary project branding.
- Claims that the solver is certified, independently reviewed or validated
  beyond the evidence actually published.

## Public Documentation

The public documentation documents the solver formulation, interfaces,
verified scope, known limitations and selected reproducible demonstrations. It does not
publish internal working instructions, local execution context, private model
data or machine configuration. URLs created for documentation, packages or
releases must point only to reviewed public content and must be added to the
release checklist before publication.

## Prospective Package Selection

The engineering evidence repository and an installable package are distinct
scopes. A preparation plan may select source, examples, package metadata and
specific reviewed qualification records. Every selected file must map to an
exact Git blob, size and SHA-256; required build/data inputs must be covered.
Run `python -m scripts.plan_public_package --contract <preparation-contract>`
to inspect that mapping and apply the existing strict scans to selected bytes.
This command is read-only: it does not stage, build, publish, or update a ledger.

A successful preparation scan does not close the whole-repository release
gates. A separate prospective execution contract must bind the updated source
before staging, building and checking wheel/sdist bytes and installed commands.
The existing package version at the frozen source revision remains
authoritative for that contract. A preparation plan cannot silently change it
or announce a new release; a subsequent candidate needs its own reviewed
version change, new source freeze and new contract.

Unselected engineering records and historical failures remain intact. The
package selection does not make committed Git history private. No history
rewrite, broad gate waiver, tag, upload or Owner score attribution follows
from this plan.

### Candidate build verification

`scripts/verify_public_package.py` executes a separately committed
`FROZEN_CANDIDATE_BUILD` contract, not the preparation plan. The contract binds
an exact source commit, all build/probe/scan tools, the selection and exclusions,
and the unchanged package version. A clean execution checkout and a new external
output directory are required. Existing outputs are never reused or overwritten.

The tool materializes only the selected Git blobs, builds wheel and sdist, scans
both with the existing strict rules, and checks every selected byte against the
archives. It rejects undeclared payloads, missing resources, path aliases,
symlinks, and package-version mismatches. Generated build metadata is explicitly
distinguished from selected source inputs.

Installation uses a separate venv, `--no-index` and `--no-deps`. System and user
dependency sites may be visible; this is not full dependency isolation. Every installed
QF source file must match its bound SHA-256. The three installed CLI launchers are
smoke-tested without solving. Fresh interpreter probes check that installed
`verify-all` is refused with exit code 2, both outside a checkout and with a real
checkout as the current directory. The audit runner requires Python 3.11+ for
`-P` safe-path mode, excluding the script directory and cwd from import search
without hiding the declared dependency sites. Package Python support is not
changed. They record Python subprocess audit events during the CLI checks;
this is not a system-wide OS trace. No verification campaign is authorized.

Each command records its actual argv, working directory, PID, UTC endpoints,
exit code, and hashed stdout/stderr. The manifest binds the binaries, source
mapping, command records, probes and logs. Generated build trees and the venv
are not treated as immutable evidence inputs. Large outputs remain external.

`PASS_CANDIDATE_PACKAGE_ONLY` means that this selected installable package
satisfies its candidate checks. It does not convert the historical whole-repo
publication failures to PASS, certify the full documentation collection,
recover missing historical raw evidence, close WP14, or authorize publication.

### Separate PyPI distribution decision

PyPI wheel and sdist are a bounded publication channel distinct from the
GitHub repository's automatically generated source archives. The Owner may
authorize that channel separately only when the *tagged* source is covered by
a prospectively committed contract, the strict selected-source and served-docs
scan passes, the wheel/sdist content and installed-package probes pass, the
engineering CI passes on that tag, and the package version, README, changelog,
documentation and `CITATION.cff` consistently identify the published version
and its assigned version DOI. The manual `confirm_publish` input and any PyPI
environment approval are the final publication decision; a candidate PASS
alone is not.

The selected package must be built from the contract's exact tagged Git blobs,
not from the rest of the engineering checkout. Publish only those audited
wheel/sdist bytes. A PyPI-only decision never clears a failing whole-repository
source/archive/history audit and never authorizes a GitHub Release, an upload
of the repository archive to Zenodo, or a WP14 status change. Do not move an
existing tag to make corrected metadata appear retroactively in its source.
If the immutable tag's public metadata is inconsistent, prepare a new version
and tag after the corrections and a new frozen audit.
