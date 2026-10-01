---
doc_id: DOC-029-WP16-EXTERNAL-ARCHIVE-001
revision: "0.1"
status: controlled_evidence
applicable_version: "0.2.9"
reviewer: ""
approver: ""
---

# 0.2.9 WP16 — off-Git evidence archive, first verified tranche

WP16 has zero qualification points. On 2026-09-29 the Owner advanced this
operational archive ahead of the next WP14 review/integration. This is **not**
the unrelated 0.2.7 WP16 million-DOF qualification. No solver run, gate
threshold, historical verdict, ledger entry, or package version was changed.

The only remote destination used was the
[Owner-designated Google Drive folder](https://drive.google.com/drive/folders/1Aye0b1kcfK4Vm2gc01OaiIbZL9XdgHel).
The machine-readable catalog at
`qualification/0_2_9/wp16_external_archive/drive_catalog_2026_09_29.json`
contains exact file IDs, SHA-256 digests, byte counts, source/contract lineage,
and the per-file manifests. The original local files remain untouched.

| Selected evidence lot | Files | Source bytes | Remote bytes | Read-back and full restore |
|---|---:|---:|---:|---|
| WP07-D R2–R2.4 historical runs | 293 | 17,198,829,455 | 914,863,559 in fourteen parts | Verified on E:; mixed historical verdicts not reclassified |
| WP07-D R2.5 | 99 | 3,949,086,874 | 222,039,833 in four parts | Verified |
| WP08-D R2 | 131 | 98,005,150 | 5,000,902 | Verified; original HOLD/FAIL_CLOSED preserved |
| WP08 area-supported R1.10, M1–M3/M4 evidence | 73 | 382,579,508 | 19,580,256 | Verified; no new qualification claim |
| WP08-D R1 historical requalification | 251 | 195,997,323 | 10,011,168 | Verified; historical status unchanged |
| WP09 Hex20 evidence | 30 | 159,722,418 | 14,916,935 | Verified; historical status unchanged |
| WP09 Tet10 R2 study | 14 | 165,516,367 | 15,112,377 | Verified; historical status unchanged |
| WP09 Tet4 R1/R2 studies | 26 | 35,358,736 | 2,676,632 | Verified; historical status unchanged |
| WP04-D reproduced NPZ and records | 31 | 8,724,153 | 7,886,032 | Verified; four reproduced NPZ match recorded historical sizes/hashes, **not recovered original provenance** |
| WP12 R3.x diagnostics, twelve selected roots | 8,890 | 53,491,469 | 26,046,944 | Verified; mixed historical verdicts not reclassified |
| WP12 R4 gallery | 14,692 | 243,014,078 | 141,280,982 in three parts | Verified |
| WP13 R2 | 18 | 99,611,184 | 8,353,651 | Verified against all 18 older file hashes |

This is a selected archive of **12 bundles**, totaling 24,548 files and
22,589,936,715 uncompressed source bytes. It is not a claim that every
historical run or local worktree has been inventoried. The exact Drive object
IDs and hashes are in the catalog. The compact per-file manifests retain the
builder's `LOCAL_ARCHIVE_VERIFIED_PENDING_REMOTE` state from archive creation;
the later upload, download, hash comparison, and restore are recorded in the
catalog's `readback` fields, and the uploaded manifests were not rewritten.

Separately, the recorded WP09 V1 tarball was absent at its historical local
path and absent from this designated Drive folder. Its ten named directories
still contain **32 Git-tracked files, 51,308,333 source bytes**, and no
additional ignored raw files in this checkout. A new, explicitly labelled
**surviving-files reconstruction** was created from those directories:
[ZIP](https://drive.google.com/file/d/1aiMbw08Ys2EWE2NJ_a8DqVCStLT3kZ95/view)
and [manifest](https://drive.google.com/file/d/1RJX2y0FCq4wu9Oyot2QaG0U5JvsgRGgm/view).
The ZIP is 3,926,535 bytes with SHA-256
`6796c3283d3fc058b64089c0e992721988361d7004716c3fe133ce086bb6198a`;
the manifest is 6,768 bytes with SHA-256
`b0b7f69ac018a91629990ad3e9bfb1e380446620ea3b3608cb320bdb528f12c9`.
Both remote files were downloaded and byte-checked, every ZIP member verified,
and the complete bundle restored to a new directory. This **is not the
historical V1 tarball**, does not reproduce its recorded SHA-256, and cannot
prove whether that tarball contained additional untracked raw files. Its
historical record remains unchanged. The reconstruction is supplementary to,
not a thirteenth member of, the twelve raw-evidence bundles above.

The previously uploaded [WP14 recovered source archive](https://drive.google.com/file/d/1ly_pVCeeyW7MfsHxgBKjL3DM0UeHawv9/view)
was also downloaded, matched its frozen SHA-256 and restored seven files with
the existing hash-pinned preparation script. An older CI copy from run
`36480728483` was separately hash-checked; it is not the current CI run.

The six artifacts from the newer WP14 CI run `36552758385`, source SHA
`d4decf99ab5bfe96a54f17835b35e6eb8c5c49cc`, were copied into the same
Drive folder and downloaded again. All six downloaded byte counts and SHA-256
digests matched GitHub's artifact records: the recovered-evidence ZIP, the
documentation ZIP, and four coverage ZIPs (Windows/Ubuntu × Python 3.10/3.13).
The recovered-evidence ZIP has exactly seven members, all matching the frozen
WP14 file hashes; the documentation ZIP contains `docs_manifest.json` and
`review_readiness.json`, while each coverage ZIP contains `coverage.json`,
`coverage-p0.json`, and `coverage.xml`. The recovered-evidence GitHub artifact
was scheduled to expire on 2026-10-02; this verified Drive copy is distinct
from the older one. This is not a claim that every CI log or every future
WP14 artifact is preserved.

## Storage and restoration boundary

The raw ZIPs and their parts are not in Git, the wheel, or the sdist. Git holds
only this record, the source-level integrity manifests, and the operator-only
`scripts/wp16_external_archive.py`. Ordinary `pip install` and ordinary tests
perform no Google Drive access or evidence download. Access is explicit and
on demand. The Drive connector refused an archive over 100 MiB, so the two
larger ZIPs were split into parts below that limit. Each part, its index, the
reassembled ZIP, and every uncompressed file was hash-checked; the remote
bytes were then fully restored in a separate temporary directory.
The 17.20-GB historical WP07-D lot was restored on E: rather than the nearly
full C: volume. Its source checkout HEAD records the surviving copy's
location, not one execution SHA for all five generations.

For a later restore, download the manifest and ZIP (or all numbered parts and
the parts index) from the file IDs in the catalog into a new local directory.
For a direct ZIP, run `python scripts/wp16_external_archive.py verify
--archive <downloaded.zip> --manifest <manifest.json>`, then `restore` with a
new `--destination`. For a split ZIP, run `assemble --parts-dir <directory>
--receipt <parts.json> --manifest <manifest.json> --output <new.zip>` first,
then `restore`. These commands reject hash mismatches, missing or extra ZIP
members, unsafe paths, and overwrites. No raw bytes should be removed from
their source worktrees until the full WP16 inventory and storage policy are
accepted.

## Remaining gates

WP16 is **open** after this verified tranche. The historical WP09 V1 tarball
path recorded in Git is absent locally; the original archive must not be
called recovered. The supplementary surviving-files reconstruction above does
not close that historical gap. The named surviving WP07-D, WP08-D, WP09, WP04-D, WP12, and
WP13 donor worktrees have been covered by the selected inventory, but this is
not a universal scan of all disks, worktrees, or historical backups. Remaining
scope must be classified as required, superseded, or unavailable. The WP04-D
NPZ files in the new bundle are reproducible outputs from the historical
execution SHA, not the four missing historical originals. Their four sizes
and SHA-256 digests match the values recorded for those originals; the gap is
original-file provenance, not a lack of hash-equivalent bytes. The separate
[digest-equivalence record](../../../qualification/0_2_9/wp16_external_archive/wp04d_digest_equivalent_reproductions_2026_09_29.json)
lists each mapping without reclassifying the historical result. WP12 R3.x remains
mixed historical diagnostic evidence, not a new qualification. Read-only Drive
metadata showed the folder itself is Owner-only. The current folder has 55
direct files: a prior check found 40 of the 41 pre-existing files Owner-only,
and the fresh check found all 14 newly added files Owner-only. The one
exception is the existing
68-KB WP14 source archive: it has an `anyone with the link: reader` permission
because `.github/workflows/quality.yml` currently downloads it with
unauthenticated `curl`. Revoking that permission without first adding an
authenticated CI fetch would break the WP14 checks. The Owner must either
accept this narrowly public file or approve a CI authentication design;
no permission was changed here. Retention, backup redundancy and account-wide
connector permissions remain unattested. Using only this folder does not
technically restrict the connection to that folder. These are storage-
governance limits, not new mechanical FAILs.

WP14 remains `HOLD`, 0/1 point, and the official total remains 95/100. The
selected package-candidate CI evidence is tied to its earlier exact source
SHA; this archive work does not automatically qualify a later commit.

## Owner decision memo — bounded acceptance and provenance gaps

The defensible decision is to **accept the WP16 selected archival tranche
with explicit limitations**, not to close WP16 or WP14. The 12 selected bundles
and the six copied CI ZIPs have remote readback evidence; the supplemental
WP09 reconstruction is also independently verified. These are operational
preservation results, not a new numerical qualification. The historical WP09
V1 tarball remains `UNAVAILABLE_ORIGINAL`; its SHA-256 must not be replaced
with the reconstruction SHA. The four historical WP04-D NPZ paths are still
missing **as original files**. H1 and H1-replay carry the same historical
SHA-256, so there are four paths but three distinct expected contents.
Crucially, the reproduced NPZs already archived under WP04-D match all four
recorded historical sizes and SHA-256 digests. Hash-equivalent bytes are
therefore recoverable from Drive, but the later-run origin cannot be relabelled
as the historical physical files. Recovery from an actual old backup, if one
is found, should compare each size and SHA-256; otherwise use the digest-
equivalent reproductions under an explicit prospective provenance decision.
No historical FAIL is changed by this storage step.

| Decision boundary | Evidence now | Remaining condition |
|---|---|---|
| WP16 selected tranche | 12 bundles, 24,548 files, readback and restore PASS | Owner may accept this bounded preservation result |
| WP09 V1 | 32 surviving tracked files in a new verified ZIP | Original tar and any absent raw members remain unavailable |
| WP04-D historical raw | Four later reproductions match all recorded historical sizes and hashes; three unique contents | Original-file provenance is absent; decide whether the later-run lineage is admissible for a new evidence gate |
| WP14 | Selected package/CI evidence remains source-SHA-bound | Other release gates and Owner governance remain open; HOLD, 0/1 |

## Owner-approved bounded retention policy and backup limits

On 2026-09-29 the Owner accepted the selected preservation tranche and the
rolling retention rule below, with the limitations in the decision record
preserved. The machine-readable decision is
`qualification/0_2_9/wp16_external_archive/owner_bounded_acceptance_2026_09_29.json`.
This is a bounded operational acceptance; it does **not** close WP16, award
qualification points, waive any WP14 gate, or authorize release.

The folder's 55 direct stored files total **1,399,236,630 bytes** (about
1.40 GB decimal or 1.30 GiB) at the 2026-09-29 metadata snapshot. The
22.59 GB figure above is uncompressed source volume, not Drive occupancy.
This measurement covers only this folder; it does not establish the Google
account quota or usage by Gmail, Photos, other Drive folders, Trash, or file
revisions. If the Owner's 50-GB quota estimate is accurate, this folder alone
uses about 2.8% of it. Confirm actual account-wide free space in Google's
Storage Manager before expanding the inventory.

The accepted rolling rule is: keep the **latest Owner-accepted complete
version** and **one candidate** until the candidate is accepted and restored
from remote bytes. Keep compact manifests, hashes, run IDs, source SHAs,
decisions, and historical failure records in Git. Retain irreplaceable raw
records underlying still-active claims separately, or mark them explicitly
`UNAVAILABLE`; never silently reinterpret a later run as the original.
Only after an accepted replacement and a specific Owner deletion decision
should superseded remote raw be eligible for removal. No automatic deletion or
overwrite is permitted by this rule. Independent backup redundancy remains
unverified and is not represented as satisfied.
An operational capacity review when usage approaches 80% of the **actual**
account quota is a planning trigger, not a numerical or release gate. A temp
directory is staging, not a second backup. Google Drive alone is not an
independent backup of irreplaceable qualification bytes.

## Links, CI retrieval, and private-fetch migration

The [Drive folder](https://drive.google.com/drive/folders/1Aye0b1kcfK4Vm2gc01OaiIbZL9XdgHel)
is the browsing entry point; the catalog's file IDs and SHA-256 values are the
machine identity. A browser `.../file/d/<id>/view` link is not a stable
anonymous download contract: access depends on each file's permissions.
The existing 68-KB WP14 source ZIP is the sole known `anyone-with-link`
exception, because the current `quality.yml` fetches it by unauthenticated
`curl` and then checks its frozen hash. Revoking that ACL now would break
the CI job. The rest of the folder must not be made public for convenience.

The [GitHub CI run 36552758385](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/36552758385)
is marked **Success** at source SHA `d4decf99ab5bfe96a54f17835b35e6eb8c5c49cc`
and has six catalogued artifacts. In the GitHub UI: open the run, find
**Artifacts**, and select `wp14-r23-recovered-evidence`,
`fem-documentation-evidence`, or a `coverage-...` artifact. With `gh` and
repository read access, for example:

```powershell
gh run download 36552758385 --repo emptiesvoid-cloud/QF_solver --name wp14-r23-recovered-evidence --dir .\wp14-ci-download
```

The browser-downloaded ZIP should be checked against the catalog's ZIP
SHA-256 and its contained files, not accepted merely because its filename
matches. `gh run download` extracts the artifact; in that case verify the
extracted file hashes or download the ZIP through the GitHub UI to compare
the outer ZIP digest. GitHub CLI is not installed in the current local shell,
so the command above is an Owner-side option rather than a locally executed
check. See [GitHub's download instructions](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)
and the [GitHub CLI command reference](https://cli.github.com/manual/gh_run_download).
The WP14 recovered-evidence GitHub artifact is scheduled to expire on
2026-10-02; the copied [Drive ZIP](https://drive.google.com/file/d/1zrJYA1c8NDUpYEAuZz7SAy_iYw3CnCU6/view)
is the recoverable copy after that date, subject to Owner account access.
The run is bound to SHA `d4decf99ab5bfe96a54f17835b35e6eb8c5c49cc`;
it is not evidence for an arbitrary later branch state.

Google's [Storage Manager guidance](https://support.google.com/drive/answer/17196458?hl=fr)
explains why this folder count does not measure the account's total usage.
Google's [Drive sharing documentation](https://developers.google.com/workspace/drive/api/guides/manage-sharing)
explains that a file URL does not itself grant access; the ACL does.

For private future CI fetching, first establish an independent Google
service account with read access only to the designated folder or the exact
needed file, and GitHub-to-Google short-lived workload identity federation
restricted to this repository/workflow. Then use the authenticated Drive API
`files.get?alt=media` by catalogued file ID, verify size/SHA-256, and only
then revoke the WP14 public-link ACL. This is a proposed migration requiring
credential and sharing configuration; it has **not** been deployed or tested.
It also does not narrow the existing interactive Drive connector's OAuth
scope. Ordinary package installation and tests must never invoke this fetch.
Implementation references are Google's [authenticated blob-download guide](https://developers.google.com/workspace/drive/api/guides/manage-downloads)
and the [GitHub-to-Google federation action](https://github.com/google-github-actions/auth/blob/main/README.md).
