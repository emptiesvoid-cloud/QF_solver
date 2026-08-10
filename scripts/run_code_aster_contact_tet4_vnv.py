"""Run the pinned Code_Aster correlation for an active TET4 master face."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_contact_tet4 import CodeAsterTet4MasterContactCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/VNV-CONTACT-CODEASTER-TET4-MASTER-004")
    args = parser.parse_args()
    summary = CodeAsterTet4MasterContactCampaign(Path(args.output)).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
