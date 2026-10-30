"""Small synthetic-only child used by process-attestation tests."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def _write_junit(path: Path, nodeid: str, outcome: str) -> None:
    node_path, _, test_name = nodeid.partition("::")
    module = node_path.removesuffix(".py").replace("/", ".")
    suite = ET.Element(
        "testsuite",
        {
            "name": module,
            "tests": "1",
            "failures": "1" if outcome == "failure" else "0",
            "errors": "0",
            "skipped": "0",
        },
    )
    case = ET.SubElement(suite, "testcase", {"classname": module, "name": test_name})
    if outcome == "failure":
        ET.SubElement(case, "failure", {"message": "synthetic failure"}).text = "synthetic only"
    path.write_bytes(ET.tostring(suite, encoding="utf-8", xml_declaration=True))


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--hold":
        Path(sys.argv[2]).write_text(str(os.getpid()), encoding="ascii")
        time.sleep(30)
        return 0
    if len(sys.argv) != 4:
        return 64
    scenario, junit_text, nodeid = sys.argv[1:]
    junit_path = Path(junit_text)
    print(f"WP12_C_SYNTHETIC_CHILD:{scenario}", flush=True)
    time.sleep(0.15)
    if scenario == "timeout":
        time.sleep(30)
    if scenario == "descendant":
        pid_path = junit_path.parent / "descendant.pid"
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--hold", str(pid_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            close_fds=True,
        )
        deadline = time.monotonic() + 2
        while not pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        time.sleep(30)
    if scenario == "no_junit":
        return 0
    if scenario == "contradictory_junit":
        junit_path.write_text("<testsuite tests='2' failures='0' errors='0' skipped='0'></testsuite>", encoding="utf-8")
        return 0
    if scenario == "junit_substitution":
        _write_junit(junit_path.with_name("substituted-junit.xml"), nodeid, "pass")
        return 0
    if scenario == "nonzero":
        _write_junit(junit_path, nodeid, "failure")
        return 1
    if scenario != "success":
        return 65
    _write_junit(junit_path, nodeid, "pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
