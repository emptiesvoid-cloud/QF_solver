# ruff: noqa: F401

"""Shared imports and identifiers for the nonlinear robustness campaign."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.contact.solver import assemble_penalty_contact
from solveur.core.errors import NumericalConvergenceError
from solveur.core.material_state import MaterialStateSession
from solveur.core.material_state import state_digest
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear import NonlinearStaticSolver
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.elements.solid.total_lagrangian_j2 import (
    TotalLagrangianJ2Hex20Element,
    TotalLagrangianJ2Hex8Element,
    TotalLagrangianJ2Tet10Element,
    TotalLagrangianJ2Tet4Element,
)
from solveur.io.manifest import write_json_file
from solveur.materials.solid import SolidMaterial, VonMisesElastoplasticMaterial
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh
from solveur.verification.tet4_total_lagrangian_buckling import TotalLagrangianBucklingCampaign
from solveur.verification.nonlinear_failure_campaign import run_failure_campaign
from solveur.verification.total_lagrangian_structural import trace_sparse_arc_length

ELEMENT_TYPES = ("TET4", "TET10", "HEX8", "HEX20")
CAMPAIGN_ID = "VNV-ROBUSTNESS-NONLINEAR-SOLIDS-025"

__all__ = [name for name in globals() if not name.startswith("__")]
