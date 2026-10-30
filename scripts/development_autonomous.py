"""Bounded, noninteractive pytest launcher for local development only.

This is a workflow/resource monitor, not a sandbox. It intentionally exposes
fixed pytest scopes instead of an arbitrary command execution interface.
"""

from __future__ import annotations

import argparse
import ast
import base64
import binascii
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
import re
import shutil
import subprocess
import struct
import sys
import tempfile
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from contextlib import ExitStack, contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator, Mapping, Sequence

try:
    import psutil
except ImportError:  # pragma: no cover - exercised only in an incomplete dev install
    psutil = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]


def _load_vv3d_r2_ledger_module() -> Any:
    """Load the R2 ledger as a sibling module in CLI and package contexts."""
    module_name = ".wp12_vv3d_r2_ledger" if __package__ else "wp12_vv3d_r2_ledger"
    module = importlib.import_module(module_name, package=__package__ or None)
    expected_path = Path(__file__).resolve().with_name("wp12_vv3d_r2_ledger.py")
    try:
        actual_path = Path(module.__file__).resolve(strict=True)
    except (AttributeError, OSError) as exc:
        raise PolicyError("VV3D R2 ledger module has no verifiable source path") from exc
    if actual_path != expected_path:
        raise PolicyError("VV3D R2 ledger module resolved outside the active controller checkout")
    return module


def _registered_root(value: str, *, strict: bool = False) -> Path:
    """Resolve an absolute worktree root or a repository-relative root."""
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve(strict=strict)


POLICY_PATH = ROOT / "development_autonomous_policy.json"
SERIES_RE = re.compile(r"^dev-[a-z0-9][a-z0-9-]{7,48}$")
PREFLIGHT_RE = re.compile(r"^pf-[a-z0-9]{12}$")
STANDARD_SCOPES = {"unit", "integration"}
WORKTREE_SCOPES = {"fem_exploratory", "math_non_fem"}
HEX8SRI_CONVERGENCE24_WORKTREE_ID = "hex8sri-convergence24"
HEX8SRI_CONVERGENCE24_CAMPAIGN_ID = "HEX8-SRI-CONVERGENCE-24-2026-10-27"
HEX8SRI_CONVERGENCE24_MANDATE_ID = "DEVELOPMENT_AUTONOMOUS-HEX8SRI-CONVERGENCE24-2026-10-27-v1"
HEX8SRI_CONVERGENCE24_LEDGER = "node-attempt-ledger-hex8sri-convergence24.json"
WP12_DYNAMICS_LEDGER = "node-attempt-ledger-wp12-dynamics-v2.json"
_WP12A_BATCH_LOCK_LOCAL = threading.local()
WP12_DYNAMICS_LEGACY_MANDATE_ID = "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v1"
HEX8SRI_EXECUTION_MANIFEST_SCHEMA = "qfsolver-hex8sri-convergence24-execution-v1"
HEX8SRI_CRITERIA_FREEZE_SCHEMA = "qfsolver-hex8sri-criteria-freeze-v1"
HEX8SRI_CRITERIA_FREEZE_DECISION_SCHEMA = "qfsolver-hex8sri-criteria-freeze-decision-v1"
HEX8SRI_EXECUTION_APPROVAL_SCHEMA = "qfsolver-hex8sri-execution-approval-v1"
HEX8SRI_CRITERIA_CONTRACT_SCHEMA = "qfsolver-hex8sri-criteria-contract-v1"
HEX8SRI_CRITERIA_CONTRACT_REVISION = "first6-4x2x2-owner-criteria-2026-10-27-r1"
HEX8SRI_REFINED3_CRITERIA_CONTRACT_REVISION = "refined3-8x4x4-nu04999-owner-criteria-2026-10-30-r1"
VV3D_WORKTREE_ID = "wp12_vv3d_adaptive"
VV3D_CAMPAIGN_ID = "WP12-VV3D-ADAPTIVE-20261029-R1"
VV3D_R2_WORKTREE_ID = "wp12_vv3d_recovery_r2"
VV3D_R2_CAMPAIGN_ID = "WP12-VV3D-RECOVERY-20261030-R2"
VV3D_R2_MANDATE_ID = "DEVELOPMENT_AUTONOMOUS-WP12-VV3D-RECOVERY-2026-10-30-R2"
VV3D_R2_LEDGER_FILENAME = "node-attempt-ledger-wp12-vv3d-recovery-r2.jsonl"
VV3D_R1_LEDGER_SHA256 = "2788619d097d148c74a3e71cef456ee52bc03642d680f9090360418b61d20bf8"
VV3D_R1_LEDGER_PATH = Path(
    r"E:\QFSolverAgents\evidence\wp12-vv3d-adaptive\node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl"
)
VV3D_R2_SOURCE_IDENTITY = {
    "branch": "research/wp12-vv3d-recovery-r2",
    "head": "ba36860a156468dd7c54ee435a809222e227205a",
    "tree": "2f8c0d3cef5a6b07eac9ad48d0dcb1a311af72e2",
    "fingerprint_sha256": "651bbacaf133106a6a8c8b2177e8741cf3fed9a9fdfc7f907d350484dfebd3ce",
}
VV3D_R2_SOURCE_ROOT = Path(r"E:\QFSolverAgents\test-worktrees\vv3d-science-source-candidate")
VV3D_R2_EVIDENCE_ROOT = Path(r"E:\QFSolverAgents\evidence\wp12-vv3d-recovery-r2")
VV3D_INITIAL_CASE_IDS = tuple(
    f"VV3D-{family}-L{level}"
    for family in ("TET4", "TET10", "HEX8", "HEX20")
    for level in (1, 2, 3)
)
VV3D_INITIAL_NODEIDS = tuple(
    "tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[" + case_id + "]"
    for case_id in VV3D_INITIAL_CASE_IDS
)
VV3D_R2_NODEIDS = VV3D_INITIAL_NODEIDS
VV3D_ADAPTIVE_FEM_NODEIDS = tuple(
    "tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_adaptive_fem_case[VV3D-ADAPT-"
    f"{family}-{kind}]"
    for family in ("TET4", "TET10", "HEX8", "HEX20")
    for kind in ("H1", "QLOAD")
)
VV3D_QPOST_NODEIDS = tuple(
    "tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_archived_postprocess_case["
    f"{family}]"
    for family in ("TET4", "TET10", "HEX8", "HEX20")
)
VV3D_INITIAL_DOFS = {
    "VV3D-TET4-L1": 81, "VV3D-TET4-L2": 375, "VV3D-TET4-L3": 2187,
    "VV3D-TET10-L1": 375, "VV3D-TET10-L2": 2187, "VV3D-TET10-L3": 14739,
    "VV3D-HEX8-L1": 81, "VV3D-HEX8-L2": 375, "VV3D-HEX8-L3": 2187,
    "VV3D-HEX20-L1": 243, "VV3D-HEX20-L2": 1275, "VV3D-HEX20-L3": 8019,
}
VV3D_ADAPTIVE_DOFS = {
    VV3D_ADAPTIVE_FEM_NODEIDS[0]: 14739, VV3D_ADAPTIVE_FEM_NODEIDS[1]: 2187,
    VV3D_ADAPTIVE_FEM_NODEIDS[2]: 27783, VV3D_ADAPTIVE_FEM_NODEIDS[3]: 14739,
    VV3D_ADAPTIVE_FEM_NODEIDS[4]: 14739, VV3D_ADAPTIVE_FEM_NODEIDS[5]: 2187,
    VV3D_ADAPTIVE_FEM_NODEIDS[6]: 24843, VV3D_ADAPTIVE_FEM_NODEIDS[7]: 8019,
}
VV3D_QPOST_DOFS = {
    VV3D_QPOST_NODEIDS[0]: 2187, VV3D_QPOST_NODEIDS[1]: 14739,
    VV3D_QPOST_NODEIDS[2]: 2187, VV3D_QPOST_NODEIDS[3]: 8019,
}
VV3D_ALL_NODEIDS = (*VV3D_INITIAL_NODEIDS, *VV3D_ADAPTIVE_FEM_NODEIDS, *VV3D_QPOST_NODEIDS)
VV3D_ALL_DOFS = {
    **{nodeid: VV3D_INITIAL_DOFS[nodeid.rsplit("[", maxsplit=1)[-1][:-1]] for nodeid in VV3D_INITIAL_NODEIDS},
    **VV3D_ADAPTIVE_DOFS, **VV3D_QPOST_DOFS,
}
VV3D_ADAPTIVE_SOURCE_FILES = (
    "experiments/wp12_vv3d_adaptive/case_harness.py",
    "experiments/wp12_vv3d_adaptive/load_assembly_draft.py",
    "experiments/wp12_vv3d_adaptive/field_error_draft.py",
    "experiments/wp12_vv3d_adaptive/sampling.py",
    "experiments/wp12_vv3d_adaptive/quadrature.py",
    "experiments/wp12_vv3d_adaptive/basis.py",
    "experiments/wp12_vv3d_adaptive/oracle.py",
    "experiments/wp12_vv3d_adaptive/mesh.py",
    "experiments/wp12_vv3d_adaptive/metrics.py",
    "experiments/wp12_vv3d_adaptive/criteria_evaluator.py",
    "experiments/wp12_vv3d_adaptive/evidence.py",
    "tests/unit/test_wp12_vv3d_adaptive_prepared.py",
)
HEX8SRI_CONVERGENCE24_MANIFEST_BINDING = "canonical_case_content_v1"
HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT = "64d5760e1c904d110a1c1ce9bc490f3f64fdc5168b264de244a7cd878e6c4f2d"
HEX8SRI_CONVERGENCE24_SOURCE_HEAD = "e251883a0dd13e20628eb2ee229b630603af1efb"
HEX8SRI_CONVERGENCE24_SOURCE_TREE = "fdf9e76cff3293be3705cf29a3226fb480a928ad"
HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_PATH = (
    "docs/development/hex8sri-source-byte-inventory-e251883a.json"
)
HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_SHA256 = "53bc4d1b4c1506562469aa018d30dde8c9b7b39f1ed4ac61d6bb93e06028d183"
HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_FILE_COUNT = 540
HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT_ALGORITHM = "raw_worktree_inventory_sha256_v1"
HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY = {
    "branch": "research/hex8sri-equilibrium-8x4x4-20261030",
    "head": HEX8SRI_CONVERGENCE24_SOURCE_HEAD,
    "tree": HEX8SRI_CONVERGENCE24_SOURCE_TREE,
    "fingerprint_sha256": HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
    "fingerprint_algorithm": HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT_ALGORITHM,
    "inventory_path": HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_PATH,
    "inventory_sha256": HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_SHA256,
    "inventory_file_count": HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_FILE_COUNT,
    "raw_byte_policy": "preserve checkout bytes; no LF/CRLF normalization",
}
HEX8SRI_EXECUTION_TEST_CONTRACT_MARKER = "QF-HEX8SRI-EXECUTION-CONTRACT: hex8sri-convergence24-v2"
HEX8SRI_CONVERGENCE24_FORMULATIONS = ("hex8_standard", "sri_historical", "sri_corrected")
HEX8SRI_CONVERGENCE24_NU_TOKENS = {"0p3": 0.3, "0p4999": 0.4999}
HEX8SRI_FIRST6_NODEIDS = (
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-4x2x2]",
)
HEX8SRI_REFINED3_NODEIDS = (
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-8x4x4]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-8x4x4]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-8x4x4]",
)
HEX8SRI_FREEZABLE_NODEIDS = HEX8SRI_FIRST6_NODEIDS + HEX8SRI_REFINED3_NODEIDS
HEX8SRI_PROPOSED_CRITERIA = {
    "energy_identity_relative_max": 1e-8,
    "finest_level_independent_3d_energy_relative_error_max": 0.05,
    "finest_level_independent_3d_mean_UZ_relative_error_max": 0.05,
    "force_closure_relative_max": 1e-6,
    "free_residual_relative_max": 1e-7,
    "last_two_levels_energy_relative_change_max": 0.02,
    "last_two_levels_mean_UZ_relative_change_max": 0.02,
    "moment_closure_relative_max": 1e-6,
}
HEX8SRI_CASE_GATE_THRESHOLD_KEYS = (
    "free_residual_relative_max",
    "energy_identity_relative_max",
    "force_closure_relative_max",
    "moment_closure_relative_max",
)
HEX8SRI_CRITERIA_DISPOSITIONS = {
    "finite_state": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "positive_sampled_jacobians_center_and_gauss": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "free_residual_relative_max": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "energy_identity_relative_max": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "force_closure_relative_max": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "moment_closure_relative_max": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "negative_mean_loaded_face_uz": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "stiffness_symmetry_relative_frobenius": {
        "classification": "CASE_DIAGNOSTIC",
        "status": "DESCRIPTIVE_ONLY",
    },
    "affine_jacobian_reproduction": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "positive_internal_energy": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "formulation_comparison": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "condition_number_1_estimate_Kff": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "timing_seconds": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "rss_peak_bytes": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "timoshenko_relative_difference": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "last_two_levels_energy_relative_change_max": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
    "last_two_levels_mean_UZ_relative_change_max": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
    "finest_level_independent_3d_energy_relative_error_max": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
    "finest_level_independent_3d_mean_UZ_relative_error_max": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
    "single_case_convergence": {"classification": "CAMPAIGN_GATE_DEFERRED", "status": "NOT_ASSESSED"},
    "independent_3d_reference_error": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
}
HEX8SRI_CRITERIA_DEFINITIONS = {
    "finite_state": {
        "formula": "All required scalar and array observables satisfy isfinite(value).",
        "units": "Each observable retains its declared SI unit.",
        "threshold": {"operator": "all_finite"},
        "applicability": "Each case; failure blocks the case.",
    },
    "positive_sampled_jacobians_center_and_gauss": {
        "formula": "det(J_q) > 0 for every element center and every evaluated 2x2x2 Gauss point.",
        "units": "m^3",
        "threshold": {"operator": ">", "value": 0.0},
        "applicability": "Each case at the points evaluated by the formulation.",
    },
    "free_residual_relative_max": {
        "formula": "||r_free||_2 / max(||F_free||_2, ||K_ff u_free||_2, 1 N), where r=K u-F.",
        "units": "dimensionless",
        "threshold": {"operator": "<=", "value": 1e-7},
        "applicability": "Each case; free-DOF equilibrium gate.",
    },
    "energy_identity_relative_max": {
        "formula": "|2 U_internal - W_external| / |W_external|; undefined work is a failure.",
        "units": "dimensionless; U_internal and W_external are J.",
        "threshold": {"operator": "<=", "value": 1e-8},
        "applicability": "Each case; algebraic linear-elastic identity.",
    },
    "force_closure_relative_max": {
        "formula": "||sum(F_applied)+sum(R_support)||_2 / max(||sum(F_applied)||_2, ||sum(R_support)||_2, 1 N).",
        "units": "dimensionless; force resultants are N.",
        "threshold": {"operator": "<=", "value": 1e-6},
        "applicability": "Each case; global resultant balance.",
    },
    "moment_closure_relative_max": {
        "formula": "||sum(M_applied)+sum(M_support)||_2 / max(||sum(M_applied)||_2, ||sum(M_support)||_2, 1 N m).",
        "units": "dimensionless; moment resultants are N m.",
        "threshold": {"operator": "<=", "value": 1e-6},
        "applicability": "Each case; global moment balance about the recorded origin.",
    },
    "negative_mean_loaded_face_uz": {
        "formula": "Consistent area-weighted Q1 mean displacement on the loaded face satisfies mean(U_z) < 0.",
        "units": "m",
        "threshold": {"operator": "<", "value": 0.0},
        "applicability": "Each case under the registered negative-Z traction.",
    },
    "stiffness_symmetry_relative_frobenius": {
        "formula": "||K-K^T||_F / max(||K||_F, tiny).",
        "units": "dimensionless",
        "threshold": None,
        "applicability": "Diagnostic only; not an assertion in this campaign.",
    },
    "affine_jacobian_reproduction": {
        "formula": "max_q |det(J_q)-det(J_center)| / max(|det(J_center)|, tiny), over sampled points.",
        "units": "dimensionless",
        "threshold": None,
        "applicability": "Diagnostic only; zero for an affine mapping up to arithmetic error.",
    },
    "positive_internal_energy": {
        "formula": "U_internal = 0.5 u^T K u; report whether U_internal > 0 without gating.",
        "units": "J",
        "threshold": None,
        "applicability": "Diagnostic only; positivity is not asserted by the first-six test.",
    },
    "formulation_comparison": {
        "formula": "For paired observables a,b: |a-b| / max(|a|,|b|,tiny).",
        "units": "dimensionless for relative differences; source observables retain their SI units.",
        "threshold": None,
        "applicability": "Descriptive comparison across matched formulations; not a case gate.",
    },
    "condition_number_1_estimate_Kff": {
        "formula": "Estimate of kappa_1(K_ff)=||K_ff||_1 ||K_ff^-1||_1 using the registered sparse estimator.",
        "units": "dimensionless",
        "threshold": None,
        "applicability": "Diagnostic estimate; no eigensolve and no acceptance threshold.",
    },
    "timing_seconds": {
        "formula": "Controller-observed elapsed wall time for the case and its phases.",
        "units": "s",
        "threshold": None,
        "applicability": "Descriptive resource observation; controller timeout remains a separate budget.",
    },
    "rss_peak_bytes": {
        "formula": "Maximum sampled resident-set size reported by the controller process monitor.",
        "units": "bytes",
        "threshold": None,
        "applicability": "Descriptive soft observation; not an OS memory quota.",
    },
    "timoshenko_relative_difference": {
        "formula": "|UZ_FE-UZ_Timoshenko| / |UZ_Timoshenko| for the stated beam model and observable.",
        "units": "dimensionless; both displacements are m.",
        "threshold": None,
        "applicability": "Trend indicator only; not an absolute 3D oracle or gate.",
    },
    "last_two_levels_energy_relative_change_max": {
        "formula": "|U_n-U_(n-1)| / max(|U_n|,|U_(n-1)|,tiny) at the two finest paired levels.",
        "units": "dimensionless; energy is J.",
        "threshold": {"operator": "<=", "value": 0.02},
        "applicability": "Deferred until the required paired refined meshes exist.",
    },
    "last_two_levels_mean_UZ_relative_change_max": {
        "formula": "|UZ_n-UZ_(n-1)| / max(|UZ_n|,|UZ_(n-1)|,tiny) at the two finest paired levels.",
        "units": "dimensionless; displacement is m.",
        "threshold": {"operator": "<=", "value": 0.02},
        "applicability": "Deferred until the required paired refined meshes exist.",
    },
    "finest_level_independent_3d_energy_relative_error_max": {
        "formula": "|U_finest-U_ref| / |U_ref| for a qualified independent 3D reference.",
        "units": "dimensionless; energy is J.",
        "threshold": {"operator": "<=", "value": 0.05},
        "applicability": "Deferred until a qualified independent 3D reference is available.",
    },
    "finest_level_independent_3d_mean_UZ_relative_error_max": {
        "formula": "|UZ_finest-UZ_ref| / |UZ_ref| for a qualified independent 3D reference.",
        "units": "dimensionless; displacement is m.",
        "threshold": {"operator": "<=", "value": 0.05},
        "applicability": "Deferred until a qualified independent 3D reference is available.",
    },
    "single_case_convergence": {
        "formula": "Campaign-level assessment from paired mesh-level displacement and energy changes.",
        "units": "dimensionless derived indicators.",
        "threshold": None,
        "applicability": "Deferred; a single 4x2x2 result cannot establish convergence.",
    },
    "independent_3d_reference_error": {
        "formula": "Campaign-level comparison of displacement and energy against a qualified independent 3D oracle.",
        "units": "dimensionless relative errors.",
        "threshold": None,
        "applicability": "Deferred; status remains NOT_ASSESSED until the reference is qualified.",
    },
}
HEX8SRI_CRITERIA_PROPOSAL_DISPOSITIONS = {
    key: {
        "classification": value["classification"],
        "status": "OWNER_FREEZE_REQUIRED" if value["classification"] == "CASE_GATE" else value["status"],
    }
    for key, value in HEX8SRI_CRITERIA_DISPOSITIONS.items()
}
HEX8SRI_FROZEN_CASE_GATE_CRITERIA = {
    key: HEX8SRI_PROPOSED_CRITERIA[key] for key in HEX8SRI_CASE_GATE_THRESHOLD_KEYS
}
HEX8SRI_CONVERGENCE24_MESH_BUDGETS = {
    "4x2x2": (180, 512),
    "8x4x4": (300, 1024),
    "16x8x8": (900, 4096),
    "32x16x16": (3600, 16384),
}
HEX8SRI_CONVERGENCE24_COMMON_BUDGET = {
    "process_tree_limit": 8,
    "output_total_limit_mib": 16,
    "output_stream_limit_mib": 8,
    "temporary_limit_mib": 512,
    "archive_size_limit_mib": 256,
    "minimum_free_disk_mib": 2048,
}
HEX8SRI_CONVERGENCE24_MANIFEST_CONTROLLER_FIELDS = frozenset(
    {"controller_code_sha256", "controller_identity", "controller_identity_status"}
)
OWNER_ENV_KEYS = {
    "WPC02_AR_NATIVE_OWNER_GO_TOKEN",
    "WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256",
    "QF_SOLVER_RUN_EVIDENCE",
    "QF_SOLVER_RUN_RECOVERED_EVIDENCE",
    "QF_SOLVER_EVIDENCE_ARCHIVE_ROOT",
}
NATIVE_GUARD_ENV_KEYS = (
    "QF_SOLVER_NO_NATIVE_EXECUTION",
    "WPC01_NO_NATIVE_EXECUTION",
    "WPC01_SPATIAL_NO_FEM_TEST",
    "WPC01_SPATIAL_TERMINAL_REHEARSAL",
)
D01_NATIVE_NODEIDS = (
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M1]",
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M2]",
    "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M3]",
)
D01_ATTEMPT_BASES = (
    "baseline",
    "source_change",
    "instrumentation_change",
    "launcher_correction",
    "new_diagnostic_hypothesis",
)
D01_OWNER_BUDGETS = {
    "timeout_seconds": 180,
    "rss_soft_limit_mib": 2048,
    "output_total_limit_mib": 64,
}
WP12_BASELINE_COMMIT = "6d8f140834db75ea9b968b055af23445261d0073"
WP12_COORDINATION_ROOT = Path(r"E:\QFSolverAgents\evidence\.wp12-coordination")
WP12_EXECUTION_SCOPE_ALIASES = {"wp12_elements_loads_corrective": "wp12_elements_loads"}
WP12_DYNAMICS_PREFLIGHT_NODEIDS = (
    "tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables",
    "tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation",
    "tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization",
    "tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames",
    "tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators",
    "tests/unit/test_reduced_harmonic.py::test_reduced_impedance_matches_independent_analytical_sdof_amplitude_and_phase",
    "tests/unit/test_reduced_harmonic.py::test_coupled_two_dof_complex_response_uses_full_projected_operators",
    "tests/unit/test_reduced_harmonic.py::test_reduced_impedance_detects_exact_and_near_resonance_before_solving",
    "tests/unit/test_modal_basis_damping.py::test_degenerate_subspace_rotation_and_sign_are_equivalent_and_residual_safe",
    "tests/unit/test_modal_basis_damping.py::test_rayleigh_projection_and_modal_damping_provenance_and_cluster_guard",
    "tests/unit/test_analysis_features.py::test_transient_dynamic_sdof_matches_closed_form_initial_energy",
    "tests/unit/test_analysis_features.py::test_harmonic_sdof_matches_closed_form_amplitude_and_phase",
    "tests/unit/test_prepared_dynamic_system.py::test_prepared_system_assembles_once_and_excitation_does_not_invalidate_operators",
)
WP12_DYNAMICS_P0_BATCH_NODEIDS = (
    "tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators",
    "tests/unit/test_modal_basis_damping.py::test_degenerate_subspace_rotation_and_sign_are_equivalent_and_residual_safe",
    "tests/unit/test_modal_basis_damping.py::test_rayleigh_projection_and_modal_damping_provenance_and_cluster_guard",
    "tests/unit/test_analysis_features.py::test_transient_dynamic_sdof_matches_closed_form_initial_energy",
    "tests/unit/test_analysis_features.py::test_harmonic_sdof_matches_closed_form_amplitude_and_phase",
    "tests/unit/test_prepared_dynamic_system.py::test_prepared_system_assembles_once_and_excitation_does_not_invalidate_operators",
)
WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID = "wp12_hex20_affine_diagnostic"
WP12B_HEX20_DIAGNOSTIC_NODEID = (
    "tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual"
)
WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_SCHEMA = "qfsolver-wp12b-hex20-diagnostic-collect-only-v1"
WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_MARKER = "QF_DEV_WP12B_HEX20_DIAGNOSTIC_PREFLIGHT="
WP12B_HEX20_R1_LEDGER_SHA256 = "ab5a8e4967ca204898f2eeec52b50f0c6b8e603d0328c3dff06926ff10669f53"
WP12B_HEX20_R1_MANDATE_ID = "DEVELOPMENT_AUTONOMOUS-WP12B-HEX20-AFFINE-DIAGNOSTIC-2026-10-27-R1"
WP12B_HEX20_R2_WORKTREE_ID = "wp12_hex20_affine_diagnostic_r2"
WP12B_HEX20_R2_MANDATE_ID = "DEVELOPMENT_AUTONOMOUS-WP12B-HEX20-AFFINE-DIAGNOSTIC-2026-10-29-R2"
WP12B_HEX20_R1_LEDGER_PATH = Path(
    r"E:\QFSolverAgents\evidence\wp12b-hex20-affine-diagnostic-consolidated\node-attempt-ledger.json"
)
WP12B_HEX20_R2_CRITERIA = {
    "displacement_rtol": 1e-10, "displacement_atol_m": 1e-13,
    "stress_rtol": 1e-10, "stress_atol_pa": 1e-4,
    "energy_relative_atol": 1e-10, "free_residual_max": 1e-10,
    "force_balance_max": 1e-12, "moment_balance_max": 1e-12, "energy_identity_max": 1e-10,
    "face_nodal_force_rtol": 1e-12, "face_nodal_force_atol_n": 1e-6,
    "additional_assertions": "finiteness, mesh and solver PASS, fixed indices, five faces, dimensions",
    "face_nodal_gate_status": "PROPOSED_FOR_OWNER",
}
WP12_OWNER_ENVELOPES: dict[str, dict[str, Any]] = {
    "wp12_wp07": {
        "root": r"E:\QFSolverAgents\wp07",
        "branch": "fix/wp12-wp07-serialization",
        "evidence_root": r"E:\QFSolverAgents\evidence\wp07",
        "timeout_seconds": 300,
        "max_timeout_seconds": 300,
        "max_total_attempts": 10,
        "attempt_limit_per_nodeid": 10,
        "max_registered_nodeids": 10,
        "max_dofs": None,
        "max_fem_cases_per_attempt": 1,
        "concurrency_class": "parallel",
        "development_mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-WP07-2026-10-26-v1",
    },
    "wp12_tet4": {
        "root": r"E:\QFSolverAgents\tet4",
        "branch": "experiment/wp12-tet4-convergence",
        "evidence_root": r"E:\QFSolverAgents\evidence\tet4",
        "timeout_seconds": 900,
        "max_timeout_seconds": 900,
        "max_total_attempts": 12,
        "attempt_limit_per_nodeid": 12,
        "max_registered_nodeids": 12,
        "max_dofs": 50000,
        "max_fem_cases_per_attempt": 1,
        "concurrency_class": "parallel",
        "development_mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-TET4-2026-10-26-v1",
    },
    "wp12_elements": {
        "root": r"E:\QFSolverAgents\vv-elements",
        "branch": "test/wp12-fem-regressions",
        "evidence_root": r"E:\QFSolverAgents\evidence\vv-elements",
        "timeout_seconds": 300,
        "max_timeout_seconds": 900,
        "max_total_attempts": 20,
        "attempt_limit_per_nodeid": 20,
        "max_registered_nodeids": 20,
        "max_dofs": 30000,
        "max_fem_cases_per_attempt": 1,
        "concurrency_class": "parallel",
        "development_mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-ELEMENTS-2026-10-26-v1",
    },
    "wp12_elements_loads": {
        "root": r"C:\Users\fari\.codex\worktrees\verify-wp12-elements-loads\qf_solver",
        "branch": "verify/wp12-elements-loads",
        "evidence_root": r"E:\QFSolverAgents\evidence\wp12-elements-loads",
        "timeout_seconds": 300,
        "max_timeout_seconds": 300,
        "max_total_attempts": 3,
        "attempt_limit_per_nodeid": 1,
        "max_registered_nodeids": 3,
        "max_dofs": 30000,
        "max_fem_cases_per_attempt": 1,
        "concurrency_class": "parallel",
        "development_mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-B-ELEMENTS-LOADS-2026-10-26-v1",
    },
    "wp12_elements_loads_corrective": {
        "root": r"C:\Users\fari\.codex\worktrees\verify-wp12-elements-loads\qf_solver",
        "branch": "emptiesvoids-cloud/fix-wp12b-scope-identity-guard",
        "evidence_root": r"E:\QFSolverAgents\evidence\wp12-elements-loads-corrective-r1",
        "timeout_seconds": 300,
        "max_timeout_seconds": 300,
        "max_total_attempts": 3,
        "attempt_limit_per_nodeid": 1,
        "max_registered_nodeids": 3,
        "max_dofs": 30000,
        "max_fem_cases_per_attempt": 1,
        "concurrency_class": "parallel",
        "development_mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-B-ELEMENTS-LOADS-CORRECTIVE-2026-10-26-R1",
        "campaign_id": "WP12B-CORRECTIVE-R1-2026-10-26",
        "execution_scope_id": "wp12_elements_loads",
    },
    "wp12_dynamics": {
        "root": r"E:\QFSolverAgents\wp12-dynamics",
        "branch": "codex/wp12-dynamic-harmonic-verification",
        "evidence_root": r"E:\QFSolverAgents\evidence\dynamics",
        "timeout_seconds": 300,
        "max_timeout_seconds": 300,
        "max_total_attempts": 130,
        "attempt_limit_per_nodeid": 10,
        "max_registered_nodeids": 18,
        "max_dofs": None,
        "max_fem_cases_per_attempt": 1,
        "concurrency_class": "parallel",
        "development_mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-DYNAMICS-2026-10-26-v1",
    },
    "rotor": {
        "root": r"C:\Users\fari\.codex\worktrees\wp12-rotor-performance\qf_solver",
        "branch": "verify/wp12-rotor-performance",
        "evidence_root": r"E:\QFSolverAgents\evidence\rotor",
        "timeout_seconds": 300,
        "max_timeout_seconds": 300,
        "max_total_attempts": 8,
        "attempt_limit_per_nodeid": 1,
        "max_registered_nodeids": 8,
        "max_dofs": 12,
        "max_fem_cases_per_attempt": 1,
        "concurrency_class": "parallel",
        "development_mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-ROTOR-2026-10-26-v1",
    },
    WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID: {
        "root": r"C:\Users\fari\.codex\worktrees\wp12b-hex20-r4-restore\qf_solver",
        "branch": "emptiesvoids-cloud/wp12b-hex20-r4-assertions",
        "evidence_root": r"E:\QFSolverAgents\evidence\wp12b-hex20-affine-diagnostic-consolidated",
        "timeout_seconds": 300,
        "max_timeout_seconds": 300,
        "max_total_attempts": 1,
        "attempt_limit_per_nodeid": 1,
        "max_registered_nodeids": 1,
        "max_dofs": 60,
        "max_fem_cases_per_attempt": 1,
        "concurrency_class": "parallel",
        "development_mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12B-HEX20-AFFINE-DIAGNOSTIC-2026-10-27-R1",
        "campaign_id": "WP12B-HEX20-AFFINE-DIAGNOSTIC-R1-2026-10-27",
        "execution_scope_id": WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID,
    },
    WP12B_HEX20_R2_WORKTREE_ID: {
        "root": r"E:\QFSolverAgents\wp12b-hex20-r2-prospective",
        "branch": "research/wp12b-hex20-r2-prospective",
        "evidence_root": r"E:\QFSolverAgents\evidence\wp12b-hex20-affine-diagnostic-r2",
        "timeout_seconds": 300,
        "max_timeout_seconds": 300,
        "max_total_attempts": 1,
        "attempt_limit_per_nodeid": 1,
        "max_registered_nodeids": 1,
        "max_dofs": 60,
        "max_fem_cases_per_attempt": 1,
        "concurrency_class": "parallel",
        "development_mandate_id": WP12B_HEX20_R2_MANDATE_ID,
        "campaign_id": "WP12B-HEX20-AFFINE-DIAGNOSTIC-R2-2026-10-29",
        "execution_scope_id": WP12B_HEX20_R2_WORKTREE_ID,
    },
}
WP12_RUN_BUDGETS = {
    "rss_soft_limit_mib": 4096,
    "process_tree_limit": 16,
    "output_total_limit_mib": 64,
    "output_stream_limit_mib": 32,
    "temporary_limit_mib": 512,
    "archive_size_limit_mib": 256,
}
WP12_MAX_PARALLEL_FEM_SLOTS = 3
WP12_TEST_SELECTOR_RE = re.compile(r"(test_[A-Za-z0-9_]+)(?:\[[^\]\r\n]{1,128}\])?")
WP12_ELEMENTS_VERIFICATION_NODEIDS = frozenset(
    {
        "tests/verification/test_wp12_hex8_sri_diagnostics.py::test_wp12_hex8_sri_near_incompressible_nu04999_nx16",
        "tests/verification/test_wp12_hex8_sri_diagnostics.py::test_wp12_hex8_sri_near_degenerate_nu0495_nx4",
    }
)
WP12_ROTOR_NODEIDS = frozenset(
    {
        "tests/unit/test_rotating_modal_cases.py::test_gyro01_zero_speed_matches_modal_frequencies_multiplicity_and_subspaces",
        "tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_unit_speed_gyro_blocks_match_contract",
        "tests/unit/test_rotating_disk_gyro.py::test_assembled_gyro_uses_same_global_dof_map_and_has_zero_quadratic_work",
        "tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[100.0]",
        "tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[-100.0]",
        "tests/unit/test_modal_tracking.py::test_competing_source_modes_make_the_global_assignment_ambiguous",
        "tests/unit/test_campbell.py::test_campbell_sweep_reuses_one_model_and_serializes_complex_source_results",
        "tests/unit/test_campbell.py::test_campbell_is_exposed_through_model_schema_and_analysis_router",
    }
)


class PolicyError(ValueError):
    """A development run is outside the repository policy."""


@dataclass(frozen=True)
class ProcessResult:
    status: str
    return_code: int | None
    elapsed_seconds: float
    peak_rss_bytes: int
    peak_process_count: int
    stdout_bytes: int
    stderr_bytes: int
    archive_bytes: int
    temporary_bytes: int
    stop_reason: str | None


def _positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"policy field {name} must be a positive number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise PolicyError(f"policy field {name} must be a finite positive number") from exc
    if not math.isfinite(number) or number <= 0:
        raise PolicyError(f"policy field {name} must be a positive number")
    return number


def _positive_integer(value: Any, name: str) -> int:
    number = _positive_number(value, name)
    if not number.is_integer():
        raise PolicyError(f"policy field {name} must be an integer")
    return int(number)


def _hex8sri_convergence24_nodeids() -> tuple[str, ...]:
    return tuple(
        sorted(
            "tests/verification/test_hex8_sri_convergence.py::test_convergence_case["
            f"{formulation}-nu_{nu_token}-{mesh_token}]"
            for formulation in HEX8SRI_CONVERGENCE24_FORMULATIONS
            for nu_token in HEX8SRI_CONVERGENCE24_NU_TOKENS
            for mesh_token in HEX8SRI_CONVERGENCE24_MESH_BUDGETS
        )
    )


def _hex8sri_convergence24_case(nodeid: str) -> tuple[str, str, str] | None:
    prefix = "tests/verification/test_hex8_sri_convergence.py::test_convergence_case["
    if not nodeid.startswith(prefix) or not nodeid.endswith("]"):
        return None
    try:
        formulation, nu_token, mesh_token = nodeid[len(prefix) : -1].split("-", maxsplit=2)
    except ValueError:
        return None
    if (
        formulation not in HEX8SRI_CONVERGENCE24_FORMULATIONS
        or not nu_token.startswith("nu_")
        or nu_token[3:] not in HEX8SRI_CONVERGENCE24_NU_TOKENS
        or mesh_token not in HEX8SRI_CONVERGENCE24_MESH_BUDGETS
    ):
        return None
    return formulation, nu_token[3:], mesh_token


def _hex8sri_convergence24_budget(nodeid: str) -> dict[str, int]:
    case = _hex8sri_convergence24_case(nodeid)
    if case is None:
        raise PolicyError("HEX8-SRI convergence nodeid is outside its exact 24-case matrix")
    _, _, mesh_token = case
    timeout_seconds, rss_mib = HEX8SRI_CONVERGENCE24_MESH_BUDGETS[mesh_token]
    return {
        **HEX8SRI_CONVERGENCE24_COMMON_BUDGET,
        "timeout_seconds": timeout_seconds,
        "rss_soft_limit_mib": rss_mib,
    }


def _hex8sri_execution_limits(entry: Mapping[str, Any], target: str) -> dict[str, Any]:
    """Return the immutable per-case budget and attempt envelope for an Owner manifest."""
    if target not in entry.get("allowed_nodeids", ()):
        raise PolicyError("HEX8-SRI execution limits require one exactly registered nodeid")
    budgets = entry.get("per_node_budgets", {}).get(target)
    if not isinstance(budgets, Mapping):
        raise PolicyError("HEX8-SRI execution node has no registered per-node budget")
    return {
        **dict(budgets),
        "attempts_per_nodeid": int(entry["attempt_limit_per_nodeid"]),
        "campaign_max_attempts": int(entry["max_total_attempts"]),
        "blas_thread_environment": dict(entry["blas_thread_environment"]),
        "budget_semantics": {
            "captured_output": "controller-enforced byte caps",
            "rss_process_temporary_archive": "sampled soft observations, not OS quotas",
            "wall_timeout": "watchdog process-tree termination, best effort",
        },
    }


def _hex8sri_manifest_registration_sha256(manifest: Mapping[str, Any]) -> str:
    content = {
        key: value for key, value in manifest.items() if key not in HEX8SRI_CONVERGENCE24_MANIFEST_CONTROLLER_FIELDS
    }
    payload = json.dumps(content, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def _hex8sri_convergence24_case_contract(manifest: Mapping[str, Any]) -> dict[str, Any]:
    mesh = manifest.get("mesh")
    if not isinstance(mesh, Mapping):
        raise PolicyError("HEX8-SRI convergence manifest has no mesh contract")
    divisions = mesh.get("divisions_xyz")
    if (
        not isinstance(divisions, list)
        or len(divisions) != 3
        or any(type(value) is not int or value < 1 for value in divisions)
    ):
        raise PolicyError("HEX8-SRI convergence manifest has invalid structured mesh divisions")
    nx, ny, nz = divisions
    total_dofs = 3 * (nx + 1) * (ny + 1) * (nz + 1)
    fixed_dofs = 3 * (ny + 1) * (nz + 1)
    expected = {
        "element_count": nx * ny * nz,
        "node_count": (nx + 1) * (ny + 1) * (nz + 1),
        "dof_count": total_dofs,
        "fixed_dof_count": fixed_dofs,
        "free_dof_count": total_dofs - fixed_dofs,
    }
    if any(mesh.get(name) != value for name, value in expected.items()):
        raise PolicyError("HEX8-SRI convergence manifest DDL or element counts do not match its structured mesh")
    return {"divisions_xyz": divisions, **expected}


def _validate_wp12_case_selection(
    worktree_id: str,
    *,
    selected_dofs: Any,
    selection_basis: Any,
    timeout_seconds: Any = None,
    timeout_reason: Any = None,
) -> dict[str, Any]:
    envelope = WP12_OWNER_ENVELOPES[worktree_id]
    if isinstance(selected_dofs, bool) or not isinstance(selected_dofs, int) or selected_dofs < 1:
        raise PolicyError("WP12 registration requires a positive integer selected DDL count before execution")
    dof_cap = envelope["max_dofs"]
    if dof_cap is not None and selected_dofs > dof_cap:
        raise PolicyError(f"selected DDL {selected_dofs} exceeds the {dof_cap}-DDL cap; case refused before execution")
    if (
        not isinstance(selection_basis, str)
        or not 8 <= len(selection_basis.strip()) <= 300
        or "\n" in selection_basis
        or "\r" in selection_basis
    ):
        raise PolicyError("WP12 registration requires an 8 to 300 character one-line DDL selection basis")

    default_timeout = envelope["timeout_seconds"]
    maximum_timeout = envelope["max_timeout_seconds"]
    actual_timeout = default_timeout if timeout_seconds is None else timeout_seconds
    if isinstance(actual_timeout, bool) or not isinstance(actual_timeout, int):
        raise PolicyError("WP12 timeout must be an integer number of seconds")
    if actual_timeout not in {default_timeout, maximum_timeout}:
        raise PolicyError(f"WP12 timeout must be {default_timeout} seconds by default or its registered maximum")
    normalized_timeout_reason: str | None = None
    if actual_timeout != default_timeout:
        if worktree_id != "wp12_elements" or actual_timeout != 900:
            raise PolicyError("only WP12 elements cases may request the exceptional 900-second timeout")
        if (
            not isinstance(timeout_reason, str)
            or not 20 <= len(timeout_reason.strip()) <= 300
            or "\n" in timeout_reason
            or "\r" in timeout_reason
        ):
            raise PolicyError(
                "the exceptional 900-second elements timeout requires a one-line 20 to 300 character reason"
            )
        normalized_timeout_reason = timeout_reason.strip()
    elif timeout_reason not in (None, ""):
        raise PolicyError("timeout reason is only valid for the exceptional 900-second elements budget")
    return {
        "selected_dofs": selected_dofs,
        "selection_basis": selection_basis.strip(),
        "timeout_seconds": actual_timeout,
        "timeout_reason": normalized_timeout_reason,
    }


def _validate_wp12_registration_history(worktree_id: str, entry: Mapping[str, Any]) -> None:
    nodeids = entry["allowed_nodeids"]
    records = entry.get("nodeid_registration_records", [])
    if not isinstance(records, list):
        raise PolicyError(f"{worktree_id} nodeid registration history must be a list")
    first_seen: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            raise PolicyError(f"{worktree_id} nodeid registration history contains a malformed record")
        target = record.get("target")
        if not isinstance(target, str) or target not in nodeids:
            raise PolicyError(f"{worktree_id} registration history contains an unallowlisted target")
        if record.get("campaign_id") != entry.get("campaign_id"):
            raise PolicyError(f"{worktree_id} registration history is bound to a different corrective campaign")
        if target not in first_seen:
            first_seen.append(target)
        if (
            not isinstance(record.get("reason"), str)
            or not record["reason"].strip()
            or not re.fullmatch(r"[0-9a-f]{40}", str(record.get("worktree_head", "")))
            or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("source_fingerprint", "")))
        ):
            raise PolicyError(f"{worktree_id} registration history lacks its rationale, Git head or source fingerprint")
        dependency_inventory = record.get("test_source_dependencies")
        if dependency_inventory is not None:
            if not isinstance(dependency_inventory, dict):
                raise PolicyError(f"{worktree_id} registration has a malformed test-source dependency inventory")
            for path_text, digest in dependency_inventory.items():
                path = Path(path_text) if isinstance(path_text, str) else Path(".")
                if (
                    not isinstance(path_text, str)
                    or "\\" in path_text
                    or path.is_absolute()
                    or ".." in path.parts
                    or not path.parts
                    or path.as_posix() != path_text
                    or ":" in path.parts[0]
                    or path.suffix != ".py"
                    or not isinstance(digest, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", digest)
                ):
                    raise PolicyError(f"{worktree_id} registration has an invalid test-source dependency entry")
        try:
            registered_at = datetime.fromisoformat(str(record.get("registered_at_utc", "")).replace("Z", "+00:00"))
        except ValueError as exc:
            raise PolicyError(f"{worktree_id} registration history has an invalid timestamp") from exc
        if registered_at.tzinfo is None or registered_at.utcoffset() != timezone.utc.utcoffset(registered_at):
            raise PolicyError(f"{worktree_id} registration timestamps must use UTC")
        selection = _validate_wp12_case_selection(
            worktree_id,
            selected_dofs=record.get("selected_dofs"),
            selection_basis=record.get("selection_basis"),
            timeout_seconds=record.get("timeout_seconds"),
            timeout_reason=record.get("timeout_reason"),
        )
        if any(record.get(field) != value for field, value in selection.items()):
            raise PolicyError(f"{worktree_id} registration selection metadata is not normalized")
    if first_seen != nodeids:
        raise PolicyError(f"{worktree_id} registration history must bind every exact allowlisted target")


def _validate_wp12_nodeid_syntax(target: str, *, worktree_id: str | None = None) -> re.Match[str]:
    if not isinstance(target, str) or target.count("::") != 1:
        raise PolicyError("WP12 allowlists require one exact pytest test-function nodeid")
    module_name, selector = target.split("::", maxsplit=1)
    module_path = Path(module_name)
    match = WP12_TEST_SELECTOR_RE.fullmatch(selector)
    if (
        match is None
        or module_path.is_absolute()
        or "\\" in module_name
        or ".." in module_path.parts
        or module_path.suffix != ".py"
        or not module_path.name.startswith("test_")
        or not (
            module_name.startswith("tests/unit/")
            or (worktree_id == "wp12_elements" and target in WP12_ELEMENTS_VERIFICATION_NODEIDS)
        )
        or (worktree_id == "rotor" and target not in WP12_ROTOR_NODEIDS)
    ):
        raise PolicyError(
            "WP12 target must be below tests/unit or one of the exact registered wp12_elements verification nodeids; "
            "rotor permits only its exact approved sentinel nodeids"
        )
    return match


def _wp12_nodeid_module_within_scope(
    worktree_id: str,
    target: str,
    module_file: Path,
    registered_root: Path,
    test_root: Path,
) -> bool:
    """Keep the normal tests/unit root and allow only two named element diagnostics."""
    if not _is_within(module_file, registered_root):
        return False
    if _is_within(module_file, test_root):
        return True
    if worktree_id != "wp12_elements" or target not in WP12_ELEMENTS_VERIFICATION_NODEIDS:
        return False
    requested_module = (registered_root / target.split("::", maxsplit=1)[0]).resolve()
    verification_root = (registered_root / "tests" / "verification").resolve()
    return module_file == requested_module and _is_within(module_file, verification_root)


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    if not _is_within(path.resolve(), ROOT.resolve()):
        raise PolicyError("development policy must be stored inside this worktree")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"cannot read development policy: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("schema") != "qfsolver-development-autonomous-v2":
        raise PolicyError("unsupported development policy schema")
    if policy.get("mode") != "DEVELOPMENT_AUTONOMOUS":
        raise PolicyError("this launcher only accepts DEVELOPMENT_AUTONOMOUS")
    store = Path(str(policy.get("run_store", "")))
    if store.as_posix() != ".codex/development-runs":
        raise PolicyError("run_store must be the dedicated .codex/development-runs directory")
    _positive_number(policy.get("minimum_free_disk_mib"), "minimum_free_disk_mib")
    poll = _positive_number(policy.get("poll_interval_seconds"), "poll_interval_seconds")
    if poll > 5:
        raise PolicyError("poll_interval_seconds must not exceed 5")
    if not isinstance(policy.get("mandate_id"), str) or not policy["mandate_id"].startswith("DEVELOPMENT_AUTONOMOUS-"):
        raise PolicyError("a development-only mandate ID is required")
    scopes = policy.get("standard_scopes")
    expected_roots = {"unit": "tests/unit", "integration": "tests/integration"}
    if not isinstance(scopes, dict) or set(scopes) != set(expected_roots):
        raise PolicyError("only the fixed unit and integration scopes are accepted here")
    for name, scope in scopes.items():
        if not isinstance(scope, dict):
            raise PolicyError(f"scope {name} must be an object")
        for field in (
            "timeout_seconds",
            "rss_soft_limit_mib",
            "process_tree_limit",
            "output_total_limit_mib",
            "output_stream_limit_mib",
            "temporary_limit_mib",
            "archive_size_limit_mib",
            "max_attempts_per_series",
        ):
            _positive_number(scope.get(field), f"scopes.{name}.{field}")
        for field in ("process_tree_limit", "max_attempts_per_series"):
            _positive_integer(scope.get(field), f"scopes.{name}.{field}")
        if scope.get("pytest_root") != expected_roots[name]:
            raise PolicyError(f"scope {name} is bound to its fixed repository test directory")
        if name in STANDARD_SCOPES and scope.get("markers") != "not evidence and not benchmark and not large":
            raise PolicyError(f"scope {name} must exclude controlled evidence, benchmark, and large tests")
        if scope["output_total_limit_mib"] > 2 * scope["output_stream_limit_mib"]:
            raise PolicyError(f"scope {name} total output limit exceeds its two stream limits")
    worktrees = policy.get("worktrees")
    legacy_worktree_ids = {"d01", "c01", "e01"}
    expected_worktree_ids = legacy_worktree_ids | set(WP12_OWNER_ENVELOPES) | {
        HEX8SRI_CONVERGENCE24_WORKTREE_ID,
        VV3D_WORKTREE_ID,
        VV3D_R2_WORKTREE_ID,
    }
    if not isinstance(worktrees, dict) or set(worktrees) != expected_worktree_ids:
        raise PolicyError(
            "the worktree registry must retain all existing scopes plus isolated HEX8-SRI and VV3D scopes"
        )
    required_budget_fields = (
        "timeout_seconds",
        "rss_soft_limit_mib",
        "process_tree_limit",
        "output_total_limit_mib",
        "output_stream_limit_mib",
        "temporary_limit_mib",
        "archive_size_limit_mib",
    )
    for worktree_id, entry in worktrees.items():
        if not isinstance(entry, dict):
            raise PolicyError(f"worktree {worktree_id} must be an object")
        expected_mode = "math_non_fem" if worktree_id == "e01" else "fem_exploratory"
        if entry.get("mode") != expected_mode:
            raise PolicyError(f"worktree {worktree_id} has an unauthorized execution mode")
        for field in ("root", "git_root", "branch", "baseline_commit", "source_root", "pytest_root"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise PolicyError(f"worktree {worktree_id} requires {field}")
        if not re.fullmatch(r"[0-9a-f]{40}", entry["baseline_commit"]):
            raise PolicyError(f"worktree {worktree_id} baseline_commit must be a full Git SHA-1")
        if _registered_root(entry["root"]) != _registered_root(entry["git_root"]):
            raise PolicyError(f"worktree {worktree_id} root and git_root must be identical")
        nodeids = entry.get("allowed_nodeids")
        is_wp12 = worktree_id in WP12_OWNER_ENVELOPES
        if not isinstance(nodeids, list) or (not nodeids and not is_wp12) or len(nodeids) != len(set(nodeids)):
            raise PolicyError(f"worktree {worktree_id} requires unique exact nodeids")
        if entry.get("allow_native_vv_skip_override") is not (worktree_id == "d01"):
            raise PolicyError("only exact D01 development nodes may lift their native-V&V skip")
        attempt_limit = _positive_integer(
            entry.get("attempt_limit_per_nodeid"), f"worktrees.{worktree_id}.attempt_limit_per_nodeid"
        )
        is_hex8sri_convergence24 = worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID
        is_vv3d = worktree_id == VV3D_WORKTREE_ID
        is_vv3d_r2 = worktree_id == VV3D_R2_WORKTREE_ID
        if not is_wp12 and not is_hex8sri_convergence24 and not is_vv3d and not is_vv3d_r2 and attempt_limit != 3:
            raise PolicyError("this Owner mandate permits at most three attempts per nodeid")
        if is_hex8sri_convergence24 and attempt_limit != 1:
            raise PolicyError("HEX8-SRI convergence preparation is limited to one future attempt per nodeid")
        budgets = entry.get("budgets")
        if not isinstance(budgets, dict):
            raise PolicyError(f"worktree {worktree_id} requires a budgets object")
        for field in required_budget_fields:
            _positive_number(budgets.get(field), f"worktrees.{worktree_id}.budgets.{field}")
        for field in ("process_tree_limit",):
            _positive_integer(budgets[field], f"worktrees.{worktree_id}.budgets.{field}")
        if budgets["output_total_limit_mib"] > 2 * budgets["output_stream_limit_mib"]:
            raise PolicyError(f"worktree {worktree_id} aggregate output exceeds its two stream caps")
        expected_test_root = (
            "tests/unit" if worktree_id in {"c01", "e01", VV3D_WORKTREE_ID, VV3D_R2_WORKTREE_ID, *WP12_OWNER_ENVELOPES} else "tests/verification"
        )
        if entry["pytest_root"] != expected_test_root:
            raise PolicyError(f"worktree {worktree_id} is bound to the wrong test class")
        for nodeid in nodeids:
            if not isinstance(nodeid, str) or "::" not in nodeid:
                raise PolicyError(f"worktree {worktree_id} contains a non-nodeid target")
            test_path = Path(nodeid.split("::", maxsplit=1)[0])
            exact_verification_node = worktree_id == "wp12_elements" and nodeid in WP12_ELEMENTS_VERIFICATION_NODEIDS
            if (
                test_path.is_absolute()
                or ".." in test_path.parts
                or not (nodeid.startswith(expected_test_root + "/") or exact_verification_node)
            ):
                raise PolicyError(f"worktree {worktree_id} nodeid escapes its approved test root")
            if is_wp12:
                _validate_wp12_nodeid_syntax(nodeid, worktree_id=worktree_id)
            if is_vv3d and nodeid not in VV3D_ALL_NODEIDS:
                raise PolicyError("VV3D catalogue accepts only its exact 12 initial, 8 adaptive, and 4 QPOST nodeids")
            if is_vv3d_r2 and nodeid not in VV3D_R2_NODEIDS:
                raise PolicyError("VV3D R2 accepts only its exact twelve initial FEM nodeids")
            if worktree_id == "e01" and re.search(r"(?i)(tet|hex|beam|assembly|fem)", nodeid):
                raise PolicyError("E01 allowlist may contain only non-FEM constitutive-math tests")
        if is_wp12:
            envelope = WP12_OWNER_ENVELOPES[worktree_id]
            expected_identity = {
                "root": envelope["root"],
                "git_root": envelope["root"],
                "branch": envelope["branch"],
                "baseline_commit": WP12_BASELINE_COMMIT,
                "source_root": "src",
                "pytest_root": "tests/unit",
                "mode": "fem_exploratory",
                "evidence_root": envelope["evidence_root"],
                "target_max_dofs": envelope["max_dofs"],
                "max_fem_cases_per_attempt": envelope["max_fem_cases_per_attempt"],
                "concurrency_class": envelope["concurrency_class"],
                "development_mandate_id": envelope["development_mandate_id"],
                "max_timeout_seconds": envelope["max_timeout_seconds"],
                "attempt_limit_per_nodeid": envelope["attempt_limit_per_nodeid"],
                "max_total_attempts": envelope["max_total_attempts"],
                "require_clean_worktree": True,
            }
            for campaign_field in ("campaign_id", "execution_scope_id"):
                if campaign_field in envelope:
                    expected_identity[campaign_field] = envelope[campaign_field]
            if any(entry.get(field) != expected for field, expected in expected_identity.items()):
                raise PolicyError(
                    f"{worktree_id} identity and attempt envelope must match its Owner authorization exactly"
                )
            expected_execution_scope = WP12_EXECUTION_SCOPE_ALIASES.get(worktree_id, worktree_id)
            if entry.get("execution_scope_id", worktree_id) != expected_execution_scope:
                raise PolicyError(f"{worktree_id} execution-scope identity does not match the fixed controller mapping")
            registration = entry.get("nodeid_registration")
            if registration != {"enabled": True, "max_nodeids": envelope["max_registered_nodeids"]}:
                raise PolicyError(f"{worktree_id} nodeid registration cap must match its Owner authorization")
            if len(nodeids) > envelope["max_registered_nodeids"]:
                raise PolicyError(f"{worktree_id} has more registered nodeids than its Owner cap")
            _validate_wp12_registration_history(worktree_id, entry)
            if entry.get("allow_native_vv_skip_override") is not False:
                raise PolicyError("WP12 scopes cannot override native-V&V skips")
            expected_budgets = {"timeout_seconds": envelope["timeout_seconds"], **WP12_RUN_BUDGETS}
            if budgets != expected_budgets:
                raise PolicyError(f"{worktree_id} budgets must match its Owner-approved resource envelope exactly")

    r2_ledger = worktrees[WP12B_HEX20_R2_WORKTREE_ID].get("node_attempt_ledger")
    if r2_ledger != {
        "path": "node-attempt-ledger-r2.json",
        "predecessor": {
            "path": str(WP12B_HEX20_R1_LEDGER_PATH),
            "sha256": WP12B_HEX20_R1_LEDGER_SHA256,
            "mandate_id": WP12B_HEX20_R1_MANDATE_ID,
        },
    } or worktrees[WP12B_HEX20_R2_WORKTREE_ID].get("allowed_nodeids") != [WP12B_HEX20_DIAGNOSTIC_NODEID]:
        raise PolicyError("WP12-B HEX20 R2 must retain its exact node and independent predecessor ledger")

    dynamics_ledger = worktrees["wp12_dynamics"].get("node_attempt_ledger")
    if not isinstance(dynamics_ledger, dict) or set(dynamics_ledger) != {"path", "predecessor"}:
        raise PolicyError("WP12-A dynamics requires a dedicated ledger linked to its immutable predecessor")
    predecessor = dynamics_ledger.get("predecessor")
    if (
        dynamics_ledger.get("path") != WP12_DYNAMICS_LEDGER
        or not isinstance(predecessor, dict)
        or set(predecessor) != {"path", "sha256", "mandate_id"}
        or predecessor.get("path") != "node-attempt-ledger.json"
        or not isinstance(predecessor.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", predecessor["sha256"])
        or predecessor.get("mandate_id") != WP12_DYNAMICS_LEGACY_MANDATE_ID
    ):
        raise PolicyError("WP12-A dynamics ledger path or historical predecessor identity is invalid")

    hex8sri = worktrees[HEX8SRI_CONVERGENCE24_WORKTREE_ID]
    hex8sri_nodeids = _hex8sri_convergence24_nodeids()
    if (
        hex8sri.get("development_mandate_id") != HEX8SRI_CONVERGENCE24_MANDATE_ID
        or hex8sri.get("campaign_id") != HEX8SRI_CONVERGENCE24_CAMPAIGN_ID
        or hex8sri.get("campaign_scope_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        or hex8sri.get("execution_authorized") is not False
        or hex8sri.get("require_clean_worktree") is not True
        or hex8sri.get("branch") != HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY["branch"]
        or hex8sri.get("root") != r"E:\QFSolverAgents\hex8-sri-research"
        or hex8sri.get("git_root") != hex8sri.get("root")
        or hex8sri.get("baseline_commit") != "b547cf0e1c8057ef7f58ba780967d1b19c891ac4"
        or hex8sri.get("source_fingerprint_sha256") != HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT
        or hex8sri.get("source_identity") != HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY
        or hex8sri.get("source_test_worktree_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        or hex8sri.get("manifest_registration_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        or hex8sri.get("manifest_binding_mode") != HEX8SRI_CONVERGENCE24_MANIFEST_BINDING
        or hex8sri.get("allowed_nodeids") != list(hex8sri_nodeids)
        or hex8sri.get("attempt_limit_per_nodeid") != 1
        or hex8sri.get("max_total_attempts") != 24
        or hex8sri.get("node_attempt_ledger") != {"path": HEX8SRI_CONVERGENCE24_LEDGER}
    ):
        raise PolicyError(
            "HEX8-SRI convergence scope identity, nodeids, ledger, or preparation-only mandate is invalid"
        )
    expected_hex8sri_budgets = {
        **HEX8SRI_CONVERGENCE24_COMMON_BUDGET,
        "timeout_seconds": 3600,
        "rss_soft_limit_mib": 16384,
    }
    if hex8sri.get("budgets") != expected_hex8sri_budgets:
        raise PolicyError("HEX8-SRI convergence shared budget must equal the largest registered case budget")
    expected_per_node_budgets = {nodeid: _hex8sri_convergence24_budget(nodeid) for nodeid in hex8sri_nodeids}
    if hex8sri.get("per_node_budgets") != expected_per_node_budgets:
        raise PolicyError("HEX8-SRI per-node budgets must match the exact four-mesh envelope")
    expected_threads = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
    if hex8sri.get("blas_thread_environment") != expected_threads:
        raise PolicyError("HEX8-SRI convergence requires the registered single-thread BLAS environment")
    case_manifests = hex8sri.get("case_manifests")
    if not isinstance(case_manifests, dict) or set(case_manifests) != set(hex8sri_nodeids):
        raise PolicyError("HEX8-SRI convergence requires exactly one case manifest per registered nodeid")
    for nodeid, binding in case_manifests.items():
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
            raise PolicyError("HEX8-SRI case manifest binding has an invalid shape")
        manifest_path = Path(str(binding.get("path", "")))
        if (
            manifest_path.is_absolute()
            or ".." in manifest_path.parts
            or not str(binding.get("path", "")).startswith((
                "investigations/hex8_sri_equilibrium_20261026/campaign_preparation/first_convergence_24/",
            ))
            or not re.fullmatch(r"[0-9a-f]{64}", str(binding.get("sha256", "")))
        ):
            raise PolicyError(f"HEX8-SRI case manifest binding is invalid for {nodeid}")
    vv3d = worktrees[VV3D_WORKTREE_ID]
    expected_vv3d_budget = {
        "timeout_seconds": 1200,
        "rss_soft_limit_mib": 4096,
        "process_tree_limit": 32,
        "output_total_limit_mib": 64,
        "output_stream_limit_mib": 32,
        "temporary_limit_mib": 1024,
        "archive_size_limit_mib": 256,
    }
    if (
        vv3d.get("campaign_id") != "WP12-VV3D-ADAPTIVE-20261029-R1"
        or vv3d.get("development_mandate_id") != "DEVELOPMENT_AUTONOMOUS-WP12-VV3D-ADAPTIVE-2026-10-29-R1"
        or vv3d.get("execution_authorized") is not False
        or vv3d.get("execution_capability") != "INITIAL_AND_CLOSED_CATALOG_ADAPTIVE_FEM_AND_QPOST_RUNNER_PATHS"
        or vv3d.get("runner_capabilities") != {"initial_fem": True, "adaptive_fem": True, "qpost": True}
        or vv3d.get("root") != r"C:\Users\fari\.codex\worktrees\wp12-vv3d-adaptive\qf_solver"
        or vv3d.get("git_root") != vv3d.get("root")
        or vv3d.get("branch") != "emptiesvoids-cloud/research-wp12-vv3d-adaptive"
        or vv3d.get("baseline_commit") != "b4ac817cdb565c45f8f8d92a9c10bbb609f6df37"
        or vv3d.get("source_root") != "src"
        or vv3d.get("pytest_root") != "tests/unit"
        or vv3d.get("evidence_root") != r"E:\QFSolverAgents\evidence\wp12-vv3d-adaptive"
        or vv3d.get("require_clean_worktree") is not True
        or vv3d.get("allow_native_vv_skip_override") is not False
        or vv3d.get("attempt_limit_per_nodeid") != 1
        or vv3d.get("max_total_attempts") != 24
        or vv3d.get("max_total_seconds") != 28800
        or vv3d.get("max_timeout_seconds") != 1200
        or vv3d.get("target_max_dofs") != 30000
        or vv3d.get("rss_soft_limit_mib") != 4096
        or vv3d.get("concurrency_class") != "vv3d_serial"
        or vv3d.get("nodeid_registration") != {"enabled": False, "max_nodeids": 24}
        or vv3d.get("budgets") != expected_vv3d_budget
        or vv3d.get("allowed_nodeids") != list(VV3D_ALL_NODEIDS)
        or vv3d.get("adaptive_fem_nodeids") != list(VV3D_ADAPTIVE_FEM_NODEIDS)
        or vv3d.get("qpost_nodeids") != list(VV3D_QPOST_NODEIDS)
        or vv3d.get("per_node_selected_dofs") != VV3D_ALL_DOFS
        or vv3d.get("node_attempt_ledger") != {"path": "node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl"}
    ):
        raise PolicyError("VV3D must retain its exact catalogue, pending Owner gate, supported runner capability map, and budgets")
    vv3d_r2 = worktrees[VV3D_R2_WORKTREE_ID]
    r2_expected_budgets = {
        "timeout_seconds": 1200,
        "rss_soft_limit_mib": 4096,
        "process_tree_limit": 32,
        "output_total_limit_mib": 64,
        "output_stream_limit_mib": 32,
        "temporary_limit_mib": 1024,
        "archive_size_limit_mib": 256,
    }
    r2_predecessor = {
        "path": str(VV3D_R1_LEDGER_PATH),
        "sha256": VV3D_R1_LEDGER_SHA256,
        "mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-VV3D-ADAPTIVE-2026-10-29-R1",
    }
    if (
        vv3d_r2.get("campaign_id") != VV3D_R2_CAMPAIGN_ID
        or vv3d_r2.get("development_mandate_id") != VV3D_R2_MANDATE_ID
        or vv3d_r2.get("execution_authorized") is not False
        or vv3d_r2.get("execution_capability") != "INITIAL_FEM_ONLY_WITH_EXACT_R2_OWNER_DECISION"
        or vv3d_r2.get("runner_capabilities") != {"initial_fem": True, "adaptive_fem": False, "qpost": False}
        or vv3d_r2.get("root") != str(VV3D_R2_SOURCE_ROOT)
        or vv3d_r2.get("git_root") != str(VV3D_R2_SOURCE_ROOT)
        or vv3d_r2.get("branch") != VV3D_R2_SOURCE_IDENTITY["branch"]
        or vv3d_r2.get("baseline_commit") != "34812fc7525859686f88ac7e56e1833ee558cb66"
        or vv3d_r2.get("source_root") != "src"
        or vv3d_r2.get("pytest_root") != "tests/unit"
        or vv3d_r2.get("evidence_root") != str(VV3D_R2_EVIDENCE_ROOT)
        or vv3d_r2.get("allow_native_vv_skip_override") is not False
        or vv3d_r2.get("require_clean_worktree") is not True
        or vv3d_r2.get("attempt_limit_per_nodeid") != 1
        or vv3d_r2.get("max_r2_attempts") != 12
        or vv3d_r2.get("max_total_attempts") != 24
        or vv3d_r2.get("max_total_seconds") != 28800
        or vv3d_r2.get("max_timeout_seconds") != 1200
        or vv3d_r2.get("target_max_dofs") != 30000
        or vv3d_r2.get("rss_soft_limit_mib") != 4096
        or vv3d_r2.get("concurrency_class") != "vv3d_serial"
        or vv3d_r2.get("nodeid_registration") != {"enabled": False, "max_nodeids": 12}
        or vv3d_r2.get("budgets") != r2_expected_budgets
        or vv3d_r2.get("allowed_nodeids") != list(VV3D_R2_NODEIDS)
        or vv3d_r2.get("adaptive_fem_nodeids") != []
        or vv3d_r2.get("qpost_nodeids") != []
        or vv3d_r2.get("per_node_selected_dofs") != {
            nodeid: VV3D_INITIAL_DOFS[nodeid.rsplit("[", maxsplit=1)[-1][:-1]]
            for nodeid in VV3D_R2_NODEIDS
        }
        or vv3d_r2.get("source_identity") != VV3D_R2_SOURCE_IDENTITY
        or vv3d_r2.get("source_fingerprint_sha256") != VV3D_R2_SOURCE_IDENTITY["fingerprint_sha256"]
        or vv3d_r2.get("node_attempt_ledger") != {
            "path": VV3D_R2_LEDGER_FILENAME,
            "predecessor": r2_predecessor,
        }
    ):
        raise PolicyError("VV3D R2 scope identity, closed node set, independent ledger or limits are invalid")
    if policy.get("resource_coordination_root") != str(WP12_COORDINATION_ROOT):
        raise PolicyError("WP12 runs must use the one registered shared resource coordination root")
    d01 = worktrees["d01"]
    d01_budgets = d01["budgets"]
    if any(
        type(d01_budgets.get(field)) is not int or d01_budgets[field] != expected
        for field, expected in D01_OWNER_BUDGETS.items()
    ):
        raise PolicyError("D01 timeout, soft RSS, and aggregate-output budgets must match the Owner envelope exactly")
    if d01["allowed_nodeids"] != list(D01_NATIVE_NODEIDS):
        raise PolicyError("D01 development permission is limited to the exact M1/M2/M3 diagnostic nodes")
    if d01.get("attempt_limits_per_nodeid") != {
        D01_NATIVE_NODEIDS[0]: 1,
        D01_NATIVE_NODEIDS[1]: 1,
        D01_NATIVE_NODEIDS[2]: 3,
    }:
        raise PolicyError("D01 per-nodeid attempt limits must match the new Owner envelope exactly")
    if d01.get("development_mandate_id") != "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v2-d01":
        raise PolicyError("D01 requires its distinct, development-only v2 mandate")
    if d01.get("require_clean_worktree") is not True:
        raise PolicyError("D01 requires a clean source worktree")
    ledger_config = d01.get("node_attempt_ledger")
    if not isinstance(ledger_config, dict) or set(ledger_config) != {"path", "predecessor"}:
        raise PolicyError("D01 requires a separate ledger linked to its immutable predecessor")
    ledger_path = ledger_config.get("path")
    if not isinstance(ledger_path, str) or not re.fullmatch(r"node-attempt-ledger-d01-v2\.json", ledger_path):
        raise PolicyError("D01 v2 ledger path must be the fixed mandate-specific filename")
    predecessor = ledger_config.get("predecessor")
    if (
        not isinstance(predecessor, dict)
        or set(predecessor) != {"path", "sha256", "mandate_id"}
        or predecessor.get("path") != "node-attempt-ledger.json"
        or not isinstance(predecessor.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", predecessor["sha256"])
        or predecessor.get("mandate_id") != policy["mandate_id"]
    ):
        raise PolicyError("D01 v2 predecessor ledger identity is invalid")
    return policy


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_targets(
    scope_name: str,
    target: str | None,
    policy: Mapping[str, Any],
    *,
    worktree_id: str | None = None,
) -> list[str]:
    if scope_name in WORKTREE_SCOPES:
        if worktree_id not in policy["worktrees"]:
            raise PolicyError("a registered worktree ID is required for this scope")
        entry = policy["worktrees"][worktree_id]
        if entry["mode"] != scope_name:
            raise PolicyError(f"worktree {worktree_id} is not authorized for {scope_name}")
        if not target or target not in entry["allowed_nodeids"]:
            raise PolicyError("target must be one exact nodeid in the registered worktree allowlist")
        path_text = target.split("::", maxsplit=1)[0]
        registered_root = _registered_root(entry["root"])
        candidate = (registered_root / path_text).resolve()
        scope_root = (registered_root / entry["pytest_root"]).resolve()
        if (
            not _wp12_nodeid_module_within_scope(worktree_id, target, candidate, registered_root, scope_root)
            or not candidate.is_file()
        ):
            raise PolicyError("registered nodeid resolves outside its canonical worktree test scope")
        return [target]

    if scope_name not in STANDARD_SCOPES:
        raise PolicyError(f"unsupported development scope: {scope_name}")
    if worktree_id is not None:
        raise PolicyError("standard local scopes do not accept an external worktree ID")
    scope = policy["standard_scopes"][scope_name]
    scope_root = (ROOT / scope["pytest_root"]).resolve()
    if target is None:
        raise PolicyError(
            "standard development scopes require one explicit test function; broad suites are not auto-enabled"
        )
    if "::" not in target or not target.rsplit("::", maxsplit=1)[-1].startswith("test_"):
        raise PolicyError("standard development scopes require one exact pytest test-function nodeid")
    path_text = target.split("::", maxsplit=1)[0]
    relative = Path(path_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise PolicyError("test target must be repository-relative and cannot traverse parents")
    candidate = (ROOT / relative).resolve()
    if (
        not _is_within(candidate, scope_root)
        or not candidate.is_file()
        or candidate.suffix != ".py"
        or not candidate.name.startswith("test_")
    ):
        raise PolicyError(f"target must be a test module below {scope['pytest_root']}")
    return [target]


def _verify_solver_import_origin(source_root: Path, imported_file: Path) -> Path:
    expected = (source_root.resolve() / "solveur" / "__init__.py").resolve()
    actual = Path(imported_file).resolve()
    if actual != expected:
        raise PolicyError(f"wrong solveur import origin: expected {expected}, got {actual}")
    return actual


def _observed_solver_origin(output: str) -> str | None:
    prefix = "QF_DEV_SOLVER_ORIGIN="
    lines = [line[len(prefix) :] for line in output.splitlines() if line.startswith(prefix)]
    return lines[0] if len(lines) == 1 else None


def _wp12_active_registration(
    worktree_id: str,
    target: str,
    entry: Mapping[str, Any],
    source_fingerprint: str,
) -> dict[str, Any]:
    records = entry.get("nodeid_registration_records", [])
    active = next(
        (record for record in reversed(records) if record.get("target") == target),
        None,
    )
    if active is None:
        raise PolicyError("WP12 nodeid has no inspected registration record")
    if active.get("source_fingerprint") != source_fingerprint:
        raise PolicyError(
            "WP12 source fingerprint changed; inspect and register the exact nodeid revision before execution"
        )
    current_dependencies = _test_source_dependency_inventory(
        _registered_root(str(entry["git_root"]), strict=True), target.split("::", maxsplit=1)[0]
    )
    recorded_dependencies = active.get("test_source_dependencies")
    if (current_dependencies and recorded_dependencies != current_dependencies) or (
        recorded_dependencies is not None and recorded_dependencies != current_dependencies
    ):
        raise PolicyError(
            "WP12 test-source dependency inventory changed or is missing; inspect and register the exact nodeid revision"
        )
    selection = _validate_wp12_case_selection(
        worktree_id,
        selected_dofs=active.get("selected_dofs"),
        selection_basis=active.get("selection_basis"),
        timeout_seconds=active.get("timeout_seconds"),
        timeout_reason=active.get("timeout_reason"),
    )
    return {**active, **selection}


def _wp12_manifest_limits(entry: Mapping[str, Any], selection: Mapping[str, Any]) -> dict[str, Any]:
    budgets = dict(entry["budgets"])
    budgets["timeout_seconds"] = selection["timeout_seconds"]
    return {
        **budgets,
        "max_total_attempts": entry["max_total_attempts"],
        "attempt_limit_per_nodeid": entry["attempt_limit_per_nodeid"],
        "max_fem_cases_per_attempt": entry["max_fem_cases_per_attempt"],
        "target_max_dofs": entry["target_max_dofs"],
        "selected_dofs": selection["selected_dofs"],
        "selection_basis": selection["selection_basis"],
        "timeout_reason": selection["timeout_reason"],
    }


def _validate_wp12_execution_manifest(
    manifest_path: Path,
    *,
    worktree_id: str,
    target: str,
    entry: Mapping[str, Any],
    identity: Mapping[str, Any],
    source_fingerprint: str,
    controller_fingerprint: str,
    selection: Mapping[str, Any],
    preflight_id: str | None = None,
    preflight_receipt: tuple[Path, str] | None = None,
    batch_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_root = Path(entry["evidence_root"]).resolve()
    authorization_root = (evidence_root / "authorizations" / worktree_id).resolve()
    try:
        path = manifest_path.resolve(strict=True)
    except OSError as exc:
        raise PolicyError(f"WP12 execution manifest is missing: {exc}") from exc
    if not _is_within(path, authorization_root) or not path.is_file():
        raise PolicyError("WP12 execution manifest must be a file in this mission's evidence authorization directory")
    try:
        manifest = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyError(f"WP12 execution manifest is unreadable or not strict JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PolicyError("WP12 execution manifest must be a JSON object")
    decision = manifest.get("owner_decision")
    if (
        manifest.get("schema") != "qfsolver-wp12-development-execution-v1"
        or manifest.get("state") != "OWNER_AUTHORIZED"
        or not isinstance(manifest.get("authorization_id"), str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", manifest["authorization_id"])
        or not isinstance(decision, dict)
        or decision.get("status") != "APPROVED"
        or decision.get("approved_by") != "Owner"
        or not isinstance(decision.get("approved_at_utc"), str)
        or not isinstance(decision.get("reason"), str)
        or len(decision["reason"].strip()) < 20
    ):
        raise PolicyError("WP12 execution manifest lacks a distinct, explicit Owner decision")
    try:
        decision_time = datetime.fromisoformat(decision["approved_at_utc"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise PolicyError("WP12 Owner approval time must be an ISO-8601 timestamp") from exc
    if decision_time.tzinfo is None or decision_time.utcoffset() != timezone.utc.utcoffset(decision_time):
        raise PolicyError("WP12 Owner approval time must be expressed in UTC")
    if (
        manifest.get("worktree_id") != worktree_id
        or manifest.get("mandate_id") != entry.get("development_mandate_id")
        or manifest.get("campaign_id") != entry.get("campaign_id")
        or manifest.get("target") != target
        or manifest.get("identity") != dict(identity)
        or manifest.get("source_fingerprint") != source_fingerprint
        or manifest.get("controller_fingerprint") != controller_fingerprint
        or manifest.get("limits") != _wp12_manifest_limits(entry, selection)
    ):
        raise PolicyError(
            "WP12 execution manifest does not bind this exact worktree, source, nodeid, controller and budget"
        )
    if worktree_id in {"wp12_dynamics", WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID, WP12B_HEX20_R2_WORKTREE_ID}:
        decision_id = decision.get("decision_id")
        if not isinstance(decision_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", decision_id):
            raise PolicyError(f"{worktree_id} Owner decision requires a valid decision_id")
    if worktree_id == "wp12_dynamics":
        if manifest.get("execution_authorized") is not True or manifest.get("do_not_execute") is not False:
            raise PolicyError("WP12-A execution manifest has inconsistent explicit authorization flags")
    if worktree_id == "wp12_dynamics":
        expected_preflight = (
            {
                "preflight_id": preflight_id,
                "receipt_path": str(preflight_receipt[0]),
                "receipt_sha256": preflight_receipt[1],
            }
            if preflight_id is not None and preflight_receipt is not None
            else None
        )
        if expected_preflight is None or manifest.get("preflight") != expected_preflight:
            raise PolicyError("WP12-A execution manifest does not bind its successful exact-node preflight receipt")
        recorded_batch = manifest.get("batch_authorization")
        if batch_binding is None:
            if recorded_batch is not None:
                raise PolicyError("a batch-authorized manifest requires the official batch execution path")
        else:
            batch_fields = {
                "campaign_id", "contract_path", "contract_sha256", "decision_path", "decision_id",
                "decision_sha256", "case_ordinal", "nodeid", "case_manifest_path", "case_manifest_sha256",
                "preflight_id", "preflight_receipt_sha256", "authorization_id", "prepared_manifest_path",
                "prepared_manifest_sha256",
            }
            if (
                worktree_id != "wp12_dynamics"
                or not isinstance(recorded_batch, Mapping)
                or set(recorded_batch) != batch_fields
                or set(batch_binding) != batch_fields
                or dict(recorded_batch) != dict(batch_binding)
                or decision.get("decision_id") != batch_binding.get("decision_id")
                or batch_binding.get("nodeid") != target
                or not isinstance(batch_binding.get("campaign_id"), str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", batch_binding["campaign_id"])
                or not isinstance(batch_binding.get("case_ordinal"), int)
                or batch_binding["case_ordinal"] < 1
                or batch_binding.get("authorization_id") != manifest.get("authorization_id")
                or batch_binding.get("preflight_id") != preflight_id
                or batch_binding.get("preflight_receipt_sha256") != preflight_receipt[1]
            ):
                raise PolicyError("WP12-A execution manifest does not bind the exact approved batch case")
            batch_root = authorization_root / "batches" / str(batch_binding["campaign_id"])
            bound_paths = (
                ("contract_path", "contract.json", batch_root, batch_binding["contract_sha256"]),
                ("decision_path", "owner-decision.json", batch_root, batch_binding["decision_sha256"]),
                ("prepared_manifest_path", f"{manifest['authorization_id']}.json", authorization_root,
                 batch_binding["prepared_manifest_sha256"]),
            )
            for path_key, expected_name, root, expected_sha in bound_paths:
                try:
                    bound_path = Path(str(batch_binding[path_key])).resolve(strict=True)
                except OSError as exc:
                    raise PolicyError(f"WP12-A batch-bound {path_key} is missing") from exc
                if (
                    bound_path.name != expected_name
                    or not _is_within(bound_path, root.resolve())
                    or not bound_path.is_file()
                    or not re.fullmatch(r"[0-9a-f]{64}", str(expected_sha))
                    or _sha256(bound_path) != expected_sha
                ):
                    raise PolicyError(f"WP12-A batch-bound {path_key} identity or SHA-256 changed")
            try:
                case_path = Path(str(batch_binding["case_manifest_path"])).resolve(strict=True)
            except OSError as exc:
                raise PolicyError("WP12-A batch case manifest is missing") from exc
            if (
                not _is_within(case_path, ROOT.resolve())
                or not case_path.is_file()
                or not re.fullmatch(r"[0-9a-f]{64}", str(batch_binding["case_manifest_sha256"]))
                or _sha256(case_path) != batch_binding["case_manifest_sha256"]
            ):
                raise PolicyError("WP12-A batch case manifest identity or SHA-256 changed")
            case_payload = _read_strict_json(case_path)
            if not isinstance(case_payload, Mapping) or case_payload.get("nodeid") != target:
                raise PolicyError("WP12-A batch case manifest does not contain the exact execution nodeid")
    elif worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
        expected_preflight = (
            {"preflight_id": preflight_id, "receipt_path": str(preflight_receipt[0]),
             "receipt_sha256": preflight_receipt[1]}
            if preflight_id is not None and preflight_receipt is not None else None
        )
        if (manifest.get("execution_authorized") is not True or manifest.get("do_not_execute") is not False
                or manifest.get("scientific_criteria") != WP12B_HEX20_R2_CRITERIA
                or expected_preflight is None or manifest.get("preflight") != expected_preflight):
            raise PolicyError("WP12-B R2 execution requires its exact authorized preflight binding")
    elif manifest.get("preflight") is not None:
        raise PolicyError("only WP12-A dynamics manifests may bind a collect-only preflight receipt")
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "authorization_id": manifest["authorization_id"],
        "decision_id": decision.get("decision_id"),
        "mandate_id": manifest["mandate_id"],
        "owner_decision": decision,
    }


def _validate_wp12b_decision_receipt(receipt: Mapping[str, Any]) -> None:
    """Reject a missing or inconsistent decision before any HEX20 reservation."""
    decision = receipt.get("owner_decision")
    decision_id = receipt.get("decision_id")
    if (
        not isinstance(decision, Mapping)
        or not isinstance(decision_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", decision_id)
        or decision.get("decision_id") != decision_id
    ):
        raise PolicyError("WP12-B HEX20 Owner decision receipt has a missing or inconsistent decision_id")


def build_pytest_command(
    scope_name: str,
    targets: Sequence[str],
    temp_dir: Path,
    *,
    repository_root: Path = ROOT,
    source_root: Path | None = None,
    controller_root: Path = ROOT,
    allow_native_skip_override: bool = False,
    collect_only: bool = False,
    rotor_collect_only_attestation: bool = False,
    hex8sri_convergence24_collect_only_attestation: bool = False,
    vv3d_collect_only_attestation: bool = False,
    vv3d_r2_collect_only_attestation: bool = False,
    wp12_dynamics_collect_only_attestation: bool = False,
    wp12b_hex20_diagnostic_collect_only_attestation: bool = False,
    junit_xml_path: Path | None = None,
) -> list[str]:
    attestation_modes = (
        rotor_collect_only_attestation,
        hex8sri_convergence24_collect_only_attestation,
        vv3d_collect_only_attestation,
        vv3d_r2_collect_only_attestation,
        wp12_dynamics_collect_only_attestation,
        wp12b_hex20_diagnostic_collect_only_attestation,
    )
    if sum(attestation_modes) > 1:
        raise PolicyError("a pytest collection command may use only one scope attestor")
    if scope_name in WORKTREE_SCOPES:
        if len(targets) != 1 or source_root is None:
            raise PolicyError("registered worktree execution requires one exact nodeid and a source root")
        if rotor_collect_only_attestation and (not collect_only or allow_native_skip_override):
            raise PolicyError("rotor collection attestation requires collect-only without any skip override")
        if rotor_collect_only_attestation and targets[0] not in WP12_ROTOR_NODEIDS:
            raise PolicyError("rotor collection attestation is restricted to the exact rotor nodeid allowlist")
        if hex8sri_convergence24_collect_only_attestation and (
            not collect_only or allow_native_skip_override or targets[0] not in _hex8sri_convergence24_nodeids()
        ):
            raise PolicyError("HEX8-SRI attestation is restricted to exact preparation-only collect-only nodes")
        if vv3d_collect_only_attestation and (
            not collect_only or allow_native_skip_override or targets[0] not in VV3D_ALL_NODEIDS
        ):
            raise PolicyError("VV3D attestation is restricted to exact skip-free collect-only catalog nodes")
        if vv3d_r2_collect_only_attestation and (
            not collect_only or allow_native_skip_override or targets[0] not in VV3D_R2_NODEIDS
        ):
            raise PolicyError("VV3D R2 attestation is restricted to its exact twelve skip-free collect-only nodes")
        if wp12_dynamics_collect_only_attestation and (not collect_only or allow_native_skip_override):
            raise PolicyError("WP12 dynamics attestation requires collect-only without any skip override")
        if wp12_dynamics_collect_only_attestation and targets[0] not in WP12_DYNAMICS_PREFLIGHT_NODEIDS:
            raise PolicyError("WP12-A dynamics attestation is restricted to its reviewed exact collect-only nodeids")
        if wp12b_hex20_diagnostic_collect_only_attestation and (
            not collect_only
            or allow_native_skip_override
            or len(targets) != 1
            or targets[0] != WP12B_HEX20_DIAGNOSTIC_NODEID
        ):
            raise PolicyError(
                "HEX20 diagnostic attestation requires collect-only for its one exact nodeid without a skip override"
            )
        native_override = "True" if allow_native_skip_override else "False"
        bootstrap = "\n".join(
            (
                "from pathlib import Path",
                "import os",
                "import sys",
                "src = Path(sys.argv[1]).resolve()",
                "root = Path(sys.argv[2]).resolve()",
                "controller = Path(sys.argv[3]).resolve()",
                "mode = sys.argv[4]",
                "target = sys.argv[5]",
                "sys.path.insert(0, str(src))",
                "sys.path.insert(0, str(controller / 'scripts'))",
                "import solveur",
                "origin = Path(solveur.__file__).resolve()",
                "print('QF_DEV_SOLVER_ORIGIN=' + str(origin))",
                "from development_autonomous import PolicyError, _verify_solver_import_origin",
                "try:",
                "    _verify_solver_import_origin(src, origin)",
                "except PolicyError as exc:",
                "    raise SystemExit(str(exc))",
                "import pytest",
                "from development_autonomous_pytest_plugin import ExactNodeGate",
                f"gate = ExactNodeGate((target,), allow_native_skip_override=(mode == 'd01' and {native_override}))",
                "plugins = [gate]",
                "if mode == 'rotor-preflight':",
                "    from development_autonomous_pytest_plugin import ExactCollectOnlyAttestor",
                "    attestor = ExactCollectOnlyAttestor(",
                "        target, solver_origin=str(origin),",
                "        selected_dofs=int(os.environ['QF_DEV_SELECTED_DOFS']),",
                "        max_dofs=int(os.environ['QF_DEV_MAX_DOFS']),",
                "    )",
                "    plugins.append(attestor)",
                "if mode == 'hex8sri-convergence24-preflight':",
                "    from development_autonomous_pytest_plugin import Hex8SRIConvergence24Attestor",
                "    plugins.append(Hex8SRIConvergence24Attestor(target, scope_id='hex8sri-convergence24'))",
                "if mode == 'vv3d-preflight':",
                "    from development_autonomous_pytest_plugin import VV3DCollectOnlyAttestor",
                "    plugins.append(VV3DCollectOnlyAttestor(target, scope_id='wp12_vv3d_adaptive'))",
                "if mode == 'vv3d-r2-preflight':",
                "    from development_autonomous_pytest_plugin import VV3DCollectOnlyAttestor",
                "    plugins.append(VV3DCollectOnlyAttestor(target, scope_id='wp12_vv3d_recovery_r2'))",
                "if mode == 'wp12-dynamics-preflight':",
                "    from development_autonomous_pytest_plugin import ExactCollectOnlyAttestor",
                "    attestor = ExactCollectOnlyAttestor(",
                "        target, solver_origin=str(origin), selected_dofs=int(os.environ['QF_DEV_SELECTED_DOFS']),",
                "        max_dofs=None, schema='qfsolver-wp12-dynamics-collect-only-v1',",
                "        marker='QF_DEV_WP12_DYNAMICS_PREFLIGHT=',",
                "    )",
                "    plugins.append(attestor)",
                "if mode == 'wp12b-hex20-diagnostic-preflight':",
                "    from development_autonomous_pytest_plugin import ExactCollectOnlyAttestor",
                "    attestor = ExactCollectOnlyAttestor(",
                "        target, solver_origin=str(origin), selected_dofs=int(os.environ['QF_DEV_SELECTED_DOFS']),",
                "        max_dofs=60, schema='qfsolver-wp12b-hex20-diagnostic-collect-only-v1',",
                "        marker='QF_DEV_WP12B_HEX20_DIAGNOSTIC_PREFLIGHT=',",
                "    )",
                "    plugins.append(attestor)",
                "raise SystemExit(pytest.main(sys.argv[6:], plugins=plugins))",
            )
        )
        if allow_native_skip_override:
            bootstrap_mode = "d01"
        elif rotor_collect_only_attestation:
            bootstrap_mode = "rotor-preflight"
        elif hex8sri_convergence24_collect_only_attestation:
            bootstrap_mode = "hex8sri-convergence24-preflight"
        elif vv3d_collect_only_attestation:
            bootstrap_mode = "vv3d-preflight"
        elif vv3d_r2_collect_only_attestation:
            bootstrap_mode = "vv3d-r2-preflight"
        elif wp12_dynamics_collect_only_attestation:
            bootstrap_mode = "wp12-dynamics-preflight"
        elif wp12b_hex20_diagnostic_collect_only_attestation:
            bootstrap_mode = "wp12b-hex20-diagnostic-preflight"
        else:
            bootstrap_mode = "registered"
        command = [
            sys.executable,
            "-B",
            "-c",
            bootstrap,
            str(source_root),
            str(repository_root),
            str(controller_root),
            bootstrap_mode,
            targets[0],
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(temp_dir),
        ]
        if collect_only:
            command.append("--collect-only")
        if junit_xml_path is not None:
            command.append(f"--junitxml={junit_xml_path.resolve()}")
        command.append(targets[0])
        return command
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--basetemp",
        str(temp_dir),
    ]
    if scope_name in STANDARD_SCOPES:
        command.extend(["-m", "not evidence and not benchmark and not large"])
    if collect_only:
        command.append("--collect-only")
    if junit_xml_path is not None:
        command.append(f"--junitxml={junit_xml_path.resolve()}")
    command.extend(targets)
    return command


def build_child_environment(
    temp_dir: Path,
    base: Mapping[str, str] | None = None,
    *,
    source_root: Path | None = None,
    d01_source_sha: str | None = None,
    wp12_entry: Mapping[str, Any] | None = None,
    wp12_selection: Mapping[str, Any] | None = None,
    wp12_attempt_id: str | None = None,
    wp12_manifest_receipt: Mapping[str, Any] | None = None,
    wp12_run_json_path: Path | None = None,
) -> dict[str, str]:
    environment = dict(os.environ if base is None else base)
    for key in tuple(environment):
        if key in OWNER_ENV_KEYS or (key.startswith("QF_") and ("OWNER" in key or "QUALIFICATION" in key)):
            environment.pop(key, None)
        elif key.startswith("QF_DEV_"):
            environment.pop(key, None)
    environment.pop("PYTEST_ADDOPTS", None)
    environment.pop("PYTEST_PLUGINS", None)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONSTARTUP", None)
    environment["QF_SOLVER_RUN_EVIDENCE"] = "0"
    environment["QF_SOLVER_RUN_RECOVERED_EVIDENCE"] = "0"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["TMP"] = str(temp_dir)
    environment["TEMP"] = str(temp_dir)
    environment["TMPDIR"] = str(temp_dir)
    if source_root is not None:
        environment["PYTHONPATH"] = str(source_root)
    if d01_source_sha is not None:
        environment["QF_WP_D01_BJ_SOURCE_SHA"] = d01_source_sha
    if wp12_entry is not None:
        registered_worktree_id = str(wp12_entry["worktree_id"])
        execution_scope_id = WP12_EXECUTION_SCOPE_ALIASES.get(registered_worktree_id, registered_worktree_id)
        if wp12_entry.get("execution_scope_id", registered_worktree_id) != execution_scope_id:
            raise PolicyError("registered WP12 execution-scope identity is inconsistent")
        environment["QF_DEV_WORKTREE_ID"] = execution_scope_id
        environment["QF_DEV_MAX_FEM_CASES"] = str(wp12_entry["max_fem_cases_per_attempt"])
        evidence_root = wp12_entry.get("evidence_root")
        if not isinstance(evidence_root, str) or not evidence_root:
            raise PolicyError("registered WP12 child environment requires its evidence root")
        environment["QF_DEV_EVIDENCE_ROOT"] = str(Path(evidence_root).resolve())
        if wp12_entry.get("target_max_dofs") is not None:
            environment["QF_DEV_MAX_DOFS"] = str(wp12_entry["target_max_dofs"])
    if wp12_selection is not None:
        environment["QF_DEV_SELECTED_DOFS"] = str(wp12_selection["selected_dofs"])
    provenance_parts = (wp12_attempt_id, wp12_manifest_receipt, wp12_run_json_path)
    if any(part is not None for part in provenance_parts):
        if not all(part is not None for part in provenance_parts):
            raise PolicyError("WP12 diagnostic provenance requires attempt, manifest and run.json identities together")
        assert wp12_attempt_id is not None and wp12_manifest_receipt is not None and wp12_run_json_path is not None
        manifest_id = wp12_manifest_receipt.get("authorization_id")
        manifest_sha256 = wp12_manifest_receipt.get("sha256")
        if (
            not isinstance(manifest_id, str)
            or not isinstance(manifest_sha256, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", manifest_id)
            or not re.fullmatch(r"[a-f0-9]{64}", manifest_sha256)
            or not re.fullmatch(r"dev-[a-z0-9][a-z0-9-]{7,48}-attempt-[1-9][0-9]*", wp12_attempt_id)
        ):
            raise PolicyError("WP12 diagnostic provenance identities are malformed")
        environment["QF_DEV_ATTEMPT_ID"] = wp12_attempt_id
        environment["QF_DEV_MANIFEST_ID"] = manifest_id
        environment["QF_DEV_MANIFEST_SHA256"] = manifest_sha256
        environment["QF_DEV_RUN_JSON_PATH"] = str(wp12_run_json_path.resolve())
    environment["QF_DEVELOPMENT_AUTONOMOUS"] = "1"
    return environment


def _native_guard_environment(environment: Mapping[str, str]) -> dict[str, Any]:
    """Record no-native marker states without persisting arbitrary env values."""
    values: dict[str, str] = {}
    for index, name in enumerate(NATIVE_GUARD_ENV_KEYS):
        value = environment.get(name)
        if value is None:
            values[name] = "UNSET"
        elif index < 2:
            values[name] = "ACTIVE" if value not in ("", "0", "false", "False") else "INACTIVE"
        else:
            values[name] = "ACTIVE" if value == "1" else "INACTIVE"
    active = [name for name in NATIVE_GUARD_ENV_KEYS[:2] if values[name] == "ACTIVE"]
    active.extend(name for name in NATIVE_GUARD_ENV_KEYS[2:] if values[name] == "ACTIVE")
    return {"values": values, "active_markers": active}


def _validate_native_guard_environment(
    parent_environment: Mapping[str, str],
    child_environment: Mapping[str, str],
) -> dict[str, Any]:
    """Require the child to preserve the no-native guard state checked preflight."""
    parent_state = _native_guard_environment(parent_environment)
    child_state = _native_guard_environment(child_environment)
    if child_state != parent_state:
        raise PolicyError("child environment changed an explicit no-native marker after development preflight")
    return child_state


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _strict_json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int equivalence or permissive NaNs."""
    try:
        return json.dumps(left, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
            right, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError):
        return False


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys so authorization JSON cannot depend on parser choice."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
    )


def _atomic_json(path: Path, payload: Mapping[str, Any], *, sort_keys: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as stream:
        json.dump(payload, stream, indent=2, sort_keys=sort_keys)
        stream.write("\n")
        temporary = Path(stream.name)
    os.replace(temporary, path)


def _atomic_json_new(path: Path, payload: Mapping[str, Any], *, sort_keys: bool = True) -> None:
    """Atomically publish a new JSON artifact without replacing an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as stream:
        json.dump(payload, stream, indent=2, sort_keys=sort_keys)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    try:
        os.link(temporary, path)
    except FileExistsError as exc:
        raise PolicyError("refusing to overwrite an existing development artifact") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _archive_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def _directory_size(path: Path) -> int:
    return _archive_size(path) if path.exists() else 0


def _file_inventory(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        {"path": item.relative_to(path).as_posix(), "bytes": item.stat().st_size, "sha256": _sha256(item)}
        for item in sorted(path.rglob("*"))
        if item.is_file()
    ]


def _wp12b_hex20_diagnostic_sidecar(
    *,
    worktree_id: str | None,
    target: str | None,
    evidence_root: str | None,
    attempt_id: str,
    manifest_receipt: Mapping[str, Any] | None,
    selected_dofs: int | None,
    run_json_path: Path,
    sidecar_limit_bytes: int | None,
) -> dict[str, Any] | None:
    """Verify and hash-link the exact prospective HEX20 sidecar into final run.json."""
    if worktree_id not in {WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID, WP12B_HEX20_R2_WORKTREE_ID}:
        return None
    reasons: list[str] = []
    if target != WP12B_HEX20_DIAGNOSTIC_NODEID:
        reasons.append("unexpected nodeid")
    if selected_dofs != 60:
        reasons.append("selected DDL mismatch")
    if not evidence_root or manifest_receipt is None:
        reasons.append("missing evidence root or validated manifest")
        return {"status": "PROVENANCE_MISMATCH", "reasons": reasons}

    root = Path(evidence_root).resolve()
    path = root / "wp12b_hex20_affine_diagnostic" / f"{attempt_id}.json"
    try:
        run_record = json.loads(
            run_json_path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "RUN_RECORD_UNREADABLE",
            "path": str(path),
            "run_json_path": str(run_json_path.resolve()),
            "reasons": [*reasons, f"{type(exc).__name__}: {exc}"],
        }
    run_manifest = run_record.get("execution_manifest") if isinstance(run_record, dict) else None
    run_selection = run_record.get("wp12_case_selection") if isinstance(run_record, dict) else None
    if not isinstance(run_manifest, dict):
        run_manifest = {}
    if not isinstance(run_selection, dict):
        run_selection = {}
    if (
        not isinstance(run_record, dict)
        or run_record.get("controller_attempt_id") != attempt_id
        or run_record.get("worktree_id") != worktree_id
        or run_record.get("target") not in (target, [target])
        or run_record.get("series_id") is None
        or f"{run_record.get('series_id')}-attempt-{run_record.get('attempt')}" != attempt_id
        or run_manifest.get("authorization_id") != (manifest_receipt or {}).get("authorization_id")
        or run_manifest.get("sha256") != (manifest_receipt or {}).get("sha256")
        or run_selection.get("selected_dofs") != selected_dofs
    ):
        reasons.append("run.json attempt, manifest, nodeid or DDL binding mismatch")
    try:
        resolved = path.resolve(strict=True)
        if not _is_within(resolved, root) or not resolved.is_file():
            reasons.append("sidecar path is outside the scope evidence root")
            return {"status": "PROVENANCE_MISMATCH", "path": str(path), "reasons": reasons}
        sidecar = json.loads(
            resolved.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
        )
    except FileNotFoundError:
        return {"status": "SIDECAR_NOT_FOUND", "path": str(path), "reasons": reasons}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "SIDECAR_UNREADABLE",
            "path": str(path),
            "reasons": [*reasons, f"{type(exc).__name__}: {exc}"],
        }

    sidecar_controller = sidecar.get("controller") if isinstance(sidecar, dict) else None
    manifest_id = manifest_receipt.get("authorization_id")
    manifest_sha256 = manifest_receipt.get("sha256")
    expected = {
        "worktree_id": worktree_id,
        "selected_dofs": 60,
        "controller_attempt_id": attempt_id,
        "manifest_id": manifest_id,
        "manifest_sha256": manifest_sha256,
        "run_json_path": str(run_json_path.resolve()),
    }
    observed = sidecar_controller if isinstance(sidecar_controller, dict) else {}
    reasons.extend(key for key, value in expected.items() if observed.get(key) != value)
    sidecar_bytes = resolved.stat().st_size
    if sidecar_limit_bytes is not None and sidecar_bytes > sidecar_limit_bytes:
        reasons.append("sidecar exceeds the registered archive-size budget")
    sidecar_identity = sidecar.get("identity") if isinstance(sidecar, dict) else None
    supported_schemas = (
        "qfsolver-wp12b-hex20-affine-diagnostic-v1",
        "qfsolver-wp12b-hex20-affine-diagnostic-v2",
    )
    if not isinstance(sidecar_identity, dict) or sidecar.get("schema") not in supported_schemas:
        reasons.append("sidecar schema mismatch")
    if not isinstance(sidecar_identity, dict) or sidecar_identity.get("nodeid") != target:
        reasons.append("nodeid mismatch")
    if worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
        criteria = sidecar.get("diagnostic_criteria") if isinstance(sidecar, dict) else None
        gate = criteria.get("r2_face_nodal_gate") if isinstance(criteria, dict) else None
        if (
            not isinstance(sidecar, dict)
            or sidecar.get("schema") != "qfsolver-wp12b-hex20-affine-diagnostic-v2"
            or not isinstance(gate, dict)
            or gate.get("rtol") != 1.0e-12
            or gate.get("atol_N") != 1.0e-6
            or gate.get("status") != "PROPOSED_FOR_OWNER; ASSERTED_AFTER_PRE_ASSERTION_ARCHIVE"
        ):
            reasons.append("R2 nodal gate provenance mismatch")
    return {
        "status": "VERIFIED" if not reasons else "PROVENANCE_MISMATCH",
        "path": str(resolved),
        "sha256": _sha256(resolved),
        "bytes": sidecar_bytes,
        "maximum_bytes": sidecar_limit_bytes,
        "controller_attempt_id": attempt_id,
        "manifest_id": manifest_id,
        "manifest_sha256": manifest_sha256,
        "reasons": reasons,
    }


def _unpack_numeric_bytes(dtype: str, raw: bytes) -> list[int | float | bool] | tuple[list[float], list[float]] | None:
    match = re.fullmatch(r"[<>=|]([biufc])(\d+)", dtype)
    if match is None:
        return None
    kind, size_text = match.groups()
    size = int(size_text)
    prefix = dtype[0] if dtype[0] in "<>=" else "="
    formats = {
        ("b", 1): "?",
        ("i", 1): "b",
        ("i", 2): "h",
        ("i", 4): "i",
        ("i", 8): "q",
        ("u", 1): "B",
        ("u", 2): "H",
        ("u", 4): "I",
        ("u", 8): "Q",
        ("f", 2): "e",
        ("f", 4): "f",
        ("f", 8): "d",
    }
    if kind == "c":
        component_format = {8: "f", 16: "d"}.get(size)
        if component_format is None:
            return None
        if len(raw) % size:
            return None
        components = list(struct.unpack(f"{prefix}{len(raw) // (size // 2)}{component_format}", raw))
        return components[::2], components[1::2]
    item_format = formats.get((kind, size))
    if item_format is None or len(raw) % size:
        return None
    return list(struct.unpack(f"{prefix}{len(raw) // size}{item_format}", raw))


def _flatten_json_array(value: Any, shape: list[int], kind: str) -> list[int | float | bool] | None:
    if not shape:
        if kind == "b":
            return [value] if isinstance(value, bool) else None
        if kind in "iu":
            return [value] if isinstance(value, int) and not isinstance(value, bool) else None
        return [value] if _finite_number(value) else None
    if not isinstance(value, list) or len(value) != shape[0]:
        return None
    flattened: list[int | float | bool] = []
    for item in value:
        child = _flatten_json_array(item, shape[1:], kind)
        if child is None:
            return None
        flattened.extend(child)
    return flattened


def _valid_numeric_array_snapshot(value: Any, expected_shape: list[int]) -> bool:
    shape = value.get("shape") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or not isinstance(shape, list)
        or any(not isinstance(size, int) or isinstance(size, bool) for size in shape)
        or shape != expected_shape
        or "values" not in value
    ):
        return False
    dtype = value.get("dtype")
    dtype_match = re.fullmatch(r"[<>=|]([biufc])(\d+)", dtype) if isinstance(dtype, str) else None
    encoded = value.get("raw_bytes_base64")
    digest = value.get("raw_representation_sha256")
    if dtype_match is None or not isinstance(encoded, str) or not isinstance(digest, str):
        return False
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        return False
    if any(not isinstance(size, int) or isinstance(size, bool) or size <= 0 for size in expected_shape):
        return False
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return False
    expected_bytes = math.prod(expected_shape) * int(dtype_match.group(2))
    if len(raw) != expected_bytes:
        return False
    identity = json.dumps(
        {"dtype": dtype, "shape": expected_shape, "order": "C"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    if hashlib.sha256(identity + b"\0" + raw).hexdigest() != digest:
        return False
    unpacked = _unpack_numeric_bytes(dtype, raw)
    kind = dtype_match.group(1)
    if kind == "c":
        if not isinstance(unpacked, tuple) or not isinstance(value["values"], dict):
            return False
        real = _flatten_json_array(value["values"].get("real"), expected_shape, "f")
        imag = _flatten_json_array(value["values"].get("imag"), expected_shape, "f")
        return real == unpacked[0] and imag == unpacked[1]
    flattened = _flatten_json_array(value["values"], expected_shape, kind)
    return isinstance(unpacked, list) and flattened == unpacked


def _valid_csr_snapshot(value: Any, expected_shape: list[int]) -> bool:
    shape = value.get("shape") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("format") != "CSR_COPY_WITH_STORED_ORDER"
        or not isinstance(shape, list)
        or any(not isinstance(size, int) or isinstance(size, bool) for size in shape)
        or shape != expected_shape
        or not isinstance(value.get("nnz_stored"), int)
        or isinstance(value.get("nnz_stored"), bool)
        or value["nnz_stored"] <= 0
        or not isinstance(value.get("arrays"), dict)
    ):
        return False
    nnz = value["nnz_stored"]
    arrays = value["arrays"]
    if set(arrays) != {"data", "indices", "indptr"}:
        return False
    digest = hashlib.sha256()
    digest.update(json.dumps({"shape": expected_shape}, sort_keys=True).encode("ascii"))
    expected_lengths = {"data": nnz, "indices": nnz, "indptr": expected_shape[0] + 1}
    for name in ("data", "indices", "indptr"):
        item = arrays[name]
        if not isinstance(item, dict) or not isinstance(item.get("values"), list):
            return False
        dtype = item.get("dtype")
        dtype_match = re.fullmatch(r"[<>=|]([biufc])(\d+)", dtype) if isinstance(dtype, str) else None
        encoded = item.get("raw_bytes_base64")
        if dtype_match is None or not isinstance(encoded, str) or len(item["values"]) != expected_lengths[name]:
            return False
        if (name == "data" and dtype_match.group(1) != "f") or (name != "data" and dtype_match.group(1) not in "iu"):
            return False
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            return False
        if len(raw) != expected_lengths[name] * int(dtype_match.group(2)):
            return False
        unpacked = _unpack_numeric_bytes(dtype, raw)
        if not isinstance(unpacked, list) or unpacked != item["values"]:
            return False
        if name == "data":
            if any(not _finite_number(number) for number in item["values"]):
                return False
        elif any(not isinstance(index, int) or isinstance(index, bool) or index < 0 for index in item["values"]):
            return False
        digest.update(name.encode("ascii"))
        digest.update(dtype.encode("ascii"))
        digest.update(raw)
    if digest.hexdigest() != value.get("stored_representation_sha256"):
        return False
    indices = arrays["indices"]["values"]
    indptr = arrays["indptr"]["values"]
    return (
        indptr[0] == 0
        and indptr[-1] == nnz
        and all(left <= right for left, right in zip(indptr, indptr[1:]))
        and all(index < expected_shape[1] for index in indices)
    )


def _same_csr_snapshot(left: Any, right: Any) -> bool:
    """Compare validated CSR evidence by its exact stored representation."""
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    return all(left.get(field) == right.get(field) for field in ("format", "shape", "nnz_stored", "arrays"))


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _validate_d01_junit_payload(
    xml_path: Path,
    target: str,
    expected_source_sha: str,
    pytest_return_code: int = 0,
) -> tuple[bool, list[str], dict[str, Any] | None]:
    """Require durable numerical record_property payloads for a D01 result."""
    mesh_match = re.search(r"\[(M[123])\]$", target)
    if mesh_match is None:
        return False, ["target has no registered D01 mesh suffix"], None
    mesh_id = mesh_match.group(1)
    if not xml_path.is_file():
        return False, ["pytest JUnit XML is missing"], None
    try:
        root = ET.parse(xml_path).getroot()
    except (OSError, ET.ParseError, ValueError, RecursionError) as exc:
        return False, [f"pytest JUnit XML is unreadable: {type(exc).__name__}: {exc}"], None
    expected_module, expected_name = target.split("::", 1)
    expected_classname = expected_module.replace("\\", "/").removesuffix(".py").replace("/", ".")
    if root.tag != "testsuites" or len(root) != 1 or root[0].tag != "testsuite":
        return False, ["JUnit document does not have the expected single testsuites/testsuite structure"], None
    suite = root[0]
    cases = suite.findall("./testcase")
    if suite.get("tests") != "1" or len(cases) != 1:
        return False, [f"expected one JUnit testcase in one-test suite, found {len(cases)}"], None
    case = cases[0]
    if case.get("classname") != expected_classname or case.get("name") != expected_name:
        return False, ["JUnit testcase classname/name does not match the exact requested nodeid"], None
    if case.find("./skipped") is not None or suite.get("skipped") != "0":
        return False, ["JUnit testcase was skipped; a zero pytest exit code is not a scenario PASS"], None
    case_failures = int(case.find("./failure") is not None)
    case_errors = int(case.find("./error") is not None)
    try:
        suite_failures = int(suite.get("failures", ""))
        suite_errors = int(suite.get("errors", ""))
    except ValueError:
        return False, ["JUnit suite failure/error counters are malformed"], None
    if suite_failures != case_failures or suite_errors != case_errors:
        return False, ["JUnit suite counters do not match the exact testcase state"], None
    if pytest_return_code == 0 and (case_failures or case_errors):
        return False, ["JUnit reports a failed testcase despite pytest's successful exit code"], None
    property_items = case.findall("./properties/property")
    property_names = [item.get("name") for item in property_items]
    properties = {item.get("name"): item.get("value", item.text or "") for item in property_items if item.get("name")}
    required = (
        "wp_d01_cg_source_operands_json",
        "wp_d01_cg_projected_damping_m2_json",
        "wp_d01_cg_projected_damping_m4_json",
        "wp_d01_bj_experimental_results_json",
    )
    if any(property_names.count(name) != 1 for name in required):
        return False, ["JUnit must contain exactly one of every required numerical property"], None
    missing = [name for name in required if not properties.get(name)]
    if missing:
        return False, ["JUnit numerical properties missing: " + ", ".join(missing)], None
    decoded: dict[str, Any] = {}
    for name in required:
        try:
            decoded[name] = json.loads(
                properties[name],
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
            )
        except (json.JSONDecodeError, TypeError, ValueError, RecursionError) as exc:
            return False, [f"JUnit property {name} is not strict JSON: {exc}"], None
    expected_elements, expected_free_dofs = {"M1": (8, 48), "M2": (16, 96), "M3": (32, 192)}[mesh_id]
    matrix_shape = [expected_free_dofs, expected_free_dofs]
    source = decoded["wp_d01_cg_source_operands_json"]
    source_sha_values = [
        decoded["wp_d01_cg_source_operands_json"].get("source_sha")
        if isinstance(decoded["wp_d01_cg_source_operands_json"], dict)
        else None,
        decoded["wp_d01_cg_projected_damping_m2_json"].get("source_sha")
        if isinstance(decoded["wp_d01_cg_projected_damping_m2_json"], dict)
        else None,
        decoded["wp_d01_cg_projected_damping_m4_json"].get("source_sha")
        if isinstance(decoded["wp_d01_cg_projected_damping_m4_json"], dict)
        else None,
        decoded["wp_d01_bj_experimental_results_json"].get("source_sha")
        if isinstance(decoded["wp_d01_bj_experimental_results_json"], dict)
        else None,
    ]
    if expected_source_sha != expected_source_sha.lower() or not re.fullmatch(r"[0-9a-f]{40}", expected_source_sha):
        return False, ["expected source identity is not a full lowercase Git commit SHA"], None
    if source_sha_values != [expected_source_sha] * len(required):
        return False, ["numerical JUnit properties do not all bind to the exact D01 source commit"], None
    source_mesh = source.get("mesh") if isinstance(source, dict) else None
    operators = source.get("operators") if isinstance(source, dict) else None
    if (
        not isinstance(source_mesh, dict)
        or source_mesh.get("id") != mesh_id
        or source_mesh.get("elements") != expected_elements
        or source_mesh.get("free_dofs") != expected_free_dofs
        or not isinstance(source.get("operator_identity"), str)
        or not source["operator_identity"]
        or not isinstance(operators, dict)
        or not {"M", "K", "C_used_by_experiment"}.issubset(operators)
        or not isinstance(source.get("exact_numeric_arrays"), dict)
    ):
        return False, ["source-operator payload lacks the expected FEM mesh or exact M/K/C operands"], None
    if any(not _valid_csr_snapshot(operators[name], matrix_shape) for name in ("M", "K", "C_used_by_experiment")):
        return False, ["source M/K/C sparse snapshots are empty, malformed, or fail their stored-byte hashes"], None
    source_arrays = source["exact_numeric_arrays"]
    if (
        not _valid_numeric_array_snapshot(source_arrays.get("frequencies_hz"), [6])
        or not _valid_numeric_array_snapshot(source_arrays.get("normalized_equilibrium_residuals"), [6])
        or not _valid_numeric_array_snapshot(source_arrays.get("reduced_force"), [expected_free_dofs])
        or not isinstance(source_arrays.get("responses_full_free_complex"), list)
        or len(source_arrays["responses_full_free_complex"]) != 6
        or any(
            not _valid_numeric_array_snapshot(item, [expected_free_dofs])
            for item in source_arrays["responses_full_free_complex"]
        )
    ):
        return False, ["source numerical arrays are missing, empty, malformed, or fail their exact-byte hashes"], None
    for mode_count, property_name in (
        (2, "wp_d01_cg_projected_damping_m2_json"),
        (4, "wp_d01_cg_projected_damping_m4_json"),
    ):
        projection = decoded[property_name]
        if (
            not isinstance(projection, dict)
            or projection.get("mesh_id") != mesh_id
            or projection.get("mode_count") != mode_count
            or projection.get("source_sha") != expected_source_sha
            or projection.get("frozen_symmetry_threshold") != 1.0e-12
            or projection.get("acceptance_verdict") != "DIAGNOSTIC_ONLY_NOT_AN_ACCEPTANCE_OVERRIDE"
            or not isinstance(projection.get("exact_numeric_arrays"), dict)
        ):
            return False, [f"projected-damping payload for {mode_count} modes is incomplete or mismatched"], None
        projected_arrays = projection["exact_numeric_arrays"]
        projected_shapes = {
            "mode_matrix": [expected_free_dofs, mode_count],
            "eigenvalues_rad2_s2": [mode_count],
            "damping_times_modes": [expected_free_dofs, mode_count],
            "projected_mass": [mode_count, mode_count],
            "projected_stiffness": [mode_count, mode_count],
            "projected_mass_gram": [mode_count, mode_count],
            "projected_damping": [mode_count, mode_count],
            "expected_projected_rayleigh_from_cached_operators": [mode_count, mode_count],
        }
        if any(
            not _valid_numeric_array_snapshot(projected_arrays.get(name), shape)
            for name, shape in projected_shapes.items()
        ) or not _valid_csr_snapshot(projection.get("input_damping"), matrix_shape):
            return (
                False,
                [f"projected-damping exact operands for {mode_count} modes are missing, malformed, or hash-invalid"],
                None,
            )
        if not _same_csr_snapshot(operators["C_used_by_experiment"], projection["input_damping"]):
            return (
                False,
                [f"projected-damping input for {mode_count} modes does not exactly match source C_used_by_experiment"],
                None,
            )
    payload = decoded["wp_d01_bj_experimental_results_json"]
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("mesh"), dict)
        or payload["mesh"].get("id") != mesh_id
        or payload["mesh"].get("elements") != expected_elements
        or payload["mesh"].get("free_dofs") != expected_free_dofs
    ):
        return False, ["experimental payload mesh identity does not match the nodeid"], None
    if (
        payload.get("retained_mode_counts") != [2, 4]
        or payload.get("qualification") != "NOT_CERTIFIED"
        or payload.get("source_sha") != expected_source_sha
        or payload.get("c4_official_status") != "NOT_EVALUATED_BY_DESIGN"
        or payload.get("c4_complete_spectrum_captured") is not False
    ):
        return False, ["experimental payload mode counts or non-qualification marker are unexpected"], None
    responses = payload.get("responses")
    if not isinstance(responses, dict) or set(responses) != {"uncorrected", "corrected"}:
        return False, ["experimental response groups are missing or malformed"], None
    frequencies = payload.get("frequencies_hz")
    if not _valid_d01_experimental_frequency_grid(frequencies):
        return (
            False,
            ["experimental payload must contain 0 Hz followed by five finite, positive, increasing frequencies"],
            None,
        )
    if source_arrays["frequencies_hz"]["values"] != frequencies:
        return False, ["source-operator and response payload frequency grids differ"], None
    for treatment, rows in responses.items():
        if not isinstance(rows, list) or len(rows) != 12:
            return False, [f"{treatment} payload must contain 12 rows (6 frequencies × 2 truncations)"], None
        if any(not isinstance(row, dict) for row in rows):
            return False, [f"{treatment} payload contains a non-object response row"], None
        if [row.get("mode_count") for row in rows] != [2] * 6 + [4] * 6:
            return False, [f"{treatment} payload does not preserve the expected 2/4-mode order"], None
        if [row.get("frequency_hz") for row in rows] != frequencies * 2:
            return False, [f"{treatment} response rows do not match the frozen frequency grid and order"], None
        for row in rows:
            tip = row.get("tip_uy_m")
            if (
                not isinstance(tip, dict)
                or not _finite_number(tip.get("real"))
                or not _finite_number(tip.get("imag"))
                or any(
                    not _finite_number(row.get(name)) or row[name] < 0
                    for name in (
                        "relative_full_free_displacement_error",
                        "normalized_free_equilibrium_residual",
                        "direct_reference_residual",
                    )
                )
                or any(
                    row.get(name) is not None and not _finite_number(row.get(name))
                    for name in ("relative_tip_amplitude_error", "tip_phase_error_rad")
                )
                or not isinstance(row.get("energy"), dict)
                or not all(
                    _finite_number(row["energy"].get(key))
                    for key in ("average_input_power_W", "average_rayleigh_dissipation_W")
                )
                or (
                    row["energy"].get("absolute_balance_gap_W") is not None
                    and not _finite_number(row["energy"].get("absolute_balance_gap_W"))
                )
            ):
                return False, [f"{treatment} response row lacks finite displacement/error/residual metrics"], None
            if treatment == "uncorrected" and (
                not isinstance(row.get("wp05_diagnostic"), dict) or not row["wp05_diagnostic"]
            ):
                return False, ["uncorrected response row lacks WP05 diagnostic evidence"], None
            if treatment == "corrected" and (
                row.get("correction_error_ratio_status") is None
                or not isinstance(row.get("correction_degraded_error"), bool)
                or not isinstance(row.get("wp_d01_diagnostics"), dict)
                or not row["wp_d01_diagnostics"]
                or (
                    row.get("correction_error_ratio") is not None
                    and (not _finite_number(row["correction_error_ratio"]) or row["correction_error_ratio"] < 0)
                )
            ):
                return False, ["corrected response row lacks a valid correction ratio or D01 diagnostic"], None
    operator_identities = [
        source.get("operator_identity"),
        decoded["wp_d01_cg_projected_damping_m2_json"].get("operator_identity"),
        decoded["wp_d01_cg_projected_damping_m4_json"].get("operator_identity"),
    ]
    if (
        not isinstance(payload.get("operator_identity"), str)
        or not payload["operator_identity"]
        or operator_identities != [payload["operator_identity"]] * 3
    ):
        return (
            False,
            ["source operators, projected damping and harmonic result payloads do not share one operator identity"],
            None,
        )
    return (
        True,
        [],
        {
            "mesh_id": mesh_id,
            "elements": expected_elements,
            "free_dofs": expected_free_dofs,
            "property_names": list(required),
            "response_rows_per_treatment": 12,
            "symmetry_threshold": 1.0e-12,
        },
    )


def _valid_d01_experimental_frequency_grid(frequencies: Any) -> bool:
    """Accept the frozen experiment grid: one static point, then five positive points."""
    if not isinstance(frequencies, list) or len(frequencies) != 6:
        return False
    if any(not _finite_number(value) for value in frequencies):
        return False
    numeric = [float(value) for value in frequencies]
    return (
        numeric[0] == 0.0
        and all(value > 0.0 for value in numeric[1:])
        and all(left < right for left, right in zip(numeric, numeric[1:]))
    )


def _d01_final_state(current_state: str, payload_complete: bool | None) -> str:
    """Never expose a pytest PASS when the required numerical archive is absent."""
    if current_state == "PASS" and payload_complete is not True:
        return "RESULT_ARCHIVE_INCOMPLETE"
    return current_state


def _process_snapshot(pid: int) -> tuple[int, int]:
    if psutil is None:
        raise PolicyError("psutil is required for monitored development execution")
    try:
        root = psutil.Process(pid)
        processes = [root, *root.children(recursive=True)]
    except psutil.NoSuchProcess:
        return 0, 0
    alive = []
    rss = 0
    for process in processes:
        try:
            if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                alive.append(process)
                rss += process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return len(alive), rss


def _terminate_tree(pid: int) -> None:
    if psutil is None:
        return
    try:
        root = psutil.Process(pid)
        children = root.children(recursive=True)
    except psutil.NoSuchProcess:
        return
    processes = list(reversed(children)) + [root]
    for process in processes:
        try:
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _gone, alive = psutil.wait_procs(processes, timeout=2)
    for process in alive:
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    psutil.wait_procs(alive, timeout=2)


def run_supervised_command(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    output_dir: Path,
    temporary_dir: Path | None = None,
    limits: Mapping[str, Any],
    poll_interval: float = 0.25,
) -> ProcessResult:
    """Run a child noninteractively with bounded capture and monitored resources."""
    if psutil is None:
        raise PolicyError("psutil is required; install the project test/dev dependencies before launching")
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"
    total_cap = int(limits["output_total_limit_mib"] * 1024 * 1024)
    stream_cap = int(limits["output_stream_limit_mib"] * 1024 * 1024)
    archive_cap = int(limits["archive_size_limit_mib"] * 1024 * 1024)
    temporary_dir = output_dir if temporary_dir is None else temporary_dir
    temporary_cap = int(limits.get("temporary_limit_mib", limits["archive_size_limit_mib"]) * 1024 * 1024)
    free_disk_floor = int(limits.get("minimum_free_disk_mib", 0) * 1024 * 1024)
    rss_cap = int(limits["rss_soft_limit_mib"] * 1024 * 1024)
    process_cap = int(limits["process_tree_limit"])
    timeout = float(limits["timeout_seconds"])

    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=dict(environment),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
        start_new_session=(os.name != "nt"),
        bufsize=0,
    )
    state_lock = threading.Lock()
    output_exceeded = threading.Event()
    capture = {"observed": {"stdout": 0, "stderr": 0}, "saved": {"stdout": 0, "stderr": 0}, "total_saved": 0}
    reader_errors: list[str] = []

    def pump(pipe: BinaryIO, path: Path, name: str) -> None:
        try:
            with path.open("wb") as output:
                while True:
                    chunk = pipe.read(64 * 1024)
                    if not chunk:
                        break
                    with state_lock:
                        capture["observed"][name] += len(chunk)
                        allowed = min(
                            len(chunk),
                            max(0, stream_cap - capture["saved"][name]),
                            max(0, total_cap - capture["total_saved"]),
                        )
                        if allowed:
                            output.write(chunk[:allowed])
                            capture["saved"][name] += allowed
                            capture["total_saved"] += allowed
                        if allowed < len(chunk):
                            output_exceeded.set()
                output.flush()
        except (OSError, ValueError) as exc:
            reader_errors.append(f"{name}: {exc}")
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    assert process.stdout is not None and process.stderr is not None
    readers = [
        threading.Thread(target=pump, args=(process.stdout, stdout_path, "stdout"), daemon=True),
        threading.Thread(target=pump, args=(process.stderr, stderr_path, "stderr"), daemon=True),
    ]
    for reader in readers:
        reader.start()

    started = time.monotonic()
    peak_rss = 0
    peak_processes = 0
    stop_reason: str | None = None
    try:
        while True:
            if output_exceeded.is_set():
                stop_reason = "CAPTURED_OUTPUT_LIMIT_EXCEEDED"
                _terminate_tree(process.pid)
                break
            elapsed = time.monotonic() - started
            if elapsed > timeout:
                stop_reason = "WALL_TIMEOUT_EXCEEDED"
                _terminate_tree(process.pid)
                break
            if process.poll() is not None:
                break
            process_count, rss = _process_snapshot(process.pid)
            peak_processes = max(peak_processes, process_count)
            peak_rss = max(peak_rss, rss)
            if process_count > process_cap:
                stop_reason = "PROCESS_TREE_LIMIT_EXCEEDED"
            elif rss > rss_cap:
                stop_reason = "RSS_SOFT_LIMIT_EXCEEDED"
            elif _directory_size(output_dir) > archive_cap:
                stop_reason = "RUN_ARCHIVE_SIZE_LIMIT_OBSERVED"
            elif _directory_size(temporary_dir) > temporary_cap:
                stop_reason = "TEMPORARY_SIZE_LIMIT_OBSERVED"
            elif free_disk_floor and shutil.disk_usage(cwd).free < free_disk_floor:
                stop_reason = "MINIMUM_FREE_DISK_FLOOR_CROSSED"
            if stop_reason is not None:
                _terminate_tree(process.pid)
                break
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        stop_reason = "INTERRUPTED_BY_OPERATOR"
        _terminate_tree(process.pid)

    try:
        return_code = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _terminate_tree(process.pid)
        return_code = process.wait(timeout=5)
    except KeyboardInterrupt:
        stop_reason = "INTERRUPTED_BY_OPERATOR"
        _terminate_tree(process.pid)
        return_code = process.wait(timeout=5)
    for reader in readers:
        reader.join(timeout=5)
    elapsed = time.monotonic() - started
    archive_bytes = _directory_size(output_dir)
    temporary_bytes = _directory_size(temporary_dir)
    if archive_bytes > archive_cap and stop_reason is None:
        stop_reason = "RUN_ARCHIVE_SIZE_LIMIT_OBSERVED"
    if temporary_bytes > temporary_cap and stop_reason is None:
        stop_reason = "TEMPORARY_SIZE_LIMIT_OBSERVED"
    if output_exceeded.is_set() and stop_reason is None:
        stop_reason = "CAPTURED_OUTPUT_LIMIT_EXCEEDED"
    if reader_errors and stop_reason is None:
        stop_reason = "OUTPUT_CAPTURE_ERROR"
    if stop_reason:
        status = stop_reason
    elif return_code == 0:
        status = "PASS"
    else:
        status = "PYTEST_FAILED"
    with state_lock:
        stdout_bytes = int(capture["saved"]["stdout"])
        stderr_bytes = int(capture["saved"]["stderr"])
    return ProcessResult(
        status=status,
        return_code=return_code,
        elapsed_seconds=elapsed,
        peak_rss_bytes=peak_rss,
        peak_process_count=peak_processes,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        archive_bytes=archive_bytes,
        temporary_bytes=temporary_bytes,
        stop_reason=stop_reason or ("; ".join(reader_errors) if reader_errors else None),
    )


def _git_identity(
    root: Path = ROOT,
    *,
    expected_branch: str | None = None,
    baseline_commit: str | None = None,
) -> dict[str, Any]:
    def git(*args: str) -> str | None:
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    top_level = git("rev-parse", "--show-toplevel")
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    branch = git("branch", "--show-current")
    if not top_level or Path(top_level).resolve() != root.resolve() or not head or not tree:
        raise PolicyError("registered project root is not the Git worktree being executed")
    if expected_branch is not None and branch != expected_branch:
        raise PolicyError(f"worktree branch mismatch: expected {expected_branch}, got {branch}")
    if baseline_commit is not None:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", baseline_commit, "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise PolicyError("registered baseline is not an ancestor of this worktree HEAD")
    return {
        "root": str(root.resolve()),
        "branch": branch,
        "head": head,
        "tree": tree,
        "status_short": git("status", "--short", "--untracked-files=all"),
    }


def _next_attempt(
    series_dir: Path,
    series_id: str,
    scope_name: str,
    maximum: int,
    *,
    worktree_id: str | None = None,
    target: str | None = None,
) -> tuple[int, Path]:
    if worktree_id == VV3D_WORKTREE_ID:
        try:
            campaign_store = series_dir.parents[2]
        except IndexError as exc:
            raise PolicyError("VV3D attempt path is not nested in its campaign store") from exc
        _create_campaign_directory(campaign_store, series_dir)
    else:
        series_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = series_dir / "series.json"
    metadata = {
        "schema": "qfsolver-development-series-v2",
        "series_id": series_id,
        "scope": scope_name,
        "worktree_id": worktree_id,
        "target": target,
    }
    try:
        with metadata_path.open("x", encoding="utf-8") as stream:
            json.dump(metadata, stream, sort_keys=True)
            stream.write("\n")
    except FileExistsError:
        try:
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyError(f"development series metadata is unreadable: {exc}") from exc
        if existing != metadata:
            raise PolicyError("development series ID is already bound to a different scope")
    prior = [path for path in series_dir.glob("attempt-[0-9][0-9][0-9][0-9]") if path.is_dir()]
    number = len(prior) + 1
    if number > maximum:
        raise PolicyError(f"development series exhausted its {maximum}-attempt budget")
    attempt_dir = series_dir / f"attempt-{number:04d}"
    try:
        attempt_dir.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise PolicyError("another invocation is already using this development series") from exc
    return number, attempt_dir


@contextmanager
def _exclusive_file_lock(path: Path) -> Iterator[None]:
    """Acquire an OS-released lock; a stale lock file never blocks a later run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise PolicyError(f"another authorized scenario is active ({path.name})") from exc
        else:  # pragma: no cover - exercised on non-Windows development hosts
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise PolicyError(f"another authorized scenario is active ({path.name})") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - exercised on non-Windows development hosts
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    finally:
        stream.close()


@contextmanager
def _node_attempt_locks(ledger_path: Path, ledger_lock: Path, worktree_id: str) -> Iterator[None]:
    """Serialize Dynamics reservations against an active batch; other scopes keep their old lock path."""
    if worktree_id == "wp12_dynamics" and not getattr(_WP12A_BATCH_LOCK_LOCAL, "held", False):
        with _exclusive_file_lock(ledger_path.with_suffix(".batch.lock")):
            with _exclusive_file_lock(ledger_lock):
                yield
    else:
        with _exclusive_file_lock(ledger_lock):
            yield


def _test_source_dependency_inventory(root: Path, target_module: str) -> dict[str, str]:
    """Hash repository-local Python imports reachable from a target and its pytest setup."""
    repository_root = root.resolve()
    tests_root = (repository_root / "tests").resolve()
    target_path = (repository_root / Path(target_module)).resolve()
    if not _is_within(target_path, tests_root) or not target_path.is_file() or target_path.suffix != ".py":
        raise PolicyError("target test source must resolve to a Python file below tests/")

    roots_to_scan = {target_path}
    parent = target_path.parent
    package_initializers: set[Path] = set()
    conftest_files: set[Path] = set()
    while _is_within(parent, repository_root):
        if _is_within(parent, tests_root):
            package_initializer = parent / "__init__.py"
            if package_initializer.is_file():
                resolved_initializer = package_initializer.resolve()
                if not _is_within(resolved_initializer, repository_root):
                    raise PolicyError(f"test package initializer escapes the repository: {package_initializer}")
                roots_to_scan.add(resolved_initializer)
                package_initializers.add(resolved_initializer)
        conftest = parent / "conftest.py"
        if conftest.is_file():
            resolved_conftest = conftest.resolve()
            if not _is_within(resolved_conftest, repository_root):
                raise PolicyError(f"pytest conftest escapes the repository: {conftest}")
            roots_to_scan.add(resolved_conftest)
            conftest_files.add(resolved_conftest)
        if parent == repository_root:
            break
        parent = parent.parent

    dependencies: set[Path] = package_initializers | conftest_files
    pending = list(roots_to_scan)
    scanned: set[Path] = set()

    def covered_by_full_source_inventory(path: Path) -> bool:
        relative_text = path.relative_to(repository_root).as_posix()
        return relative_text.startswith(("src/solveur/", "experiments/"))

    def resolve_module(importer: Path, module_parts: Sequence[str], *, relative_base: Path | None = None) -> set[Path]:
        if not module_parts or any(not part.isidentifier() for part in module_parts):
            return set()
        search_roots = (
            [relative_base]
            if relative_base is not None
            else [importer.parent, tests_root, repository_root / "src", repository_root]
        )
        resolved: set[Path] = set()
        for search_root in search_roots:
            if search_root is None:
                continue
            for index in range(1, len(module_parts) + 1):
                stem = search_root.joinpath(*module_parts[:index])
                candidates = (stem.with_suffix(".py"), stem / "__init__.py")
                for candidate in candidates:
                    path = candidate.resolve()
                    if _is_within(path, repository_root) and path.is_file():
                        resolved.add(path)
        return resolved

    def import_modules(source: Path, tree: ast.AST) -> set[Path]:
        found: set[Path] = set()
        importlib_names = {"importlib"}
        import_module_names = {"import_module"}
        builtins_names = {"builtins"}
        builtin_import_names = {"__import__"}
        for imported in ast.walk(tree):
            if isinstance(imported, ast.Import):
                importlib_names.update(
                    alias.asname for alias in imported.names if alias.name == "importlib" and alias.asname
                )
                builtins_names.update(
                    alias.asname for alias in imported.names if alias.name == "builtins" and alias.asname
                )
            elif isinstance(imported, ast.ImportFrom) and imported.module == "importlib":
                import_module_names.update(
                    alias.asname or alias.name for alias in imported.names if alias.name == "import_module"
                )
            elif isinstance(imported, ast.ImportFrom) and imported.module == "builtins":
                builtin_import_names.update(
                    alias.asname or alias.name for alias in imported.names if alias.name == "__import__"
                )

        for node in ast.walk(tree):
            module_groups: list[tuple[Sequence[str], Path | None]] = []
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(target, ast.Name) and target.id == "pytest_plugins" for target in targets):
                    value = node.value
                    values = value.elts if isinstance(value, (ast.List, ast.Tuple, ast.Set)) else [value]
                    if any(not isinstance(item, ast.Constant) or not isinstance(item.value, str) for item in values):
                        raise PolicyError(f"pytest_plugins must be a statically resolvable string sequence: {source}")
                    module_groups.extend((item.value.split("."), None) for item in values)
            elif (
                isinstance(node, ast.AugAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "pytest_plugins"
            ):
                raise PolicyError(f"pytest_plugins mutations must be statically resolvable: {source}")
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "pytest_plugins"
                and node.func.attr in {"append", "extend", "insert"}
            ):
                raise PolicyError(f"pytest_plugins mutations must be statically resolvable: {source}")
            if isinstance(node, ast.Import):
                module_groups.extend((alias.name.split("."), None) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                relative_base = source.parent
                if node.level:
                    for _ in range(node.level - 1):
                        relative_base = relative_base.parent
                    if not _is_within(relative_base, repository_root):
                        raise PolicyError(f"relative source import escapes the repository: {source}")
                    if node.module:
                        module_groups.append((node.module.split("."), relative_base))
                    for alias in node.names:
                        module_parts = node.module.split(".") if node.module else []
                        if alias.name == "*":
                            if not module_parts or resolve_module(source, module_parts, relative_base=relative_base):
                                raise PolicyError(
                                    f"wildcard import from a repository-local module cannot be inventoried: {source}"
                                )
                        else:
                            module_groups.append(([*module_parts, alias.name], relative_base))
                else:
                    if node.module:
                        module_groups.append((node.module.split("."), None))
                    for alias in node.names:
                        module_parts = node.module.split(".") if node.module else []
                        if alias.name == "*":
                            if not module_parts or resolve_module(source, module_parts):
                                raise PolicyError(
                                    f"wildcard import from a repository-local module cannot be inventoried: {source}"
                                )
                        else:
                            module_groups.append(([*module_parts, alias.name], None))
            elif isinstance(node, ast.Call):
                function = node.func
                dynamic_import = isinstance(function, ast.Name) and function.id in (
                    builtin_import_names | import_module_names
                )
                dynamic_import = dynamic_import or (
                    isinstance(function, ast.Attribute)
                    and function.attr == "import_module"
                    and isinstance(function.value, ast.Name)
                    and function.value.id in importlib_names
                )
                dynamic_import = dynamic_import or (
                    isinstance(function, ast.Attribute)
                    and function.attr == "__import__"
                    and isinstance(function.value, ast.Name)
                    and function.value.id in builtins_names
                )
                if not dynamic_import:
                    continue
                call = node
                if (
                    not call.args
                    or not isinstance(call.args[0], ast.Constant)
                    or not isinstance(call.args[0].value, str)
                ):
                    raise PolicyError(f"dynamic test import cannot be source-inventoried statically: {source}")
                import_name = call.args[0].value
                if import_name.startswith("."):
                    raise PolicyError(f"relative dynamic test import is unsupported for source inventory: {source}")
                module_parts = import_name.split(".")
                module_groups.append((module_parts, None))
                fromlist = None
                if isinstance(function, ast.Name) and function.id in builtin_import_names:
                    if len(call.args) > 3:
                        fromlist = call.args[3]
                    else:
                        fromlist = next((item.value for item in call.keywords if item.arg == "fromlist"), None)
                if fromlist is not None:
                    if not isinstance(fromlist, (ast.List, ast.Tuple)) or any(
                        not isinstance(item, ast.Constant) or not isinstance(item.value, str) for item in fromlist.elts
                    ):
                        raise PolicyError(
                            f"dynamic __import__ fromlist cannot be source-inventoried statically: {source}"
                        )
                    module_groups.extend(([*module_parts, item.value], None) for item in fromlist.elts)

            for module_parts, relative_base in module_groups:
                found.update(resolve_module(source, module_parts, relative_base=relative_base))
        return found

    while pending:
        source = pending.pop()
        if source in scanned:
            continue
        scanned.add(source)
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (OSError, SyntaxError, UnicodeError) as exc:
            raise PolicyError(f"cannot inspect test-local imports without importing source: {exc}") from exc
        for dependency in import_modules(source, tree):
            if dependency not in roots_to_scan and not covered_by_full_source_inventory(dependency):
                dependencies.add(dependency)
            if dependency not in scanned and not covered_by_full_source_inventory(dependency):
                pending.append(dependency)

    return {
        path.relative_to(repository_root).as_posix(): _sha256(path)
        for path in sorted(dependencies, key=lambda item: item.as_posix())
    }


def _worktree_source_inventory(root: Path, target: str) -> dict[str, str]:
    """Return raw-byte SHA-256 values for the target, its local test imports, and solver source."""
    listed = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "src/solveur",
            "experiments",
            "tests",
            "pyproject.toml",
            "pytest.ini",
        ],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if listed.returncode != 0:
        raise PolicyError("cannot inventory worktree source files for retry identity")
    target_module = target.split("::", maxsplit=1)[0]
    test_dependencies = _test_source_dependency_inventory(root, target_module)
    files: set[str] = set()
    for raw in listed.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(os.fsdecode(raw).replace("\\", "/"))
        relative_text = relative.as_posix()
        if (
            relative_text.startswith("src/solveur/")
            and relative.suffix == ".py"
            or relative_text.startswith("experiments/")
            and relative.suffix == ".py"
            or relative_text == target_module
            or relative_text in test_dependencies
            or relative_text in {"tests/conftest.py", "tests/unit/conftest.py", "pyproject.toml", "pytest.ini"}
        ):
            files.add(relative_text)
    files.update(test_dependencies)
    if target_module not in files:
        raise PolicyError("approved test module is absent from the source fingerprint inventory")
    inventory: dict[str, str] = {}
    for relative_text in sorted(files):
        path = (root / Path(relative_text)).resolve()
        if not _is_within(path, root.resolve()) or not path.is_file():
            raise PolicyError(f"source file escapes or is unavailable: {relative_text}")
        inventory[relative_text] = _sha256(path)
    return inventory


def _source_inventory_fingerprint(inventory: Mapping[str, str]) -> str:
    digest = hashlib.sha256()
    for relative_text, sha256 in sorted(inventory.items()):
        digest.update(relative_text.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256))
    return digest.hexdigest()


def _worktree_source_fingerprint(root: Path, target: str) -> str:
    """Hash the raw loaded solver, helpers, test, conftests, and project config bytes."""
    return _source_inventory_fingerprint(_worktree_source_inventory(root, target))


def _validate_hex8sri_registered_source_identity(
    root: Path,
    entry: Mapping[str, Any],
    identity: Mapping[str, Any],
    target: str,
    inventory: Mapping[str, str],
    fingerprint: str,
) -> None:
    expected_identity = entry.get("source_identity")
    if (
        expected_identity != HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY
        or identity.get("branch") != HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY["branch"]
        or identity.get("head") != HEX8SRI_CONVERGENCE24_SOURCE_HEAD
        or identity.get("tree") != HEX8SRI_CONVERGENCE24_SOURCE_TREE
        or fingerprint != HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT
    ):
        raise PolicyError("HEX8-SRI registered science HEAD, tree or raw-byte fingerprint is stale")
    relative = Path(HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_PATH)
    inventory_path = (ROOT / relative).resolve()
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not _is_within(inventory_path, ROOT.resolve())
        or not inventory_path.is_file()
        or _sha256(inventory_path) != HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_SHA256
    ):
        raise PolicyError("HEX8-SRI raw-byte source inventory is missing or has changed")
    try:
        recorded = _read_strict_json(inventory_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyError(f"HEX8-SRI raw-byte source inventory is invalid: {exc}") from exc
    inventory_checks = {
        "schema": isinstance(recorded, Mapping)
        and recorded.get("schema") == "qfsolver-hex8sri-source-byte-inventory-v1",
        "branch": recorded.get("branch") == identity.get("branch"),
        "head": recorded.get("head") == identity.get("head"),
        "tree": recorded.get("tree") == identity.get("tree"),
        "fingerprint": recorded.get("fingerprint_sha256") == fingerprint,
        "fingerprint_algorithm": recorded.get("fingerprint_algorithm")
        == "sha256(sorted(relative_path_utf8 + NUL + raw_file_sha256_bytes))",
        "raw_byte_policy": recorded.get("raw_byte_policy")
        == "Raw checkout bytes; no LF/CRLF normalization or conversion.",
        "file_count": recorded.get("inventory_file_count") == len(inventory),
        "files_sha256": recorded.get("files_sha256") == dict(inventory),
    }
    failed_checks = [name for name, passed in inventory_checks.items() if not passed]
    if failed_checks:
        raise PolicyError(
            "HEX8-SRI source bytes differ from the registered raw-byte inventory: "
            + ", ".join(failed_checks)
        )


def _reserve_node_attempt(
    ledger_path: Path,
    lock_path: Path,
    *,
    mandate_id: str,
    worktree_id: str,
    target: str,
    series_id: str,
    source_fingerprint: str,
    reason: str,
    maximum: int,
    total_maximum: int | None = None,
    wp12_selection: Mapping[str, Any] | None = None,
    authorization_id: str | None = None,
    owner_decision_id: str | None = None,
    predecessor: Mapping[str, str] | None = None,
    controller_fingerprint: str | None = None,
    attempt_basis: str | None = None,
    hypothesis_id: str | None = None,
    expected_ledger_sha256: str | None = None,
    require_ledger_snapshot: bool = False,
    batch_binding: Mapping[str, Any] | None = None,
) -> tuple[str, int]:
    key = f"{mandate_id}:{worktree_id}:{target}"
    schema = "qfsolver-development-node-ledger-v2" if predecessor is not None else "qfsolver-development-node-ledger-v1"
    if worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
        expected_predecessor = {
            "path": str(WP12B_HEX20_R1_LEDGER_PATH.resolve()),
            "sha256": WP12B_HEX20_R1_LEDGER_SHA256,
            "mandate_id": WP12B_HEX20_R1_MANDATE_ID,
        }
        if (
            mandate_id != WP12B_HEX20_R2_MANDATE_ID
            or target != WP12B_HEX20_DIAGNOSTIC_NODEID
            or predecessor != expected_predecessor
            or maximum != 1
            or total_maximum != 1
            or not require_ledger_snapshot
            or not isinstance(authorization_id, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", authorization_id)
            or not isinstance(owner_decision_id, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", owner_decision_id)
            or not re.fullmatch(r"[0-9a-f]{64}", source_fingerprint)
            or not isinstance(controller_fingerprint, str)
            or not re.fullmatch(r"[0-9a-f]{64}", controller_fingerprint)
        ):
            raise PolicyError("WP12-B HEX20 R2 reservation identity, predecessor, authorization or budget mismatch")
        _validate_wp12b_hex20_r2_ledger_binding(
            predecessor_path=WP12B_HEX20_R1_LEDGER_PATH, ledger_path=ledger_path, lock_path=lock_path
        )
    with _node_attempt_locks(ledger_path, lock_path, worktree_id):
        if worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
            _validate_wp12b_hex20_r2_ledger_binding(
                predecessor_path=WP12B_HEX20_R1_LEDGER_PATH, ledger_path=ledger_path, lock_path=lock_path
            )
        if batch_binding is not None:
            required_batch_fields = {
                "campaign_id",
                "contract_path",
                "contract_sha256",
                "decision_path",
                "decision_id",
                "decision_sha256",
                "case_ordinal",
                "nodeid",
                "case_manifest_path",
                "case_manifest_sha256",
                "preflight_id",
                "preflight_receipt_sha256",
                "authorization_id",
                "prepared_manifest_path",
                "prepared_manifest_sha256",
            }
            if (
                worktree_id != "wp12_dynamics"
                or set(batch_binding) != required_batch_fields
                or batch_binding.get("nodeid") != target
                or batch_binding.get("authorization_id") != authorization_id
                or batch_binding.get("decision_id") != owner_decision_id
                or any(
                    not re.fullmatch(r"[0-9a-f]{64}", str(batch_binding.get(field, "")))
                    for field in (
                        "contract_sha256",
                        "decision_sha256",
                        "case_manifest_sha256",
                        "preflight_receipt_sha256",
                        "prepared_manifest_sha256",
                    )
                )
                or not isinstance(batch_binding.get("case_ordinal"), int)
                or batch_binding["case_ordinal"] < 1
                or any(not isinstance(batch_binding.get(field), str) for field in (
                    "contract_path", "decision_path", "case_manifest_path", "prepared_manifest_path"
                ))
            ):
                raise PolicyError("WP12-A P0 batch attempt provenance is malformed")
        if require_ledger_snapshot:
            current_ledger_sha256 = _sha256(ledger_path) if ledger_path.is_file() else None
            if current_ledger_sha256 != expected_ledger_sha256:
                raise PolicyError("development attempt ledger changed before reservation")
        if ledger_path.exists():
            try:
                ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PolicyError(f"development attempt ledger is unreadable: {exc}") from exc
        else:
            ledger = {"schema": schema, "mandate_id": mandate_id, "entries": {}}
            if predecessor is not None:
                ledger["predecessor"] = dict(predecessor)
        if (
            not isinstance(ledger, dict)
            or ledger.get("schema") != schema
            or ledger.get("mandate_id") != mandate_id
            or not isinstance(ledger.get("entries"), dict)
            or (predecessor is not None and ledger.get("predecessor") != dict(predecessor))
        ):
            raise PolicyError("development attempt ledger identity/schema mismatch")
        if worktree_id == WP12B_HEX20_R2_WORKTREE_ID and (
            set(ledger) != {"schema", "mandate_id", "entries", "predecessor"}
            or set(ledger["entries"]) - {key}
            or not all(isinstance(items, list) and len(items) <= 1 for items in ledger["entries"].values())
        ):
            raise PolicyError("WP12-B HEX20 R2 ledger contains invalid or foreign attempts")
        predecessor_counts: dict[str, int] = {}
        predecessor_total = 0
        predecessor_ledger: dict[str, Any] | None = None
        if worktree_id == "wp12_dynamics":
            if predecessor is None:
                raise PolicyError("WP12-A dynamics reservations require the linked historical ledger")
            if ledger_path.name != WP12_DYNAMICS_LEDGER:
                raise PolicyError("WP12-A dynamics reservations require the mandate-specific ledger path")
            registered_entry = load_policy()["worktrees"]["wp12_dynamics"]
            configured_predecessor = registered_entry["node_attempt_ledger"]["predecessor"]
            if (
                dict(predecessor) != configured_predecessor
                or mandate_id != registered_entry["development_mandate_id"]
                or maximum != int(registered_entry["attempt_limit_per_nodeid"])
                or total_maximum != int(registered_entry["max_total_attempts"])
            ):
                raise PolicyError("WP12-A dynamics reservation differs from its registered ledger mandate or budgets")
            _predecessor_path, predecessor_ledger, predecessor_counts, predecessor_total = (
                _wp12_dynamics_predecessor_history(
                    ledger_path.parent,
                    predecessor,
                    allowed_nodeids=set(registered_entry["allowed_nodeids"]),
                )
            )
            _validate_wp12_dynamics_ledger(
                ledger,
                mandate_id=mandate_id,
                predecessor=predecessor,
                allowed_nodeids=set(registered_entry["allowed_nodeids"]),
                predecessor_counts=predecessor_counts,
                predecessor_total=predecessor_total,
                attempt_limit=maximum,
                total_limit=total_maximum or int(registered_entry["max_total_attempts"]),
            )
        attempts = ledger["entries"].setdefault(key, [])
        if not isinstance(attempts, list):
            raise PolicyError("development attempt ledger entry is malformed")
        inherited_node_attempts = predecessor_counts.get(target, 0)
        if inherited_node_attempts + len(attempts) >= maximum:
            raise PolicyError(f"development mandate exhausted {maximum} attempts for this nodeid")
        if total_maximum is not None:
            mission_prefix = f"{mandate_id}:{worktree_id}:"
            mission_records = [
                item
                for ledger_key, items in ledger["entries"].items()
                if ledger_key.startswith(mission_prefix) and isinstance(items, list)
                for item in items
                if isinstance(item, dict)
            ]
            if authorization_id is not None and any(
                item.get("authorization_id") == authorization_id for item in mission_records
            ):
                raise PolicyError("WP12 execution manifest authorization ID has already been consumed")
            historical_prefix = f"{predecessor['mandate_id']}:{worktree_id}:" if predecessor is not None else None
            historical_records = (
                [
                    item
                    for ledger_key, items in predecessor_ledger["entries"].items()
                    if historical_prefix is not None and ledger_key.startswith(historical_prefix)
                    for item in items
                    if isinstance(item, dict)
                ]
                if predecessor_ledger is not None
                else []
            )
            if authorization_id is not None and any(
                item.get("authorization_id") == authorization_id for item in historical_records
            ):
                raise PolicyError("WP12 execution manifest authorization ID was already consumed by its predecessor")
            total_attempts = predecessor_total + sum(
                len(items)
                for ledger_key, items in ledger["entries"].items()
                if ledger_key.startswith(mission_prefix) and isinstance(items, list)
            )
            if total_attempts >= total_maximum:
                raise PolicyError(f"development mandate exhausted its {total_maximum}-attempt mission cap")
        if worktree_id == "d01" and mandate_id.endswith("-v2-d01"):
            if attempt_basis not in D01_ATTEMPT_BASES or controller_fingerprint is None:
                raise PolicyError("D01 v2 attempts require a classified change basis and controller fingerprint")
            if attempt_basis == "new_diagnostic_hypothesis":
                if not hypothesis_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}", hypothesis_id):
                    raise PolicyError("a new diagnostic hypothesis requires a concise unique hypothesis ID")
                if any(item.get("hypothesis_id") == hypothesis_id for item in attempts):
                    raise PolicyError("D01 diagnostic hypothesis ID has already been used for this nodeid")
            elif hypothesis_id is not None:
                raise PolicyError("hypothesis_id is only valid for the new_diagnostic_hypothesis basis")
            if not attempts and attempt_basis != "baseline":
                raise PolicyError("the first D01 v2 attempt must be classified as baseline")
            if attempts:
                if attempt_basis == "baseline":
                    raise PolicyError("baseline is only valid for the first D01 attempt")
                last = attempts[-1]
                same_inputs = (
                    last.get("source_fingerprint") == source_fingerprint
                    and last.get("controller_fingerprint") == controller_fingerprint
                )
                if (
                    attempt_basis in {"source_change", "instrumentation_change"}
                    and last.get("source_fingerprint") == source_fingerprint
                ):
                    raise PolicyError(f"{attempt_basis} requires a changed D01 source fingerprint")
                if (
                    attempt_basis == "launcher_correction"
                    and last.get("controller_fingerprint") == controller_fingerprint
                ):
                    raise PolicyError("launcher_correction requires a changed controller fingerprint")
                if same_inputs and attempt_basis != "new_diagnostic_hypothesis":
                    raise PolicyError("identical D01 inputs require a separately identified new diagnostic hypothesis")
                if (
                    same_inputs
                    and last.get("attempt_basis") == attempt_basis
                    and last.get("hypothesis_id") == hypothesis_id
                ):
                    raise PolicyError("identical D01 attempt basis/hypothesis refused")
        elif attempts:
            last = attempts[-1]
            if last.get("source_fingerprint") == source_fingerprint and last.get("reason") == reason:
                raise PolicyError("identical repeat refused: change the source or document a new diagnostic hypothesis")
        number = len(attempts) + 1
        record = {
            "attempt": number,
            "series_id": series_id,
            "source_fingerprint": source_fingerprint,
            "controller_fingerprint": controller_fingerprint,
            "attempt_basis": attempt_basis,
            "hypothesis_id": hypothesis_id,
            "reason": reason,
            "wp12_selection": dict(wp12_selection) if wp12_selection is not None else None,
            "authorization_id": authorization_id,
            "state": "RESERVED",
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        if owner_decision_id is not None:
            record["owner_decision_id"] = owner_decision_id
        if batch_binding is not None:
            record["batch"] = dict(batch_binding)
        if worktree_id == "wp12_dynamics":
            record["predecessor_attempts_for_nodeid"] = inherited_node_attempts
        attempts.append(record)
        _atomic_json(ledger_path, ledger)
    return key, number


def _complete_node_attempt(
    ledger_path: Path,
    lock_path: Path,
    *,
    key: str,
    attempt_number: int,
    state: str,
    finished_at_utc: str,
    post_fingerprint: str,
    worktree_id: str = "",
    expected_ledger_sha256: str | None = None,
) -> None:
    with _node_attempt_locks(ledger_path, lock_path, worktree_id):
        if worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
            _validate_wp12b_hex20_r2_ledger_binding(
                predecessor_path=WP12B_HEX20_R1_LEDGER_PATH, ledger_path=ledger_path, lock_path=lock_path
            )
        if expected_ledger_sha256 is not None and _sha256(ledger_path) != expected_ledger_sha256:
            raise PolicyError("development attempt ledger changed before batch attempt completion")
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            attempts = ledger["entries"][key]
            record = attempts[attempt_number - 1]
        except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise PolicyError(f"cannot finalize development attempt ledger: {exc}") from exc
        record["state"] = state
        record["finished_at_utc"] = finished_at_utc
        record["post_source_fingerprint"] = post_fingerprint
        _atomic_json(ledger_path, ledger)


def _registered_worktree(
    worktree_id: str,
    target: str,
    policy: Mapping[str, Any],
) -> tuple[dict[str, Any], Path, Path, dict[str, Any], str]:
    try:
        entry = policy["worktrees"][worktree_id]
    except KeyError as exc:
        raise PolicyError("unknown registered worktree") from exc
    root = _registered_root(entry["root"], strict=True)
    git_root = _registered_root(entry["git_root"], strict=True)
    if root != git_root:
        raise PolicyError("registered worktree/Git root identity changed")
    source_root = (root / entry["source_root"]).resolve(strict=True)
    expected_init = (source_root / "solveur" / "__init__.py").resolve(strict=True)
    if not _is_within(source_root, root) or not expected_init.is_file():
        raise PolicyError("registered solver package is missing or outside its source root")
    test_module = (root / target.split("::", maxsplit=1)[0]).resolve(strict=True)
    test_root = (root / entry["pytest_root"]).resolve(strict=True)
    if (
        not _wp12_nodeid_module_within_scope(worktree_id, target, test_module, root, test_root)
        or not test_module.is_file()
    ):
        raise PolicyError("registered test module is missing or escaped its worktree")
    identity = _git_identity(
        root,
        expected_branch=entry["branch"],
        baseline_commit=entry["baseline_commit"],
    )
    if entry.get("require_clean_worktree") and identity["status_short"]:
        raise PolicyError(f"registered {worktree_id} source worktree must be clean before collection or execution")
    if worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID:
        inventory = _worktree_source_inventory(root, target)
        fingerprint = _source_inventory_fingerprint(inventory)
        _validate_hex8sri_registered_source_identity(root, entry, identity, target, inventory, fingerprint)
    else:
        fingerprint = _worktree_source_fingerprint(root, target)
    if worktree_id == VV3D_R2_WORKTREE_ID and (
        identity.get("branch") != VV3D_R2_SOURCE_IDENTITY["branch"]
        or identity.get("head") != VV3D_R2_SOURCE_IDENTITY["head"]
        or identity.get("tree") != VV3D_R2_SOURCE_IDENTITY["tree"]
        or fingerprint != VV3D_R2_SOURCE_IDENTITY["fingerprint_sha256"]
        or entry.get("source_identity") != VV3D_R2_SOURCE_IDENTITY
        or entry.get("source_fingerprint_sha256") != fingerprint
    ):
        raise PolicyError("VV3D R2 science source identity or raw source fingerprint is stale")
    return entry, root, source_root, identity, fingerprint


def _run_root(policy: Mapping[str, Any], worktree_id: str | None = None) -> Path:
    if worktree_id in WP12_OWNER_ENVELOPES:
        root = Path(policy["worktrees"][worktree_id]["evidence_root"]).resolve()
        checkout = Path(policy["worktrees"][worktree_id]["git_root"]).resolve()
        coordination_root = WP12_COORDINATION_ROOT.resolve()
        if _is_within(root, checkout) or _is_within(root, coordination_root) or _is_within(coordination_root, root):
            raise PolicyError("WP12 evidence must be separate from source and shared coordination roots")
        return root
    if worktree_id in {VV3D_WORKTREE_ID, VV3D_R2_WORKTREE_ID}:
        root = Path(policy["worktrees"][worktree_id]["evidence_root"]).resolve()
        checkout = Path(policy["worktrees"][worktree_id]["git_root"]).resolve()
        coordination_root = WP12_COORDINATION_ROOT.resolve()
        if _is_within(root, checkout) or _is_within(root, coordination_root) or _is_within(coordination_root, root):
            raise PolicyError("VV3D evidence must be separate from source and shared coordination roots")
        return root
    root = (ROOT / policy["run_store"]).resolve()
    if not _is_within(root, ROOT.resolve()) or _is_within(root, (ROOT / "qualification").resolve()):
        raise PolicyError("development run store must be inside the worktree and outside qualification")
    return root


def _wp12_dynamics_predecessor_history(
    store: Path,
    predecessor: Mapping[str, str],
    *,
    allowed_nodeids: set[str] | None = None,
) -> tuple[Path, dict[str, Any], dict[str, int], int]:
    """Read the immutable generic ledger and count its WP12 dynamics attempts."""
    if (
        set(predecessor) != {"path", "sha256", "mandate_id"}
        or predecessor.get("path") != "node-attempt-ledger.json"
        or predecessor.get("mandate_id") != WP12_DYNAMICS_LEGACY_MANDATE_ID
        or not re.fullmatch(r"[0-9a-f]{64}", str(predecessor.get("sha256", "")))
    ):
        raise PolicyError("WP12-A dynamics predecessor ledger identity is invalid")
    predecessor_path = (store / predecessor["path"]).resolve()
    ledger_path = (store / WP12_DYNAMICS_LEDGER).resolve()
    if (
        not _is_within(predecessor_path, store.resolve())
        or predecessor_path == ledger_path
        or not predecessor_path.is_file()
    ):
        raise PolicyError("the historical WP12-A dynamics ledger is missing or outside its evidence root")
    if _sha256(predecessor_path) != predecessor["sha256"]:
        raise PolicyError("the historical WP12-A dynamics ledger changed; refusing to start a new mandate ledger")
    try:
        historical = json.loads(predecessor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"the historical WP12-A dynamics ledger is unreadable: {exc}") from exc
    if (
        not isinstance(historical, dict)
        or historical.get("schema") != "qfsolver-development-node-ledger-v1"
        or historical.get("mandate_id") != predecessor["mandate_id"]
        or not isinstance(historical.get("entries"), dict)
    ):
        raise PolicyError("the historical WP12-A dynamics ledger does not match its declared identity")

    prefix = f"{predecessor['mandate_id']}:wp12_dynamics:"
    counts: dict[str, int] = {}
    total = 0
    for key, attempts in historical["entries"].items():
        if not isinstance(key, str) or not key.startswith(prefix):
            raise PolicyError("the historical WP12-A ledger contains an entry from another mandate or scope")
        target = key[len(prefix) :]
        if (allowed_nodeids is not None and target not in allowed_nodeids) or not isinstance(attempts, list):
            raise PolicyError("the historical WP12-A ledger contains an unregistered node or malformed attempts")
        for index, attempt in enumerate(attempts, start=1):
            if not isinstance(attempt, Mapping) or attempt.get("attempt") != index:
                raise PolicyError("the historical WP12-A ledger contains a malformed attempt record")
        counts[target] = len(attempts)
        total += len(attempts)
    return predecessor_path, historical, counts, total


def _validate_wp12_dynamics_ledger(
    ledger: Any,
    *,
    mandate_id: str,
    predecessor: Mapping[str, str],
    allowed_nodeids: set[str],
    predecessor_counts: Mapping[str, int],
    predecessor_total: int,
    attempt_limit: int,
    total_limit: int,
) -> None:
    if (
        not isinstance(ledger, dict)
        or ledger.get("schema") != "qfsolver-development-node-ledger-v2"
        or ledger.get("mandate_id") != mandate_id
        or ledger.get("predecessor") != dict(predecessor)
        or not isinstance(ledger.get("entries"), dict)
    ):
        raise PolicyError("WP12-A dynamics attempt ledger identity/schema mismatch")
    prefix = f"{mandate_id}:wp12_dynamics:"
    current_total = 0
    for key, attempts in ledger["entries"].items():
        if not isinstance(key, str) or not key.startswith(prefix):
            raise PolicyError("WP12-A dynamics ledger contains an entry from another scope or mandate")
        target = key[len(prefix) :]
        if target not in allowed_nodeids or not isinstance(attempts, list):
            raise PolicyError("WP12-A dynamics ledger contains an unregistered node or malformed attempts")
        for index, attempt in enumerate(attempts, start=1):
            if not isinstance(attempt, Mapping) or attempt.get("attempt") != index:
                raise PolicyError("WP12-A dynamics ledger contains a malformed attempt record")
        if predecessor_counts.get(target, 0) + len(attempts) > attempt_limit:
            raise PolicyError("WP12-A dynamics ledger exceeds its inherited per-node attempt limit")
        current_total += len(attempts)
    if predecessor_total + current_total > total_limit:
        raise PolicyError("WP12-A dynamics ledger exceeds its inherited mission attempt limit")


def _validate_wp12b_hex20_r1_predecessor(path: Path) -> dict[str, Any]:
    """Read the immutable R1 ledger before any future R2 activity; never write it."""
    if not path.is_file() or _sha256(path) != WP12B_HEX20_R1_LEDGER_SHA256:
        raise PolicyError("WP12-B HEX20 R1 predecessor ledger is missing or has a different SHA-256")
    try:
        ledger = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyError(f"WP12-B HEX20 R1 predecessor ledger is unreadable: {exc}") from exc
    key = f"{WP12B_HEX20_R1_MANDATE_ID}:{WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID}:{WP12B_HEX20_DIAGNOSTIC_NODEID}"
    entries = ledger.get("entries") if isinstance(ledger, dict) else None
    if (
        not isinstance(ledger, dict)
        or ledger.get("schema") != "qfsolver-development-node-ledger-v1"
        or ledger.get("mandate_id") != WP12B_HEX20_R1_MANDATE_ID
        or not isinstance(entries, dict)
        or set(entries) != {key}
        or not isinstance(entries[key], list)
        or len(entries[key]) != 1
        or not isinstance(entries[key][0], dict)
        or entries[key][0].get("attempt") != 1
        or entries[key][0].get("state") != "PROVENANCE_MISMATCH"
    ):
        raise PolicyError("WP12-B HEX20 R1 predecessor ledger has an incompatible history")
    return ledger


def _validate_wp12b_hex20_r2_ledger_binding(
    *, predecessor_path: Path, ledger_path: Path, lock_path: Path
) -> dict[str, Any]:
    """Validate the read-only R1 link and prevent R2 paths aliasing R1.

    The caller must repeat this check under the R2 reservation lock before
    writing an R2 record. This check alone does not register or authorize R2.
    """
    predecessor = predecessor_path.resolve()
    ledger = ledger_path.resolve()
    lock = lock_path.resolve()
    if len({predecessor, ledger, lock}) != 3:
        raise PolicyError("WP12-B HEX20 R2 ledger and lock must be distinct from the R1 ledger")
    for left, right in ((ledger_path, predecessor_path), (lock_path, predecessor_path), (ledger_path, lock_path)):
        if left.exists() and right.exists():
            try:
                if left.samefile(right):
                    raise PolicyError("WP12-B HEX20 R2 ledger paths alias the same file")
            except OSError as exc:
                raise PolicyError(f"WP12-B HEX20 ledger identity cannot be verified: {exc}") from exc
    return _validate_wp12b_hex20_r1_predecessor(predecessor_path)


def _node_ledger_context(
    policy: Mapping[str, Any],
    store: Path,
    worktree_id: str,
) -> tuple[Path, Path, str, dict[str, str] | None]:
    entry = policy["worktrees"][worktree_id]
    if worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
        config = entry.get("node_attempt_ledger")
        expected_predecessor = {
            "path": str(WP12B_HEX20_R1_LEDGER_PATH.resolve()),
            "sha256": WP12B_HEX20_R1_LEDGER_SHA256,
            "mandate_id": WP12B_HEX20_R1_MANDATE_ID,
        }
        if not isinstance(config, Mapping) or config.get("path") != "node-attempt-ledger-r2.json":
            raise PolicyError("WP12-B HEX20 R2 requires its dedicated ledger")
        if config.get("predecessor") != expected_predecessor:
            raise PolicyError("WP12-B HEX20 R2 predecessor binding is invalid")
        ledger_path = (store / config["path"]).resolve()
        lock_path = ledger_path.with_suffix(".lock")
        if not _is_within(ledger_path, store.resolve()):
            raise PolicyError("WP12-B HEX20 R2 ledger escapes its evidence root")
        _validate_wp12b_hex20_r2_ledger_binding(
            predecessor_path=WP12B_HEX20_R1_LEDGER_PATH, ledger_path=ledger_path, lock_path=lock_path
        )
        if ledger_path.exists():
            ledger = _read_strict_json(ledger_path)
            expected_key = f"{WP12B_HEX20_R2_MANDATE_ID}:{worktree_id}:{WP12B_HEX20_DIAGNOSTIC_NODEID}"
            if (not isinstance(ledger, dict) or set(ledger) != {"schema", "mandate_id", "entries", "predecessor"}
                    or ledger.get("schema") != "qfsolver-development-node-ledger-v2"
                    or ledger.get("mandate_id") != WP12B_HEX20_R2_MANDATE_ID
                    or ledger.get("predecessor") != expected_predecessor
                    or not isinstance(ledger.get("entries"), dict)
                    or set(ledger["entries"]) - {expected_key}
                    or any(not isinstance(items, list) or len(items) > 1 for items in ledger["entries"].values())):
                raise PolicyError("WP12-B HEX20 R2 ledger identity or entries are invalid")
        return ledger_path, lock_path, WP12B_HEX20_R2_MANDATE_ID, expected_predecessor
    if worktree_id == "wp12_dynamics":
        config = entry.get("node_attempt_ledger")
        if not isinstance(config, Mapping) or config.get("path") != WP12_DYNAMICS_LEDGER:
            raise PolicyError("WP12-A dynamics requires its mandate-specific ledger configuration")
        predecessor = config.get("predecessor")
        if not isinstance(predecessor, Mapping):
            raise PolicyError("WP12-A dynamics requires an immutable historical ledger predecessor")
        ledger_path = (store / WP12_DYNAMICS_LEDGER).resolve()
        if not _is_within(ledger_path, store.resolve()):
            raise PolicyError("WP12-A dynamics ledger must be confined to its evidence root")
        _predecessor_path, _historical, predecessor_counts, predecessor_total = _wp12_dynamics_predecessor_history(
            store,
            predecessor,
            allowed_nodeids=set(entry["allowed_nodeids"]),
        )
        if ledger_path.is_file():
            try:
                current = json.loads(ledger_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PolicyError(f"WP12-A dynamics attempt ledger is unreadable: {exc}") from exc
            _validate_wp12_dynamics_ledger(
                current,
                mandate_id=str(entry["development_mandate_id"]),
                predecessor=predecessor,
                allowed_nodeids=set(entry["allowed_nodeids"]),
                predecessor_counts=predecessor_counts,
                predecessor_total=predecessor_total,
                attempt_limit=int(entry["attempt_limit_per_nodeid"]),
                total_limit=int(entry["max_total_attempts"]),
            )
        return (
            ledger_path,
            ledger_path.with_suffix(".lock"),
            str(entry["development_mandate_id"]),
            dict(predecessor),
        )
    if worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID:
        ledger_path = (store / entry["node_attempt_ledger"]["path"]).resolve()
        if (
            not _is_within(ledger_path, store.resolve())
            or ledger_path == (store / "node-attempt-ledger.json").resolve()
        ):
            raise PolicyError("HEX8-SRI convergence ledger must be separate and confined to its run store")
        return (
            ledger_path,
            ledger_path.with_suffix(".lock"),
            str(entry["development_mandate_id"]),
            None,
        )
    if worktree_id != "d01" or "node_attempt_ledger" not in entry:
        return (
            store / "node-attempt-ledger.json",
            store / "node-attempt-ledger.lock",
            str(entry.get("development_mandate_id", policy["mandate_id"])),
            None,
        )

    config = entry["node_attempt_ledger"]
    predecessor = dict(config["predecessor"])
    predecessor_path = (store / predecessor["path"]).resolve()
    if not _is_within(predecessor_path, store.resolve()) or not predecessor_path.is_file():
        raise PolicyError("the historical D01 ledger predecessor is missing or outside the run store")
    predecessor_hash = _sha256(predecessor_path)
    if predecessor_hash != predecessor["sha256"]:
        raise PolicyError("the historical D01 ledger changed; refusing to start a new envelope")
    try:
        historical = json.loads(predecessor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"the historical D01 ledger is unreadable: {exc}") from exc
    if (
        not isinstance(historical, dict)
        or historical.get("schema") != "qfsolver-development-node-ledger-v1"
        or historical.get("mandate_id") != predecessor["mandate_id"]
        or not isinstance(historical.get("entries"), dict)
    ):
        raise PolicyError("the historical D01 ledger does not match its declared predecessor identity")
    historical_m3_key = f"{predecessor['mandate_id']}:d01:{D01_NATIVE_NODEIDS[2]}"
    historical_m3 = historical["entries"].get(historical_m3_key)
    if not isinstance(historical_m3, list) or len(historical_m3) != 3:
        raise PolicyError("the historical ledger does not contain exactly three preserved M3 attempts")
    ledger_path = (store / config["path"]).resolve()
    if not _is_within(ledger_path, store.resolve()) or ledger_path == predecessor_path:
        raise PolicyError("the new D01 ledger must be separate from the historical ledger")
    return (
        ledger_path,
        ledger_path.with_suffix(".lock"),
        str(entry["development_mandate_id"]),
        predecessor,
    )


def _series_root(store: Path, scope_name: str, worktree_id: str | None) -> Path:
    if worktree_id is not None:
        if worktree_id not in {"d01", "c01", "e01", VV3D_WORKTREE_ID, VV3D_R2_WORKTREE_ID, *WP12_OWNER_ENVELOPES}:
            raise PolicyError("unknown worktree output namespace")
        return store / "worktrees" / worktree_id
    if scope_name not in STANDARD_SCOPES:
        raise PolicyError("standard output namespace requires a fixed local test scope")
    return store / "standard" / scope_name


@contextmanager
def _wp12_resource_lock(store: Path, concurrency_class: str) -> Iterator[None]:
    """Reserve one of three shared FEM slots, or every slot for an exclusive run."""
    if concurrency_class not in {"parallel", "exclusive"}:
        raise PolicyError("unknown WP12 FEM concurrency class")
    lock_root = store / "fem-slots"
    with ExitStack() as stack:
        acquired = 0
        for index in range(WP12_MAX_PARALLEL_FEM_SLOTS):
            try:
                stack.enter_context(_exclusive_file_lock(lock_root / f"slot-{index}.lock"))
                acquired += 1
                if concurrency_class == "parallel":
                    break
            except PolicyError:
                if concurrency_class == "exclusive":
                    raise
        if acquired == 0:
            raise PolicyError("all shared WP12 FEM resource slots are busy")
        yield


def register_wp12_nodeid(
    worktree_id: str,
    target: str,
    reason: str,
    *,
    selected_dofs: int,
    selection_basis: str,
    timeout_seconds: int | None = None,
    timeout_reason: str | None = None,
) -> dict[str, Any]:
    """Register one inspected exact WP12 pytest function and its preselected case envelope."""
    if worktree_id not in WP12_OWNER_ENVELOPES:
        raise PolicyError("controlled nodeid registration is available only for registered WP12 scopes")
    if not isinstance(reason, str) or not 8 <= len(reason.strip()) <= 300 or "\n" in reason or "\r" in reason:
        raise PolicyError("nodeid registration requires a one-line reason of 8 to 300 characters")
    selection = _validate_wp12_case_selection(
        worktree_id,
        selected_dofs=selected_dofs,
        selection_basis=selection_basis,
        timeout_seconds=timeout_seconds,
        timeout_reason=timeout_reason,
    )
    if not isinstance(target, str) or len(target) > 512 or target.count("::") != 1:
        raise PolicyError("registration requires one exact repository-relative pytest nodeid")
    match = _validate_wp12_nodeid_syntax(target, worktree_id=worktree_id)
    module_name = target.split("::", maxsplit=1)[0]
    module_path = Path(module_name)

    policy = load_policy(POLICY_PATH)
    entry = policy["worktrees"][worktree_id]
    root = Path(entry["git_root"]).resolve(strict=True)
    identity = _git_identity(
        root,
        expected_branch=entry["branch"],
        baseline_commit=entry["baseline_commit"],
    )
    if entry.get("require_clean_worktree") and identity["status_short"]:
        raise PolicyError(f"registered {worktree_id} source worktree must be clean before nodeid inspection")
    source_root = (root / entry["source_root"]).resolve(strict=True)
    if (
        not _is_within(source_root / "solveur" / "__init__.py", root)
        or not (source_root / "solveur" / "__init__.py").is_file()
    ):
        raise PolicyError("registered solver source root is not inside the exact worktree")
    module_file = (root / module_path).resolve(strict=True)
    tests_root = (root / entry["pytest_root"]).resolve(strict=True)
    if (
        not _wp12_nodeid_module_within_scope(worktree_id, target, module_file, root, tests_root)
        or not module_file.is_file()
    ):
        raise PolicyError("registered nodeid module is missing or escaped its approved test scope")
    function_name = match.group(1)
    try:
        syntax_tree = ast.parse(module_file.read_text(encoding="utf-8"), filename=str(module_file))
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise PolicyError(f"cannot inspect nodeid test module without importing it: {exc}") from exc
    if not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
        for node in ast.walk(syntax_tree)
    ):
        raise PolicyError("registered nodeid does not name a test function in its exact module")

    lock_path = WP12_COORDINATION_ROOT / "locks" / "nodeid-registration.lock"
    with _exclusive_file_lock(lock_path):
        policy = load_policy(POLICY_PATH)
        entry = policy["worktrees"][worktree_id]
        nodeids = entry["allowed_nodeids"]
        records = entry.setdefault("nodeid_registration_records", [])
        current_identity = _git_identity(
            root,
            expected_branch=entry["branch"],
            baseline_commit=entry["baseline_commit"],
        )
        if entry.get("require_clean_worktree") and current_identity["status_short"]:
            raise PolicyError(f"registered {worktree_id} source worktree must be clean before nodeid inspection")
        current_fingerprint = _worktree_source_fingerprint(root, target)
        current_test_dependencies = _test_source_dependency_inventory(root, module_name)
        previous = next((item for item in reversed(records) if item.get("target") == target), None)
        if (
            previous is not None
            and previous.get("source_fingerprint") == current_fingerprint
            and previous.get("test_source_dependencies") == current_test_dependencies
        ):
            raise PolicyError("nodeid and source revision are already registered")
        if target not in nodeids:
            if len(nodeids) >= entry["nodeid_registration"]["max_nodeids"]:
                raise PolicyError("nodeid registration cap is exhausted for this WP12 scope")
            nodeids.append(target)
        record = {
            "target": target,
            **({"campaign_id": entry["campaign_id"]} if "campaign_id" in entry else {}),
            "reason": reason.strip(),
            "registered_at_utc": datetime.now(timezone.utc).isoformat(),
            "worktree_head": current_identity["head"],
            "source_fingerprint": current_fingerprint,
            "test_source_dependencies": current_test_dependencies,
            **selection,
        }
        records.append(record)
        _atomic_json(POLICY_PATH, policy, sort_keys=False)
    return {
        "state": "NODEID_REGISTERED",
        "worktree_id": worktree_id,
        "target": target,
        "registered_count": len(nodeids),
        "registration_cap": entry["nodeid_registration"]["max_nodeids"],
        "selected_dofs": selection["selected_dofs"],
        "test_source_dependency_count": len(current_test_dependencies),
        "timeout_seconds": selection["timeout_seconds"],
        "revision": sum(item.get("target") == target for item in records),
        "policy": str(POLICY_PATH.resolve()),
    }


def _controller_provenance() -> dict[str, Any]:
    files = {
        "runner": Path(__file__).resolve(),
        "pytest_plugin": Path(__file__).with_name("development_autonomous_pytest_plugin.py").resolve(),
        "policy": POLICY_PATH.resolve(),
    }
    return {
        "identity": _git_identity(ROOT),
        "sha256": {name: _sha256(path) for name, path in files.items()},
        "runtime": {
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "pytest_version": importlib.metadata.version("pytest"),
            "psutil_version": importlib.metadata.version("psutil") if psutil is not None else None,
        },
    }


def _vv3d_controller_provenance() -> dict[str, Any]:
    """Bind VV3D's imported contract and ledger code without changing other scopes.

    The generic fingerprint is a long-lived identity used by existing scopes. VV3D
    executes two additional controller modules, so its scope-specific identity must
    include their raw bytes while leaving those older scope identities unchanged.
    """
    provenance = dict(_controller_provenance())
    hashes = dict(provenance.get("sha256", {}))
    for name in ("wp12_vv3d_contract", "wp12_vv3d_ledger"):
        path = Path(__file__).with_name(f"{name}.py").resolve(strict=True)
        hashes[name] = _sha256(path)
    provenance["sha256"] = hashes
    provenance["vv3d_provenance_revision"] = "vv3d-executable-components-v1"
    return provenance


def _vv3d_scope_controller_provenance(worktree_id: str) -> dict[str, Any]:
    """Keep the closed R1 identity stable while binding R2's independent ledger."""
    provenance = _vv3d_controller_provenance()
    if worktree_id == VV3D_R2_WORKTREE_ID:
        hashes = dict(provenance.get("sha256", {}))
        path = Path(__file__).with_name("wp12_vv3d_r2_ledger.py").resolve(strict=True)
        hashes["wp12_vv3d_r2_ledger"] = _sha256(path)
        provenance["sha256"] = hashes
        provenance["vv3d_r2_provenance_revision"] = "vv3d-r2-independent-ledger-v1"
    elif worktree_id != VV3D_WORKTREE_ID:
        raise PolicyError("VV3D controller identity is available only for registered R1 and R2 scopes")
    return provenance


def _hex8sri_convergence24_manifest(
    entry: Mapping[str, Any], execution_root: Path, target: str
) -> tuple[Path, dict[str, Any], str]:
    bindings = entry.get("case_manifests")
    binding = bindings.get(target) if isinstance(bindings, Mapping) else None
    if not isinstance(binding, Mapping):
        raise PolicyError("HEX8-SRI exact node has no registered case manifest")
    registered_path = str(binding.get("path", ""))
    if "{controller_head}" in registered_path:
        controller_identity = _git_identity(ROOT)
        controller_head = controller_identity.get("head")
        if controller_identity.get("status_short") or not isinstance(controller_head, str) or not re.fullmatch(r"[0-9a-f]{40}", controller_head):
            raise PolicyError("HEX8-SRI versioned manifest requires a clean controller HEAD")
        registered_path = registered_path.replace("{controller_head}", controller_head)
    if "{" in registered_path or "}" in registered_path:
        raise PolicyError("HEX8-SRI case manifest path has an invalid identity placeholder")
    relative = Path(registered_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise PolicyError("HEX8-SRI case manifest path is not worktree-relative")
    manifest_path = (execution_root / relative).resolve()
    if not _is_within(manifest_path, execution_root.resolve()) or not manifest_path.is_file():
        raise PolicyError("HEX8-SRI case manifest is missing or outside its registered worktree")
    raw_sha256 = _sha256(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"HEX8-SRI case manifest is unreadable: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PolicyError("HEX8-SRI case manifest must be a JSON object")
    try:
        registration_sha256 = _hex8sri_manifest_registration_sha256(manifest)
    except (TypeError, ValueError) as exc:
        raise PolicyError(f"HEX8-SRI manifest contains invalid canonical content: {exc}") from exc
    if registration_sha256 != binding.get("sha256"):
        raise PolicyError("HEX8-SRI case manifest registration digest differs from its registered value")
    live_fingerprint = _worktree_source_fingerprint(execution_root, target)
    case = _hex8sri_convergence24_case(target)
    if case is None:
        raise PolicyError("HEX8-SRI target is outside the exact convergence24 nodeid matrix")
    formulation, nu_token, mesh_token = case
    expected_case_id = f"{formulation}_nu_{nu_token}_{mesh_token}"
    formulation_record = manifest.get("formulation")
    if (
        manifest.get("schema") != "qfsolver-hex8-sri-structural-case-v2"
        or manifest.get("controller_registration_id") != entry.get("manifest_registration_id")
        or manifest.get("controller_campaign_scope_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        or manifest.get("campaign_id") != HEX8SRI_CONVERGENCE24_CAMPAIGN_ID
        or manifest.get("case_id") != expected_case_id
        or manifest.get("exact_nodeid") != target
        or manifest.get("source_fingerprint_sha256") != live_fingerprint
        or live_fingerprint != entry.get("source_fingerprint_sha256")
        or manifest.get("science_branch") != entry.get("branch")
        or not isinstance(formulation_record, Mapping)
        or formulation_record.get("id") != formulation
        or manifest.get("poisson_ratio") != HEX8SRI_CONVERGENCE24_NU_TOKENS[nu_token]
    ):
        raise PolicyError("HEX8-SRI manifest does not match its registered node, branch, source or case")
    common_problem = manifest.get("common_problem")
    common_relative = Path(str(common_problem.get("path", ""))) if isinstance(common_problem, Mapping) else Path()
    common_sha256 = common_problem.get("sha256") if isinstance(common_problem, Mapping) else None
    if (
        not isinstance(common_problem, Mapping)
        or not str(common_problem.get("path", ""))
        or common_relative.is_absolute()
        or ".." in common_relative.parts
        or not re.fullmatch(r"[0-9a-f]{64}", str(common_sha256 or ""))
    ):
        raise PolicyError("HEX8-SRI manifest has an invalid common-problem binding")
    common_path = (manifest_path.parent / common_relative).resolve()
    if not _is_within(common_path, execution_root.resolve()) or not common_path.is_file():
        raise PolicyError("HEX8-SRI common-problem file is missing or outside its worktree")
    if _sha256(common_path) != common_sha256:
        raise PolicyError("HEX8-SRI common-problem SHA-256 differs from its manifest")
    if manifest.get("execution_authorized") is not False or manifest.get("do_not_execute") is not True:
        raise PolicyError("HEX8-SRI manifest is not explicitly preparation-only")
    if manifest.get("execution_state") != "PREPARED_NOT_AUTHORIZED":
        raise PolicyError("HEX8-SRI manifest execution state is not PREPARED_NOT_AUTHORIZED")
    expected_budget = _hex8sri_convergence24_budget(target)
    if manifest.get("budgets") != {
        **expected_budget,
        "attempts_per_nodeid": 1,
        "initial_campaign_max_attempts": 24,
        "blas_thread_environment": entry["blas_thread_environment"],
        "budget_semantics": {
            "captured_output": "controller-enforced byte caps",
            "rss_process_temporary_archive": "sampled soft observations, not OS quotas",
            "wall_timeout": "watchdog process-tree termination, best effort",
        },
    }:
        raise PolicyError("HEX8-SRI manifest budget differs from its registered per-node envelope")
    return manifest_path, manifest, raw_sha256


def _verify_hex8sri_convergence24_controller_identity(
    manifest: Mapping[str, Any], controller: Mapping[str, Any]
) -> None:
    current_identity = controller.get("identity", {})
    current_hashes = controller.get("sha256", {})
    manifest_identity = manifest.get("controller_identity", {})
    manifest_hashes = manifest.get("controller_code_sha256", {})
    if (
        manifest.get("controller_identity_status") != "FINAL_CONTROLLER_IDENTITY_BOUND"
        or not isinstance(manifest_identity, Mapping)
        or not isinstance(manifest_hashes, Mapping)
        or manifest_identity.get("branch") != current_identity.get("branch")
        or manifest_identity.get("head") != current_identity.get("head")
        or manifest_hashes.get("runner") != current_hashes.get("runner")
        or manifest_hashes.get("pytest_plugin") != current_hashes.get("pytest_plugin")
        or manifest_hashes.get("policy") != current_hashes.get("policy")
        or manifest_identity.get("runner_sha256") != current_hashes.get("runner")
        or manifest_identity.get("pytest_plugin_sha256") != current_hashes.get("pytest_plugin")
        or manifest_identity.get("policy_sha256") != current_hashes.get("policy")
    ):
        raise PolicyError("HEX8-SRI convergence manifest is not bound to the final controller identity")


def _hex8sri_criteria_scope_for_nodeids(nodeids: Any) -> tuple[str, tuple[str, ...]] | None:
    if nodeids == list(HEX8SRI_FIRST6_NODEIDS):
        return HEX8SRI_CRITERIA_CONTRACT_REVISION, HEX8SRI_FIRST6_NODEIDS
    if nodeids == list(HEX8SRI_REFINED3_NODEIDS):
        return HEX8SRI_REFINED3_CRITERIA_CONTRACT_REVISION, HEX8SRI_REFINED3_NODEIDS
    return None


def _hex8sri_criteria_scope_for_target(target: str) -> tuple[str, tuple[str, ...]] | None:
    if target in HEX8SRI_FIRST6_NODEIDS:
        return HEX8SRI_CRITERIA_CONTRACT_REVISION, HEX8SRI_FIRST6_NODEIDS
    if target in HEX8SRI_REFINED3_NODEIDS:
        return HEX8SRI_REFINED3_CRITERIA_CONTRACT_REVISION, HEX8SRI_REFINED3_NODEIDS
    return None


def _hex8sri_registration_sha256_by_nodeid(
    entry: Mapping[str, Any], nodeids: Sequence[str]
) -> dict[str, str]:
    registrations = entry.get("case_manifests")
    if not isinstance(registrations, Mapping):
        raise PolicyError("HEX8-SRI registered case-manifest map is missing")
    result: dict[str, str] = {}
    for nodeid in nodeids:
        if nodeid not in entry.get("allowed_nodeids", ()):
            raise PolicyError("HEX8-SRI criteria scope contains an unregistered nodeid")
        binding = registrations.get(nodeid)
        sha256 = binding.get("sha256") if isinstance(binding, Mapping) else None
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise PolicyError("HEX8-SRI registered case-manifest digest is absent or malformed")
        result[nodeid] = sha256
    return result


def _hex8sri_first6_registration_sha256_by_nodeid(entry: Mapping[str, Any]) -> dict[str, str]:
    return _hex8sri_registration_sha256_by_nodeid(entry, HEX8SRI_FIRST6_NODEIDS)


def _hex8sri_expected_criteria_freeze(
    *,
    entry: Mapping[str, Any],
    source_fingerprint: str,
    controller_provenance: Mapping[str, Any],
    frozen_nodeids: Sequence[str] = HEX8SRI_FIRST6_NODEIDS,
) -> dict[str, Any]:
    scope = _hex8sri_criteria_scope_for_nodeids(list(frozen_nodeids))
    if scope is None:
        raise PolicyError("HEX8-SRI criteria freeze must select exactly one reviewed nodeid scope")
    revision, scope_nodeids = scope
    controller_identity = controller_provenance.get("identity", {})
    return {
        "schema": HEX8SRI_CRITERIA_FREEZE_SCHEMA,
        "revision": revision,
        "dispositions": HEX8SRI_CRITERIA_DISPOSITIONS,
        "criteria_definitions": HEX8SRI_CRITERIA_DEFINITIONS,
        "frozen_case_gate_criteria": HEX8SRI_FROZEN_CASE_GATE_CRITERIA,
        "frozen_nodeids": list(scope_nodeids),
        "case_manifest_registration_sha256_by_nodeid": _hex8sri_registration_sha256_by_nodeid(
            entry, scope_nodeids
        ),
        "scope_id": HEX8SRI_CONVERGENCE24_WORKTREE_ID,
        "mandate_id": entry.get("development_mandate_id"),
        "campaign_id": entry.get("campaign_id"),
        "source_identity": {
            "branch": HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY["branch"],
            "head": HEX8SRI_CONVERGENCE24_SOURCE_HEAD,
            "tree": HEX8SRI_CONVERGENCE24_SOURCE_TREE,
            "fingerprint_sha256": source_fingerprint,
        },
        "controller_fingerprint": _stable_fingerprint(controller_provenance),
        "controller_head": controller_identity.get("head"),
    }


def _validate_owner_decision_time(decision: Mapping[str, Any], *, execution: bool) -> None:
    def parse(field: str) -> datetime:
        try:
            value = datetime.fromisoformat(str(decision.get(field, "")).replace("Z", "+00:00"))
        except ValueError as exc:
            raise PolicyError(f"HEX8-SRI Owner {field} must be an ISO-8601 timestamp") from exc
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise PolicyError(f"HEX8-SRI Owner {field} must be expressed in UTC")
        return value

    now = datetime.now(timezone.utc)
    approved_at = parse("approved_at_utc")
    if approved_at > now:
        raise PolicyError("HEX8-SRI Owner approval time cannot be in the future")
    if execution:
        expires_at = parse("expires_at_utc")
        if expires_at <= now or expires_at <= approved_at:
            raise PolicyError("HEX8-SRI execution approval is expired or has an invalid validity interval")


def _validate_hex8sri_criteria_freeze_decision(
    decision: Any,
    *,
    entry: Mapping[str, Any],
    source_fingerprint: str,
    controller_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a freeze-only decision that is structurally incapable of authorizing a run."""
    required = {
        "schema",
        "decision_type",
        "decision_id",
        "status",
        "execution_authorized",
        "do_not_execute",
        "approved_by",
        "approved_at_utc",
        "reason",
        "scope_id",
        "mandate_id",
        "campaign_id",
        "frozen_nodeids",
        "source_fingerprint",
        "controller_fingerprint",
        "controller_head",
        "criteria_freeze",
    }
    identity = controller_provenance.get("identity", {})
    reason = decision.get("reason") if isinstance(decision, Mapping) else None
    decision_id = decision.get("decision_id") if isinstance(decision, Mapping) else None
    frozen_nodeids = decision.get("frozen_nodeids") if isinstance(decision, Mapping) else None
    criteria_scope = _hex8sri_criteria_scope_for_nodeids(frozen_nodeids)
    if (
        not isinstance(decision, Mapping)
        or set(decision) != required
        or decision.get("schema") != HEX8SRI_CRITERIA_FREEZE_DECISION_SCHEMA
        or decision.get("decision_type") != "CRITERIA_FREEZE_ONLY"
        or decision.get("status") != "CRITERIA_FROZEN_EXECUTION_NOT_AUTHORIZED"
        or decision.get("execution_authorized") is not False
        or decision.get("do_not_execute") is not True
        or decision.get("approved_by") != "Owner"
        or not isinstance(decision_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", decision_id)
        or not isinstance(reason, str)
        or not 20 <= len(reason.strip()) <= 300
        or "\n" in reason
        or "\r" in reason
        or decision.get("scope_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        or decision.get("mandate_id") != entry.get("development_mandate_id")
        or decision.get("campaign_id") != entry.get("campaign_id")
        or criteria_scope is None
        or decision.get("source_fingerprint") != source_fingerprint
        or decision.get("controller_fingerprint") != _stable_fingerprint(controller_provenance)
        or decision.get("controller_head") != identity.get("head")
        or not _strict_json_equal(
            decision.get("criteria_freeze"),
            _hex8sri_expected_criteria_freeze(
                entry=entry,
                source_fingerprint=source_fingerprint,
                controller_provenance=controller_provenance,
                frozen_nodeids=frozen_nodeids,
            ),
        )
    ):
        raise PolicyError("HEX8-SRI criteria-freeze decision is incomplete, stale or inconsistent")
    _validate_owner_decision_time(decision, execution=False)
    return dict(decision)


def _read_hex8sri_owner_decision_record(
    store: Path,
    record_ref: Any,
    *,
    expected_decision_type: str,
) -> tuple[dict[str, Any], Path, str]:
    if not isinstance(record_ref, Mapping) or set(record_ref) != {"decision_id", "path", "sha256"}:
        raise PolicyError("HEX8-SRI Owner decision record reference has an invalid shape")
    decision_root = (store / "authorizations" / HEX8SRI_CONVERGENCE24_WORKTREE_ID / "owner-decisions").resolve()
    try:
        decision_path = Path(str(record_ref["path"])).resolve(strict=True)
    except OSError as exc:
        raise PolicyError(f"HEX8-SRI Owner decision record is missing: {exc}") from exc
    decision_sha256 = record_ref.get("sha256")
    if (
        not _is_within(decision_path, decision_root)
        or not decision_path.is_file()
        or not isinstance(decision_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", decision_sha256)
        or _sha256(decision_path) != decision_sha256
    ):
        raise PolicyError("HEX8-SRI Owner decision record path or SHA-256 is invalid")
    try:
        recorded = _read_strict_json(decision_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyError(f"HEX8-SRI Owner decision record is unreadable: {exc}") from exc
    if (
        not isinstance(recorded, dict)
        or recorded.get("decision_type") != expected_decision_type
        or recorded.get("decision_id") != record_ref.get("decision_id")
    ):
        raise PolicyError("HEX8-SRI Owner decision record has the wrong decision type or identity")
    return recorded, decision_path, decision_sha256


def _validate_hex8sri_execution_approval(
    decision: Any,
    *,
    store: Path,
    entry: Mapping[str, Any],
    target: str,
    source_fingerprint: str,
    controller_provenance: Mapping[str, Any],
    case_manifest_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Require a time-bounded execution approval that references a distinct frozen criteria record."""
    required = {
        "schema",
        "decision_type",
        "decision_id",
        "status",
        "execution_authorized",
        "do_not_execute",
        "approved_by",
        "approved_at_utc",
        "expires_at_utc",
        "reason",
        "scope_id",
        "mandate_id",
        "campaign_id",
        "authorized_nodeids",
        "source_fingerprint",
        "controller_fingerprint",
        "controller_head",
        "criteria_freeze_record",
        "criteria_freeze",
        "case_manifests_by_nodeid",
        "limits_by_nodeid",
    }
    identity = controller_provenance.get("identity", {})
    reason = decision.get("reason") if isinstance(decision, Mapping) else None
    decision_id = decision.get("decision_id") if isinstance(decision, Mapping) else None
    nodeids = decision.get("authorized_nodeids") if isinstance(decision, Mapping) else None
    limits = decision.get("limits_by_nodeid") if isinstance(decision, Mapping) else None
    manifest_bindings = decision.get("case_manifests_by_nodeid") if isinstance(decision, Mapping) else None
    if (
        not isinstance(nodeids, list)
        or not nodeids
        or any(not isinstance(nodeid, str) for nodeid in nodeids)
        or len(nodeids) != len(set(nodeids))
        or not set(nodeids).issubset(set(HEX8SRI_FREEZABLE_NODEIDS))
    ):
        raise PolicyError("HEX8-SRI execution decision must select unique nodeids in a reviewed criteria scope")
    if (
        not isinstance(decision, Mapping)
        or set(decision) != required
        or decision.get("schema") != HEX8SRI_EXECUTION_APPROVAL_SCHEMA
        or decision.get("decision_type") != "EXECUTION_APPROVED"
        or decision.get("status") != "APPROVED"
        or decision.get("execution_authorized") is not True
        or decision.get("do_not_execute") is not False
        or decision.get("approved_by") != "Owner"
        or not isinstance(decision_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", decision_id)
        or not isinstance(reason, str)
        or not 20 <= len(reason.strip()) <= 300
        or "\n" in reason
        or "\r" in reason
        or decision.get("scope_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        or decision.get("mandate_id") != entry.get("development_mandate_id")
        or decision.get("campaign_id") != entry.get("campaign_id")
        or target not in nodeids
        or not set(nodeids).issubset(set(entry.get("allowed_nodeids", ())))
        or decision.get("source_fingerprint") != source_fingerprint
        or decision.get("controller_fingerprint") != _stable_fingerprint(controller_provenance)
        or decision.get("controller_head") != identity.get("head")
        or not isinstance(limits, Mapping)
        or set(limits) != set(nodeids)
        or not isinstance(manifest_bindings, Mapping)
        or set(manifest_bindings) != set(nodeids)
        or not _strict_json_equal(manifest_bindings.get(target), dict(case_manifest_binding))
    ):
        raise PolicyError("HEX8-SRI execution decision does not authorize this exact scope, source, controller or nodeid")
    for nodeid in nodeids:
        if not _strict_json_equal(limits.get(nodeid), _hex8sri_execution_limits(entry, nodeid)):
            raise PolicyError("HEX8-SRI execution decision exceeds or changes a registered case budget")
    expected_registrations = _hex8sri_registration_sha256_by_nodeid(entry, nodeids)
    for nodeid in nodeids:
        binding = manifest_bindings[nodeid]
        case = _hex8sri_convergence24_case(nodeid)
        expected_case_id = f"{case[0]}_nu_{case[1]}_{case[2]}" if case is not None else None
        if (
            not isinstance(binding, Mapping)
            or set(binding) != {"path", "sha256", "registration_sha256", "case_id", "scope_id"}
            or not isinstance(binding.get("path"), str)
            or not binding.get("path")
            or not re.fullmatch(r"[0-9a-f]{64}", str(binding.get("sha256", "")))
            or binding.get("registration_sha256") != expected_registrations[nodeid]
            or binding.get("case_id") != expected_case_id
            or binding.get("scope_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        ):
            raise PolicyError("HEX8-SRI execution decision does not bind every exact registered case manifest")
    freeze_ref = decision.get("criteria_freeze_record")
    freeze_decision, _freeze_path, _freeze_sha256 = _read_hex8sri_owner_decision_record(
        store,
        freeze_ref,
        expected_decision_type="CRITERIA_FREEZE_ONLY",
    )
    validated_freeze = _validate_hex8sri_criteria_freeze_decision(
        freeze_decision,
        entry=entry,
        source_fingerprint=source_fingerprint,
        controller_provenance=controller_provenance,
    )
    if not set(nodeids).issubset(set(validated_freeze["frozen_nodeids"])):
        raise PolicyError("HEX8-SRI execution decision selects a case outside its frozen criteria scope")
    if not _strict_json_equal(decision.get("criteria_freeze"), validated_freeze.get("criteria_freeze")):
        raise PolicyError("HEX8-SRI execution decision does not match its separately frozen criteria record")
    _validate_owner_decision_time(decision, execution=True)
    freeze_time = datetime.fromisoformat(validated_freeze["approved_at_utc"].replace("Z", "+00:00"))
    execution_time = datetime.fromisoformat(decision["approved_at_utc"].replace("Z", "+00:00"))
    if execution_time < freeze_time:
        raise PolicyError("HEX8-SRI execution approval predates its criteria freeze")
    return dict(decision)


def _validate_hex8sri_frozen_case_criteria(
    case_manifest: Mapping[str, Any],
    *,
    decision: Mapping[str, Any],
    target: str,
    case_registration_sha256: str,
) -> dict[str, Any]:
    """Require the exact case's criteria scope and thresholds to be explicitly Owner-frozen."""
    scope = _hex8sri_criteria_scope_for_target(target)
    if scope is None:
        raise PolicyError("HEX8-SRI case is outside the frozen first-six and refined-three criteria scopes")
    revision, scope_nodeids = scope
    proposed = case_manifest.get("proposed_criteria")
    frozen = case_manifest.get("frozen_criteria")
    expected_contract = {
        "schema": HEX8SRI_CRITERIA_CONTRACT_SCHEMA,
        "revision": revision,
        "dispositions": HEX8SRI_CRITERIA_PROPOSAL_DISPOSITIONS,
    }
    criteria_freeze = decision.get("criteria_freeze")
    registration_hashes = (
        criteria_freeze.get("case_manifest_registration_sha256_by_nodeid")
        if isinstance(criteria_freeze, Mapping)
        else None
    )
    if (
        case_manifest.get("criteria_status") != "OWNER_FREEZE_REQUIRED"
        or not _strict_json_equal(case_manifest.get("criteria_contract"), expected_contract)
        or not _strict_json_equal(proposed, HEX8SRI_PROPOSED_CRITERIA)
        or frozen is not None
        or not isinstance(registration_hashes, Mapping)
        or set(registration_hashes) != set(scope_nodeids)
        or registration_hashes.get(target) != case_registration_sha256
        or criteria_freeze.get("schema") != HEX8SRI_CRITERIA_FREEZE_SCHEMA
        or criteria_freeze.get("revision") != revision
        or not _strict_json_equal(criteria_freeze.get("dispositions"), HEX8SRI_CRITERIA_DISPOSITIONS)
        or not _strict_json_equal(criteria_freeze.get("criteria_definitions"), HEX8SRI_CRITERIA_DEFINITIONS)
        or not _strict_json_equal(
            criteria_freeze.get("frozen_case_gate_criteria"), HEX8SRI_FROZEN_CASE_GATE_CRITERIA
        )
        or criteria_freeze.get("frozen_nodeids") != list(scope_nodeids)
    ):
        raise PolicyError(
            "HEX8-SRI Owner decision does not freeze the exact registered criteria scope; "
            "refresh the case identity and preflight after a criteria decision"
        )
    return dict(HEX8SRI_FROZEN_CASE_GATE_CRITERIA)


def _validate_hex8sri_execution_manifest(
    manifest_path: Path,
    *,
    store: Path,
    target: str,
    entry: Mapping[str, Any],
    identity: Mapping[str, Any],
    source_fingerprint: str,
    controller_provenance: Mapping[str, Any],
    case_manifest_binding: Mapping[str, Any],
    case_manifest: Mapping[str, Any],
    preflight_id: str,
    preflight_receipt: tuple[Path, str],
) -> dict[str, Any]:
    """Accept only an exact per-case Owner grant; never mutates policy or attempts."""
    if target not in entry.get("allowed_nodeids", ()):
        raise PolicyError("HEX8-SRI execution nodeid is not registered")
    authorization_root = (store / "authorizations" / HEX8SRI_CONVERGENCE24_WORKTREE_ID).resolve()
    try:
        path = manifest_path.resolve(strict=True)
    except OSError as exc:
        raise PolicyError(f"HEX8-SRI execution manifest is missing: {exc}") from exc
    if path.parent != authorization_root or not path.is_file():
        raise PolicyError(
            "HEX8-SRI execution manifest must be a direct child of the dedicated campaign authorization root"
        )
    try:
        manifest = _read_strict_json(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyError(f"HEX8-SRI execution manifest is unreadable or not strict JSON: {exc}") from exc
    required_fields = {
        "schema",
        "state",
        "execution_authorized",
        "do_not_execute",
        "authorization_id",
        "worktree_id",
        "mandate_id",
        "campaign_id",
        "target",
        "identity",
        "source_fingerprint",
        "controller_provenance",
        "controller_fingerprint",
        "case_manifest",
        "preflight",
        "limits",
        "owner_decision",
        "owner_decision_record",
    }
    if not isinstance(manifest, dict) or set(manifest) != required_fields:
        raise PolicyError("HEX8-SRI execution manifest has an invalid or ambiguous shape")
    authorization_id = manifest.get("authorization_id")
    decision_record_ref = manifest.get("owner_decision_record")
    if not isinstance(decision_record_ref, Mapping) or set(decision_record_ref) != {"path", "sha256"}:
        raise PolicyError("HEX8-SRI Owner decision record reference has an invalid shape")
    decision_root = authorization_root / "owner-decisions"
    try:
        decision_path = Path(str(decision_record_ref["path"])).resolve(strict=True)
    except OSError as exc:
        raise PolicyError(f"HEX8-SRI Owner decision record is missing: {exc}") from exc
    decision_sha256 = decision_record_ref.get("sha256")
    if (
        not _is_within(decision_path, decision_root.resolve())
        or not decision_path.is_file()
        or not isinstance(decision_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", decision_sha256)
        or _sha256(decision_path) != decision_sha256
    ):
        raise PolicyError("HEX8-SRI Owner decision record path or SHA-256 is invalid")
    try:
        recorded_decision = _read_strict_json(decision_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyError(f"HEX8-SRI Owner decision record is unreadable: {exc}") from exc
    if recorded_decision != manifest.get("owner_decision"):
        raise PolicyError("HEX8-SRI Owner decision differs from its separately archived approval record")
    decision = _validate_hex8sri_execution_approval(
        recorded_decision,
        store=store,
        entry=entry,
        target=target,
        source_fingerprint=source_fingerprint,
        controller_provenance=controller_provenance,
        case_manifest_binding=case_manifest_binding,
    )
    frozen_criteria = _validate_hex8sri_frozen_case_criteria(
        case_manifest,
        decision=decision,
        target=target,
        case_registration_sha256=str(case_manifest_binding.get("registration_sha256", "")),
    )
    expected_preflight = {
        "preflight_id": preflight_id,
        "receipt_path": str(preflight_receipt[0]),
        "receipt_sha256": preflight_receipt[1],
    }
    if (
        not isinstance(authorization_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", authorization_id)
        or path.name != f"{authorization_id}.json"
        or manifest.get("schema") != HEX8SRI_EXECUTION_MANIFEST_SCHEMA
        or manifest.get("state") != "OWNER_AUTHORIZED"
        or manifest.get("execution_authorized") is not True
        or manifest.get("do_not_execute") is not False
        or manifest.get("worktree_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        or manifest.get("mandate_id") != entry.get("development_mandate_id")
        or manifest.get("campaign_id") != entry.get("campaign_id")
        or manifest.get("target") != target
        or manifest.get("identity") != dict(identity)
        or manifest.get("source_fingerprint") != source_fingerprint
        or manifest.get("controller_provenance") != dict(controller_provenance)
        or manifest.get("controller_fingerprint") != _stable_fingerprint(controller_provenance)
        or manifest.get("case_manifest") != dict(case_manifest_binding)
        or manifest.get("preflight") != expected_preflight
        or manifest.get("limits") != _hex8sri_execution_limits(entry, target)
    ):
        raise PolicyError(
            "HEX8-SRI Owner manifest does not bind this exact source, controller, case, preflight and budget"
        )
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "authorization_id": authorization_id,
        "decision_id": decision["decision_id"],
        "owner_decision": decision,
        "owner_decision_record": {"path": str(decision_path), "sha256": decision_sha256},
        "criteria_freeze_record": dict(decision["criteria_freeze_record"]),
        "frozen_criteria": frozen_criteria,
        "criteria_dispositions": dict(decision["criteria_freeze"]["dispositions"]),
        "preflight": expected_preflight,
    }


def _hex8sri_current_case_manifest_bindings(
    entry: Mapping[str, Any],
    execution_root: Path,
    controller_provenance: Mapping[str, Any],
    nodeids: Sequence[str],
) -> dict[str, dict[str, str]]:
    if not nodeids or len(nodeids) != len(set(nodeids)) or not set(nodeids).issubset(HEX8SRI_FREEZABLE_NODEIDS):
        raise PolicyError("HEX8-SRI current manifest bindings require exact reviewed nodeids")
    result: dict[str, dict[str, str]] = {}
    for nodeid in nodeids:
        manifest_path, case_manifest, raw_sha256 = _hex8sri_convergence24_manifest(entry, execution_root, nodeid)
        _verify_hex8sri_convergence24_controller_identity(case_manifest, controller_provenance)
        result[nodeid] = {
            "path": str(manifest_path),
            "sha256": raw_sha256,
            "registration_sha256": _hex8sri_manifest_registration_sha256(case_manifest),
            "case_id": str(case_manifest["case_id"]),
            "scope_id": HEX8SRI_CONVERGENCE24_WORKTREE_ID,
        }
    return result


def _hex8sri_selected_current_case_manifest_bindings(
    decision: Mapping[str, Any], current_bindings: Mapping[str, Mapping[str, str]]
) -> dict[str, Mapping[str, str]]:
    """Require a decision to bind exactly the currently registered manifests it selects."""
    nodeids = decision.get("authorized_nodeids")
    if (
        not isinstance(nodeids, list)
        or not nodeids
        or any(not isinstance(nodeid, str) for nodeid in nodeids)
        or len(nodeids) != len(set(nodeids))
        or not set(nodeids).issubset(set(HEX8SRI_FREEZABLE_NODEIDS))
    ):
        raise PolicyError("HEX8-SRI execution decision must select unique nodeids in a reviewed criteria scope")
    selected = {nodeid: current_bindings[nodeid] for nodeid in nodeids}
    if decision.get("case_manifests_by_nodeid") != selected:
        raise PolicyError("HEX8-SRI execution decision does not match every current selected case manifest")
    return selected


def archive_hex8sri_owner_decision(decision_file: Path) -> dict[str, Any]:
    """Validate and immutably archive a freeze-only or execution Owner decision.

    This records the submitted decision and its digest; it does not authenticate
    the Owner cryptographically, create an execution manifest, or reserve an attempt.
    """
    policy = load_policy(POLICY_PATH)
    scope_id = HEX8SRI_CONVERGENCE24_WORKTREE_ID
    target = HEX8SRI_FIRST6_NODEIDS[0]
    resolve_targets("fem_exploratory", target, policy, worktree_id=scope_id)
    entry, execution_root, _source_root, identity, source_fingerprint = _registered_worktree(scope_id, target, policy)
    controller_provenance = _controller_provenance()
    try:
        decision = _read_strict_json(decision_file.resolve(strict=True))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyError(f"HEX8-SRI Owner decision input is missing or invalid: {exc}") from exc
    if not isinstance(decision, Mapping):
        raise PolicyError("HEX8-SRI Owner decision input must be a JSON object")
    decision_type = decision.get("decision_type")
    if decision_type == "CRITERIA_FREEZE_ONLY":
        validated = _validate_hex8sri_criteria_freeze_decision(
            decision,
            entry=entry,
            source_fingerprint=source_fingerprint,
            controller_provenance=controller_provenance,
        )
        # Bind the exact frozen scope, without a preflight or ledger mutation.
        _hex8sri_current_case_manifest_bindings(
            entry, execution_root, controller_provenance, validated["frozen_nodeids"]
        )
        directory = _run_root(policy) / "authorizations" / scope_id / "owner-decisions" / "criteria-freeze"
    elif decision_type == "EXECUTION_APPROVED":
        requested_nodeids = decision.get("authorized_nodeids")
        if not isinstance(requested_nodeids, list):
            raise PolicyError("HEX8-SRI execution decision must list its exact authorized nodeids")
        current_bindings = _hex8sri_current_case_manifest_bindings(
            entry, execution_root, controller_provenance, requested_nodeids
        )
        selected_bindings = _hex8sri_selected_current_case_manifest_bindings(decision, current_bindings)
        authorized_nodeids = decision["authorized_nodeids"]
        validated = _validate_hex8sri_execution_approval(
            decision,
            store=_run_root(policy),
            entry=entry,
            target=authorized_nodeids[0],
            source_fingerprint=source_fingerprint,
            controller_provenance=controller_provenance,
            case_manifest_binding=selected_bindings[authorized_nodeids[0]],
        )
        directory = _run_root(policy) / "authorizations" / scope_id / "owner-decisions" / "execution"
    else:
        raise PolicyError("HEX8-SRI Owner decision_type must be CRITERIA_FREEZE_ONLY or EXECUTION_APPROVED")
    decision_id = str(validated["decision_id"])
    path = directory / f"{decision_id}.json"
    with _exclusive_file_lock(_run_root(policy) / "locks" / "hex8sri-owner-decision-archive.lock"):
        _atomic_json_new(path, validated)
    return {
        "state": validated["status"],
        "decision_type": decision_type,
        "decision_id": decision_id,
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "execution_manifest_created": False,
        "attempt_reserved": False,
    }


def _validate_hex8sri_execution_test_contract(execution_root: Path, target: str) -> None:
    """Refuse before ledger reservation until the science test consumes the dedicated identity."""
    module_path = target.split("::", maxsplit=1)[0]
    test_path = (execution_root / module_path).resolve()
    if not _is_within(test_path, execution_root.resolve()) or not test_path.is_file():
        raise PolicyError("HEX8-SRI execution test module is missing or outside its registered science worktree")
    try:
        source = test_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyError(f"HEX8-SRI execution test module is unreadable: {exc}") from exc
    try:
        syntax_tree = ast.parse(source, filename=str(test_path))
    except SyntaxError as exc:
        raise PolicyError("HEX8-SRI execution test contract cannot be parsed") from exc
    authorization_function = next(
        (
            node
            for node in ast.walk(syntax_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_authorized_case"
        ),
        None,
    )
    if authorization_function is None:
        raise PolicyError("HEX8-SRI execution test has no exact pre-assembly authorization function")
    module_strings = {
        node.value for node in ast.walk(syntax_tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    function_strings = {
        node.value
        for node in ast.walk(authorization_function)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    required_environment_contract = {
        "QF_DEV_EXECUTION_MANIFEST_PATH",
        "QF_DEV_EXECUTION_MANIFEST_SHA256",
        "QF_DEV_OWNER_DECISION_ID",
        "QF_DEV_CASE_MANIFEST_PATH",
        "QF_DEV_PREFLIGHT_ID",
        "QF_DEV_PREFLIGHT_SHA256",
        "QF_DEV_TARGET_NODEID",
        "QF_DEV_CONTROLLER_ROOT",
        "QF_DEV_CONTROLLER_BRANCH",
        "QF_DEV_CONTROLLER_HEAD",
        "QF_DEV_CONTROLLER_RUNNER_SHA256",
        "QF_DEV_CONTROLLER_POLICY_SHA256",
        "QF_DEV_CONTROLLER_PLUGIN_SHA256",
        "hex8sri-convergence24",
        "OWNER_AUTHORIZED",
    }
    required_criteria_contract = {
        "criteria_contract",
        "criteria_freeze",
        "CASE_GATE",
        "CASE_DIAGNOSTIC",
        "CAMPAIGN_GATE_DEFERRED",
        "NOT_ASSESSED",
        "negative_mean_loaded_face_uz",
    }
    if (
        HEX8SRI_EXECUTION_TEST_CONTRACT_MARKER not in function_strings
        or not required_environment_contract.issubset(module_strings)
        or not required_criteria_contract.issubset(module_strings)
        or "codex/hex8sri-controller-registration" in module_strings
        or "hex8sri" in module_strings
    ):
        raise PolicyError(
            "HEX8-SRI source test does not implement the dedicated Owner-manifest/preflight contract; "
            "update and re-fingerprint the science test before execution"
        )


def _validate_hex8sri_execution_ledger(ledger_path: Path, *, entry: Mapping[str, Any], target: str) -> None:
    """Fail closed on a malformed, cross-mandate, or over-consumed campaign ledger."""
    if not ledger_path.exists():
        return
    try:
        ledger = _read_strict_json(ledger_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyError(f"HEX8-SRI attempt ledger is unreadable: {exc}") from exc
    mandate_id = str(entry["development_mandate_id"])
    prefix = f"{mandate_id}:{HEX8SRI_CONVERGENCE24_WORKTREE_ID}:"
    allowed = set(entry["allowed_nodeids"])
    if (
        not isinstance(ledger, dict)
        or ledger.get("schema") != "qfsolver-development-node-ledger-v1"
        or ledger.get("mandate_id") != mandate_id
        or not isinstance(ledger.get("entries"), dict)
    ):
        raise PolicyError("HEX8-SRI execution ledger identity/schema mismatch")
    for key, attempts in ledger["entries"].items():
        if not isinstance(key, str) or not key.startswith(prefix):
            raise PolicyError("HEX8-SRI ledger contains an entry from another scope or mandate")
        registered_target = key[len(prefix) :]
        if registered_target not in allowed or not isinstance(attempts, list) or len(attempts) > 1:
            raise PolicyError("HEX8-SRI ledger contains an unregistered node or exceeds its one-attempt limit")
        for index, attempt in enumerate(attempts, start=1):
            if (
                not isinstance(attempt, Mapping)
                or attempt.get("attempt") != index
                or not isinstance(attempt.get("authorization_id"), str)
                or not isinstance(attempt.get("owner_decision_id"), str)
                or not isinstance(attempt.get("state"), str)
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", attempt["state"])
            ):
                raise PolicyError("HEX8-SRI ledger attempt lacks coherent Owner authorization provenance")


def prepare_wp12_execution_manifest(
    worktree_id: str, target: str, authorization_id: str, preflight_id: str | None = None
) -> dict[str, Any]:
    """Write an exact WP12 execution-manifest template that remains unapproved."""
    if worktree_id not in WP12_OWNER_ENVELOPES:
        raise PolicyError("WP12 execution manifests are available only for registered WP12 scopes")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", authorization_id):
        raise PolicyError("authorization ID must be 8 to 64 safe alphanumeric, dot, underscore or hyphen characters")
    policy = load_policy(POLICY_PATH)
    resolve_targets("fem_exploratory", target, policy, worktree_id=worktree_id)
    entry, _root, _source_root, identity, source_fingerprint = _registered_worktree(worktree_id, target, policy)
    selection = _wp12_active_registration(worktree_id, target, entry, source_fingerprint)
    controller_provenance = _controller_provenance()
    controller_fingerprint = _stable_fingerprint(controller_provenance)
    evidence_root = _run_root(policy, worktree_id)
    preflight_receipt: tuple[Path, str] | None = None
    if worktree_id == "wp12_dynamics":
        if preflight_id is None:
            raise PolicyError("WP12-A dynamics manifests require a successful exact-node collect-only preflight")
        preflight_receipt = _validate_wp12_dynamics_preflight_receipt(
            evidence_root,
            preflight_id,
            target=target,
            identity=identity,
            source_fingerprint=source_fingerprint,
            controller_provenance=controller_provenance,
            policy=policy,
        )
    elif worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
        if preflight_id is None:
            raise PolicyError("WP12-B R2 manifests require a successful exact-node preflight")
        preflight_receipt = _validate_wp12b_hex20_r2_preflight_receipt(
            evidence_root, preflight_id, target=target, identity=identity,
            source_fingerprint=source_fingerprint, controller_provenance=controller_provenance, policy=policy,
        )
    elif preflight_id is not None:
        raise PolicyError("prepare-manifest accepts preflight receipt IDs only for WP12-A dynamics")
    manifest_dir = evidence_root / "authorizations" / worktree_id
    path = manifest_dir / f"{authorization_id}.json"
    with _exclusive_file_lock(evidence_root / "locks" / "manifest-template.lock"):
        if path.exists():
            raise PolicyError("refusing to overwrite an existing WP12 execution manifest")
        payload = {
            "schema": "qfsolver-wp12-development-execution-v1",
            "state": "PREPARED_NOT_AUTHORIZED",
            **({"execution_authorized": False, "do_not_execute": True}
               if worktree_id in {"wp12_dynamics", WP12B_HEX20_R2_WORKTREE_ID} else {}),
            "authorization_id": authorization_id,
            "worktree_id": worktree_id,
            "mandate_id": entry["development_mandate_id"],
            **({"campaign_id": entry["campaign_id"]} if "campaign_id" in entry else {}),
            "target": target,
            "identity": identity,
            "source_fingerprint": source_fingerprint,
            "controller_fingerprint": controller_fingerprint,
            "limits": _wp12_manifest_limits(entry, selection),
            **({"scientific_criteria": WP12B_HEX20_R2_CRITERIA}
               if worktree_id == WP12B_HEX20_R2_WORKTREE_ID else {}),
            "owner_decision": {
                "status": "NOT_AUTHORIZED",
                "approved_by": None,
                "approved_at_utc": None,
                "reason": None,
            },
            **(
                {
                    "preflight": {
                        "preflight_id": preflight_id,
                        "receipt_path": str(preflight_receipt[0]),
                        "receipt_sha256": preflight_receipt[1],
                    }
                }
                if preflight_id is not None and preflight_receipt is not None
                else {}
            ),
            "preparation_note": "Template only. A distinct Owner execution decision is required before setting OWNER_AUTHORIZED.",
        }
        _atomic_json(path, payload)
    return {"state": payload["state"], "path": str(path.resolve()), "target": target}


def prepare_hex8sri_execution_manifest(target: str, preflight_id: str, authorization_id: str) -> dict[str, Any]:
    """Write a non-authorized, exact-case HEX8-SRI execution template; never reserves an attempt."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", authorization_id):
        raise PolicyError("draft ID must be 8 to 64 safe alphanumeric, dot, underscore or hyphen characters")
    policy = load_policy(POLICY_PATH)
    worktree_id = HEX8SRI_CONVERGENCE24_WORKTREE_ID
    resolve_targets("fem_exploratory", target, policy, worktree_id=worktree_id)
    entry, execution_root, _source_root, identity, source_fingerprint = _registered_worktree(
        worktree_id, target, policy
    )
    store = _run_root(policy)
    ledger_path, _ledger_lock, mandate_id, predecessor = _node_ledger_context(policy, store, worktree_id)
    if predecessor is not None or mandate_id != entry["development_mandate_id"]:
        raise PolicyError("HEX8-SRI authorization template is not bound to the isolated campaign mandate")
    manifest_path, case_manifest, manifest_sha256 = _hex8sri_convergence24_manifest(entry, execution_root, target)
    controller_provenance = _controller_provenance()
    _verify_hex8sri_convergence24_controller_identity(case_manifest, controller_provenance)
    case_contract = _hex8sri_convergence24_case_contract(case_manifest)
    case_binding = {
        "path": str(manifest_path),
        "sha256": manifest_sha256,
        "registration_sha256": _hex8sri_manifest_registration_sha256(case_manifest),
        "case_id": case_manifest["case_id"],
        "scope_id": worktree_id,
    }
    preflight_receipt = _validate_hex8sri_convergence24_preflight_receipt(
        store,
        preflight_id,
        target=target,
        identity=identity,
        source_fingerprint=source_fingerprint,
        controller_provenance=controller_provenance,
        manifest_binding=case_binding,
        attempt_ledger={
            "path": str(ledger_path),
            "mandate_id": mandate_id,
            "attempts_reserved": False,
        },
    )
    authorization_root = store / "authorizations" / worktree_id / "prepared"
    path = authorization_root / f"{authorization_id}.json"
    payload = {
        "schema": HEX8SRI_EXECUTION_MANIFEST_SCHEMA,
        "state": "PREPARED_NOT_AUTHORIZED",
        "execution_authorized": False,
        "do_not_execute": True,
        "authorization_id": authorization_id,
        "worktree_id": worktree_id,
        "mandate_id": mandate_id,
        "campaign_id": entry["campaign_id"],
        "target": target,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "controller_provenance": controller_provenance,
        "controller_fingerprint": _stable_fingerprint(controller_provenance),
        "case_manifest": case_binding,
        "preflight": {
            "preflight_id": preflight_id,
            "receipt_path": str(preflight_receipt[0]),
            "receipt_sha256": preflight_receipt[1],
        },
        "limits": _hex8sri_execution_limits(entry, target),
        "owner_decision": None,
        "owner_decision_record": None,
    }
    with _exclusive_file_lock(store / "locks" / "hex8sri-execution-manifest.lock"):
        _atomic_json_new(path, payload)
    return {
        "state": payload["state"],
        "path": str(path.resolve()),
        "target": target,
        "preflight_id": preflight_id,
        "case_contract": case_contract,
        "sha256": _sha256(path),
    }


def _preflight_directory(store: Path, worktree_id: str, preflight_id: str) -> Path:
    if not PREFLIGHT_RE.fullmatch(preflight_id):
        raise PolicyError("preflight ID must use the generated pf-<12 lowercase hex> format")
    directory = (store / "worktrees" / worktree_id / "preflight" / preflight_id).resolve()
    if not _is_within(directory, store.resolve()):
        raise PolicyError("preflight evidence path escapes the development run store")
    return directory


ROTOR_PREFLIGHT_ATTESTATION_PREFIX = "QF_DEV_ROTOR_PREFLIGHT="
WP12_DYNAMICS_PREFLIGHT_ATTESTATION_PREFIX = "QF_DEV_WP12_DYNAMICS_PREFLIGHT="


def _validate_rotor_collect_attestation(
    stdout: str,
    *,
    target: str,
    solver_origin: str,
    selected_dofs: int,
    max_dofs: int,
) -> tuple[str, dict[str, Any] | None]:
    lines = [
        line[len(ROTOR_PREFLIGHT_ATTESTATION_PREFIX) :]
        for line in stdout.splitlines()
        if line.startswith(ROTOR_PREFLIGHT_ATTESTATION_PREFIX)
    ]
    if len(lines) != 1:
        return "PREFLIGHT_ATTESTATION_INVALID", None
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError:
        return "PREFLIGHT_ATTESTATION_INVALID", None
    if not isinstance(payload, dict) or payload.get("schema") != "qfsolver-rotor-collect-only-v1":
        return "PREFLIGHT_ATTESTATION_INVALID", None
    if payload.get("worktree_id") != "rotor":
        return "PREFLIGHT_SCOPE_MISMATCH", payload
    if payload.get("expected_nodeid") != target:
        return "PREFLIGHT_NODEID_NOT_CONFIRMED", payload
    if payload.get("solver_origin") != solver_origin:
        return "PREFLIGHT_WRONG_SOLVER_ORIGIN", payload
    if payload.get("collected_nodeids") != [target]:
        return "PREFLIGHT_NODEID_NOT_CONFIRMED", payload
    if payload.get("skip_markers") != []:
        return "PREFLIGHT_SKIPPED", payload
    if payload.get("bodies_executed") is not False:
        return "PREFLIGHT_BODY_EXECUTION_DETECTED", payload
    if (
        payload.get("selected_dofs_expected") != selected_dofs
        or payload.get("selected_dofs") != str(selected_dofs)
        or payload.get("max_dofs_expected") != max_dofs
        or payload.get("max_dofs") != str(max_dofs)
    ):
        return "PREFLIGHT_SCOPE_MISMATCH", payload
    if payload.get("exitstatus") != 0:
        return "PREFLIGHT_FAILED", payload
    return "PREFLIGHT_PASS", payload


def _validate_wp12_collect_attestation(
    stdout: str,
    *,
    target: str,
    solver_origin: str,
    selected_dofs: int,
    max_dofs: int | None,
    worktree_id: str,
    schema: str,
    marker: str,
) -> tuple[str, dict[str, Any] | None]:
    lines = [line[len(marker) :] for line in stdout.splitlines() if line.startswith(marker)]
    if len(lines) != 1:
        return "PREFLIGHT_ATTESTATION_INVALID", None
    try:
        payload = json.loads(lines[0])
    except json.JSONDecodeError:
        return "PREFLIGHT_ATTESTATION_INVALID", None
    if not isinstance(payload, dict) or payload.get("schema") != schema:
        return "PREFLIGHT_ATTESTATION_INVALID", None
    if payload.get("worktree_id") != worktree_id:
        return "PREFLIGHT_SCOPE_MISMATCH", payload
    if payload.get("expected_nodeid") != target or payload.get("collected_nodeids") != [target]:
        return "PREFLIGHT_NODEID_NOT_CONFIRMED", payload
    if payload.get("solver_origin") != solver_origin:
        return "PREFLIGHT_WRONG_SOLVER_ORIGIN", payload
    if payload.get("skip_markers") != []:
        return "PREFLIGHT_SKIPPED", payload
    if payload.get("bodies_executed") is not False:
        return "PREFLIGHT_BODY_EXECUTION_DETECTED", payload
    if payload.get("selected_dofs_expected") != selected_dofs or payload.get("selected_dofs") != str(selected_dofs):
        return "PREFLIGHT_SCOPE_MISMATCH", payload
    expected_max_dofs = str(max_dofs) if max_dofs is not None else None
    if payload.get("max_dofs_expected") != max_dofs or payload.get("max_dofs") != expected_max_dofs:
        return "PREFLIGHT_SCOPE_MISMATCH", payload
    if payload.get("exitstatus") != 0:
        return "PREFLIGHT_FAILED", payload
    return "PREFLIGHT_PASS", payload


def _validate_wp12_dynamics_collect_attestation(
    stdout: str,
    *,
    target: str,
    solver_origin: str,
    selected_dofs: int,
) -> tuple[str, dict[str, Any] | None]:
    return _validate_wp12_collect_attestation(
        stdout,
        target=target,
        solver_origin=solver_origin,
        selected_dofs=selected_dofs,
        max_dofs=None,
        worktree_id="wp12_dynamics",
        schema="qfsolver-wp12-dynamics-collect-only-v1",
        marker=WP12_DYNAMICS_PREFLIGHT_ATTESTATION_PREFIX,
    )


def _validate_wp12b_hex20_diagnostic_collect_attestation(
    stdout: str,
    *,
    target: str,
    solver_origin: str,
    selected_dofs: int,
) -> tuple[str, dict[str, Any] | None]:
    return _validate_wp12_collect_attestation(
        stdout,
        target=target,
        solver_origin=solver_origin,
        selected_dofs=selected_dofs,
        max_dofs=60,
        worktree_id=WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID,
        schema=WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_SCHEMA,
        marker=WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_MARKER,
    )


def preflight_wp12_dynamics_pytest(
    target: str, preflight_id: str | None = None, *, policy: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Collect one WP12-A dynamics node without reserving an attempt."""
    if target not in WP12_DYNAMICS_PREFLIGHT_NODEIDS:
        raise PolicyError("WP12-A dynamics preflight is limited to its reviewed exact registered nodeids")
    return _preflight_wp12_attested_pytest(
        target,
        preflight_id,
        policy=policy,
        worktree_id="wp12_dynamics",
        schema="qfsolver-wp12-dynamics-collect-only-v1",
        marker=WP12_DYNAMICS_PREFLIGHT_ATTESTATION_PREFIX,
        preflight_schema="qfsolver-development-wp12-dynamics-preflight-v2",
        attestation_mode="wp12_dynamics_collect_only_attestation",
        label="WP12 dynamics",
    )


def preflight_wp12b_hex20_diagnostic_pytest(
    target: str, preflight_id: str | None = None, *, policy: Mapping[str, Any] | None = None,
    worktree_id: str = WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID,
) -> dict[str, Any]:
    """Collect the one exact HEX20 diagnostic node without reserving an attempt."""
    if target != WP12B_HEX20_DIAGNOSTIC_NODEID:
        raise PolicyError("HEX20 diagnostic preflight is limited to its exact registered nodeid")
    return _preflight_wp12_attested_pytest(
        target,
        preflight_id,
        policy=policy,
        worktree_id=worktree_id,
        schema=WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_SCHEMA,
        marker=WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_MARKER,
        preflight_schema=("qfsolver-development-wp12b-hex20-r2-preflight-v1"
                          if worktree_id == WP12B_HEX20_R2_WORKTREE_ID
                          else "qfsolver-development-wp12b-hex20-diagnostic-preflight-v1"),
        attestation_mode="wp12b_hex20_diagnostic_collect_only_attestation",
        label="WP12-B HEX20 diagnostic",
    )


def _preflight_wp12_attested_pytest(
    target: str,
    preflight_id: str | None,
    *,
    policy: Mapping[str, Any] | None,
    worktree_id: str,
    schema: str,
    marker: str,
    preflight_schema: str,
    attestation_mode: str,
    label: str,
) -> dict[str, Any]:
    """Collect one registered WP12 node and prove provenance without ledger reservation."""
    current_policy = load_policy() if policy is None else dict(policy)
    targets = resolve_targets("fem_exploratory", target, current_policy, worktree_id=worktree_id)
    if targets != [target]:
        raise PolicyError(f"{label} preflight requires exactly one registered nodeid")
    entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
        worktree_id, target, current_policy
    )
    selection = _wp12_active_registration(worktree_id, target, entry, source_fingerprint)
    if entry.get("development_mandate_id") != WP12_OWNER_ENVELOPES[worktree_id]["development_mandate_id"]:
        raise PolicyError(f"{label} preflight is not bound to its registered mandate")
    store = _run_root(current_policy, worktree_id)
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free)
    minimum_free = int(current_policy["minimum_free_disk_mib"] * 1024 * 1024)
    if free_bytes < minimum_free:
        raise PolicyError(f"insufficient free disk for {label} preflight: {free_bytes} bytes; requires {minimum_free}")

    preflight_id = preflight_id or f"pf-{uuid.uuid4().hex[:12]}"
    receipt_dir = _preflight_directory(store, worktree_id, preflight_id)
    try:
        receipt_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise PolicyError("preflight ID already exists; refusing to overwrite a prior receipt") from exc
    temporary_dir = receipt_dir / "tmp"
    output_dir = receipt_dir / "output"
    temporary_dir.mkdir()
    output_dir.mkdir()
    attestation_flags = {attestation_mode: True}
    command = build_pytest_command(
        "fem_exploratory",
        targets,
        temporary_dir,
        repository_root=execution_root,
        source_root=source_root,
        controller_root=ROOT,
        allow_native_skip_override=False,
        collect_only=True,
        **attestation_flags,
    )
    if "--collect-only" not in command or command[-1] != target:
        raise PolicyError(f"{label} preflight command must collect only its one exact registered nodeid")
    environment = build_child_environment(
        temporary_dir,
        source_root=source_root,
        wp12_entry={**entry, "worktree_id": worktree_id},
        wp12_selection=selection,
    )
    environment.update({"QF_DEV_PREFLIGHT_SCOPE_ID": worktree_id, "QF_DEV_PREFLIGHT_TARGET": target})
    budgets = dict(entry["budgets"])
    budgets["timeout_seconds"] = selection["timeout_seconds"]
    ledger_predecessor: dict[str, str] | None = None
    predecessor_path: Path | None = None
    predecessor_sha256_before: str | None = None
    if worktree_id in {"wp12_dynamics", WP12B_HEX20_R2_WORKTREE_ID}:
        ledger_path, _ledger_lock, ledger_mandate_id, ledger_predecessor = _node_ledger_context(
            current_policy, store, worktree_id
        )
        if ledger_mandate_id != entry["development_mandate_id"] or ledger_predecessor is None:
            raise PolicyError("WP12-A collect-only preflight is not bound to its mandate-specific ledger")
        predecessor_path = (store / ledger_predecessor["path"]).resolve()
        predecessor_sha256_before = _sha256(predecessor_path)
    else:
        ledger_path = store / "node-attempt-ledger.json"
    ledger_sha256_before = _sha256(ledger_path) if ledger_path.is_file() else None
    attempt_ledger_initial: dict[str, Any] = {
        "path": str(ledger_path),
        "sha256_before": ledger_sha256_before,
        "touched": False,
    }
    if worktree_id in {"wp12_dynamics", WP12B_HEX20_R2_WORKTREE_ID}:
        attempt_ledger_initial.update(
            {
                "predecessor": ledger_predecessor,
                "predecessor_sha256_before": predecessor_sha256_before,
            }
        )
    controller_provenance = _controller_provenance()
    expected_origin = str((source_root / "solveur" / "__init__.py").resolve())
    started = datetime.now(timezone.utc).isoformat()
    record_path = receipt_dir / "preflight.json"
    initial = {
        "schema": preflight_schema,
        "mode": "DEVELOPMENT_AUTONOMOUS",
        "mandate_id": entry["development_mandate_id"],
        "worktree_id": worktree_id,
        "target": target,
        "preflight_id": preflight_id,
        "phase": "PYTEST_COLLECT_ONLY",
        "bodies_executed": False,
        "attempt_reserved": False,
        "ledger_touched": False,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "registration": selection,
        "attempt_ledger": attempt_ledger_initial,
        "solver_origin_expected": expected_origin,
        "controller_provenance": controller_provenance,
        "command": command,
        "budgets": budgets,
        "free_disk_before_bytes": free_bytes,
    }
    try:
        result = run_supervised_command(
            command,
            cwd=execution_root,
            environment=environment,
            output_dir=output_dir,
            temporary_dir=temporary_dir,
            limits=budgets,
            poll_interval=float(current_policy["poll_interval_seconds"]),
        )
    except OSError as exc:
        ledger_sha256_after = _sha256(ledger_path) if ledger_path.is_file() else None
        predecessor_sha256_after = _sha256(predecessor_path) if predecessor_path is not None else None
        predecessor_touched = predecessor_sha256_before != predecessor_sha256_after
        ledger_touched = ledger_sha256_before != ledger_sha256_after or predecessor_touched
        _atomic_json_new(
            record_path,
            {
                **initial,
                "state": "PREFLIGHT_LAUNCH_FAILED",
                "ledger_touched": ledger_touched,
                "attempt_ledger": {
                    **attempt_ledger_initial,
                    "sha256_after": ledger_sha256_after,
                    **(
                        {"predecessor_sha256_after": predecessor_sha256_after}
                        if worktree_id in {"wp12_dynamics", WP12B_HEX20_R2_WORKTREE_ID}
                        else {}
                    ),
                    "touched": ledger_touched,
                },
                "started_at_utc": started,
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "launch_error": f"{type(exc).__name__}: {exc}",
            },
        )
        _atomic_json_new(receipt_dir / "preflight.sha256.json", {"sha256": _sha256(record_path)})
        raise PolicyError(f"{label} collect-only preflight could not launch: {exc}") from exc

    stdout_path, stderr_path = output_dir / "stdout.log", output_dir / "stderr.log"
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
    combined = stdout + "\n" + stderr
    attestation_status, attestation = _validate_wp12_collect_attestation(
        stdout,
        target=target,
        solver_origin=expected_origin,
        selected_dofs=selection["selected_dofs"],
        max_dofs=entry["target_max_dofs"],
        worktree_id=worktree_id,
        schema=schema,
        marker=marker,
    )
    after_policy = load_policy()
    after_entry, _after_root, _after_source, after_identity, after_fingerprint = _registered_worktree(
        worktree_id, target, after_policy
    )
    ledger_sha256_after = _sha256(ledger_path) if ledger_path.is_file() else None
    predecessor_sha256_after = _sha256(predecessor_path) if predecessor_path is not None else None
    predecessor_touched = predecessor_sha256_before != predecessor_sha256_after
    ledger_touched = ledger_sha256_before != ledger_sha256_after or predecessor_touched
    controller_provenance_after = _controller_provenance()
    observed_origin = _observed_solver_origin(combined)
    if after_identity != identity or after_fingerprint != source_fingerprint or after_entry != entry:
        state = "PREFLIGHT_SOURCE_CHANGED"
    elif controller_provenance_after != controller_provenance:
        state = "PREFLIGHT_CONTROLLER_CHANGED"
    elif ledger_touched:
        state = "PREFLIGHT_LEDGER_CHANGED"
    elif result.status != "PASS":
        state = "PREFLIGHT_FAILED"
    elif observed_origin != expected_origin:
        state = "PREFLIGHT_WRONG_SOLVER_ORIGIN"
    else:
        state = attestation_status
    final = {
        **initial,
        "state": state,
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "collected_nodeids": (attestation or {}).get("collected_nodeids", []),
        "skip_markers": (attestation or {}).get("skip_markers"),
        "bodies_executed": (attestation or {}).get("bodies_executed"),
        "attempt_reserved": False,
        "ledger_touched": ledger_touched,
        "attempt_ledger": {
            **attempt_ledger_initial,
            "sha256_after": ledger_sha256_after,
            **(
                {"predecessor_sha256_after": predecessor_sha256_after}
                if worktree_id in {"wp12_dynamics", WP12B_HEX20_R2_WORKTREE_ID}
                else {}
            ),
            "touched": ledger_touched,
        },
        "solver_origin_observed": observed_origin,
        "attestation_error": None if attestation is not None else attestation_status,
        "return_code": result.return_code,
        "elapsed_seconds": result.elapsed_seconds,
        "peak_rss_bytes": result.peak_rss_bytes,
        "peak_process_count": result.peak_process_count,
        "stdout_bytes": result.stdout_bytes,
        "stderr_bytes": result.stderr_bytes,
        "stdout_sha256": _sha256(stdout_path) if stdout_path.is_file() else None,
        "stderr_sha256": _sha256(stderr_path) if stderr_path.is_file() else None,
        "identity_after": after_identity,
        "source_fingerprint_after": after_fingerprint,
        "controller_provenance_after": controller_provenance_after,
        "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
    }
    _atomic_json_new(record_path, final)
    receipt_sha256 = _sha256(record_path)
    _atomic_json_new(receipt_dir / "preflight.sha256.json", {"sha256": receipt_sha256})
    return {
        "preflight_id": preflight_id,
        "state": state,
        "bodies_executed": final["bodies_executed"],
        "attempt_reserved": False,
        "ledger_touched": ledger_touched,
        "nodeid": target if final["collected_nodeids"] == [target] else None,
        "receipt": str(record_path),
        "receipt_sha256": receipt_sha256,
    }


def preflight_rotor_pytest(
    target: str, preflight_id: str | None = None, *, policy: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Collect one registered rotor node with exact-node, origin, skip and body attestations."""
    current_policy = load_policy() if policy is None else policy
    targets = resolve_targets("fem_exploratory", target, current_policy, worktree_id="rotor")
    entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
        "rotor", target, current_policy
    )
    selection = _wp12_active_registration("rotor", target, entry, source_fingerprint)
    store = _run_root(current_policy, "rotor")
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free)
    minimum_free = int(current_policy["minimum_free_disk_mib"] * 1024 * 1024)
    if free_bytes < minimum_free:
        raise PolicyError(f"insufficient free disk for rotor preflight: {free_bytes} bytes; requires {minimum_free}")

    preflight_id = preflight_id or f"pf-{uuid.uuid4().hex[:12]}"
    receipt_dir = _preflight_directory(store, "rotor", preflight_id)
    if receipt_dir.exists():
        raise PolicyError("preflight ID already exists; refusing to overwrite a prior receipt")
    temporary_dir = receipt_dir / "tmp"
    output_dir = receipt_dir / "output"
    temporary_dir.mkdir(parents=True)
    output_dir.mkdir()
    controller_provenance = _controller_provenance()
    expected_origin = str((source_root / "solveur" / "__init__.py").resolve())
    command = build_pytest_command(
        "fem_exploratory",
        targets,
        temporary_dir,
        repository_root=execution_root,
        source_root=source_root,
        controller_root=ROOT,
        collect_only=True,
        rotor_collect_only_attestation=True,
    )
    if "--collect-only" not in command or command[-1] != target:
        raise PolicyError("rotor preflight command must collect only its exact registered nodeid")
    environment = build_child_environment(
        temporary_dir,
        source_root=source_root,
        wp12_entry={**entry, "worktree_id": "rotor"},
        wp12_selection=selection,
    )
    budgets = dict(entry["budgets"])
    budgets["minimum_free_disk_mib"] = current_policy["minimum_free_disk_mib"]
    started = datetime.now(timezone.utc).isoformat()
    record_path = receipt_dir / "preflight.json"
    initial = {
        "schema": "qfsolver-development-wp12-rotor-preflight-v1",
        "mode": "DEVELOPMENT_AUTONOMOUS",
        "mandate_id": entry["development_mandate_id"],
        "worktree_id": "rotor",
        "target": target,
        "preflight_id": preflight_id,
        "phase": "PYTEST_COLLECT_ONLY",
        "attempt_reserved": False,
        "execution_manifest_required_for_test_execution": True,
        "execution_authorization_evaluated": False,
        "bodies_executed": None,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "solver_origin_expected": expected_origin,
        "controller_provenance": controller_provenance,
        "command": command,
        "budgets": budgets,
        "free_disk_before_bytes": free_bytes,
    }
    try:
        with _wp12_resource_lock(WP12_COORDINATION_ROOT, entry["concurrency_class"]):
            result = run_supervised_command(
                command,
                cwd=execution_root,
                environment=environment,
                output_dir=output_dir,
                temporary_dir=temporary_dir,
                limits=budgets,
                poll_interval=float(current_policy["poll_interval_seconds"]),
            )
    except OSError as exc:
        _atomic_json(
            record_path,
            {
                **initial,
                "state": "PREFLIGHT_LAUNCH_FAILED",
                "started_at_utc": started,
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "launch_error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise PolicyError(f"rotor collect-only preflight could not launch: {exc}") from exc

    stdout_path, stderr_path = output_dir / "stdout.log", output_dir / "stderr.log"
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    origin_prefix = "QF_DEV_SOLVER_ORIGIN="
    origin_lines = [line[len(origin_prefix) :] for line in stdout.splitlines() if line.startswith(origin_prefix)]
    origin_status = (
        "PREFLIGHT_WRONG_SOLVER_ORIGIN"
        if len(origin_lines) == 1 and origin_lines[0] != expected_origin
        else "PREFLIGHT_IMPORT_FAILED"
        if len(origin_lines) != 1
        else None
    )
    attestation_status, attestation = _validate_rotor_collect_attestation(
        stdout,
        target=target,
        solver_origin=expected_origin,
        selected_dofs=selection["selected_dofs"],
        max_dofs=entry["target_max_dofs"],
    )
    after_policy = load_policy()
    after_entry, _after_root, _after_source, after_identity, after_fingerprint = _registered_worktree(
        "rotor", target, after_policy
    )
    if after_identity != identity or after_fingerprint != source_fingerprint or after_entry != entry:
        state = "PREFLIGHT_SOURCE_CHANGED"
    elif origin_status is not None:
        state = origin_status
    elif result.status != "PASS":
        state = "PREFLIGHT_FAILED"
    else:
        state = attestation_status
    final = {
        **initial,
        "state": state,
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "collected_nodeids": (attestation or {}).get("collected_nodeids", []),
        "skip_markers": (attestation or {}).get("skip_markers"),
        "bodies_executed": (attestation or {}).get("bodies_executed"),
        "worktree_id_observed": (attestation or {}).get("worktree_id"),
        "selected_dofs_observed": (attestation or {}).get("selected_dofs"),
        "max_dofs_observed": (attestation or {}).get("max_dofs"),
        "solver_origin_observed": origin_lines[0] if len(origin_lines) == 1 else None,
        "attestation_error": None if attestation is not None else attestation_status,
        "return_code": result.return_code,
        "elapsed_seconds": result.elapsed_seconds,
        "peak_rss_bytes": result.peak_rss_bytes,
        "peak_process_count": result.peak_process_count,
        "stdout_bytes": result.stdout_bytes,
        "stderr_bytes": result.stderr_bytes,
        "stdout_sha256": _sha256(stdout_path) if stdout_path.is_file() else None,
        "stderr_sha256": _sha256(stderr_path) if stderr_path.is_file() else None,
        "identity_after": after_identity,
        "source_fingerprint_after": after_fingerprint,
        "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
    }
    _atomic_json(record_path, final)
    receipt_sha256 = _sha256(record_path)
    _atomic_json(receipt_dir / "preflight.sha256.json", {"sha256": receipt_sha256})
    return {
        "preflight_id": preflight_id,
        "state": state,
        "bodies_executed": final["bodies_executed"],
        "nodeid": target if final["collected_nodeids"] == [target] else None,
        "receipt": str(record_path),
        "receipt_sha256": receipt_sha256,
    }


def _validate_hex8sri_convergence24_preflight_receipt(
    store: Path,
    preflight_id: str,
    *,
    target: str,
    identity: Mapping[str, Any],
    source_fingerprint: str,
    controller_provenance: Mapping[str, Any],
    manifest_binding: Mapping[str, Any],
    attempt_ledger: Mapping[str, Any],
) -> tuple[Path, str]:
    receipt_dir = _preflight_directory(store, HEX8SRI_CONVERGENCE24_WORKTREE_ID, preflight_id)
    record_path = receipt_dir / "preflight.json"
    sha_path = receipt_dir / "preflight.sha256.json"
    if not record_path.is_file() or not sha_path.is_file():
        raise PolicyError("a successful exact-node HEX8-SRI collect-only receipt is required")
    try:
        receipt = _read_strict_json(record_path)
        sidecar = _read_strict_json(sha_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PolicyError(f"HEX8-SRI preflight receipt is unreadable: {exc}") from exc
    actual_sha256 = _sha256(record_path)
    collection = receipt.get("collection_report")
    recorded_ledger = receipt.get("attempt_ledger")
    try:
        expected_solver_origin = str((Path(str(identity["root"])) / "src" / "solveur" / "__init__.py").resolve())
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise PolicyError("HEX8-SRI preflight identity does not provide a registered solver root") from exc
    if sidecar.get("sha256") != actual_sha256:
        raise PolicyError("HEX8-SRI preflight receipt checksum mismatch")
    if (
        receipt.get("schema") != "qfsolver-development-hex8sri-convergence24-preflight-v1"
        or receipt.get("state") != "PREFLIGHT_PASS"
        or receipt.get("mandate_id") != HEX8SRI_CONVERGENCE24_MANDATE_ID
        or receipt.get("campaign_id") != HEX8SRI_CONVERGENCE24_CAMPAIGN_ID
        or receipt.get("bodies_executed") is not False
        or receipt.get("attempt_reserved") is not False
        or receipt.get("execution_authorized") is not False
        or receipt.get("worktree_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        or receipt.get("target") != target
        or receipt.get("preflight_id") != preflight_id
        or receipt.get("identity") != dict(identity)
        or receipt.get("source_fingerprint") != source_fingerprint
        or receipt.get("controller_provenance") != dict(controller_provenance)
        or receipt.get("case_manifest") != dict(manifest_binding)
        or receipt.get("solver_origin_expected") != expected_solver_origin
        or receipt.get("solver_origin_observed") != expected_solver_origin
        or receipt.get("collected_nodeids") != [target]
        or receipt.get("skip_status") != "NO_SKIP_MARKERS"
        or not isinstance(recorded_ledger, Mapping)
        or dict(recorded_ledger) != dict(attempt_ledger)
        or recorded_ledger.get("attempts_reserved") is not False
        or not isinstance(collection, Mapping)
        or collection.get("schema") != "qfsolver-hex8sri-convergence24-collection-v1"
        or collection.get("scope_id") != HEX8SRI_CONVERGENCE24_WORKTREE_ID
        or collection.get("target") != target
        or collection.get("collected_nodeids") != [target]
        or collection.get("skip_markers") != []
        or collection.get("bodies_executed") is not False
        or collection.get("exitstatus") != 0
    ):
        raise PolicyError(
            "HEX8-SRI preflight does not match this source, controller, manifest and exact collect-only node"
        )
    return record_path, actual_sha256


def preflight_hex8sri_convergence24_pytest(
    target: str, preflight_id: str | None = None, *, policy: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Collect one registered HEX8-SRI convergence node without reserving an attempt."""
    current_policy = load_policy() if policy is None else dict(policy)
    worktree_id = HEX8SRI_CONVERGENCE24_WORKTREE_ID
    targets = resolve_targets("fem_exploratory", target, current_policy, worktree_id=worktree_id)
    entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
        worktree_id, target, current_policy
    )
    store = _run_root(current_policy)
    ledger_path, _ledger_lock, mandate_id, predecessor = _node_ledger_context(current_policy, store, worktree_id)
    if predecessor is not None or mandate_id != entry["development_mandate_id"]:
        raise PolicyError("HEX8-SRI collect-only preflight is not bound to its isolated campaign mandate")
    manifest_path, manifest, manifest_sha256 = _hex8sri_convergence24_manifest(entry, execution_root, target)
    controller_provenance = _controller_provenance()
    _verify_hex8sri_convergence24_controller_identity(manifest, controller_provenance)
    case = _hex8sri_convergence24_case(target)
    if case is None:
        raise PolicyError("HEX8-SRI preflight target is outside the exact convergence24 matrix")
    formulation, nu_token, mesh_token = case
    case_contract = _hex8sri_convergence24_case_contract(manifest)
    if (
        "x".join(map(str, case_contract["divisions_xyz"])) != mesh_token
        or case_contract["element_count"] != math.prod(case_contract["divisions_xyz"])
        or manifest.get("budgets")
        != {
            **_hex8sri_convergence24_budget(target),
            "attempts_per_nodeid": 1,
            "initial_campaign_max_attempts": 24,
            "blas_thread_environment": entry["blas_thread_environment"],
            "budget_semantics": {
                "captured_output": "controller-enforced byte caps",
                "rss_process_temporary_archive": "sampled soft observations, not OS quotas",
                "wall_timeout": "watchdog process-tree termination, best effort",
            },
        }
    ):
        raise PolicyError("HEX8-SRI case mesh or budget differs from its exact registered contract")
    manifest_binding = {
        "path": str(manifest_path),
        "sha256": manifest_sha256,
        "registration_sha256": _hex8sri_manifest_registration_sha256(manifest),
        "case_id": manifest["case_id"],
        "scope_id": worktree_id,
    }
    attempt_ledger = {
        "path": str(ledger_path),
        "mandate_id": mandate_id,
        "attempts_reserved": False,
    }
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    limits = dict(entry["per_node_budgets"][target])
    minimum_free_mib = max(int(current_policy["minimum_free_disk_mib"]), int(limits["minimum_free_disk_mib"]))
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free)
    if free_bytes < minimum_free_mib * 1024 * 1024:
        raise PolicyError(
            f"insufficient free disk for HEX8-SRI collect-only preflight: {free_bytes} bytes; "
            f"requires {minimum_free_mib} MiB"
        )

    preflight_id = preflight_id or f"pf-{uuid.uuid4().hex[:12]}"
    receipt_dir = _preflight_directory(store, worktree_id, preflight_id)
    if receipt_dir.exists():
        raise PolicyError("preflight ID already exists; refusing to overwrite a prior receipt")
    temporary_dir = receipt_dir / "tmp"
    output_dir = receipt_dir / "output"
    temporary_dir.mkdir(parents=True)
    output_dir.mkdir()
    collection_report_path = temporary_dir / "collection-report.json"
    command = build_pytest_command(
        "fem_exploratory",
        targets,
        temporary_dir,
        repository_root=execution_root,
        source_root=source_root,
        controller_root=ROOT,
        allow_native_skip_override=False,
        collect_only=True,
        hex8sri_convergence24_collect_only_attestation=True,
    )
    if "--collect-only" not in command or command[-1] != target:
        raise PolicyError("HEX8-SRI preflight must collect only its one exact registered nodeid")
    environment = build_child_environment(temporary_dir, source_root=source_root)
    environment.update(entry["blas_thread_environment"])
    environment.update(
        {
            "QF_DEV_WORKTREE_ID": worktree_id,
            "QF_DEV_PREFLIGHT_SCOPE_ID": worktree_id,
            "QF_DEV_PREFLIGHT_TARGET": target,
            "QF_DEV_PREFLIGHT_COLLECTION_REPORT": str(collection_report_path),
        }
    )
    limits["minimum_free_disk_mib"] = minimum_free_mib
    expected_origin = str((source_root / "solveur" / "__init__.py").resolve())
    started = datetime.now(timezone.utc).isoformat()
    record_path = receipt_dir / "preflight.json"
    initial = {
        "schema": "qfsolver-development-hex8sri-convergence24-preflight-v1",
        "mode": "DEVELOPMENT_AUTONOMOUS",
        "mandate_id": mandate_id,
        "worktree_id": worktree_id,
        "campaign_id": entry["campaign_id"],
        "target": target,
        "preflight_id": preflight_id,
        "phase": "PYTEST_COLLECT_ONLY",
        "attempt_reserved": False,
        "execution_authorized": False,
        "bodies_executed": False,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "case_manifest": manifest_binding,
        "case_contract": case_contract,
        "attempt_ledger": attempt_ledger,
        "solver_origin_expected": expected_origin,
        "controller_provenance": controller_provenance,
        "command": command,
        "budgets": limits,
        "free_disk_before_bytes": free_bytes,
    }
    try:
        with _exclusive_file_lock(store / "locks" / "hex8sri-convergence24-preflight.lock"):
            result = run_supervised_command(
                command,
                cwd=execution_root,
                environment=environment,
                output_dir=output_dir,
                temporary_dir=temporary_dir,
                limits=limits,
                poll_interval=float(current_policy["poll_interval_seconds"]),
            )
    except OSError as exc:
        _atomic_json(
            record_path,
            {
                **initial,
                "state": "PREFLIGHT_LAUNCH_FAILED",
                "started_at_utc": started,
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "launch_error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise PolicyError(f"HEX8-SRI collect-only preflight could not launch: {exc}") from exc

    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
    combined = stdout + "\n" + stderr
    collection_report = None
    skip_status = "UNCONFIRMED"
    if collection_report_path.is_file():
        try:
            parsed = json.loads(collection_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            collection_report = parsed
            if (
                parsed.get("schema") == "qfsolver-hex8sri-convergence24-collection-v1"
                and parsed.get("scope_id") == worktree_id
                and parsed.get("target") == target
                and parsed.get("collected_nodeids") == [target]
                and parsed.get("bodies_executed") is False
                and parsed.get("exitstatus") == 0
                and isinstance(parsed.get("skip_markers"), list)
            ):
                skip_status = "SKIP_MARKER_PRESENT" if parsed["skip_markers"] else "NO_SKIP_MARKERS"
    solver_origin_observed = _observed_solver_origin(combined)
    exact_node_collected = isinstance(collection_report, Mapping) and collection_report.get("collected_nodeids") == [
        target
    ]
    _after_entry, _after_root, _after_source, after_identity, after_fingerprint = _registered_worktree(
        worktree_id, target, current_policy
    )
    if after_identity != identity or after_fingerprint != source_fingerprint:
        state = "PREFLIGHT_SOURCE_CHANGED"
    elif result.status != "PASS":
        state = "PREFLIGHT_FAILED"
    elif solver_origin_observed != expected_origin:
        state = "PREFLIGHT_WRONG_SOLVER_ORIGIN"
    elif not exact_node_collected:
        state = "PREFLIGHT_NODEID_NOT_CONFIRMED"
    elif collection_report is None:
        state = "PREFLIGHT_COLLECTION_REPORT_MISSING"
    elif skip_status == "SKIP_MARKER_PRESENT":
        state = "PREFLIGHT_SKIP_MARKED"
    elif skip_status != "NO_SKIP_MARKERS":
        state = "PREFLIGHT_COLLECTION_REPORT_INVALID"
    else:
        state = "PREFLIGHT_PASS"
    final = {
        **initial,
        "state": state,
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "collected_nodeids": [target] if exact_node_collected else [],
        "solver_origin_observed": solver_origin_observed,
        "return_code": result.return_code,
        "elapsed_seconds": result.elapsed_seconds,
        "peak_rss_bytes": result.peak_rss_bytes,
        "peak_process_count": result.peak_process_count,
        "stdout_bytes": result.stdout_bytes,
        "stderr_bytes": result.stderr_bytes,
        "stdout_sha256": _sha256(stdout_path),
        "stderr_sha256": _sha256(stderr_path),
        "archive_bytes": result.archive_bytes,
        "temporary_bytes": result.temporary_bytes,
        "stop_reason": result.stop_reason,
        "identity_after": after_identity,
        "source_fingerprint_after": after_fingerprint,
        "collection_report": collection_report,
        "skip_status": skip_status,
        "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
    }
    _atomic_json(record_path, final)
    receipt_sha256 = _sha256(record_path)
    _atomic_json(receipt_dir / "preflight.sha256.json", {"sha256": receipt_sha256})
    receipt_validated = False
    if state == "PREFLIGHT_PASS":
        try:
            validated_path, validated_sha256 = _validate_hex8sri_convergence24_preflight_receipt(
                store,
                preflight_id,
                target=target,
                identity=identity,
                source_fingerprint=source_fingerprint,
                controller_provenance=controller_provenance,
                manifest_binding=manifest_binding,
                attempt_ledger=attempt_ledger,
            )
            if validated_path != record_path or validated_sha256 != receipt_sha256:
                raise PolicyError("HEX8-SRI receipt validator returned a different evidence identity")
            receipt_validated = True
        except PolicyError:
            state = "PREFLIGHT_RECEIPT_INVALID"
            final["state"] = state
            _atomic_json(record_path, final)
            receipt_sha256 = _sha256(record_path)
            _atomic_json(receipt_dir / "preflight.sha256.json", {"sha256": receipt_sha256})
    return {
        "preflight_id": preflight_id,
        "state": state,
        "receipt_validated": receipt_validated,
        "bodies_executed": False,
        "nodeid": target if exact_node_collected else None,
        "receipt": str(record_path),
        "receipt_sha256": receipt_sha256,
        "metrics": final,
    }


def preflight_wp12_vv3d_pytest(
    target: str, preflight_id: str | None = None, *, policy: Mapping[str, Any] | None = None,
    worktree_id: str = VV3D_WORKTREE_ID,
) -> dict[str, Any]:
    """Collect exactly one registered VV3D node; this never reserves campaign budget."""
    current_policy = load_policy() if policy is None else dict(policy)
    if worktree_id not in {VV3D_WORKTREE_ID, VV3D_R2_WORKTREE_ID}:
        raise PolicyError("VV3D collect-only supports only the registered R1 or R2 scope")
    is_r2 = worktree_id == VV3D_R2_WORKTREE_ID
    campaign_id = VV3D_R2_CAMPAIGN_ID if is_r2 else VV3D_CAMPAIGN_ID
    matrix_subdirectory = "prepared_20261030_r2" if is_r2 else "prepared_20261029"
    targets = resolve_targets("fem_exploratory", target, current_policy, worktree_id=worktree_id)
    entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
        worktree_id, target, current_policy
    )
    matrix_path = execution_root / "experiments" / "wp12_vv3d_adaptive" / matrix_subdirectory / "MATRIX_NOT_AUTHORIZED.json"
    try:
        matrix = _read_strict_json(matrix_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PolicyError(f"VV3D prepared matrix is unreadable: {exc}") from exc
    cases = matrix.get("cases") if isinstance(matrix, Mapping) else None
    case_id = target.rsplit("[", maxsplit=1)[-1][:-1]
    expected_dofs = entry["per_node_selected_dofs"].get(target)
    initial_nodes = VV3D_R2_NODEIDS if is_r2 else VV3D_INITIAL_NODEIDS
    if target in initial_nodes:
        expected_ids = {nodeid.rsplit("[", maxsplit=1)[-1][:-1] for nodeid in initial_nodes}
        if (not isinstance(cases, list) or len(cases) != len(expected_ids)
                or {item.get("case_id") for item in cases if isinstance(item, Mapping)} != expected_ids):
            raise PolicyError("VV3D prepared matrix differs from the exact twelve-case controller catalogue")
        case = next((item for item in cases if item.get("case_id") == case_id), None)
        if (case is None or case.get("nodeid") != target or case.get("dofs") != expected_dofs
                or case.get("execution_authorized") is not False or case.get("do_not_execute") is not True
                or case.get("nodeid_status") != "PREPARED_NOT_AUTHORIZED"):
            raise PolicyError("VV3D case identity or preparation-only state does not match controller registration")
        mesh_path = execution_root / "experiments" / "wp12_vv3d_adaptive" / matrix_subdirectory / str(case.get("mesh_file", ""))
        expected_mesh_sha = case.get("mesh_sha256")
    else:
        if is_r2:
            raise PolicyError("VV3D R2 scope excludes adaptive FEM and QPOST targets")
        candidate, adaptive_bindings = _vv3d_adaptive_candidate_metadata(execution_root, target)
        case = candidate
        case_id = candidate["candidate_id"]
        if (case.get("candidate_id") != case_id or case.get("nodeid") != target
                or candidate.get("status") != "PREPARED_NOT_AUTHORIZED"
                or candidate.get("nodeid_status") != "REGISTERED_PREPARED_NOT_AUTHORIZED"
                or candidate.get("prepared_mesh", {}).get("selected_dofs") != expected_dofs):
            raise PolicyError("VV3D adaptive candidate differs from exact controller node/DDL registration")
        mesh_path = (execution_root / "experiments" / "wp12_vv3d_adaptive" /
                     str(candidate["prepared_mesh"]["path"]))
        expected_mesh_sha = adaptive_bindings["mesh_sha256"]
    if not mesh_path.is_file() or _sha256(mesh_path) != expected_mesh_sha:
        raise PolicyError("VV3D mesh raw SHA-256 does not match the prepared case/catalog binding")

    store = _run_root(current_policy, worktree_id)
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    minimum_free_mib = int(current_policy["minimum_free_disk_mib"])
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free,
                     shutil.disk_usage(store.parent if not store.exists() else store).free)
    if free_bytes < minimum_free_mib * 1024 * 1024:
        raise PolicyError(f"insufficient free disk for VV3D collect-only: {free_bytes} bytes")
    preflight_id = preflight_id or f"pf-{uuid.uuid4().hex[:12]}"
    receipt_dir = _preflight_directory(store, worktree_id, preflight_id)
    if receipt_dir.exists():
        raise PolicyError("VV3D preflight ID already exists; refusing to overwrite a prior receipt")
    temporary_dir = receipt_dir / "tmp"
    output_dir = receipt_dir / "output"
    temporary_dir.mkdir(parents=True)
    output_dir.mkdir()
    collection_report_path = temporary_dir / "collection-report.json"
    limits = dict(entry["budgets"])
    limits["minimum_free_disk_mib"] = minimum_free_mib
    command = build_pytest_command(
        "fem_exploratory", targets, temporary_dir, repository_root=execution_root,
        source_root=source_root, controller_root=ROOT, collect_only=True,
        vv3d_collect_only_attestation=not is_r2,
        vv3d_r2_collect_only_attestation=is_r2,
    )
    environment = build_child_environment(temporary_dir, source_root=source_root)
    environment.update({
        "QF_DEV_WORKTREE_ID": worktree_id,
        "QF_DEV_SELECTED_DOFS": str(expected_dofs),
        "QF_DEV_MAX_DOFS": str(entry["target_max_dofs"]),
        "QF_DEV_PREFLIGHT_COLLECTION_REPORT": str(collection_report_path),
    })
    ledger = store / str(entry["node_attempt_ledger"]["path"])
    r1_predecessor_sha = None
    if is_r2:
        predecessor_path = Path(str(entry["node_attempt_ledger"]["predecessor"]["path"]))
        try:
            r1_predecessor_sha = _sha256(predecessor_path)
        except OSError as exc:
            raise PolicyError("VV3D R2 immutable R1 predecessor ledger is unavailable") from exc
        if r1_predecessor_sha != entry["node_attempt_ledger"]["predecessor"]["sha256"]:
            raise PolicyError("VV3D R2 immutable R1 predecessor ledger SHA-256 mismatch")
    initial_ledger_sha = _sha256(ledger) if ledger.is_file() else None
    record_path = receipt_dir / "preflight.json"
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        with _exclusive_file_lock(store / "locks" / f"{worktree_id}-preflight.lock"):
            result = run_supervised_command(
                command, cwd=execution_root, environment=environment, output_dir=output_dir,
                temporary_dir=temporary_dir, limits=limits,
                poll_interval=float(current_policy["poll_interval_seconds"]),
            )
    except OSError as exc:
        _atomic_json(record_path, {
            "schema": "qfsolver-development-vv3d-preflight-v1", "state": "PREFLIGHT_LAUNCH_FAILED",
        "campaign_id": campaign_id, "worktree_id": worktree_id, "target": target,
            "preflight_id": preflight_id, "attempt_reserved": False, "bodies_executed": False,
            "started_at_utc": started_at, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "launch_error": f"{type(exc).__name__}: {exc}",
        })
        raise PolicyError(f"VV3D collect-only preflight could not launch: {exc}") from exc
    stdout = (output_dir / "stdout.log").read_text(encoding="utf-8", errors="replace")
    stderr = (output_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
    report = _read_strict_json(collection_report_path) if collection_report_path.is_file() else None
    expected_origin = str((source_root / "solveur" / "__init__.py").resolve())
    observed_origin = _observed_solver_origin(stdout + "\n" + stderr)
    after_entry, after_root, after_src, after_identity, after_fingerprint = _registered_worktree(
        worktree_id, target, current_policy
    )
    if after_entry != entry or after_root != execution_root or after_src != source_root \
            or after_identity != identity or after_fingerprint != source_fingerprint:
        state = "PREFLIGHT_SOURCE_CHANGED"
    elif (result.status == "PASS" and observed_origin == expected_origin and isinstance(report, Mapping)
          and report.get("schema") == "qfsolver-wp12-vv3d-collection-v1"
          and report.get("scope_id") == worktree_id and report.get("target") == target
          and report.get("collected_nodeids") == [target] and report.get("skip_markers") == []
          and report.get("bodies_executed") is False and report.get("exitstatus") == 0):
        state = "PREFLIGHT_PASS"
    else:
        state = "PREFLIGHT_FAILED"
    if is_r2:
        observed_r1_sha = _sha256(Path(str(entry["node_attempt_ledger"]["predecessor"]["path"])))
        if observed_r1_sha != r1_predecessor_sha or (_sha256(ledger) if ledger.is_file() else None) != initial_ledger_sha:
            state = "PREFLIGHT_LEDGER_CHANGED"
    final = {
        "schema": "qfsolver-development-vv3d-preflight-v1", "state": state, "status": state,
        "campaign_id": campaign_id, "worktree_id": worktree_id, "target": target, "nodeid": target,
        "case_id": case_id, "preflight_id": preflight_id, "identity": identity,
        "source_fingerprint": source_fingerprint,
        "controller_provenance": _vv3d_scope_controller_provenance(worktree_id),
        "solver_origin_expected": expected_origin, "solver_origin_observed": observed_origin,
        "collection_report": report, "selected_nodeids": [target] if state == "PREFLIGHT_PASS" else [],
        "skipped": 0 if state == "PREFLIGHT_PASS" else None,
        "attempt_reserved": False, "reservation_created": False, "bodies_executed": False,
        "ledger_path": str(ledger), "ledger_sha256_before": initial_ledger_sha,
        "ledger_sha256_after": _sha256(ledger) if ledger.is_file() else None,
        "command": command, "budgets": limits, "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "return_code": result.return_code, "elapsed_seconds": result.elapsed_seconds,
        "stdout_sha256": _sha256(output_dir / "stdout.log"),
        "stderr_sha256": _sha256(output_dir / "stderr.log"),
        "peak_rss_bytes": result.peak_rss_bytes, "stop_reason": result.stop_reason,
    }
    if is_r2:
        final["r1_predecessor_sha256"] = r1_predecessor_sha
    _atomic_json(record_path, final)
    receipt_sha = _sha256(record_path)
    _atomic_json(receipt_dir / "preflight.sha256.json", {"sha256": receipt_sha})
    if state != "PREFLIGHT_PASS":
        raise PolicyError(f"VV3D collect-only preflight failed closed: {state}")
    return {"preflight_id": preflight_id, "state": state, "bodies_executed": False,
            "attempt_reserved": False, "nodeid": target, "receipt": str(record_path),
            "receipt_sha256": receipt_sha, "metrics": final}


def _vv3d_execution_bindings(
    *, target: str, preflight_id: str, manifest_path: Path, entry: Mapping[str, Any], execution_root: Path,
    identity: Mapping[str, Any], source_fingerprint: str, controller_provenance: Mapping[str, Any],
    store: Path,
) -> tuple[dict[str, Any], dict[str, Any], str, str, str, str]:
    """Validate campaign decision, exact case manifest and collect-only receipt before reservation."""
    if target in VV3D_ADAPTIVE_FEM_NODEIDS:
        return _vv3d_adaptive_fem_launch_bindings(
            target=target, preflight_id=preflight_id, manifest_path=manifest_path,
            entry=entry, execution_root=execution_root, identity=identity,
            source_fingerprint=source_fingerprint, controller_provenance=controller_provenance,
            store=store,
        )
    vv3d_contract = _load_vv3d_contract_module()

    manifest_path = manifest_path.resolve(strict=True)
    auth_root = (store / "authorizations" / VV3D_WORKTREE_ID).resolve()
    try:
        manifest_path.relative_to(auth_root)
    except ValueError as exc:
        raise PolicyError("VV3D execution manifest must be inside the isolated campaign authorization root") from exc
    manifest_raw = manifest_path.read_bytes()
    try:
        manifest = _read_strict_json(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PolicyError(f"VV3D execution manifest is invalid: {exc}") from exc
    contract_path = auth_root / "campaign-contract.json"
    decision_path = auth_root / "campaign-decision.json"
    try:
        contract_raw = contract_path.read_bytes()
        decision_raw = decision_path.read_bytes()
        contract = _read_strict_json(contract_path)
        decision = _read_strict_json(decision_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PolicyError(f"VV3D frozen campaign contract or Owner decision is unavailable: {exc}") from exc
    registered_nodes = set(VV3D_INITIAL_NODEIDS) | set(VV3D_ADAPTIVE_FEM_NODEIDS) | set(VV3D_QPOST_NODEIDS)
    controller_fingerprint = _stable_fingerprint(controller_provenance)
    try:
        vv3d_contract.validate_contract(
            contract, registered_nodeids=registered_nodes,
            controller_fingerprint=controller_fingerprint, scientific_fingerprint=source_fingerprint,
        )
        vv3d_contract.validate_decision(contract, decision, contract_bytes=contract_raw)
        case_id = target.rsplit("[", maxsplit=1)[-1][:-1]
        vv3d_contract.validate_decision_scope(decision, case_id)
        vv3d_contract.verify_artifact_bindings(
            contract, roots={kind: execution_root / "experiments" / "wp12_vv3d_adaptive"
                             for kind in ("mesh", "manifest", "oracle", "criteria")},
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise PolicyError(f"VV3D campaign decision or bound contract is invalid: {exc}") from exc
    contract_case = next((case for case in contract["cases"] if case.get("case_id") == case_id), None)
    matrix_path = execution_root / "experiments" / "wp12_vv3d_adaptive" / "prepared_20261029" / "MATRIX_NOT_AUTHORIZED.json"
    matrix = _read_strict_json(matrix_path)
    matrix_case = next((case for case in matrix["cases"] if case.get("case_id") == case_id), None)
    if contract_case is None or matrix_case is None or contract_case.get("nodeid") != target:
        raise PolicyError("VV3D exact nodeid is not present in both the approved contract and prepared case matrix")
    transition_binding = None
    if contract_case.get("phase") == "ADAPTIVE":
        receipt_binding = manifest.get("transition_eligibility")
        if not isinstance(receipt_binding, Mapping) or set(receipt_binding) != {"path", "sha256"}:
            raise PolicyError("adaptive VV3D case requires an immutable eligibility receipt binding")
        if not re.fullmatch(r"[0-9a-f]{64}", str(receipt_binding.get("sha256", ""))):
            raise PolicyError("adaptive eligibility receipt SHA-256 is invalid")
        eligibility_root = (auth_root / "eligibility").resolve()
        eligibility_path = (auth_root / str(receipt_binding["path"])).resolve(strict=True)
        try:
            eligibility_path.relative_to(eligibility_root)
        except ValueError as exc:
            raise PolicyError("adaptive eligibility receipt must be below the campaign eligibility root") from exc
        eligibility_raw = eligibility_path.read_bytes()
        if hashlib.sha256(eligibility_raw).hexdigest() != receipt_binding["sha256"]:
            raise PolicyError("adaptive eligibility receipt SHA-256 mismatch")
        eligibility = _read_strict_json(eligibility_path)
        source_case_id = contract_case["trigger"]["source_case_id"]
        source_records = []
        for candidate in store.rglob("run.json") if store.exists() else ():
            try:
                value = _read_strict_json(candidate)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if value.get("case_id") == source_case_id and value.get("state") != "RUNNING":
                source_records.append((candidate, value))
        if len(source_records) != 1:
            raise PolicyError("adaptive transition requires exactly one completed source-case run record")
        source_path, source_record = source_records[0]
        if not _vv3d_seed_passes_required_gates(source_record, require_campaign_pass=True):
            raise PolicyError("adaptive transitions require a consistent verified source PASS and campaign-gate PASS")
        source_status = {"PASS": "PASS", "PYTEST_FAILED": "FAIL"}.get(
            source_record.get("state"), str(source_record.get("state")),
        )
        try:
            vv3d_contract.validate_transition_eligibility(
                contract, decision, contract_sha256=hashlib.sha256(contract_raw).hexdigest(),
                decision_sha256=hashlib.sha256(decision_raw).hexdigest(),
                source_case_id=source_case_id, destination_case_id=case_id,
                source_status=source_status, source_result_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                source_observables=source_record.get("scientific_observables", {}), receipt=eligibility,
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise PolicyError(f"adaptive continuation receipt is invalid: {exc}") from exc
        transition_binding = {
            "transition_receipt_sha256": receipt_binding["sha256"],
            "transition_source_case_id": source_case_id,
            "transition_destination_case_id": case_id,
        }
    criteria_path = (execution_root / "experiments" / "wp12_vv3d_adaptive" /
                     str(contract_case["criteria_path"])).resolve(strict=True)
    try:
        criteria_path.relative_to((execution_root / "experiments" / "wp12_vv3d_adaptive").resolve())
        criteria_document = _read_strict_json(criteria_path)
        frozen_criteria = criteria_document["criteria"]
        frozen_criteria_sha = hashlib.sha256(json.dumps(
            frozen_criteria, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PolicyError(f"VV3D frozen criteria artifact is invalid: {exc}") from exc
    expected = {
        "schema": "qf-wp12-vv3d-case-manifest-v1", "campaign_id": VV3D_CAMPAIGN_ID,
        "case_id": case_id, "nodeid": target, "state": "OWNER_AUTHORIZED",
        "execution_authorized": True, "do_not_execute": False,
        "mesh_sha256": matrix_case.get("mesh_sha256"),
        "selected_dofs": matrix_case.get("dofs"),
        "timeout_seconds": matrix_case.get("timeout_max_seconds"),
        "rss_soft_limit_mib": 4096, "max_attempts": 1,
        "criteria_sha256": frozen_criteria_sha,
        "frozen_criteria": frozen_criteria,
        "scientific_fingerprint": source_fingerprint, "controller_fingerprint": controller_fingerprint,
    }
    if not isinstance(manifest, Mapping) or any(manifest.get(key) != value for key, value in expected.items()):
        raise PolicyError("VV3D Owner manifest identity, state or budget does not match this exact case")
    if (manifest.get("campaign_contract_sha256") != hashlib.sha256(contract_raw).hexdigest()
            or manifest.get("prepared_case_manifest_sha256") != contract_case.get("manifest_sha256")):
        raise PolicyError("VV3D execution manifest is not bound to the approved campaign and prepared case")
    approved = manifest.get("owner_decision")
    if (not isinstance(approved, Mapping) or approved.get("status") != "APPROVED"
            or approved.get("approved_by") != "Owner" or approved.get("decision_id") != decision.get("decision_id")
            or approved.get("decision_sha256") != hashlib.sha256(decision_raw).hexdigest()):
        raise PolicyError("VV3D execution manifest does not reference the exact archived campaign Owner decision")
    # This static preparation policy advertises runner capability only. The
    # exact Owner decision, authorized case manifest, collect-only receipt and
    # provenance checks above/below are the sole execution gate.
    preflight = manifest.get("preflight")
    if (not isinstance(preflight, Mapping) or preflight.get("nodeid") != target
            or preflight.get("preflight_id") != preflight_id or preflight.get("status") != "PREFLIGHT_PASS"):
        raise PolicyError("VV3D execution manifest lacks the exact successful collect-only preflight")
    preflight_path = Path(str(preflight.get("receipt_path", ""))).resolve(strict=True)
    try:
        preflight_path.relative_to(store.resolve())
    except ValueError as exc:
        raise PolicyError("VV3D preflight receipt must be inside the candidate run store") from exc
    preflight_raw = preflight_path.read_bytes()
    preflight_digest = hashlib.sha256(preflight_raw).hexdigest()
    if preflight_digest != preflight.get("receipt_sha256"):
        raise PolicyError("VV3D preflight raw-byte SHA-256 mismatch")
    try:
        preflight_sha_sidecar = _read_strict_json(
            preflight_path.parent / "preflight.sha256.json"
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PolicyError(f"VV3D preflight checksum sidecar is unavailable: {exc}") from exc
    if preflight_sha_sidecar.get("sha256") != preflight_digest:
        raise PolicyError("VV3D preflight checksum sidecar does not match its immutable receipt")
    preflight_receipt = _read_strict_json(preflight_path)
    if (preflight_receipt.get("status") != "PREFLIGHT_PASS" or preflight_receipt.get("target") != target
            or preflight_receipt.get("nodeid") != target or preflight_receipt.get("preflight_id") != preflight_id
            or preflight_receipt.get("source_fingerprint") != source_fingerprint
            or preflight_receipt.get("controller_provenance") != dict(controller_provenance)
            or preflight_receipt.get("identity") != dict(identity)
            or preflight_receipt.get("bodies_executed") is not False
            or preflight_receipt.get("attempt_reserved") is not False
            or preflight_receipt.get("reservation_created") is not False
            or preflight_receipt.get("selected_nodeids") != [target]
            or preflight_receipt.get("skipped") != 0):
        raise PolicyError("VV3D preflight receipt does not attest this exact source and node without skips")
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    resolved_manifest = dict(manifest)
    if transition_binding is not None:
        resolved_manifest["_validated_transition_binding"] = transition_binding
    return resolved_manifest, dict(preflight_receipt), manifest_sha, preflight_digest, decision["decision_id"], hashlib.sha256(decision_raw).hexdigest()


def _load_vv3d_r2_contract_module(execution_root: Path) -> Any:
    """Load the source-bound R2 contract helpers without importing solver code."""
    import importlib.util

    path = execution_root / "experiments" / "wp12_vv3d_adaptive" / "r2_contract.py"
    spec = importlib.util.spec_from_file_location("qf_wp12_vv3d_r2_contract", path)
    if spec is None or spec.loader is None:
        raise PolicyError("VV3D R2 contract helper is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _vv3d_r2_execution_bindings(
    *, target: str, preflight_id: str, manifest_path: Path, entry: Mapping[str, Any],
    execution_root: Path, identity: Mapping[str, Any], source_fingerprint: str,
    controller_provenance: Mapping[str, Any], store: Path,
) -> tuple[dict[str, Any], dict[str, Any], str, str, str, str]:
    """Validate the independent R2 contract, exact Owner decision and fresh collect-only receipt."""
    if target not in VV3D_R2_NODEIDS:
        raise PolicyError("VV3D R2 accepts only its exact twelve initial FEM nodeids")
    helper = _load_vv3d_r2_contract_module(execution_root)
    current_controller = _stable_fingerprint(controller_provenance)
    predecessor = entry["node_attempt_ledger"]["predecessor"]
    if _sha256(Path(predecessor["path"])) != predecessor["sha256"]:
        raise PolicyError("VV3D R2 immutable R1 predecessor ledger SHA-256 mismatch")

    auth_root = (store / "authorizations" / VV3D_R2_WORKTREE_ID).resolve()
    try:
        resolved_manifest = manifest_path.resolve(strict=True)
        resolved_manifest.relative_to((auth_root / "manifests").resolve())
        contract_path = auth_root / "campaign-contract.json"
        decision_path = auth_root / "campaign-decision.json"
        contract_raw, decision_raw = contract_path.read_bytes(), decision_path.read_bytes()
        contract, decision = _read_strict_json(contract_path), _read_strict_json(decision_path)
        manifest_raw = resolved_manifest.read_bytes()
        manifest = _read_strict_json(resolved_manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PolicyError(f"VV3D R2 Owner contract, decision or case manifest is unavailable: {exc}") from exc
    # R2 files are emitted in canonical JSON form. This prevents semantically
    # equivalent rewrites from silently changing the contract/decision binding.
    if (contract_raw != json.dumps(contract, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            or decision_raw != json.dumps(decision, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")):
        raise PolicyError("VV3D R2 contract and Owner decision must use canonical immutable JSON bytes")
    contract_sha = hashlib.sha256(contract_raw).hexdigest()
    decision_sha = hashlib.sha256(decision_raw).hexdigest()
    try:
        validated_contract_sha = helper.validate_contract(
            contract, scientific_fingerprint=source_fingerprint,
            controller_fingerprint=current_controller,
            r1_ledger_sha256=predecessor["sha256"],
        )
        validated_decision_sha = helper.validate_owner_decision(
            decision, contract_sha256=contract_sha,
            scientific_fingerprint=source_fingerprint, controller_fingerprint=current_controller,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise PolicyError(f"VV3D R2 contract or Owner decision is invalid: {exc}") from exc
    if validated_contract_sha != contract_sha or validated_decision_sha != decision_sha:
        raise PolicyError("VV3D R2 canonical contract or decision digest mismatch")

    case_id = target.rsplit("[", maxsplit=1)[-1][:-1]
    case = next((record for record in contract["cases"] if record["case_id"] == case_id), None)
    matrix_path = (execution_root / "experiments" / "wp12_vv3d_adaptive" /
                   "prepared_20261030_r2" / "MATRIX_NOT_AUTHORIZED.json")
    matrix = _read_strict_json(matrix_path)
    matrix_case = next((record for record in matrix.get("cases", [])
                        if isinstance(record, Mapping) and record.get("case_id") == case_id), None)
    if (case is None or matrix.get("campaign_id") != VV3D_R2_CAMPAIGN_ID
            or matrix_case is None or case["nodeid"] != target
            or case["mesh_sha256"] != matrix_case.get("mesh_sha256")
            or case["selected_dofs"] != matrix_case.get("dofs")
            or case["timeout_seconds"] != matrix_case.get("timeout_max_seconds")):
        raise PolicyError("VV3D R2 contract case differs from the exact prepared matrix or nodeid")

    criteria_path = (execution_root / "experiments" / "wp12_vv3d_adaptive" / case["criteria_path"]).resolve(strict=True)
    oracle_path = (execution_root / "experiments" / "wp12_vv3d_adaptive" / case["oracle_path"]).resolve(strict=True)
    experiment_root = (execution_root / "experiments" / "wp12_vv3d_adaptive").resolve(strict=True)
    for artifact in (criteria_path, oracle_path):
        try:
            artifact.relative_to(experiment_root)
        except ValueError as exc:
            raise PolicyError("VV3D R2 criteria/oracle artifact escapes its scientific source root") from exc
    if (_sha256(criteria_path) != case["criteria_file_sha256"]
            or _sha256(oracle_path) != case["oracle_sha256"]):
        raise PolicyError("VV3D R2 criteria or independent-oracle raw SHA-256 mismatch")
    criteria_doc = _read_strict_json(criteria_path)
    frozen_criteria = criteria_doc.get("criteria") if isinstance(criteria_doc, Mapping) else None
    if not isinstance(frozen_criteria, list) or not frozen_criteria:
        raise PolicyError("VV3D R2 criteria artifact has no frozen criteria list")
    criteria_sha = hashlib.sha256(json.dumps(
        frozen_criteria, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()

    preflight_dir = _preflight_directory(store, VV3D_R2_WORKTREE_ID, preflight_id)
    preflight_path = preflight_dir / "preflight.json"
    try:
        preflight_raw = preflight_path.read_bytes()
        preflight = _read_strict_json(preflight_path)
        checksum = _read_strict_json(preflight_dir / "preflight.sha256.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PolicyError(f"VV3D R2 collect-only receipt is unavailable: {exc}") from exc
    preflight_sha = hashlib.sha256(preflight_raw).hexdigest()
    expected_origin = str((execution_root / "src" / "solveur" / "__init__.py").resolve())
    collection = preflight.get("collection_report")
    stdout_path, stderr_path = preflight_dir / "output" / "stdout.log", preflight_dir / "output" / "stderr.log"
    output_hashes_valid = (
        stdout_path.is_file() and stderr_path.is_file()
        and preflight.get("stdout_sha256") == _sha256(stdout_path)
        and preflight.get("stderr_sha256") == _sha256(stderr_path)
    )
    if (checksum.get("sha256") != preflight_sha or preflight.get("status") != "PREFLIGHT_PASS"
            or preflight.get("campaign_id") != VV3D_R2_CAMPAIGN_ID
            or preflight.get("worktree_id") != VV3D_R2_WORKTREE_ID
            or preflight.get("preflight_id") != preflight_id
            or preflight.get("target") != target or preflight.get("nodeid") != target
            or preflight.get("identity") != dict(identity)
            or preflight.get("source_fingerprint") != source_fingerprint
            or preflight.get("controller_provenance") != dict(controller_provenance)
            or preflight.get("solver_origin_expected") != expected_origin
            or preflight.get("solver_origin_observed") != expected_origin
            or preflight.get("r1_predecessor_sha256") != predecessor["sha256"]
            or not output_hashes_valid
            or not isinstance(collection, Mapping)
            or collection.get("schema") != "qfsolver-wp12-vv3d-collection-v1"
            or collection.get("scope_id") != VV3D_R2_WORKTREE_ID
            or collection.get("target") != target
            or collection.get("collected_nodeids") != [target]
            or collection.get("skip_markers") != []
            or collection.get("bodies_executed") is not False
            or collection.get("exitstatus") != 0
            or preflight.get("selected_nodeids") != [target] or preflight.get("skipped") != 0
            or preflight.get("bodies_executed") is not False
            or preflight.get("attempt_reserved") is not False
            or preflight.get("reservation_created") is not False
            or preflight.get("ledger_sha256_before") != preflight.get("ledger_sha256_after")):
        raise PolicyError("VV3D R2 preflight does not bind this exact source, controller and nodeid")

    expected = {
        "schema": "qf-wp12-vv3d-case-manifest-v1", "campaign_id": VV3D_R2_CAMPAIGN_ID,
        "scope_id": VV3D_R2_WORKTREE_ID, "case_id": case_id, "nodeid": target,
        "state": "OWNER_AUTHORIZED", "execution_authorized": True, "do_not_execute": False,
        "mesh_sha256": case["mesh_sha256"], "selected_dofs": case["selected_dofs"],
        "timeout_seconds": case["timeout_seconds"], "rss_soft_limit_mib": 4096,
        "archive_size_limit_mib": 256, "max_attempts": 1,
        "scientific_fingerprint": source_fingerprint, "controller_fingerprint": current_controller,
        "campaign_contract_sha256": contract_sha, "criteria_sha256": criteria_sha,
        "frozen_criteria": frozen_criteria,
        "owner_decision": {
            "status": "APPROVED", "approved_by": "Owner", "decision_id": decision["decision_id"],
            "decision_sha256": decision_sha,
        },
        "preflight": {"preflight_id": preflight_id, "nodeid": target, "status": "PREFLIGHT_PASS",
                       "receipt_sha256": preflight_sha, "receipt_path": str(preflight_path.resolve())},
    }
    if not isinstance(manifest, Mapping) or any(manifest.get(key) != value for key, value in expected.items()):
        raise PolicyError("VV3D R2 case manifest does not bind the exact Owner decision, criteria, source and budget")
    authorization_id = manifest.get("authorization_id")
    if not isinstance(authorization_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", authorization_id):
        raise PolicyError("VV3D R2 case manifest authorization_id is invalid")
    return (dict(manifest), dict(preflight), hashlib.sha256(manifest_raw).hexdigest(), preflight_sha,
            str(decision["decision_id"]), decision_sha)


def _vv3d_adaptive_fem_launch_bindings(
    *, target: str, preflight_id: str, manifest_path: Path, entry: Mapping[str, Any],
    execution_root: Path, identity: Mapping[str, Any], source_fingerprint: str,
    controller_provenance: Mapping[str, Any], store: Path,
) -> tuple[dict[str, Any], dict[str, Any], str, str, str, str]:
    """Validate H1/QLOAD authorization against exact seed sidecars before reservation."""
    import importlib
    import sys
    vv3d_contract = _load_vv3d_contract_module()

    candidate, bindings = _vv3d_adaptive_candidate_metadata(execution_root, target)
    if candidate.get("execution_kind") != "FEM" or candidate.get("kind") not in {
        "uniform_h_refinement", "body_load_quadrature_escalation",
    }:
        raise PolicyError("adaptive FEM route accepts only the closed H1/QLOAD catalog")
    candidate_id = str(candidate["candidate_id"])
    auth_root = (store / "authorizations" / VV3D_WORKTREE_ID).resolve(strict=True)
    manifest_path = manifest_path.resolve(strict=True)
    manifest_raw = manifest_path.read_bytes()
    manifest = _read_strict_json(manifest_path)
    contract_path = auth_root / "campaign-contract.json"
    decision_path = auth_root / "campaign-decision.json"
    contract_raw, decision_raw = contract_path.read_bytes(), decision_path.read_bytes()
    contract, decision = _read_strict_json(contract_path), _read_strict_json(decision_path)
    controller_fingerprint = _stable_fingerprint(controller_provenance)
    try:
        vv3d_contract.validate_contract(
            contract, registered_nodeids=set(VV3D_ALL_NODEIDS),
            controller_fingerprint=controller_fingerprint, scientific_fingerprint=source_fingerprint,
        )
        vv3d_contract.validate_decision(contract, decision, contract_bytes=contract_raw)
        vv3d_contract.validate_decision_scope(decision, candidate_id)
        vv3d_contract.verify_artifact_bindings(
            contract, roots={kind: execution_root / "experiments" / "wp12_vv3d_adaptive"
                             for kind in ("mesh", "manifest", "oracle", "criteria")},
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise PolicyError(f"adaptive campaign contract/Owner decision is invalid: {exc}") from exc
    case = next((item for item in contract["cases"] if item.get("case_id") == candidate_id), None)
    catalog_binding = contract["adaptive_catalog"]["candidates"].get(candidate_id)
    if (case is None or case.get("phase") != "ADAPTIVE" or case.get("nodeid") != target
            or not isinstance(case.get("trigger"), Mapping)
            or case["trigger"].get("source_case_id") != candidate.get("seed_case")
            or not isinstance(catalog_binding, Mapping)
            or any(catalog_binding.get(key) != bindings.get(key) for key in
                   ("candidate_sha256", "mesh_sha256", "criteria_sha256", "rule_sha256"))):
        raise PolicyError("adaptive candidate does not match exact approved contract and catalog bindings")
    evidence_root = Path(str(entry["evidence_root"])).resolve(strict=True)
    try:
        manifest_path.relative_to(evidence_root)
    except ValueError as exc:
        raise PolicyError("adaptive manifest must be inside the assigned evidence root") from exc
    if manifest.get("schema") != "qf-wp12-vv3d-adaptive-execution-manifest-v1":
        raise PolicyError("adaptive manifest schema is not the science harness contract")
    campaign_decision = {
        "status": "APPROVED", "decision_id": decision["decision_id"],
        "decision_sha256": hashlib.sha256(decision_raw).hexdigest(),
        "catalog_sha256": bindings["catalog_sha256"],
    }
    transition = manifest.get("transition_decision")
    eligibility_ref = manifest.get("eligibility_record")
    if (not isinstance(transition, Mapping) or transition.get("status") != "APPROVED"
            or transition.get("source_case_id") != candidate["seed_case"]
            or transition.get("candidate_id") != candidate_id
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", str(transition.get("decision_id", "")))
            or not re.fullmatch(r"[0-9a-f]{64}", str(transition.get("decision_sha256", "")))
            or not isinstance(eligibility_ref, Mapping)
            or set(eligibility_ref) != {"path", "sha256"}
            or not re.fullmatch(r"[0-9a-f]{64}", str(eligibility_ref.get("sha256", "")))
            or transition.get("eligibility_sha256") != eligibility_ref.get("sha256")):
        raise PolicyError("adaptive manifest lacks an exact approved transition and eligibility binding")
    eligibility_path = (evidence_root / str(eligibility_ref["path"])).resolve(strict=True)
    try:
        eligibility_path.relative_to(evidence_root)
    except ValueError as exc:
        raise PolicyError("adaptive eligibility receipt escapes the evidence root") from exc
    eligibility_raw = eligibility_path.read_bytes()
    if hashlib.sha256(eligibility_raw).hexdigest() != eligibility_ref["sha256"]:
        raise PolicyError("adaptive eligibility receipt raw-byte SHA-256 mismatch")
    eligibility_record = _read_strict_json(eligibility_path)
    if eligibility_record.get("schema") != "qf-wp12-vv3d-adaptive-eligibility-v1" or eligibility_record.get(
            "candidate_id") != candidate_id:
        raise PolicyError("adaptive eligibility receipt identity mismatch")

    # Reconstruct eligibility input only from immutable completed seed records
    # and their hashed sidecars; a manifest cannot supply synthetic observations.
    source = _vv3d_adaptive_source_from_completed_runs(
        candidate=candidate, store=store, evidence_root=evidence_root, execution_root=execution_root,
        ledger_path=store / str(entry["node_attempt_ledger"]["path"]),
        campaign_id=VV3D_CAMPAIGN_ID, source_fingerprint=source_fingerprint,
        controller_fingerprint=controller_fingerprint,
    )
    if eligibility_record.get("source") != source:
        raise PolicyError("adaptive eligibility input differs from completed seed sidecars")
    sys.path.insert(0, str(execution_root))
    try:
        science_harness = importlib.import_module("experiments.wp12_vv3d_adaptive.case_harness")
        evaluated = science_harness.evaluate_adaptive_eligibility(candidate_id, source)
    except (ImportError, ValueError, KeyError, TypeError) as exc:
        raise PolicyError(f"science eligibility evaluator could not validate the exact seed data: {exc}") from exc
    finally:
        try:
            sys.path.remove(str(execution_root))
        except ValueError:
            pass
    if evaluated.get("status") != "ELIGIBLE" or eligibility_record.get("result") != evaluated:
        raise PolicyError("adaptive transition is not eligible under the frozen science evaluator")
    expected_transition = {
        "status": "APPROVED", "decision_id": campaign_decision["decision_id"],
        "decision_sha256": campaign_decision["decision_sha256"],
        "source_case_id": candidate["seed_case"], "candidate_id": candidate_id,
        "eligibility_sha256": eligibility_ref["sha256"],
    }
    if dict(transition) != expected_transition:
        raise PolicyError("adaptive transition is not the exact campaign-approved trigger binding")

    criteria_path = (execution_root / "experiments" / "wp12_vv3d_adaptive" /
                     candidate["criteria_path"]).resolve(strict=True)
    criteria_doc = _read_strict_json(criteria_path)
    frozen_criteria = criteria_doc.get("criteria")
    frozen_sha = hashlib.sha256(json.dumps(
        frozen_criteria, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    preflight_path = (_preflight_directory(store, VV3D_WORKTREE_ID, preflight_id) / "preflight.json").resolve(strict=True)
    preflight_raw = preflight_path.read_bytes()
    preflight = _read_strict_json(preflight_path)
    preflight_sha = hashlib.sha256(preflight_raw).hexdigest()
    if (preflight.get("nodeid") != target or preflight.get("preflight_id") != preflight_id
            or preflight.get("status") != "PREFLIGHT_PASS" or preflight.get("bodies_executed") is not False
            or preflight.get("attempt_reserved") is not False or preflight.get("selected_nodeids") != [target]
            or preflight.get("skipped") != 0 or preflight.get("identity") != dict(identity)
            or preflight.get("source_fingerprint") != source_fingerprint
            or preflight.get("controller_provenance") != dict(controller_provenance)
            or manifest.get("preflight_receipt_sha256") != preflight_sha):
        raise PolicyError("adaptive preflight does not bind the exact node/source/controller")
    expected = {
        "campaign_id": VV3D_CAMPAIGN_ID, "candidate_id": candidate_id, "nodeid": target,
        "execution_kind": "FEM", "seed_case": candidate["seed_case"],
        **bindings, "authorization_id": manifest.get("authorization_id"),
        "scientific_fingerprint": source_fingerprint, "controller_fingerprint": controller_fingerprint,
        "campaign_decision": campaign_decision, "transition_decision": dict(transition),
        "execution_authorized": True, "do_not_execute": False,
        "frozen_criteria": frozen_criteria, "frozen_criteria_sha256": frozen_sha,
        "preflight_receipt_sha256": preflight_sha, "evidence_root": str(evidence_root),
        "attempt_id": manifest.get("attempt_id"), "reservation_id": manifest.get("reservation_id"),
        "selected_dofs": candidate["prepared_mesh"]["selected_dofs"],
        "timeout_seconds": candidate["numerical_conditions"]["timeout_seconds_max"],
        "attempt_number": 1, "max_attempts": 1,
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise PolicyError("adaptive manifest differs from exact candidate, criteria, provenance or budget")
    for name in ("authorization_id", "attempt_id", "reservation_id"):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", str(manifest.get(name, ""))):
            raise PolicyError(f"adaptive manifest {name} is invalid")
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    contract_sha = hashlib.sha256(contract_raw).hexdigest()
    decision_sha = campaign_decision["decision_sha256"]
    receipt_fields = {
        "schema": "qf-wp12-vv3d-adaptive-runner-receipt-v1", "status": "RESERVED",
        "campaign_id": VV3D_CAMPAIGN_ID, "candidate_id": candidate_id, "nodeid": target,
        "execution_kind": "FEM", "seed_case": candidate["seed_case"], **bindings,
        "manifest_sha256": manifest_sha, "manifest_path": str(manifest_path),
        "authorization_id": manifest["authorization_id"],
        "scientific_fingerprint": source_fingerprint, "controller_fingerprint": controller_fingerprint,
        "preflight_receipt_sha256": preflight_sha, "campaign_decision": campaign_decision,
        "transition_decision": dict(transition),
        "eligibility_record": {"path": str(eligibility_path), "sha256": eligibility_ref["sha256"]},
        "eligibility": {"status": "ELIGIBLE", "sha256": eligibility_ref["sha256"]},
        "allowed_evidence_roots": [str(evidence_root), str(auth_root)], "evidence_root": str(evidence_root),
        "frozen_criteria": frozen_criteria,
        "attempt_id": manifest["attempt_id"], "reservation_id": manifest["reservation_id"],
        "selected_dofs": expected["selected_dofs"], "timeout_seconds": expected["timeout_seconds"],
        "attempt_number": 1, "max_attempts": 1, "attempt_reserved": True,
        "postprocessing_reserved": False,
    }
    result_manifest = dict(manifest)
    result_manifest.update({"case_id": candidate_id, "mesh_sha256": bindings["mesh_sha256"],
                            "rss_soft_limit_mib": 4096, "archive_size_limit_mib": 256,
                            "campaign_contract_sha256": contract_sha,
                            "_validated_transition_binding": {
                                "transition_receipt_sha256": eligibility_ref["sha256"],
                                "transition_source_case_id": candidate["seed_case"],
                                "transition_destination_case_id": candidate_id,
                            }, "_runner_receipt_fields": receipt_fields})
    return (result_manifest, dict(preflight), manifest_sha, preflight_sha,
            str(decision["decision_id"]), decision_sha)


def _vv3d_adaptive_source_from_completed_runs(
    *, candidate: Mapping[str, Any], store: Path, evidence_root: Path, execution_root: Path,
    ledger_path: Path,
    campaign_id: str, source_fingerprint: str, controller_fingerprint: str,
) -> dict[str, Any]:
    """Read source observations from completed PASS run receipts and their immutable sidecars."""
    case_ids = ([f"VV3D-{candidate['family']}-L{level}" for level in (1, 2, 3)]
                if candidate["kind"] == "uniform_h_refinement" else [str(candidate["seed_case"])])
    try:
        from wp12_vv3d_ledger import BudgetLedger
    except ModuleNotFoundError:
        from scripts.wp12_vv3d_ledger import BudgetLedger
    ledger_records = BudgetLedger(ledger_path, allowed_root=store).verify()
    source_records: dict[str, tuple[Path, Mapping[str, Any], Mapping[str, Any]]] = {}
    for case_id in case_ids:
        matches = []
        for path in store.rglob("run.json") if store.exists() else ():
            try:
                run = _read_strict_json(path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if run.get("campaign_id") == campaign_id and run.get("case_id") == case_id and run.get("state") == "PASS":
                matches.append((path, run))
        if len(matches) != 1:
            raise PolicyError(f"adaptive source requires exactly one PASS record for {case_id}")
        run_path, run = matches[0]
        attempt_start = next((item for item in ledger_records if item.get("event") == "ATTEMPT_STARTED"
                              and item.get("case_id") == case_id
                              and item.get("attempt_id") == run.get("attempt_id")), None)
        attempt_finish = next((item for item in ledger_records if item.get("event") == "ATTEMPT_FINISHED"
                               and attempt_start is not None
                               and item.get("run_id") == attempt_start.get("run_id")), None)
        if (attempt_start is None or attempt_finish is None or attempt_finish.get("status") != "PASS"
                or attempt_start.get("manifest_sha256") != run.get("manifest", {}).get("sha256")
                or run.get("source_fingerprint") != source_fingerprint
                or run.get("controller_fingerprint") != controller_fingerprint):
            raise PolicyError(f"adaptive source ledger does not record the exact PASS attempt for {case_id}")
        sidecar_ref = run.get("observables_sidecar")
        if not isinstance(sidecar_ref, Mapping) or set(sidecar_ref) != {"path", "sha256"}:
            raise PolicyError(f"adaptive source {case_id} has no immutable sidecar binding")
        sidecar_path = Path(str(sidecar_ref["path"])).resolve(strict=True)
        try:
            sidecar_path.relative_to(evidence_root)
        except ValueError as exc:
            raise PolicyError("adaptive source sidecar escapes the evidence root") from exc
        raw = sidecar_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sidecar_ref["sha256"]:
            raise PolicyError(f"adaptive source sidecar hash mismatch for {case_id}")
        sidecar = _read_strict_json(sidecar_path)
        if (sidecar.get("campaign_id") != campaign_id or sidecar.get("case_id") != case_id
                or sidecar.get("attempt_id") != run.get("attempt_id")
                or sidecar.get("mesh_sha256") != run.get("mesh_sha256")
                or sidecar.get("manifest_sha256") != run.get("manifest", {}).get("sha256")
                or sidecar.get("scientific_fingerprint") != run.get("source_fingerprint")
                or sidecar.get("controller_fingerprint") != run.get("controller_fingerprint")
                or sidecar.get("scientific_fingerprint") != source_fingerprint
                or sidecar.get("controller_fingerprint") != controller_fingerprint
                or sidecar.get("execution", {}).get("status") != "COMPLETED_UNASSESSED"):
            raise PolicyError(f"adaptive source sidecar identity differs from PASS run {case_id}")
        if not _vv3d_seed_passes_required_gates(
                run, require_campaign_pass=(candidate["kind"] == "body_load_quadrature_escalation"
                                             or case_id.endswith("-L3"))):
            raise PolicyError(f"adaptive source is not a consistent verified PASS for {case_id}")
        source_records[case_id] = (run_path, run, sidecar)
    if candidate["kind"] == "uniform_h_refinement":
        matrix_path = execution_root / "experiments" / "wp12_vv3d_adaptive" / "prepared_20261029" / "MATRIX_NOT_AUTHORIZED.json"
        matrix = _read_strict_json(matrix_path)
        matrix_cases = {item.get("case_id"): item for item in matrix.get("cases", []) if isinstance(item, Mapping)}
        l3_run = source_records[f"VV3D-{candidate['family']}-L3"][1]
        assessment_ref = l3_run.get("campaign_assessment")
        if (l3_run.get("campaign_gate_status") != "PASS"
                or not isinstance(assessment_ref, Mapping)
                or not isinstance(assessment_ref.get("path"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", str(assessment_ref.get("sha256", "")))):
            raise PolicyError("H1 requires a complete passing campaign-gate assessment archived by the runner")
        assessment_path = Path(assessment_ref["path"]).resolve(strict=True)
        try:
            assessment_path.relative_to(evidence_root.resolve(strict=True))
        except ValueError as exc:
            raise PolicyError("H1 campaign assessment escapes the assigned evidence root") from exc
        assessment_raw = assessment_path.read_bytes()
        if hashlib.sha256(assessment_raw).hexdigest() != assessment_ref["sha256"]:
            raise PolicyError("H1 campaign assessment SHA-256 mismatch")
        assessment_record = _read_strict_json(assessment_path)
        if (assessment_record.get("schema") != "qf-wp12-vv3d-campaign-assessment-record-v1"
                or assessment_record.get("campaign_id") != campaign_id
                or assessment_record.get("family") != candidate["family"]
                or assessment_record.get("assessment", {}).get("status") != "PASS"
                or assessment_record.get("scientific_fingerprint") != source_fingerprint
                or assessment_record.get("controller_fingerprint") != controller_fingerprint):
            raise PolicyError("H1 campaign assessment record does not bind the exact passing family and identities")
        return {"seed_cases": {
            case_id: {
                "case_id": case_id, "state": run.get("state"),
                "provenance_state": run.get("provenance_state"), "sidecar_valid": True,
                "sidecar_sha256": run.get("observables_sidecar", {}).get("sha256"),
                "manifest_sha256": run.get("manifest", {}).get("sha256"),
                "mesh_sha256": run.get("mesh_sha256"),
                "scientific_fingerprint": run.get("source_fingerprint"),
                "controller_fingerprint": run.get("controller_fingerprint"),
                "h_m": 1.0 / matrix_cases[case_id]["divisions"][0],
                "observables": sidecar.get("observables"), "criteria": sidecar.get("criteria"),
            }
            for case_id, (_path, run, sidecar) in source_records.items()
        }}
    _path, _run, sidecar = source_records[str(candidate["seed_case"])]
    load = sidecar.get("observables", {}).get("load_quadrature_8_12")
    if not isinstance(load, Mapping):
        raise PolicyError("QLOAD seed sidecar lacks the frozen order-8/order-12 observation")
    return {"load_quadrature_8_12": load}


def _vv3d_adaptive_candidate_metadata(execution_root: Path, target: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recompute the science harness's closed adaptive catalog bindings without importing it."""
    experiment_root = (execution_root / "experiments" / "wp12_vv3d_adaptive").resolve(strict=True)
    catalog_path = experiment_root / "ADAPTIVE_CATALOG_DRAFT.json"
    try:
        catalog_raw = catalog_path.read_bytes()
        catalog = _read_strict_json(catalog_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PolicyError(f"VV3D adaptive catalog is unavailable or invalid: {exc}") from exc
    candidates = catalog.get("candidates") if isinstance(catalog, Mapping) else None
    expected_ids = {f"VV3D-ADAPT-{family}-{kind}" for family in ("TET4", "TET10", "HEX8", "HEX20")
                    for kind in ("H1", "QLOAD", "QPOST")}
    if (catalog.get("campaign_id") != VV3D_CAMPAIGN_ID or not isinstance(candidates, list)
            or {item.get("candidate_id") for item in candidates if isinstance(item, Mapping)} != expected_ids
            or len(candidates) != 12):
        raise PolicyError("VV3D adaptive catalog differs from the exact twelve-candidate catalog")
    candidate_id = next((cid for cid in expected_ids if any(
        isinstance(item, Mapping) and item.get("candidate_id") == cid and item.get("nodeid") == target
        for item in candidates)), None)
    candidate = next((item for item in candidates if item.get("candidate_id") == candidate_id), None)
    if candidate is None or candidate.get("status") != "PREPARED_NOT_AUTHORIZED":
        raise PolicyError("VV3D adaptive candidate is absent or not in its frozen preparation state")
    expected_nodeid = (
        f"tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_archived_postprocess_case[{candidate['family']}]"
        if candidate.get("execution_kind") == "POSTPROCESS_ONLY"
        else f"tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_adaptive_fem_case[{candidate_id}]"
    )
    if candidate.get("nodeid") != expected_nodeid:
        raise PolicyError("VV3D adaptive nodeid differs from its exact parametrized identity")
    prepared = candidate.get("prepared_mesh")
    if not isinstance(prepared, Mapping):
        raise PolicyError("VV3D adaptive candidate has no mesh binding")
    mesh_path = (experiment_root / str(prepared.get("path", ""))).resolve(strict=True)
    try:
        mesh_path.relative_to(experiment_root)
    except ValueError as exc:
        raise PolicyError("VV3D adaptive mesh path escapes its source root") from exc
    mesh_sha = _sha256(mesh_path)
    criteria_path = (experiment_root / str(candidate.get("criteria_path", ""))).resolve(strict=True)
    try:
        criteria_path.relative_to(experiment_root)
    except ValueError as exc:
        raise PolicyError("VV3D adaptive criteria path escapes its source root") from exc
    criteria_sha = _sha256(criteria_path)
    if mesh_sha != prepared.get("sha256") or criteria_sha != candidate.get("criteria_sha256_provisional"):
        raise PolicyError("VV3D adaptive catalog mesh or criteria raw-byte fingerprint mismatch")
    source_hashes = {}
    for relative in VV3D_ADAPTIVE_SOURCE_FILES:
        path = (execution_root / relative).resolve(strict=True)
        try:
            path.relative_to(execution_root.resolve())
        except ValueError as exc:
            raise PolicyError("VV3D adaptive source inventory path escapes the science checkout") from exc
        source_hashes[relative] = _sha256(path)
    rule_identity = {
        "execution_kind": candidate["execution_kind"], "kind": candidate["kind"],
        "mesh_rule": candidate["mesh_rule"], "numerical_conditions": candidate["numerical_conditions"],
        "criteria_sha256": criteria_sha,
        "quadrature_source_sha256": source_hashes["experiments/wp12_vv3d_adaptive/quadrature.py"],
        "field_error_source_sha256": source_hashes["experiments/wp12_vv3d_adaptive/field_error_draft.py"],
    }
    rule_raw = json.dumps(rule_identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    bindings = {
        "catalog_sha256": hashlib.sha256(catalog_raw).hexdigest(),
        "candidate_sha256": hashlib.sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":"),
                                             allow_nan=False).encode()).hexdigest(),
        "mesh_sha256": mesh_sha, "criteria_sha256": criteria_sha,
        "rule_sha256": hashlib.sha256(rule_raw).hexdigest(), "source_hashes": source_hashes,
    }
    return dict(candidate), bindings


def _write_vv3d_state_archive(
    *, evidence_root: Path, case_id: str, attempt_id: str, mesh_sha256: str,
    manifest_sha256: str, scientific_fingerprint: str, controller_fingerprint: str,
) -> dict[str, str] | None:
    """Create a QPOST input archive from a completed initial-case sidecar, once.

    This is post-run bookkeeping only. Missing displacement evidence is kept as
    missing and never synthesized from an incomplete or failed run.
    """
    if (not isinstance(case_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", case_id) is None
            or not isinstance(attempt_id, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", attempt_id) is None):
        raise PolicyError("VV3D archive case/attempt identity is invalid")
    sidecar_path = evidence_root.resolve(strict=True) / case_id / attempt_id / "observables.json"
    sidecar = _read_strict_json(sidecar_path)
    if (not isinstance(sidecar, Mapping) or sidecar.get("schema") != "qf-wp12-vv3d-observables-v1"
            or sidecar.get("campaign_id") != VV3D_CAMPAIGN_ID or sidecar.get("case_id") != case_id
            or sidecar.get("attempt_id") != attempt_id or sidecar.get("mesh_sha256") != mesh_sha256
            or sidecar.get("manifest_sha256") != manifest_sha256
            or sidecar.get("scientific_fingerprint") != scientific_fingerprint
            or sidecar.get("controller_fingerprint") != controller_fingerprint
            or not isinstance(sidecar.get("execution"), Mapping)
            or sidecar["execution"].get("status") != "COMPLETED_UNASSESSED"):
        raise PolicyError("VV3D source sidecar does not represent the exact completed authorized case")
    displacement = sidecar.get("observables", {}).get("nodal_displacements_m", {})
    values = displacement.get("value") if isinstance(displacement, Mapping) else None
    if (not isinstance(values, list) or not values or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in values)):
        raise PolicyError("VV3D QPOST source sidecar has no complete finite nodal displacement vector")
    archive = {
        "schema": "qf-wp12-vv3d-state-archive-v1", "campaign_id": VV3D_CAMPAIGN_ID,
        "case_id": case_id, "mesh_sha256": mesh_sha256,
        "case_state": "OWNER_AUTHORIZED_EXECUTION", "execution_status": "COMPLETED_UNASSESSED",
        "manifest_sha256": manifest_sha256, "attempt_id": attempt_id,
        "nodal_displacements_m": values,
    }
    raw = (json.dumps(archive, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    target = sidecar_path.parent / "state-archive.json"
    try:
        with target.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise PolicyError("VV3D source state archive already exists; refusing overwrite") from exc
    return {"path": str(target.resolve()), "sha256": hashlib.sha256(raw).hexdigest()}


def _is_symlink_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    junction_check = getattr(path, "is_junction", None)
    return bool(junction_check()) if callable(junction_check) else False


def _create_campaign_directory(root: Path, target: Path) -> None:
    """Create a new campaign directory without traversing a symlink ancestor."""
    root.mkdir(parents=True, exist_ok=True)
    if _is_symlink_or_junction(root):
        raise PolicyError("VV3D campaign root must not be a symlink or junction")
    root_abs = root.resolve(strict=True)
    target_abs = target.absolute()
    try:
        relative = target_abs.relative_to(root.absolute())
    except ValueError as exc:
        raise PolicyError("VV3D run directory is outside its campaign store") from exc
    current = root_abs
    for part in relative.parts:
        current = current / part
        if _is_symlink_or_junction(current):
            raise PolicyError("VV3D run path contains a symlink or junction component")
        if current.exists():
            if not current.is_dir():
                raise PolicyError("VV3D run path component is not a directory")
        else:
            current.mkdir()


def _vv3d_qpost_launch_bindings(
    *, target: str, preflight_id: str, manifest_path: Path, entry: Mapping[str, Any],
    execution_root: Path, identity: Mapping[str, Any], source_fingerprint: str,
    controller_provenance: Mapping[str, Any], store: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate QPOST's launch preconditions and freeze its source/archive proof.

    QPOST launch eligibility is source PASS + exact immutable displacement archive
    + unused catalog slot. Its 1e-4 quadrature sensitivity is an output criterion,
    never a precondition to computing that output.
    """
    try:
        from wp12_vv3d_ledger import BudgetLedger
    except ModuleNotFoundError:  # imported as scripts.development_autonomous by tests
        from scripts.wp12_vv3d_ledger import BudgetLedger

    candidate, bindings = _vv3d_adaptive_candidate_metadata(execution_root, target)
    if candidate.get("execution_kind") != "POSTPROCESS_ONLY":
        raise PolicyError("QPOST launch binding requires a catalogued POSTPROCESS_ONLY candidate")
    candidate_id = str(candidate["candidate_id"])
    campaign_id = VV3D_CAMPAIGN_ID
    controller_fingerprint = _stable_fingerprint(controller_provenance)
    try:
        evidence_root = Path(str(entry.get("evidence_root", ""))).resolve(strict=True)
        auth_root = (store / "authorizations" / VV3D_WORKTREE_ID).resolve(strict=True)
    except OSError as exc:
        raise PolicyError("VV3D QPOST evidence and authorization roots must already exist") from exc
    if not evidence_root.is_dir() or not auth_root.is_dir():
        raise PolicyError("VV3D QPOST evidence and authorization roots must be directories")
    manifest_path = manifest_path.resolve(strict=True)
    try:
        manifest_path.relative_to(auth_root)
    except ValueError as exc:
        raise PolicyError("VV3D QPOST manifest must be inside its campaign authorization root") from exc
    manifest_raw = manifest_path.read_bytes()
    manifest = _read_strict_json(manifest_path)
    contract_path = auth_root / "campaign-contract.json"
    decision_path = auth_root / "campaign-decision.json"
    contract_raw = contract_path.read_bytes()
    decision_raw = decision_path.read_bytes()
    contract = _read_strict_json(contract_path)
    decision = _read_strict_json(decision_path)
    try:
        vv3d_contract = _load_vv3d_contract_module()
        vv3d_contract.validate_contract(
            contract, registered_nodeids=set(VV3D_ALL_NODEIDS),
            controller_fingerprint=_stable_fingerprint(controller_provenance),
            scientific_fingerprint=source_fingerprint,
        )
        vv3d_contract.validate_decision(contract, decision, contract_bytes=contract_raw)
        vv3d_contract.validate_decision_scope(decision, candidate_id)
        vv3d_contract.verify_artifact_bindings(
            contract, roots={kind: execution_root / "experiments" / "wp12_vv3d_adaptive"
                             for kind in ("mesh", "manifest", "oracle", "criteria")},
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise PolicyError(f"VV3D QPOST campaign contract or Owner decision is invalid: {exc}") from exc
    job = next((item for item in contract.get("qpost_jobs", []) if item.get("job_id") == candidate_id), None)
    if job is None or job.get("nodeid") != target:
        raise PolicyError("VV3D QPOST job/nodeid is not present in the exact approved campaign contract")
    expected_base = {
        "campaign_id": campaign_id, "candidate_id": candidate_id, "nodeid": target,
        "execution_kind": "POSTPROCESS_ONLY", "seed_case": candidate["seed_case"],
        "catalog_sha256": bindings["catalog_sha256"], "candidate_sha256": bindings["candidate_sha256"],
        "mesh_sha256": bindings["mesh_sha256"], "criteria_sha256": bindings["criteria_sha256"],
        "rule_sha256": bindings["rule_sha256"], "source_hashes": bindings["source_hashes"],
    }
    if (manifest.get("schema") != "qf-wp12-vv3d-adaptive-execution-manifest-v1"
            or manifest.get("execution_authorized") is not True or manifest.get("do_not_execute") is not False
            or any(manifest.get(key) != value for key, value in expected_base.items())
            or manifest.get("scientific_fingerprint") != source_fingerprint
            or manifest.get("controller_fingerprint") != _stable_fingerprint(controller_provenance)):
        raise PolicyError("VV3D QPOST execution manifest does not bind the exact catalog and source identities")
    decision_ref = manifest.get("campaign_decision")
    expected_decision = {
        "status": "APPROVED", "decision_id": decision.get("decision_id"),
        "decision_sha256": hashlib.sha256(decision_raw).hexdigest(),
        "catalog_sha256": bindings["catalog_sha256"],
    }
    if decision_ref != expected_decision:
        raise PolicyError("VV3D QPOST manifest does not bind the exact campaign Owner decision/catalog")

    # Confirm the exact seed has one completed PASS record and that the append-only
    # campaign ledger agrees before reading its state archive.
    case_id = str(candidate["seed_case"])
    records = []
    for path in store.rglob("run.json") if store.exists() else ():
        try:
            value = _read_strict_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if value.get("case_id") == case_id and value.get("state") != "RUNNING":
            records.append((path, value))
    if len(records) != 1:
        raise PolicyError("VV3D QPOST requires exactly one completed seed result")
    source_run_path, source_run = records[0]
    source_manifest_sha = source_run.get("manifest", {}).get("sha256")
    source_attempt = source_run.get("attempt_id")
    archive_ref = source_run.get("qpost_state_archive")
    if (source_run.get("campaign_id") != campaign_id
            or not _vv3d_seed_passes_required_gates(source_run, require_campaign_pass=True)
            or source_run.get("source_fingerprint") != source_fingerprint
            or source_run.get("controller_fingerprint") != controller_fingerprint
            or not isinstance(source_manifest_sha, str) or not isinstance(source_attempt, str)
            or not isinstance(archive_ref, Mapping) or not isinstance(archive_ref.get("path"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", str(archive_ref.get("sha256", "")))):
        raise PolicyError("VV3D QPOST requires a verified PASS seed and its immutable state archive")
    ledger_path = store / str(entry["node_attempt_ledger"]["path"])
    ledger = BudgetLedger(ledger_path, allowed_root=store)
    ledger_records = list(ledger.verify())
    source_starts = [r for r in ledger_records if r.get("event") == "ATTEMPT_STARTED" and r.get("case_id") == case_id]
    if (len(source_starts) != 1 or source_starts[0].get("manifest_sha256") != source_manifest_sha
            or any(r.get("event") == "POSTPROCESS_STARTED" and r.get("job_id") == candidate_id
                   for r in ledger_records)):
        raise PolicyError("VV3D QPOST seed ledger provenance or unused job slot is invalid")
    source_finishes = [r for r in ledger_records if r.get("event") == "ATTEMPT_FINISHED"
                       and r.get("run_id") == source_starts[0].get("run_id")]
    if len(source_finishes) != 1 or source_finishes[0].get("status") != "PASS":
        raise PolicyError("VV3D QPOST ledger does not attest the exact seed PASS")
    archive_path = Path(str(archive_ref["path"])).resolve(strict=True)
    allowed_root = Path(str(entry["evidence_root"])).resolve(strict=True)
    try:
        archive_path.relative_to(allowed_root)
    except ValueError as exc:
        raise PolicyError("VV3D QPOST archive is outside the approved evidence root") from exc
    archive_raw = archive_path.read_bytes()
    archive_sha = hashlib.sha256(archive_raw).hexdigest()
    archive = _read_strict_json(archive_path)
    if (archive_sha != archive_ref["sha256"] or archive.get("schema") != "qf-wp12-vv3d-state-archive-v1"
            or archive.get("campaign_id") != campaign_id or archive.get("case_id") != case_id
            or archive.get("mesh_sha256") != bindings["mesh_sha256"]
            or archive.get("case_state") != "OWNER_AUTHORIZED_EXECUTION"
            or archive.get("execution_status") != "COMPLETED_UNASSESSED"
            or archive.get("manifest_sha256") != source_manifest_sha
            or archive.get("attempt_id") != source_attempt):
        raise PolicyError("VV3D QPOST state archive identity/content is invalid")

    source_hash = hashlib.sha256(source_run_path.read_bytes()).hexdigest()
    transition_ref = manifest.get("transition_decision")
    if (not isinstance(transition_ref, Mapping) or transition_ref.get("status") != "APPROVED"
            or transition_ref.get("source_case_id") != case_id
            or transition_ref.get("candidate_id") != candidate_id):
        raise PolicyError("VV3D QPOST transition decision does not bind this seed and catalogued job")
    source = {
        "campaign_id": campaign_id, "candidate_id": candidate_id,
        "postprocessing_job_id": manifest.get("postprocessing_job_id"), "seed_case": {
            "case_id": case_id, "status": "PASS", "source_run_receipt_sha256": source_hash,
            "manifest_sha256": source_manifest_sha, "attempt_id": source_attempt,
            "mesh_sha256": bindings["mesh_sha256"],
        },
        "archive": {"status": "AVAILABLE", "path": str(archive_path), "sha256": archive_sha,
                    "source_case_id": case_id, "source_mesh_sha256": bindings["mesh_sha256"],
                    "source_manifest_sha256": source_manifest_sha, "source_attempt_id": source_attempt},
        "campaign_decision": {"decision_id": decision.get("decision_id"),
                              "decision_sha256": hashlib.sha256(decision_raw).hexdigest()},
        "transition_decision": {"decision_id": transition_ref.get("decision_id"),
                                "decision_sha256": transition_ref.get("decision_sha256")},
        "postprocessing_slot": {"postprocessing_jobs_used": 0, "postprocessing_jobs_max": 1},
    }
    source_sha = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":"),
                                           allow_nan=False).encode()).hexdigest()
    if transition_ref.get("eligibility_sha256") != source_sha:
        raise PolicyError("VV3D QPOST transition decision does not bind the canonical launch-eligibility source")
    expected_transition = {
        "status": "APPROVED", "decision_id": expected_decision["decision_id"],
        "decision_sha256": expected_decision["decision_sha256"],
        "source_case_id": case_id, "candidate_id": candidate_id,
        "eligibility_sha256": source_sha,
    }
    if dict(transition_ref) != expected_transition:
        raise PolicyError("VV3D QPOST transition is not the exact campaign-approved eligibility binding")
    eligibility_record = {
        "schema": "qf-wp12-vv3d-adaptive-eligibility-v1", "candidate_id": candidate_id,
        "source": source,
        "result": {
            "status": "ELIGIBLE", "trigger": "SEED_PASS_ARCHIVE_BOUND_SLOT_UNUSED",
            "postprocessing_jobs_used": 0,
            "postprocessing_jobs_max": candidate["numerical_conditions"]["postprocessing_jobs_max"],
            "eligibility_source_sha256": source_sha,
            "postprocess_result_trigger_gt": candidate["numerical_conditions"][
                "relative_observable_change_trigger_gt"],
        },
    }
    eligibility_raw = (json.dumps(eligibility_record, sort_keys=True, separators=(",", ":"),
                                  allow_nan=False) + "\n").encode("utf-8")
    eligibility_path = evidence_root / "eligibility" / f"{candidate_id}.json"
    eligibility_path.parent.mkdir(parents=True, exist_ok=True)
    eligibility_sha = hashlib.sha256(eligibility_raw).hexdigest()
    try:
        with eligibility_path.open("xb") as stream:
            stream.write(eligibility_raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if eligibility_path.read_bytes() != eligibility_raw:
            raise PolicyError("VV3D QPOST eligibility record exists with different bytes")
    frozen_criteria = _read_strict_json(
        (execution_root / "experiments" / "wp12_vv3d_adaptive" / candidate["criteria_path"]).resolve(strict=True)
    )["criteria"]
    frozen_sha = hashlib.sha256(json.dumps(frozen_criteria, sort_keys=True, separators=(",", ":"),
                                           allow_nan=False).encode()).hexdigest()
    preflight_path = (_preflight_directory(store, VV3D_WORKTREE_ID, preflight_id) / "preflight.json").resolve(strict=True)
    try:
        preflight_path.relative_to(store.resolve())
    except ValueError as exc:
        raise PolicyError("VV3D QPOST preflight must be within the campaign run store") from exc
    preflight_receipt = _read_strict_json(preflight_path)
    if (hashlib.sha256(preflight_path.read_bytes()).hexdigest() != manifest.get("preflight_receipt_sha256")
            or preflight_receipt.get("preflight_id") != preflight_id
            or preflight_receipt.get("target") != target or preflight_receipt.get("nodeid") != target
            or preflight_receipt.get("status") != "PREFLIGHT_PASS"
            or preflight_receipt.get("bodies_executed") is not False
            or preflight_receipt.get("attempt_reserved") is not False
            or preflight_receipt.get("reservation_created") is not False
            or preflight_receipt.get("selected_nodeids") != [target] or preflight_receipt.get("skipped") != 0
            or preflight_receipt.get("source_fingerprint") != source_fingerprint
            or preflight_receipt.get("identity") != dict(identity)
            or preflight_receipt.get("controller_provenance") != dict(controller_provenance)):
        raise PolicyError("VV3D QPOST preflight receipt provenance is invalid")
    if (not isinstance(manifest.get("authorization_id"), str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", manifest["authorization_id"]) is None
            or manifest.get("frozen_criteria") != frozen_criteria
            or manifest.get("frozen_criteria_sha256") != frozen_sha
            or manifest.get("preflight_receipt_sha256") != hashlib.sha256(preflight_path.read_bytes()).hexdigest()
            or manifest.get("evidence_root") != str(evidence_root)
            or not isinstance(manifest.get("postprocessing_job_id"), str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", manifest["postprocessing_job_id"]) is None):
        raise PolicyError("VV3D QPOST manifest criteria, reservation slot or evidence binding is invalid")
    job_manifest = next((item for item in contract.get("qpost_jobs", [])
                         if item.get("job_id") == candidate_id), None)
    if (job_manifest is None or job_manifest.get("nodeid") != target
            or manifest.get("job_manifest_sha256") != job_manifest.get("manifest_sha256")
            or type(manifest.get("timeout_seconds")) is not int
            or manifest.get("timeout_seconds") != job_manifest.get("timeout_seconds")
            or type(manifest.get("rss_soft_limit_mib")) is not int
            or manifest.get("rss_soft_limit_mib") != job_manifest.get("rss_soft_limit_mib")
            or type(manifest.get("postprocessing_jobs_used_before")) is not int
            or manifest.get("postprocessing_jobs_used_before") != 0
            or type(manifest.get("postprocessing_jobs_used_after")) is not int
            or manifest.get("postprocessing_jobs_used_after") != 1
            or type(manifest.get("postprocessing_jobs_max")) is not int
            or manifest.get("postprocessing_jobs_max") != job_manifest.get("max_jobs")
            or manifest.get("source_run_receipt_sha256") != source_hash):
        raise PolicyError("VV3D QPOST manifest is not bound to the approved QPOST catalog row")
    receipt_fields = {
        "schema": "qf-wp12-vv3d-adaptive-runner-receipt-v1", "status": "POSTPROCESS_RESERVED",
        "candidate_id": candidate_id, "nodeid": target, "execution_kind": "POSTPROCESS_ONLY",
        "seed_case": case_id, "catalog_sha256": bindings["catalog_sha256"],
        "candidate_sha256": bindings["candidate_sha256"], "mesh_sha256": bindings["mesh_sha256"],
        "criteria_sha256": bindings["criteria_sha256"], "rule_sha256": bindings["rule_sha256"],
        "source_hashes": bindings["source_hashes"],
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "manifest_path": str(manifest_path), "authorization_id": manifest["authorization_id"],
        "scientific_fingerprint": source_fingerprint,
        "controller_fingerprint": _stable_fingerprint(controller_provenance),
        "preflight_receipt_sha256": hashlib.sha256(preflight_path.read_bytes()).hexdigest(),
        "campaign_decision": expected_decision,
        "transition_decision": dict(transition_ref),
        "eligibility_record": {"path": str(eligibility_path.resolve()), "sha256": eligibility_sha},
        "eligibility": {"status": "ELIGIBLE", "sha256": eligibility_sha},
        "allowed_evidence_roots": [str(evidence_root), str(auth_root)], "evidence_root": str(evidence_root),
        "archive": {"path": str(archive_path), "sha256": archive_sha,
                    "source_case_id": case_id, "source_mesh_sha256": bindings["mesh_sha256"],
                    "source_manifest_sha256": source_manifest_sha, "source_attempt_id": source_attempt},
        "source_manifest_sha256": source_manifest_sha,
        "postprocessing_reserved": True, "postprocessing_job_id": manifest["postprocessing_job_id"],
        "attempt_reserved": False, "frozen_criteria": frozen_criteria,
        "postprocessing_jobs_used_before": 0, "postprocessing_jobs_used_after": 1,
        "postprocessing_jobs_max": int(candidate["numerical_conditions"]["postprocessing_jobs_max"]),
        "source_run_receipt_sha256": source_hash,
        "eligibility_threshold": candidate["numerical_conditions"]["relative_observable_change_trigger_gt"],
    }
    if manifest.get("campaign_decision") != expected_decision or manifest.get("transition_decision") != dict(transition_ref):
        raise PolicyError("VV3D QPOST manifest decision bindings differ from the verified decisions")
    return dict(manifest), dict(preflight_receipt), receipt_fields


def _load_vv3d_contract_module() -> Any:
    """Load the same source module in script and package-import execution modes."""
    try:
        import wp12_vv3d_contract as vv3d_contract
    except ModuleNotFoundError:  # imported as scripts.development_autonomous by tests/tools
        from scripts import wp12_vv3d_contract as vv3d_contract
    return vv3d_contract


def preflight_pytest(
    worktree_id: str,
    target: str,
    preflight_id: str | None = None,
) -> dict[str, Any]:
    """Collect one exact registered node without reserving a FEM attempt."""
    policy = load_policy()
    if worktree_id in {VV3D_WORKTREE_ID, VV3D_R2_WORKTREE_ID}:
        if target not in policy["worktrees"][worktree_id]["allowed_nodeids"]:
            raise PolicyError("VV3D preflight target is outside the exact closed case catalogue")
        return preflight_wp12_vv3d_pytest(
            target, preflight_id, policy=policy, worktree_id=worktree_id,
        )
    if worktree_id == "rotor":
        return preflight_rotor_pytest(target, preflight_id, policy=policy)
    if worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID:
        return preflight_hex8sri_convergence24_pytest(target, preflight_id, policy=policy)
    if worktree_id == "wp12_dynamics":
        return preflight_wp12_dynamics_pytest(target, preflight_id, policy=policy)
    if worktree_id in {WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID, WP12B_HEX20_R2_WORKTREE_ID}:
        return preflight_wp12b_hex20_diagnostic_pytest(target, preflight_id, policy=policy, worktree_id=worktree_id)
    if worktree_id != "d01":
        raise PolicyError(
            "collect-only preflight is enabled only for D01, rotor, WP12 dynamics, WP12-B HEX20 diagnostic, "
            "and preparation-only HEX8-SRI"
        )
    targets = resolve_targets("fem_exploratory", target, policy, worktree_id=worktree_id)
    entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(worktree_id, target, policy)
    store = _run_root(policy)
    ledger_path, _ledger_lock, mandate_id, predecessor = _node_ledger_context(policy, store, worktree_id)
    if predecessor is None or mandate_id != entry["development_mandate_id"]:
        raise PolicyError("D01 preflight is not bound to its distinct development envelope")
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    inherited = dict(os.environ)
    guard_state = _native_guard_environment(inherited)
    if guard_state["active_markers"]:
        raise PolicyError(
            "D01 preflight refused before collection because explicit no-FEM environment markers are active"
        )
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free)
    minimum_free = int(policy["minimum_free_disk_mib"] * 1024 * 1024)
    if free_bytes < minimum_free:
        raise PolicyError(f"insufficient free disk for D01 preflight: {free_bytes} bytes; requires {minimum_free}")

    preflight_id = preflight_id or f"pf-{uuid.uuid4().hex[:12]}"
    receipt_dir = _preflight_directory(store, worktree_id, preflight_id)
    if receipt_dir.exists():
        raise PolicyError("preflight ID already exists; refusing to overwrite a prior receipt")
    temporary_dir = receipt_dir / "tmp"
    output_dir = receipt_dir / "output"
    temporary_dir.mkdir(parents=True)
    output_dir.mkdir()
    command = build_pytest_command(
        "fem_exploratory",
        targets,
        temporary_dir,
        repository_root=execution_root,
        source_root=source_root,
        controller_root=ROOT,
        allow_native_skip_override=True,
        collect_only=True,
    )
    if "--collect-only" not in command:
        raise PolicyError("D01 readiness preflight must be pytest collect-only")
    environment = build_child_environment(
        temporary_dir,
        base=inherited,
        source_root=source_root,
        d01_source_sha=identity["head"],
    )
    child_guard_state = _validate_native_guard_environment(inherited, environment)
    limits = dict(entry["budgets"])
    limits["minimum_free_disk_mib"] = policy["minimum_free_disk_mib"]
    started = datetime.now(timezone.utc).isoformat()
    record_path = receipt_dir / "preflight.json"
    initial = {
        "schema": "qfsolver-development-d01-preflight-v1",
        "mode": "DEVELOPMENT_AUTONOMOUS",
        "mandate_id": mandate_id,
        "worktree_id": worktree_id,
        "target": target,
        "preflight_id": preflight_id,
        "phase": "PYTEST_COLLECT_ONLY",
        "bodies_executed": False,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "solver_origin_expected": str((source_root / "solveur" / "__init__.py").resolve()),
        "controller_provenance": _controller_provenance(),
        "native_guard_environment": child_guard_state,
        "command": command,
        "budgets": limits,
        "budget_semantics": {
            "wall_timeout": "watchdog-triggered process-tree termination; best-effort OS control",
            "rss": "sampled soft monitor; not a hard memory/commit limit",
            "process_count": "sampled process-tree monitor; not a job-object boundary",
            "captured_output": "application-enforced byte caps on captured stdout/stderr",
            "temporary_and_archive_size": "sampled size monitoring; not an NTFS quota",
        },
        "free_disk_before_bytes": free_bytes,
        "predecessor_ledger": predecessor,
        "predecessor_ledger_sha256_verified": _sha256(store / predecessor["path"]),
    }

    scenario_lock = _exclusive_file_lock(store / "locks" / "fem-exploratory.lock")
    with scenario_lock:
        try:
            result = run_supervised_command(
                command,
                cwd=execution_root,
                environment=environment,
                output_dir=output_dir,
                temporary_dir=temporary_dir,
                limits=limits,
                poll_interval=float(policy["poll_interval_seconds"]),
            )
        except OSError as exc:
            _atomic_json(
                record_path,
                {
                    **initial,
                    "state": "PREFLIGHT_LAUNCH_FAILED",
                    "started_at_utc": started,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    "launch_error": f"{type(exc).__name__}: {exc}",
                },
            )
            raise PolicyError(f"D01 collect-only preflight could not launch: {exc}") from exc

    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
    combined = stdout + "\n" + stderr
    origin_line = f"QF_DEV_SOLVER_ORIGIN={initial['solver_origin_expected']}"
    collected_exact_node = target in combined.splitlines()
    after_entry, _after_root, _after_source, after_identity, after_fingerprint = _registered_worktree(
        worktree_id, target, policy
    )
    if after_identity != identity or after_fingerprint != source_fingerprint or after_entry != entry:
        state = "PREFLIGHT_SOURCE_CHANGED"
    elif result.status != "PASS":
        state = "PREFLIGHT_FAILED"
    elif origin_line not in combined:
        state = "PREFLIGHT_WRONG_SOLVER_ORIGIN"
    elif not collected_exact_node:
        state = "PREFLIGHT_NODEID_NOT_CONFIRMED"
    else:
        state = "PREFLIGHT_PASS"
    final = {
        **initial,
        "state": state,
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "collected_nodeids": [target] if collected_exact_node else [],
        "solver_origin_observed": origin_line if origin_line in combined else None,
        "return_code": result.return_code,
        "elapsed_seconds": result.elapsed_seconds,
        "peak_rss_bytes": result.peak_rss_bytes,
        "peak_process_count": result.peak_process_count,
        "stdout_bytes": result.stdout_bytes,
        "stderr_bytes": result.stderr_bytes,
        "stdout_sha256": _sha256(stdout_path),
        "stderr_sha256": _sha256(stderr_path),
        "archive_bytes": result.archive_bytes,
        "temporary_bytes": result.temporary_bytes,
        "stop_reason": result.stop_reason,
        "identity_after": after_identity,
        "source_fingerprint_after": after_fingerprint,
        "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
    }
    _atomic_json(record_path, final)
    receipt_sha256 = _sha256(record_path)
    _atomic_json(receipt_dir / "preflight.sha256.json", {"sha256": receipt_sha256})
    return {
        "preflight_id": preflight_id,
        "state": state,
        "bodies_executed": False,
        "nodeid": target if collected_exact_node else None,
        "receipt": str(record_path),
        "receipt_sha256": receipt_sha256,
        "metrics": final,
    }


def _validate_d01_preflight_receipt(
    store: Path,
    preflight_id: str,
    *,
    target: str,
    identity: Mapping[str, Any],
    source_fingerprint: str,
    controller_provenance: Mapping[str, Any],
    guard_state: Mapping[str, Any],
) -> tuple[Path, str]:
    receipt_dir = _preflight_directory(store, "d01", preflight_id)
    record_path = receipt_dir / "preflight.json"
    sha_path = receipt_dir / "preflight.sha256.json"
    if not record_path.is_file() or not sha_path.is_file():
        raise PolicyError("a successful exact-node collect-only preflight receipt is required before reserving FEM")
    try:
        receipt = json.loads(record_path.read_text(encoding="utf-8"))
        sidecar = json.loads(sha_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"D01 preflight receipt is unreadable: {exc}") from exc
    actual_hash = _sha256(record_path)
    if sidecar.get("sha256") != actual_hash:
        raise PolicyError("D01 preflight receipt checksum mismatch")
    if (
        receipt.get("schema") != "qfsolver-development-d01-preflight-v1"
        or receipt.get("state") != "PREFLIGHT_PASS"
        or receipt.get("bodies_executed") is not False
        or receipt.get("target") != target
        or receipt.get("preflight_id") != preflight_id
        or receipt.get("identity") != dict(identity)
        or receipt.get("source_fingerprint") != source_fingerprint
        or receipt.get("controller_provenance") != dict(controller_provenance)
        or receipt.get("native_guard_environment") != dict(guard_state)
        or receipt.get("solver_origin_observed") != receipt.get("solver_origin_expected")
        or receipt.get("collected_nodeids") != [target]
    ):
        raise PolicyError("D01 preflight does not match this exact source, controller, environment and nodeid")
    return record_path, actual_hash


def _validate_wp12_dynamics_preflight_receipt(
    store: Path,
    preflight_id: str,
    *,
    target: str,
    identity: Mapping[str, Any],
    source_fingerprint: str,
    controller_provenance: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> tuple[Path, str]:
    """Require a checksummed, exact-node WP12-A collect-only receipt before manifest or attempt creation."""
    if target not in WP12_DYNAMICS_PREFLIGHT_NODEIDS:
        raise PolicyError("WP12-A preflight receipts are limited to the reviewed exact registered dynamics nodes")
    receipt_dir = _preflight_directory(store, "wp12_dynamics", preflight_id)
    record_path = receipt_dir / "preflight.json"
    sha_path = receipt_dir / "preflight.sha256.json"
    if not record_path.is_file() or not sha_path.is_file():
        raise PolicyError("a successful exact-node WP12-A collect-only preflight receipt is required")
    try:
        receipt = json.loads(record_path.read_text(encoding="utf-8"))
        sidecar = json.loads(sha_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"WP12-A preflight receipt is unreadable: {exc}") from exc
    if not isinstance(receipt, dict) or not isinstance(sidecar, dict):
        raise PolicyError("WP12-A preflight receipt and checksum sidecar must be JSON objects")
    actual_hash = _sha256(record_path)
    registration = receipt.get("registration")
    ledger = receipt.get("attempt_ledger")
    budgets = receipt.get("budgets")
    if not isinstance(registration, Mapping) or not isinstance(ledger, Mapping) or not isinstance(budgets, Mapping):
        raise PolicyError("WP12-A preflight receipt lacks registration or ledger attestations")
    current_policy = load_policy() if policy is None else policy
    ledger_path, _ledger_lock, mandate_id, predecessor = _node_ledger_context(
        current_policy, store, "wp12_dynamics"
    )
    if mandate_id != WP12_OWNER_ENVELOPES["wp12_dynamics"]["development_mandate_id"] or predecessor is None:
        raise PolicyError("WP12-A preflight ledger is not bound to the active scope mandate")
    current_ledger_sha = _sha256(ledger_path) if ledger_path.is_file() else None
    predecessor_sha = _sha256((store / predecessor["path"]).resolve())
    if sidecar.get("sha256") != actual_hash:
        raise PolicyError("WP12-A preflight receipt checksum mismatch")
    if (
        receipt.get("schema") != "qfsolver-development-wp12-dynamics-preflight-v2"
        or receipt.get("state") != "PREFLIGHT_PASS"
        or receipt.get("mode") != "DEVELOPMENT_AUTONOMOUS"
        or receipt.get("mandate_id") != WP12_OWNER_ENVELOPES["wp12_dynamics"]["development_mandate_id"]
        or receipt.get("worktree_id") != "wp12_dynamics"
        or receipt.get("target") != target
        or receipt.get("preflight_id") != preflight_id
        or receipt.get("phase") != "PYTEST_COLLECT_ONLY"
        or receipt.get("bodies_executed") is not False
        or receipt.get("attempt_reserved") is not False
        or receipt.get("ledger_touched") is not False
        or receipt.get("identity") != dict(identity)
        or receipt.get("identity_after") != dict(identity)
        or receipt.get("source_fingerprint") != source_fingerprint
        or receipt.get("source_fingerprint_after") != source_fingerprint
        or receipt.get("controller_provenance") != dict(controller_provenance)
        or receipt.get("controller_provenance_after") != dict(controller_provenance)
        or receipt.get("solver_origin_observed") != receipt.get("solver_origin_expected")
        or receipt.get("collected_nodeids") != [target]
        or receipt.get("skip_markers") != []
        or receipt.get("return_code") != 0
        or registration.get("target") != target
        or registration.get("source_fingerprint") != source_fingerprint
        or registration.get("timeout_seconds") != budgets.get("timeout_seconds")
        or ledger.get("touched") is not False
        or ledger.get("sha256_before") != ledger.get("sha256_after")
        or ledger.get("sha256_after") != current_ledger_sha
        or ledger.get("path") != str(ledger_path)
        or ledger.get("predecessor") != predecessor
        or ledger.get("predecessor_sha256_before") != predecessor_sha
        or ledger.get("predecessor_sha256_after") != predecessor_sha
    ):
        raise PolicyError("WP12-A preflight does not match this exact source, controller, ledger and nodeid")
    return record_path, actual_hash


def _validate_wp12b_hex20_r2_preflight_receipt(
    store: Path, preflight_id: str, *, target: str, identity: Mapping[str, Any],
    source_fingerprint: str, controller_provenance: Mapping[str, Any], policy: Mapping[str, Any],
) -> tuple[Path, str]:
    """Bind one checksummed R2 collect-only receipt to the current sources and ledgers."""
    if target != WP12B_HEX20_DIAGNOSTIC_NODEID:
        raise PolicyError("WP12-B R2 preflight target is not registered")
    receipt_dir = _preflight_directory(store, WP12B_HEX20_R2_WORKTREE_ID, preflight_id)
    path, sidecar_path = receipt_dir / "preflight.json", receipt_dir / "preflight.sha256.json"
    try:
        receipt = _read_strict_json(path)
        sidecar = _read_strict_json(sidecar_path)
        digest = _sha256(path)
    except (OSError, ValueError) as exc:
        raise PolicyError(f"WP12-B R2 preflight receipt is unreadable: {exc}") from exc
    if not isinstance(receipt, Mapping) or not isinstance(sidecar, Mapping) or sidecar != {"sha256": digest}:
        raise PolicyError("WP12-B R2 preflight receipt checksum mismatch")
    entry = policy["worktrees"][WP12B_HEX20_R2_WORKTREE_ID]
    ledger_path, _lock, mandate, predecessor = _node_ledger_context(policy, store, WP12B_HEX20_R2_WORKTREE_ID)
    if ledger_path.exists():
        current_ledger = _read_strict_json(ledger_path)
        if any(current_ledger["entries"].values()):
            raise PolicyError("WP12-B R2 attempt has already been consumed")
    ledger = receipt.get("attempt_ledger")
    current_sha = _sha256(ledger_path) if ledger_path.is_file() else None
    expected_origin = str((Path(entry["root"]) / entry["source_root"] / "solveur" / "__init__.py").resolve())
    registration = _wp12_active_registration(WP12B_HEX20_R2_WORKTREE_ID, target, entry, source_fingerprint)
    stdout_path, stderr_path = receipt_dir / "output" / "stdout.log", receipt_dir / "output" / "stderr.log"
    if (not stdout_path.is_file() or not stderr_path.is_file()
            or receipt.get("stdout_sha256") != _sha256(stdout_path)
            or receipt.get("stderr_sha256") != _sha256(stderr_path)):
        raise PolicyError("WP12-B R2 preflight output evidence is missing or changed")
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    attestation_status, _attestation = _validate_wp12_collect_attestation(
        stdout, target=target, solver_origin=expected_origin, selected_dofs=60, max_dofs=60,
        worktree_id=WP12B_HEX20_R2_WORKTREE_ID, schema=WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_SCHEMA,
        marker=WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_MARKER,
    )
    if attestation_status != "PREFLIGHT_PASS" or _observed_solver_origin(stdout + "\n" + stderr) != expected_origin:
        raise PolicyError("WP12-B R2 preflight output attestation is invalid")
    if (
        receipt.get("schema") != "qfsolver-development-wp12b-hex20-r2-preflight-v1"
        or receipt.get("state") != "PREFLIGHT_PASS"
        or receipt.get("mode") != "DEVELOPMENT_AUTONOMOUS"
        or receipt.get("mandate_id") != mandate
        or receipt.get("worktree_id") != WP12B_HEX20_R2_WORKTREE_ID
        or receipt.get("target") != target or receipt.get("preflight_id") != preflight_id
        or receipt.get("phase") != "PYTEST_COLLECT_ONLY" or receipt.get("bodies_executed") is not False
        or receipt.get("attempt_reserved") is not False or receipt.get("ledger_touched") is not False
        or receipt.get("identity") != dict(identity) or receipt.get("identity_after") != dict(identity)
        or receipt.get("source_fingerprint") != source_fingerprint
        or receipt.get("source_fingerprint_after") != source_fingerprint
        or receipt.get("controller_provenance") != dict(controller_provenance)
        or receipt.get("controller_provenance_after") != dict(controller_provenance)
        or receipt.get("solver_origin_expected") != expected_origin
        or receipt.get("solver_origin_observed") != expected_origin
        or receipt.get("collected_nodeids") != [target] or receipt.get("skip_markers") != []
        or receipt.get("return_code") != 0 or receipt.get("registration") != registration
        or receipt.get("budgets") != dict(entry["budgets"])
        or not isinstance(ledger, Mapping) or ledger.get("path") != str(ledger_path)
        or ledger.get("touched") is not False or ledger.get("sha256_before") != current_sha
        or ledger.get("sha256_after") != current_sha or ledger.get("predecessor") != predecessor
        or ledger.get("predecessor_sha256_before") != WP12B_HEX20_R1_LEDGER_SHA256
        or ledger.get("predecessor_sha256_after") != WP12B_HEX20_R1_LEDGER_SHA256
    ):
        raise PolicyError("WP12-B R2 preflight identity, provenance, ledger or nodeid mismatch")
    return path, digest


def _vv3d_campaign_disposition(assessment: Mapping[str, Any]) -> dict[str, str | None]:
    """Map a persisted campaign-gate verdict to runner/ledger terminal states."""
    status = assessment.get("status")
    if status == "PASS":
        return {"run_state": None, "ledger_status": None}
    if status == "FAIL":
        return {"run_state": "SCIENTIFIC_DEVIATION", "ledger_status": "FAIL"}
    if status == "INCONCLUSIVE":
        return {"run_state": "INCONCLUSIVE", "ledger_status": "INCONCLUSIVE"}
    if status == "NOT_ASSESSED":
        return {"run_state": None, "ledger_status": None}
    raise PolicyError("VV3D campaign assessment has an unknown terminal status")


def _vv3d_terminal_disposition(
    *, science_state: str, provenance_state: str, campaign_gate_status: str | None,
) -> dict[str, str]:
    """Preserve the observed test/provenance state while applying campaign STOP gates."""
    if provenance_state != "VERIFIED":
        return {"run_state": "PROVENANCE_MISMATCH", "ledger_status": "INFRA_ERROR"}
    if science_state == "PYTEST_FAILED":
        return {"run_state": "PYTEST_FAILED", "ledger_status": "FAIL"}
    if science_state != "PASS":
        if "TIMEOUT" in science_state:
            ledger_status = "TIMEOUT"
        elif "INTERRUPTED" in science_state:
            ledger_status = "INTERRUPTED"
        elif science_state == "INFRA_ERROR":
            ledger_status = "INFRA_ERROR"
        else:
            ledger_status = "RESOURCE_LIMIT"
        return {"run_state": science_state, "ledger_status": ledger_status}
    if campaign_gate_status == "FAIL":
        return {"run_state": "SCIENTIFIC_DEVIATION", "ledger_status": "FAIL"}
    if campaign_gate_status == "INCONCLUSIVE":
        return {"run_state": "INCONCLUSIVE", "ledger_status": "INCONCLUSIVE"}
    if campaign_gate_status not in {None, "PASS", "NOT_ASSESSED"}:
        raise PolicyError("VV3D campaign assessment has an unknown terminal status")
    return {"run_state": "PASS", "ledger_status": "PASS"}


def _vv3d_seed_passes_required_gates(run: Mapping[str, Any], *, require_campaign_pass: bool) -> bool:
    """Check that an adaptive seed is a consistent verified PASS with the required gates."""
    if (run.get("state") != "PASS" or run.get("scientific_state") != "PASS"
            or run.get("provenance_state") != "VERIFIED"):
        return False
    return not require_campaign_pass or run.get("campaign_gate_status") == "PASS"


def _vv3d_assess_campaign_family_after_run(
    *, case_id: str, attempt_id: str, science_state: str, provenance_state: str,
    sidecar_doc: Mapping[str, Any] | None, sidecar_ref: Mapping[str, str] | None,
    current_manifest: Mapping[str, Any], current_manifest_sha256: str,
    current_manifest_path: Path,
    evidence_root: Path, store: Path, execution_root: Path,
    source_fingerprint: str, controller_fingerprint: str, campaign_ledger: Any,
    campaign_id: str = VV3D_CAMPAIGN_ID,
    matrix_subdirectory: str = "prepared_20261029",
) -> tuple[dict[str, Any], dict[str, str]]:
    """Assess and immutably archive one family's campaign criteria after an initial case.

    Prior levels are admitted only through completed runner records, their bound
    manifest and sidecar bytes, and the append-only VV3D ledger. The current
    level uses the just-validated sidecar and its still-open reservation.
    """
    family, level_text = case_id.rsplit("-L", maxsplit=1)
    family = family.removeprefix("VV3D-")
    if family not in {"TET4", "TET10", "HEX8", "HEX20"} or level_text not in {"1", "2", "3"}:
        raise PolicyError("campaign assessment requires an exact initial family case")
    case_ids = [f"VV3D-{family}-L{level}" for level in (1, 2, 3)]
    matrix_path = execution_root / "experiments" / "wp12_vv3d_adaptive" / matrix_subdirectory / "MATRIX_NOT_AUTHORIZED.json"
    matrix = _read_strict_json(matrix_path)
    matrix_cases = {item.get("case_id"): item for item in matrix.get("cases", []) if isinstance(item, Mapping)}
    if matrix.get("campaign_id") != campaign_id or any(case not in matrix_cases for case in case_ids):
        raise PolicyError("campaign assessment matrix does not bind the exact family L1/L2/L3 cases")
    criteria = current_manifest.get("frozen_criteria")
    criteria_raw = json.dumps(criteria, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    criteria_sha256 = hashlib.sha256(criteria_raw).hexdigest()
    if current_manifest.get("criteria_sha256") != criteria_sha256:
        raise PolicyError("campaign assessment criteria differ from the exact current manifest")

    ledger_records = list(campaign_ledger.verify())
    seeds: dict[str, dict[str, Any]] = {}
    input_refs: list[dict[str, Any]] = []
    root = evidence_root.resolve(strict=False)
    store_root = store.resolve(strict=True)

    def seed_record(seed_case_id: str, run: Mapping[str, Any], *, current: bool = False) -> dict[str, Any]:
        expected_matrix = matrix_cases[seed_case_id]
        divisions = expected_matrix.get("divisions")
        if (not isinstance(divisions, list) or len(divisions) != 3
                or any(type(value) is not int or value <= 0 for value in divisions)
                or len(set(divisions)) != 1):
            raise PolicyError(f"campaign mesh size is not defined by the exact uniform mesh: {seed_case_id}")
        h_m = 1.0 / divisions[0]  # Frozen unit-cube protocol: h=1/n.
        result: dict[str, Any] = {
            "case_id": seed_case_id, "h_m": h_m,
            "mesh_sha256": expected_matrix.get("mesh_sha256"),
            "state": run.get("state", run.get("scientific_state")),
            "provenance_state": run.get("provenance_state"),
            "sidecar_valid": False,
        }
        manifest_meta = run.get("manifest")
        sidecar_meta = run.get("observables_sidecar")
        if (run.get("campaign_id") != campaign_id or run.get("case_id") != seed_case_id
                or run.get("source_fingerprint") != source_fingerprint
                or run.get("controller_fingerprint") != controller_fingerprint
                or run.get("provenance_state") != "VERIFIED"
                or run.get("mesh_sha256") != expected_matrix.get("mesh_sha256")
                or not isinstance(manifest_meta, Mapping)
                or not isinstance(sidecar_meta, Mapping)):
            result["state"] = "PROVENANCE_MISMATCH"
            return result
        manifest_path = current_manifest_path if current else Path(str(manifest_meta.get("path", ""))).resolve(strict=True)
        if not current:
            try:
                manifest_path.relative_to(store_root)
            except ValueError:
                result["state"] = "PROVENANCE_MISMATCH"
                return result
        manifest_raw = manifest_path.read_bytes()
        manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
        if manifest_sha != (current_manifest_sha256 if current else manifest_meta.get("sha256")):
            result["state"] = "PROVENANCE_MISMATCH"
            return result
        prior_manifest = _read_strict_json(manifest_path)
        if (prior_manifest.get("case_id") != seed_case_id
                or prior_manifest.get("mesh_sha256") != expected_matrix.get("mesh_sha256")
                or prior_manifest.get("frozen_criteria") != criteria
                or prior_manifest.get("criteria_sha256") != criteria_sha256):
            result["state"] = "PROVENANCE_MISMATCH"
            return result
        sidecar_path = (Path(str(sidecar_meta.get("path", ""))).resolve(strict=True) if not current
                        else Path(str(sidecar_meta.get("path", ""))).resolve(strict=True))
        try:
            sidecar_path.relative_to(root)
        except ValueError:
            result["state"] = "PROVENANCE_MISMATCH"
            return result
        sidecar_raw = sidecar_path.read_bytes()
        sidecar_sha = hashlib.sha256(sidecar_raw).hexdigest()
        if sidecar_sha != sidecar_meta.get("sha256"):
            result["state"] = "PROVENANCE_MISMATCH"
            return result
        sidecar = _read_strict_json(sidecar_path)
        if (sidecar.get("schema") != "qf-wp12-vv3d-observables-v1"
                or sidecar.get("campaign_id") != campaign_id
                or sidecar.get("case_id") != seed_case_id
                or sidecar.get("attempt_id") != run.get("attempt_id")
                or sidecar.get("mesh_sha256") != expected_matrix.get("mesh_sha256")
                or sidecar.get("manifest_sha256") != manifest_sha
                or sidecar.get("scientific_fingerprint") != source_fingerprint
                or sidecar.get("controller_fingerprint") != controller_fingerprint
                or not isinstance(sidecar.get("observables"), Mapping)
                or not isinstance(sidecar.get("criteria"), Mapping)):
            result["state"] = "PROVENANCE_MISMATCH"
            return result

        expected_nodeid = expected_matrix.get("nodeid")
        starts = [entry for entry in ledger_records
                  if entry.get("event") == "ATTEMPT_STARTED" and entry.get("case_id") == seed_case_id]
        if (len(starts) != 1 or starts[0].get("manifest_sha256") != manifest_sha
                or starts[0].get("attempt_id") != run.get("attempt_id")
                or starts[0].get("nodeid") != expected_nodeid
                or run.get("target") != expected_nodeid
                or starts[0].get("source_fingerprint") != source_fingerprint
                or starts[0].get("controller_fingerprint") != controller_fingerprint
                or starts[0].get("selected_dofs") != expected_matrix.get("dofs")):
            result["state"] = "PROVENANCE_MISMATCH"
            return result
        finishes = [entry for entry in ledger_records
                    if entry.get("event") == "ATTEMPT_FINISHED" and entry.get("run_id") == starts[0].get("run_id")]
        if current:
            if finishes:
                result["state"] = "PROVENANCE_MISMATCH"
                return result
        else:
            if len(finishes) != 1:
                result["state"] = "PROVENANCE_MISMATCH"
                return result
            expected_disposition = _vv3d_terminal_disposition(
                science_state=str(run.get("scientific_state", run.get("state", ""))),
                provenance_state=str(run.get("provenance_state", "")),
                campaign_gate_status=run.get("campaign_gate_status"),
            )
            if (finishes[0].get("status") != expected_disposition["ledger_status"]
                    or run.get("state") != expected_disposition["run_state"]):
                result["state"] = "PROVENANCE_MISMATCH"
                return result
        result.update({
            "state": run.get("scientific_state", run.get("state")),
            "provenance_state": "VERIFIED", "sidecar_valid": True,
            "sidecar_sha256": sidecar_sha, "manifest_sha256": manifest_sha,
            "scientific_fingerprint": source_fingerprint,
            "controller_fingerprint": controller_fingerprint,
            "observables": sidecar["observables"], "criteria": sidecar["criteria"],
        })
        input_refs.append({
            "case_id": seed_case_id, "state": result["state"], "h_m": h_m,
            "mesh_sha256": result["mesh_sha256"], "manifest_sha256": manifest_sha,
            "sidecar_path": str(sidecar_path), "sidecar_sha256": sidecar_sha,
        })
        return result

    for seed_case_id in case_ids:
        if seed_case_id == case_id:
            current_run = {
                "campaign_id": campaign_id, "case_id": case_id, "attempt_id": attempt_id,
                "target": matrix_cases[case_id].get("nodeid"),
                "scientific_state": science_state, "provenance_state": provenance_state,
                "source_fingerprint": source_fingerprint, "controller_fingerprint": controller_fingerprint,
                "mesh_sha256": current_manifest.get("mesh_sha256"),
                "manifest": {"path": str(current_manifest_path), "sha256": current_manifest_sha256},
                "observables_sidecar": dict(sidecar_ref) if sidecar_ref else None,
            }
            seeds[seed_case_id] = seed_record(seed_case_id, current_run, current=True)
            continue
        matches: list[Mapping[str, Any]] = []
        for record_path in store.rglob("run.json") if store.exists() else ():
            try:
                candidate_record = _read_strict_json(record_path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if (candidate_record.get("campaign_id") == campaign_id
                    and candidate_record.get("case_id") == seed_case_id
                    and candidate_record.get("state") != "RUNNING"):
                matches.append(candidate_record)
        if len(matches) > 1:
            seeds[seed_case_id] = {"case_id": seed_case_id, "state": "PROVENANCE_MISMATCH",
                                   "provenance_state": "PROVENANCE_MISMATCH", "sidecar_valid": False}
        elif matches:
            seeds[seed_case_id] = seed_record(seed_case_id, matches[0])

    import importlib
    import sys
    sys.path.insert(0, str(execution_root))
    try:
        science_harness = importlib.import_module("experiments.wp12_vv3d_adaptive.case_harness")
        assessment = science_harness.evaluate_campaign_criteria(family, seeds, criteria)
    except Exception as exc:
        campaign_criteria = {
            name: {"classification": "CAMPAIGN_GATE", "status": "INCONCLUSIVE",
                   "reason": "CAMPAIGN_EVALUATOR_ERROR"}
            for name in (
                "displacement_error_L3", "energy_error_L3", "stress_error_L3",
                "scalar_energy_error_L3", "displacement_order", "energy_order",
            )
        }
        assessment = {
            "schema": "qf-wp12-vv3d-campaign-assessment-v1", "status": "INCONCLUSIVE",
            "decision": "STOP_INCONCLUSIVE", "criteria": campaign_criteria, "level_metrics": {},
            "blocking_failures": [], "reason": f"CAMPAIGN_EVALUATOR_ERROR:{type(exc).__name__}:{exc}",
        }
    finally:
        try:
            sys.path.remove(str(execution_root))
        except ValueError:
            pass
    record = {
        "schema": "qf-wp12-vv3d-campaign-assessment-record-v1",
        "campaign_id": campaign_id, "family": family,
        "evaluated_after_case_id": case_id, "evaluated_after_attempt_id": attempt_id,
        "scientific_fingerprint": source_fingerprint,
        "controller_fingerprint": controller_fingerprint,
        "criteria_sha256": criteria_sha256,
        "input_evidence": sorted(input_refs, key=lambda item: item["case_id"]),
        "assessment": assessment,
    }
    assessment_path = (evidence_root / "campaign-assessments" / campaign_id / family /
                       f"{case_id}-{attempt_id}.json")
    _atomic_json_new(assessment_path, record)
    return assessment, {"path": str(assessment_path.resolve()), "sha256": _sha256(assessment_path)}


def run_wp12_vv3d_pytest(
    target: str | None, series_id: str | None, *, worktree_id: str, reason: str,
    preflight_id: str | None, execution_manifest: Path | None,
) -> tuple[dict[str, Any], int]:
    """Run one Owner-approved VV3D R1 or R2 case through its campaign ledger."""
    policy = load_policy()
    is_r2 = worktree_id == VV3D_R2_WORKTREE_ID
    allowed_nodes = VV3D_R2_NODEIDS if is_r2 else (*VV3D_INITIAL_NODEIDS, *VV3D_ADAPTIVE_FEM_NODEIDS)
    if worktree_id not in {VV3D_WORKTREE_ID, VV3D_R2_WORKTREE_ID} or target not in allowed_nodes:
        raise PolicyError("VV3D runner accepts only one exact nodeid registered in its R1 or R2 scope")
    if is_r2 and target not in VV3D_R2_NODEIDS:
        raise PolicyError("VV3D R2 excludes H1, QLOAD and QPOST routes")
    if not reason or not reason.strip() or not preflight_id or execution_manifest is None:
        raise PolicyError("VV3D requires a reason, exact collect-only preflight, and case execution manifest")
    entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
        worktree_id, target, policy
    )
    controller_provenance = (_vv3d_scope_controller_provenance(worktree_id) if is_r2
                              else _vv3d_controller_provenance())
    store = _run_root(policy, worktree_id)
    bindings_validator = _vv3d_r2_execution_bindings if is_r2 else _vv3d_execution_bindings
    manifest, preflight, manifest_sha, preflight_sha, decision_id, decision_sha = bindings_validator(
        target=target, preflight_id=preflight_id, manifest_path=execution_manifest,
        entry=entry, execution_root=execution_root, identity=identity,
        source_fingerprint=source_fingerprint, controller_provenance=controller_provenance, store=store,
    )
    case_id = manifest["case_id"]
    selected_dofs = manifest["selected_dofs"]
    timeout = manifest["timeout_seconds"]
    scope = dict(entry["budgets"])
    scope["timeout_seconds"] = timeout
    scope["archive_size_limit_mib"] = manifest.get("archive_size_limit_mib", 256)
    if (selected_dofs != entry["per_node_selected_dofs"].get(target)
            or selected_dofs > entry["target_max_dofs"] or timeout > entry["max_timeout_seconds"]
            or scope["rss_soft_limit_mib"] != manifest["rss_soft_limit_mib"]
            or scope["archive_size_limit_mib"] != 256):
        raise PolicyError("VV3D case selection or resource envelope exceeds the exact policy")
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free,
                     shutil.disk_usage(store.parent if not store.exists() else store).free)
    if free_bytes < int(policy["minimum_free_disk_mib"] * 1024 * 1024):
        raise PolicyError("insufficient free disk before VV3D campaign reservation")
    if series_id is None:
        series_id = f"dev-{uuid.uuid4().hex[:12]}"
    if not SERIES_RE.fullmatch(series_id):
        raise PolicyError("series ID must use the development-only format dev-<lowercase-id>")
    campaign_ledger_path = store / str(entry["node_attempt_ledger"]["path"])
    series_dir = _series_root(store, "fem_exploratory", worktree_id) / series_id
    evidence_root = str(Path(entry["evidence_root"]).resolve())
    controller_fingerprint = _stable_fingerprint(controller_provenance)
    adaptive = not is_r2 and target in VV3D_ADAPTIVE_FEM_NODEIDS
    attempt_id = str(manifest["attempt_id"]) if adaptive else f"{series_id}-attempt-1"
    if is_r2:
        RecoveryR2Ledger = _load_vv3d_r2_ledger_module().RecoveryR2Ledger
        if __package__:
            from .wp12_vv3d_ledger import RunBinding, RunnerCaseBinding
        else:
            from wp12_vv3d_ledger import RunBinding, RunnerCaseBinding
    else:
        try:
            from wp12_vv3d_ledger import BudgetLedger, RunBinding, RunnerCaseBinding
        except ModuleNotFoundError:  # imported as scripts.development_autonomous by tests
            from scripts.wp12_vv3d_ledger import BudgetLedger, RunBinding, RunnerCaseBinding

    store.mkdir(parents=True, exist_ok=True)
    if is_r2:
        predecessor = entry["node_attempt_ledger"]["predecessor"]
        campaign_ledger = RecoveryR2Ledger(
            campaign_ledger_path, allowed_root=store,
            predecessor_path=Path(predecessor["path"]), predecessor_sha256=predecessor["sha256"],
        )
    else:
        campaign_ledger = BudgetLedger(campaign_ledger_path, allowed_root=store)
    with _exclusive_file_lock(store / "locks" / "vv3d-campaign-exclusive.lock"):
        number, attempt_dir = _next_attempt(
            series_dir, series_id, "fem_exploratory", 1, worktree_id=worktree_id, target=target,
        )
        if number != 1:
            raise PolicyError("VV3D case attempts are single-use; no retry is allowed")
        temp_dir = attempt_dir / "tmp"
        output_dir = attempt_dir / "output"
        temp_dir.mkdir()
        output_dir.mkdir()
        runner_receipt_path = attempt_dir / "vv3d-runner-reservation.json"
        run_binding = RunBinding(
            contract_sha256=manifest["campaign_contract_sha256"], decision_id=decision_id,
            decision_sha256=decision_sha, manifest_sha256=manifest_sha, preflight_sha256=preflight_sha,
            **manifest.get("_validated_transition_binding", {}),
        )
        case_binding = RunnerCaseBinding(
            case_id=case_id, nodeid=target, attempt_id=attempt_id,
            authorization_id=manifest["authorization_id"],
            source_fingerprint=source_fingerprint, controller_fingerprint=controller_fingerprint,
            selected_dofs=selected_dofs, timeout_seconds=timeout, rss_soft_limit_mib=4096,
            archive_limit_mib=256, evidence_root=evidence_root,
            reservation_id=(str(manifest["reservation_id"]) if adaptive else None),
        )
        try:
            if is_r2:
                runner_receipt = campaign_ledger.start_runner_attempt(
                    binding=run_binding, case=case_binding, receipt_path=runner_receipt_path,
                )
            else:
                runner_receipt = campaign_ledger.start_runner_attempt(
                    binding=run_binding, case=case_binding, receipt_path=runner_receipt_path,
                    receipt_fields=(manifest.get("_runner_receipt_fields") if adaptive else None),
                )
        except Exception:
            # No campaign reservation succeeded, so the empty local attempt directory
            # can be removed without altering the campaign ledger.
            try:
                temp_dir.rmdir()
                output_dir.rmdir()
                attempt_dir.rmdir()
            except OSError:
                pass
            raise
        reservation_started_monotonic = time.monotonic()
        runner_receipt_sha = runner_receipt["receipt_sha256"]
        record_path = attempt_dir / "run.json"
        command = build_pytest_command(
            "fem_exploratory", [target], temp_dir, repository_root=execution_root,
            source_root=source_root, controller_root=ROOT,
        )
        environment = build_child_environment(temp_dir, source_root=source_root)
        if adaptive:
            environment.update({
                "QF_DEV_VV3D_ADAPTIVE_CANDIDATE_ID": case_id,
                "QF_DEV_TARGET_NODEID": target,
                "QF_DEV_VV3D_ADAPTIVE_RECEIPT_PATH": str(runner_receipt_path),
                "QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256": runner_receipt_sha,
                "QF_DEV_EVIDENCE_ROOT": evidence_root,
            })
        else:
            environment.update({
            "QF_DEV_WORKTREE_ID": worktree_id,
            "QF_DEV_CAMPAIGN_SCOPE_ID": worktree_id,
            "QF_DEV_VV3D_CASE_ID": case_id,
            "QF_DEV_TARGET_NODEID": target,
            "QF_DEV_MANIFEST_PATH": str(execution_manifest.resolve()),
            "QF_DEV_MANIFEST_SHA256": manifest_sha,
            "QF_DEV_AUTHORIZATION_ID": manifest["authorization_id"],
            "QF_DEV_VV3D_SCIENCE_FINGERPRINT": source_fingerprint,
            "QF_DEV_CONTROLLER_FINGERPRINT": controller_fingerprint,
            "QF_DEV_EVIDENCE_ROOT": evidence_root,
            "QF_DEV_VV3D_RUNNER_RECEIPT_PATH": str(runner_receipt_path),
            "QF_DEV_VV3D_RUNNER_RECEIPT_SHA256": runner_receipt_sha,
            })
        started_at = datetime.now(timezone.utc).isoformat()
        initial = {
            "schema": "qfsolver-development-vv3d-run-v1", "state": "RUNNING",
            "campaign_id": VV3D_R2_CAMPAIGN_ID if is_r2 else VV3D_CAMPAIGN_ID,
            "case_id": case_id, "attempt_id": attempt_id,
            "worktree_id": worktree_id,
            "target": target, "reason": reason.strip(), "identity": identity,
            "source_fingerprint": source_fingerprint, "controller_fingerprint": controller_fingerprint,
            "controller_provenance": controller_provenance,
            "manifest": {"path": str(execution_manifest.resolve()), "sha256": manifest_sha},
            "mesh_sha256": manifest["mesh_sha256"],
            "preflight": {"id": preflight_id, "sha256": preflight_sha},
            "campaign_decision": {"decision_id": decision_id, "sha256": decision_sha},
            "campaign_ledger": {"path": str(campaign_ledger_path), "sha256_after_reservation": runner_receipt["ledger_sha256_after_reservation"]},
            "runner_receipt": {"path": str(runner_receipt_path), "sha256": runner_receipt_sha},
            "command": command, "budgets": scope, "started_at_utc": started_at,
            "scientific_state": None, "provenance_state": "PENDING",
        }
        _atomic_json(record_path, initial)
        scope["minimum_free_disk_mib"] = policy["minimum_free_disk_mib"]
        try:
            result = run_supervised_command(
                command, cwd=execution_root, environment=environment, output_dir=output_dir,
                temporary_dir=temp_dir, limits=scope, poll_interval=float(policy["poll_interval_seconds"]),
            )
            science_state = result.status
            try:
                after_entry, _after_root, _after_source, after_identity, after_fingerprint = _registered_worktree(
                    worktree_id, target, policy
                )
                origin = _observed_solver_origin(
                    (output_dir / "stdout.log").read_text(encoding="utf-8", errors="replace") + "\n" +
                    (output_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
                )
                expected_origin = str((source_root / "solveur" / "__init__.py").resolve())
                provenance_state = ("VERIFIED" if after_entry == entry and after_identity == identity
                                    and after_fingerprint == source_fingerprint
                                    and (_vv3d_scope_controller_provenance(worktree_id) if is_r2
                                         else _vv3d_controller_provenance()) == controller_provenance
                                    and origin == expected_origin else "PROVENANCE_MISMATCH")
            except (OSError, PolicyError):
                origin = None
                provenance_state = "PROVENANCE_MISMATCH"
            final_state = science_state if provenance_state == "VERIFIED" else "PROVENANCE_MISMATCH"
            sidecar_path = Path(evidence_root) / case_id / attempt_id / "observables.json"
            sidecar_ref = None
            scientific_observables = None
            scientific_criteria = None
            sidecar_doc: Mapping[str, Any] | None = None
            if sidecar_path.is_file():
                try:
                    candidate_sidecar = _read_strict_json(sidecar_path)
                    sidecar_execution = (candidate_sidecar.get("execution")
                                         if isinstance(candidate_sidecar, Mapping) else None)
                    if (isinstance(candidate_sidecar, Mapping)
                            and candidate_sidecar.get("schema") == "qf-wp12-vv3d-observables-v1"
                            and candidate_sidecar.get("campaign_id") == (VV3D_R2_CAMPAIGN_ID if is_r2 else VV3D_CAMPAIGN_ID)
                            and candidate_sidecar.get("case_id") == case_id
                            and candidate_sidecar.get("attempt_id") == attempt_id
                            and candidate_sidecar.get("case_state") == "OWNER_AUTHORIZED_EXECUTION"
                            and candidate_sidecar.get("runner_receipt_sha256") == runner_receipt_sha
                            and candidate_sidecar.get("mesh_sha256") == manifest.get("mesh_sha256")
                            and candidate_sidecar.get("manifest_sha256") == manifest_sha
                            and candidate_sidecar.get("scientific_fingerprint") == source_fingerprint
                            and candidate_sidecar.get("controller_fingerprint") == controller_fingerprint
                            and isinstance(sidecar_execution, Mapping)
                            and sidecar_execution.get("status") in {
                                "COMPLETED_UNASSESSED", "FAILED_OR_INCOMPLETE"}
                            and sidecar_execution.get("attempt_reserved") is True
                            and sidecar_execution.get("fem_started") is True
                            and (science_state != "PASS"
                                 or sidecar_execution.get("status") == "COMPLETED_UNASSESSED")):
                        sidecar_doc = candidate_sidecar
                        sidecar_ref = {"path": str(sidecar_path.resolve()), "sha256": _sha256(sidecar_path)}
                        scientific_observables = sidecar_doc.get("observables")
                        scientific_criteria = sidecar_doc.get("criteria")
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    sidecar_ref = None
            if sidecar_ref is None:
                provenance_state = "PROVENANCE_MISMATCH"
                final_state = "PROVENANCE_MISMATCH"
            campaign_assessment = None
            campaign_assessment_ref = None
            campaign_gate_status = None
            if not adaptive:
                try:
                    campaign_assessment, campaign_assessment_ref = _vv3d_assess_campaign_family_after_run(
                        case_id=case_id, attempt_id=attempt_id, science_state=science_state,
                        provenance_state=provenance_state, sidecar_doc=sidecar_doc, sidecar_ref=sidecar_ref,
                        current_manifest=manifest, current_manifest_sha256=manifest_sha,
                        current_manifest_path=execution_manifest.resolve(strict=True),
                        evidence_root=Path(evidence_root), store=store, execution_root=execution_root,
                        source_fingerprint=source_fingerprint, controller_fingerprint=controller_fingerprint,
                        campaign_ledger=campaign_ledger,
                        campaign_id=VV3D_R2_CAMPAIGN_ID if is_r2 else VV3D_CAMPAIGN_ID,
                        matrix_subdirectory="prepared_20261030_r2" if is_r2 else "prepared_20261029",
                    )
                    campaign_gate_status = campaign_assessment.get("status")
                except (OSError, PolicyError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                    # The scientific attempt remains consumed. A failure to produce
                    # a provenance-bound assessment blocks continuation as infrastructure.
                    provenance_state = "PROVENANCE_MISMATCH"
                    final_state = "PROVENANCE_MISMATCH"
                    campaign_assessment = {
                        "schema": "qf-wp12-vv3d-campaign-assessment-v1",
                        "status": "INCONCLUSIVE", "decision": "STOP_INCONCLUSIVE",
                        "criteria": {}, "level_metrics": {}, "blocking_failures": [],
                        "reason": f"ASSESSMENT_ARCHIVE_OR_PROVENANCE_ERROR:{type(exc).__name__}:{exc}",
                    }
                    campaign_gate_status = "INCONCLUSIVE"
            terminal = _vv3d_terminal_disposition(
                science_state=science_state, provenance_state=provenance_state,
                campaign_gate_status=campaign_gate_status,
            )
            final_state = terminal["run_state"]
            state_archive = None
            state_archive_error = None
            if final_state == "PASS" and not adaptive and not is_r2:
                try:
                    state_archive = _write_vv3d_state_archive(
                        evidence_root=Path(evidence_root), case_id=case_id, attempt_id=attempt_id,
                        mesh_sha256=str(manifest["mesh_sha256"]), manifest_sha256=manifest_sha,
                        scientific_fingerprint=source_fingerprint,
                        controller_fingerprint=controller_fingerprint,
                    )
                except (OSError, PolicyError, TypeError, ValueError) as exc:
                    state_archive_error = f"{type(exc).__name__}: {exc}"
                if state_archive is None or state_archive_error is not None:
                    provenance_state = "PROVENANCE_MISMATCH"
            terminal = _vv3d_terminal_disposition(
                science_state=science_state, provenance_state=provenance_state,
                campaign_gate_status=campaign_gate_status,
            )
            final_state = terminal["run_state"]
            ledger_status = terminal["ledger_status"]
            campaign_ledger.finish_runner_attempt(
                run_id=runner_receipt["reservation_id"], status=ledger_status,
                elapsed_seconds=result.elapsed_seconds,
            )
            final = {
                **initial, "state": final_state, "scientific_state": science_state,
                "provenance_state": provenance_state, "solver_origin_observed": origin,
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "return_code": result.return_code, "elapsed_seconds": result.elapsed_seconds,
                "peak_rss_bytes": result.peak_rss_bytes, "peak_process_count": result.peak_process_count,
                "stdout_bytes": result.stdout_bytes, "stderr_bytes": result.stderr_bytes,
                "stdout_sha256": _sha256(output_dir / "stdout.log"),
                "stderr_sha256": _sha256(output_dir / "stderr.log"),
                "archive_bytes": result.archive_bytes, "temporary_bytes": result.temporary_bytes,
                "stop_reason": result.stop_reason,
                "qpost_state_archive": state_archive,
                "qpost_state_archive_error": state_archive_error,
                "observables_sidecar": sidecar_ref,
                "scientific_observables": scientific_observables,
                "scientific_criteria": scientific_criteria,
                "campaign_gate_status": campaign_gate_status,
                "campaign_assessment": campaign_assessment_ref,
                "campaign_assessment_result": campaign_assessment,
                "campaign_ledger_sha256_after_completion": _sha256(campaign_ledger_path),
            }
            _atomic_json(record_path, final)
            return {"series_id": series_id, "attempt": 1, "state": final_state,
                    "record": str(record_path), "metrics": final}, (0 if final_state == "PASS" else 1)
        except Exception as exc:
            # Handled launcher/infrastructure errors consume the reserved attempt
            # and elapsed budget. A hard process termination leaves ATTEMPT_STARTED
            # open, which the ledger treats as an unrecoverable blocking reservation.
            elapsed = max(0.0, time.monotonic() - reservation_started_monotonic)
            try:
                campaign_ledger.finish_runner_attempt(
                    run_id=runner_receipt["reservation_id"], status="INFRA_ERROR", elapsed_seconds=elapsed,
                )
            except Exception:
                pass
            _atomic_json(record_path, {
                **initial, "state": "INFRA_ERROR", "scientific_state": "NOT_COMPLETED",
                "provenance_state": "NOT_VERIFIED", "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "error": f"{type(exc).__name__}: {exc}",
            })
            return {"series_id": series_id, "attempt": 1, "state": "INFRA_ERROR", "record": str(record_path)}, 1


def run_wp12_vv3d_qpost_pytest(
    target: str, series_id: str | None, *, reason: str, preflight_id: str | None,
    execution_manifest: Path | None,
) -> tuple[dict[str, Any], int]:
    """Run one catalogued archive-only QPOST job; it consumes seconds, not FEM attempts."""
    policy = load_policy()
    entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
        VV3D_WORKTREE_ID, target, policy,
    )
    if not reason.strip() or not preflight_id or execution_manifest is None:
        raise PolicyError("VV3D QPOST requires a reason, exact preflight, and exact execution manifest")
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    controller_provenance = _vv3d_controller_provenance()
    store = _run_root(policy, VV3D_WORKTREE_ID)
    manifest, preflight, receipt_fields = _vv3d_qpost_launch_bindings(
        target=target, preflight_id=preflight_id, manifest_path=execution_manifest,
        entry=entry, execution_root=execution_root, identity=identity,
        source_fingerprint=source_fingerprint, controller_provenance=controller_provenance,
        store=store,
    )
    if series_id is None:
        series_id = f"dev-{uuid.uuid4().hex[:12]}"
    if not SERIES_RE.fullmatch(series_id):
        raise PolicyError("series ID must use the development-only format dev-<lowercase-id>")
    candidate_id = str(manifest["candidate_id"])
    case_id = str(manifest["seed_case"])
    source_manifest_sha = str(receipt_fields["source_manifest_sha256"])
    archive_ref = receipt_fields["archive"]
    ledger_path = store / str(entry["node_attempt_ledger"]["path"])
    evidence_root = str(Path(entry["evidence_root"]).resolve())
    controller_fingerprint = _stable_fingerprint(controller_provenance)
    qpost_id = str(manifest["postprocessing_job_id"])
    run_dir = _series_root(store, "fem_exploratory", VV3D_WORKTREE_ID) / "qpost" / qpost_id / series_id
    _create_campaign_directory(store, run_dir)
    temp_dir, output_dir = run_dir / "tmp", run_dir / "output"
    temp_dir.mkdir()
    output_dir.mkdir()
    receipt_path = run_dir / "vv3d-adaptive-runner-receipt.json"
    try:
        from wp12_vv3d_ledger import BudgetLedger, RunBinding
    except ModuleNotFoundError:  # imported as scripts.development_autonomous by tests
        from scripts.wp12_vv3d_ledger import BudgetLedger, RunBinding

    ledger = BudgetLedger(ledger_path, allowed_root=store)
    binding = RunBinding(
        contract_sha256=hashlib.sha256((store / "authorizations" / VV3D_WORKTREE_ID /
                                        "campaign-contract.json").read_bytes()).hexdigest(),
        decision_id=str(receipt_fields["campaign_decision"]["decision_id"]),
        decision_sha256=str(receipt_fields["campaign_decision"]["decision_sha256"]),
        manifest_sha256=source_manifest_sha,
        preflight_sha256=str(receipt_fields["preflight_receipt_sha256"]),
        transition_receipt_sha256=str(receipt_fields["eligibility_record"]["sha256"]),
        transition_source_case_id=case_id,
        transition_destination_case_id=candidate_id,
    )
    timeout = min(int(manifest.get("timeout_seconds", 1200)), 1200)
    if type(manifest.get("timeout_seconds")) is not int or timeout <= 0:
        raise PolicyError("VV3D QPOST manifest timeout is invalid")
    scope = dict(entry["budgets"])
    scope.update({"timeout_seconds": timeout, "archive_size_limit_mib": 256,
                  "minimum_free_disk_mib": policy["minimum_free_disk_mib"]})
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free,
                     shutil.disk_usage(store.parent if not store.exists() else store).free)
    if free_bytes < int(policy["minimum_free_disk_mib"] * 1024 * 1024):
        raise PolicyError("insufficient free disk before VV3D QPOST reservation")
    try:
        with _exclusive_file_lock(store / "locks" / "vv3d-campaign-exclusive.lock"):
            receipt = ledger.start_runner_postprocess_job(
                job_id=candidate_id, source_case_id=case_id,
                archived_state_sha256=str(archive_ref["sha256"]), binding=binding,
                nodeid=target, source_fingerprint=source_fingerprint,
                controller_fingerprint=controller_fingerprint, evidence_root=evidence_root,
                receipt_path=receipt_path, job_manifest_sha256=str(receipt_fields["manifest_sha256"]),
                receipt_fields=receipt_fields,
            )
            receipt_sha = str(receipt["receipt_sha256"])
            command = build_pytest_command(
                "fem_exploratory", [target], temp_dir, repository_root=execution_root,
                source_root=source_root, controller_root=ROOT,
            )
            environment = build_child_environment(temp_dir, source_root=source_root)
            environment.update({
                "QF_DEV_WORKTREE_ID": VV3D_WORKTREE_ID,
                "QF_DEV_VV3D_ADAPTIVE_CANDIDATE_ID": candidate_id,
                "QF_DEV_TARGET_NODEID": target,
                "QF_DEV_VV3D_ADAPTIVE_RECEIPT_PATH": str(receipt_path),
                "QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256": receipt_sha,
                "QF_DEV_EVIDENCE_ROOT": evidence_root,
            })
            started_monotonic = time.monotonic()
            try:
                result = run_supervised_command(
                    command, cwd=execution_root, environment=environment,
                    output_dir=output_dir, temporary_dir=temp_dir, limits=scope,
                    poll_interval=float(policy["poll_interval_seconds"]),
                )
                science_state = result.status
                provenance_state = "VERIFIED"
                after_entry, _after_root, _after_source, after_identity, after_fingerprint = _registered_worktree(
                    VV3D_WORKTREE_ID, target, policy,
                )
                if (after_entry != entry or after_identity != identity or after_fingerprint != source_fingerprint
                        or _vv3d_controller_provenance() != controller_provenance):
                    provenance_state = "PROVENANCE_MISMATCH"
                qpost_sidecar_path = (Path(evidence_root) / candidate_id / qpost_id / "observables.json")
                qpost_sidecar = None
                if qpost_sidecar_path.is_file():
                    try:
                        qpost_sidecar = _read_strict_json(qpost_sidecar_path)
                    except (OSError, ValueError, json.JSONDecodeError):
                        provenance_state = "PROVENANCE_MISMATCH"
                qpost_execution = (qpost_sidecar.get("execution")
                                   if isinstance(qpost_sidecar, Mapping) else None)
                if (not isinstance(qpost_sidecar, Mapping)
                        or qpost_sidecar.get("schema") != "qf-wp12-vv3d-observables-v1"
                        or qpost_sidecar.get("campaign_id") != VV3D_CAMPAIGN_ID
                        or qpost_sidecar.get("case_id") != candidate_id
                        or qpost_sidecar.get("attempt_id") != qpost_id
                        or qpost_sidecar.get("case_state") != "OWNER_AUTHORIZED_POSTPROCESS_ONLY"
                        or qpost_sidecar.get("mesh_sha256") != receipt_fields["mesh_sha256"]
                        or qpost_sidecar.get("manifest_sha256") != receipt_fields["manifest_sha256"]
                        or qpost_sidecar.get("scientific_fingerprint") != source_fingerprint
                        or qpost_sidecar.get("controller_fingerprint") != controller_fingerprint
                        or qpost_sidecar.get("runner_receipt_sha256") != receipt_sha
                        or qpost_sidecar.get("archive_sha256") != archive_ref["sha256"]
                        or not isinstance(qpost_execution, Mapping)
                        or qpost_execution.get("status") not in {
                            "COMPLETED_UNASSESSED", "FAILED_OR_INCOMPLETE"}):
                    provenance_state = "PROVENANCE_MISMATCH"
                elif (qpost_execution.get("attempt_reserved") is not False
                      or qpost_execution.get("postprocessing_reserved") is not True
                      or qpost_execution.get("fem_started") is not False):
                    provenance_state = "PROVENANCE_MISMATCH"
                receipt_raw = receipt_path.read_bytes()
                receipt_checksum = receipt_path.with_suffix(receipt_path.suffix + ".sha256.json")
                if (hashlib.sha256(receipt_raw).hexdigest() != receipt_sha
                        or _read_strict_json(receipt_checksum).get("sha256") != receipt_sha
                        or receipt.get("attempt_reserved") is not False
                        or receipt.get("postprocessing_reserved") is not True):
                    provenance_state = "PROVENANCE_MISMATCH"
                qpost_result = (qpost_sidecar.get("observables", {}).get("qpost", {})
                                if isinstance(qpost_sidecar, Mapping) else {})
                observed_max = qpost_result.get("maximum_relative_change") if isinstance(qpost_result, Mapping) else None
                threshold = float(receipt_fields["eligibility_threshold"])
                if (science_state == "PASS" and provenance_state == "VERIFIED"
                        and (isinstance(observed_max, bool) or not isinstance(observed_max, (int, float))
                             or not math.isfinite(observed_max))):
                    final_state = "INCONCLUSIVE"
                else:
                    final_state = science_state if provenance_state == "VERIFIED" else "PROVENANCE_MISMATCH"
                run_id = str(receipt["reservation_id"])
                ledger_status = ("PASS" if science_state == "PASS" and provenance_state == "VERIFIED"
                                 and final_state != "INCONCLUSIVE" else
                                 "FAIL" if science_state == "PYTEST_FAILED" and provenance_state == "VERIFIED"
                                 else "INFRA_ERROR")
                ledger.finish_runner_postprocess_job(
                    run_id=run_id, status=ledger_status, elapsed_seconds=result.elapsed_seconds,
                )
                record = {
                    "schema": "qfsolver-development-vv3d-qpost-run-v1", "state": final_state,
                    "campaign_id": VV3D_CAMPAIGN_ID, "candidate_id": candidate_id, "nodeid": target,
                    "source_case_id": case_id, "source_manifest_sha256": source_manifest_sha,
                    "archive": archive_ref, "manifest_sha256": receipt_fields["manifest_sha256"],
                    "preflight_sha256": receipt_fields["preflight_receipt_sha256"],
                    "runner_receipt": {"path": str(receipt_path), "sha256": receipt_sha},
                    "identity": identity, "source_fingerprint": source_fingerprint,
                    "controller_provenance": controller_provenance, "provenance_state": provenance_state,
                    "command": command,
                    "budgets": scope, "return_code": result.return_code,
                    "elapsed_seconds": result.elapsed_seconds, "peak_rss_bytes": result.peak_rss_bytes,
                    "stdout_sha256": _sha256(output_dir / "stdout.log"),
                    "stderr_sha256": _sha256(output_dir / "stderr.log"),
                    "qpost_sidecar": (str(qpost_sidecar_path) if qpost_sidecar_path.is_file() else None),
                    "qpost_sidecar_sha256": (_sha256(qpost_sidecar_path) if qpost_sidecar_path.is_file() else None),
                    "qpost_observable_maximum_relative_change": observed_max,
                    "qpost_frozen_trigger_threshold": threshold,
                    "qpost_scientific_output": qpost_result,
                    "qpost_triggered": (bool(observed_max > threshold)
                                        if isinstance(observed_max, (int, float)) and not isinstance(observed_max, bool)
                                        else None),
                    "stop_reason": result.stop_reason,
                }
                record_path = run_dir / "run.json"
                _atomic_json(record_path, record)
                return {"state": final_state, "record": str(record_path), "metrics": record}, (
                    0 if final_state == "PASS" else 1
                )
            except Exception as exc:
                elapsed = max(0.0, time.monotonic() - started_monotonic)
                try:
                    ledger.finish_runner_postprocess_job(
                        run_id=str(receipt["reservation_id"]), status="INFRA_ERROR", elapsed_seconds=elapsed,
                    )
                except Exception:
                    pass
                record_path = run_dir / "run.json"
                record = {"schema": "qfsolver-development-vv3d-qpost-run-v1", "state": "INFRA_ERROR",
                          "campaign_id": VV3D_CAMPAIGN_ID, "candidate_id": candidate_id,
                          "nodeid": target, "source_case_id": case_id,
                          "runner_receipt": {"path": str(receipt_path), "sha256": receipt_sha},
                          "elapsed_seconds": elapsed, "error": f"{type(exc).__name__}: {exc}"}
                _atomic_json(record_path, record)
                return {"state": "INFRA_ERROR", "record": str(record_path), "metrics": record}, 1
    except Exception:
        raise


def run_pytest(
    scope_name: str,
    target: str | None,
    series_id: str | None,
    *,
    worktree_id: str | None = None,
    reason: str | None = None,
    preflight_id: str | None = None,
    execution_manifest: Path | None = None,
    attempt_basis: str | None = None,
    hypothesis_id: str | None = None,
    batch_context: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    policy = load_policy()
    if worktree_id == VV3D_R2_WORKTREE_ID:
        vv3d_r2_entry = policy["worktrees"][VV3D_R2_WORKTREE_ID]
        if scope_name != "fem_exploratory":
            raise PolicyError("VV3D R2 supports only its registered FEM exploratory scope")
        if target not in vv3d_r2_entry["allowed_nodeids"] or target not in VV3D_R2_NODEIDS:
            raise PolicyError("VV3D R2 target is outside its exact twelve-case initial FEM catalogue")
        if not reason or not reason.strip() or not preflight_id or execution_manifest is None:
            raise PolicyError("VV3D R2 requires a reason, exact collect-only preflight and Owner-authorized manifest")
        return run_wp12_vv3d_pytest(
            target, series_id, worktree_id=VV3D_R2_WORKTREE_ID, reason=reason.strip(),
            preflight_id=preflight_id, execution_manifest=Path(execution_manifest),
        )
    if worktree_id == VV3D_WORKTREE_ID:
        vv3d_entry = policy["worktrees"][VV3D_WORKTREE_ID]
        if target not in vv3d_entry["allowed_nodeids"]:
            raise PolicyError("VV3D target is outside the exact initial case catalogue")
        if scope_name != "fem_exploratory":
            raise PolicyError("VV3D only supports its registered FEM exploratory scope")
        if target in VV3D_ADAPTIVE_FEM_NODEIDS and vv3d_entry["runner_capabilities"]["adaptive_fem"] is not True:
            raise PolicyError("VV3D adaptive FEM dispatch is not integrated with the science receipt contract")
        if target in VV3D_QPOST_NODEIDS and vv3d_entry["runner_capabilities"]["qpost"] is not True:
            raise PolicyError("VV3D QPOST dispatch is not integrated with the science receipt/archive contract")
        if target in VV3D_QPOST_NODEIDS:
            if not reason or not reason.strip() or not preflight_id or execution_manifest is None:
                raise PolicyError("VV3D QPOST requires a reason, exact preflight, and exact execution manifest")
            return run_wp12_vv3d_qpost_pytest(
                target, series_id, reason=reason, preflight_id=preflight_id,
                execution_manifest=Path(execution_manifest),
            )
        return run_wp12_vv3d_pytest(
            target, series_id, worktree_id=worktree_id, reason=reason or "",
            preflight_id=preflight_id, execution_manifest=Path(execution_manifest) if execution_manifest else None,
        )
    is_registered = scope_name in WORKTREE_SCOPES
    targets = resolve_targets(scope_name, target, policy, worktree_id=worktree_id)
    entry: dict[str, Any] | None = None
    source_root: Path | None = None
    source_fingerprint: str | None = None
    wp12_registration: dict[str, Any] | None = None
    ledger_context: tuple[Path, Path, str, dict[str, str] | None] | None = None
    controller_provenance: dict[str, Any] | None = None
    execution_manifest_receipt: dict[str, Any] | None = None
    hex8sri_preflight_receipt: tuple[Path, str] | None = None
    wp12_dynamics_preflight_receipt: tuple[Path, str] | None = None
    wp12_expected_ledger_sha256: str | None = None
    if is_registered:
        if not worktree_id or not target or not reason or not reason.strip():
            raise PolicyError("registered worktree tests require one exact target, worktree, and documented reason")
        if batch_context is not None and worktree_id != "wp12_dynamics":
            raise PolicyError("WP12-A batch context is valid only for the Dynamics scope")
        entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
            worktree_id,
            target,
            policy,
        )
        scope = (
            dict(entry["per_node_budgets"][target])
            if worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID
            else dict(entry["budgets"])
        )
        attempt_limit = int(entry.get("attempt_limits_per_nodeid", {}).get(target, entry["attempt_limit_per_nodeid"]))
        if worktree_id in WP12_OWNER_ENVELOPES:
            assert source_fingerprint is not None
            wp12_registration = _wp12_active_registration(worktree_id, target, entry, source_fingerprint)
            scope["timeout_seconds"] = wp12_registration["timeout_seconds"]
        if worktree_id == "d01":
            if preflight_id is None:
                raise PolicyError("D01 FEM attempts require a successful exact-node collect-only preflight first")
            if attempt_basis not in D01_ATTEMPT_BASES:
                raise PolicyError("D01 FEM attempts require a classified attempt basis")
            ledger_context = _node_ledger_context(policy, _run_root(policy, worktree_id), worktree_id)
        elif worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID:
            if preflight_id is None or execution_manifest is None:
                raise PolicyError(
                    "HEX8-SRI execution requires one validated collect-only receipt and a distinct OWNER_AUTHORIZED manifest"
                )
            controller_provenance = _controller_provenance()
            case_manifest_path, case_manifest, case_manifest_sha256 = _hex8sri_convergence24_manifest(
                entry, execution_root, target
            )
            _verify_hex8sri_convergence24_controller_identity(case_manifest, controller_provenance)
            case_contract = _hex8sri_convergence24_case_contract(case_manifest)
            if "x".join(map(str, case_contract["divisions_xyz"])) != _hex8sri_convergence24_case(target)[2]:
                raise PolicyError("HEX8-SRI execution case mesh does not match the exact registered nodeid")
            case_manifest_binding = {
                "path": str(case_manifest_path),
                "sha256": case_manifest_sha256,
                "registration_sha256": _hex8sri_manifest_registration_sha256(case_manifest),
                "case_id": case_manifest["case_id"],
                "scope_id": worktree_id,
            }
            store = _run_root(policy)
            ledger_path, ledger_lock, mandate_id, predecessor = _node_ledger_context(policy, store, worktree_id)
            if predecessor is not None or mandate_id != entry["development_mandate_id"]:
                raise PolicyError("HEX8-SRI execution ledger is not bound to its dedicated campaign mandate")
            _validate_hex8sri_execution_ledger(ledger_path, entry=entry, target=target)
            expected_ledger = {
                "path": str(ledger_path),
                "mandate_id": mandate_id,
                "attempts_reserved": False,
            }
            hex8sri_preflight_receipt = _validate_hex8sri_convergence24_preflight_receipt(
                store,
                preflight_id,
                target=target,
                identity=identity,
                source_fingerprint=source_fingerprint,
                controller_provenance=controller_provenance,
                manifest_binding=case_manifest_binding,
                attempt_ledger=expected_ledger,
            )
            execution_manifest_receipt = _validate_hex8sri_execution_manifest(
                execution_manifest,
                store=store,
                target=target,
                entry=entry,
                identity=identity,
                source_fingerprint=source_fingerprint,
                controller_provenance=controller_provenance,
                case_manifest_binding=case_manifest_binding,
                case_manifest=case_manifest,
                preflight_id=preflight_id,
                preflight_receipt=hex8sri_preflight_receipt,
            )
            _validate_hex8sri_execution_test_contract(execution_root, target)
            ledger_context = (ledger_path, ledger_lock, mandate_id, predecessor)
        elif worktree_id == "wp12_dynamics":
            if preflight_id is None:
                raise PolicyError("WP12-A dynamics attempts require a successful exact-node collect-only preflight")
            controller_provenance = _controller_provenance()
            wp12_dynamics_preflight_receipt = _validate_wp12_dynamics_preflight_receipt(
                _run_root(policy, worktree_id),
                preflight_id,
                target=target,
                identity=identity,
                source_fingerprint=source_fingerprint,
                controller_provenance=controller_provenance,
                policy=policy,
            )
            try:
                preflight_bytes = wp12_dynamics_preflight_receipt[0].read_bytes()
                if hashlib.sha256(preflight_bytes).hexdigest() != wp12_dynamics_preflight_receipt[1]:
                    raise PolicyError("WP12-A preflight receipt changed after validation")
                wp12_expected_ledger_sha256 = json.loads(preflight_bytes)["attempt_ledger"]["sha256_after"]
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise PolicyError(f"WP12-A preflight ledger binding is unreadable: {exc}") from exc
        elif worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
            if preflight_id is None or execution_manifest is None:
                raise PolicyError("WP12-B R2 requires its exact preflight and an authorized manifest")
            controller_provenance = _controller_provenance()
            wp12_dynamics_preflight_receipt = _validate_wp12b_hex20_r2_preflight_receipt(
                _run_root(policy, worktree_id), preflight_id, target=target, identity=identity,
                source_fingerprint=source_fingerprint, controller_provenance=controller_provenance, policy=policy,
            )
            preflight_bytes = wp12_dynamics_preflight_receipt[0].read_bytes()
            if hashlib.sha256(preflight_bytes).hexdigest() != wp12_dynamics_preflight_receipt[1]:
                raise PolicyError("WP12-B R2 preflight changed after validation")
            wp12_expected_ledger_sha256 = json.loads(preflight_bytes)["attempt_ledger"]["sha256_after"]
        elif preflight_id is not None:
            raise PolicyError("preflight receipt IDs are supported only for D01, WP12-A dynamics and HEX8-SRI")
        if worktree_id in WP12_OWNER_ENVELOPES:
            if execution_manifest is None:
                raise PolicyError("WP12 FEM attempts require a distinct Owner-authorized execution manifest")
            assert wp12_registration is not None and source_fingerprint is not None
            controller_provenance = _controller_provenance()
            execution_manifest_receipt = _validate_wp12_execution_manifest(
                execution_manifest,
                worktree_id=worktree_id,
                target=target,
                entry=entry,
                identity=identity,
                source_fingerprint=source_fingerprint,
                controller_fingerprint=_stable_fingerprint(controller_provenance),
                selection=wp12_registration,
                preflight_id=preflight_id if worktree_id in {"wp12_dynamics", WP12B_HEX20_R2_WORKTREE_ID} else None,
                preflight_receipt=wp12_dynamics_preflight_receipt,
                batch_binding=batch_context,
            )
            if worktree_id in {WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID, WP12B_HEX20_R2_WORKTREE_ID}:
                _validate_wp12b_decision_receipt(execution_manifest_receipt)
            # WP12 mandates are scope-specific. Preserve D01's separately handled
            # predecessor ledger while binding every WP12 ledger key to its scope.
            ledger_context = _node_ledger_context(policy, _run_root(policy, worktree_id), worktree_id)
        elif execution_manifest is not None and worktree_id != HEX8SRI_CONVERGENCE24_WORKTREE_ID:
            raise PolicyError("execution manifests are supported only by registered WP12 or HEX8-SRI cases")
    else:
        execution_root = ROOT
        scope = policy["standard_scopes"][scope_name]
        identity = _git_identity(ROOT)
        attempt_limit = int(scope["max_attempts_per_series"])
    if is_registered and scope_name == "fem_exploratory":
        if worktree_id in WP12_OWNER_ENVELOPES:
            scenario_lock = _wp12_resource_lock(
                WP12_COORDINATION_ROOT,
                entry["concurrency_class"],
            )
        elif worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID:
            scenario_lock = _exclusive_file_lock(_run_root(policy) / "locks" / "hex8sri-convergence24-execution.lock")
        else:
            # The lock remains shared by the historical D01/C01 scopes.
            scenario_lock = _exclusive_file_lock(_run_root(policy) / "locks" / "fem-exploratory.lock")
    else:
        scenario_lock = nullcontext()
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    disk_paths = [ROOT, execution_root]
    if worktree_id in WP12_OWNER_ENVELOPES:
        disk_paths.extend([_run_root(policy, worktree_id), WP12_COORDINATION_ROOT])
    elif worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID:
        disk_paths.append(_run_root(policy))
    disk_anchors: list[Path] = []
    for disk_path in disk_paths:
        anchor = disk_path.resolve()
        while not anchor.exists():
            anchor = anchor.parent
        disk_anchors.append(anchor)
    free_bytes = min(shutil.disk_usage(path).free for path in disk_anchors)
    minimum_free = int(policy["minimum_free_disk_mib"] * 1024 * 1024)
    if free_bytes < minimum_free:
        raise PolicyError(f"insufficient free disk: {free_bytes} bytes; requires {minimum_free}")
    inherited_environment = dict(os.environ)
    inherited_native_guard = _native_guard_environment(inherited_environment)
    if (
        worktree_id == "d01"
        and entry is not None
        and entry["allow_native_vv_skip_override"]
        and inherited_native_guard["active_markers"]
    ):
        markers = ", ".join(inherited_native_guard["active_markers"])
        raise PolicyError(
            "D01 native development is refused before reserving an attempt because explicit no-FEM "
            f"environment markers are active: {markers}"
        )
    if series_id is None:
        series_id = f"dev-{uuid.uuid4().hex[:12]}"
    if not SERIES_RE.fullmatch(series_id):
        raise PolicyError("series ID must use the development-only format dev-<lowercase-id>")
    store = _run_root(policy, worktree_id)
    series_dir = _series_root(store, scope_name, worktree_id) / series_id
    preflight_receipt: tuple[Path, str] | None = hex8sri_preflight_receipt or wp12_dynamics_preflight_receipt
    controller_provenance = controller_provenance or _controller_provenance()
    if worktree_id == "d01":
        assert preflight_id is not None and source_fingerprint is not None and target is not None
        preflight_receipt = _validate_d01_preflight_receipt(
            store,
            preflight_id,
            target=target,
            identity=identity,
            source_fingerprint=source_fingerprint,
            controller_provenance=controller_provenance,
            guard_state=_native_guard_environment(inherited_environment),
        )
    with scenario_lock:
        if worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
            assert target is not None and preflight_id is not None and execution_manifest_receipt is not None
            current_policy = load_policy()
            current_entry, _root, _source, current_identity, current_fingerprint = _registered_worktree(
                worktree_id, target, current_policy
            )
            if (current_entry != entry or current_identity != identity or current_fingerprint != source_fingerprint
                    or _controller_provenance() != controller_provenance):
                raise PolicyError("WP12-B R2 source, policy or controller changed before reservation")
            current_preflight = _validate_wp12b_hex20_r2_preflight_receipt(
                store, preflight_id, target=target, identity=identity, source_fingerprint=source_fingerprint,
                controller_provenance=controller_provenance, policy=current_policy,
            )
            if (current_preflight != preflight_receipt
                    or _sha256(Path(execution_manifest_receipt["path"])) != execution_manifest_receipt["sha256"]):
                raise PolicyError("WP12-B R2 preflight or execution manifest changed before reservation")
        number, attempt_dir = _next_attempt(
            series_dir,
            series_id,
            scope_name,
            attempt_limit,
            worktree_id=worktree_id,
            target=targets[0] if is_registered else (target or "<scope>"),
        )
        node_ledger_path, node_ledger_lock, effective_mandate_id, ledger_predecessor = (
            ledger_context
            if ledger_context is not None
            else (
                store / "node-attempt-ledger.json",
                store / "node-attempt-ledger.lock",
                str(policy["mandate_id"]),
                None,
            )
        )
        ledger_key: str | None = None
        ledger_number: int | None = None
        wp12_reserved_ledger_sha256: str | None = None
        if is_registered:
            assert (
                worktree_id is not None and source_fingerprint is not None and reason is not None and target is not None
            )
            try:
                ledger_key, ledger_number = _reserve_node_attempt(
                    node_ledger_path,
                    node_ledger_lock,
                    mandate_id=effective_mandate_id,
                    worktree_id=worktree_id,
                    target=target,
                    series_id=series_id,
                    source_fingerprint=source_fingerprint,
                    reason=reason.strip(),
                    maximum=attempt_limit,
                    total_maximum=(
                        entry.get("max_total_attempts")
                        if worktree_id in WP12_OWNER_ENVELOPES or worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID
                        else None
                    ),
                    wp12_selection=wp12_registration,
                    authorization_id=(
                        execution_manifest_receipt["authorization_id"]
                        if execution_manifest_receipt is not None
                        else None
                    ),
                    owner_decision_id=(
                        execution_manifest_receipt.get("decision_id")
                        if execution_manifest_receipt is not None
                        else None
                    ),
                    predecessor=ledger_predecessor,
                    controller_fingerprint=_stable_fingerprint(controller_provenance),
                    attempt_basis=attempt_basis,
                    hypothesis_id=hypothesis_id,
                    expected_ledger_sha256=wp12_expected_ledger_sha256,
                    require_ledger_snapshot=worktree_id in {"wp12_dynamics", WP12B_HEX20_R2_WORKTREE_ID},
                    batch_binding=batch_context,
                )
                if batch_context is not None or worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
                    wp12_reserved_ledger_sha256 = _sha256(node_ledger_path)
            except Exception:
                attempt_dir.rmdir()
                raise
        temp_dir = attempt_dir / "tmp"
        output_dir = attempt_dir / "output"
        temp_dir.mkdir()
        output_dir.mkdir()
        record_path = attempt_dir / "run.json"
        controller_attempt_id = (
            f"{series_id}-attempt-{ledger_number or number}"
            if worktree_id in {WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID, WP12B_HEX20_R2_WORKTREE_ID}
            and execution_manifest_receipt is not None
            else None
        )
        command = build_pytest_command(
            scope_name,
            targets,
            temp_dir,
            repository_root=execution_root,
            source_root=source_root,
            controller_root=ROOT,
            allow_native_skip_override=bool(entry and entry["allow_native_vv_skip_override"]),
            junit_xml_path=(output_dir / "pytest-results.xml") if worktree_id == "d01" or batch_context is not None else None,
        )
        environment = build_child_environment(
            temp_dir,
            base=inherited_environment,
            source_root=source_root,
            d01_source_sha=identity["head"] if worktree_id == "d01" else None,
            wp12_entry=(
                {**entry, "worktree_id": worktree_id}
                if worktree_id in WP12_OWNER_ENVELOPES and entry is not None
                else None
            ),
            wp12_selection=wp12_registration,
            wp12_attempt_id=controller_attempt_id,
            wp12_manifest_receipt=(
                execution_manifest_receipt if controller_attempt_id is not None else None
            ),
            wp12_run_json_path=record_path if controller_attempt_id is not None else None,
        )
        if worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID:
            assert (
                target is not None
                and preflight_id is not None
                and execution_manifest_receipt is not None
                and controller_provenance is not None
                and hex8sri_preflight_receipt is not None
            )
            controller_identity = controller_provenance["identity"]
            controller_hashes = controller_provenance["sha256"]
            environment.update(
                {
                    "QF_DEV_WORKTREE_ID": HEX8SRI_CONVERGENCE24_WORKTREE_ID,
                    "QF_DEV_CAMPAIGN_SCOPE_ID": HEX8SRI_CONVERGENCE24_WORKTREE_ID,
                    "QF_DEV_TARGET_NODEID": target,
                    "QF_DEV_MANIFEST_PATH": execution_manifest_receipt["path"],
                    "QF_DEV_MANIFEST_SHA256": execution_manifest_receipt["sha256"],
                    "QF_DEV_CASE_MANIFEST_PATH": str(case_manifest_path),
                    "QF_DEV_CASE_MANIFEST_SHA256": case_manifest_sha256,
                    "QF_DEV_PREFLIGHT_ID": preflight_id,
                    "QF_DEV_PREFLIGHT_SHA256": hex8sri_preflight_receipt[1],
                    "QF_DEV_CONTROLLER_ROOT": str(ROOT.resolve()),
                    "QF_DEV_CONTROLLER_BRANCH": controller_identity["branch"],
                    "QF_DEV_CONTROLLER_HEAD": controller_identity["head"],
                    "QF_DEV_CONTROLLER_TREE": controller_identity["tree"],
                    "QF_DEV_CONTROLLER_RUNNER_SHA256": controller_hashes["runner"],
                    "QF_DEV_CONTROLLER_POLICY_SHA256": controller_hashes["policy"],
                    "QF_DEV_CONTROLLER_PLUGIN_SHA256": controller_hashes["pytest_plugin"],
                    "QF_DEV_AUTHORIZATION_ID": execution_manifest_receipt["authorization_id"],
                    "QF_DEV_OWNER_DECISION_ID": execution_manifest_receipt.get("decision_id", ""),
                }
            )
        child_native_guard = _validate_native_guard_environment(inherited_environment, environment)
        started_at = datetime.now(timezone.utc).isoformat()
        initial: dict[str, Any] = {
            "schema": "qfsolver-development-attempt-v2",
            "mode": "DEVELOPMENT_AUTONOMOUS",
            "mandate_id": effective_mandate_id,
            "series_id": series_id,
            "attempt": ledger_number or number,
            **({"controller_attempt_id": controller_attempt_id} if controller_attempt_id is not None else {}),
            "scope": scope_name,
            "worktree_id": worktree_id,
            "target": targets,
            "reason": reason.strip() if reason else None,
            "attempt_basis": attempt_basis,
            "hypothesis_id": hypothesis_id,
            "state": "RUNNING",
            "started_at_utc": started_at,
            "identity": identity,
            "controller_provenance": controller_provenance,
            "source_fingerprint": source_fingerprint,
            "solver_import_root": str(source_root.resolve()) if source_root else None,
            "solver_origin_expected": str((source_root / "solveur" / "__init__.py").resolve()) if source_root else None,
            "native_guard_environment": child_native_guard,
            "preflight_receipt": (
                {"path": str(preflight_receipt[0]), "sha256": preflight_receipt[1]}
                if preflight_receipt is not None
                else None
            ),
            "execution_manifest": execution_manifest_receipt,
            **({"batch_context": dict(batch_context)} if batch_context is not None else {}),
            "command": command,
            "budgets": dict(scope),
            "wp12_case_selection": (
                {
                    **{
                        key: wp12_registration[key]
                        for key in ("selected_dofs", "selection_basis", "timeout_seconds", "timeout_reason")
                    },
                    "checked_before_attempt_reservation": True,
                    "registration_source_fingerprint": wp12_registration["source_fingerprint"],
                }
                if wp12_registration is not None
                else None
            ),
            "wp12_mission_limits": (
                {
                    "max_total_attempts": entry["max_total_attempts"],
                    "max_fem_cases_per_attempt": entry["max_fem_cases_per_attempt"],
                    "target_max_dofs": entry["target_max_dofs"],
                    "concurrency_class": entry["concurrency_class"],
                    "enforcement": "exact nodeid and declared selected DDL are validated before attempt reservation; the cap is also passed to the child test",
                }
                if worktree_id in WP12_OWNER_ENVELOPES and entry is not None
                else None
            ),
            "budget_semantics": {
                "wall_timeout": "watchdog-triggered process-tree termination; best-effort OS control",
                "rss": "sampled soft monitor; not a hard memory/commit limit",
                "process_count": "sampled process-tree monitor; not a job-object boundary",
                "captured_output": "application-enforced byte caps on captured stdout/stderr",
                "temporary_and_archive_size": "sampled size monitoring; not an NTFS quota",
                "free_disk": "preflight and sampled floor check",
                "attempt_limit": "persistent procedural ledger under the mission evidence root",
            },
            "free_disk_before_bytes": free_bytes,
            "qualification": "NOT_APPLICABLE_DEVELOPMENT_ONLY",
            "qualification_promotion": "PROHIBITED",
        }
        _atomic_json(record_path, initial)
        limits = dict(scope)
        limits["minimum_free_disk_mib"] = policy["minimum_free_disk_mib"]
        try:
            result = run_supervised_command(
                command,
                cwd=execution_root,
                environment=environment,
                output_dir=output_dir,
                temporary_dir=temp_dir,
                limits=limits,
                poll_interval=float(policy["poll_interval_seconds"]),
            )
        except OSError as exc:
            finished_at = datetime.now(timezone.utc).isoformat()
            post_fingerprint = (
                _worktree_source_fingerprint(execution_root, target) if is_registered and target else "NOT_CAPTURED"
            )
            final = {
                **initial,
                "state": "LAUNCH_FAILED",
                "finished_at_utc": finished_at,
                "launch_error": f"{type(exc).__name__}: {exc}",
                "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
                "temporary_bytes": _directory_size(temp_dir),
                "output_inventory": _file_inventory(output_dir),
            }
            _atomic_json(record_path, final)
            if ledger_key and ledger_number:
                _complete_node_attempt(
                    node_ledger_path,
                    node_ledger_lock,
                    key=ledger_key,
                    attempt_number=ledger_number,
                    state="LAUNCH_FAILED",
                    finished_at_utc=finished_at,
                    post_fingerprint=post_fingerprint,
                    worktree_id=worktree_id or "",
                    expected_ledger_sha256=wp12_reserved_ledger_sha256,
                )
            return {
                "series_id": series_id,
                "attempt": ledger_number or number,
                "state": "LAUNCH_FAILED",
                "record": str(record_path),
            }, 1
        finished_at = datetime.now(timezone.utc).isoformat()
        post_fingerprint = source_fingerprint
        state = result.status
        if is_registered and target:
            try:
                post_fingerprint = _worktree_source_fingerprint(execution_root, target)
            except PolicyError:
                post_fingerprint = "UNAVAILABLE"
            if post_fingerprint != source_fingerprint:
                state = "SOURCE_CHANGED_DURING_RUN"
        result_payload_complete = None
        result_payload_errors: list[str] = []
        result_payload_metadata: dict[str, Any] | None = None
        if worktree_id == "d01" and target is not None:
            result_payload_complete, result_payload_errors, result_payload_metadata = _validate_d01_junit_payload(
                output_dir / "pytest-results.xml",
                target,
                identity["head"],
                result.return_code,
            )
            state = _d01_final_state(state, result_payload_complete)
        final = {
            **initial,
            "state": state,
            "finished_at_utc": finished_at,
            "return_code": result.return_code,
            "elapsed_seconds": result.elapsed_seconds,
            "peak_rss_bytes": result.peak_rss_bytes,
            "peak_process_count": result.peak_process_count,
            "stdout_bytes": result.stdout_bytes,
            "stderr_bytes": result.stderr_bytes,
            "stdout_sha256": _sha256(output_dir / "stdout.log"),
            "stderr_sha256": _sha256(output_dir / "stderr.log"),
            "output_inventory": _file_inventory(output_dir),
            "result_payload_complete": result_payload_complete,
            "result_payload_errors": result_payload_errors,
            "result_payload_metadata": result_payload_metadata,
            "archive_bytes": result.archive_bytes,
            "temporary_bytes": result.temporary_bytes,
            "post_source_fingerprint": post_fingerprint,
            "stop_reason": result.stop_reason,
            "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
        }
        sidecar_binding = _wp12b_hex20_diagnostic_sidecar(
            worktree_id=worktree_id,
            target=target,
            evidence_root=str(entry.get("evidence_root")) if entry is not None else None,
            attempt_id=controller_attempt_id or "",
            manifest_receipt=execution_manifest_receipt,
            selected_dofs=(wp12_registration or {}).get("selected_dofs"),
            run_json_path=record_path,
            sidecar_limit_bytes=(
                int(entry["budgets"]["archive_size_limit_mib"] * 1024 * 1024)
                if entry is not None and "budgets" in entry
                else None
            ),
        )
        if sidecar_binding is not None:
            final["diagnostic_sidecar"] = sidecar_binding
            if worktree_id == WP12B_HEX20_R2_WORKTREE_ID:
                final["scientific_state"] = result.status
                observed_origin = None
                try:
                    observed_origin = _observed_solver_origin(
                        (output_dir / "stdout.log").read_text(encoding="utf-8", errors="replace")
                        + "\n" + (output_dir / "stderr.log").read_text(encoding="utf-8", errors="replace")
                    )
                    provenance_valid = (
                        post_fingerprint == source_fingerprint
                        and _controller_provenance() == controller_provenance
                        and source_root is not None
                        and observed_origin == str((source_root / "solveur" / "__init__.py").resolve())
                        and sidecar_binding["status"] == "VERIFIED"
                    )
                except (OSError, PolicyError):
                    provenance_valid = False
                final["provenance_state"] = "VERIFIED" if provenance_valid else "PROVENANCE_MISMATCH"
                final["solver_origin_observed"] = observed_origin
                if not provenance_valid:
                    state = "PROVENANCE_MISMATCH"
                    final["state"] = state
            if sidecar_binding["status"] != "VERIFIED":
                state = "PROVENANCE_MISMATCH"
                final["state"] = state
        _atomic_json(record_path, final)
        if ledger_key and ledger_number:
            _complete_node_attempt(
                node_ledger_path,
                node_ledger_lock,
                key=ledger_key,
                attempt_number=ledger_number,
                state=state,
                finished_at_utc=finished_at,
                post_fingerprint=post_fingerprint,
                worktree_id=worktree_id or "",
                expected_ledger_sha256=wp12_reserved_ledger_sha256,
            )
        return {
            "series_id": series_id,
            "attempt": ledger_number or number,
            "state": state,
            "record": str(record_path),
            "metrics": final,
        }, (0 if state == "PASS" else 1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "verify-vv3d-r2-ledger-import",
        help="verify the R2 ledger sibling import and source path without reading or writing a ledger",
    )
    p0_batch_prepare_parser = subparsers.add_parser(
        "prepare-wp12a-p0-batch",
        help="freeze an ordered WP12-A P0 case contract and ledger baseline; does not authorize or run FEM",
    )
    p0_batch_prepare_parser.add_argument("--campaign-id", required=True)
    p0_batch_prepare_parser.add_argument(
        "--case-manifest", action="append", required=True, type=Path,
        help="one exact inspected scientific case manifest; repeat in the approved execution order",
    )
    p0_batch_run_parser = subparsers.add_parser(
        "run-wp12a-p0-batch",
        help="execute an explicitly Owner-authorized closed P0 batch sequentially with JIT preflights",
    )
    p0_batch_run_parser.add_argument("--contract", required=True, type=Path)
    p0_batch_run_parser.add_argument("--contract-sha256", required=True)
    p0_batch_run_parser.add_argument("--decision", required=True, type=Path)
    p0_batch_run_parser.add_argument("--decision-sha256", required=True)
    p0_batch_run_parser.add_argument("--resume", action="store_true")
    preflight_parser = subparsers.add_parser(
        "preflight",
        help=(
            "collect one exact D01, rotor, WP12 dynamics, WP12-B HEX20 diagnostic, "
            "or preparation-only HEX8-SRI node without running its body"
        ),
    )
    preflight_parser.add_argument(
        "--worktree",
        choices=(
            "d01",
            "rotor",
            "wp12_dynamics",
            WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID,
            WP12B_HEX20_R2_WORKTREE_ID,
            HEX8SRI_CONVERGENCE24_WORKTREE_ID,
            VV3D_WORKTREE_ID,
            VV3D_R2_WORKTREE_ID,
        ),
        required=True,
    )
    preflight_parser.add_argument("--target", required=True)
    preflight_parser.add_argument("--preflight-id", help="optional unused pf-<12 lowercase hex> ID")
    registration_parser = subparsers.add_parser(
        "register-nodeid",
        help="append one exact WP12 pytest function to its bounded allowlist without importing or executing it",
    )
    registration_parser.add_argument("--worktree", choices=tuple(WP12_OWNER_ENVELOPES), required=True)
    registration_parser.add_argument("--target", required=True, help="exact tests/unit/module.py::test_function nodeid")
    registration_parser.add_argument("--reason", required=True, help="short scientific or regression rationale")
    registration_parser.add_argument(
        "--selected-dofs", type=int, required=True, help="declared DDL count checked before execution"
    )
    registration_parser.add_argument(
        "--selection-basis", required=True, help="brief mesh/formulation basis for the selected DDL count"
    )
    registration_parser.add_argument(
        "--timeout-seconds",
        type=int,
        choices=(300, 900),
        help="defaults to the scope budget; 900 is exceptional for elements",
    )
    registration_parser.add_argument(
        "--timeout-reason", help="required only for an exceptional 900-second elements case"
    )
    manifest_parser = subparsers.add_parser(
        "prepare-manifest",
        help="write a source-bound WP12 execution-manifest template marked NOT_AUTHORIZED; never runs tests",
    )
    manifest_parser.add_argument("--worktree", choices=tuple(WP12_OWNER_ENVELOPES), required=True)
    manifest_parser.add_argument("--target", required=True, help="one previously registered exact nodeid")
    manifest_parser.add_argument("--authorization-id", required=True)
    manifest_parser.add_argument(
        "--preflight-id",
        help="required for wp12_dynamics; binds the manifest to one successful collect-only receipt",
    )
    hex8sri_manifest_parser = subparsers.add_parser(
        "prepare-hex8sri-manifest",
        help="write an exact HEX8-SRI execution template that remains PREPARED_NOT_AUTHORIZED",
    )
    hex8sri_manifest_parser.add_argument("--target", required=True, help="one exact registered convergence24 nodeid")
    hex8sri_manifest_parser.add_argument(
        "--preflight-id", required=True, help="validated exact-node collect-only receipt ID"
    )
    hex8sri_manifest_parser.add_argument(
        "--authorization-id", required=True, help="unique draft ID; not an Owner grant"
    )
    owner_decision_parser = subparsers.add_parser(
        "archive-hex8sri-owner-decision",
        help="validate and immutably archive a freeze-only or execution decision; never creates a manifest or runs tests",
    )
    owner_decision_parser.add_argument("--decision-json", type=Path, required=True, help="Owner decision JSON input")
    test_parser = subparsers.add_parser("test", help="run one fixed development pytest scope")
    test_parser.add_argument(
        "--scope", choices=("unit", "integration", "fem_exploratory", "math_non_fem"), required=True
    )
    test_parser.add_argument(
        "--target", help="repository-relative test file/nodeid; FEM requires an exact approved nodeid"
    )
    test_parser.add_argument("--series", help="development-only dev-* series ID for bounded follow-up attempts")
    test_parser.add_argument("--worktree", help="registered worktree ID for one exact development nodeid")
    test_parser.add_argument(
        "--reason", help="short documented development hypothesis/reason for a registered nodeid attempt"
    )
    test_parser.add_argument(
        "--preflight-id",
        help="successful exact-node collect-only receipt ID for D01, WP12-A dynamics or HEX8-SRI",
    )
    test_parser.add_argument(
        "--execution-manifest", help="Owner-authorized WP12 or HEX8-SRI manifest under its mission authorization root"
    )
    test_parser.add_argument(
        "--attempt-basis", choices=D01_ATTEMPT_BASES, help="D01 baseline/change/hypothesis classification"
    )
    test_parser.add_argument("--hypothesis-id", help="unique ID required for a same-input new diagnostic hypothesis")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-vv3d-r2-ledger-import":
            ledger_module = _load_vv3d_r2_ledger_module()
            result = {
                "state": "IMPORT_OK",
                "module": ledger_module.__name__,
                "path": str(Path(ledger_module.__file__).resolve()),
                "ledger_class": f"{ledger_module.RecoveryR2Ledger.__module__}.RecoveryR2Ledger",
                "ledger_created": False,
                "attempt_reserved": False,
            }
            exit_code = 0
        elif args.command == "prepare-wp12a-p0-batch":
            from wp12a_p0_batch import prepare_contract

            result = prepare_contract(sys.modules[__name__], args.campaign_id, args.case_manifest)
            exit_code = 0
        elif args.command == "run-wp12a-p0-batch":
            from wp12a_p0_batch import run_batch

            result = run_batch(
                sys.modules[__name__],
                args.contract,
                args.contract_sha256,
                args.decision,
                args.decision_sha256,
                resume=args.resume,
            )
            exit_code = 0 if result["state"] == "BATCH_COMPLETED" else 1
        elif args.command == "register-nodeid":
            result = register_wp12_nodeid(
                args.worktree,
                args.target,
                args.reason,
                selected_dofs=args.selected_dofs,
                selection_basis=args.selection_basis,
                timeout_seconds=args.timeout_seconds,
                timeout_reason=args.timeout_reason,
            )
            exit_code = 0
        elif args.command == "prepare-manifest":
            result = prepare_wp12_execution_manifest(
                args.worktree, args.target, args.authorization_id, preflight_id=args.preflight_id
            )
            exit_code = 0
        elif args.command == "prepare-hex8sri-manifest":
            result = prepare_hex8sri_execution_manifest(args.target, args.preflight_id, args.authorization_id)
            exit_code = 0
        elif args.command == "archive-hex8sri-owner-decision":
            result = archive_hex8sri_owner_decision(args.decision_json)
            exit_code = 0
        elif args.command == "preflight":
            result = preflight_pytest(args.worktree, args.target, args.preflight_id)
            exit_code = 0 if result["state"] == "PREFLIGHT_PASS" else 1
        else:
            result, exit_code = run_pytest(
                args.scope,
                args.target,
                args.series,
                worktree_id=args.worktree,
                reason=args.reason,
                preflight_id=args.preflight_id,
                execution_manifest=(Path(args.execution_manifest) if args.execution_manifest else None),
                attempt_basis=args.attempt_basis,
                hypothesis_id=args.hypothesis_id,
            )
    except PolicyError as exc:
        print(json.dumps({"state": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
