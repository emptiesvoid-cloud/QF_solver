"""Public aggregation of the controlled V1 contact verification studies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from solveur.verification.contact_deformable_master import DeformableMasterContactCampaign
from solveur.verification.contact_master_surface import MasterSurfaceContactCampaign
from solveur.verification.contact_tet4_master import Tet4MasterContactCampaign
from solveur.verification.frictional_contact import FrictionalContactVerificationCampaign
from solveur.verification.frictional_contact_structural import FrictionalStructuralContactCampaign
from solveur.verification.frictionless_contact_structural import FrictionlessStructuralContactCampaign
from solveur.verification.vnv_manifest import write_vnv_manifest


class ContactVerificationCampaign:
    """Run bounded normal-contact and regularized-friction V&V studies."""

    campaign_id = "VNV-CONTACT-V1-001"

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, Any]:
        """Write a self-contained, reviewable verification directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        friction = FrictionalContactVerificationCampaign(self.output_dir / "friction").run()
        structural = FrictionlessStructuralContactCampaign(self.output_dir / "structural").run()
        elastic_master = DeformableMasterContactCampaign(self.output_dir / "elastic_master").run()
        tet4_master = Tet4MasterContactCampaign(self.output_dir / "tet4_master_face").run()
        master_surface = MasterSurfaceContactCampaign(self.output_dir / "master_surface").run()
        frictional_structural = FrictionalStructuralContactCampaign(self.output_dir / "friction_structural").run()
        studies = (friction, structural, elastic_master, tet4_master, master_surface, frictional_structural)
        status = "PASS_INTERNAL" if all(study["status"] == "PASS_INTERNAL" for study in studies) else "FAIL"
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental",
            "studies": [
                {"campaign_id": study["campaign_id"], "status": study["status"], "scope": study["scope"]}
                for study in studies
            ],
            "limitations": [
                "The normal law, a bounded active TET4 master face and saturated frictional slip each have separate Code_Aster correlations; elastic master nodes are internally verified only.",
                "The deformable-master evidence includes one bounded planar TET4 face; it is not a general deformable finite-element surface formulation.",
                "V1 supports bounded selection among explicit master triangles; updated search is restricted to small, frictionless translation iterations and is internally verified only.",
                "Surface-to-surface contact, large sliding and dynamic contact are outside scope.",
            ],
        }
        (self.output_dir / "contact_campaign_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (self.output_dir / "contact_campaign_report.md").write_text(self._markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary

    @staticmethod
    def _markdown(summary: dict[str, Any]) -> str:
        lines = [
            "# Verification contact V1",
            "",
            f"- Campagne : `{summary['campaign_id']}`",
            f"- Verdict interne : `{summary['status']}`",
            "- Maturite : `experimental`",
            "",
            "| Etude | Scope | Verdict |",
            "| --- | --- | --- |",
        ]
        for study in summary["studies"]:
            lines.append(f"| {study['campaign_id']} | {study['scope']} | {study['status']} |")
        lines.extend(
            [
                "",
                "Le dossier contient les resultats, rapports, PNG et manifestes des six etudes. "
                "Un verdict interne PASS ne constitue pas une correlation externe ni une qualification de contact general.",
                "",
            ]
        )
        return "\n".join(lines)
