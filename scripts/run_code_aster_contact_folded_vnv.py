"""Run the pinned Code_Aster folded-contact final-normal correlation."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_contact_folded import CodeAsterFoldedContactCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/VNV-CONTACT-CODEASTER-FOLDED-NORMAL-006")
    summary = CodeAsterFoldedContactCampaign(Path(parser.parse_args().output)).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
