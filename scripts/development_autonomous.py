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
HEX8SRI_CONVERGENCE24_MANIFEST_BINDING = "canonical_case_content_v1"
HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT = "bb6238db9954ff2992347b980c0dfc681f73b74433f76e01dd94e40811c85ea3"
HEX8SRI_CONVERGENCE24_SOURCE_HEAD = "5304e3f00e73a916d1af4c1d75375a9b051f0524"
HEX8SRI_CONVERGENCE24_SOURCE_TREE = "5d995ab972e8627d266e1cd2b86d2b858b93f84a"
HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_PATH = (
    "docs/development/hex8sri-source-byte-inventory-5304e3f0.json"
)
HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_SHA256 = "13eaa22b2f9ea9bb4c88a9605c96e65451fefef500b2cf32c54905d895bc7b09"
HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_FILE_COUNT = 517
HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT_ALGORITHM = "raw_worktree_inventory_sha256_v1"
HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY = {
    "branch": "research/hex8-sri-equilibrium",
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
    expected_worktree_ids = legacy_worktree_ids | set(WP12_OWNER_ENVELOPES) | {HEX8SRI_CONVERGENCE24_WORKTREE_ID}
    if not isinstance(worktrees, dict) or set(worktrees) != expected_worktree_ids:
        raise PolicyError(
            "the worktree registry must retain all existing scopes and the isolated HEX8-SRI preparation scope"
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
        if not is_wp12 and not is_hex8sri_convergence24 and attempt_limit != 3:
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
            "tests/unit" if worktree_id in {"c01", "e01", *WP12_OWNER_ENVELOPES} else "tests/verification"
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
        or hex8sri.get("branch") != "research/hex8-sri-equilibrium"
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
    if worktree_id in {"wp12_dynamics", WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID}:
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
    wp12_dynamics_collect_only_attestation: bool = False,
    wp12b_hex20_diagnostic_collect_only_attestation: bool = False,
    junit_xml_path: Path | None = None,
) -> list[str]:
    attestation_modes = (
        rotor_collect_only_attestation,
        hex8sri_convergence24_collect_only_attestation,
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
    if worktree_id != WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID:
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
    if (
        not isinstance(recorded, Mapping)
        or recorded.get("schema") != "qfsolver-hex8sri-source-byte-inventory-v1"
        or recorded.get("branch") != identity.get("branch")
        or recorded.get("head") != identity.get("head")
        or recorded.get("tree") != identity.get("tree")
        or recorded.get("fingerprint_sha256") != fingerprint
        or recorded.get("fingerprint_algorithm") != "sha256(sorted(relative_path_utf8 + NUL + raw_file_sha256_bytes))"
        or recorded.get("raw_byte_policy") != "Raw checkout bytes; no LF/CRLF normalization or conversion."
        or recorded.get("inventory_file_count") != len(inventory)
        or recorded.get("files_sha256") != dict(inventory)
    ):
        raise PolicyError("HEX8-SRI source bytes differ from the registered raw-byte inventory")


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
    with _node_attempt_locks(ledger_path, lock_path, worktree_id):
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
    return entry, root, source_root, identity, fingerprint


def _run_root(policy: Mapping[str, Any], worktree_id: str | None = None) -> Path:
    if worktree_id in WP12_OWNER_ENVELOPES:
        root = Path(policy["worktrees"][worktree_id]["evidence_root"]).resolve()
        checkout = Path(policy["worktrees"][worktree_id]["git_root"]).resolve()
        coordination_root = WP12_COORDINATION_ROOT.resolve()
        if _is_within(root, checkout) or _is_within(root, coordination_root) or _is_within(coordination_root, root):
            raise PolicyError("WP12 evidence must be separate from source and shared coordination roots")
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


def _node_ledger_context(
    policy: Mapping[str, Any],
    store: Path,
    worktree_id: str,
) -> tuple[Path, Path, str, dict[str, str] | None]:
    entry = policy["worktrees"][worktree_id]
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
        if worktree_id not in {"d01", "c01", "e01", *WP12_OWNER_ENVELOPES}:
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


def _hex8sri_first6_registration_sha256_by_nodeid(entry: Mapping[str, Any]) -> dict[str, str]:
    registrations = entry.get("case_manifests")
    if not isinstance(registrations, Mapping):
        raise PolicyError("HEX8-SRI registered case-manifest map is missing")
    result: dict[str, str] = {}
    for nodeid in HEX8SRI_FIRST6_NODEIDS:
        binding = registrations.get(nodeid)
        sha256 = binding.get("sha256") if isinstance(binding, Mapping) else None
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise PolicyError("HEX8-SRI first-six registration digest is absent or malformed")
        result[nodeid] = sha256
    return result


def _hex8sri_expected_criteria_freeze(
    *,
    entry: Mapping[str, Any],
    source_fingerprint: str,
    controller_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    controller_identity = controller_provenance.get("identity", {})
    return {
        "schema": HEX8SRI_CRITERIA_FREEZE_SCHEMA,
        "revision": HEX8SRI_CRITERIA_CONTRACT_REVISION,
        "dispositions": HEX8SRI_CRITERIA_DISPOSITIONS,
        "criteria_definitions": HEX8SRI_CRITERIA_DEFINITIONS,
        "frozen_case_gate_criteria": HEX8SRI_FROZEN_CASE_GATE_CRITERIA,
        "frozen_nodeids": list(HEX8SRI_FIRST6_NODEIDS),
        "case_manifest_registration_sha256_by_nodeid": _hex8sri_first6_registration_sha256_by_nodeid(entry),
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
        or decision.get("frozen_nodeids") != list(HEX8SRI_FIRST6_NODEIDS)
        or decision.get("source_fingerprint") != source_fingerprint
        or decision.get("controller_fingerprint") != _stable_fingerprint(controller_provenance)
        or decision.get("controller_head") != identity.get("head")
        or not _strict_json_equal(
            decision.get("criteria_freeze"),
            _hex8sri_expected_criteria_freeze(
                entry=entry,
                source_fingerprint=source_fingerprint,
                controller_provenance=controller_provenance,
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
        or not set(nodeids).issubset(set(HEX8SRI_FIRST6_NODEIDS))
    ):
        raise PolicyError("HEX8-SRI execution decision must select a non-empty unique subset of first-six nodeids")
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
    expected_registrations = _hex8sri_first6_registration_sha256_by_nodeid(entry)
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
    """Require the first-six criteria contract and thresholds to be explicitly Owner-frozen."""
    proposed = case_manifest.get("proposed_criteria")
    frozen = case_manifest.get("frozen_criteria")
    expected_contract = {
        "schema": HEX8SRI_CRITERIA_CONTRACT_SCHEMA,
        "revision": HEX8SRI_CRITERIA_CONTRACT_REVISION,
        "dispositions": HEX8SRI_CRITERIA_PROPOSAL_DISPOSITIONS,
    }
    criteria_freeze = decision.get("criteria_freeze")
    registration_hashes = (
        criteria_freeze.get("case_manifest_registration_sha256_by_nodeid")
        if isinstance(criteria_freeze, Mapping)
        else None
    )
    if (
        target not in HEX8SRI_FIRST6_NODEIDS
        or case_manifest.get("criteria_status") != "OWNER_FREEZE_REQUIRED"
        or not _strict_json_equal(case_manifest.get("criteria_contract"), expected_contract)
        or not _strict_json_equal(proposed, HEX8SRI_PROPOSED_CRITERIA)
        or frozen is not None
        or not isinstance(registration_hashes, Mapping)
        or set(registration_hashes) != set(HEX8SRI_FIRST6_NODEIDS)
        or registration_hashes.get(target) != case_registration_sha256
        or criteria_freeze.get("schema") != HEX8SRI_CRITERIA_FREEZE_SCHEMA
        or criteria_freeze.get("revision") != HEX8SRI_CRITERIA_CONTRACT_REVISION
        or not _strict_json_equal(criteria_freeze.get("dispositions"), HEX8SRI_CRITERIA_DISPOSITIONS)
        or not _strict_json_equal(criteria_freeze.get("criteria_definitions"), HEX8SRI_CRITERIA_DEFINITIONS)
        or not _strict_json_equal(
            criteria_freeze.get("frozen_case_gate_criteria"), HEX8SRI_FROZEN_CASE_GATE_CRITERIA
        )
        or criteria_freeze.get("frozen_nodeids") != list(HEX8SRI_FIRST6_NODEIDS)
    ):
        raise PolicyError(
            "HEX8-SRI Owner decision does not freeze the registered first-six criteria contract; "
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


def _hex8sri_first6_current_case_manifest_bindings(
    entry: Mapping[str, Any], execution_root: Path, controller_provenance: Mapping[str, Any]
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for nodeid in HEX8SRI_FIRST6_NODEIDS:
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
        or not set(nodeids).issubset(set(HEX8SRI_FIRST6_NODEIDS))
    ):
        raise PolicyError("HEX8-SRI execution decision must select a non-empty unique subset of first-six nodeids")
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
        # Require all six regenerated current registrations, but no preflight or ledger.
        _hex8sri_first6_current_case_manifest_bindings(entry, execution_root, controller_provenance)
        directory = _run_root(policy) / "authorizations" / scope_id / "owner-decisions" / "criteria-freeze"
    elif decision_type == "EXECUTION_APPROVED":
        current_bindings = _hex8sri_first6_current_case_manifest_bindings(
            entry, execution_root, controller_provenance
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
            **({"execution_authorized": False, "do_not_execute": True} if worktree_id == "wp12_dynamics" else {}),
            "authorization_id": authorization_id,
            "worktree_id": worktree_id,
            "mandate_id": entry["development_mandate_id"],
            **({"campaign_id": entry["campaign_id"]} if "campaign_id" in entry else {}),
            "target": target,
            "identity": identity,
            "source_fingerprint": source_fingerprint,
            "controller_fingerprint": controller_fingerprint,
            "limits": _wp12_manifest_limits(entry, selection),
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
    target: str, preflight_id: str | None = None, *, policy: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Collect the one exact HEX20 diagnostic node without reserving an attempt."""
    if target != WP12B_HEX20_DIAGNOSTIC_NODEID:
        raise PolicyError("HEX20 diagnostic preflight is limited to its exact registered nodeid")
    return _preflight_wp12_attested_pytest(
        target,
        preflight_id,
        policy=policy,
        worktree_id=WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID,
        schema=WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_SCHEMA,
        marker=WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_MARKER,
        preflight_schema="qfsolver-development-wp12b-hex20-diagnostic-preflight-v1",
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
    if worktree_id == "wp12_dynamics":
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
    if worktree_id == "wp12_dynamics":
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
                        if worktree_id == "wp12_dynamics"
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
                if worktree_id == "wp12_dynamics"
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


def preflight_pytest(
    worktree_id: str,
    target: str,
    preflight_id: str | None = None,
) -> dict[str, Any]:
    """Collect one exact registered node without reserving a FEM attempt."""
    policy = load_policy()
    if worktree_id == "rotor":
        return preflight_rotor_pytest(target, preflight_id, policy=policy)
    if worktree_id == HEX8SRI_CONVERGENCE24_WORKTREE_ID:
        return preflight_hex8sri_convergence24_pytest(target, preflight_id, policy=policy)
    if worktree_id == "wp12_dynamics":
        return preflight_wp12_dynamics_pytest(target, preflight_id, policy=policy)
    if worktree_id == WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID:
        return preflight_wp12b_hex20_diagnostic_pytest(target, preflight_id, policy=policy)
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
                preflight_id=preflight_id if worktree_id == "wp12_dynamics" else None,
                preflight_receipt=wp12_dynamics_preflight_receipt,
                batch_binding=batch_context,
            )
            if worktree_id == WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID:
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
                    require_ledger_snapshot=worktree_id == "wp12_dynamics",
                    batch_binding=batch_context,
                )
                if batch_context is not None:
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
            if worktree_id == WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID and execution_manifest_receipt is not None
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
            HEX8SRI_CONVERGENCE24_WORKTREE_ID,
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
        if args.command == "prepare-wp12a-p0-batch":
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
