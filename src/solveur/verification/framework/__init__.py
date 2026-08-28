"""Reusable, release-neutral primitives for controlled V&V campaigns.

This package is deliberately not imported by normal solver execution.  It
provides deterministic case registration, execution and evidence generation
for developer-controlled verification only.
"""

from .case import VnvCase, VnvCaseError
from .registry import VnvRegistry
from .runner import VnvRunner

__all__ = ["VnvCase", "VnvCaseError", "VnvRegistry", "VnvRunner"]
