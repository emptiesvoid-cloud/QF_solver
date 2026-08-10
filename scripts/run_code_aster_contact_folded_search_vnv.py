"""Run the exploratory autonomous Code_Aster folded-contact search study."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_contact_folded_search import CodeAsterFoldedSearchCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/VNV-CONTACT-CODEASTER-FOLDED-SEARCH-007")
    summary = CodeAsterFoldedSearchCampaign(Path(parser.parse_args().output)).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
