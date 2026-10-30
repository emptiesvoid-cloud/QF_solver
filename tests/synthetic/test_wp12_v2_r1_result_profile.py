"""Stdlib-only checks for the WP12 V2 R1 local-VV result profile.

Run directly with ``python tests/synthetic/test_wp12_v2_r1_result_profile.py``.
This file does not invoke pytest, numerical code, or child processes.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.local_vv.manifest import (
    COMMAND_PROFILE,
    COMMAND_PROFILE_V2,
    V2_CAMPAIGN_ID,
    V2_COMMAND_TEMPLATE,
    V2_CASE_ID,
    V2_NODEID,
    V2_RESULT_SCHEMA,
)
from scripts.local_vv.process import _case_command, classify_junit, extract_numeric_payload
from scripts.local_vv.results import V2_GAMMA_ASSERTIONS, V2_MANDATORY_ASSERTIONS, classify_v2_result


NODEID = V2_NODEID
TEST_NAME = NODEID.split("::", 1)[1]
CASE_ID = V2_CASE_ID
MARKER = "QF_VV_NUMERIC_RESULT="


def _payload(*, gamma: str = "PASS", pytest: str = "PASS", mandatory: str = "PASS") -> dict[str, object]:
    records = []
    for index, name in enumerate(V2_MANDATORY_ASSERTIONS):
        if mandatory == "FAIL":
            status = "FAIL" if index == 0 else "NOT_REACHED"
        else:
            status = "PASS"
        records.append({"name": name, "status": status, "acceptance_role": "mandatory"})
    if gamma == "INCONCLUSIVE":
        records.extend(
            {
                "name": name,
                "status": "NOT_REACHED",
                "acceptance_role": "gamma_conditional",
                "reason": "rounding assumptions are not verified; diagnostic is not established as an acceptance criterion",
            }
            for name in V2_GAMMA_ASSERTIONS
        )
        evaluated, satisfied = False, None
    else:
        records.extend(
            {
                "name": name,
                "status": (
                    "NOT_REACHED"
                    if mandatory == "FAIL"
                    else "FAIL"
                    if gamma == "FAIL" and index == len(V2_GAMMA_ASSERTIONS) - 1
                    else "PASS"
                ),
                "acceptance_role": "gamma_conditional",
            }
            for index, name in enumerate(V2_GAMMA_ASSERTIONS)
        )
        evaluated, satisfied = True, gamma == "PASS"
    return {
        "schema": V2_RESULT_SCHEMA,
        "case_id": CASE_ID,
        "nodeid": NODEID,
        "rounding_assumptions_verified": gamma != "INCONCLUSIVE",
        "gamma_bound_evaluated": evaluated,
        "gamma_bound_satisfied": satisfied,
        "gamma_scientific_status": gamma,
        "pytest_execution_status": pytest,
        "overall_scientific_status": "FAIL" if mandatory == "FAIL" or gamma == "FAIL" else gamma,
        "assertion_records": records,
    }


class V2ResultProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.process_launcher = patch.object(subprocess, "Popen", side_effect=AssertionError("child launch forbidden"))
        cls.process_mock = cls.process_launcher.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process_mock.assert_not_called()
        cls.process_launcher.stop()

    def test_successful_junit_and_gamma_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            junit = Path(directory) / "junit.xml"
            junit.write_text(f'<testsuite><testcase name="{TEST_NAME}" /></testsuite>', encoding="utf-8")
            pytest_status = classify_junit(junit, NODEID, [NODEID], 0)
        self.assertEqual(pytest_status, "PYTEST_PASS_ONLY")
        result = classify_v2_result("EXPOSED_JSON", _payload(), case_id=CASE_ID, pytest_execution_status="PASS")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["pytest_execution_status"], "PASS")

    def test_successful_junit_does_not_promote_gamma_inconclusive(self) -> None:
        payload = _payload(gamma="INCONCLUSIVE")
        result = classify_v2_result("EXPOSED_JSON", payload, case_id=CASE_ID, pytest_execution_status="PASS")
        self.assertEqual(result["gamma_scientific_status"], "INCONCLUSIVE")
        self.assertEqual(result["status"], "INCONCLUSIVE")

    def test_failed_junit_and_gamma_pass_remain_separate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            junit = Path(directory) / "junit.xml"
            junit.write_text(
                f'<testsuite><testcase name="{TEST_NAME}"><failure /></testcase></testsuite>',
                encoding="utf-8",
            )
            pytest_status = classify_junit(junit, NODEID, [NODEID], 1)
        self.assertEqual(pytest_status, "FAIL")
        result = classify_v2_result(
            "EXPOSED_JSON",
            _payload(pytest="FAIL", mandatory="FAIL"),
            case_id=CASE_ID,
            pytest_execution_status="FAIL",
        )
        self.assertEqual(result["gamma_scientific_status"], "PASS")
        self.assertEqual(result["pytest_execution_status"], "FAIL")
        self.assertEqual(result["status"], "FAIL")
        records = result["assertion_records"]
        self.assertEqual(records[0]["status"], "FAIL")
        self.assertTrue(all(record["status"] == "NOT_REACHED" for record in records[1:]))

    def test_gamma_not_evaluated_cannot_expose_boolean_outcome(self) -> None:
        payload = _payload(gamma="INCONCLUSIVE")
        payload["gamma_bound_evaluated"] = False
        payload["gamma_bound_satisfied"] = True
        result = classify_v2_result("EXPOSED_JSON", payload, case_id=CASE_ID, pytest_execution_status="PASS")
        self.assertEqual(result["status"], "ERROR")

    def test_evaluated_gamma_requires_present_boolean_outcome(self) -> None:
        payload = _payload(gamma="INCONCLUSIVE")
        payload["gamma_bound_evaluated"] = True
        payload["gamma_bound_satisfied"] = None
        result = classify_v2_result("EXPOSED_JSON", payload, case_id=CASE_ID, pytest_execution_status="PASS")
        self.assertEqual(result["status"], "ERROR")

        payload.pop("gamma_bound_satisfied")
        result = classify_v2_result("EXPOSED_JSON", payload, case_id=CASE_ID, pytest_execution_status="PASS")
        self.assertEqual(result["status"], "ERROR")

    def test_payload_nodeid_must_match_exact_profile_node(self) -> None:
        payload = _payload()
        payload["nodeid"] = "tests/unit/test_other.py::test_other"
        result = classify_v2_result("EXPOSED_JSON", payload, case_id=CASE_ID, pytest_execution_status="PASS")
        self.assertEqual(result["status"], "ERROR")

    def test_unverified_gamma_can_retain_diagnostic_boolean(self) -> None:
        payload = _payload(gamma="INCONCLUSIVE")
        payload["gamma_bound_evaluated"] = True
        payload["gamma_bound_satisfied"] = True
        result = classify_v2_result("EXPOSED_JSON", payload, case_id=CASE_ID, pytest_execution_status="PASS")
        self.assertEqual(result["gamma_bound_satisfied"], True)
        self.assertEqual(result["gamma_scientific_status"], "INCONCLUSIVE")
        self.assertEqual(result["status"], "INCONCLUSIVE")

    def test_missing_marker_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "stdout.log"
            output.write_text("no result marker\n", encoding="utf-8")
            marker_status, payload = extract_numeric_payload(output)
        result = classify_v2_result(marker_status, payload, case_id=CASE_ID, pytest_execution_status="PASS")
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["pytest_execution_status"], "PASS")
        self.assertNotEqual(result["status"], "PASS")

    def test_malformed_and_duplicate_markers_are_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "stdout.log"
            output.write_text(MARKER + "{bad json}\n", encoding="utf-8")
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                extract_numeric_payload(output, strict=True)
            output.write_text(MARKER + '{"schema":"one","schema":"two"}\n', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                extract_numeric_payload(output, strict=True)
            output.write_text(MARKER + "{}\n" + MARKER + "{}\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                extract_numeric_payload(output)
        for marker_status in ("MALFORMED", "DUPLICATE"):
            result = classify_v2_result(marker_status, None, case_id=CASE_ID, pytest_execution_status="PASS")
            self.assertEqual(result["status"], "ERROR")

    def test_divergent_template_is_rejected_without_launch(self) -> None:
        manifest = {
            "campaign_id": V2_CAMPAIGN_ID,
            "command_template": V2_COMMAND_TEMPLATE[:-1],
            "identities": {name: {"path": "/synthetic/" + name} for name in ("science", "runner", "tests")},
            "environment": {"python": {"executable": sys.executable}},
        }
        case = {
            "command_profile": COMMAND_PROFILE_V2,
            "test_checkout": "tests",
            "case_id": CASE_ID,
            "nodeid": NODEID,
        }
        with patch("scripts.local_vv.process._checkout_path", side_effect=AssertionError("must reject first")):
            with patch.object(subprocess, "Popen", side_effect=AssertionError("must not launch")):
                with self.assertRaisesRegex(RuntimeError, "diverges"):
                    _case_command(manifest, case, Path("/synthetic/run"))
                manifest["command_template"] = list(V2_COMMAND_TEMPLATE)
                manifest["command_template"][4] = "--unknown-option"
                with self.assertRaisesRegex(RuntimeError, "diverges"):
                    _case_command(manifest, case, Path("/synthetic/run"))
                manifest["command_template"] = V2_COMMAND_TEMPLATE
                case["nodeid"] = "tests/unit/test_other.py::test_other"
                with self.assertRaisesRegex(RuntimeError, "scoped"):
                    _case_command(manifest, case, Path("/synthetic/run"))

    def test_fixed_v2_argv_and_historical_v1_argv(self) -> None:
        manifest = {
            "campaign_id": V2_CAMPAIGN_ID,
            "command_template": V2_COMMAND_TEMPLATE,
            "identities": {name: {"path": "/synthetic/" + name} for name in ("science", "runner", "tests")},
            "environment": {"python": {"executable": sys.executable}},
        }
        case = {"command_profile": COMMAND_PROFILE_V2, "test_checkout": "tests", "case_id": CASE_ID, "nodeid": NODEID}
        with patch(
            "scripts.local_vv.process._checkout_path", side_effect=lambda _manifest, key: Path("/synthetic/" + key)
        ):
            with patch("scripts.local_vv.process._execution_environment", return_value={}):
                with patch.object(subprocess, "Popen", side_effect=AssertionError("must not launch")):
                    argv, _cwd, _environment = _case_command(manifest, case, Path("/synthetic/run"))
        template_values = {
            "python_executable": sys.executable,
            "tests_checkout": str(Path("/synthetic/tests")),
            "new_run_directory": str(Path("/synthetic/run")),
            "one_exact_nodeid": NODEID,
        }
        expected_argv = []
        for part in V2_COMMAND_TEMPLATE:
            if part == "{tests_checkout}/pyproject.toml":
                expected_argv.append(str(Path(template_values["tests_checkout"]) / "pyproject.toml"))
            elif part == "--junitxml={new_run_directory}/junit.xml":
                expected_argv.append(f"--junitxml={Path(template_values['new_run_directory']) / 'junit.xml'}")
            else:
                expected_argv.append(part.format_map(template_values))
        self.assertEqual(argv, expected_argv)
        self.assertEqual(argv.count(NODEID), 1)

        case["command_profile"] = COMMAND_PROFILE
        manifest.pop("command_template")
        with patch(
            "scripts.local_vv.process._checkout_path", side_effect=lambda _manifest, key: Path("/synthetic/" + key)
        ):
            with patch("scripts.local_vv.process._execution_environment", return_value={}):
                argv_v1, _cwd, _environment = _case_command(manifest, case, Path("/synthetic/run"))
        self.assertEqual(argv_v1, argv)


if __name__ == "__main__":
    forbidden = {"pytest", "solveur", "numpy", "scipy"}.intersection(sys.modules)
    if forbidden:
        raise SystemExit("synthetic harness unexpectedly imported: " + ", ".join(sorted(forbidden)))
    unittest.main()
