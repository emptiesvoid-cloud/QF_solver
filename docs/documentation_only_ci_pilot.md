# Documentation only CI pilot

This branch proposes an informational diagnostic for a narrow pilot: changes to
README.md and CITATION_REPORTS.bib. It fetches candidate Git objects but executes
only the classifier from the trusted base commit. It rejects changes to other
paths, deletes, renames, executable files, symlinks, binary content, oversized
files, outdated bases and whitespace errors. It runs no FEM analysis.

The diagnostic does not alter the existing workflows, the signed identity gate,
the required status checks or Owner decisions. The output is not scientific
validation or a merge approval. The diagnostic is not yet deployed.

GitHub states that checks from pull_request_target cannot satisfy a required
ruleset status check. Therefore this pilot alone cannot unblock PR 133. Before
any required check is changed, a separately reviewed trusted status mechanism
must bind the classification and the checks to the exact PR head and base. A
workflow from the candidate PR must not be able to attest its own trust. The
existing checks remain required until that mechanism and any ruleset change are
reviewed and authorized by the Owner.

References:
https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target
https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks
