from scripts.check_privacy_diff import privacy_findings


def test_privacy_diff_flags_employer_and_real_profile_paths() -> None:
    diff = (
        "+saf" + "ran\n"
        "+C:\\Users\\fari\\Documents\\private.txt\n"
        "+/home/" + "alice/private.txt\n"
    )

    assert len(privacy_findings(diff)) == 3


def test_privacy_diff_allows_generic_user_path_fixtures() -> None:
    diff = "+C:\\Users\\private\\fixture.csv\n+/home/runner/private/model.json\n"

    assert privacy_findings(diff) == []


def test_privacy_diff_redacts_agent_root_matches() -> None:
    sensitive = "E:" + "\\" + "QFSolverAgents" + "\\private\\evidence.json"
    findings = privacy_findings("+" + sensitive + "\n")
    assert len(findings) == 1
    assert sensitive not in findings[0]
    assert "[redacted]" in findings[0]
    assert len(privacy_findings("+" + sensitive.replace("\\", "\\\\") + "\n")) == 1
