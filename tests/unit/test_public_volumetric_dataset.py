import json
from pathlib import Path

from scripts import public_volumetric_dataset as dataset
from scripts.public_volumetric_dataset import _worktree_dirty_except, _write_qf_case, select_models


def test_selection_round_robins_nonempty_step_files_and_excludes_domains() -> None:
    tree = [
        {"path": "A/one.step", "size": 10, "sha": "a"},
        {"path": "A/empty.step", "size": 0, "sha": "b"},
        {"path": "B/two.stp", "size": 20, "sha": "c"},
        {"path": "C/engine.step", "size": 30, "sha": "d"},
        {"path": "D/three.txt", "size": 30, "sha": "e"},
    ]

    selected, rejected = select_models(tree, limit=2)

    assert [row["path"] for row in selected] == ["A/one.step", "B/two.stp"]
    assert {row["path"] for row in rejected} == {"A/empty.step", "C/engine.step"}


def test_qf_case_generation_distributes_load_and_constrains_extremes(tmp_path: Path) -> None:
    case_path = tmp_path / "case.json"
    nodes = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]

    _write_qf_case(nodes, [[0, 1, 2, 3]], case_path)
    payload = json.loads(case_path.read_text(encoding="utf-8"))

    assert payload["analysis"] == {"type": "linear_static", "method": "direct"}
    assert payload["elements"] == [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}]
    assert {item["node"] for item in payload["fixed_dofs"]} == {0, 1, 2, 3}
    assert sum(item["value"] for item in payload["loads"]) == 1000.0


def test_qf_case_generation_rejects_mesh_without_x_extremes(tmp_path: Path) -> None:
    case_path = tmp_path / "case.json"

    try:
        _write_qf_case([(0.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [], case_path)
    except ValueError as exc:
        assert str(exc) == "volume mesh has no distinct x-extreme nodes"
    else:
        raise AssertionError("Expected an unusable one-node mesh to be rejected")


def test_manifest_dirty_check_ignores_its_own_output(monkeypatch) -> None:
    manifest = dataset.ROOT / "qualification" / "0_2_6" / "public_volumetric_dataset_manifest.json"
    responses = {
        ("diff", "--name-only"): "qualification/0_2_6/public_volumetric_dataset_manifest.json",
        ("diff", "--cached", "--name-only"): "",
        ("ls-files", "--others", "--exclude-standard"): "",
    }
    monkeypatch.setattr(dataset, "_git", lambda *arguments: responses[arguments])

    assert _worktree_dirty_except(manifest) is False

    responses[("diff", "--name-only")] = "scripts/public_volumetric_dataset.py"
    assert _worktree_dirty_except(manifest) is True
