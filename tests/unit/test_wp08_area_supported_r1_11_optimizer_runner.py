"""Tests for the source-bound R1.11 campaign configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def _runner_constants(environment: dict[str, str]) -> dict[str, object]:
    snippet = """
import json
from scripts import run_wp08_area_supported_m1_diagnostic_r1_10 as m1
from scripts import run_wp08_area_supported_m2_m3_diagnostic_r1_10 as m23
print(json.dumps({
  'm1_revision': m1.CAMPAIGN_REVISION,
  'm1_artifact': m1.ARTIFACT_ID,
  'm1_document': m1.CONTRACT_DOCUMENT_REL.as_posix(),
  'm2_revision': m23.CAMPAIGN_REVISION,
  'm2_artifact': m23.ARTIFACT_ID,
  'm1_root': m23.M1_OUTPUT_ROOT_REL.as_posix(),
  'm2_contract': m23.CONTRACT_REL.as_posix(),
  'm2_binding': m23.FREEZE_BINDING_REL.as_posix(),
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_r1_11_environment_binds_both_runners_to_new_contract_and_output() -> None:
    env = os.environ.copy()
    env.update(
        {
            "QF_WP08_CAMPAIGN_REVISION": "R1.11",
            "QF_WP08_ARTIFACT_ID": "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.11",
            "QF_WP08_CONTRACT_DOCUMENT_REL": "docs/verification/0_2_9/wp08-area-supported-contact-r1-11-optimizer.md",
            "QF_WP08_M1_OUTPUT_ROOT_REL": "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_11_optimizer_20260926",
            "QF_WP08_M2M3_CONTRACT_REL": "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_11_optimizer_20260926/contract_r1_11_optimizer_contact_requalification.json",
            "QF_WP08_M2M3_BINDING_REL": "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_11_optimizer_20260926/freeze_binding_r1_11_optimizer_contact_requalification.json",
        }
    )

    observed = _runner_constants(env)

    assert observed == {
        "m1_revision": "R1.11",
        "m1_artifact": "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.11",
        "m1_document": "docs/verification/0_2_9/wp08-area-supported-contact-r1-11-optimizer.md",
        "m2_revision": "R1.11",
        "m2_artifact": "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.11",
        "m1_root": "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_11_optimizer_20260926",
        "m2_contract": "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_11_optimizer_20260926/contract_r1_11_optimizer_contact_requalification.json",
        "m2_binding": "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_11_optimizer_20260926/freeze_binding_r1_11_optimizer_contact_requalification.json",
    }


def test_r1_10_runner_defaults_remain_unchanged() -> None:
    env = os.environ.copy()
    for name in (
        "QF_WP08_CAMPAIGN_REVISION",
        "QF_WP08_ARTIFACT_ID",
        "QF_WP08_CONTRACT_DOCUMENT_REL",
        "QF_WP08_M1_OUTPUT_ROOT_REL",
        "QF_WP08_M2M3_CONTRACT_REL",
        "QF_WP08_M2M3_BINDING_REL",
    ):
        env.pop(name, None)

    observed = _runner_constants(env)

    assert observed["m1_revision"] == "R1.10"
    assert observed["m2_revision"] == "R1.10"
    assert observed["m1_artifact"] == "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.10"
    assert observed["m2_artifact"] == observed["m1_artifact"]
    assert observed["m1_root"].endswith("area_supported_r1_10_20260926")
    assert observed["m2_contract"].endswith("contract_r1_10_contact_requalification.json")
