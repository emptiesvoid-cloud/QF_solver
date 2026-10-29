# VV3D Owner preparation — 2026-10-29

Campaign: WP12-VV3D-ADAPTIVE-20261029-R1.

This directory contains a prospective campaign contract and 20 FEM plus four QPOST case/job manifests. Every manifest is PREPARED_NOT_AUTHORIZED, has execution disabled, and is bound to the campaign contract. The files are preparation records, not Owner decisions or execution permissions.

The 20 FEM records are 12 initial mesh cases and eight closed-catalog adaptive cases. The four QPOST jobs each have a one-job cap; they consume no FEM attempt, but their elapsed time shares the 28,800 second campaign budget. FEM attempts are globally capped at 24 by policy; only 20 FEM case identities are currently cataloged, so the four unused attempt slots are not executable cases. Operations are serial, at most 1,200 seconds and 4,096 MiB sampled RSS each; each FEM case is at most 30,000 selected DDL. These are controller-observed/soft resource limits, not OS-enforced quotas. No retry is implicit.

The contract freezes the exact nodeids, source/controller fingerprints, case and QPOST bindings, criteria-file identities, adaptive-catalog identities, stop/continuation transitions, and an empty-ledger genesis identity. Collect-only receipts must be regenerated after this source checkout is committed because preflight requires a clean worktree and binds the exact final source identity. Prior receipts remain historical.

All scientific thresholds remain proposals until one explicit Owner decision approves the exact campaign contract. No campaign decision, authorized execution manifest, ledger reservation, FEM operation, QPOST operation, assembly, solve, or eigensolve is created by these files.

The scoped .gitattributes -text rule preserves these exact raw bytes across checkouts. See SHA256SUMS.txt for raw SHA-256 values covering these records and their principal mesh/oracle/criteria/catalog inputs. The official controller remains the only execution route; preparation and collect-only do not authorize execution.