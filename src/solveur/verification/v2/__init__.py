"""Declarative V&V v2 contracts and deterministic evidence runner."""

from solveur.verification.v2.runner import (
    ExternalUnavailableError,
    DuplicateJsonKeyError,
    ExecutionOutput,
    ResourceLimitedError,
    VnvEvidence,
    VnvRunner,
    canonical_json_bytes,
    canonical_sha256,
    load_evidence,
    load_cases,
    load_json_strict,
    replay_case,
    validate_case,
)
from solveur.verification.v2.schema import (
    CASE_SCHEMA_VERSION,
    ORACLE_TYPES,
    VERDICTS,
    VnvCase,
    VnvOracle,
    VnvSchemaError,
)

__all__ = [
    "CASE_SCHEMA_VERSION",
    "ORACLE_TYPES",
    "VERDICTS",
    "VnvCase",
    "VnvOracle",
    "VnvSchemaError",
    "ExternalUnavailableError",
    "DuplicateJsonKeyError",
    "ExecutionOutput",
    "ResourceLimitedError",
    "VnvEvidence",
    "VnvRunner",
    "canonical_json_bytes",
    "canonical_sha256",
    "load_evidence",
    "load_cases",
    "load_json_strict",
    "replay_case",
    "validate_case",
]
