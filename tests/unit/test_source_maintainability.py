from pathlib import Path

import pytest

from scripts.audit_source_maintainability import (
    HISTORICAL_LINE_REFERENCES,
    SOURCE_ROOTS,
    audit_source_maintainability,
    main,
)


def _source_tree(root: Path) -> None:
    for relative in SOURCE_ROOTS:
        (root / relative).mkdir(parents=True)


@pytest.mark.parametrize("lines", [699, 700, 701, 1000, 2000, 2001, 3000])
def test_size_is_an_objective_not_a_hard_cap(tmp_path: Path, lines: int) -> None:
    _source_tree(tmp_path)
    (tmp_path / "src/solveur/example.py").write_text("# source\n" * lines, encoding="utf-8")
    report = audit_source_maintainability(tmp_path)
    assert report["errors"] == []
    assert report["oversized_files"] == int(lines > 700)
    assert report["status"] == ("PASS_WITH_MAINTENANCE_DEBT" if lines > 700 else "PASS")
    if lines > 700:
        assert report["findings"][0]["lines"] == lines
        assert report["findings"][0]["excess_lines"] == lines - 700


def test_historical_reference_is_not_an_exception_or_a_limit(tmp_path: Path) -> None:
    _source_tree(tmp_path)
    relative, reference = next(iter(HISTORICAL_LINE_REFERENCES.items()))
    (tmp_path / relative).write_text("# source\n" * (reference + 1), encoding="utf-8")
    report = audit_source_maintainability(tmp_path)
    assert report["status"] == "PASS_WITH_MAINTENANCE_DEBT"
    row = report["findings"][0]
    assert row["historical_reference_lines"] == reference
    assert row["growth_from_historical_reference"] == 1


def test_inventory_is_deterministic_and_does_not_write_reports(tmp_path: Path) -> None:
    _source_tree(tmp_path)
    for name, count in (("z.py", 701), ("a.py", 900), ("b.py", 900)):
        (tmp_path / "tests" / name).write_text("# source\n" * count, encoding="utf-8")
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    first = audit_source_maintainability(tmp_path)
    assert first == audit_source_maintainability(tmp_path)
    assert [row["path"] for row in first["findings"]] == ["tests/a.py", "tests/b.py", "tests/z.py"]
    assert before == sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))


@pytest.mark.parametrize("target", [0, -1, True, 1.5])
def test_invalid_target_is_rejected(tmp_path: Path, target: int) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        audit_source_maintainability(tmp_path, target=target)


def test_missing_roots_still_fail_closed(tmp_path: Path, capsys) -> None:
    report = audit_source_maintainability(tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert len(report["errors"]) == len(SOURCE_ROOTS)
    assert main(["--root", str(tmp_path)]) == 1
    assert "FAIL_CLOSED" in capsys.readouterr().out


def test_unreadable_source_is_not_silently_ignored(tmp_path: Path) -> None:
    _source_tree(tmp_path)
    (tmp_path / "src/solveur/bad.py").write_bytes(b"\xff")
    report = audit_source_maintainability(tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert report["errors"] == [{"path": "src/solveur/bad.py", "reason": "UnicodeDecodeError"}]


def test_advisory_cli_success_keeps_debt_visible(tmp_path: Path, capsys) -> None:
    _source_tree(tmp_path)
    (tmp_path / "scripts/large.py").write_text("# source\n" * 2500, encoding="utf-8")
    assert main(["--root", str(tmp_path)]) == 0
    assert "MAINTENANCE_DEBT_NON_BLOCKING" in capsys.readouterr().out
