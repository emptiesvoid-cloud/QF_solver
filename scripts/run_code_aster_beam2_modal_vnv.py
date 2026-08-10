"""Run the opt-in BEAM2 modal correlation with the pinned Code_Aster Docker image."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.code_aster_beam2_modal import CodeAsterBeam2ModalCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="results/VNV-BEAM2-MODAL-CODEASTER-POUDE-002")
    args = parser.parse_args()
    summary = CodeAsterBeam2ModalCampaign(Path(args.output)).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 3


if __name__ == "__main__":
    raise SystemExit(main())
