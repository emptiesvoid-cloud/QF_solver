"""Experimental small-displacement contact mechanics."""

from solveur.contact.entities import FrictionlessContact
from solveur.contact.evaluation import (
    ContactEvaluation,
    PenaltyContactRestartMetadata,
    contact_configuration_digest,
    evaluate_penalty_contact,
    validate_penalty_contact_restart_metadata,
)

__all__ = [
    "ContactEvaluation",
    "FrictionlessContact",
    "PenaltyContactRestartMetadata",
    "contact_configuration_digest",
    "evaluate_penalty_contact",
    "validate_penalty_contact_restart_metadata",
]
