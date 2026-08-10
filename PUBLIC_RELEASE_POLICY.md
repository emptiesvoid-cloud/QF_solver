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

Before creating a tag or source archive, run:

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

The public site documents the solver formulation, interfaces, verified scope,
known limitations and selected reproducible demonstrations. It does not
publish internal working instructions, local execution context, private model
data or machine configuration. URLs created for documentation, packages or
releases must point only to reviewed public content and must be added to the
release checklist before publication.
