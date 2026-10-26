"""Isolated pytest lifecycle checks for the local-VV source provenance hook.

Run directly with the dedicated Python interpreter:
``python tests/synthetic/test_local_vv_provenance_hook_r2.py``.
The subprocesses execute only generated fake tests and fake ``solveur`` packages.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.local_vv.manifest import (
    COMMAND_PROFILE_V2,
    V2_CAMPAIGN_ID,
    V2_CAMPAIGN_IDS,
    V2_CASE_ID,
    V2_COMMAND_TEMPLATE,
    V2_NODEID,
    V2_R2_CAMPAIGN_ID,
    V2_R3_CAMPAIGN_ID,
    V2_RESULT_SCHEMA,
    validate_manifest_shape,
)
from scripts.local_vv.process import _case_command


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)
NODEID = "tests/synthetic_case.py::test_body"
PLUGIN_NAME = "local_vv_pytest_plugin"


class ProvenanceHookLifecycleTests(unittest.TestCase):
    def _run_case(
        self,
        *,
        package: str | None = "valid",
        expected_source: str = "source",
        expected_nodeid: str = NODEID,
        preimport: bool = False,
        preexisting_selection: bytes | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object] | None, Path]:
        temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temp_directory.cleanup)
        root = Path(temp_directory.name)
        source_package = root / ("decoy" if package == "wrong_checkout" else expected_source) / "solveur"
        if package is not None:
            source_package.mkdir(parents=True)
            if package == "import_error":
                init = "raise ImportError('synthetic import failure')\n"
            elif package == "path_mutation":
                init = "import sys\nsys.path.append('synthetic-path-mutation')\nVALUE = 1\n"
            else:
                init = "VALUE = 1\n"
            (source_package / "__init__.py").write_text(init, encoding="utf-8")
        tests = root / "checkout"
        (tests / "tests").mkdir(parents=True)
        (tests / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
        selection = root / "selection.json"
        if preexisting_selection is not None:
            selection.write_bytes(preexisting_selection)
        body_marker = root / "body-reached"
        module_marker = root / "module-import-state.json"
        import_line = "import solveur\n" if preimport else ""
        test_source = (
            "import json, sys\n"
            f"{import_line}"
            f"open({str(module_marker)!r}, 'w', encoding='utf-8').write(json.dumps("
            "{'solveur_loaded': 'solveur' in sys.modules}))\n"
            "def test_body():\n"
            f"    open({str(body_marker)!r}, 'w', encoding='utf-8').write('reached')\n"
        )
        (tests / "tests" / "synthetic_case.py").write_text(test_source, encoding="utf-8")
        if package is None:
            source_package.mkdir(parents=True)
            (source_package / "__init__.py").write_text("VALUE = 2\n", encoding="utf-8")
        import_root = source_package.parent
        plugin_root = PROJECT_ROOT / "scripts"
        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": os.pathsep.join((str(import_root), str(plugin_root))),
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "QF_LOCAL_VV_EXPECTED_NODEID": expected_nodeid,
                "QF_LOCAL_VV_EXPECTED_SOURCE_ROOT": str(root / expected_source),
                "QF_LOCAL_VV_SELECTION_PATH": str(selection),
            }
        )
        command = [
            str(PYTHON),
            "-m",
            "pytest",
            "-q",
            "-s",
            "--noconftest",
            "-p",
            "no:cacheprovider",
            "-p",
            PLUGIN_NAME,
            "-c",
            str(tests / "pyproject.toml"),
            "-o",
            "pythonpath=",
            "-o",
            "addopts=",
            NODEID,
        ]
        result = subprocess.run(
            command,
            cwd=tests,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        record = (
            json.loads(selection.read_text(encoding="utf-8"))
            if selection.exists() and preexisting_selection is None
            else None
        )
        self._last_module_marker = module_marker
        self._last_body_marker = body_marker
        self._last_selection_path = selection
        return result, record, root

    def _assert_denied(self, result: subprocess.CompletedProcess[str], body_marker: Path) -> None:
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(body_marker.exists(), "test body ran despite a provenance/selection denial")

    def test_fresh_collection_imports_source_and_records_exact_selection(self) -> None:
        result, record, _root = self._run_case(preimport=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(record)
        assert record is not None
        self.assertEqual(record["collected_nodeids"], [NODEID])
        self.assertEqual(record["source_import"], record["expected_source_import"])
        self.assertTrue(record["source_import_ok"])
        self.assertIsNone(record["import_error"])
        self.assertTrue(record["sys_path_unchanged"])
        module_state = json.loads(self._last_module_marker.read_text(encoding="utf-8"))
        self.assertFalse(module_state["solveur_loaded"], "package was imported before collection-finish hook")
        self.assertTrue(self._last_body_marker.exists())

    def test_wrong_checkout_is_denied_and_source_is_recorded(self) -> None:
        result, record, _root = self._run_case(expected_source="expected", package="wrong_checkout")
        self._assert_denied(result, self._last_body_marker)
        assert record is not None
        self.assertNotEqual(record["source_import"], record["expected_source_import"])
        self.assertFalse(record["source_import_ok"])

    def test_import_error_is_recorded_and_denied(self) -> None:
        result, record, _root = self._run_case(package="import_error")
        self._assert_denied(result, self._last_body_marker)
        assert record is not None
        self.assertIn("ImportError: synthetic import failure", str(record["import_error"]))
        self.assertFalse(record["source_import_ok"])

    def test_sys_path_mutation_during_import_is_denied(self) -> None:
        result, record, _root = self._run_case(package="path_mutation")
        self._assert_denied(result, self._last_body_marker)
        assert record is not None
        self.assertFalse(record["sys_path_unchanged"])
        self.assertFalse(record["source_import_ok"])

    def test_wrong_nodeid_is_denied_after_recording_collection(self) -> None:
        result, record, _root = self._run_case(expected_nodeid="tests/synthetic_case.py::test_other")
        self._assert_denied(result, self._last_body_marker)
        assert record is not None
        self.assertEqual(record["collected_nodeids"], [NODEID])
        self.assertFalse(record["exact_match"])

    def test_existing_selection_bytes_are_preserved_and_body_is_denied(self) -> None:
        original = b"operator-owned selection\x00bytes\n"
        result, record, _root = self._run_case(preexisting_selection=original)
        self._assert_denied(result, self._last_body_marker)
        self.assertIsNone(record)
        self.assertEqual(self._last_selection_path.read_bytes(), original)

    def test_preimported_conforming_source_and_new_selection_are_allowed(self) -> None:
        result, record, _root = self._run_case(preimport=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        assert record is not None
        self.assertTrue(record["source_import_ok"])
        self.assertTrue(record["exact_match"])
        self.assertTrue(self._last_body_marker.exists())

    def test_r2_campaign_uses_the_existing_fixed_v2_argv_profile(self) -> None:
        manifest = {
            "campaign_id": V2_R2_CAMPAIGN_ID,
            "command_template": V2_COMMAND_TEMPLATE,
            "identities": {name: {"path": f"/synthetic/{name}"} for name in ("science", "runner", "tests")},
            "environment": {"python": {"executable": str(PYTHON)}},
        }
        case = {
            "command_profile": COMMAND_PROFILE_V2,
            "case_id": V2_CASE_ID,
            "nodeid": V2_NODEID,
            "test_checkout": "tests",
        }
        with (
            patch(
                "scripts.local_vv.process._checkout_path",
                side_effect=lambda _manifest, key: Path(f"/synthetic/{key}"),
            ),
            patch("scripts.local_vv.process._execution_environment", return_value={}),
        ):
            argv, _cwd, _environment = _case_command(manifest, case, Path("/synthetic/run"))
        self.assertEqual(argv[0], str(PYTHON))
        self.assertIn(V2_NODEID, argv)
        self.assertEqual(argv.count(V2_NODEID), 1)
        self.assertEqual(manifest["campaign_id"], V2_R2_CAMPAIGN_ID)
        self.assertEqual(V2_CAMPAIGN_IDS[0], V2_CAMPAIGN_ID)
        self.assertEqual(V2_CAMPAIGN_IDS[1], V2_R2_CAMPAIGN_ID)
        self.assertEqual(V2_CAMPAIGN_IDS[2], V2_R3_CAMPAIGN_ID)
        self.assertTrue(V2_RESULT_SCHEMA.startswith("qf-wp12-v2-r1-"))

    def test_r3_campaign_uses_the_same_fixed_v2_argv_profile(self) -> None:
        manifest = {
            "campaign_id": V2_R3_CAMPAIGN_ID,
            "command_template": V2_COMMAND_TEMPLATE,
            "identities": {name: {"path": f"/synthetic/{name}"} for name in ("science", "runner", "tests")},
            "environment": {"python": {"executable": str(PYTHON)}},
        }
        case = {
            "command_profile": COMMAND_PROFILE_V2,
            "case_id": V2_CASE_ID,
            "nodeid": V2_NODEID,
            "test_checkout": "tests",
        }
        with (
            patch(
                "scripts.local_vv.process._checkout_path",
                side_effect=lambda _manifest, key: Path(f"/synthetic/{key}"),
            ),
            patch("scripts.local_vv.process._execution_environment", return_value={}),
        ):
            argv, _cwd, _environment = _case_command(manifest, case, Path("/synthetic/run"))
        self.assertEqual(argv[0], str(PYTHON))
        self.assertIn("-s", argv)
        self.assertIn(V2_NODEID, argv)
        self.assertEqual(argv.count(V2_NODEID), 1)
        self.assertEqual(V2_CAMPAIGN_IDS, (V2_CAMPAIGN_ID, V2_R2_CAMPAIGN_ID, V2_R3_CAMPAIGN_ID))

    def test_unlisted_v2_campaign_is_rejected_by_manifest_shape(self) -> None:
        manifest = json.loads(
            (PROJECT_ROOT / "qualification/0_2_12/vv_local/wp12_v2/r3/V2_R3_MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        manifest["campaign_id"] = "WP12-V2-R3-UNAPPROVED-002"
        errors = validate_manifest_shape(manifest)
        self.assertIn("v2 result profile is scoped to its named campaign, case, and exact nodeid", errors)


if __name__ == "__main__":
    forbidden = {"solveur", "numpy", "scipy"}.intersection(sys.modules)
    if forbidden:
        raise SystemExit("synthetic harness unexpectedly imported: " + ", ".join(sorted(forbidden)))
    unittest.main()
