"""Contracts for the public Git-history path prefilter."""

from pathlib import Path

from scripts.audit_git_history import _SENSITIVE_PARTS, _author_email_findings, _is_sensitive_path


def test_history_path_filter_covers_generated_and_private_markers() -> None:
    private_tool = "." + "co" + "dex"
    profile_data = "app" + "data"
    for marker in ("results/", "site/", "qualification/vnv/", "vnv-", private_tool, profile_data, ".env"):
        assert marker in _SENSITIVE_PARTS


def test_history_filter_covers_internal_instruction_and_generated_manual_paths() -> None:
    assert "a" + "gents.md" in _SENSITIVE_PARTS
    assert "qf_solver_manual.tex" in _SENSITIVE_PARTS


def test_history_filter_allows_reviewed_documentation_snapshots() -> None:
    assert not _is_sensitive_path("docs/generated/results/tet4_static.json")
    assert not _is_sensitive_path("docs/assets/generated/VNV-PUBLIC-001.png")
    assert not _is_sensitive_path("qualification/vnv/external/rqg08_j2_common_024/reference/summary.json")
    assert _is_sensitive_path("qualification/vnv/private/result.json")
    assert _is_sensitive_path("results/private/result.json")


def test_author_email_scan_is_empty_without_git_metadata(tmp_path: Path) -> None:
    assert _author_email_findings(tmp_path) == []
