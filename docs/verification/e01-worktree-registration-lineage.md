# E01 registered worktree lineage

The E01 registry originally bound the local checkout at
`C:\Users\fari\Documents\projet\SAFRAN\solveur\tmp\qf-v0.2.12-integration`
to `codex/v0.2.12-integration`, with baseline `ae429934edc8a18d3febaf85d9b14b21d548eefe`.
That registration was introduced by `0a2c507441b63515da10944a4ad55e5d1329b4be` on
2026-10-24, before the checkout migration recorded below.

The Git worktree at that path has a direct HEAD reflog entry at
`2026-10-24T11:05:22+02:00`:

```text
checkout: moving from codex/v0.2.12-integration to emptiesvoids-cloud/0.2.12
```

At the migration both refs pointed to `5fc9437a9d6eb8f2101a04d997a88e132c0a8fef`.
The current branch is `emptiesvoids-cloud/0.2.12` at
`2aa994f34900f39bef8df9db5fb025157fb694bb`, five commits ahead of that shared
point. The additional commits are recorded in the worktree history; they include
subsequent D01 and E01 changes. The originally registered baseline remains an
ancestor of the current checkout. This is a stale branch-name registration after
an explicit checkout migration, not evidence that the registered path resolves
to a different repository or that the baseline ancestry was lost.

The minimal registry correction updates only the expected branch name. It keeps
the worktree path, source/test roots, E01 math-only mode, allowed nodeids, budgets,
and original baseline commit unchanged. The E01 source and historical test
fingerprints are not rewritten. Since controller provenance includes the Git
identity and policy SHA-256, prior collect-only receipts must be renewed against
the corrected controller identity before they can authorize any later run.
This correction does not authorize or execute FEM.
